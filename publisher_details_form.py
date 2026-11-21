"""The extra-details section of the publisher profile window (T-046-C).

Each detail the user has defined gets a drop-down (when it has allowed values,
so the stored value can never differ from what the wording tests for) or a
plain box. "Add a detail…" defines a new one.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from publisher_detail_dialog import PublisherDetailDialog


class DetailsForm:
    """Edit one publisher's extra details."""

    def __init__(self, parent_window, container, store, on_changed=None):
        self.parent_window = parent_window
        self.store = store
        self.on_changed = on_changed
        self.frame = ttk.LabelFrame(container, text="More about this publisher", padding=10)
        self.frame.columnconfigure(1, weight=1)
        self.variables: dict[str, tk.StringVar] = {}
        self.rebuild({})

    def rebuild(self, values):
        for child in self.frame.winfo_children():
            child.destroy()
        self.variables = {}
        try:
            definitions = self.store.list_detail_definitions()
        except Exception:  # an older database without details: show nothing to edit
            definitions = []
        row = 0
        for definition in definitions:
            ttk.Label(self.frame, text=definition["name"]).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=4
            )
            variable = tk.StringVar(master=self.parent_window)
            variable.set(str(values.get(definition["name"], "")))
            if definition["allowed_values"]:
                widget = ttk.Combobox(
                    self.frame, textvariable=variable, state="readonly",
                    values=[""] + list(definition["allowed_values"]),
                )
            else:
                widget = ttk.Entry(self.frame, textvariable=variable)
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            self.variables[definition["name"]] = variable
            row += 1
        if not definitions:
            ttk.Label(
                self.frame,
                text=(
                    "No extra details yet. Add one, such as Publisher type, to choose "
                    "wording by publisher automatically."
                ),
                foreground="#555555", wraplength=420, justify="left",
            ).grid(row=row, column=0, columnspan=2, sticky="w")
            row += 1
        ttk.Button(self.frame, text="Add a detail…", command=self._add).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

    def _add(self):
        current = self.values()
        PublisherDetailDialog(
            self.parent_window, self.store, lambda: self._added(current)
        )

    def _added(self, current):
        self.rebuild(current)
        if self.on_changed is not None:
            self.on_changed()

    def values(self) -> dict[str, str]:
        return {name: variable.get().strip() for name, variable in self.variables.items()}

    def set(self, values):
        for name, variable in self.variables.items():
            variable.set(str(values.get(name, "")))
