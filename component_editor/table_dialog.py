"""Table grid dialog: edit a table without typing Markdown pipes."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .tables import build_markdown_table


class TableEditorDialog:
    """Grid editor that serializes a table without requiring Markdown pipes."""

    def __init__(self, parent, rows, alignments, on_save):
        self.window = tk.Toplevel(parent)
        self.window.title("Edit table")
        self.window.geometry("760x520")
        self.window.minsize(520, 360)
        self.window.lift()
        self.on_save = on_save
        self.alignments = list(alignments or [])
        self.rows = [list(row) for row in rows] or [["", ""], ["", ""]]
        width = max((len(row) for row in self.rows), default=2)
        self.rows = [row + [""] * (width - len(row)) for row in self.rows]
        self.entries = []

        outer = ttk.Frame(self.window, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer,
            text="Enter text in the cells. ContractBuilder will create the table for you.",
            wraplength=700,
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            outer,
            text="The first row is the table's column-heading row.",
        ).pack(anchor="w", pady=(0, 8))
        self.grid_frame = ttk.Frame(outer)
        self.grid_frame.pack(fill="both", expand=True)
        self._draw_grid()

        row_buttons = ttk.Frame(outer)
        row_buttons.pack(fill="x", pady=(8, 0))
        for label, command in (
            ("Add row", self.add_row),
            ("Remove last row", self.remove_row),
            ("Add column", self.add_column),
            ("Remove last column", self.remove_column),
        ):
            ttk.Button(row_buttons, text=label, command=command).pack(side="left", padx=(0, 5))
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(footer, text="Cancel", command=self.window.destroy).pack(side="right")
        ttk.Button(footer, text="Use table", command=self.save).pack(side="right", padx=(0, 8))
        self.window.grab_set()

    def _values(self):
        return [[entry.get() for entry in row] for row in self.entries]

    def _draw_grid(self):
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.entries = []
        width = max((len(row) for row in self.rows), default=1)
        for column in range(width):
            ttk.Label(self.grid_frame, text=f"Column {column + 1}").grid(
                row=0, column=column, sticky="w", padx=3, pady=(0, 4)
            )
            self.grid_frame.columnconfigure(column, weight=1, minsize=90)
        for row_index, row in enumerate(self.rows, 1):
            entries = []
            for column_index in range(width):
                value = row[column_index] if column_index < len(row) else ""
                entry = ttk.Entry(self.grid_frame, width=18)
                entry.insert(0, value)
                entry.grid(row=row_index, column=column_index, sticky="ew", padx=3, pady=3)
                entries.append(entry)
            self.entries.append(entries)

    def _capture(self):
        self.rows = self._values()

    def add_row(self):
        self._capture()
        self.rows.append([""] * max(1, len(self.rows[0]) if self.rows else 1))
        self._draw_grid()

    def remove_row(self):
        self._capture()
        if len(self.rows) > 1:
            self.rows.pop()
            self._draw_grid()

    def add_column(self):
        self._capture()
        for row in self.rows:
            row.append("")
        self.alignments.append(None)
        self._draw_grid()

    def remove_column(self):
        self._capture()
        if self.rows and len(self.rows[0]) > 1:
            for row in self.rows:
                row.pop()
            if self.alignments:
                self.alignments.pop()
            self._draw_grid()

    def save(self):
        try:
            markdown = build_markdown_table(
                self._values(),
                alignments=self.alignments,
            )
        except ValueError as exc:
            messagebox.showerror("Could not create table", str(exc), parent=self.window)
            return
        self.on_save(markdown)
        self.window.destroy()
