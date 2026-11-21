"""The bundled guide explains how to choose a field type (T-059)."""

from pathlib import Path


GUIDE = Path(__file__).resolve().parents[1] / "USER-GUIDE.txt"


def test_guide_has_field_type_advice_and_comparison():
    guide = GUIDE.read_text(encoding="utf-8")
    start = guide.index("CHOOSING THE RIGHT KIND OF FIELD")
    end = guide.index("OPTIONAL AND ALTERNATIVE WORDING", start)
    section = guide[start:end]

    for heading in (
        "Plain text",
        "Date",
        "Amount",
        "List",
        "Choice",
        "Yes/no clause",
        "Different wording by a value",
        "Singular or plural",
        "A worked example",
    ):
        assert heading in section

    assert "| If the person filling in the form needs to…" in section
    assert "{{One-time Fee Wording | choice:" in section
    assert "{{#if One-time Fee Applies}}" in section
    assert "Keep field names short" in section


def test_template_help_includes_the_field_type_section():
    source = (GUIDE.parent / "help_windows.py").read_text(encoding="utf-8")
    assert 'window.title("How to write a template and choose fields")' in source
    assert 'contents.index("WRITING A TEMPLATE")' in source
    assert 'contents.index("TEMPLATE CHECKS", start)' in source


def test_guide_has_the_starting_a_contract_section():
    guide = GUIDE.read_text(encoding="utf-8")
    start = guide.index("STARTING A CONTRACT")
    end = guide.index("COMPONENTS AND ASSEMBLED CONTRACTS", start)
    section = guide[start:end]
    for words in ("Existing contract assembly", "New contract assembly", "Word file", "Recent", "Remove from list"):
        assert words in section
