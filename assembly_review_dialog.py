"""The Review updates window of the assembly builder."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from assembly_helpers import update_component_items, version_diff_lines


def review_updates(builder):
    """Compare pinned wording with newer options; save only checked choices."""
    pending = [item for item in builder.items if item.get("newer_versions")]
    if not pending:
        messagebox.showinfo(
            "No newer versions",
            "Every component in this revision is already at its latest saved version.",
            parent=builder.window,
        )
        return

    dialog = tk.Toplevel(builder.window)
    dialog.title("Review component updates")
    dialog.geometry("980x650")
    dialog.minsize(760, 480)
    dialog.lift()
    dialog.columnconfigure(0, weight=1)
    dialog.rowconfigure(1, weight=1)
    ttk.Label(
        dialog,
        text=("New wording is available for the pinned components below. "
              "Nothing changes unless you tick an item and save the selected updates."),
        wraplength=940,
    ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

    body = ttk.Panedwindow(dialog, orient="horizontal")
    body.grid(row=1, column=0, sticky="nsew", padx=12)
    left = ttk.LabelFrame(body, text="Pinned components", padding=7)
    left.columnconfigure(0, weight=1)
    left.rowconfigure(0, weight=1)
    body.add(left, weight=2)
    tree = ttk.Treeview(
        left, columns=("update", "component", "pinned", "latest"),
        show="headings", selectmode="browse",
    )
    for column, label, width in (
        ("update", "Update", 62), ("component", "Component", 170),
        ("pinned", "Pinned", 66), ("latest", "Latest", 66),
    ):
        tree.heading(column, text=label)
        tree.column(
            column, width=width,
            anchor="center" if column != "component" else "w",
            stretch=column == "component",
        )
    tree.grid(row=0, column=0, sticky="nsew")
    tree_scroll = ttk.Scrollbar(left, orient="vertical", command=tree.yview)
    tree_scroll.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=tree_scroll.set)

    right = ttk.LabelFrame(body, text="Wording changes", padding=8)
    right.columnconfigure(0, weight=1)
    right.rowconfigure(2, weight=1)
    body.add(right, weight=3)
    ttk.Label(right, text="Compare the pinned wording with a newer version:").grid(
        row=0, column=0, sticky="w"
    )
    version_variable = tk.StringVar(master=dialog)
    version_combo = ttk.Combobox(
        right, textvariable=version_variable, state="readonly", width=36
    )
    version_combo.grid(row=1, column=0, sticky="w", pady=(5, 7))
    diff_text = tk.Text(
        right, wrap="none", state="disabled", font="TkFixedFont", padx=7, pady=6
    )
    diff_text.grid(row=2, column=0, sticky="nsew")
    diff_y = ttk.Scrollbar(right, orient="vertical", command=diff_text.yview)
    diff_y.grid(row=2, column=1, sticky="ns")
    diff_text.configure(yscrollcommand=diff_y.set)
    diff_x = ttk.Scrollbar(right, orient="horizontal", command=diff_text.xview)
    diff_x.grid(row=3, column=0, sticky="ew")
    diff_text.configure(xscrollcommand=diff_x.set)
    diff_text.tag_configure("added", foreground="#16733b", background="#eaf6ee")
    diff_text.tag_configure("removed", foreground="#a32626", background="#faeeee")
    diff_text.tag_configure(
        "header", foreground="#555555", font=("TkFixedFont", 9, "bold")
    )

    by_key = {int(item["key"]): item for item in pending}
    choices = {key: item["newer_versions"][-1] for key, item in by_key.items()}
    checked: set[int] = set()

    def show_diff(_event=None):
        selection = tree.selection()
        if not selection:
            return
        key = int(selection[0])
        item = by_key.get(key)
        if item is None:
            return
        versions = item["newer_versions"]
        labels = [
            f"v{version['number']} · {version['created'][:10]}"
            for version in versions
        ]
        by_label = dict(zip(labels, versions))
        version_combo.configure(values=labels)
        chosen = choices.get(key, versions[-1])
        version_variable.set(next(
            (label for label, version in by_label.items()
             if int(version["id"]) == int(chosen["id"])),
            labels[-1],
        ))

        def draw():
            selected = by_label.get(version_variable.get(), versions[-1])
            choices[key] = selected
            diff_text.configure(state="normal")
            diff_text.delete("1.0", "end")
            lines = version_diff_lines(item["markdown"], selected["markdown"])
            for line in lines or ["No wording changes."]:
                if line.startswith("+") and not line.startswith("+++"):
                    tag = "added"
                elif line.startswith("-") and not line.startswith("---"):
                    tag = "removed"
                elif line.startswith(("---", "+++", "@@")):
                    tag = "header"
                else:
                    tag = ""
                diff_text.insert("end", line + "\n", (tag,) if tag else ())
            diff_text.configure(state="disabled")

        draw()
        version_combo.bind("<<ComboboxSelected>>", draw)

    def toggle_update(event):
        if (tree.identify_region(event.x, event.y) != "cell"
                or tree.identify_column(event.x) != "#1"):
            return
        row = tree.identify_row(event.y)
        if not row:
            return
        key = int(row)
        if key in checked:
            checked.remove(key)
        else:
            checked.add(key)
        tree.set(key, "update", "☑" if key in checked else "☐")

    for item in pending:
        key = int(item["key"])
        tree.insert(
            "", "end", iid=str(key),
            values=(
                "☐", item["component_name"],
                f"v{item['component_version_number']}",
                f"v{item['newer_versions'][-1]['number']}",
            ),
        )
    tree.bind("<<TreeviewSelect>>", show_diff)
    tree.bind("<Button-1>", toggle_update)
    tree.selection_set(str(pending[0]["key"]))
    show_diff()

    def save_selected():
        if not checked:
            messagebox.showinfo(
                "No updates selected",
                "Tick at least one component whose newer wording you want to use.",
                parent=dialog,
            )
            return
        try:
            revised = update_component_items(
                builder.items, {key: choices[key] for key in checked}
            )
        except (KeyError, TypeError, ValueError) as exc:
            messagebox.showerror("Could not apply updates", str(exc), parent=dialog)
            return
        previous = builder.items
        builder.items = revised
        if not builder.save_assembly():
            builder.items = previous
            builder._render_items()
            return
        dialog.destroy()

    actions = ttk.Frame(dialog, padding=12)
    actions.grid(row=2, column=0, sticky="ew")
    ttk.Label(
        actions,
        text="Saving creates a new revision; earlier revisions remain unchanged.",
        foreground="#555555",
    ).pack(side="left", fill="x", expand=True)
    ttk.Button(actions, text="Cancel", command=dialog.destroy).pack(side="right")
    ttk.Button(
        actions, text="Save selected updates", command=save_selected
    ).pack(side="right", padx=(0, 7))
