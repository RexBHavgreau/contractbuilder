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
        "name": "Contract Builder 0.2.0",
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


def test_public_repository_404_without_token_says_no_release_yet(monkeypatch):
    from urllib.error import HTTPError
    for name in ("CONTRACTBUILDER_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    def fake_urlopen(_request, timeout):
        raise HTTPError("https://api.github.com", 404, "Not Found", {}, None)

    monkeypatch.setattr(update_checker, "urlopen", fake_urlopen)
    with pytest.raises(UpdateCheckError) as info:
        check_for_update("0.1.0", "RexBHavgreau/contractbuilder")
    assert str(info.value) == (
        "GitHub has no published release for this app yet, or the repository has moved."
    )
    assert not info.value.needs_token


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
    exe = tmp_path / "Contract Builder.exe"
    note = tmp_path / "Contract Builder.exe.update-failed.txt"
    note.write_text("could not replace")
    assert self_update.leftover_note(exe) == "could not replace"
    assert not note.exists() and self_update.leftover_note(exe) == ""


def test_only_a_built_windows_app_installs_in_place(monkeypatch):
    monkeypatch.setattr(self_update.sys, "platform", "win32")
    monkeypatch.setattr(self_update.sys, "frozen", True, raising=False)
    assert self_update.can_install_in_place()
    monkeypatch.setattr(self_update.sys, "platform", "darwin")
    assert not self_update.can_install_in_place()


@pytest.mark.parametrize("age, removed", [(24 * 60 * 60 + 1, True), (24 * 60 * 60, False), (60, False)])
def test_cleanup_stale_update_download_only_removes_files_older_than_one_day(tmp_path, age, removed):
    import os
    import time

    target = tmp_path / "Contract Builder.exe"
    leftover = tmp_path / "Contract Builder.exe.new"
    leftover.write_bytes(b"partial or abandoned update")
    now = time.time()
    os.utime(leftover, (now - age, now - age))

    assert self_update.cleanup_stale_update_download(target, now=now) is removed
    assert leftover.exists() is not removed


def test_cleanup_stale_update_download_ignores_missing_file(tmp_path):
    target = tmp_path / "Contract Builder.exe"
    assert not self_update.cleanup_stale_update_download(target, now=10**10)


def test_cleanup_stale_update_download_does_not_follow_symlinks(tmp_path):
    target = tmp_path / "Contract Builder.exe"
    outside = tmp_path / "keep.me"
    outside.write_text("keep")
    leftover = tmp_path / "Contract Builder.exe.new"
    try:
        leftover.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are unavailable")
    assert not self_update.cleanup_stale_update_download(target, now=10**10)
    assert outside.read_text() == "keep"


# --------------------------------------------- update-check frequency/limits ---

@pytest.mark.parametrize(
    ("status", "headers"),
    [
        (403, {"X-RateLimit-Remaining": "0"}),
        (403, {"Retry-After": "60"}),
        (429, {}),
    ],
)
def test_rate_limited_update_check_has_a_clear_retry_message(monkeypatch, status, headers):
    from urllib.error import HTTPError

    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, status, "Limited", headers, None)

    monkeypatch.setattr(update_checker, "urlopen", fake_urlopen)
    with pytest.raises(UpdateCheckError) as info:
        check_for_update("0.3.0", "o/r")

    assert str(info.value) == (
        "GitHub is limiting update checks from your network for now. "
        "The app will try again later."
    )
    assert not info.value.needs_token


def test_ordinary_403_is_not_misreported_as_a_rate_limit(monkeypatch):
    from urllib.error import HTTPError

    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(update_checker, "urlopen", fake_urlopen)
    with pytest.raises(UpdateCheckError) as info:
        check_for_update("0.3.0", "o/r")

    assert str(info.value) == (
        "GitHub refused the update check. If you saved an optional token, "
        "check it in Help > Update settings."
    )
    assert not info.value.needs_token


