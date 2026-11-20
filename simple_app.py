"""A focused desktop interface for filling Word templates.

The earlier contract-oriented GUI is preserved in advanced_app.py, but the
packaged application starts here and exposes only the single-document workflow.
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, scrolledtext, ttk

import core
import self_update
from publisher_profiles import PublisherProfileStore, values_for_template
from update_checker import UpdateCheckError, check_for_update
from version import APP_NAME, APP_VERSION, GITHUB_REPOSITORY


def resource_path(name: str) -> pathlib.Path:
    """Find a bundled resource both in source form and in a PyInstaller build."""
    base = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent))
    return base / name


class ScrollableFrame(ttk.Frame):
    """A compact, vertically scrollable container for a template's fields."""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, padding=(4, 4, 14, 4))
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(self.window, width=event.width),
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)
        self.inner.columnconfigure(1, weight=1)

    def _bind_wheel(self, _event=None):
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", lambda _e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda _e: self.canvas.yview_scroll(3, "units"))

    def _unbind_wheel(self, _event=None):
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.unbind_all(sequence)

    def _wheel(self, event):
        if self.canvas.winfo_height() >= self.inner.winfo_height():
            return
        step = -event.delta if sys.platform == "darwin" else -int(event.delta / 120) * 3
        self.canvas.yview_scroll(step, "units")

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)


class FieldInput:
    """A basic form control corresponding to one unique placeholder."""

    def __init__(self, parent, field, row):
        self.field = field
        self.variable = None
        self.text = None
        self.control = None

        if field.kind == "yesno":
            self.variable = tk.BooleanVar(master=parent, value=False)
            self.control = ttk.Checkbutton(
                parent, text=field.name, variable=self.variable
            )
            self.control.grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
            return

        ttk.Label(parent, text=field.name).grid(
            row=row, column=0, sticky="nw", padx=(0, 16), pady=(8, 0)
        )

        if field.kind == "long":
            self.text = tk.Text(
                parent,
                height=4,
                wrap="word",
                undo=True,
                font="TkDefaultFont",
                relief="solid",
                borderwidth=1,
                highlightthickness=0,
            )
            self.text.grid(row=row, column=1, sticky="ew", pady=(5, 0))
        else:
            self.variable = tk.StringVar(master=parent, value="")
            if field.kind == "choice":
                self.control = ttk.Combobox(
                    parent,
                    textvariable=self.variable,
                    values=[""] + field.choices,
                    state="readonly",
                )
            else:
                self.control = ttk.Entry(parent, textvariable=self.variable)
            self.control.grid(row=row, column=1, sticky="ew", pady=(5, 0))

    def get(self):
        if self.field.kind == "yesno":
            return bool(self.variable.get())
        if self.text is not None:
            return self.text.get("1.0", "end-1c")
        return self.variable.get()

    def set(self, value):
        """Set this field from a saved publisher profile."""
        if self.field.kind == "yesno":
            self.variable.set(core.as_bool(value))
        elif self.text is not None:
            self.text.delete("1.0", "end")
            self.text.insert("1.0", "" if value is None else str(value))
        else:
            self.variable.set("" if value is None else str(value))

    def clear(self):
        if self.field.kind == "yesno":
            self.variable.set(False)
        elif self.text is not None:
            self.text.delete("1.0", "end")
        else:
            self.variable.set("")


