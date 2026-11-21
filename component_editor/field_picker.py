"""Searchable field picker and plain-language field creator."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .fields import _FIELD_FORMATS, make_field_placeholder


FIELD_KINDS = (
    ("Text", "A name, an address.", ""),
    ("Long text", "Several lines of text.", "long"),
    ("Date", "A date, such as October 5, 2026.", "date"),
    ("Amount of money", "A fee, such as $1,250.00.", "money"),
    ("Number", "A quantity, such as 30.", "number"),
    ("List", "One item per line, such as book titles.", "list"),
    ("Choice", "A drop-down of allowed values.", "choice"),
    ("Optional clause", "Include a phrase or paragraph only when ticked.", "optional"),
    ("Conditional wording", "Use different wording for each choice.", "conditional"),
    ("Singular or plural word", "Choose one wording for one item and another for several.", "plural"),
)
_KIND_BY_LABEL = {label: (example, kind) for label, example, kind in FIELD_KINDS}
_FORMAT_LABELS = {
    "": "Text",
    "long": "Long text",
    "date": "Date",
    "money": "Amount of money",
    "number": "Number",
    "list": "List",
    "choice": "Choice",
    "plural": "Singular or plural word",
}


def field_kind_definition(
    kind: str,
    name: str,
    description: str = "",
    values=(),
    singular: str = "",
    plural: str = "",
) -> dict:
    """Translate the creator's plain-language kind into a stored field definition."""
    if not str(name or "").strip():
        raise ValueError("Enter a field name.")
    labels = {label.casefold(): (example, value) for label, example, value in FIELD_KINDS}
    selected = labels.get(str(kind).strip().casefold())
    if selected is None:
        raise ValueError("Choose a field kind.")
    _example, field_kind = selected
    options = []
    allowed = []
    if field_kind == "choice":
        allowed = [str(value).strip() for value in values if str(value).strip()]
        if not allowed:
            raise ValueError("Enter at least one choice, one per line.")
        if any("{{" in value or "}}" in value or "|" in value for value in allowed):
            raise ValueError("Choices cannot contain braces or a vertical bar.")
    elif field_kind == "conditional":
        allowed = [str(value).strip() for value in values if str(value).strip()]
        if len(allowed) < 2:
            raise ValueError("Enter at least two choices for conditional wording.")
        if any("{{" in value or "}}" in value or "|" in value or "\n" in value for value in allowed):
            raise ValueError("Each choice must be a single line without braces.")
        field_kind = "choice"
    elif field_kind == "plural":
        singular = str(singular or "").strip()
        plural = str(plural or "").strip()
        if not singular or not plural:
            raise ValueError("Enter both the singular and plural wording.")
        options = [singular, plural]
    elif field_kind not in {"optional"} and values:
        raise ValueError("This field kind does not use a list of choices.")
    return {
        "name": name,
        "description": description,
        "group": "Your fields",
        "default_format": field_kind if field_kind not in {"optional"} else "",
        "default_options": options,
        "allowed_values": allowed,
        "publisher_profile_column": None,
        "publisher_detail_name": None,
    }


def field_definition_placeholder(definition: dict) -> str:
    """Build a stored field using its saved default format and options."""
    name = str(definition["name"])
    fmt = str(definition.get("default_format") or "")
    return field_definition_placeholder(definition)