def test_successful_update_check_time_limits_only_automatic_checks(tmp_path, monkeypatch):
    import simple_app

    settings = tmp_path / "update-settings.json"
    fixed_now = 1_800_000_000.0
    self_update.record_successful_update_check(settings, now=fixed_now)
    assert not self_update.automatic_update_check_due(
        settings, now=fixed_now + self_update.AUTOMATIC_CHECK_INTERVAL_SECONDS - 1
    )
    assert self_update.automatic_update_check_due(
        settings, now=fixed_now + self_update.AUTOMATIC_CHECK_INTERVAL_SECONDS
    )

    monkeypatch.setattr(self_update, "settings_path", lambda: settings)
    started = []

    class FakeThread:
        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            started.append(self)

    monkeypatch.setattr(simple_app.threading, "Thread", FakeThread)
    app = simple_app.WordTemplateFiller.__new__(simple_app.WordTemplateFiller)
    app.update_checking = False
    app.status = type("Status", (), {"config": lambda self, **kwargs: None})()
    app.check_for_updates(manual=False)
    assert not app.update_checking
    assert not started

    app.check_for_updates(manual=True)
    assert app.update_checking
    assert len(started) == 1


def test_update_settings_keep_the_saved_token_when_recording_a_check(tmp_path):
    path = tmp_path / "update-settings.json"
    self_update.save_token("private-token", path)
    self_update.record_successful_update_check(path, now=1_800_000_000.0)

    settings = json.loads(path.read_text(encoding="utf-8"))
    assert settings["github_token"] == "private-token"
    assert settings["last_successful_check"] == 1_800_000_000.0
    assert self_update.load_token(path) == "private-token"


def test_restart_environment_is_clean_for_a_pyinstaller_one_file_app():
    env = self_update.clean_restart_environment({
        "PATH": "keep",
        "_MEIPASS2": r"C:\Temp\_MEI12345",
        "_PYI_APPLICATION_HOME_DIR": r"C:\Temp\_MEI12345",
        "_pyi_archive_file": "old.exe",
    })
    assert env["PATH"] == "keep"
    assert env["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert not any(name.upper().startswith("_PYI_") or name.upper() == "_MEIPASS2" for name in env)


def test_start_swap_passes_the_clean_environment(tmp_path, monkeypatch):
    seen = {}

    def fake_popen(command, **kwargs):
        seen.update(kwargs)

    monkeypatch.setenv("_PYI_APPLICATION_HOME_DIR", "stale")
    monkeypatch.setattr(self_update.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(self_update.subprocess, "Popen", fake_popen)
    self_update.start_swap(tmp_path / "app.exe", tmp_path / "app.exe.new")
    assert seen["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert "_PYI_APPLICATION_HOME_DIR" not in seen["env"]


class _Release:
    """Only what windows_download needs: the version and an asset lookup."""

    def __init__(self, version, names):
        self.latest_version = version
        self._items = {name: object() for name in names}

    def asset(self, name):
        return self._items.get(name)


def test_windows_download_prefers_the_versioned_name():
    both = _Release("0.4.5", [self_update.WINDOWS_ASSET, "ContractBuilder-0.4.5-windows-x64.exe"])
    assert self_update.windows_download(both) is both.asset("ContractBuilder-0.4.5-windows-x64.exe")


def test_windows_download_accepts_the_fixed_name_for_older_releases():
    fixed = _Release("0.4.4", [self_update.WINDOWS_ASSET])
    assert self_update.windows_download(fixed) is fixed.asset(self_update.WINDOWS_ASSET)


def test_windows_download_ignores_a_versioned_name_for_another_version():
    other = _Release("0.4.5", ["ContractBuilder-0.4.4-windows-x64.exe"])
    assert self_update.windows_download(other) is None


def test_windows_download_is_none_without_a_windows_file():
    assert self_update.windows_download(_Release("0.4.5", ["macOS.zip"])) is None


def test_versioned_name_follows_the_pattern():
    assert self_update.versioned_windows_asset("0.4.5") == "ContractBuilder-0.4.5-windows-x64.exe"
