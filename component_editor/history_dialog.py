"""Read-only version history of one component."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def open_version_history_dialog(parent, component, versions):
    """Show the saved versions of a component, newest first; return the dialog."""
    dialog = tk.Toplevel(parent)
    dialog.title(f"Version history · {component['name']}")
    dialog.geometry("760x560")
    dialog.minsize(560, 400)
    dialog.lift()
    dialog.columnconfigure(0, weight=1)
    dialog.rowconfigure(1, weight=1)

    ttk.Label(
        dialog,
        text="Saved wording is read-only. Each version remains available to assemblies that use it.",
        wraplength=720,
    ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

    body = ttk.Frame(dialog, padding=(12, 0, 12, 8))
    body.grid(row=1, column=0, sticky="nsew")
    body.columnconfigure(0, weight=1)
    body.columnconfigure(1, weight=0)
    body.columnconfigure(2, weight=3)
    body.rowconfigure(0, weight=1)
    history = ttk.Treeview(
        body, columns=("version", "date", "note"), show="headings",
        selectmode="browse",
    )
    history.heading("version", text="Version")
    history.heading("date", text="Saved")
    history.heading("note", text="Version note")
    history.column("version", width=60, anchor="center", stretch=False)
    history.column("date", width=120, anchor="w", stretch=False)
    history.column("note", width=170, anchor="w")
    history.grid(row=0, column=0, sticky="nsew")
    history_scroll = ttk.Scrollbar(body, orient="vertical", command=history.yview)
    history_scroll.grid(row=0, column=1, sticky="ns")
    history.configure(yscrollcommand=history_scroll.set)

    detail = ttk.LabelFrame(body, text="Saved wording", padding=7)
    detail.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
    detail.columnconfigure(0, weight=1)
    detail.rowconfigure(1, weight=1)
    detail_info = ttk.Label(detail, text="", wraplength=430)
    detail_info.grid(row=0, column=0, sticky="w", pady=(0, 6))
    wording = tk.Text(detail, wrap="word", state="disabled", padx=7, pady=6)
    wording.grid(row=1, column=0, sticky="nsew")
    wording_scroll = ttk.Scrollbar(detail, orient="vertical", command=wording.yview)
    wording_scroll.grid(row=1, column=1, sticky="ns")
    wording.configure(yscrollcommand=wording_scroll.set)

    by_id = {str(version["id"]): version for version in versions}
    for version in versions:
        history.insert(
            "", "end", iid=str(version["id"]),
            values=(
                f"v{version['number']}",
                str(version["created"])[:10],
                version["note"] or "",
            ),
        )

    def show_version(_event=None):
        selected = history.selection()
        if not selected:
            return
        version = by_id.get(selected[0])
        if version is None:
            return
        detail_info.configure(
            text=f"Version {version['number']} · {version['created']}"
            + (f" · {version['note']}" if version["note"] else "")
        )
        wording.configure(state="normal")
        wording.delete("1.0", "end")
        wording.insert("1.0", version["markdown"])
        wording.configure(state="disabled")

    history.bind("<<TreeviewSelect>>", show_version)
    if versions:
        history.selection_set(str(versions[0]["id"]))
        show_version()

    ttk.Button(dialog, text="Close", command=dialog.destroy).grid(
        row=2, column=0, sticky="e", padx=12, pady=(0, 12)
    )
    return dialog
