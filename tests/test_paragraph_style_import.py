"""Importing Word paragraph styles, and warning about hand-centered text (T-061)."""
import os
import pathlib
import sys
import tkinter as tk

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import component_editor  # noqa: E402
import docx_to_markdown  # noqa: E402
from component_editor import ComponentEditorWindow  # noqa: E402
from component_editor.import_dialog import ImportReviewDialog  # noqa: E402
from library import ComponentLibrary  # noqa: E402


def make_docx(path):
    document = Document()
    document.add_paragraph("An invented title", style="Title")
    document.add_paragraph("An invented subtitle", style="Subtitle")
    document.add_heading("A heading", level=1)
    document.add_paragraph("Ordinary words.")
    document.add_paragraph("Quoted words.", style="Intense Quote")
    centered = document.add_paragraph("Centered by hand.")
    centered.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph("A bullet", style="List Bullet")
    document.save(path)
    return path


def test_known_styles_are_kept_in_paragraph_order(tmp_path):
    imported = docx_to_markdown.import_docx(make_docx(tmp_path / "in.docx"))
    # Text paragraphs: title, subtitle, ordinary, quote, centered. Heading and list excluded.
    assert imported.paragraph_styles == ("Title", "Subtitle")


def test_unoffered_styles_become_normal_with_a_plain_note(tmp_path):
    imported = docx_to_markdown.import_docx(make_docx(tmp_path / "in.docx"))
    notes = [w.message for w in imported.warnings if w.location == "style Intense Quote"]
    assert notes and "does not offer" in notes[0] and "imported as Normal" in notes[0]


def test_hand_centered_paragraphs_get_a_warning_that_names_the_fix(tmp_path):
    imported = docx_to_markdown.import_docx(make_docx(tmp_path / "in.docx"))
    found = [w for w in imported.warnings if "centered by hand" in w.message]
    assert len(found) == 1
    assert "Title or Subtitle style" in found[0].message
    assert found[0].location.startswith("paragraph")


def test_styles_are_dropped_rather_than_misplaced_when_the_counts_disagree():
    assert docx_to_markdown._importable_styles("One\n\nTwo", ["Title"]) == ()
    assert docx_to_markdown._importable_styles("One\n\nTwo", ["Title", ""]) == ("Title",)


def test_a_file_with_no_special_styles_imports_with_no_styles(tmp_path):
    document = Document()
    document.add_paragraph("Plain one.")
    document.add_paragraph("Plain two.")
    document.save(tmp_path / "plain.docx")
    assert docx_to_markdown.import_docx(tmp_path / "plain.docx").paragraph_styles == ()


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk window tests need a display; CI runs window tests under xvfb-run.",
)
def test_saving_an_import_stores_the_styles_even_after_editing(tmp_path, monkeypatch):
    for name in ("showinfo", "showerror"):
        monkeypatch.setattr(component_editor.messagebox, name, lambda *a, **k: None)
    monkeypatch.setattr(component_editor.import_dialog.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(component_editor.import_dialog.messagebox, "showerror", lambda *a, **k: None)
    root = tk.Tk()
    root.geometry("200x100")
    try:
        editor = ComponentEditorWindow(root, ComponentLibrary(tmp_path / "db.sqlite3"))
        dialog = ImportReviewDialog(editor, make_docx(tmp_path / "in.docx"))
        dialog.name_variable.set("Imported")
        # The reviewer inserts a new paragraph above the title: styles must follow.
        dialog.source.insert("1.0", "Added first\n\n")
        dialog.save()
        component_id = editor.library.list_components()[0]["id"]
        version = editor.library.list_component_versions(component_id)[0]
        assert version["paragraph_styles"] == ["", "Title", "Subtitle"]
    finally:
        root.destroy()