def build_created_field(
    definition: dict, kind: str, wording: str = "", placement: str = "Inside a sentence"
) -> str:
    """Build the exact placeholder or conditional block produced by the creator."""
    name = str(definition["name"])
    field_kind = str(kind).strip().casefold()
    if field_kind == "optional clause":
        clause = str(wording or "").strip()
        if not clause:
            raise ValueError("Enter the wording to include when this option is ticked.")
        if "\n" in clause:
            return "{{#if " + name + "}}\n\n" + clause + "\n\n{{/if}}"
        return "{{#if " + name + "}}" + clause + "{{/if}}"
    if field_kind == "conditional wording":
        lines = [line for line in str(wording or "").splitlines() if line.strip()]
        mapping = {}
        for line in lines:
            if "|" not in line:
                raise ValueError("Enter one line per choice as: Choice | wording.")
            value, text = line.split("|", 1)
            mapping[value.strip().casefold()] = text.strip()
        values = definition.get("allowed_values") or []
        missing = [value for value in values if not mapping.get(str(value).casefold())]
        if missing:
            raise ValueError("Add wording for: " + ", ".join(missing))
        blocks = []
        for value in values:
            blocks.append(
                "{{#if " + name + " = " + str(value) + "}}"
                + mapping[str(value).casefold()]
                + "{{/if}}"
            )
        separator = " " if placement == "Inside a sentence" else "\n\n"
        return separator.join(blocks)
    options = definition.get("default_options") or definition.get("allowed_values") or []
    separator = " / " if any("," in str(value) for value in options) else ", "
    return make_field_placeholder(name, fmt, separator.join(str(value) for value in options))


