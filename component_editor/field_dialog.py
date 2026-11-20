"""Insert-a-field dialog. The field picker and creator of T-043 land here."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .fields import _FIELD_FORMATS, make_field_placeholder


class FieldInsertDialog:
    """Choose a known field and optional format before inserting its placeholder."""

    def __init__(self, parent, field_names, on_insert):
        self.window = tk.Toplevel(parent)
        self.window.title("Insert a field")
        self.window.transient(parent)
        self.window.resizable(False, False)
        self.on_insert = on_insert
        frame = ttk.Frame(self.window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Field name").grid(row=0, column=0, sticky="w", pady=4)
        self.name_variable = tk.StringVar(master=self.window)
        self.name_entry = ttk.Combobox(
            frame, textvariable=self.name_variable, values=field_names, width=38
        )
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=4)
        self.name_entry.focus_set()

        ttk.Label(frame, text="Format").grid(row=1, column=0, sticky="w", pady=4)
        self.format_variable = tk.StringVar(master=self.window, value="Plain text")
        self.format_values = {label: value for label, value in _FIELD_FORMATS}
        self.format_entry = ttk.Combobox(
            frame,
            textvariable=self.format_variable,
            values=[label for label, _value in _FIELD_FORMATS],
            state="readonly",
            width=38,
        )
        self.format_entry.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Options (for choice or singular/plural)").grid(
            row=2, column=0, sticky="w", pady=4
        )
        self.options_variable = tk.StringVar(master=self.window)
        ttk.Entry(frame, textvariable=self.options_variable, width=40).grid(
            row=2, column=1, sticky="ew", pady=4
        )
        self.status = ttk.Label(frame, text="", foreground="#8a5a00", wraplength=400)
        self.status.grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 8))
        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Cancel", command=self.window.destroy).pack(side="right")
        ttk.Button(buttons, text="Insert field", command=self.insert).pack(
            side="right", padx=(0, 8)
        )
        self.window.grab_set()

    def insert(self):
        label = self.format_variable.get()
        format_name = self.format_values.get(label, "")
        try:
            placeholder = make_field_placeholder(
                self.name_variable.get(), format_name, self.options_variable.get()
            )
        except ValueError as exc:
            self.status.configure(text=str(exc))
            return
        self.on_insert(placeholder)
        self.window.destroy()
