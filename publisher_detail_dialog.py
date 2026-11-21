"""Define an extra publisher detail, such as Publisher type (T-046-C)."""
from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk


class PublisherDetailDialog:
    """Ask for a detail's name and, if it is a choice, its allowed values."""

    def __init__(self, parent, store, on_saved):
        self.store = store
        self.on_saved = on_saved
        self.window = tk.Toplevel(parent)
        self.window.title("Add a publisher detail")
        self.window.transient(parent)
        self.window.resizable(False, False)
        frame = ttk.Frame(self.window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=(
                "A detail is something extra you keep for each publisher, such as "
                "Publisher type. Wording that depends on it can then be chosen "
                "automatically when you pick the publisher."
            ),
            wraplength=420, justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(frame, text="Name").grid(row=1, column=0, sticky="w", pady=4)
        self.name = tk.StringVar(master=self.window)
        entry = ttk.Entry(frame, textvariable=self.name, width=36)
        entry.grid(row=1, column=1, sticky="ew", pady=4)
        entry.focus_set()
        ttk.Label(frame, text="Choices (one per line)").grid(row=2, column=0, sticky="nw", pady=4)
        self.values = tk.Text(frame, width=36, height=5, wrap="word", relief="solid", borderwidth=1)
        self.values.grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(
            frame,
            text=(
                "Example: name it Publisher type, then list Non-profit, Sole proprietor "
                "and Company. Leave the choices empty for a detail you type freely."
            ),
            foreground="#555555", wraplength=420, justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 8))
        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Cancel", command=self.window.destroy).pack(side="right")
        ttk.Button(buttons, text="Add detail", command=self.save).pack(side="right", padx=(0, 8))
        self.window.bind("<Escape>", lambda _e: self.window.destroy())
        self.window.grab_set()

    def save(self):
        choices = [line.strip() for line in self.values.get("1.0", "end-1c").splitlines()]
        try:
            self.store.add_detail_definition(self.name.get(), choices)
        except (ValueError, sqlite3.Error, OSError) as exc:
            messagebox.showerror("Could not add the detail", str(exc), parent=self.window)
            return
        self.window.destroy()
        self.on_saved()
