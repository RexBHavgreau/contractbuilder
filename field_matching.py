"""Window for linking template field names to saved publisher details."""
from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from publisher_profiles import PROFILE_FIELDS

PROFILE_COLUMNS = (*PROFILE_FIELDS, "formatted_address")
PROFILE_LABELS = {
    "publisher_name": "Publisher name",
    "contact_name": "Contact name",
    "contact_title": "Contact title",
    "contact_email": "Contact email",
    "contact_phone": "Contact phone",
    "website": "Website",
    "address_line1": "Address line 1",
    "address_line2": "Address line 2",
    "city": "City",
    "region": "State / province / region",
    "postal_code": "Postal code",
    "country": "Country",
    "notes": "Publisher notes",
    "formatted_address": "Combined mailing address",
}


class FieldMatchingDialog:
    """Manage user-defined names that fill from saved publisher profiles."""

    def __init__(self, parent, store):
        self.store = store
        self.window = tk.Toplevel(parent)
        self.window.title("Field Matching")
        self.window.geometry("720x500")
        self.window.minsize(560, 380)
        self.window.transient(parent)

        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer,
            text="Match your contract's field names to saved publisher details.",
            wraplength=660,
        ).pack(anchor="w", pady=(0, 10))

        self.tree = ttk.Treeview(
            outer, columns=("field", "detail"), show="headings", selectmode="browse"
        )
        self.tree.heading("field", text="Field name in contract")
        self.tree.heading("detail", text="Saved publisher detail")
        self.tree.column("field", width=280, anchor="w")
        self.tree.column("detail", width=260, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._select)

        form = ttk.LabelFrame(outer, text="Add or change a match", padding=10)
        form.pack(fill="x", pady=(10, 0))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Contract field name").grid(row=0, column=0, sticky="w")
        self.name = tk.StringVar(master=self.window)
        ttk.Entry(form, textvariable=self.name).grid(
            row=0, column=1, sticky="ew", padx=(10, 0), pady=3
        )
        ttk.Label(form, text="Fill it from").grid(row=1, column=0, sticky="w")
        self.column = tk.StringVar(master=self.window)
        self.choice = ttk.Combobox(
            form, textvariable=self.column, state="readonly",
            values=[PROFILE_LABELS[item] for item in PROFILE_COLUMNS],
        )
        self.choice.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=3)
        self._column_by_label = {label: key for key, label in PROFILE_LABELS.items()}

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(10, 0))
        self.status = ttk.Label(footer, text="")
        self.status.pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Remove match", command=self.remove).pack(side="left")
        ttk.Button(footer, text="Save match", command=self.save).pack(side="left", padx=6)
        ttk.Button(footer, text="Close", command=self.window.destroy).pack(side="right")
        self.refresh()

    def refresh(self, selected=None):
        self.tree.delete(*self.tree.get_children())
        for item in self.store.list_field_matches():
            iid = str(item["id"])
            self.tree.insert(
                "", "end", iid=iid,
                values=(item["field_name"], PROFILE_LABELS[item["profile_column"]]),
            )
        if selected is not None and self.tree.exists(str(selected)):
            self.tree.selection_set(str(selected))
            self.tree.focus(str(selected))

    def _select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        self.name.set(values[0])
        self.column.set(values[1])

    def save(self):
        label = self.column.get()
        profile_column = self._column_by_label.get(label)
        try:
            if not profile_column:
                raise ValueError("Choose a saved publisher detail.")
            match_id = self.store.save_field_match(self.name.get(), profile_column)
        except (ValueError, OSError, sqlite3.Error) as exc:
            messagebox.showerror("Could not save field match", str(exc), parent=self.window)
            return
        self.status.config(text="Field match saved.")
        self.refresh(match_id)

    def remove(self):
        selected = self.tree.selection()
        if not selected:
            self.status.config(text="Select a match to remove.")
            return
        if self.store.delete_field_match(int(selected[0])):
            self.name.set("")
            self.column.set("")
            self.refresh()
            self.status.config(text="Field match removed.")
