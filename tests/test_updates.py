import json

import pytest

import update_checker
from update_checker import ReleaseInfo, UpdateCheckError, check_for_update, version_key


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.1.0", (0, 1)),
        ("v1.12.3", (1, 12, 3)),
        ("release-2.0", (2,)),
    ],
)
def test_version_key(value, expected):
    assert version_key(value) == expected


def test_version_key_rejects_unrecognized_values():
    with pytest.raises(ValueError):
        version_key("development")


def test_version_comparison_uses_numeric_parts():
    assert version_key("0.10.0") > version_key("0.9.9")
    assert version_key("1.0.0") > version_key("0.99.99")
    assert version_key("1.2") == version_key("1.2.0")


def test_release_info_reports_newer_version():
    current = ReleaseInfo("0.1.0", "0.2.0", "https://github.com/releases/tag/v0.2.0",
                         "Version 0.2.0", "", "2026-11-17T00:00:00Z")
    assert current.available


def test_check_for_update_parses_latest_release(monkeypatch):
    payload = {
        "tag_name": "v0.2.0",
        "html_url": "https://github.com/RexBHavgreau/contractbuilder/releases/tag/v0.2.0",
        "name": "Word Template Filler 0.2.0",
        "body": "Release notes",
        "published_at": "2026-11-17T00:00:00Z",
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("/repos/RexBHavgreau/contractbuilder/releases/latest")
        assert timeout == 5.0
        return Response()

    monkeypatch.setattr(update_checker, "urlopen", fake_urlopen)
    result = check_for_update("0.1.0", "RexBHavgreau/contractbuilder")
    assert result.latest_version == "0.2.0"
    assert result.available
    assert result.release_url == payload["html_url"]


def test_private_repository_404_has_actionable_message(monkeypatch):
    from urllib.error import HTTPError
    for name in ("CONTRACTBUILDER_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    def fake_urlopen(_request, timeout):
        raise HTTPError("https://api.github.com", 404, "Not Found", {}, None)

    monkeypatch.setattr(update_checker, "urlopen", fake_urlopen)
    with pytest.raises(UpdateCheckError, match="CONTRACTBUILDER_GITHUB_TOKEN"):
        check_for_update("0.1.0", "RexBHavgreau/contractbuilder")


# ------------------------------------------------- downloading and installing ---

import hashlib
import io

import self_update
from update_checker import ReleaseAsset


def test_release_lists_its_files(monkeypatch):
    payload = {
        "tag_name": "v0.3.0", "html_url": "https://example/r", "name": "v0.3.0",
        "assets": [{"name": self_update.WINDOWS_ASSET, "url": "https://api.github.com/a/1",
                    "browser_download_url": "https://github.com/d/1", "size": 10,
                    "digest": "sha256:abc"}],
    }

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(update_checker, "urlopen", lambda request, timeout: Response(json.dumps(payload).encode()))
    result = check_for_update("0.2.0", "o/r", token="t")
    asset = result.asset(self_update.WINDOWS_ASSET)
    assert asset.size == 10 and asset.digest == "sha256:abc" and asset.api_url.endswith("/a/1")
    assert result.asset("missing.exe") is None


def test_saved_token_is_sent_and_404_says_so(monkeypatch):
    from urllib.error import HTTPError
    seen = {}

    def fake_urlopen(request, timeout):
        seen.update(request.headers)
        raise HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(update_checker, "urlopen", fake_urlopen)
    with pytest.raises(UpdateCheckError) as info:
        check_for_update("0.1.0", "o/r", token="secret")
    assert seen["Authorization"] == "Bearer secret"
    assert info.value.needs_token and "saved token" in str(info.value)


def test_private_without_token_points_to_settings(monkeypatch):
    from urllib.error import HTTPError
    for name in ("CONTRACTBUILDER_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    def fake_urlopen(request, timeout):
        assert "Authorization" not in request.headers
        raise HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(update_checker, "urlopen", fake_urlopen)
    with pytest.raises(UpdateCheckError) as info:
        check_for_update("0.1.0", "o/r")
    assert info.value.needs_token and "Update settings" in str(info.value)


def asset_for(data: bytes, **changes):
    values = dict(name=self_update.WINDOWS_ASSET, api_url="https://api.github.com/assets/1",
                  download_url="https://github.com/dl/1", size=len(data),
                  digest="sha256:" + hashlib.sha256(data).hexdigest())
    values.update(changes)
    return ReleaseAsset(**values)


class FakeOpener:
    def __init__(self, data, record):
        self.data, self.record = data, record

    def open(self, request, timeout):
        self.record.append(request)

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        return Response(self.data)


def test_download_checks_size_and_fingerprint(tmp_path, monkeypatch):
    data = b"MZ new version"
    requests = []
    monkeypatch.setattr(self_update, "_opener", lambda: FakeOpener(data, requests))
    done = []
    out = self_update.download_asset(asset_for(data), tmp_path / "new.exe", token="t",
                                     progress=lambda d, t: done.append((d, t)))
    assert out.read_bytes() == data and done[-1] == (len(data), len(data))
    req = requests[0]
    assert req.full_url == "https://api.github.com/assets/1"          # private: the API address, with the token
    assert req.headers["Accept"] == "application/octet-stream" and req.headers["Authorization"] == "Bearer t"

    requests.clear()
    self_update.download_asset(asset_for(data), tmp_path / "pub.exe")
    assert requests[0].full_url == "https://github.com/dl/1"           # public: no token needed


@pytest.mark.parametrize("changes, words", [
    ({"size": 999}, "should be 999"),
    ({"digest": "sha256:" + "0" * 64}, "fingerprint"),
])
def test_bad_download_is_discarded(tmp_path, monkeypatch, changes, words):
    data = b"MZ tampered"
    monkeypatch.setattr(self_update, "_opener", lambda: FakeOpener(data, []))
    with pytest.raises(self_update.UpdateInstallError, match=words):
        self_update.download_asset(asset_for(data, **changes), tmp_path / "new.exe")
    assert list(tmp_path.iterdir()) == []                              # nothing left behind


def test_redirect_to_file_storage_drops_the_token():
    from urllib.request import Request
    handler = self_update._DropAuthOnRedirect()
    req = Request("https://api.github.com/repos/o/r/releases/assets/1",
                  headers={"Authorization": "Bearer t", "Accept": "application/octet-stream"})
    same = handler.redirect_request(req, None, 302, "Found", {}, "https://api.github.com/other")
    away = handler.redirect_request(req, None, 302, "Found", {},
                                    "https://objects.githubusercontent.com/signed?x=1")
    assert same.get_header("Authorization") == "Bearer t"
    assert away.get_header("Authorization") is None


def test_swap_script_and_command():
    script = self_update.swap_script()
    assert script.isascii() and "%~1" in script and "%~2" in script
    assert "\r\n" in script and "timeout" not in script               # timeout fails without a console
    command = self_update.swap_command(r"C:\Users\A B\Temp\u.cmd", r"D:\Program Files\x\W 1.exe",
                                       r"D:\Program Files\x\W 1.exe.new")
    assert command == (r'cmd.exe /d /s /c ""C:\Users\A B\Temp\u.cmd" "D:\Program Files\x\W 1.exe" '
                       r'"D:\Program Files\x\W 1.exe.new""')


def test_token_saved_privately(tmp_path):
    path = tmp_path / "settings" / "update-settings.json"
    assert self_update.load_token(path) == ""
    self_update.save_token("  abc  ", path)
    assert self_update.load_token(path) == "abc"
    import os
    import stat
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_leftover_note_is_read_once(tmp_path):
    exe = tmp_path / "Word Template Filler.exe"
    note = tmp_path / "Word Template Filler.exe.update-failed.txt"
    note.write_text("could not replace")
    assert self_update.leftover_note(exe) == "could not replace"
    assert not note.exists() and self_update.leftover_note(exe) == ""


def test_only_a_built_windows_app_installs_in_place(monkeypatch):
    monkeypatch.setattr(self_update.sys, "platform", "win32")
    monkeypatch.setattr(self_update.sys, "frozen", True, raising=False)
    assert self_update.can_install_in_place()
    monkeypatch.setattr(self_update.sys, "platform", "darwin")
    assert not self_update.can_install_in_place()