class PublisherProfileDialog:
    """Create, edit, and delete locally stored publisher profiles."""

    FORM_FIELDS = (
        ("Publisher name *", "publisher_name"),
        ("Primary contact", "contact_name"),
        ("Contact title", "contact_title"),
        ("Contact email", "contact_email"),
        ("Contact phone", "contact_phone"),
        ("Website", "website"),
        ("Address line 1", "address_line1"),
        ("Address line 2", "address_line2"),
        ("City", "city"),
        ("State / Province / Region", "region"),
        ("Postal code", "postal_code"),
        ("Country", "country"),
    )

    def __init__(self, parent, store, on_close=None):
        self.parent = parent
        self.store = store
        self.on_close = on_close
        self.current_id = None
        self.loaded_snapshot = None
        self.ignore_selection_event = False

        self.window = tk.Toplevel(parent)
        self.window.title("Publisher Profiles")
        self.window.geometry("940x650")
        self.window.minsize(760, 520)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer,
            text="Publisher Profiles",
            font=("TkDefaultFont", 15, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Save publisher and primary-contact details once, then load them "
                "into matching fields in any contract template."
            ),
            wraplength=860,
        ).pack(anchor="w", pady=(3, 12))

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(body, text="Saved publishers", padding=8)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(list_frame, columns=("publisher",), show="headings")
        self.tree.heading("publisher", text="Publisher")
        self.tree.column("publisher", width=245, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.select_profile)

        list_buttons = ttk.Frame(list_frame)
        list_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(list_buttons, text="New profile", command=self.new_profile).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(list_buttons, text="Delete", command=self.delete_profile).pack(
            side="left", padx=(6, 0)
        )

        form = ttk.LabelFrame(body, text="Publisher information", padding=10)
        form.grid(row=0, column=1, sticky="nsew")
        form.columnconfigure(1, weight=1)
        self.variables = {}
        for row, (label, name) in enumerate(self.FORM_FIELDS):
            ttk.Label(form, text=label).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=4
            )
            variable = tk.StringVar(master=self.window)
            self.variables[name] = variable
            ttk.Entry(form, textvariable=variable).grid(
                row=row, column=1, sticky="ew", pady=4
            )

        notes_row = len(self.FORM_FIELDS)
        ttk.Label(form, text="Notes").grid(
            row=notes_row, column=0, sticky="nw", padx=(0, 12), pady=(8, 0)
        )
        self.notes = tk.Text(
            form, height=4, wrap="word", undo=True,
            font="TkDefaultFont", relief="solid", borderwidth=1,
        )
        self.notes.grid(row=notes_row, column=1, sticky="ew", pady=(8, 0))

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        self.status = ttk.Label(footer, text="", foreground="#555555")
        self.status.pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Close", command=self.close).pack(side="right")
        ttk.Button(footer, text="Save profile", command=self.save_profile).pack(
            side="right", padx=(0, 8)
        )

        self.refresh_profiles()

    def refresh_profiles(self, selected_id=None):
        for item in self.tree.get_children():
            self.tree.delete(item)
        profiles = self.store.list_profiles()
        for profile in profiles:
            profile_id = str(profile["id"])
            self.tree.insert("", "end", iid=profile_id, values=(profile["publisher_name"],))
        if selected_id is not None and self.tree.exists(str(selected_id)):
            self.tree.selection_set(str(selected_id))
            self.tree.focus(str(selected_id))
            self.tree.see(str(selected_id))
            self._load_profile(int(selected_id))
        elif profiles:
            first_id = str(profiles[0]["id"])
            self.tree.selection_set(first_id)
            self.tree.focus(first_id)
            self._load_profile(int(first_id))
        else:
            self.new_profile()

    def _current_form_values(self):
        values = {name: variable.get() for name, variable in self.variables.items()}
        values["notes"] = self.notes.get("1.0", "end-1c")
        return values

    def _has_unsaved_changes(self):
        current = self._current_form_values()
        if self.loaded_snapshot is None:
            return any(str(value).strip() for value in current.values())
        return current != self.loaded_snapshot

    def select_profile(self, _event=None):
        if self.ignore_selection_event:
            self.ignore_selection_event = False
            return
        selection = self.tree.selection()
        if not selection:
            return
        if self._has_unsaved_changes() and not messagebox.askyesno(
            "Discard unsaved changes?",
            "Discard the unsaved changes to this profile and open the selected publisher?",
            parent=self.window,
        ):
            if self.current_id is not None and self.tree.exists(str(self.current_id)):
                self.ignore_selection_event = True
                self.tree.selection_set(str(self.current_id))
                self.tree.focus(str(self.current_id))
            else:
                self.tree.selection_remove(*selection)
            return
        self._load_profile(int(selection[0]))

    def _load_profile(self, profile_id):
        profile = self.store.get_profile(profile_id)
        if profile is None:
            return
        self.current_id = profile_id
        for name, variable in self.variables.items():
            variable.set(str(profile.get(name) or ""))
        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", str(profile.get("notes") or ""))
        self.loaded_snapshot = self._current_form_values()
        self.status.config(text=f"Editing {profile['publisher_name']}.")

    def new_profile(self):
        if self._has_unsaved_changes() and not messagebox.askyesno(
            "Discard unsaved changes?",
            "Discard the unsaved changes and start a new publisher profile?",
            parent=self.window,
        ):
            return
        self.current_id = None
        for variable in self.variables.values():
            variable.set("")
        self.notes.delete("1.0", "end")
        self.loaded_snapshot = self._current_form_values()
        selection = self.tree.selection()
        if selection:
            self.tree.selection_remove(*selection)
        self.status.config(text="New publisher profile.")

    def save_profile(self):
        profile = {name: variable.get().strip() for name, variable in self.variables.items()}
        profile["notes"] = self.notes.get("1.0", "end-1c").strip()
        try:
            profile_id = self.store.save_profile(profile, self.current_id)
        except (ValueError, OSError, sqlite3.Error) as exc:
            messagebox.showerror("Could not save profile", str(exc), parent=self.window)
            return
        self.status.config(text="Profile saved.")
        self.refresh_profiles(profile_id)

    def delete_profile(self):
        if self.current_id is None:
            messagebox.showinfo("No saved profile", "Select a saved profile to delete.", parent=self.window)
            return
        name = self.variables["publisher_name"].get() or "this publisher"
        if not messagebox.askyesno(
            "Delete publisher profile",
            f"Delete the profile for {name}? This cannot be undone.",
            parent=self.window,
        ):
            return
        self.store.delete_profile(self.current_id)
        self.refresh_profiles()
        self.status.config(text="Profile deleted.")

    def close(self):
        try:
            if self.on_close is not None:
                self.on_close()
        finally:
            self.window.destroy()


