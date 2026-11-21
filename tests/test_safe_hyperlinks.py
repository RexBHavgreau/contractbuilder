"""Tests for the allowlist used by component hyperlinks."""
import pytest

from safe_hyperlinks import safe_hyperlink_target


@pytest.mark.parametrize(
    "target",
    [
        "https://example.com/terms",
        "http://example.com:8080/path?q=one%20two",
        "mailto:legal@example.com",
        "mailto:first@example.com,second@example.com?subject=Contract",
    ],
)
def test_allows_supported_external_targets(target):
    assert safe_hyperlink_target(target) == target


@pytest.mark.parametrize(
    "target",
    [
        "",
        " https://example.com",
        "https://example.com ",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "ftp://example.com/file",
        "//example.com/path",
        "https:/missing-host",
        "https:///missing-host",
        "https://user:secret@example.com",
        "https://example.com:99999/path",
        "https://example.com\\\\evil.test",
        "https://example.com/path|other",
        "https://example.com/%0d%0aBcc:evil@example.com",
        "https://example.com/%3Cscript%3E",
        "mailto:",
        "mailto:missing-at-sign",
        "mailto://example.com",
        "mailto:person@",
        "mailto:@example.com",
    ],
)
def test_rejects_unsupported_or_malformed_targets(target):
    assert safe_hyperlink_target(target) is None


def test_rejects_non_string_targets():
    assert safe_hyperlink_target(None) is None
    assert safe_hyperlink_target(42) is None
