"""Saving an opened assembly under a new name makes a copy (Build an assembly window)."""
import os
import pathlib
import sys
import tkinter as tk

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assembly_builder  # noqa: E402
from assembly_builder import AssemblyBuilderWindow  # noqa: E402
from library import ComponentLibrary  # noqa: E402
from test_shell_check import make_shell  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk window tests need a display; CI runs window tests under xvfb-run.",
)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    for name in ("showinfo", "showerror"):
        monkeypatch.setattr(assembly_builder.messagebox, name, lambda *a, **k: None)
    monkeypatch.setattr(assembly_builder.messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(assembly_builder.messagebox, "askyesnocancel", lambda *a, **k: False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "data"))
    root = tk.Tk()
    root.geometry("200x100")
    library = ComponentLibrary(tmp_path / "db.sqlite3")
    component_id = library.create_component("Clause", "Some wording.")
    shell = make_shell(tmp_path / "layout.docx")
    builder = AssemblyBuilderWindow(root, library)
    root.update()
    builder._set_shell(shell)
    version = library.list_component_versions(component_id)[0]
    builder.items.append({
        "key": 1, "component_id": component_id, "component_version_id": version["id"],
        "component_name": "Clause", "component_version_number": version["number"],
        "markdown": version["markdown"], "paragraph_styles": [], "included": True,
    })
    builder._next_item_key = 2
    yield root, builder, library
    root.destroy()


def names(library):
    return [a["name"] for a in library.list_assemblies()]


def test_the_name_can_be_changed_after_opening_and_saving_makes_a_copy(setup):
    root, builder, library = setup
    builder.name_variable.set("Original")
    assert builder.save_assembly()
    original_id = builder.assembly_id
    assert str(builder.name_entry.cget("state")) != "readonly"          # editable once saved
    builder.name_variable.set("Copy of original")
    assert "Saving will create a new assembly named Copy of original" in builder.status.cget("text")
    assert "Original will stay as it is" in builder.status.cget("text")
    assert builder.save_assembly()
    assert builder.assembly_id != original_id
    assert sorted(names(library)) == ["Copy of original", "Original"]
    assert len(library.list_assembly_revisions(original_id)) == 1      # the original is untouched
    assert len(library.list_assembly_revisions(builder.assembly_id)) == 1
    assert "Saved as a new assembly, Copy of original" in builder.status.cget("text")
    assert "Original was not changed" in builder.status.cget("text")


def test_the_copy_pins_the_same_component_versions(setup):
    root, builder, library = setup
    builder.name_variable.set("Original")
    builder.save_assembly()
    first = library.get_assembly_revision(builder.revision_id)["components"][0]["component_version_id"]
    builder.name_variable.set("Second")
    builder.save_assembly()
    copied = library.get_assembly_revision(builder.revision_id)["components"][0]["component_version_id"]
    assert copied == first


def test_an_opened_assembly_can_be_renamed_into_a_copy(setup):
    root, builder, library = setup
    builder.name_variable.set("Saved earlier")
    builder.save_assembly()
    assembly_id = builder.assembly_id
    revision = library.get_assembly_revision(builder.revision_id)
    builder._load_revision(revision)                                    # as "Open saved" does
    assert str(builder.name_entry.cget("state")) != "readonly"
    builder.name_variable.set("Based on saved earlier")
    assert builder.save_assembly()
    assert builder.assembly_id != assembly_id
    assert len(library.list_assembly_revisions(assembly_id)) == 1


def test_a_change_of_capitals_or_spacing_alone_is_the_same_assembly(setup):
    root, builder, library = setup
    builder.name_variable.set("Original")
    builder.save_assembly()
    original_id = builder.assembly_id
    builder.name_variable.set("  ORIGINAL ")
    assert "Saving will create" not in builder.status.cget("text")
    builder.items[0]["included"] = True
    builder.save_assembly()
    assert builder.assembly_id == original_id
    assert names(library) == ["Original"]
    assert len(library.list_assembly_revisions(original_id)) == 2       # a new revision, as before


def test_saving_under_the_same_name_still_adds_a_revision(setup):
    root, builder, library = setup
    builder.name_variable.set("Same")
    builder.save_assembly()
    builder.save_assembly()
    assert names(library) == ["Same"]
    assert len(library.list_assembly_revisions(builder.assembly_id)) == 2


def test_an_unsaved_rename_counts_as_an_unsaved_change(setup):
    root, builder, library = setup
    builder.name_variable.set("Original")
    builder.save_assembly()
    assert builder.saved_snapshot == builder._snapshot()
    builder.name_variable.set("Renamed")
    assert builder.saved_snapshot != builder._snapshot()