class FieldPickerDialog:
    """Search and insert publisher, library and user-defined fields."""

    def __init__(self, parent, library, on_insert):
        self.library = library
        self.on_insert = on_insert
        self.window = tk.Toplevel(parent)
        self.window.title("Insert a field")
        self.window.geometry("760x540")
        self.window.minsize(590, 400)
        self.window.grab_set()
        self.window.lift()

        outer = ttk.Frame(self.window, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Find a field").pack(anchor="w")
        self.search = tk.StringVar(master=self.window)
        entry = ttk.Entry(outer, textvariable=self.search)
        entry.pack(fill="x", pady=(3, 8))
        entry.bind("<KeyRelease>", lambda _event: self.refresh())
        one_off = ttk.Frame(outer)
        one_off.pack(fill="x", pady=(0, 8))
        self.one_off_name = tk.StringVar(master=self.window)
        ttk.Label(one_off, text="Or type a one-off field").pack(side="left")
        ttk.Entry(one_off, textvariable=self.one_off_name, width=28).pack(side="left", padx=6)
        self.one_off_format = tk.StringVar(master=self.window, value="Plain text")
        self.one_off_format_values = {label: value for label, value in _FIELD_FORMATS}
        ttk.Combobox(
            one_off, textvariable=self.one_off_format, state="readonly", width=18,
            values=list(self.one_off_format_values),
        ).pack(side="left")
        ttk.Label(one_off, text="Options").pack(side="left", padx=(6, 2))
        self.one_off_options = tk.StringVar(master=self.window)
        ttk.Entry(one_off, textvariable=self.one_off_options, width=22).pack(side="left")
        ttk.Button(one_off, text="Insert one-off", command=self.insert_one_off).pack(side="left", padx=6)
        self.one_off_status = ttk.Label(outer, text="", foreground="#8a5a00")
        self.one_off_status.pack(anchor="w")
        self.tree = ttk.Treeview(
            outer, columns=("kind", "description"), show="tree headings",
            selectmode="browse",
        )
        self.tree.heading("#0", text="Field")
        self.tree.heading("kind", text="Kind")
        self.tree.heading("description", text="Description / choices")
        self.tree.column("#0", width=210, anchor="w")
        self.tree.column("kind", width=145, anchor="w")
        self.tree.column("description", width=310, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _event: self.insert_selected())
        self.tree.bind("<<TreeviewSelect>>", self._show_details)
        self.details = ttk.Label(outer, text="", wraplength=700)
        self.details.pack(fill="x", pady=(6, 0))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(10, 0))
        self.keep_open = tk.BooleanVar(master=self.window, value=False)
        ttk.Checkbutton(
            controls, text="Keep this window open after inserting",
            variable=self.keep_open,
        ).pack(side="left")
        ttk.Button(controls, text="New field…", command=self.new_field).pack(side="right")
        ttk.Button(controls, text="Edit…", command=self.edit_field).pack(side="right", padx=5)
        ttk.Button(controls, text="Archive", command=self.archive_field).pack(side="right")
        ttk.Button(controls, text="Insert", command=self.insert_selected).pack(side="right", padx=5)
        ttk.Button(controls, text="Close", command=self.window.destroy).pack(side="right")
        self._field_by_iid = {}
        self.refresh()
        entry.focus_set()

    def refresh(self, selected_key=None):
        query = self.search.get().strip().casefold()
        self.tree.delete(*self.tree.get_children())
        self._field_by_iid.clear()
        groups = {}
        try:
            fields = self.library.list_picker_fields()
        except (OSError, ValueError):
            fields = []
        for field in fields:
            haystack = " ".join((
                str(field.get("name", "")), str(field.get("description", "")),
                " ".join(str(x) for x in field.get("allowed_values", [])),
            )).casefold()
            if query and query not in haystack:
                continue
            group = str(field.get("group") or "Fields from your library")
            if group not in groups:
                groups[group] = self.tree.insert("", "end", text=group, open=True, values=("", ""))
            parent = groups[group]
            iid = self.tree.insert(
                parent, "end",
                text=field.get("name", ""),
                values=(
                    _FORMAT_LABELS.get(field.get("default_format", ""), "Text"),
                    ", ".join(field.get("allowed_values") or field.get("default_options") or [])
                    or field.get("description", ""),
                ),
            )
            self._field_by_iid[iid] = field
            if selected_key and str(field.get("name_key", "")).casefold() == selected_key.casefold():
                self.tree.selection_set(iid)
                self.tree.focus(iid)
        for group in groups.values():
            self.tree.item(group, open=True)

    def insert_one_off(self):
        try:
            value = make_field_placeholder(
                self.one_off_name.get(),
                self.one_off_format_values.get(self.one_off_format.get(), ""),
                self.one_off_options.get(),
            )
        except ValueError as exc:
            self.one_off_status.configure(text=str(exc))
            return
        self.on_insert(value)
        if self.keep_open.get():
            self.one_off_name.set("")
            self.one_off_options.set("")
            self.window.lift()
            self.window.focus_force()
        else:
            self.window.destroy()

    def _selected_field(self):
        selected = self.tree.selection()
        return self._field_by_iid.get(selected[0]) if selected else None

    def _show_details(self, _event=None):
        field = self._selected_field()
        if not field:
            self.details.configure(text="")
            return
        choices = field.get("allowed_values") or []
        description = str(field.get("description") or "")
        if choices:
            description = (description + " · " if description else "") + "Choices: " + ", ".join(choices)
        self.details.configure(text=description)

    def insert_selected(self):
        field = self._selected_field()
        if field is None:
            return
        try:
            value = field_definition_placeholder(field)
        except ValueError as exc:
            messagebox.showerror("Cannot insert this field", str(exc), parent=self.window)
            return
        self.on_insert(value)
        if self.keep_open.get():
            self.window.lift()
            self.window.focus_force()
        else:
            self.window.destroy()

    def new_field(self):
        FieldCreatorDialog(self.window, self.library, self._created)

    def _created(self, definition, insertion):
        self.refresh(definition.get("name_key"))
        if insertion:
            self.on_insert(insertion)
            if self.keep_open.get():
                self.window.lift()
                self.window.focus_force()
            else:
                self.window.destroy()

    def edit_field(self):
        field = self._selected_field()
        if not field or field.get("source") != "field_definition":
            self.details.configure(text="Only fields under Your fields can be edited.")
            return
        definition = self.library.get_field_definition(field["id"])
        FieldCreatorDialog(self.window, self.library, self._updated, existing=definition)

    def _updated(self, definition, _insertion):
        self.refresh(definition.get("name_key"))
        self.details.configure(text="Field definition updated.")

    def archive_field(self):
        field = self._selected_field()
        if not field or field.get("source") != "field_definition":
            self.details.configure(text="Only fields under Your fields can be archived.")
            return
        if not messagebox.askyesno(
            "Archive field",
            f"Archive '{field['name']}'? Existing contract wording will not be changed.",
            parent=self.window,
        ):
            return
        self.library.archive_field_definition(field["id"])
        self.refresh()
        self.details.configure(text="Field archived. Existing uses remain intact.")


