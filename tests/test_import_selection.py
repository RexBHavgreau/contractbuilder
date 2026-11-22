"""Importing part of a Word document (T-064-C)."""
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
import import_choice_dialog  # noqa: E402
import import_selection  # noqa: E402
import import_selection_dialog  # noqa: E402
from component_editor import ComponentEditorWindow, wording_actions  # noqa: E402
from library import ComponentLibrary  # noqa: E402

needs_display = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk window tests need a display; CI runs window tests under xvfb-run.",
)


def make_docx(path):
    document = Document()
    document.sections[0].header.paragraphs[0].text = "An invented header"
    document.add_paragraph("An invented title", style="Title")              # 0
    document.add_heading("First section", level=1)                           # 1
    document.add_paragraph("Ordinary opening words.")                         # 2
    quote = document.add_paragraph("A quoted passage.", style="Intense Quote")  # 3
    centered = document.add_paragraph("Centered by hand.")                   # 4
    centered.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph("Bullet one", style="List Bullet")                # 5 (a list)
    document.add_paragraph("Bullet two", style="List Bullet")
    document.add_paragraph("Between the lists.")                              # 6
    document.add_paragraph("Step one", style="List Number")                   # 7 (a list)
    document.add_paragraph("Step two", style="List Number")
    table = document.add_table(rows=1, cols=2)                                # 8
    table.rows[0].cells[0].text = "Left"
    table.rows[0].cells[1].text = "Right"
    document.save(path)
    return path


@pytest.fixture
def imported(tmp_path):
    return docx_to_markdown.import_docx(make_docx(tmp_path / "in.docx"))


def index_of(imported, text):
    return next(i for i, b in enumerate(imported.blocks) if text in b.markdown)


# ---- pure rules -----------------------------------------------------------

def test_every_block_has_a_plain_label_and_a_one_line_preview(imported):
    labels = [import_selection.block_label(b) for b in imported.blocks]
    assert labels[0] == "Title" and "Heading 1" in labels and "Paragraph" in labels
    assert labels.count("List") == 2 and labels[-1] == "Table"
    heading = imported.blocks[index_of(imported, "First section")]
    assert import_selection.block_preview(heading) == "First section"      # no # mark
    long = docx_to_markdown.DocxBlock("paragraph", "word " * 80, "", None, 0, (1,), ())
    assert len(import_selection.block_preview(long)) == 100 and import_selection.block_preview(long).endswith("…")


def test_only_the_ticked_blocks_come_back_in_document_order(imported):
    chosen = [index_of(imported, "Ordinary opening"), index_of(imported, "invented title")]
    result = import_selection.selection_import(imported, chosen)
    assert result.markdown == "An invented title\n\nOrdinary opening words\\."
    assert "First section" not in result.markdown
    assert [b.markdown.startswith("An invented") or "Ordinary" in b.markdown for b in result.blocks] == [True, True]


def test_the_paragraph_styles_travel_with_the_chosen_paragraphs(imported):
    result = import_selection.selection_import(
        imported, [index_of(imported, "Ordinary opening"), index_of(imported, "invented title")]
    )
    assert result.paragraph_styles == ("Title",)
    second = import_selection.selection_import(imported, [index_of(imported, "Ordinary opening")])
    assert second.paragraph_styles == ()


def test_warnings_follow_their_blocks_and_document_notes_stay(imported):
    centered = import_selection.selection_import(imported, [index_of(imported, "Centered by hand")])
    messages = " ".join(w.message for w in centered.warnings)
    assert "centered by hand" in messages and "Headers are not imported" in messages
    plain = import_selection.selection_import(imported, [index_of(imported, "Ordinary opening")])
    assert "centered by hand" not in " ".join(w.message for w in plain.warnings)
    assert "Headers are not imported" in " ".join(w.message for w in plain.warnings)


def test_the_note_about_styles_the_editor_does_not_offer_is_recomputed_for_the_choice(imported):
    with_quote = import_selection.selection_import(imported, [index_of(imported, "quoted passage")])
    assert any(w.location == "style Intense Quote" and w.message.startswith("1 paragraph") for w in with_quote.warnings)
    without = import_selection.selection_import(imported, [index_of(imported, "Ordinary opening")])
    assert not any(w.location.startswith("style ") for w in without.warnings)


def test_a_table_and_a_list_are_taken_whole(imported):
    result = import_selection.selection_import(
        imported, [index_of(imported, "Left"), index_of(imported, "Bullet one")]
    )
    assert "- Bullet one" in result.markdown and "- Bullet two" in result.markdown
    assert "| Left | Right |" in result.markdown.replace("  ", " ") or "Left" in result.markdown


