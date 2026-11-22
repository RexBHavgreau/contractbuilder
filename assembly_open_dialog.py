"""Opening a saved assembly: the chooser window and loading a revision into the builder."""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Mapping

from assembly_helpers import shell_file_sha256


def open_saved_assembly(builder):
    if not builder._confirm_replace():
        return
    choices = []
    for assembly in builder.library.list_assemblies():
        for revision in builder.library.list_assembly_revisions(assembly["id"]):
            if revision["finalized"]:
                choices.append(
                    {
                        "assembly": assembly,
                        "revision": revision,
                    }
                )
    if not choices:
        messagebox.showinfo(
            "No saved assemblies",
            "Save an assembly first. Saved assemblies will appear here.",
            parent=builder.window,
        )
        return

    dialog = tk.Toplevel(builder.window)
    dialog.title("Open a saved assembly")
    dialog.geometry("680x420")
    dialog.minsize(500, 300)
    dialog.lift()
    dialog.columnconfigure(0, weight=1)
    dialog.rowconfigure(0, weight=1)
    tree = ttk.Treeview(
        dialog, columns=("assembly", "revision", "saved"),
        show="headings", selectmode="browse",
    )
    tree.heading("assembly", text="Assembly")
    tree.heading("revision", text="Revision")
    tree.heading("saved", text="Saved")
    tree.column("assembly", width=300, anchor="w")
    tree.column("revision", width=90, anchor="center", stretch=False)
    tree.column("saved", width=140, anchor="w", stretch=False)
    tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
    scroll = ttk.Scrollbar(dialog, orient="vertical", command=tree.yview)
    scroll.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
    tree.configure(yscrollcommand=scroll.set)
    by_id = {}
    for choice in choices:
        assembly = choice["assembly"]
        revision = choice["revision"]
        key = str(revision["id"])
        by_id[key] = choice
        tree.insert(
            "", "end", iid=key,
            values=(
                assembly["name"],
                f"Revision {revision['number']}",
                str(revision["created"])[:10],
            ),
        )

    def open_selected(_event=None):
        selected = tree.selection()
        if not selected:
            return
        choice = by_id.get(selected[0])
        if choice is None:
            return
        revision = builder.library.get_assembly_revision(choice["revision"]["id"])
        if revision is None:
            messagebox.showerror(
                "Assembly unavailable",
                "That saved revision could not be read.",
                parent=dialog,
            )
            return
        builder._load_revision(revision)
        dialog.destroy()

    tree.bind("<Double-1>", open_selected)
    actions = ttk.Frame(dialog, padding=(12, 0, 12, 12))
    actions.grid(row=1, column=0, columnspan=2, sticky="ew")
    ttk.Button(actions, text="Cancel", command=dialog.destroy).pack(side="right")
    ttk.Button(
        actions, text="Open", command=open_selected
    ).pack(side="right", padx=(0, 7))
    tree.selection_set(str(choices[0]["revision"]["id"]))


def load_revision(builder, revision: Mapping[str, object]):
    builder.assembly_id = int(revision["assembly_id"])
    builder.revision_id = int(revision["id"])
    builder.assembly_name = str(revision["assembly_name"])
    builder.name_variable.set(builder.assembly_name)

    shell_path = Path(str(revision["shell_path"]))
    expected_digest = str(revision["shell_sha256"])
    if shell_path.is_file():
        try:
            actual_digest = shell_file_sha256(shell_path)
        except OSError:
            actual_digest = ""
    else:
        actual_digest = ""
    if actual_digest and actual_digest == expected_digest:
        builder.shell_digest = expected_digest
        builder.shell_variable.set(str(shell_path))
        builder.status.configure(
            text=f"Opened {builder.assembly_name} · revision {revision['number']}."
        )
    else:
        builder.shell_digest = ""
        builder.shell_variable.set(str(shell_path))
        builder.status.configure(
            text=(
                f"Opened {builder.assembly_name} · revision {revision['number']}. "
                "Its shell is missing or has changed; choose a usable shell before saving."
            )
        )

    builder.items = []
    for component in revision["components"]:
        builder.items.append(
            {
                "key": builder._next_item_key,
                "component_id": int(component["component_id"]),
                "component_version_id": int(component["component_version_id"]),
                "component_name": str(component["component_name"]),
                "component_version_number": int(component["component_version_number"]),
                "markdown": str(component["markdown"]),
                "paragraph_styles": list(component.get("paragraph_styles") or []),
                "included": bool(component["included"]),
            }
        )
        builder._next_item_key += 1
    builder._render_items(builder.items[0]["key"] if builder.items else None)
    builder.saved_snapshot = builder._snapshot()
    builder._refresh_newer_versions(
        f"Opened {builder.assembly_name} · revision {revision['number']}."
    )



