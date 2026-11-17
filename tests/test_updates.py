import io
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

    def fake_urlopen(_request, timeout):
        raise HTTPError("https://api.github.com", 404, "Not Found", {}, None)

    monkeypatch.setattr(update_checker, "urlopen", fake_urlopen)
    with pytest.raises(UpdateCheckError, match="CONTRACTBUILDER_GITHUB_TOKEN"):
        check_for_update("0.1.0", "RexBHavgreau/contractbuilder")
