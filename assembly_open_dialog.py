"""Opening a saved assembly: the chooser window and loading a revision into the builder."""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
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
    builder.name_entry.configure(state="readonly")

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
