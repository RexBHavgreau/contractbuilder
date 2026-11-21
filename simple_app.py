"""A focused desktop interface for filling Word templates.

The earlier contract-oriented GUI is preserved in advanced_app.py, but the
packaged application starts here and exposes only the single-document workflow.
"""
from __future__ import annotations

import pathlib
import sqlite3
import tempfile
import threading  # noqa: F401  (tests patch simple_app.threading.Thread)
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import core
from assembly_document_window import AssemblyDocumentWindow
from help_windows import HelpWindowsMixin
from publisher_dialog import PublisherProfileDialog
from field_matching import FieldMatchingDialog
from publisher_profiles import PublisherProfileStore, values_for_template
from start_screen import StartScreenMixin, build_start_row
from ui_widgets import FieldInput, ScrollableFrame, resource_path  # noqa: F401
from update_dialogs import UpdateDialogsMixin
from version import APP_NAME, APP_VERSION


class WordTemplateFiller(StartScreenMixin, UpdateDialogsMixin, HelpWindowsMixin):
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("820x680")
        self.root.minsize(620, 480)

        self.template = None
        self.inputs = []
        self.update_checking = False
        self.publisher_store = None
        self.publisher_store_error = None
        self.publisher_profile_ids = {}
        self.component_editor_window = None
        self.assembly_document_windows = []
        try:
            self.publisher_store = PublisherProfileStore()
        except (OSError, sqlite3.Error) as exc:
            self.publisher_store_error = str(exc)

        self._build_menu()
        self._build_window()
        self._show_welcome()
        self.root.after(600, self._report_failed_update)
        self.root.after(1200, lambda: self.check_for_updates(manual=False))

    def _build_menu(self):
        menu = tk.Menu(self.root)
        publisher_menu = tk.Menu(menu, tearoff=False)
        publisher_menu.add_command(
            label="Manage publisher profiles…", command=self.manage_publisher_profiles
        )
        publisher_menu.add_command(
            label="Field matching…", command=self.manage_field_matching
        )
        menu.add_cascade(label="Publishers", menu=publisher_menu)

        component_menu = tk.Menu(menu, tearoff=False)
        component_menu.add_command(
            label="Manage components…", command=self.manage_components
        )
        menu.add_cascade(label="Components", menu=component_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="User instructions", command=self.show_user_guide)
        help_menu.add_command(label="How to write a template", command=self.show_template_guide)
        help_menu.add_command(label="Third-party licences", command=self.show_third_party_licenses)
        help_menu.add_command(label="Check for updates", command=lambda: self.check_for_updates(manual=True))
        help_menu.add_command(label="Update settings…", command=self.update_settings)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        menu.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menu)

    def _build_window(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        heading = ttk.Label(
            outer,
            text="Create a contract or Word document",
            font=("TkDefaultFont", 15, "bold"),
        )
        heading.pack(anchor="w")
        ttk.Label(
            outer,
            text="Choose where to start, fill in the fields, and save a completed copy.",
        ).pack(anchor="w", pady=(3, 12))

        self.template_name = build_start_row(outer, self)

        publisher_frame = ttk.LabelFrame(outer, text="Saved publisher", padding=8)
        publisher_frame.pack(fill="x", pady=(0, 10))
        self.publisher_variable = tk.StringVar(master=outer)
        self.publisher_combo = ttk.Combobox(
            publisher_frame, textvariable=self.publisher_variable, state="disabled"
        )
        self.publisher_combo.pack(side="left", fill="x", expand=True)
        self.load_publisher_button = ttk.Button(
            publisher_frame, text="Load into fields",
            command=self.load_publisher_profile, state="disabled",
        )
        self.load_publisher_button.pack(side="left", padx=(8, 0))
        ttk.Button(
            publisher_frame, text="Manage profiles…",
            command=self.manage_publisher_profiles,
        ).pack(side="left", padx=(8, 0))

        self.summary = ttk.Label(
            outer, text="Choose how to build the contract to begin.", foreground="#555555"
        )
        self.summary.pack(anchor="w", pady=(0, 8))

        self.form_frame = ttk.LabelFrame(outer, text="Fields to fill in", padding=8)
        self.form_frame.pack(fill="both", expand=True)
        self.scroll = ScrollableFrame(self.form_frame)
        self.scroll.pack(fill="both", expand=True)

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(12, 0))
        self.highlight_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            bottom,
            text="Highlight inserted text for review",
            variable=self.highlight_var,
        ).pack(side="left")
        self.clear_button = ttk.Button(bottom, text="Clear fields", command=self.clear_fields)
        self.clear_button.pack(side="right", padx=(8, 0))
        self.create_button = ttk.Button(
            bottom, text="Create document…", command=self.create_document, state="disabled"
        )
        self.create_button.pack(side="right")

        self.status = ttk.Label(outer, text="", foreground="#555555", wraplength=760)
        self.status.pack(anchor="w", pady=(8, 0))
        self.refresh_publisher_profiles()

    def _show_welcome(self):
        self.scroll.clear()
        ttk.Label(
            self.scroll.inner,
            text=(
                "Use Existing or New contract assembly to build from saved components, or Word file to browse for a template. The application will find each unique "
                "placeholder, such as {{Recipient Name}}, and show one field for it. "
                "The same placeholder can appear more than once in the document."
            ),
            wraplength=690,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=12)

    def choose_template(self):
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Choose a Word template",
            filetypes=[
                ("Word documents and templates", "*.docx *.dotx"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.load_template(pathlib.Path(selected))

    def load_template(self, path: pathlib.Path):
        try:
            template = core.Template(path)
        except (core.TemplateError, OSError, PermissionError) as exc:
            messagebox.showerror("Could not read the template", str(exc), parent=self.root)
            return

        self.template = template
        self.inputs = []
        self.scroll.clear()
        self.template_name.config(text=path.name)
        fields = template.field_list()
        self.summary.config(
            text=f"Found {len(fields)} unique field(s) in {template.places} location(s)."
        )

        if template.problems:
            self.create_button.config(state="disabled")
            ttk.Label(
                self.scroll.inner,
                text=(
                    "This template has problems that should be corrected in Word "
                    "before creating a document:\n\n"
                    + "\n".join("• " + problem for problem in template.problems)
                ),
                foreground="#a00000",
                wraplength=690,
                justify="left",
            ).grid(row=0, column=0, columnspan=2, sticky="w", pady=10)
        elif not fields:
            self.create_button.config(state="disabled")
            ttk.Label(
                self.scroll.inner,
                text="No placeholders were found in this document.",
                foreground="#666666",
            ).grid(row=0, column=0, sticky="w", pady=10)
        else:
            row = 0
            for field in fields:
                control = FieldInput(self.scroll.inner, field, row)
                self.inputs.append(control)
                row += 1 if field.kind == "yesno" else 2
            self.create_button.config(state="normal")

        if template.warnings:
            self.status.config(
                text="Template notes: " + " ".join(template.warnings),
                foreground="#8a5a00",
            )
        elif template.problems:
            self.status.config(text="Correct the template problems before continuing.", foreground="#a00000")
        else:
            self.status.config(text="", foreground="#555555")

    def refresh_publisher_profiles(self):
        if self.publisher_store is None:
            self.publisher_combo.configure(state="disabled", values=[])
            self.load_publisher_button.configure(state="disabled")
            if self.publisher_store_error:
                self.status.config(
                    text=f"Publisher profiles are unavailable: {self.publisher_store_error}",
                    foreground="#8a5a00",
                )
            return
        try:
            profiles = self.publisher_store.list_profiles()
        except sqlite3.Error as exc:
            self.publisher_combo.configure(state="disabled", values=[])
            self.load_publisher_button.configure(state="disabled")
            self.status.config(
                text=f"Could not read publisher profiles: {exc}", foreground="#a00000"
            )
            return
        self.publisher_profile_ids = {
            str(profile["publisher_name"]): int(profile["id"]) for profile in profiles
        }
        names = list(self.publisher_profile_ids)
        self.publisher_combo.configure(values=names, state="readonly" if names else "disabled")
        self.load_publisher_button.configure(state="normal" if names else "disabled")
        self.publisher_variable.set("")

    def create_assembly_document(self, shell_path, component_markdown, assembly_name=""):
        """Compose an assembly draft and open a separate field-entry window."""
        temporary = tempfile.TemporaryDirectory(prefix="contractbuilder-assembly-")
        output_path = pathlib.Path(temporary.name) / "assembled.docx"
        try:
            from assembly_builder import compose_assembly_template

            template, composition = compose_assembly_template(
                shell_path, component_markdown, output_path
            )
            if template.problems:
                raise core.TemplateError(
                    "The assembled document has field problems that must be corrected:\n\n"
                    + "\n".join(template.problems)
                )
            window = AssemblyDocumentWindow(
                self, template, temporary, pathlib.Path(shell_path),
                assembly_name, composition.warnings,
            )
        except (core.TemplateError, ValueError, TypeError, OSError, sqlite3.Error) as exc:
            temporary.cleanup()
            messagebox.showerror(
                "Could not prepare the assembly", str(exc), parent=self.root
            )
            return None

        remaining = []
        for child in self.assembly_document_windows:
            try:
                if child.window.winfo_exists():
                    remaining.append(child)
            except tk.TclError:
                pass
        self.assembly_document_windows = remaining
        self.assembly_document_windows.append(window)
        return window

    def manage_components(self):
        """Open the component manager without loading it during app startup."""
        if self.component_editor_window is not None:
            try:
                if self.component_editor_window.window.winfo_exists():
                    self.component_editor_window.window.lift()
                    self.component_editor_window.window.focus_set()
                    return
            except tk.TclError:
                self.component_editor_window = None
        try:
            # Keep the editor module out of the template workflow's import
            # path; it is loaded only when the user opens Components.
            from component_editor import ComponentEditorWindow

            self.component_editor_window = ComponentEditorWindow(
                self.root,
                on_close=self._component_editor_closed,
                on_generate=self.create_assembly_document,
            )
        except (OSError, sqlite3.Error, tk.TclError, ValueError) as exc:
            self.component_editor_window = None
            messagebox.showerror(
                "Components unavailable",
                f"Could not open the component library.\n\n{exc}",
                parent=self.root,
            )

    def _component_editor_closed(self):
        self.component_editor_window = None

    def manage_field_matching(self):
        if self.publisher_store is None:
            messagebox.showerror(
                "Publisher database unavailable",
                "Field matching is unavailable because the publisher database could not be opened.",
                parent=self.root,
            )
            return
        FieldMatchingDialog(self.root, self.publisher_store)

    def manage_publisher_profiles(self):
        if self.publisher_store is None:
            messagebox.showerror(
                "Publisher profiles unavailable",
                self.publisher_store_error or "The local profile database could not be opened.",
                parent=self.root,
            )
            return
        PublisherProfileDialog(
            self.root, self.publisher_store, on_close=self.refresh_publisher_profiles
        )

    def load_publisher_profile(self):
        if self.template is None:
            messagebox.showinfo(
                "Choose a template first",
                "Select a Word template before loading a publisher profile.",
                parent=self.root,
            )
            return
        name = self.publisher_variable.get()
        profile_id = self.publisher_profile_ids.get(name)
        if profile_id is None or self.publisher_store is None:
            return
        try:
            profile = self.publisher_store.get_profile(profile_id)
        except sqlite3.Error as exc:
            messagebox.showerror("Could not load publisher profile", str(exc), parent=self.root)
            return
        if profile is None:
            self.refresh_publisher_profiles()
            messagebox.showwarning(
                "Profile not found",
                "That publisher profile was removed. Refresh the list and try again.",
                parent=self.root,
            )
            return

        field_names = [control.field.name for control in self.inputs]
        values = values_for_template(
            profile, field_names, self.publisher_store.field_match_map()
        )
        if not values:
            messagebox.showinfo(
                "No matching fields",
                "This template has no fields recognized by the publisher profile. "
                "The existing contract fields have not been changed.",
                parent=self.root,
            )
            return
        overwritten = [
            field_name for field_name, value in values.items()
            if any(
                control.field.name == field_name and str(control.get()).strip()
                for control in self.inputs
            )
        ]
        if overwritten and not messagebox.askyesno(
            "Replace existing entries?",
            "Loading this profile will replace these non-empty fields:\n\n"
            + "\n".join("• " + field for field in overwritten)
            + "\n\nContinue?",
            parent=self.root,
        ):
            return
        for control in self.inputs:
            if control.field.name in values:
                control.set(values[control.field.name])
        self.status.config(
            text=(
                f"Loaded {len(values)} field(s) from {profile['publisher_name']}. "
                "Review the remaining contract fields before creating the document."
            ),
            foreground="#1b6e2e",
        )

    def collect_values(self):
        return {control.field.name: control.get() for control in self.inputs}

    def clear_fields(self):
        for control in self.inputs:
            control.clear()
        self.status.config(text="All fields cleared.", foreground="#555555")

    def create_document(self):
        if self.template is None:
            return

        values = self.collect_values()
        problems = core.problems_with(self.template, values)
        if problems:
            messagebox.showerror(
                "Some entries need attention",
                "\n".join(f"• {name}: {reason}" for name, reason in problems),
                parent=self.root,
            )
            return

        try:
            document_bytes, report = core.render(
                self.template, values, highlight=self.highlight_var.get()
            )
        except core.TemplateError as exc:
            messagebox.showerror("Could not create the document", str(exc), parent=self.root)
            return

        if report.blanks:
            names = "\n".join("• " + name for name in report.blanks)
            proceed = messagebox.askyesno(
                "Some fields are empty",
                "These fields will be left as blank lines in the document:\n\n"
                + names
                + "\n\nCreate the document anyway?",
                parent=self.root,
            )
            if not proceed:
                return

        suggested = core.suggested_name(self.template, values) + ".docx"
        output = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save the completed Word document",
            defaultextension=".docx",
            initialdir=str(self.template.path.parent),
            initialfile=suggested,
            filetypes=[("Word document", "*.docx")],
        )
        if not output:
            return

        destination = pathlib.Path(output)
        try:
            if destination.resolve() == self.template.path.resolve():
                messagebox.showerror(
                    "Choose a different file name",
                    "The completed document cannot overwrite its template.",
                    parent=self.root,
                )
                return
            destination.write_bytes(document_bytes)
        except OSError as exc:
            messagebox.showerror("Could not save the document", str(exc), parent=self.root)
            return

        self.status.config(
            text=f"Created {destination.name} — filled {report.filled} placeholder(s).",
            foreground="#1b6e2e",
        )
        messagebox.showinfo(
            "Document created",
            f"The completed document was saved to:\n{destination}",
            parent=self.root,
        )


def main():
    root = tk.Tk()
    WordTemplateFiller(root)
    root.mainloop()


if __name__ == "__main__":
    main()
