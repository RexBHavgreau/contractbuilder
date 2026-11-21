"""The "Build contract from" row at the top of the main window (T-048-A).

Three clear ways to start: an existing contract assembly, a new one, or a Word
file. The assembly builder is loaded only when one of the first two is chosen,
so the Word-template workflow does not import it at start-up.
"""
from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

CHOICES = (
    ("Existing contract assembly", "Pick a saved assembly and fill it in.", "open_existing_assembly", "E"),
    ("New contract assembly", "Choose components and build a new one.", "open_new_assembly", "N"),
    ("Word file", "Fill in a .docx or .dotx file that has {{fields}}.", "choose_template", "W"),
)


def build_start_row(parent, app):
    """Put the three choices in `parent`; return the label that names the Word file."""
    box = ttk.LabelFrame(parent, text="Build contract from:", padding=8)
    box.pack(fill="x", pady=(0, 10))
    row = ttk.Frame(box)
    row.pack(fill="x")
    app.start_buttons = []
    for column, (label, caption, method, key) in enumerate(CHOICES):
        row.columnconfigure(column, weight=1, uniform="start")
        cell = ttk.Frame(row)
        cell.grid(row=0, column=column, sticky="nsew", padx=4)
        button = ttk.Button(
            cell, text=label, underline=label.index(key), command=getattr(app, method)
        )
        button.pack(fill="x")
        ttk.Label(cell, text=caption, foreground="#555555", wraplength=170, justify="left").pack(
            anchor="w", pady=(3, 0)
        )
        app.start_buttons.append(button)
        app.root.bind(f"<Alt-{key.lower()}>", lambda _e, b=button: b.invoke())
    name_row = ttk.Frame(box)
    name_row.pack(fill="x", pady=(8, 0))
    ttk.Label(name_row, text="Word file:").pack(side="left")
    name = ttk.Label(name_row, text="None chosen", foreground="#666666")
    name.pack(side="left", padx=(8, 0), fill="x", expand=True)
    return name


class StartScreenMixin:
    """Opens the assembly builder from the main window's start row."""

    assembly_builder_window = None

    def open_new_assembly(self):
        self._open_assembly_builder(open_saved=False)

    def open_existing_assembly(self):
        try:
            import assembly_open_dialog

            assembly_open_dialog.open_saved_assembly_direct(self)
        except (ImportError, OSError, sqlite3.Error, tk.TclError, ValueError) as exc:
            messagebox.showerror(
                "Contract assemblies unavailable",
                f"Could not open the saved contract assemblies.\\n\\n{exc}",
                parent=self.root,
            )

    def open_assembly_revision(self, revision, review_updates=False):
        """Open the builder for a pinned revision, optionally showing its updates."""
        existing = self.assembly_builder_window
        if existing is not None:
            try:
                if existing.window.winfo_exists():
                    if not existing._confirm_replace():
                        return
                    existing._load_revision(revision)
                    existing.window.deiconify()
                    existing.window.lift()
                    existing.window.focus_set()
                    if review_updates:
                        existing.review_updates()
                    return
            except tk.TclError:
                pass
            self.assembly_builder_window = None
        try:
            from assembly_builder import AssemblyBuilderWindow

            builder = AssemblyBuilderWindow(
                self.root, on_generate=self.create_assembly_document
            )
            self.assembly_builder_window = builder
            builder._load_revision(revision)
            if review_updates:
                builder.review_updates()
        except (ImportError, OSError, sqlite3.Error, tk.TclError, ValueError) as exc:
            self.assembly_builder_window = None
            messagebox.showerror(
                "Could not open this assembly",
                f"The assembly could not be opened in the builder.\\n\\n{exc}",
                parent=self.root,
            )

    def _open_assembly_builder(self, open_saved):
        existing = self.assembly_builder_window
        if existing is not None:
            try:
                if existing.window.winfo_exists():
                    existing.window.lift()
                    existing.window.focus_set()
                    if open_saved:
                        existing.open_saved_assembly()
                    return
            except tk.TclError:
                pass
            self.assembly_builder_window = None
        try:
            from assembly_builder import AssemblyBuilderWindow

            self.assembly_builder_window = AssemblyBuilderWindow(
                self.root, on_generate=self.create_assembly_document
            )
        except (ImportError, OSError, sqlite3.Error, tk.TclError, ValueError) as exc:
            self.assembly_builder_window = None
            messagebox.showerror(
                "Contract assembly unavailable",
                f"Could not open the contract assemblies.\n\n{exc}",
                parent=self.root,
            )
            return
        if open_saved:
            self.assembly_builder_window.open_saved_assembly()