def test_notes_name_skipped_blocks_and_a_numbered_list_taken_without_its_neighbour(imported):
    blocks = imported.blocks
    gap = import_selection.selection_notes(blocks, [index_of(imported, "invented title"), index_of(imported, "Ordinary opening")])
    assert any("between your first and last choice" in n for n in gap)
    contiguous = import_selection.selection_notes(blocks, [0, 1])
    assert contiguous == []
    # Two lists in a row (Word kept one numbered list going across them): taking only
    # the second one starts its numbers again at 1.
    two_lists = [
        docx_to_markdown.DocxBlock("list", "1. one\n1. two", "", None, 0, (1, 2), ()),
        docx_to_markdown.DocxBlock("list", "1. three\n1. four", "", None, 1, (3, 4), ()),
    ]
    assert any("numbers start again at 1" in n for n in import_selection.selection_notes(two_lists, [1]))
    assert import_selection.selection_notes(two_lists, [0, 1]) == []
    assert import_selection.selection_notes(blocks, [index_of(imported, "Step one")]) == []   # after a paragraph: nothing to say
    assert import_selection.selection_notes(blocks, []) == []


def test_choosing_nothing_gives_an_empty_import(imported):
    assert import_selection.selection_import(imported, []).markdown == ""


def test_the_whole_document_import_is_exactly_as_before(imported):
    assert "\n\n".join(b.markdown for b in imported.blocks) == imported.markdown


# ---- the windows ------------------------------------------------------------

@pytest.fixture
def editor(tmp_path, monkeypatch):
    for module in (component_editor.messagebox, component_editor.import_dialog.messagebox, wording_actions.messagebox):
        monkeypatch.setattr(module, "showinfo", lambda *a, **k: None)
        monkeypatch.setattr(module, "showerror", lambda *a, **k: None)
        monkeypatch.setattr(module, "askyesno", lambda *a, **k: True)
    root = tk.Tk()
    root.geometry("200x100")
    root.update()
    window = ComponentEditorWindow(root, ComponentLibrary(tmp_path / "db.sqlite3"))
    root.update()
    yield window
    root.destroy()


def press(root, label):
    def find(widget):
        for child in widget.winfo_children():
            try:
                if child.cget("text") == label:
                    return child
            except tk.TclError:
                pass
            found = find(child)
            if found is not None:
                return found
    dialog = [c for c in root.winfo_children() if isinstance(c, tk.Toplevel)][-1]
    find(dialog).invoke()


@needs_display
def test_the_choice_dialog_offers_whole_or_part_and_no_split_yet(editor):
    root = editor.parent
    root.after(100, lambda: press(root, "Part of it"))
    assert import_choice_dialog.ask_import_mode(root, "x.docx") == import_choice_dialog.PART
    root.after(100, lambda: press(root, "Whole document"))
    assert import_choice_dialog.ask_import_mode(root, "x.docx") == import_choice_dialog.WHOLE
    root.after(100, lambda: press(root, "Cancel"))
    assert import_choice_dialog.ask_import_mode(root, "x.docx") is None

    labels = []

    def collect():
        dialog = [c for c in root.winfo_children() if isinstance(c, tk.Toplevel)][-1]
        def walk(w):
            for child in w.winfo_children():
                try:
                    labels.append(str(child.cget("text")))
                except tk.TclError:
                    pass
                walk(child)
        walk(dialog)
        press(root, "Cancel")
    root.after(100, collect)
    import_choice_dialog.ask_import_mode(root, "x.docx")
    assert not any("Split into components" in t for t in labels)
    root.after(100, lambda: (labels.clear(), press(root, "Cancel")))
    # When the split import exists, the third choice appears.
    root.after(50, collect)
    import_choice_dialog.ask_import_mode(root, "x.docx", split_available=True)
    assert any("Split into components" in t for t in labels)


