"""Small real-window tests. CI runs this module under xvfb-run on Linux."""
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import tkinter.ttk as ttk
import tkinter as tk

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import assembly_builder  # noqa: E402
import component_editor  # noqa: E402
from assembly_builder import AssemblyBuilderWindow, shell_file_sha256  # noqa: E402
from component_editor import ComponentEditorWindow  # noqa: E402
from docx import Document  # noqa: E402
from library import ComponentLibrary  # noqa: E402


pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk window tests need a display; CI runs this module under xvfb-run.",
)


def _replace_wording(editor, text):
    editor.wording.configure(state="normal")
    editor.wording.delete("1.0", "end")
    editor.wording.insert("1.0", text)
    editor.editor_markdown_mode = True
    editor.wording.edit_modified(False)
    editor._refresh_editor_styling()
    editor._update_toolbar_state()


def test_component_and_assembly_windows_work_under_a_virtual_display(
    tmp_path, monkeypatch
):
    root = tk.Tk()
    root.geometry("320x120")
    root.update()

    # Dialogs must never pause CI waiting for a person.
    monkeypatch.setattr(component_editor.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(component_editor.messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(component_editor.messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(
        component_editor.filedialog, "askopenfilename", lambda *a, **k: ""
    )
    monkeypatch.setattr(assembly_builder.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(assembly_builder.messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(assembly_builder.messagebox, "askyesno", lambda *a, **k: True)

    editor = None
    builder = None
    opened_dialog = {}
    try:
        library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")
        editor = ComponentEditorWindow(root, library)
        root.update()

        # Resize through the real minimum and normal/maximized-like widths.
        for width in (820, 1060, 1460):
            editor.window.geometry(f"{width}x720+0+0")
            root.update()
            editor._layout_toolbar(force=True)
            root.update()
            assert all(
                widget.winfo_manager() == "place"
                for widget in editor.toolbar_button_widgets.values()
            )
            overflow = [
                (
                    name, widget.winfo_rootx(), widget.winfo_width(),
                    widget.winfo_rootx() + widget.winfo_width(),
                    editor.toolbar.winfo_rootx(), editor.toolbar.winfo_width(),
                    widget.place_info().get("y"), widget.place_info().get("x"),
                    widget.winfo_reqwidth(),
                )
                for name, widget in editor.toolbar_button_widgets.items()
                if widget.winfo_rootx() + widget.winfo_width()
                > editor.toolbar.winfo_rootx() + editor.toolbar.winfo_width() + 1
            ]
            assert not overflow, (
                width, overflow,
                [
                    (
                        name, widget.winfo_reqwidth(), widget.winfo_width(),
                        widget.place_info().get("y"), widget.place_info().get("x"),
                    )
                    for name, widget in editor.toolbar_button_widgets.items()
                ],
            )
        assert len({
            int(widget.place_info()["y"])
            for widget in editor.toolbar_button_widgets.values()
        }) > 1

        # Typing and saving must leave a visible confirmation in the window.
        editor.name_variable.set("Smoke-test clause")
        editor.wording.delete("1.0", "end")
        editor.wording.insert("1.0", "Payment is due within thirty days.")
        root.update()
        assert editor.save_component()
        assert editor.status.cget("text").startswith("Saved Smoke-test clause")
        component_id = editor.current_component_id
        assert component_id is not None

        # Invoke the actual controls twice: each style should undo itself.
        _replace_wording(editor, "Alpha beta")
        editor.wording.tag_add("sel", "1.0", "1.5")
        editor.bold_button.invoke()
        assert editor.wording.get("1.0", "end-1c") == "**Alpha** beta"
        editor.bold_button.invoke()
        assert editor.wording.get("1.0", "end-1c") == "Alpha beta"

        editor.source_view_variable.set(True)
        editor.toggle_source_view()
        editor.wording.tag_remove("sel", "1.0", "end")
        editor.wording.tag_add("sel", "1.6", "1.10")
        editor.italic_button.invoke()
        assert editor.wording.get("1.0", "end-1c") == "Alpha *beta*"
        editor.italic_button.invoke()
        assert editor.wording.get("1.0", "end-1c") == "Alpha beta"

        _replace_wording(editor, "Heading text")
        editor.wording.mark_set("insert", "1.3")
        editor.heading_menu.invoke(2)  # Heading 2
        assert editor.wording.get("1.0", "end-1c") == "## Heading text"
        editor.heading_menu.invoke(2)
        assert editor.wording.get("1.0", "end-1c") == "Heading text"

        _replace_wording(editor, "First item\nSecond item")
        editor.wording.tag_add("sel", "1.0", "2.11")
        editor.bullet_button.invoke()
        assert editor.wording.get("1.0", "end-1c") == "- First item\n- Second item"
        editor.bullet_button.invoke()
        assert editor.wording.get("1.0", "end-1c") == "First item\nSecond item"

        editor.wording.tag_remove("sel", "1.0", "end")
        editor.wording.tag_add("sel", "1.0", "2.11")
        editor.numbered_button.invoke()
        assert editor.wording.get("1.0", "end-1c") == "1. First item\n1. Second item"
        editor.numbered_button.invoke()
        assert editor.wording.get("1.0", "end-1c") == "First item\nSecond item"

        # Open and close the real modal field picker without blocking the test.
        field_dialog_type = component_editor.FieldInsertDialog
        def capture_field_dialog(*args, **kwargs):
            opened_dialog["dialog"] = field_dialog_type(*args, **kwargs)
            return opened_dialog["dialog"]
        monkeypatch.setattr(component_editor, "FieldInsertDialog", capture_field_dialog)
        editor.open_field_dialog()
        root.update()
        assert "dialog" in opened_dialog
        assert opened_dialog["dialog"].window.winfo_exists()
        opened_dialog["dialog"].window.destroy()
        root.update()

        # Open the assembly window, add the saved component, and save a revision.
        builder = AssemblyBuilderWindow(editor.window, library)
        root.update()
        builder.library_tree.selection_set(str(component_id))
        builder._add_selected_component()
        assert len(builder.items) == 1

        shell_path = tmp_path / "smoke-shell.docx"
        document = Document()
        document.add_paragraph("Shell wording is replaced during assembly.")
        document.save(shell_path)
        builder.shell_variable.set(str(shell_path))
        builder.shell_digest = shell_file_sha256(shell_path)
        builder.name_variable.set("Smoke-test assembly")
        assert builder.save_assembly()
        assert builder.assembly_id is not None
        assert builder.revision_id is not None
    finally:
        if opened_dialog.get("dialog") is not None:
            try:
                opened_dialog["dialog"].window.destroy()
            except tk.TclError:
                pass
        if builder is not None:
            try:
                builder.window.destroy()
            except tk.TclError:
                pass
        if editor is not None:
            try:
                editor.window.destroy()
            except tk.TclError:
                pass
        root.destroy()



def _find_widget(widget, predicate):
    for child in widget.winfo_children():
        if predicate(child):
            return child
        found = _find_widget(child, predicate)
        if found is not None:
            return found
    return None


def test_saved_assembly_picker_opens_latest_and_lists_earlier_revisions(
    tmp_path, monkeypatch
):
    import assembly_open_dialog

    root = tk.Tk()
    root.geometry("760x460")
    library = ComponentLibrary(tmp_path / "publisher_profiles.sqlite3")
    component_id = library.create_component("Picker smoke clause", "Pinned wording.")
    component_version = library.list_component_versions(component_id)[0]
    shell_path = tmp_path / "picker-shell.docx"
    document = Document()
    document.add_paragraph("Shell wording")
    document.save(shell_path)
    assembly_id = library.create_assembly("Picker smoke assembly")
    first = library.save_assembly_revision(
        assembly_id, str(shell_path), shell_file_sha256(shell_path),
        [component_version["id"]],
    )
    latest = library.save_assembly_revision(
        assembly_id, str(shell_path), shell_file_sha256(shell_path),
        [component_version["id"]],
    )
    library.save_component_version(component_id, "Newer pinned wording.")
    monkeypatch.setattr("library.ComponentLibrary", lambda: library)
    opened = []
    monkeypatch.setattr(
        assembly_open_dialog, "_open_revision_direct",
        lambda app, store, revision_id, parent: opened.append(revision_id) or object(),
    )
    app = SimpleNamespace(root=root)

    try:
        dialog = assembly_open_dialog.open_saved_assembly_direct(app)
        root.update()
        tree = _find_widget(dialog, lambda item: isinstance(item, ttk.Treeview))
        assert tree.item(str(assembly_id), "values") == (
            "Picker smoke assembly", "Revision 2",
            str(latest["created"])[:10], "New wording available",
        )
        search = _find_widget(dialog, lambda item: isinstance(item, ttk.Entry))
        search.insert(0, "not found")
        root.update()
        assert tree.get_children() == ()
        search.delete(0, "end")
        root.update()
        tree.selection_set(str(assembly_id))
        tree.focus_set()
        root.update()
        tree.event_generate("<Return>", when="tail")
        root.update()
        assert opened == [latest["id"]]

        dialog = assembly_open_dialog.open_saved_assembly_direct(app)
        root.update()
        earlier_button = _find_widget(
            dialog,
            lambda item: isinstance(item, ttk.Button)
            and item.cget("text") == "Earlier revisions…",
        )
        assert earlier_button is not None
        earlier_button.invoke()
        root.update()
        earlier = next(
            child for child in dialog.winfo_children()
            if isinstance(child, tk.Toplevel)
        )
        earlier_tree = _find_widget(
            earlier, lambda item: isinstance(item, ttk.Treeview)
        )
        assert earlier_tree.get_children() == (str(first["id"]),)
        assert earlier_tree.item(str(first["id"]), "values")[0] == "Revision 1"
        earlier_tree.selection_set(str(first["id"]))
        earlier_tree.focus_set()
        root.update()
        earlier_tree.event_generate("<Return>", when="tail")
        root.update()
        assert opened == [latest["id"], first["id"]]
    finally:
        root.destroy()