class WordTemplateFiller:
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
            text="Create a Word document from a template",
            font=("TkDefaultFont", 15, "bold"),
        )
        heading.pack(anchor="w")
        ttk.Label(
            outer,
            text="Choose a template, fill in its fields, and save a completed copy.",
        ).pack(anchor="w", pady=(3, 12))

        template_row = ttk.Frame(outer)
        template_row.pack(fill="x", pady=(0, 10))
        ttk.Label(template_row, text="Word template").pack(side="left")
        self.template_name = ttk.Label(
            template_row, text="No template selected", foreground="#666666"
        )
        self.template_name.pack(side="left", padx=(10, 10), fill="x", expand=True)
        ttk.Button(template_row, text="Browse…", command=self.choose_template).pack(side="right")

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
            outer, text="Select a .docx or .dotx file to begin.", foreground="#555555"
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
                "Browse for a Word template. The application will find each unique "
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
                self.root, on_close=self._component_editor_closed
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
        values = values_for_template(profile, field_names)
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

    def show_user_guide(self):
        path = resource_path("USER-GUIDE.txt")
        try:
            contents = path.read_text(encoding="utf-8")
        except OSError:
            contents = (
                "Choose a Word template, fill in the fields discovered from its "
                "double-braced placeholders, and create a new document. The original "
                "template is never changed."
            )

        window = tk.Toplevel(self.root)
        window.title("User instructions")
        window.transient(self.root)
        window.geometry("720x620")
        box = scrolledtext.ScrolledText(
            window, wrap="word", font="TkDefaultFont", padx=14, pady=12
        )
        box.pack(fill="both", expand=True)
        box.insert("1.0", contents)
        box.configure(state="disabled")
        ttk.Button(window, text="Close", command=window.destroy).pack(pady=8)

    def show_third_party_licenses(self):
        """Show the bundled notices for third-party packages."""
        path = resource_path("THIRD-PARTY-LICENSES.txt")
        try:
            contents = path.read_text(encoding="utf-8")
        except OSError:
            contents = "The third-party licence notice file could not be found."

        window = tk.Toplevel(self.root)
        window.title("Third-party licences")
        window.transient(self.root)
        window.geometry("720x620")
        box = scrolledtext.ScrolledText(
            window, wrap="word", font="TkFixedFont", padx=14, pady=12
        )
        box.pack(fill="both", expand=True)
        box.insert("1.0", contents)
        box.configure(state="disabled")
        ttk.Button(window, text="Close", command=window.destroy).pack(pady=8)

    def show_template_guide(self):
        """Show the template-authoring section without the rest of the user guide."""
        path = resource_path("USER-GUIDE.txt")
        try:
            contents = path.read_text(encoding="utf-8")
            start = contents.index("WRITING A TEMPLATE")
            end = contents.index("TEMPLATE CHECKS", start)
            contents = contents[start:end].strip()
        except (OSError, ValueError):
            contents = core.CHEAT_SHEET

        window = tk.Toplevel(self.root)
        window.title("How to write a template")
        window.transient(self.root)
        window.geometry("720x620")
        box = scrolledtext.ScrolledText(
            window, wrap="word", font="TkDefaultFont", padx=14, pady=12
        )
        box.pack(fill="both", expand=True)
        box.insert("1.0", contents)
        box.configure(state="disabled")
        ttk.Button(window, text="Close", command=window.destroy).pack(pady=8)

    def show_about(self):
        messagebox.showinfo(
            "About",
            f"{APP_NAME}\nVersion {APP_VERSION}\n\n"
            "A local Word-template tool. Your template and completed documents "
            "remain on your computer.",
            parent=self.root,
        )

    def check_for_updates(self, manual: bool):
        # Manual checks always run. Automatic checks are limited to once per day.
        if not manual and not self_update.automatic_update_check_due():
            return

        if self.update_checking:
            if manual:
                messagebox.showinfo(
                    "Update check",
                    "An update check is already in progress.",
                    parent=self.root,
                )
            return

        self.update_checking = True
        if manual:
            self.status.config(text="Checking for updates…", foreground="#555555")

        def worker():
            try:
                result = check_for_update(APP_VERSION, GITHUB_REPOSITORY, token=self_update.load_token())
                try:
                    self_update.record_successful_update_check()
                except OSError:
                    # A settings-file problem must not turn a successful check into a failure.
                    pass
                self.root.after(0, self._finish_update_check, result, None, manual)
            except UpdateCheckError as exc:
                self.root.after(0, self._finish_update_check, None, exc, manual)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_update_check(self, result, error, manual: bool):
        self.update_checking = False
        if error:
            if manual:
                self.status.config(text="Update check could not be completed.", foreground="#8a5a00")
                messagebox.showwarning("Update check failed", str(error), parent=self.root)
            return

        if not result.available:
            if manual:
                self.status.config(text="You are using the latest published version.", foreground="#1b6e2e")
                messagebox.showinfo(
                    "No update available",
                    f"You are using the latest published version ({APP_VERSION}).",
                    parent=self.root,
                )
            return

        self.status.config(
            text=f"Version {result.latest_version} is available (you have {APP_VERSION}).",
            foreground="#1b6e2e",
        )
        heading = (
            f"{result.release_name} is available.\n"
            f"Installed version: {APP_VERSION}\n"
            f"Latest version: {result.latest_version}\n\n"
        )
        notes = result.notes.strip()
        if notes:
            note_lines = notes.splitlines()
            notes_preview = "\n".join(note_lines[:15])
            if len(note_lines) > 15:
                notes_preview += "\n…"
            heading += "What's new:\n" + notes_preview + "\n\n"
        asset = result.asset(self_update.WINDOWS_ASSET)
        if self_update.can_install_in_place() and asset:
            if messagebox.askyesno(
                "Update available",
                heading + "Download and install it now? The app will close and reopen "
                "as the new version. Anything not yet saved will be lost.",
                parent=self.root,
            ):
                self.install_update(result, asset)
            return
        if self_update.can_install_in_place():
            message = (heading + "That release has no Windows download attached yet, so it "
                       "cannot be installed automatically. Open the release page?")
        else:
            message = heading + "Open the GitHub release page to download it?"
        if messagebox.askyesno("Update available", message, parent=self.root) and result.release_url:
            webbrowser.open(result.release_url)

    def install_update(self, result, asset):
        """Download the new .exe with a progress bar, then swap it in and restart."""
        target = self_update.running_executable()
        in_place = self_update.folder_is_writable(target.parent)
        if in_place:
            destination = target.with_name(target.name + ".new")
        else:
            destination = self_update.downloads_folder() / f"Word Template Filler {result.latest_version}.exe"

        window = tk.Toplevel(self.root)
        window.title("Downloading update")
        window.transient(self.root)
        window.resizable(False, False)
        window.protocol("WM_DELETE_WINDOW", lambda: None)      # it finishes or fails on its own
        ttk.Label(window, text=f"Downloading version {result.latest_version}…",
                  padding=(16, 14, 16, 6)).pack(anchor="w")
        bar = ttk.Progressbar(window, length=360, mode="determinate", maximum=max(asset.size, 1))
        bar.pack(padx=16, pady=(0, 16))
        window.grab_set()

        def progress(done, _total):
            self.root.after(0, lambda: bar.configure(value=done))

        def worker():
            try:
                self_update.download_asset(asset, destination, self_update.load_token(), progress)
                self.root.after(0, finished, None)
            except self_update.UpdateInstallError as exc:
                self.root.after(0, finished, str(exc))

        def finished(problem):
            window.grab_release()
            window.destroy()
            if problem:
                messagebox.showerror("Update not installed", problem, parent=self.root)
                return
            if not in_place:
                messagebox.showinfo(
                    "Update downloaded",
                    f"The app's own folder cannot be written to:\n{target.parent}\n\n"
                    f"so the new version was saved to:\n{destination}\n\n"
                    "Close this app and use that file instead, or move it over the old one.",
                    parent=self.root,
                )
                return
            try:
                self_update.start_swap(target, destination)
            except OSError as exc:
                messagebox.showerror("Update not installed", f"The update could not start: {exc}",
                                     parent=self.root)
                return
            self.root.destroy()

        threading.Thread(target=worker, daemon=True).start()

    def _report_failed_update(self):
        if not self_update.can_install_in_place():
            return
        target = self_update.running_executable()
        self_update.cleanup_stale_update_download(target)
        note = self_update.leftover_note(target)
        if note:
            messagebox.showwarning("The last update did not finish", note, parent=self.root)

    def update_settings(self):
        """Manage the optional per-user GitHub token for update checks."""
        window = tk.Toplevel(self.root)
        window.title("Update settings")
        window.transient(self.root)
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, wraplength=460, justify="left", text=(
            "You do not need a GitHub token for normal update checks. If you often see "
            "\"GitHub is limiting update checks from your network for now\", you can "
            "add an optional token here to raise GitHub's API limit for your checks.\n\n"
            "Create a fine-grained personal access token on GitHub (Settings > Developer "
            "settings) for this repository only, with read-only access to Contents and "
            "nothing else. It is saved for your Windows user only, in:\n"
            f"{self_update.settings_path()}"
        )).pack(anchor="w")
        token = tk.StringVar(value=self_update.load_token())
        entry = ttk.Entry(frame, textvariable=token, show="•", width=56)
        entry.pack(fill="x", pady=(12, 4))
        status = ttk.Label(frame, foreground="#555555", wraplength=460, justify="left")
        status.pack(anchor="w", pady=(0, 8))
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")

        def save():
            try:
                self_update.save_token(token.get())
            except OSError as exc:
                status.config(text=f"Could not save: {exc}", foreground="#b00020")
                return
            status.config(text="Saved. Checking for updates…", foreground="#555555")
            window.destroy()
            self.check_for_updates(manual=True)

        def remove():
            token.set("")
            try:
                self_update.save_token("")
            except OSError:
                pass
            status.config(text="Token removed.", foreground="#555555")

        ttk.Button(buttons, text="Save and check now", command=save).pack(side="right")
        ttk.Button(buttons, text="Remove token", command=remove).pack(side="right", padx=8)
        ttk.Button(buttons, text="Close", command=window.destroy).pack(side="left")
        entry.focus_set()


def main():
    root = tk.Tk()
    WordTemplateFiller(root)
    root.mainloop()


if __name__ == "__main__":
    main()
