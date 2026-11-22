"""Choose part of a Word document to import (T-064-C).

Shows the document's blocks in order, each with a tick box and a one-line
preview. Click a tick (or press Space) to tick a block; Shift-click ticks a
range. Warnings for the highlighted block, and anything worth knowing about the
choice, are shown below. Nothing is saved here: "Continue" hands the ticked
blocks to the usual review window, which has its own Save.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import import_selection

TICKED = "☑"
UNTICKED = "☐"


class ImportSelectionDialog:
    """Tick blocks of a Word import and continue to the review window."""

    def __init__(self, parent, imported, on_continue, file_name=""):
        self.imported = imported
        self.blocks = list(imported.blocks)
        self.on_continue = on_continue
        self.ticked: set = set()
        self._anchor = None

        self.window = tk.Toplevel(parent)
        self.window.title("Choose what to import")
        self.window.geometry("900x620")
        self.window.minsize(640, 420)
        self.window.lift()
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)

        ttk.Label(
            self.window, padding=(12, 12, 12, 6), justify="left", wraplength=840,
            text=(
                f"Tick the parts of “{file_name}” you want in a new component. Click a "
                "box (or press Space) to tick it; Shift-click ticks everything between. "
                "Lists and tables are taken whole."
            ),
        ).grid(row=0, column=0, sticky="ew")

        table = ttk.Frame(self.window, padding=(12, 0, 12, 6))
        table.grid(row=1, column=0, sticky="nsew")
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            table, columns=("tick", "kind", "text", "notes"), show="headings", selectmode="browse",
        )
        for column, title, width, stretch in (
            ("tick", "", 44, False), ("kind", "Kind", 100, False),
            ("text", "Starts with", 540, True), ("notes", "Notes", 90, False),
        ):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, anchor="center" if column == "tick" else "w", stretch=stretch)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        for index, block in enumerate(self.blocks):
            count = len(block.warnings)
            self.tree.insert(
                "", "end", iid=str(index),
                values=(
                    UNTICKED, import_selection.block_label(block),
                    import_selection.block_preview(block),
                    f"⚠ {count}" if count else "",
                ),
            )
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<space>", self._space)
        self.tree.bind("<<TreeviewSelect>>", self._show_notes)
        self.tree.bind("<Double-1>", lambda _e: self.continue_to_review() if self.ticked else None)

        self.notes = tk.Text(
            self.window, height=6, wrap="word", state="disabled", relief="solid",
            borderwidth=1, padx=8, pady=4, font="TkDefaultFont",
        )
        self.notes.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))

        controls = ttk.Frame(self.window, padding=(12, 0, 12, 12))
        controls.grid(row=3, column=0, sticky="ew")
        self.count_label = ttk.Label(controls, text="")
        self.count_label.pack(side="left", padx=(0, 12))
        ttk.Button(controls, text="Select all", command=self.select_all).pack(side="left")
        ttk.Button(controls, text="Clear", command=self.clear).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Cancel", command=self.window.destroy).pack(side="right")
        self.continue_button = ttk.Button(
            controls, text="Continue to review…", command=self.continue_to_review, state="disabled"
        )
        self.continue_button.pack(side="right", padx=(0, 7))
        self.window.bind("<Escape>", lambda _e: self.window.destroy())
        self._refresh()
        rows = self.tree.get_children()
        if rows:
            self.tree.selection_set(rows[0])
            self.tree.focus(rows[0])
        self.tree.focus_set()
        self.window.grab_set()

    # -- ticking ---------------------------------------------------------------

    def _set(self, index, value):
        (self.ticked.add if value else self.ticked.discard)(index)
        self.tree.set(str(index), "tick", TICKED if value else UNTICKED)

    def toggle(self, index, extend=False):
        """Tick or untick one block; with ``extend``, a range from the last one touched."""
        if extend and self._anchor is not None:
            low, high = sorted((self._anchor, index))
            target = index not in self.ticked
            for i in range(low, high + 1):
                self._set(i, target)
        else:
            self._set(index, index not in self.ticked)
        self._anchor = index
        self._refresh()

    def _click(self, event):
        if self.tree.identify_region(event.x, event.y) != "cell":
            return None
        row = self.tree.identify_row(event.y)
        if row and self.tree.identify_column(event.x) == "#1":
            self.toggle(int(row), extend=bool(event.state & 0x0001))   # Shift held
            self.tree.selection_set(row)
            return "break"
        return None

    def _space(self, _event=None):
        selected = self.tree.selection()
        if selected:
            self.toggle(int(selected[0]))
        return "break"

    def select_all(self):
        for index in range(len(self.blocks)):
            self._set(index, True)
        self._refresh()

    def clear(self):
        for index in range(len(self.blocks)):
            self._set(index, False)
        self._anchor = None
        self._refresh()

    # -- what to tell the user ---------------------------------------------------

    def _refresh(self):
        total = len(self.blocks)
        self.count_label.configure(text=f"{len(self.ticked)} of {total} ticked")
        self.continue_button.configure(state="normal" if self.ticked else "disabled")
        self._show_notes()

    def _show_notes(self, _event=None):
        lines = []
        selected = self.tree.selection()
        if selected:
            block = self.blocks[int(selected[0])]
            for warning in block.warnings:
                lines.append(f"• {warning.location}: {warning.message}")
        lines.extend("• " + note for note in import_selection.selection_notes(self.blocks, self.ticked))
        if not lines:
            lines = ["Nothing to note for the highlighted part or your choice."]
        self.notes.configure(state="normal")
        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", "\n".join(lines))
        self.notes.configure(state="disabled")

    # -- going on -------------------------------------------------------------------

    def continue_to_review(self):
        if not self.ticked:
            return
        chosen = import_selection.selection_import(self.imported, sorted(self.ticked))
        self.window.destroy()
        self.on_continue(chosen)
