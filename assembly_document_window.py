"""The field-entry window for a contract assembled from components."""
from __future__ import annotations

import pathlib
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import core
from publisher_profiles import (
    values_for_template, publisher_column_for_field, unmatched_profile_details,
)
from ui_widgets import FieldInput, ScrollableFrame


class AssemblyDocumentWindow:
    """Fill an assembled temporary DOCX without changing the template workflow."""

    def __init__(
        self, app, template, temporary_directory, shell_path,
        assembly_name="", composition_warnings=(),
    ):
        self.app = app
        self.template = template
        self.temporary_directory = temporary_directory
        self.shell_path = pathlib.Path(shell_path)
        self.assembly_name = str(assembly_name or "").strip()
        self.composition_warnings = tuple(composition_warnings or ())
        self.inputs = []
        self.publisher_profile_ids = {}

        self.window = tk.Toplevel(app.root)
        self.window.title("Fill assembly fields")
        self.window.geometry("820x690")
        self.window.minsize(620, 500)
        self.window.transient(app.root)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        outer = ttk.Frame(self.window, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer, text="Fill assembly fields", font=("TkDefaultFont", 15, "bold")
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                f"{self.assembly_name or 'Unsaved assembly'} · "
                f"{len(template.field_list())} unique field(s) in {template.places} location(s)"
            ),
            wraplength=760,
        ).pack(anchor="w", pady=(3, 10))

        profile_frame = ttk.LabelFrame(outer, text="Saved publisher", padding=8)
        profile_frame.pack(fill="x", pady=(0, 10))
        self.publisher_variable = tk.StringVar(master=self.window)
        self.publisher_combo = ttk.Combobox(
            profile_frame, textvariable=self.publisher_variable, state="disabled"
        )
        self.publisher_combo.pack(side="left", fill="x", expand=True)
        self.load_publisher_button = ttk.Button(
            profile_frame, text="Fill all from publisher",
            command=self.load_publisher_profile, state="disabled",
        )
        self.load_publisher_button.pack(side="left", padx=(8, 0))
        self.auto_fill_publisher = tk.BooleanVar(master=self.window, value=False)
        ttk.Checkbutton(
            outer, text="Fill automatically when I choose a publisher",
            variable=self.auto_fill_publisher,
        ).pack(anchor="w", pady=(0, 8))
        self.publisher_combo.bind("<<ComboboxSelected>>", self.publisher_selection_changed)
        ttk.Button(
            profile_frame, text="Manage profiles…",
            command=self.app.manage_publisher_profiles,
        ).pack(side="left", padx=(8, 0))

        ttk.Label(
            outer,
            text=(
                "One field is shown for each unique placeholder, even when it appears "
                "in several components or locations."
            ),
            foreground="#555555",
            wraplength=760,
        ).pack(anchor="w", pady=(0, 8))

        form = ttk.LabelFrame(outer, text="Fields to fill in", padding=8)
        form.pack(fill="both", expand=True)
        self.scroll = ScrollableFrame(form)
        self.scroll.pack(fill="both", expand=True)
        row = 0
        for field in template.field_list():
            store = self.app.publisher_store
            match_map = store.field_match_map() if store is not None else {}
            fill_callback = (
                (lambda name=field.name: self.load_publisher_profile(name))
                if publisher_column_for_field(field.name, match_map) else None
            )
            control = FieldInput(
                self.scroll.inner, field, row, on_fill_from_publisher=fill_callback
            )
            self.inputs.append(control)
            row += 1 if field.kind == "yesno" else 2
        if not self.inputs:
            ttk.Label(
                self.scroll.inner,
                text="This assembly has no fields to fill. You can create the document as it is.",
                wraplength=690,
            ).grid(row=0, column=0, sticky="w", pady=12)

        notes = list(template.warnings)
        notes.extend(
            getattr(warning, "message", str(warning))
            for warning in self.composition_warnings
        )
        ttk.Label(
            outer,
            text=("Notes: " + " ".join(notes)) if notes else "",
            foreground="#8a5a00" if notes else "#555555",
            wraplength=760,
        ).pack(anchor="w", pady=(8, 0))

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        self.status = ttk.Label(footer, text="", foreground="#555555", wraplength=350)
        self.status.pack(side="left", fill="x", expand=True)
        self.highlight_variable = tk.BooleanVar(master=self.window, value=False)
        ttk.Checkbutton(
            footer, text="Highlight inserted text", variable=self.highlight_variable
        ).pack(side="left", padx=(5, 8))
        ttk.Button(footer, text="Clear fields", command=self.clear_fields).pack(
            side="right", padx=(0, 7)
        )
        ttk.Button(footer, text="Close", command=self.close).pack(side="right")
        ttk.Button(
            footer, text="Create document…", command=self.create_document
        ).pack(side="right", padx=(0, 7))
        self._refresh_publisher_profiles()

    def _refresh_publisher_profiles(self):
        store = self.app.publisher_store
        if store is None:
            self.publisher_combo.configure(state="disabled", values=[])
            self.load_publisher_button.configure(state="disabled")
            return
        try:
            profiles = store.list_profiles()
        except sqlite3.Error as exc:
            self.publisher_combo.configure(state="disabled", values=[])
            self.load_publisher_button.configure(state="disabled")
            self.status.configure(
                text=f"Could not read publisher profiles: {exc}",
                foreground="#a00000",
            )
            return
        self.publisher_profile_ids = {
            str(profile["publisher_name"]): int(profile["id"])
            for profile in profiles
        }
        names = list(self.publisher_profile_ids)
        self.publisher_combo.configure(
            values=names, state="readonly" if names else "disabled"
        )
        self.load_publisher_button.configure(
            state="normal" if names else "disabled"
        )
        self.publisher_variable.set("")

    def publisher_selection_changed(self, _event=None):
        if self.auto_fill_publisher.get():
            self.load_publisher_profile()

    def load_publisher_profile(self, field_name=None):
        name = self.publisher_variable.get()
        profile_id = self.publisher_profile_ids.get(name)
        store = self.app.publisher_store
        if profile_id is None or store is None:
            return
        try:
            profile = store.get_profile(profile_id)
            match_map = store.field_match_map()
        except sqlite3.Error as exc:
            messagebox.showerror(
                "Could not load publisher profile", str(exc), parent=self.window
            )
            return
        if profile is None:
            self._refresh_publisher_profiles()
            messagebox.showwarning(
                "Profile not found",
                "That publisher profile was removed. Refresh the list and try again.",
                parent=self.window,
            )
            return
        field_names = [control.field.name for control in self.inputs]
        requested_names = [field_name] if field_name else field_names
        values = values_for_template(profile, requested_names, match_map)
        if not values:
            messagebox.showinfo(
                "No matching fields",
                (f"No saved publisher value is available for “{field_name}”."
                 if field_name else
                 "No fields in this assembly match the saved publisher profile."),
                parent=self.window,
            )
            return
        overwritten = [
            item for item in values
            if any(control.field.name == item and str(control.get()).strip()
                   for control in self.inputs)
        ]
        if overwritten and not messagebox.askyesno(
            "Replace existing entries?",
            "Loading this profile will replace these non-empty fields:\n\n"
            + "\n".join("• " + item for item in overwritten)
            + "\n\nContinue?",
            parent=self.window,
        ):
            return
        for control in self.inputs:
            if control.field.name in values:
                control.set(values[control.field.name])
        missing = unmatched_profile_details(profile, field_names, match_map)
        summary = "Filled: " + ", ".join(values)
        if missing:
            summary += ". No matching field for: " + ", ".join(missing)
        else:
            summary += ". All populated publisher details have a matching field."
        self.status.configure(text=summary, foreground="#1b6e2e")

    def collect_values(self):
        return {control.field.name: control.get() for control in self.inputs}

    def clear_fields(self):
        for control in self.inputs:
            control.clear()
        self.status.configure(text="All fields cleared.", foreground="#555555")

    def create_document(self):
        values = self.collect_values()
        problems = core.problems_with(self.template, values)
        if problems:
            messagebox.showerror(
                "Some entries need attention",
                "\n".join(f"• {name}: {reason}" for name, reason in problems),
                parent=self.window,
            )
            return
        try:
            document_bytes, report = core.render(
                self.template, values, highlight=self.highlight_variable.get()
            )
        except core.TemplateError as exc:
            messagebox.showerror(
                "Could not create the document", str(exc), parent=self.window
            )
            return
        if report.blanks:
            names = "\n".join("• " + name for name in report.blanks)
            if not messagebox.askyesno(
                "Some fields are empty",
                "These fields will be left as blank lines in the document:\n\n"
                + names + "\n\nCreate the document anyway?",
                parent=self.window,
            ):
                return

        suggested = core.suggested_name(self.template, values) + ".docx"
        if self.assembly_name:
            safe_name = "".join(
                character for character in self.assembly_name
                if character not in '<>:"/\\|?*'
            ).strip(" .")
            if safe_name:
                suggested = safe_name + ".docx"
        output = filedialog.asksaveasfilename(
            parent=self.window,
            title="Save the completed assembly",
            defaultextension=".docx",
            initialdir=str(self.shell_path.parent),
            initialfile=suggested,
            filetypes=[("Word document", "*.docx")],
        )
        if not output:
            return
        destination = pathlib.Path(output)
        try:
            if destination.resolve() == self.shell_path.resolve():
                messagebox.showerror(
                    "Choose a different file name",
                    "The completed document cannot overwrite its Word shell.",
                    parent=self.window,
                )
                return
            if destination.resolve() == self.template.path.resolve():
                messagebox.showerror(
                    "Choose a different file name",
                    "The completed document cannot overwrite the temporary assembly.",
                    parent=self.window,
                )
                return
            destination.write_bytes(document_bytes)
        except OSError as exc:
            messagebox.showerror(
                "Could not save the document", str(exc), parent=self.window
            )
            return
        self.status.configure(
            text=f"Created {destination.name} — filled {report.filled} placeholder(s).",
            foreground="#1b6e2e",
        )
        messagebox.showinfo(
            "Document created",
            f"The completed document was saved to:\n{destination}",
            parent=self.window,
        )

    def close(self):
        try:
            self.temporary_directory.cleanup()
        finally:
            self.window.destroy()
