"""The user guide's section outline and its Help window (side menu)."""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import user_guide_outline  # noqa: E402

GUIDE = (ROOT / "USER-GUIDE.txt").read_text(encoding="utf-8")


def _titles(headings):
    return [(h.level, h.title) for h in headings]


def test_main_sections_and_their_steps_are_found_in_the_real_guide():
    found = _titles(user_guide_outline.outline(GUIDE))
    assert (1, "CHOOSING THE RIGHT KIND OF FIELD") in found
    assert (2, "A worked example") in found
    assert (2, "1. CHOOSE WHERE TO START") in found
    assert (1, "STARTING A CONTRACT") in found
    assert (1, "PRIVACY") in found


def test_the_title_block_is_not_a_section():
    titles = [h.title for h in user_guide_outline.outline(GUIDE)]
    assert "CONTRACT BUILDER" not in titles
    assert "USER INSTRUCTIONS" not in titles


def test_body_text_in_capitals_is_not_mistaken_for_a_heading():
    text = "TITLE LINE\n\nFIRST SECTION\n\nSome body text.\nA SHORT NOTE IN CAPITALS INSIDE A SENTENCE\n\nMore."
    titles = [h.title for h in user_guide_outline.outline(text)]
    assert titles == ["FIRST SECTION"]


def test_line_numbers_point_at_the_heading_text():
    lines = GUIDE.split("\n")
    for heading in user_guide_outline.outline(GUIDE):
        assert heading.title in lines[heading.line - 1]


def test_a_guide_without_a_blank_line_has_no_outline():
    assert user_guide_outline.outline("ONLY A TITLE") == []


def test_the_help_window_offers_every_heading_as_a_contents_item():
    tk = pytest.importorskip("tkinter")
    import os
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        pytest.skip("Tk window tests need a display; CI runs window tests under xvfb-run.")
    import user_guide_window

    root = tk.Tk()
    root.withdraw()
    try:
        window = user_guide_window.open_user_guide(root, GUIDE)
        window.update()
        from tkinter import ttk
        found = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Treeview):
                    found.append(child)
                walk(child)

        walk(window)
        assert len(found) == 1
        tree = found[0]

        def items(parent=""):
            out = []
            for item in tree.get_children(parent):
                out.append(tree.item(item, "text"))
                out.extend(items(item))
            return out

        titles = items()
        expected = [h.title for h in user_guide_outline.outline(GUIDE)]
        assert titles == expected
    finally:
        root.destroy()
