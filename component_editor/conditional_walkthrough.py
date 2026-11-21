"""Four-step authoring wizard for choice-dependent contract wording.

The text builder is deliberately independent of Tkinter so the emitted
condition syntax can be tested before it reaches the editor.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

import core


def build_conditional_text(field_name, values, wording, placement="Inside a sentence"):
    """Build explicit, exhaustive condition blocks and validate them with core.Template."""
    name = str(field_name or "").strip()
    if not name or any(ch in name for ch in "{}|\n"):
        raise ValueError("Enter a valid choice-field name.")
    clean_values = [str(v).strip() for v in values if str(v).strip()]
    if len(clean_values) < 2:
        raise ValueError("A conditional choice needs at least two values.")
    if any(any(ch in value for ch in "{}|\n") for value in clean_values):
        raise ValueError("Choice values must be single lines without braces or a vertical bar.")
    if len({v.casefold() for v in clean_values}) != len(clean_values):
        raise ValueError("Choice values must be unique.")
    mapping = {}
    for key, phrase in dict(wording).items():
        k, p = str(key).strip(), str(phrase).strip()
        if k and p:
            mapping[k.casefold()] = p
    missing = [v for v in clean_values if not mapping.get(v.casefold())]
    if missing:
        raise ValueError("Add wording for: " + ", ".join(missing))
    if any("{{" in mapping[v.casefold()] or "}}" in mapping[v.casefold()] for v in clean_values):
        raise ValueError("Wording cannot contain condition markers.")
    blocks = [
        "{{#if " + name + " = " + value + "}}" + mapping[value.casefold()] + "{{/if}}"
        for value in clean_values
    ]
    if placement == "Inside a sentence":
        result = " ".join(blocks)
    else:
        paragraph_blocks = []
        for value in clean_values:
            paragraph_blocks.append(
                "{{#if " + name + " = " + value + "}}\n"
                + mapping[value.casefold()] + "\n{{/if}}"
            )
        result = "\n\n".join(paragraph_blocks)
    _validate_with_template(result)
    return result


def parse_conditional_text(text):
    """Return (field, values, phrases) for a complete explicit-choice block sequence."""
    source = str(text or "").strip()
    pattern = re.compile(
        r"\{\{#if\s+(.+?)\s*=\s*(.+?)\}\}(.*?)\{\{/if\}\}",
        re.S,
    )
    matches = list(pattern.finditer(source))
    if not matches or re.sub(pattern, "", source).strip():
        raise ValueError("This selection is not a complete choice-wording block. "
                         "It has been left unchanged.")
    field_name = matches[0].group(1).strip()
    if any(match.group(1).strip().casefold() != field_name.casefold() for match in matches):
        raise ValueError("The selected blocks use more than one field and cannot be edited together.")
    values = [match.group(2).strip() for match in matches]
    phrases = [match.group(3).strip() for match in matches]
    if len(values) < 2 or len({value.casefold() for value in values}) != len(values):
        raise ValueError("The selected blocks do not form a complete choice set.")
    return field_name, values, phrases


def build_optional_text(field_name, wording, only_if_blank=False, placement="As separate paragraphs"):
    """Build a yes/no clause or an only-if-blank clause."""
    name = str(field_name or "").strip()
    phrase = str(wording or "").strip()
    if not name or any(ch in name for ch in "{}|\n"):
        raise ValueError("Enter a valid field name.")
    if not phrase:
        raise ValueError("Enter the wording controlled by this field.")
    if "{{#if" in phrase or "{{/if}}" in phrase:
        raise ValueError("Wording cannot contain condition markers.")
    condition = "not " + name if only_if_blank else name
    if placement == "As separate paragraphs" or "\n" in phrase:
        result = "{{#if " + condition + "}}\n\n" + phrase + "\n\n{{/if}}"
    else:
        result = "{{#if " + condition + "}}" + phrase + "{{/if}}"
    _validate_with_template(result)
    return result


def _validate_with_template(text):
    """Parse the generated condition through the same DOCX template checker as the app."""
    try:
        from docx import Document
    except ImportError as exc:
        raise ValueError("Word document validation is unavailable.") from exc
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "condition-check.docx"
        document = Document()
        for paragraph in text.splitlines() or [text]:
            document.add_paragraph(paragraph)
        document.save(path)
        template = core.Template(path)
        if template.problems:
            raise ValueError("The generated wording did not pass template validation: "
                             + "; ".join(template.problems))


class ConditionalWordingDialog:
    """A four-page wizard for creating conditional or optional wording."""

    def __init__(self, parent, library, on_insert, initial_text=""):
        self.library, self.on_insert = library, on_insert
        self.window = tk.Toplevel(parent)
        self.window.title("Choice wording")
        self.window.geometry("760x610")
        self.window.minsize(620, 500)
        self.window.transient(parent)
        self.window.grab_set()
        self.page = 0
        self.kind = tk.StringVar(master=self.window, value="Conditional wording")
        self.field = tk.StringVar(master=self.window, value=str(initial_text or ""))
        self.placement = tk.StringVar(master=self.window, value="Inside a sentence")
        self.only_blank = tk.BooleanVar(master=self.window, value=False)
        self.values = []
        self.phrase_vars = {}
        self.initial_text = initial_text
        self.editing_existing = False
        if "{{#if" in str(initial_text or ""):
            self.field.set(str(initial_text))
            try:
                parsed_field, parsed_values, parsed_phrases = parse_conditional_text(initial_text)
                self.field.set(parsed_field)
                self.values = parsed_values
                self.phrases = parsed_phrases
                self.editing_existing = True
            except ValueError:
                # Do not reinterpret or rewrite hand-authored conditional text.
                self.window.destroy()
                messagebox.showwarning(
                    "Cannot edit this conditional block",
                    "This selection does not match a complete choice-wording block. "
                    "It has been left unchanged.",
                    parent=parent,
                )
                return
        self.outer = ttk.Frame(self.window, padding=14)
        self.outer.pack(fill="both", expand=True)
        self.heading = ttk.Label(self.outer, font=("", 13, "bold"))
        self.heading.pack(anchor="w")
        self.explanation = ttk.Label(self.outer, wraplength=700)
        self.explanation.pack(anchor="w", pady=(5, 10))
        self.body = ttk.Frame(self.outer)
        self.body.pack(fill="both", expand=True)
        self.preview = ttk.Label(self.outer, wraplength=700, foreground="#315b45")
        self.preview.pack(fill="x", pady=8)
        footer = ttk.Frame(self.outer)
        footer.pack(fill="x")
        self.back = ttk.Button(footer, text="Back", command=self.previous)
        self.back.pack(side="left")
        self.next = ttk.Button(footer, text="Next", command=self.advance)
        self.next.pack(side="right")
        ttk.Button(footer, text="Cancel", command=self.window.destroy).pack(side="right", padx=6)
        self._render()

    def _clear(self):
        for child in self.body.winfo_children():
            child.destroy()

    def _render(self):
        self._clear()
        self.preview.configure(text="")
        titles = ["1 of 4 · Choose a field", "2 of 4 · Enter the wording",
                  "3 of 4 · Choose placement", "4 of 4 · Review"]
        self.heading.configure(text=titles[self.page])
        self.back.configure(state="normal" if self.page else "disabled")
        self.next.configure(text="Insert wording" if self.page == 3 else "Next")
        if self.page == 0:
            self.explanation.configure(text="Choose the field whose answer controls the wording. "
                "You can use an existing choice field or create a new one.")
            ttk.Label(self.body, text="Wording type").grid(row=0, column=0, sticky="w", pady=5)
            ttk.Combobox(self.body, textvariable=self.kind, state="readonly",
                values=("Conditional wording", "Optional clause", "Only if blank")).grid(
                    row=0, column=1, sticky="ew", pady=5)
            ttk.Label(self.body, text="Field name").grid(row=1, column=0, sticky="w", pady=5)
            names = []
            try:
                names = [f["name"] for f in self.library.list_picker_fields()
                         if f.get("default_format") == "choice" or f.get("allowed_values")]
            except (AttributeError, OSError, ValueError):
                pass
            ttk.Combobox(self.body, textvariable=self.field, values=names).grid(
                row=1, column=1, sticky="ew", pady=5)
            ttk.Label(self.body, text="Or type a new field name above.").grid(
                row=2, column=1, sticky="w")
            self.body.columnconfigure(1, weight=1)
        elif self.page == 1:
            self.explanation.configure(text="Enter each allowed value and the exact wording it should produce. "
                "Every value gets its own condition; there is no hidden “everything else” choice.")
            if self.kind.get() == "Conditional wording":
                ttk.Label(self.body, text="Allowed values (one per line)").grid(row=0, column=0, sticky="nw")
                values = tk.Text(self.body, height=5, width=36)
                values.grid(row=0, column=1, sticky="ew")
                if self.values:
                    values.insert("1.0", "\n".join(self.values))
                self.values_widget = values
                values.bind("<KeyRelease>", self._update_live_preview)
                ttk.Label(self.body, text="Wording (one line per value, in the same order)").grid(
                    row=1, column=0, sticky="nw", pady=8)
                wording = tk.Text(self.body, height=9, width=50)
                wording.grid(row=1, column=1, sticky="nsew", pady=8)
                if hasattr(self, "phrases") and self.phrases:
                    wording.insert("1.0", "\n".join(self.phrases))
                self.wording_widget = wording
                wording.bind("<KeyRelease>", self._update_live_preview)
            else:
                ttk.Label(self.body, text="Clause wording").grid(row=0, column=0, sticky="nw")
                self.wording_widget = tk.Text(self.body, height=12, width=60)
                self.wording_widget.grid(row=0, column=1, sticky="nsew")
                self.wording_widget.bind("<KeyRelease>", self._update_live_preview)
            self.body.columnconfigure(1, weight=1)
            self.body.rowconfigure(1, weight=1)
        elif self.page == 2:
            self.explanation.configure(text="Choose whether the generated wording belongs inside an existing "
                "sentence or stands as its own paragraph(s).")
            ttk.Radiobutton(self.body, text="Inside a sentence", variable=self.placement,
                value="Inside a sentence").pack(anchor="w", pady=8)
            ttk.Radiobutton(self.body, text="As separate paragraphs (markers on their own lines)",
                variable=self.placement, value="As separate paragraphs").pack(anchor="w", pady=8)
        else:
            self.explanation.configure(text="Check the wording for every possible answer before inserting it.")
            try:
                result = self._build()
            except ValueError as exc:
                result = "Cannot insert yet: " + str(exc)
            preview = tk.Text(self.body, height=18, wrap="word")
            preview.pack(fill="both", expand=True)
            preview.insert("1.0", result)
            preview.configure(state="disabled")
            self.preview.configure(text=self._summary())
        self._update_preview()

    def _capture(self):
        if self.page == 1:
            if self.kind.get() == "Conditional wording":
                self.values = [x.strip() for x in self.values_widget.get("1.0", "end").splitlines() if x.strip()]
                self.phrases = [x.strip() for x in self.wording_widget.get("1.0", "end-1c").splitlines()]
            else:
                self.phrase = self.wording_widget.get("1.0", "end-1c").strip()

    def _build(self):
        name = self.field.get().strip()
        if self.kind.get() == "Conditional wording":
            if len(self.values) < 2:
                raise ValueError("Enter at least two allowed values.")
            if len(self.phrases) != len(self.values):
                raise ValueError("Enter exactly one wording line for each allowed value.")
            return build_conditional_text(name, self.values, dict(zip(self.values, self.phrases)),
                                          self.placement.get())
        return build_optional_text(name, getattr(self, "phrase", ""),
            only_if_blank=self.kind.get() == "Only if blank", placement=self.placement.get())

    def _summary(self):
        if self.kind.get() == "Conditional wording":
            return "For each answer: " + "; ".join(
                value + " → " + phrase for value, phrase in zip(self.values, self.phrases))
        return ("Shown when the field is blank." if self.kind.get() == "Only if blank"
                else "Shown when the yes/no field is selected.")

    def _update_preview(self):
        if self.page == 1:
            self._update_live_preview()
        elif self.page == 3:
            self.preview.configure(text=self._summary())

    def _update_live_preview(self, _event=None):
        if self.page != 1:
            return
        if self.kind.get() == "Conditional wording":
            values = [line.strip() for line in self.values_widget.get("1.0", "end").splitlines()
                      if line.strip()]
            phrases = [line.strip() for line in self.wording_widget.get("1.0", "end-1c").splitlines()]
            pairs = [phrase for phrase in phrases[:len(values)] if phrase]
            if pairs:
                self.preview.configure(text="Sentence preview: " + " ".join(pairs))
            else:
                self.preview.configure(text="Enter wording for each value to preview the sentence.")
        else:
            phrase = self.wording_widget.get("1.0", "end-1c").strip()
            self.preview.configure(text="Clause preview: " + phrase if phrase
                                   else "Enter the clause wording to preview it.")

    def advance(self):
        try:
            self._capture()
            if self.page == 0 and not self.field.get().strip():
                raise ValueError("Choose or enter a field name.")
            if self.page == 0 and self.kind.get() == "Conditional wording":
                existing = next((item for item in self.library.list_picker_fields()
                    if item.get("name", "").casefold() == self.field.get().strip().casefold()), None)
                if existing:
                    self.values = list(existing.get("allowed_values") or [])
            if self.page == 1:
                self._build()
            if self.page < 3:
                self.page += 1
                self._render()
            else:
                result = self._build()
                self._save_control_field()
                self.on_insert(result)
                self.window.destroy()
        except (ValueError, TypeError, OSError) as exc:
            messagebox.showerror("Check the wording", str(exc), parent=self.window)

    def _save_control_field(self):
        existing = None
        try:
            existing = next((f for f in self.library.list_picker_fields()
                if f.get("name", "").casefold() == self.field.get().strip().casefold()
                and f.get("source") == "field_definition"), None)
        except (AttributeError, OSError, ValueError):
            pass
        fmt = "choice" if self.kind.get() == "Conditional wording" else ""
        allowed = self.values if self.kind.get() == "Conditional wording" else []
        if existing:
            definition = self.library.get_field_definition(existing["id"])
            self.library.edit_field_definition(existing["id"], name=definition["name"],
                description=definition.get("description", ""), default_format=fmt,
                allowed_values=allowed, default_options=definition.get("default_options") or [],
                publisher_profile_column=definition.get("publisher_profile_column"),
                publisher_detail_name=definition.get("publisher_detail_name"))
        else:
            self.library.add_field_definition(self.field.get().strip(), default_format=fmt,
                allowed_values=allowed)
        # Saving is intentionally limited to the field definition; no component text is touched.

    def previous(self):
        self._capture()
        if self.page:
            self.page -= 1
            self._render()