def _revision_has_newer_wording(library, revision_id):
    try:
        return any(
            row["newer_versions"]
            for row in library.list_newer_versions_for_revision(revision_id)
        )
    except (ValueError, OSError):
        return False


def _choose_revision_shell(parent, revision):
    """Return a usable shell path and digest, asking for a replacement if needed."""
    from tkinter import messagebox
    import shell_selection
    from layout_file_dialog import confirm_layout_file

    shell_path = Path(str(revision["shell_path"]))
    expected = str(revision["shell_sha256"])
    try:
        actual = shell_file_sha256(shell_path) if shell_path.is_file() else ""
    except OSError:
        actual = ""
    if actual and actual == expected:
        return shell_path, actual

    if not messagebox.askyesno(
        "Choose the page layout file again",
        (
            "The page layout file saved with this assembly is missing or has changed. "
            "Choose the current Word page layout file to continue. The saved assembly "
            "and its wording will not be changed."
        ),
        parent=parent,
    ):
        return None
    selected = filedialog.askopenfilename(
        parent=parent,
        title="Choose the page layout file for this assembly",
        filetypes=[
            ("Word documents and templates", "*.docx *.dotx"),
            ("All files", "*.*"),
        ],
    )
    if not selected:
        return None
    try:
        check = shell_selection.choose_shell(selected, remember=False)
        if not check.usable:
            messagebox.showerror(
                "This page layout file cannot be used",
                "\\n".join(check.lines),
                parent=parent,
            )
            return None
        if check.needs_review and not confirm_layout_file(parent, check.lines):
            return None
        chosen = shell_selection.choose_shell(selected, remember=True)
        return Path(selected), shell_file_sha256(selected)
    except (OSError, ValueError) as exc:
        messagebox.showerror(
            "Could not use this page layout file", str(exc), parent=parent
        )
        return None


def _open_revision_direct(app, library, revision_id, parent):
    from docx_compose import ComponentText

    revision = library.get_assembly_revision(revision_id)
    if revision is None or not revision.get("finalized"):
        messagebox.showerror(
            "Assembly unavailable",
            "That saved assembly revision could not be read. Refresh the list and try again.",
            parent=parent,
        )
        return None
    shell = _choose_revision_shell(parent, revision)
    if shell is None:
        return None
    shell_path, shell_digest = shell
    # A replacement shell is used for this document only. The immutable saved
    # revision continues to retain the path and digest it originally recorded.
    revision["shell_path"] = str(shell_path)
    revision["shell_sha256"] = shell_digest
    revision["has_newer_wording"] = _revision_has_newer_wording(
        library, int(revision["id"])
    )
    component_text = [
        ComponentText(
            str(item["markdown"]),
            tuple(item.get("paragraph_styles") or ()),
        )
        for item in revision["components"] if item["included"]
    ]
    app.remember_recent({
        "kind": "assembly",
        "key": str(revision["assembly_id"]),
        "label": str(revision["assembly_name"]),
    })
    return app.create_assembly_document(
        shell_path,
        component_text,
        revision["assembly_name"],
        assembly_revision=revision,
    )


def open_latest_revision(app, assembly_id: int):
    """Open the newest finalized revision of an assembly straight to its fields."""
    from library import ComponentLibrary

    library = ComponentLibrary()
    revisions = [
        item for item in library.list_assembly_revisions(int(assembly_id))
        if item["finalized"]
    ]
    if not revisions:
        messagebox.showerror(
            "Assembly unavailable",
            "This assembly has no saved revision any more. Remove it from the list.",
            parent=app.root,
        )
        return None
    return _open_revision_direct(app, library, int(revisions[0]["id"]), app.root)


def open_saved_assembly_direct(app):
    """Search saved assemblies and open a selected pinned revision to its fields."""
    from library import ComponentLibrary

    library = ComponentLibrary()
    assemblies = []
    for assembly in library.list_assemblies():
        revisions = [
            item for item in library.list_assembly_revisions(assembly["id"])
            if item["finalized"]
        ]
        if revisions:
            latest = revisions[0]
            assemblies.append({
                "assembly": assembly,
                "latest": latest,
                "has_updates": _revision_has_newer_wording(library, latest["id"]),
            })
    if not assemblies:
        messagebox.showinfo(
            "No saved assemblies",
            "No saved contract assemblies are available yet. Build and save an assembly first.",
            parent=app.root,
        )
        return None

    import assembly_picker_window

    def open_revision(revision_id, parent):
        # Looked up when called, so a replacement of _open_revision_direct is honoured.
        return _open_revision_direct(app, library, revision_id, parent)

    edit_revision = getattr(app, "open_assembly_revision", None)
    picker = assembly_picker_window.AssemblyPicker(
        app, library, assemblies, open_revision, edit_revision
    )
    picker.window.picker = picker        # a handle for tests and callers
    return picker.window
