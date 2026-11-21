"""Direct opening of saved assemblies from the main start screen."""
import sys
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


