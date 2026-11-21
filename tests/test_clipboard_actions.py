"""Copy, cut and paste in the Components window, and bold next to an escape (T-051-B)."""
import os
import pathlib
import sys
import tkinter as tk

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import component_editor  # noqa: E402
from component_editor import ComponentEditorWindow  # noqa: E402
from component_editor.text_rules import snap_out_of_escapes, toggle_inline_format  # noqa: E402
from library import ComponentLibrary  # noqa: E402

needs_display = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk window tests need a display; CI runs window tests under xvfb-run.",
)

STORED = r"\(hereinafter the **proprietor**\) shall pay {{Fee}}."


# ---- pure rules (no display) --------------------------------------------

def test_a_selection_that_ends_between_a_hidden_backslash_and_its_character_is_pulled_back():
    source = r"\(hereinafter the proprietor\)"
    start = source.index("proprietor")
    end = source.index(")")               # just after the backslash: inside the escape
    assert snap_out_of_escapes(source, start, end) == (start, end - 1)


def test_a_selection_that_starts_inside_an_escape_takes_the_whole_escape():
    source = r"see \(this\)"
    inside = source.index("(")            # after the backslash
    assert snap_out_of_escapes(source, inside, len(source)) == (inside - 1, len(source))


def test_selections_that_split_no_escape_are_unchanged():
    assert snap_out_of_escapes("plain words", 2, 7) == (2, 7)
    source = r"\(a\)"
    assert snap_out_of_escapes(source, 0, len(source)) == (0, len(source))


def test_the_reported_case_bold_next_to_a_parenthesis_never_leaves_a_stray_backslash():
    source = r"\(hereinafter the proprietor\)"
    start = source.index("proprietor")
    end = source.index(")")               # the invisible backslash is inside the selection
    updated, _s, _e = toggle_inline_format(source, start, end, "bold")
    assert updated == r"\(hereinafter the **proprietor**\)"
    assert r"\**" not in updated
    again, _s, _e = toggle_inline_format(updated, updated.index("proprietor"), updated.index("proprietor") + 10, "bold")
    assert again == source                # toggling back restores it exactly


@pytest.mark.parametrize("action", ["bold", "italic"])
def test_toggling_next_to_either_parenthesis_keeps_every_backslash(action):
    source = r"\(inside\) outside \(more\)"
    for word in ("inside", "more"):
        start = source.index(word)
        for end in (start + len(word), start + len(word) + 1):      # with and without the hidden backslash
            updated, _s, _e = toggle_inline_format(source, start, end, action)
            assert updated.count("\\") == source.count("\\")
            assert "\\*" not in updated.replace("\\*", "", 0) or "\\**" not in updated


# ---- the window -----------------------------------------------------------

@pytest.fixture
def editor(tmp_path, monkeypatch):
    for name in ("showinfo", "showerror"):
        monkeypatch.setattr(component_editor.messagebox, name, lambda *a, **k: None)
    monkeypatch.setattr(component_editor.messagebox, "askyesno", lambda *a, **k: True)
    root = tk.Tk()
    root.geometry("200x100")
    root.update()
    window = ComponentEditorWindow(root, ComponentLibrary(tmp_path / "db.sqlite3"))
    root.update()
    yield window
    root.destroy()


def load(editor, text):
    editor.wording.configure(state="normal")
    editor.wording.delete("1.0", "end")
    editor.wording.insert("1.0", text)
    editor.editor_markdown_mode = True
    editor.wording.edit_modified(False)
    editor._refresh_editor_styling()
    editor.window.update()


def select(editor, start, end):
    editor.wording.tag_remove("sel", "1.0", "end")
    editor.wording.tag_add("sel", f"1.0 + {start} chars", f"1.0 + {end} chars")


def clipboard(editor):
    return editor.wording.clipboard_get()


@needs_display
def test_the_reported_case_in_the_window_bold_with_the_hidden_backslash_selected(editor):
    load(editor, r"\(hereinafter the proprietor\)")
    source = editor.wording.get("1.0", "end-1c")
    select(editor, source.index("proprietor"), source.index(")"))      # includes the elided backslash
    editor.apply_format("bold")
    assert editor.wording.get("1.0", "end-1c") == r"\(hereinafter the **proprietor**\)"


@needs_display
def test_copy_gives_the_text_as_shown_with_no_backslashes_or_markers(editor):
    load(editor, STORED)
    select(editor, 0, len(STORED))
    assert editor.copy_visible() == "break"
    assert clipboard(editor) == "(hereinafter the proprietor) shall pay {{Fee}}."


@needs_display
def test_copying_part_of_a_line_gives_just_that_part(editor):
    load(editor, STORED)
    start = STORED.index("proprietor")
    select(editor, start, start + len("proprietor"))
    editor.copy_visible()
    assert clipboard(editor) == "proprietor"


