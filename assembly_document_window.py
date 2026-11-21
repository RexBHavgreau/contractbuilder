"""The field-entry window for a contract assembled from components."""
from __future__ import annotations

import pathlib
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import core
from publisher_panel import PublisherPanel
from ui_widgets import FieldInput, ScrollableFrame


class AssemblyDocumentWindow:
    """Fill an assembled temporary DOCX without changing the template workflow."""

    def __init__(
        self, app, template, temporary_directory, shell_path,
        assembly_name="", composition_warnings=(), assembly_revision=None,
        on_edit_assembly=None, on_review_updates=None,
    ):
        self.app = app
        self.template = template
        self.temporary_directory = temporary_directory
        self.shell_path = pathlib.Path(shell_path)
        self.assembly_name = str(assembly_name or "").strip()
        self.composition_warnings = tuple(composition_warnings or ())
        self.assembly_revision = assembly_revision
        self.on_edit_assembly = on_edit_assembly
        self.on_review_updates = on_review_updates
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

        if self.assembly_revision is not None:
            assembly_actions = ttk.Frame(outer)
            assembly_actions.pack(fill="x", pady=(0, 8))
            if self.on_edit_assembly is not None:
                ttk.Button(
                    assembly_actions, text="Edit this assembly…",
                    command=self.on_edit_assembly,
                ).pack(side="left")
            if (
                self.assembly_revision.get("has_newer_wording")
                and self.on_review_updates is not None
            ):
                ttk.Button(
                    assembly_actions, text="Review updates…",
                    command=self.on_review_updates,
                ).pack(side="left", padx=(7, 0))

        self.publisher_panel = PublisherPanel(
            self.window, outer, self.app.publisher_store, self.app.publisher_store_error,
            lambda: self.inputs,
            lambda text, color: self.status.configure(text=text, foreground=color),
            self.app.manage_publisher_profiles,
            "No fields in this assembly match the saved publisher profile.",
        )

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
        fields = template.field_list()
        self.publisher_panel.analyze([field.name for field in fields])
        for field in fields:
            control = FieldInput(
                self.scroll.inner, field, row,
                on_fill_from_publisher=self.publisher_panel.callback_for(field.name),
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
        # The message has its own wrapping line, so a long one cannot push the
        # buttons out of the window.
        self.status = ttk.Label(footer, text="", foreground="#555555", justify="left", wraplength=700)
        self.status.pack(side="top", fill="x", anchor="w", pady=(0, 6))
        footer.bind(
            "<Configure>",
            lambda event: self.status.configure(wraplength=max(200, event.width - 20)),
        )
        buttons = ttk.Frame(footer)
        buttons.pack(side="top", fill="x")
        self.highlight_variable = tk.BooleanVar(master=self.window, value=False)
        ttk.Checkbutton(
            buttons, text="Highlight inserted text", variable=self.highlight_variable
        ).pack(side="left", padx=(5, 8))
        ttk.Button(buttons, text="Clear fields", command=self.clear_fields).pack(
            side="right", padx=(0, 7)
        )
        ttk.Button(buttons, text="Close", command=self.close).pack(side="right")
        ttk.Button(
            buttons, text="Create document…", command=self.create_document
        ).pack(side="right", padx=(0, 7))
        self._refresh_publisher_profiles()

    def _refresh_publisher_profiles(self):
        self.publisher_panel.refresh_profiles()

    def load_publisher_profile(self, field_name=None):
        """Fill the form from the chosen saved publisher (all fields, or one)."""
        resolution = self.publisher_panel.resolutions.get(field_name) if field_name else None
        self.publisher_panel.fill(resolution.party if resolution else None, field_name)

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
