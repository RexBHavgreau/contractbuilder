"""The Paragraph style control in the Components window (T-061)."""
import os
import pathlib
import sys
import tkinter as tk

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import component_editor  # noqa: E402
from component_editor import ComponentEditorWindow  # noqa: E402
from library import ComponentLibrary  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk window tests need a display; CI runs window tests under xvfb-run.",
)

TEXT = "# Heading\n\nFirst words\n\nSecond words\n\nThird words"


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


def _set_text(editor, text):
    editor.wording.configure(state="normal")
    editor.wording.delete("1.0", "end")
    editor.wording.insert("1.0", text)
    editor.editor_markdown_mode = True
    editor.wording.edit_modified(False)
    editor._reset_paragraph_styles(text)
    editor._update_toolbar_state()


def _cursor_on(editor, line):
    editor.wording.mark_set("insert", f"{line}.0")
    editor._update_toolbar_state()


def _line_of(text, needle):
    return next(i for i, line in enumerate(text.split("\n"), 1) if needle in line)


def test_choosing_a_style_applies_to_the_paragraph_at_the_cursor(editor):
    _set_text(editor, TEXT)
    _cursor_on(editor, _line_of(TEXT, "Second"))
    assert str(editor.paragraph_style_button.cget("state")) == "normal"
    editor.set_paragraph_style("Title")
    assert editor.paragraph_styles == ["", "Title"]
    assert editor.paragraph_style_variable.get() == "Title"
    editor.window.update()
    editor._update_preview()
    assert editor.preview.tag_ranges("para_title")
    assert editor.preview.get(*editor.preview.tag_ranges("para_title")[:2]).strip() == "Second words"


def test_the_control_is_off_where_it_does_not_apply(editor):
    _set_text(editor, TEXT + "\n\n- a bullet")
    _cursor_on(editor, 1)                                   # the heading
    assert str(editor.paragraph_style_button.cget("state")) == "disabled"
    _cursor_on(editor, _line_of(TEXT + "\n\n- a bullet", "bullet"))
    assert str(editor.paragraph_style_button.cget("state")) == "disabled"
    editor.set_paragraph_style("Title")                     # does nothing, no error
    assert editor.paragraph_styles == []


def test_styles_follow_their_paragraphs_when_the_text_is_edited(editor):
    _set_text(editor, TEXT)
    _cursor_on(editor, _line_of(TEXT, "Second"))
    editor.set_paragraph_style("Subtitle")
    assert editor.paragraph_styles == ["", "Subtitle"]
    editor.wording.insert("3.0", "A new paragraph\n\n")      # before the first text paragraph
    editor.wording.edit_modified(True)
    editor._on_wording_modified()
    assert editor.paragraph_styles == ["", "", "Subtitle"]
    editor.wording.delete("3.0", "5.0")                      # and remove it again
    editor.wording.edit_modified(True)
    editor._on_wording_modified()
    assert editor.paragraph_styles == ["", "Subtitle"]


def test_a_style_change_alone_is_an_unsaved_change_and_a_new_version(editor):
    editor.new_component(prompt=False)
    editor.name_variable.set("Styled")
    _set_text(editor, "Only paragraph")
    editor.saved_snapshot = None
    assert editor.save_component()
    component_id = editor.current_component_id
    assert not editor._has_unsaved_changes()
    _cursor_on(editor, 1)
    editor.set_paragraph_style("Title")
    assert editor._has_unsaved_changes()
    assert editor.save_component()
    versions = editor.library.list_component_versions(component_id)
    assert [v["paragraph_styles"] for v in versions] == [["Title"], []]
    assert [v["number"] for v in versions] == [2, 1]
    assert not editor._has_unsaved_changes()
    assert editor.save_component()                          # unchanged: no third version
    assert len(editor.library.list_component_versions(component_id)) == 2


def test_opening_a_saved_component_restores_its_styles(editor):
    component_id = editor.library.create_component(
        "Saved", "Title here\n\nSub here", paragraph_styles=["Title", "Subtitle"]
    )
    editor._load_component(component_id)
    editor.window.update()
    assert editor.paragraph_styles == ["Title", "Subtitle"]
    assert not editor._has_unsaved_changes()
    _cursor_on(editor, 3)
    assert editor.paragraph_style_variable.get() == "Subtitle"


def test_a_new_blank_component_has_no_styles_and_no_phantom_changes(editor):
    editor.new_component(prompt=False)
    assert editor.paragraph_styles == [] and not editor._has_unsaved_changes()