@needs_display
def test_the_selection_list_ticks_ranges_selects_all_and_clears(editor, imported):
    continued = []
    dialog = import_selection_dialog.ImportSelectionDialog(editor.window, imported, continued.append, "in.docx")
    editor.window.update()
    total = len(imported.blocks)
    assert len(dialog.tree.get_children()) == total and str(dialog.continue_button.cget("state")) == "disabled"
    dialog.toggle(2)
    assert dialog.ticked == {2} and dialog.tree.set("2", "tick") == import_selection_dialog.TICKED
    assert str(dialog.continue_button.cget("state")) == "normal"
    dialog.toggle(5, extend=True)                      # a range from the last one touched
    assert dialog.ticked == {2, 3, 4, 5}
    dialog.toggle(3)
    assert 3 not in dialog.ticked
    dialog.select_all()
    assert dialog.ticked == set(range(total)) and f"{total} of {total} ticked" in dialog.count_label.cget("text")
    dialog.clear()
    assert dialog.ticked == set() and str(dialog.continue_button.cget("state")) == "disabled"
    dialog.window.destroy()


@needs_display
def test_the_notes_show_the_highlighted_blocks_warnings_and_the_choice_notes(editor, imported):
    dialog = import_selection_dialog.ImportSelectionDialog(editor.window, imported, lambda c: None, "in.docx")
    editor.window.update()
    centered = index_of(imported, "Centered by hand")
    dialog.tree.selection_set(str(centered))
    editor.window.update()
    assert "centered by hand" in dialog.notes.get("1.0", "end")
    assert dialog.tree.set(str(centered), "notes").startswith("⚠")
    dialog.toggle(0)
    dialog.toggle(2)
    assert "between your first and last choice" in dialog.notes.get("1.0", "end")
    dialog.window.destroy()


@needs_display
def test_continue_hands_only_the_ticked_blocks_to_the_review_window(editor, imported):
    continued = []
    dialog = import_selection_dialog.ImportSelectionDialog(editor.window, imported, continued.append, "in.docx")
    dialog.toggle(index_of(imported, "Ordinary opening"))
    dialog.continue_to_review()
    assert len(continued) == 1 and continued[0].markdown == "Ordinary opening words\\."
    assert not dialog.window.winfo_exists()
    nothing = import_selection_dialog.ImportSelectionDialog(editor.window, imported, continued.append, "in.docx")
    nothing.continue_to_review()                       # nothing ticked: does nothing
    assert len(continued) == 1
    nothing.window.destroy()


@needs_display
def test_part_of_a_document_goes_through_review_and_is_saved_as_one_component(editor, tmp_path, monkeypatch):
    path = make_docx(tmp_path / "contract.docx")
    monkeypatch.setattr(wording_actions.filedialog, "askopenfilename", lambda **k: str(path))
    monkeypatch.setattr(import_choice_dialog, "ask_import_mode", lambda *a, **k: import_choice_dialog.PART)
    made = {}
    real = import_selection_dialog.ImportSelectionDialog

    def capture(*args, **kwargs):
        made["dialog"] = real(*args, **kwargs)
        return made["dialog"]
    monkeypatch.setattr(wording_actions, "ImportSelectionDialog", capture)
    reviews = []
    real_review = component_editor.ImportReviewDialog

    def review(*args, **kwargs):
        made["review"] = real_review(*args, **kwargs)
        reviews.append(kwargs)
        return made["review"]
    monkeypatch.setattr(component_editor, "ImportReviewDialog", review)

    editor.open_import_dialog()
    dialog = made["dialog"]
    imported = dialog.imported
    dialog.toggle(0)                                           # the Title paragraph
    dialog.toggle(index_of(imported, "Ordinary opening"))
    dialog.continue_to_review()
    review_window = made["review"]
    assert review_window.name_variable.get() == "contract (selection)"
    assert review_window.source.get("1.0", "end-1c") == "An invented title\n\nOrdinary opening words\\."
    review_window.save()
    component = editor.library.list_components()[0]
    version = editor.library.list_component_versions(component["id"])[0]
    assert component["name"] == "contract (selection)"
    assert version["markdown"] == "An invented title\n\nOrdinary opening words\\."
    assert version["paragraph_styles"] == ["Title"]            # the Title style came along


@needs_display
def test_the_whole_document_choice_is_the_old_import_and_cancel_does_nothing(editor, tmp_path, monkeypatch):
    path = make_docx(tmp_path / "contract.docx")
    monkeypatch.setattr(wording_actions.filedialog, "askopenfilename", lambda **k: str(path))
    calls = []
    monkeypatch.setattr(component_editor, "ImportReviewDialog", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(import_choice_dialog, "ask_import_mode", lambda *a, **k: import_choice_dialog.WHOLE)
    editor.open_import_dialog()
    assert calls == [((editor, str(path)), {})]
    monkeypatch.setattr(import_choice_dialog, "ask_import_mode", lambda *a, **k: None)
    editor.open_import_dialog()
    assert len(calls) == 1
