"""Guided insertion of singular/plural wording tied to a List field."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .fields import make_field_placeholder


def build_singular_plural_placeholder(field_name: str, singular: str, plural: str) -> str:
    """Build a plural formatter that counts the lines in an existing List field."""
    name = str(field_name or "").strip()
    one = str(singular or "").strip()
    many = str(plural or "").strip()
    if not name:
        raise ValueError("Choose a List field.")
    if not one or not many:
        raise ValueError("Enter both the singular and plural wording.")
    if any(character in name for character in "{}|\n"):
        raise ValueError("Choose a valid List field name.")
    if any(character in wording for wording in (one, many) for character in "{}|\n"):
        raise ValueError("Each wording must be a single line without braces or a vertical bar.")
    separator = " / " if "," in one or "," in many else ", "
    return make_field_placeholder(name, "plural", one + separator + many)


class SingularPluralDialog:
    """Choose a saved List field and insert wording that follows its item count."""

    def __init__(self, parent, library, on_insert):
        self.library = library
        self.on_insert = on_insert
        self.window = tk.Toplevel(parent)
        self.window.title("Singular/plural word")
        self.window.geometry("660x390")
        self.window.minsize(540, 340)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.lift()

        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)

        ttk.Label(
            outer,
            text="Make a word follow the number of items in a List field.",
            wraplength=610,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(outer, text="List field").grid(row=1, column=0, sticky="w", pady=5)
        self.list_fields = self._list_fields()
        self.fields_by_name = {str(field["name"]): field for field in self.list_fields}
        self.field = tk.StringVar(
            master=self.window,
            value=str(self.list_fields[0]["name"]) if self.list_fields else "",
        )
        self.field_box = ttk.Combobox(
            outer, textvariable=self.field, state="readonly",
            values=list(self.fields_by_name),
        )
        self.field_box.grid(row=1, column=1, sticky="ew", pady=5)

        self.help = ttk.Label(
            outer,
            text=(
                "The count comes from the number of nonblank lines entered for this field. "
                "In the completed contract form, enter one item per line."
            ),
            foreground="#555555", wraplength=610, justify="left",
        )
        self.help.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(outer, text="Word for one item").grid(
            row=3, column=0, sticky="w", pady=4
        )
        self.singular = tk.StringVar(master=self.window)
        self.singular_entry = ttk.Entry(outer, textvariable=self.singular)
        self.singular_entry.grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(outer, text="Word for more than one").grid(
            row=4, column=0, sticky="w", pady=4
        )
        self.plural = tk.StringVar(master=self.window)
        self.plural_entry = ttk.Entry(outer, textvariable=self.plural)
        self.plural_entry.grid(row=4, column=1, sticky="ew", pady=4)

        preview_frame = ttk.LabelFrame(outer, text="Preview", padding=8)
        preview_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 8))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.columnconfigure(1, weight=1)
        one_frame = ttk.LabelFrame(preview_frame, text="One item", padding=8)
        many_frame = ttk.LabelFrame(preview_frame, text="More than one", padding=8)
        one_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        many_frame.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self.one_preview = tk.StringVar(master=self.window, value="—")
        self.many_preview = tk.StringVar(master=self.window, value="—")
        ttk.Label(one_frame, textvariable=self.one_preview).pack(anchor="center")
        ttk.Label(many_frame, textvariable=self.many_preview).pack(anchor="center")

        self.status = ttk.Label(outer, text="", foreground="#8a5a00", wraplength=610)
        self.status.grid(row=6, column=0, columnspan=2, sticky="w")
        footer = ttk.Frame(outer)
        footer.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(footer, text="Cancel", command=self.window.destroy).pack(side="right")
        self.insert_button = ttk.Button(
            footer, text="Insert wording", command=self.insert
        )
        self.insert_button.pack(side="right", padx=(0, 7))

        self.singular.trace_add("write", self._refresh_preview)
        self.plural.trace_add("write", self._refresh_preview)
        self.field_box.bind("<<ComboboxSelected>>", self._refresh_preview)
        if not self.list_fields:
            self.status.configure(
                text="No List fields found. Create a field with the List kind first."
            )
            self.insert_button.configure(state="disabled")
            self.field_box.configure(state="disabled")
            self.singular_entry.configure(state="disabled")
            self.plural_entry.configure(state="disabled")
        else:
            self.singular_entry.focus_set()
        self._refresh_preview()

    def _list_fields(self):
        try:
            return [
                field for field in self.library.list_picker_fields()
                if str(field.get("default_format") or "").casefold() == "list"
            ]
        except (AttributeError, OSError, ValueError):
            return []

    def _refresh_preview(self, *_args):
        self.one_preview.set(self.singular.get().strip() or "—")
        self.many_preview.set(self.plural.get().strip() or "—")

    def insert(self):
        try:
            value = build_singular_plural_placeholder(
                self.field.get(), self.singular.get(), self.plural.get()
            )
        except ValueError as exc:
            self.status.configure(text=str(exc))
            return
        self.on_insert(value)
        self.window.destroy()
