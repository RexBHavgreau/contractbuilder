"""The saved-assemblies list with a preview of the highlighted assembly (T-063)."""
import os
import pathlib
import sys
import time
import tkinter as tk
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assembly_helpers  # noqa: E402
import assembly_open_dialog  # noqa: E402
import component_preview  # noqa: E402
from assembly_builder import AssemblyBuilderWindow, shell_file_sha256  # noqa: E402
from component_editor import ComponentEditorWindow  # noqa: E402
from library import ComponentLibrary  # noqa: E402
from test_shell_check import make_shell  # noqa: E402

needs_display = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk window tests need a display; CI runs window tests under xvfb-run.",
)


def preview_text(picker):
    return picker.preview.get("1.0", "end-1c")


def tagged_text(picker, tag):
    ranges = picker.preview.tag_ranges(tag)
    return [picker.preview.get(ranges[i], ranges[i + 1]) for i in range(0, len(ranges), 2)]


def wait_for(root, condition, seconds=3.0):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        if condition():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture
def setup(tmp_path, monkeypatch):
    library = ComponentLibrary(tmp_path / "db.sqlite3")
    shell = make_shell(tmp_path / "layout.docx")
    title = library.create_component("Title", "Agreement title\n\nBody words for {{Publisher Name}}.",
                                     paragraph_styles=["Title"])
    left_out = library.create_component("Optional", "This optional clause is left out.")
    pinned_body = library.create_component("Terms", "The original terms apply.")

    def version(component_id):
        return library.list_component_versions(component_id)[0]["id"]

    first_assembly = library.create_assembly("Publishing contract")
    first_revision = library.save_assembly_revision(
        first_assembly, str(shell), shell_file_sha256(shell),
        [{"component_version_id": version(title), "included": True},
         {"component_version_id": version(left_out), "included": False},
         {"component_version_id": version(pinned_body), "included": True}],
    )
    library.save_component_version(pinned_body, "The revised terms apply.")        # newer wording exists
    second_revision = library.save_assembly_revision(
        first_assembly, str(shell), shell_file_sha256(shell),
        [{"component_version_id": version(title), "included": True},
         {"component_version_id": library.list_component_versions(pinned_body)[0]["id"], "included": True}],
    )
    other = library.create_assembly("Licence agreement")
    other_comp = library.create_component("Licence", "A licence is granted.")
    library.save_assembly_revision(
        other, str(shell), shell_file_sha256(shell),
        [{"component_version_id": version(other_comp), "included": True}],
    )
    monkeypatch.setattr("library.ComponentLibrary", lambda: library)
    opened, edited = [], []
    monkeypatch.setattr(
        assembly_open_dialog, "_open_revision_direct",
        lambda app, store, revision_id, parent: opened.append(revision_id) or object(),
    )
    root = tk.Tk()
    root.geometry("200x100")
    root.update()
    app = SimpleNamespace(root=root, open_assembly_revision=lambda revision: edited.append(revision))
    window = assembly_open_dialog.open_saved_assembly_direct(app)
    root.update()
    yield SimpleNamespace(
        root=root, window=window, library=library, opened=opened, edited=edited, app=app,
        assembly=first_assembly, other=other, first=first_revision, second=second_revision,
    )
    root.destroy()


def test_the_pure_preview_shows_pinned_versions_skips_left_out_components_and_notes_updates():
    revision = {"components": [
        {"component_name": "A", "component_version_number": 1, "markdown": "First **bold**.", "included": True},
        {"component_name": "B", "component_version_number": 2, "markdown": "Dropped.", "included": False},
    ]}
    text = "".join(t for t, _ in assembly_helpers.revision_preview_segments(revision))
    assert "First bold." in text and "Dropped" not in text and "A · version 1" in text
    noted = "".join(t for t, _ in assembly_helpers.revision_preview_segments(revision, has_updates=True))
    assert noted.startswith("Newer wording is available") and "pinned to" in noted
    empty = assembly_helpers.revision_preview_segments({"components": []})
    assert "No components are included" in empty[0][0]


# ---- the window ---------------------------------------------------------------

def select(env, assembly_id):
    env.window.picker.tree.selection_set(str(assembly_id))
    env.window.picker.show_latest_preview()
    env.root.update()


@needs_display
def test_highlighting_an_assembly_previews_its_latest_pinned_wording(setup):
    picker = setup.window.picker
    select(setup, setup.assembly)
    text = preview_text(picker)
    assert "Agreement title" in text and "The revised terms apply." in text
    assert "optional clause" not in text                      # left out of this revision
    assert picker.preview_heading.cget("text").endswith("revision 2")
    select(setup, setup.other)
    assert "A licence is granted." in preview_text(picker) and "Agreement title" not in preview_text(picker)


@needs_display
def test_moving_the_highlight_redraws_after_it_rests(setup):
    picker = setup.window.picker
    picker.tree.selection_set(str(setup.other))
    assert wait_for(setup.root, lambda: "A licence is granted." in preview_text(picker))


@needs_display
def test_fields_and_paragraph_styles_show_in_the_preview(setup):
    picker = setup.window.picker
    select(setup, setup.assembly)
    assert "{{Publisher Name}}" in tagged_text(picker, "field") or any(
        "Publisher Name" in t for t in tagged_text(picker, "field"))
    assert any("Agreement title" in t for t in tagged_text(picker, "para_title"))        # the Title style, centered
    assert str(picker.preview.tag_cget("para_title", "justify")) == "center"


