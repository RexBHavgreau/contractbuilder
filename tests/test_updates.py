import pytest

from update_checker import UpdateCheckError, version_key


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.1.0", (0, 1, 0)),
        ("v1.12.3", (1, 12, 3)),
        ("release-2.0", (2, 0)),
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