class FieldCreatorDialog:
    """Create or edit a reusable field using ordinary descriptions, not syntax."""

    def __init__(self, parent, library, on_saved, existing=None):
        self.library = library
        self.on_saved = on_saved
        self.existing = existing
        self.window = tk.Toplevel(parent)
        self.window.title("Edit field" if existing else "New field")
        self.window.geometry("700x650")
        self.window.minsize(570, 480)
        self.window.grab_set()
        self.window.lift()
        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)

        ttk.Label(outer, text="What kind of field is this?").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.kind = tk.StringVar(master=self.window, value="Text")
        self.kind_box = ttk.Combobox(
            outer, textvariable=self.kind, state="readonly",
            values=[label for label, _example, _format in FIELD_KINDS],
        )
        self.kind_box.grid(row=0, column=1, sticky="ew", pady=4)
        self.example = ttk.Label(outer, text="", wraplength=620)
        self.example.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(outer, text="Field name").grid(row=2, column=0, sticky="w", pady=4)
        self.name = tk.StringVar(master=self.window, value=(existing or {}).get("name", ""))
        ttk.Entry(outer, textvariable=self.name).grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(outer, text="Description (optional)").grid(row=3, column=0, sticky="w", pady=4)
        self.description = tk.StringVar(
            master=self.window, value=(existing or {}).get("description", "")
        )
        ttk.Entry(outer, textvariable=self.description).grid(row=3, column=1, sticky="ew", pady=4)

        self.options_frame = ttk.LabelFrame(outer, text="Options", padding=8)
        self.options_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=8)
        self.options_frame.columnconfigure(1, weight=1)
        ttk.Label(self.options_frame, text="Allowed values (one per line)").grid(
            row=0, column=0, sticky="nw"
        )
        self.values_text = tk.Text(self.options_frame, height=5, width=45, wrap="word")
        self.values_text.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(self.options_frame, text="Singular wording").grid(row=1, column=0, sticky="w")
        self.singular = tk.StringVar(master=self.window)
        ttk.Entry(self.options_frame, textvariable=self.singular).grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=3
        )
        ttk.Label(self.options_frame, text="Plural wording").grid(row=2, column=0, sticky="w")
        self.plural = tk.StringVar(master=self.window)
        ttk.Entry(self.options_frame, textvariable=self.plural).grid(
            row=2, column=1, sticky="ew", padx=(8, 0), pady=3
        )
        self.wording_label = ttk.Label(self.options_frame, text="Wording to include")
        self.wording_label.grid(row=3, column=0, sticky="nw")
        self.wording_text = tk.Text(self.options_frame, height=5, width=45, wrap="word")
        self.wording_text.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=3)
        self.wording_text.bind("<KeyRelease>", self._update_conditional_preview)
        self.values_text.bind("<KeyRelease>", self._update_conditional_preview)
        self.preview = ttk.Label(self.options_frame, text="", wraplength=600)
        self.preview.grid(row=4, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self.placement_label = ttk.Label(self.options_frame, text="Where does the wording go?")
        self.placement_label.grid(row=5, column=0, sticky="w", pady=(5, 0))
        self.placement = tk.StringVar(master=self.window, value="Inside a sentence")
        self.placement_box = ttk.Combobox(
            self.options_frame, textvariable=self.placement, state="readonly",
            values=["Inside a sentence", "As separate paragraphs"], width=28,
        )
        self.placement_box.grid(row=5, column=1, sticky="w", pady=(5, 0))
        self.placement_box.bind("<<ComboboxSelected>>", self._update_conditional_preview)

        footer = ttk.Frame(outer)
        footer.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(footer, text="Cancel", command=self.window.destroy).pack(side="right")
        ttk.Button(footer, text="Save field", command=self.save).pack(side="right", padx=6)

        self.kind_box.bind("<<ComboboxSelected>>", lambda _event: self._update_kind())
        if existing:
            self._load_existing(existing)
        self._update_kind()
        self.name_entry = None

    def _load_existing(self, definition):
        fmt = definition.get("default_format") or ""
        kind = next((label for label, _example, value in FIELD_KINDS if value == fmt), "Text")
        if fmt == "choice":
            kind = "Choice"
        if fmt == "plural":
            kind = "Singular or plural word"
        self.kind.set(kind)
        self.values_text.insert("1.0", "\n".join(definition.get("allowed_values") or []))
        options = definition.get("default_options") or []
        if len(options) == 2:
            self.singular.set(options[0])
            self.plural.set(options[1])

    def _update_kind(self):
        kind = self.kind.get()
        example = next((example for label, example, _fmt in FIELD_KINDS if label == kind), "")
        self.example.configure(text=example)
        for widget in self.options_frame.winfo_children():
            widget.grid_remove()
        if kind in {"Choice", "Conditional wording"}:
            for widget in self.options_frame.winfo_children()[:2]:
                widget.grid()
            if kind == "Conditional wording":
                self.wording_label.configure(
                    text="Wording for each choice (one per line: Choice | wording)"
                )
                for widget in self.options_frame.winfo_children()[6:]:
                    widget.grid()
                self.preview.grid()
                self.placement_label.grid()
                self.placement_box.grid()
        elif kind == "Singular or plural word":
            for widget in self.options_frame.winfo_children()[2:6]:
                widget.grid()
            self.preview.grid_remove()
        elif kind == "Optional clause":
            self.wording_label.configure(text="Wording to include")
            for widget in self.options_frame.winfo_children()[6:8]:
                widget.grid()
            self.preview.grid_remove()
            self.placement_label.grid_remove()
            self.placement_box.grid_remove()
        else:
            self.preview.grid_remove()
            self.placement_label.grid_remove()
            self.placement_box.grid_remove()
        self._update_conditional_preview()

    def _update_conditional_preview(self, _event=None):
        if self.kind.get() != "Conditional wording":
            return
        values = [line.strip() for line in self.values_text.get("1.0", "end").splitlines() if line.strip()]
        entries = []
        for line in self.wording_text.get("1.0", "end-1c").splitlines():
            if "|" in line:
                choice, phrase = line.split("|", 1)
                if choice.strip() and phrase.strip():
                    entries.append(choice.strip() + " → " + phrase.strip())
        if entries:
            separator = " " if self.placement.get() == "Inside a sentence" else "\n\n"
            preview_text = ("Sentence: " if separator == " " else "Paragraphs: ")
            self.preview.configure(text=preview_text + separator.join(entries))
        else:
            self.preview.configure(
                text="Enter one line for each choice as “Choice | wording”. "
                + ("Choices: " + ", ".join(values) if values else "")
            )

    def save(self):
        kind = self.kind.get()
        values = [line.strip() for line in self.values_text.get("1.0", "end").splitlines() if line.strip()]
        try:
            definition = field_kind_definition(
                kind, self.name.get(), self.description.get(), values,
                self.singular.get(), self.plural.get(),
            )
            if self.existing:
                definition_id = self.library.edit_field_definition(
                    self.existing["id"], **definition
                )["id"]
            else:
                definition_id = self.library.add_field_definition(**definition)
            saved = self.library.get_field_definition(definition_id)
            wording = self.wording_text.get("1.0", "end-1c").strip()
            insertion = build_created_field(
                saved, kind, wording, placement=self.placement.get()
            )
        except (ValueError, TypeError, OSError) as exc:
            messagebox.showerror("Could not save field", str(exc), parent=self.window)
            return
        self.on_saved(saved, insertion)
        self.window.destroy()
