"""Direct opening of saved assemblies from the main start screen."""
import os
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from types import SimpleNamespace

import pytest
from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import assembly_open_dialog
from assembly_helpers import shell_file_sha256
from library import ComponentLibrary


class FakeApp:
    def __init__(self):
        self.root = object()
        self.calls = []

    def create_assembly_document(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return object()

    def remember_recent(self, entry):
        self.recent = getattr(self, "recent", []) + [entry]


def _saved_revision(tmp_path):
    shell = tmp_path / "layout.docx"
    document = Document()
    document.add_paragraph("Layout shell")
    document.save(shell)
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")
    opening_id = library.create_component(
        "Invented opening", "For {{Client Name}}.", paragraph_styles=()
    )
    opening = library.list_component_versions(opening_id)[0]
    optional_id = library.create_component(
        "Invented optional wording", "Optional {{Optional Detail}}."
    )
    optional = library.list_component_versions(optional_id)[0]
    assembly_id = library.create_assembly("Invented assembly")
    revision = library.save_assembly_revision(
        assembly_id,
        str(shell),
        shell_file_sha256(shell),
        [
            {"component_version_id": opening["id"], "included": True},
            {"component_version_id": optional["id"], "included": False},
        ],
    )
    return library, shell, revision, opening_id


def test_direct_open_uses_pinned_included_wording_and_offers_updates(tmp_path):
    library, shell, revision, opening_id = _saved_revision(tmp_path)
    library.save_component_version(opening_id, "Revised opening for {{Client Name}}.")
    app = FakeApp()

    result = assembly_open_dialog._open_revision_direct(
        app, library, revision["id"], parent=None
    )

    assert result is not None
    assert len(app.calls) == 1
    args, kwargs = app.calls[0]
    assert args[0] == shell
    assert args[2] == "Invented assembly"
    assert len(args[1]) == 1
    assert args[1][0].markdown == "For {{Client Name}}."
    assert kwargs["assembly_revision"]["id"] == revision["id"]
    assert kwargs["assembly_revision"]["has_newer_wording"] is True


def test_changed_or_missing_shell_can_be_reselected_without_changing_saved_revision(
    tmp_path, monkeypatch
):
    library, original_shell, revision, _opening_id = _saved_revision(tmp_path)
    original_shell.unlink()  # Simulate the saved shell having been moved.
    replacement = tmp_path / "replacement.docx"
    document = Document()
    document.add_paragraph("Replacement layout")
    document.save(replacement)

    monkeypatch.setattr(
        "tkinter.messagebox.askyesno", lambda *a, **k: True
    )
    monkeypatch.setattr(
        assembly_open_dialog.filedialog,
        "askopenfilename",
        lambda **_kwargs: str(replacement),
    )
    monkeypatch.setattr(
        "shell_selection.choose_shell",
        lambda *_args, **_kwargs: SimpleNamespace(
            usable=True, needs_review=False, lines=()
        ),
    )

    chosen = assembly_open_dialog._choose_revision_shell(None, revision)

    assert chosen[0] == replacement
    assert chosen[1] == shell_file_sha256(replacement)
    stored = library.get_assembly_revision(revision["id"])
    assert stored["shell_path"] == str(original_shell)
    assert stored["shell_sha256"] == revision["shell_sha256"]


def test_empty_saved_assembly_library_reports_a_plain_language_message(monkeypatch):
    seen = []
    monkeypatch.setattr(
        assembly_open_dialog, "messagebox",
        SimpleNamespace(showinfo=lambda *args, **kwargs: seen.append((args, kwargs))),
    )
    monkeypatch.setattr(
        "library.ComponentLibrary",
        lambda: SimpleNamespace(list_assemblies=lambda: []),
    )
    app = FakeApp()

    result = assembly_open_dialog.open_saved_assembly_direct(app)

    assert result is None
    assert seen
    assert "No saved contract assemblies" in seen[0][0][1]





def _find_widget(widget, predicate):
    for child in widget.winfo_children():
        if predicate(child):
            return child
        found = _find_widget(child, predicate)
        if found is not None:
            return found
    return None


@pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk picker tests need a display; CI runs window tests under xvfb-run.",
)
def test_picker_shows_latest_revision_searches_and_opens_with_enter(monkeypatch):
    class FakeLibrary:
        def list_assemblies(self):
            return [{"id": 4, "name": "Invented searchable assembly"}]

        def list_assembly_revisions(self, _assembly_id):
            return [
                {"id": 42, "number": 3, "created": "2026-11-20T12:00:00Z",
                 "finalized": True, "note": "Latest"},
                {"id": 41, "number": 2, "created": "2026-11-19T12:00:00Z",
                 "finalized": True, "note": "Earlier"},
            ]

        def list_newer_versions_for_revision(self, revision_id):
            return [{"newer_versions": [{"id": 99}]}] if revision_id == 42 else []

    monkeypatch.setattr("library.ComponentLibrary", FakeLibrary)
    opened = []
    monkeypatch.setattr(
        assembly_open_dialog, "_open_revision_direct",
        lambda app, library, revision_id, parent: opened.append(revision_id) or object(),
    )
    root = tk.Tk()
    root.withdraw()
    app = FakeApp()
    app.root = root
    dialog = assembly_open_dialog.open_saved_assembly_direct(app)
    root.update()

    tree = _find_widget(dialog, lambda item: isinstance(item, ttk.Treeview))
    assert tree is not None
    row = tree.item("4", "values")
    assert row == (
        "Invented searchable assembly", "Revision 3", "2026-11-20",
        "New wording available",
    )

    search = _find_widget(dialog, lambda item: isinstance(item, ttk.Entry))
    search.insert(0, "no match")
    root.update()
    assert tree.get_children() == ()

    search.delete(0, "end")
    root.update()
    tree.selection_set("4")
    # Key events go to the focused widget; with no window manager the tree
    # must be given focus first.
    # Key events are dropped by a withdrawn window, so map it briefly.
    root.deiconify()
    root.update()
    tree.focus_force()
    root.update()
    tree.event_generate("<Return>")
    root.update()
    assert opened == [42]

    for child in root.winfo_children():
        try:
            child.destroy()
        except tk.TclError:
            pass
    root.destroy()