@needs_display
def test_headings_and_list_markers_are_not_copied_but_fields_and_markers_are_kept(editor):
    text = "# Title words\n\n- first item\n\n{{#if Include}}\nOptional {{Name | upper}}\n{{/if}}"
    load(editor, text)
    select(editor, 0, len(text))
    editor.copy_visible()
    copied = clipboard(editor)
    assert "Title words" in copied and "first item" in copied
    assert "# " not in copied and "- first" not in copied
    assert "{{#if Include}}" in copied and "{{Name | upper}}" in copied and "{{/if}}" in copied


@needs_display
def test_cut_puts_the_shown_text_on_the_clipboard_and_removes_the_selection(editor):
    load(editor, STORED)
    start = STORED.index("**proprietor**")
    select(editor, start, start + len("**proprietor**"))
    editor.cut_visible()
    assert clipboard(editor) == "proprietor"
    assert "proprietor" not in editor.wording.get("1.0", "end-1c")


@needs_display
def test_cut_in_protected_wording_copies_but_changes_nothing(editor):
    load(editor, STORED)
    editor.protected_content = True
    select(editor, 0, 5)
    editor.cut_visible()
    assert editor.wording.get("1.0", "end-1c") == STORED
    assert clipboard(editor)


@needs_display
def test_copy_as_stored_text_gives_the_markdown_and_copy_all_keeps_bullets(editor):
    load(editor, "- one\n- two\n\nPlain **bold**.")
    select(editor, 0, len("- one\n- two"))
    editor.copy_stored()
    assert clipboard(editor) == "- one\n- two"
    editor.copy_all_visible()
    copied = clipboard(editor)
    assert copied.startswith("• one\n• two") and "Plain bold." in copied and "**" not in copied


@needs_display
def test_in_the_raw_view_copy_is_the_stored_text_and_the_frame_says_so(editor):
    load(editor, STORED)
    editor.source_view_variable.set(True)
    editor.toggle_source_view()
    assert "Stored text" in editor.edit_frame.cget("text")
    select(editor, 0, len(STORED))
    editor.copy_visible()
    assert clipboard(editor) == STORED
    editor.source_view_variable.set(False)
    editor.toggle_source_view()
    assert editor.edit_frame.cget("text") == "Edit wording"


@needs_display
def test_pasted_ordinary_text_is_escaped_so_it_stays_readable(editor):
    load(editor, "Start: ")
    editor.wording.mark_set("insert", "end-1c")
    editor.wording.clipboard_clear()
    editor.wording.clipboard_append("Fee is **100** (net) and {{Fee}}")
    assert editor.paste_typed_text() == "break"
    stored = editor.wording.get("1.0", "end-1c")
    assert stored == r"Start: Fee is \*\*100\*\* \(net\) and {{Fee}}"
    editor.window.update()
    editor._refresh_editor_styling()
    editor.wording.tag_add("sel", "1.0", "end-1c")
    editor.copy_visible()
    assert clipboard(editor) == "Start: Fee is **100** (net) and {{Fee}}"        # reads as it was pasted


@needs_display
def test_paste_replaces_a_selection_and_keeps_paragraphs(editor):
    load(editor, "keep REPLACE keep")
    select(editor, 5, 12)
    editor.wording.clipboard_clear()
    editor.wording.clipboard_append("one\n\ntwo")
    editor.paste_typed_text()
    assert editor.wording.get("1.0", "end-1c") == "keep one\n\ntwo keep"


@needs_display
def test_paste_in_the_raw_view_or_a_plain_draft_is_left_to_tk(editor):
    load(editor, "x")
    editor.source_view_variable.set(True)
    assert editor.paste_typed_text() is None
    editor.source_view_variable.set(False)
    editor.editor_markdown_mode = False
    assert editor.paste_typed_text() is None


@needs_display
def test_paste_into_protected_wording_does_nothing(editor):
    load(editor, STORED)
    editor.protected_content = True
    editor.wording.clipboard_clear()
    editor.wording.clipboard_append("added")
    assert editor.paste_typed_text() == "break"
    assert editor.wording.get("1.0", "end-1c") == STORED


@needs_display
def test_the_context_menu_offers_the_clipboard_actions(editor):
    labels = [editor.wording_menu.entrycget(i, "label")
              for i in range(editor.wording_menu.index("end") + 1)
              if editor.wording_menu.type(i) == "command"]
    assert labels == ["Cut", "Copy", "Paste", "Copy as stored text", "Copy all wording as text"]


@needs_display
def test_escaped_stars_and_underscores_show_as_themselves_not_as_emphasis(editor):
    load(editor, r"Fee is \*\*100\*\* and file\_name\_here")
    assert not editor.wording.tag_ranges("bold") and not editor.wording.tag_ranges("italic")
    editor.wording.tag_add("sel", "1.0", "end-1c")
    editor.copy_visible()
    assert clipboard(editor) == "Fee is **100** and file_name_here"


@needs_display
def test_real_emphasis_still_works_beside_escaped_marks(editor):
    load(editor, r"A **bold** word and \*not italic\* here")
    assert editor.wording.tag_ranges("bold")
    assert not editor.wording.tag_ranges("italic")