@needs_display
def test_the_preview_shows_pinned_versions_and_says_when_newer_wording_exists(setup):
    picker = setup.window.picker
    # Revision 1 pinned "original terms"; newer wording exists for it.
    picker.show_revision_preview(setup.first["id"], "earlier", has_updates=True)
    setup.root.update()
    text = preview_text(picker)
    assert "The original terms apply." in text and "revised terms" not in text
    assert text.startswith("Newer wording is available")


@needs_display
def test_an_earlier_revision_previews_its_own_wording_before_opening(setup, monkeypatch):
    picker = setup.window.picker
    select(setup, setup.assembly)
    picker.choose_earlier()
    setup.root.update()
    earlier = next(c for c in setup.window.winfo_children() if isinstance(c, tk.Toplevel))
    tree = next(w for w in earlier.winfo_children() if w.winfo_class() == "Treeview")
    tree.selection_set(str(setup.first["id"]))
    setup.root.update()
    assert "The original terms apply." in preview_text(picker)
    assert "(earlier)" in picker.preview_heading.cget("text")
    earlier.destroy()
    setup.root.update()
    assert "The revised terms apply." in preview_text(picker)          # back to the latest


@needs_display
def test_search_keeps_the_preview_in_step_and_says_when_nothing_matches(setup):
    picker = setup.window.picker
    picker.search_var.set("licence")
    setup.root.update()
    picker.show_latest_preview()
    assert "A licence is granted." in preview_text(picker)
    picker.search_var.set("no such assembly")
    setup.root.update()
    assert preview_text(picker) == "No saved assembly matches your search."
    picker.search_var.set("")
    setup.root.update()
    picker.show_latest_preview()
    assert preview_text(picker) != "No saved assembly matches your search."


@needs_display
def test_an_assembly_that_cannot_be_read_shows_a_plain_message_not_an_error(setup, monkeypatch):
    picker = setup.window.picker
    monkeypatch.setattr(setup.library, "get_assembly_revision", lambda _id: (_ for _ in ()).throw(ValueError("boom")))
    picker._cache.clear()
    select(setup, setup.assembly)
    assert "cannot be previewed" in preview_text(picker) and "boom" not in preview_text(picker)


@needs_display
def test_the_window_is_resizable_not_transient_and_the_preview_pane_grows(setup):
    assert setup.window.transient() == ""                       # Windows can maximize it
    assert setup.window.resizable() == (True, True)
    setup.window.geometry("1400x700")
    setup.root.update()
    picker = setup.window.picker
    assert picker.preview.winfo_width() > picker.tree.winfo_width()


@needs_display
def test_edit_in_the_builder_passes_the_revision_and_open_latest_still_opens_the_fields(setup):
    picker = setup.window.picker
    select(setup, setup.assembly)
    picker.edit_latest()
    assert [r["id"] for r in setup.edited] == [setup.second["id"]]
    assert not setup.window.winfo_exists()


@needs_display
def test_open_latest_opens_to_the_fields_from_the_list(setup):
    select(setup, setup.assembly)
    setup.window.picker.open_latest()
    assert setup.opened == [setup.second["id"]]


@needs_display
def test_without_a_builder_callback_there_is_no_edit_button(tmp_path, monkeypatch):
    library = ComponentLibrary(tmp_path / "db.sqlite3")
    shell = make_shell(tmp_path / "layout.docx")
    component = library.create_component("C", "Words.")
    assembly = library.create_assembly("Only")
    library.save_assembly_revision(
        assembly, str(shell), shell_file_sha256(shell),
        [{"component_version_id": library.list_component_versions(component)[0]["id"], "included": True}],
    )
    monkeypatch.setattr("library.ComponentLibrary", lambda: library)
    root = tk.Tk()
    try:
        window = assembly_open_dialog.open_saved_assembly_direct(SimpleNamespace(root=root))
        root.update()
        labels = []

        def walk(widget):
            for child in widget.winfo_children():
                try:
                    labels.append(str(child.cget("text")))
                except tk.TclError:
                    pass
                walk(child)
        walk(window)
        assert "Edit in Build an assembly…" not in labels and "Open latest" in labels
    finally:
        root.destroy()


@needs_display
def test_every_preview_pane_gets_its_tags_from_the_one_shared_function(tmp_path, monkeypatch):
    for module_name in ("showinfo", "showerror"):
        monkeypatch.setattr("tkinter.messagebox." + module_name, lambda *a, **k: None)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "data"))
    root = tk.Tk()
    try:
        library = ComponentLibrary(tmp_path / "db.sqlite3")
        shared = tk.Text(root)
        component_preview.configure_preview_tags(shared)
        editor = ComponentEditorWindow(root, library)
        builder = AssemblyBuilderWindow(root, library)
        root.update()
        expected = set(shared.tag_names()) - {"sel"}
        assert {"component_label", "para_title", "marker", "link_warning"} <= expected
        assert expected <= set(editor.preview.tag_names())
        assert expected <= set(builder.preview.tag_names())
    finally:
        root.destroy()
