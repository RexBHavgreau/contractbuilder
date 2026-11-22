"""User interface for arranging, previewing and saving component assemblies.

The window is loaded only when the user opens the assembly workflow. The saved
recipe pins immutable component versions and never rewrites the Word shell.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Sequence

from assembly_helpers import (  # noqa: F401  (re-exported for callers and tests)
    compose_assembly_template,
    included_component_markdown,
    preview_segments_for_components,
    shell_file_sha256,
    update_component_items,
    version_diff_lines,
)
import assembly_open_dialog
import assembly_review_dialog
from component_preview import (
    PREVIEW_KEY,
    conditional_preview_choices,
    conditional_preview_warnings,
    configure_preview_tags,
)
from library import ComponentLibrary
import shell_selection
from docx_compose import ComponentText
from layout_file_dialog import confirm_layout_file


NO_SHELL = "None chosen yet"


def _name_key(name: str) -> str:
    """Names are the same assembly when only capitals or spacing differ."""
    return " ".join(str(name or "").split()).casefold()


class AssemblyBuilderWindow:
    """Arrange components, choose a shell, preview and save immutable revisions."""

    def __init__(self, parent, library: ComponentLibrary | None = None, on_generate=None):
        self.parent = parent
        self.library = library or ComponentLibrary()
        self.on_generate = on_generate
        self.window = tk.Toplevel(parent)
        self.window.title("Build an assembly")
        self.window.geometry("1180x760")
        self.window.minsize(900, 600)
        self.window.lift()

        self.assembly_id: int | None = None
        self.revision_id: int | None = None
        self.assembly_name = ""
        self.shell_digest = ""
        self.items: list[dict] = []
        self._next_item_key = 1
        self.saved_snapshot = None
        self.preview_as_variable = tk.StringVar(
            master=self.window, value="All alternatives"
        )
        self.preview_choice_values = {"All alternatives": None}

        self.name_variable = tk.StringVar(master=self.window)
        self.shell_variable = tk.StringVar(master=self.window, value=NO_SHELL)
        self.library_search_variable = tk.StringVar(master=self.window)
        self._build_widgets()
        self._populate_library()
        self._load_last_shell()
        self.saved_snapshot = self._snapshot()
        self._refresh_preview()

    def _build_widgets(self):
        outer = ttk.Frame(self.window, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        ttk.Label(
            outer, text="Build an assembly", font=("TkDefaultFont", 15, "bold")
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text=(
                "Name the assembly, choose a page layout file, add and order saved "
                "components, and omit optional wording without removing it from the recipe."
            ),
            wraplength=1100,
        ).grid(row=1, column=0, sticky="w", pady=(3, 10))

        details = ttk.Frame(outer)
        details.grid(row=2, column=0, sticky="nsew")
        details.columnconfigure(0, weight=1)

        top = ttk.Frame(details)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Assembly name").grid(row=0, column=0, sticky="w")
        self.name_variable.trace_add("write", self._name_changed_hint)
        self.name_entry = ttk.Entry(top, textvariable=self.name_variable)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        shell_row = ttk.Frame(details)
        shell_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        shell_row.columnconfigure(1, weight=1)
        ttk.Label(shell_row, text="Page layout file").grid(row=0, column=0, sticky="w")
        ttk.Label(
            shell_row, textvariable=self.shell_variable, wraplength=700
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(
            shell_row, text="Choose page layout file…", command=self.choose_shell
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))
        ttk.Label(
            shell_row,
            text=(
                "A Word document (a .docx or .dotx you already use) that supplies the "
                "page size, fonts, headers and footers. Its own wording is not used."
            ),
            foreground="#555555", wraplength=900,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 0))

        content = ttk.Panedwindow(details, orient="horizontal")
        content.grid(row=2, column=0, sticky="nsew")
        details.rowconfigure(2, weight=1)

        library_frame = ttk.LabelFrame(content, text="Component library", padding=8)
        library_frame.columnconfigure(0, weight=1)
        library_frame.rowconfigure(1, weight=1)
        content.add(library_frame, weight=1)

        search_row = ttk.Frame(library_frame)
        search_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        search_row.columnconfigure(0, weight=1)
        search_entry = ttk.Entry(
            search_row, textvariable=self.library_search_variable
        )
        search_entry.grid(row=0, column=0, sticky="ew")
        search_entry.bind("<Return>", lambda _event: self._populate_library())
        ttk.Button(
            search_row, text="Search", command=self._populate_library
        ).grid(row=0, column=1, padx=(5, 0))

        self.library_tree = ttk.Treeview(
            library_frame, columns=("name", "category"), show="headings",
            selectmode="browse",
        )
        self.library_tree.heading("name", text="Name")
        self.library_tree.heading("category", text="Category")
        self.library_tree.column("name", width=150, anchor="w")
        self.library_tree.column("category", width=100, anchor="w")
        self.library_tree.grid(row=1, column=0, sticky="nsew")
        library_scroll = ttk.Scrollbar(
            library_frame, orient="vertical", command=self.library_tree.yview
        )
        library_scroll.grid(row=1, column=1, sticky="ns")
        self.library_tree.configure(yscrollcommand=library_scroll.set)
        self.library_tree.bind("<Double-1>", self._add_selected_component)
        ttk.Button(
            library_frame, text="Add selected component →",
            command=self._add_selected_component,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(7, 0))

        right = ttk.Frame(content)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        content.add(right, weight=3)
        right_panes = ttk.Panedwindow(right, orient="vertical")
        right_panes.grid(row=0, column=0, sticky="nsew")

        assembly_frame = ttk.LabelFrame(
            right_panes, text="Assembly order", padding=8
        )
        assembly_frame.columnconfigure(0, weight=1)
        assembly_frame.rowconfigure(0, weight=1)
        right_panes.add(assembly_frame, weight=1)

        self.assembly_tree = ttk.Treeview(
            assembly_frame, columns=("include", "name", "version"),
            show="headings", selectmode="browse",
        )
        self.assembly_tree.heading("include", text="Include")
        self.assembly_tree.heading("name", text="Component")
        self.assembly_tree.heading("version", text="Version")
        self.assembly_tree.column("include", width=66, anchor="center", stretch=False)
        self.assembly_tree.column("name", width=260, anchor="w")
        self.assembly_tree.column("version", width=72, anchor="center", stretch=False)
        self.assembly_tree.grid(row=0, column=0, sticky="nsew")
        assembly_scroll = ttk.Scrollbar(
            assembly_frame, orient="vertical", command=self.assembly_tree.yview
        )
        assembly_scroll.grid(row=0, column=1, sticky="ns")
        self.assembly_tree.configure(yscrollcommand=assembly_scroll.set)
        self.assembly_tree.bind("<Button-1>", self._toggle_include_cell)

        controls = ttk.Frame(assembly_frame)
        controls.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(7, 0))
        ttk.Button(controls, text="Move up", command=lambda: self._move_selected(-1)).pack(side="left")
        ttk.Button(controls, text="Move down", command=lambda: self._move_selected(1)).pack(side="left", padx=(5, 0))
        ttk.Button(controls, text="Remove", command=self._remove_selected).pack(side="left", padx=(5, 0))
        ttk.Label(
            controls, text="Click Include to tick or untick an optional component.",
            foreground="#555555",
        ).pack(side="right")

        preview_frame = ttk.LabelFrame(
            right_panes, text="Complete assembly preview", padding=8
        )
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(2, weight=1)
        right_panes.add(preview_frame, weight=3)

        preview_controls = ttk.Frame(preview_frame)
        preview_controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        ttk.Label(preview_controls, text="Preview as").pack(side="left")
        self.preview_as_box = ttk.Combobox(
            preview_controls,
            textvariable=self.preview_as_variable,
            values=("All alternatives",),
            state="disabled",
            width=38,
        )
        self.preview_as_box.pack(side="left", padx=(7, 0))
        self.preview_as_box.bind("<<ComboboxSelected>>", self._refresh_preview)

        self.preview_warning = ttk.Label(
            preview_frame, text="", foreground="#8a5a00",
            wraplength=760, justify="left",
        )
        self.preview_warning.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 5)
        )

        self.preview = tk.Text(
            preview_frame, wrap="word", state="disabled",
            font="TkDefaultFont", relief="solid", borderwidth=1,
            padx=8, pady=7, cursor="arrow",
        )
        self.preview.grid(row=2, column=0, sticky="nsew")
        preview_scroll = ttk.Scrollbar(
            preview_frame, orient="vertical", command=self.preview.yview
        )
        preview_scroll.grid(row=2, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=preview_scroll.set)
        self._configure_preview_tags()
        ttk.Label(
            preview_frame,
            text="Word decides the final page layout.",
            foreground="#555555",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 0))
        ttk.Label(
            preview_frame, text=PREVIEW_KEY, foreground="#555555", wraplength=760,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(3, 0))

        footer = ttk.Frame(outer)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        # The message gets its own full-width, wrapping line above the buttons.
        # Beside the buttons, a long message took all the width and pushed
        # Save assembly off the window.
        self.status = ttk.Label(
            footer, text="Start by choosing a page layout file (button above the lists).",
            justify="left", wraplength=800,
        )
        self.status.pack(side="top", fill="x", anchor="w", pady=(0, 6))
        footer.bind(
            "<Configure>",
            lambda event: self.status.configure(wraplength=max(200, event.width - 20)),
        )
        buttons = ttk.Frame(footer)
        buttons.pack(side="top", fill="x")
        ttk.Button(buttons, text="Close", command=self.window.destroy).pack(side="right")
        ttk.Button(
            buttons, text="Save assembly…", command=self.save_assembly
        ).pack(side="right", padx=(0, 7))
        self.updates_button = ttk.Button(
            buttons, text="Review updates…", command=self.review_updates, state="disabled"
        )
        self.updates_button.pack(side="right", padx=(0, 7))
        self.generate_button = ttk.Button(
            buttons, text="Fill fields and create document…",
            command=self.generate_document,
            state="normal" if self.on_generate is not None else "disabled",
        )
        self.generate_button.pack(side="right", padx=(0, 7))
        ttk.Button(
            buttons, text="Open saved…", command=self.open_saved_assembly
        ).pack(side="right", padx=(0, 7))

    def _configure_preview_tags(self):
        configure_preview_tags(self.preview)

    def _load_last_shell(self):
        remembered = shell_selection.last_shell()
        if remembered is None:
            return
        try:
            selection = shell_selection.choose_shell(remembered, remember=False)
            if selection.usable:
                self._set_shell(remembered, selection.lines)
        except (OSError, ValueError):
            return

    def _set_shell(self, path: str | Path, notes: Sequence[str] = ()):
        shell = Path(path)
        digest = shell_file_sha256(shell)
        self.shell_digest = digest
        self.shell_variable.set(str(shell))
        if notes:
            self.status.configure(text=" ".join(notes))
        else:
            self.status.configure(text="Page layout ready. Add components to the assembly.")

    def choose_shell(self):
        selected = filedialog.askopenfilename(
            parent=self.window,
            title="Choose a page layout file (a Word document)",
            filetypes=[
                ("Word documents and templates", "*.docx *.dotx"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return
        try:
            check = shell_selection.choose_shell(selected, remember=False)
            if not check.usable:
                messagebox.showerror(
                    "This page layout file cannot be used",
                    "\n".join(check.lines),
                    parent=self.window,
                )
                return
            if check.needs_review and not confirm_layout_file(self.window, check.lines):
                return
            chosen = shell_selection.choose_shell(selected, remember=True)
            self._set_shell(selected, chosen.lines)
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror(
                "Could not use this page layout file", str(exc), parent=self.window
            )

    def _populate_library(self):
        query = self.library_search_variable.get().strip()
        components = (
            self.library.search_components(query)
            if query else self.library.list_components()
        )
        for row in self.library_tree.get_children():
            self.library_tree.delete(row)
        for component in components:
            self.library_tree.insert(
                "", "end", iid=str(component["id"]),
                values=(component["name"], component["category"]),
            )

    def _add_selected_component(self, _event=None):
        selected = self.library_tree.selection()
        if not selected:
            return
        component_id = int(selected[0])
        component = self.library.get_component(component_id)
        versions = self.library.list_component_versions(component_id)
        if component is None or component["status"] != "active" or not versions:
            messagebox.showerror(
                "Could not add component",
                "The selected component is no longer available.",
                parent=self.window,
            )
            self._populate_library()
            return
        duplicates = [
            item for item in self.items
            if item["component_id"] == component_id
        ]
        if duplicates and not messagebox.askyesno(
            "Add this component again?",
            (
                f"{component['name']} is already in this assembly. "
                "Add another copy at the end?"
            ),
            parent=self.window,
        ):
            return
        latest = versions[0]
        self.items.append(
            {
                "key": self._next_item_key,
                "component_id": component_id,
                "component_version_id": int(latest["id"]),
                "component_name": component["name"],
                "component_version_number": int(latest["number"]),
                "markdown": latest["markdown"],
                "paragraph_styles": list(latest.get("paragraph_styles") or []),
                "included": True,
            }
        )
        key = self._next_item_key
        self._next_item_key += 1
        self._render_items(key)

    def _selected_item_index(self):
        selected = self.assembly_tree.selection()
        if not selected:
            return None
        key = int(selected[0])
        for index, item in enumerate(self.items):
            if item["key"] == key:
                return index
        return None

    def _render_items(self, selected_key: int | None = None):
        for row in self.assembly_tree.get_children():
            self.assembly_tree.delete(row)
        for item in self.items:
            self.assembly_tree.insert(
                "", "end", iid=str(item["key"]),
                values=(
                    "☑" if item["included"] else "☐",
                    item["component_name"],
                    f"v{item['component_version_number']}",
                ),
            )
        if selected_key is not None and self.assembly_tree.exists(str(selected_key)):
            self.assembly_tree.selection_set(str(selected_key))
            self.assembly_tree.focus(str(selected_key))
        self._refresh_preview()

    def _toggle_include_cell(self, event):
        if (
            self.assembly_tree.identify_region(event.x, event.y) != "cell"
            or self.assembly_tree.identify_column(event.x) != "#1"
        ):
            return
        row = self.assembly_tree.identify_row(event.y)
        if not row:
            return
        key = int(row)
        for item in self.items:
            if item["key"] == key:
                item["included"] = not item["included"]
                self._render_items(key)
                break

    def _move_selected(self, direction: int):
        index = self._selected_item_index()
        if index is None:
            return
        target = index + direction
        if target < 0 or target >= len(self.items):
            return
        self.items[index], self.items[target] = self.items[target], self.items[index]
        self._render_items(self.items[target]["key"])

    def _remove_selected(self):
        index = self._selected_item_index()
        if index is None:
            return
        del self.items[index]
        selected_key = None
        if self.items:
            selected_key = self.items[min(index, len(self.items) - 1)]["key"]
        self._render_items(selected_key)

    def _refresh_preview(self, _event=None):
        included = [item for item in self.items if bool(item.get("included", True))]
        choices = conditional_preview_choices(included)
        choice_values = {"All alternatives": None}
        labels = ["All alternatives"]
        for field_name, value in choices:
            display_value = (
                "filled in" if value is True
                else "not filled in" if value is False
                else str(value)
            )
            label = f"{field_name} — {display_value}"
            choice_values[label] = {field_name: value}
            labels.append(label)
        self.preview_choice_values = choice_values
        self.preview_as_box.configure(
            values=labels,
            state="readonly" if len(labels) > 1 else "disabled",
        )
        if self.preview_as_variable.get() not in choice_values:
            self.preview_as_variable.set("All alternatives")
        preview_values = choice_values[self.preview_as_variable.get()]

        warnings = []
        for item in included:
            component_name = str(item.get("component_name") or "Component")
            for warning in conditional_preview_warnings(
                str(item.get("markdown") or "")
            ):
                warnings.append(f"{component_name}: {warning}")
        self.preview_warning.configure(text="\n".join(warnings))

        segments = preview_segments_for_components(
            self.items, preview_values=preview_values
        )
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        if not segments:
            self.preview.insert(
                "1.0",
                "Add components and include the wording you want to review.",
                ("source_text",),
            )
        else:
            for text, tags in segments:
                self.preview.insert("end", text, tags)
        self.preview.configure(state="disabled")

    def generate_document(self):
        """Compose the current draft and open the shared field-entry workflow."""
        if self.on_generate is None:
            return
        shell_text = self.shell_variable.get()
        if not self.shell_digest or not shell_text or shell_text == NO_SHELL:
            messagebox.showerror(
                "Choose a shell first",
                "Choose a usable page layout file (the button next to \"Page layout file\") before creating the document.",
                parent=self.window,
            )
            return
        shell_path = Path(shell_text)
        try:
            if not shell_path.is_file():
                raise OSError("The selected shell file no longer exists. Choose it again.")
            if shell_file_sha256(shell_path) != self.shell_digest:
                raise OSError(
                    "The selected shell has changed since it was checked. "
                    "Choose it again before generating a document."
                )
        except OSError as exc:
            messagebox.showerror("The shell is unavailable", str(exc), parent=self.window)
            return
        components = [
            ComponentText(str(item["markdown"]), tuple(item.get("paragraph_styles") or ()))
            for item in self.items if item["included"]
        ]
        if not components:
            messagebox.showerror(
                "Nothing included",
                "Add and include at least one component before generating a document.",
                parent=self.window,
            )
            return
        try:
            self.on_generate(shell_path, components, self.name_variable.get().strip())
        except (ValueError, TypeError, OSError, sqlite3.Error) as exc:
            messagebox.showerror(
                "Could not prepare the document", str(exc), parent=self.window
            )

    def _snapshot(self):
        return (
            self.name_variable.get(),
            self.shell_variable.get(),
            self.shell_digest,
            tuple(
                (
                    item["component_version_id"],
                    item["included"],
                    item["component_name"],
                    item["markdown"],
                    tuple(item.get("paragraph_styles") or ()),
                )
                for item in self.items
            ),
        )

    def _has_content(self):
        # A remembered or newly chosen shell alone is not an assembly draft.
        # Do not ask users to save an empty recipe when they are only opening
        # an existing assembly.
        return bool(
            self.assembly_id is not None
            or self.name_variable.get().strip()
            or self.items
        )

    def _confirm_replace(self):
        if not self._has_content() or self.saved_snapshot == self._snapshot():
            return True
        choice = messagebox.askyesnocancel(
            "Unsaved assembly changes",
            (
                "This assembly has unsaved changes. Save them before opening "
                "another assembly?\n\nChoose Yes to save, No to discard, or "
                "Cancel to stay here."
            ),
            parent=self.window,
        )
        if choice is None:
            return False
        if choice:
            return self.save_assembly()
        return True

    def save_assembly(self):
        name = self.name_variable.get().strip()
        if not name:
            messagebox.showerror(
                "Assembly name required",
                "Enter a name for this assembly before saving it.",
                parent=self.window,
            )
            return False
        shell_text = self.shell_variable.get()
        if not self.shell_digest or not shell_text or shell_text == NO_SHELL:
            messagebox.showerror(
                "Choose a shell first",
                "Choose a usable page layout file (the button next to \"Page layout file\") before saving the assembly.",
                parent=self.window,
            )
            return False
        shell_path = Path(shell_text)
        try:
            if not shell_path.is_file():
                raise OSError("The selected shell file no longer exists. Choose it again.")
            current_digest = shell_file_sha256(shell_path)
            if current_digest != self.shell_digest:
                raise OSError(
                    "The selected shell has changed since it was checked. "
                    "Choose it again so the new revision records its current contents."
                )
        except OSError as exc:
            messagebox.showerror("The shell is unavailable", str(exc), parent=self.window)
            return False

        if not self.items:
            messagebox.showerror(
                "No components",
                "Add at least one component before saving the assembly.",
                parent=self.window,
            )
            return False
        if not any(item["included"] for item in self.items):
            messagebox.showerror(
                "Nothing included",
                "Include at least one component in the assembly.",
                parent=self.window,
            )
            return False

        mappings = [
            {
                "component_version_id": item["component_version_id"],
                "included": bool(item["included"]),
            }
            for item in self.items
        ]
        # An existing assembly saved under a different name becomes a NEW assembly
        # (a copy made from it); the original is left exactly as it was. A change
        # of capitals or spacing alone is still the same assembly.
        previous_name = self.assembly_name
        copy_of_existing = (
            self.assembly_id is not None
            and _name_key(name) != _name_key(previous_name)
        )
        new_assembly = self.assembly_id is None or copy_of_existing
        try:
            if new_assembly:
                assembly_id = self.library.create_assembly(name)
                try:
                    revision = self.library.save_assembly_revision(
                        assembly_id, str(shell_path), self.shell_digest, mappings
                    )
                except Exception:
                    # Do not leave a failed, empty draft in the normal assembly list.
                    self.library.archive_assembly(assembly_id)
                    raise
            else:
                revision = self.library.save_assembly_revision(
                    self.assembly_id, str(shell_path), self.shell_digest, mappings
                )
                assembly_id = self.assembly_id
        except (ValueError, TypeError, OSError, sqlite3.Error) as exc:
            messagebox.showerror(
                "Could not save assembly", str(exc), parent=self.window
            )
            return False

        self.assembly_id = int(assembly_id)
        self.revision_id = int(revision["id"])
        self.assembly_name = name
        self.saved_snapshot = self._snapshot()
        if copy_of_existing:
            self._refresh_newer_versions(
                f"Saved as a new assembly, {name} · revision {revision['number']}. "
                f"{previous_name} was not changed."
            )
        else:
            self._refresh_newer_versions(f"Saved {name} · revision {revision['number']}.")
        return True

    def _name_changed_hint(self, *_args):
        """Tell the user, before they save, that a new name makes a new assembly."""
        if self.assembly_id is None or not hasattr(self, "status"):
            return
        name = self.name_variable.get().strip()
        if name and _name_key(name) != _name_key(self.assembly_name):
            self.status.configure(
                text=f"Saving will create a new assembly named {name}; "
                     f"{self.assembly_name} will stay as it is."
            )


    def _refresh_newer_versions(self, prefix: str = ""):
        """Show which pinned items have newer saved options; never apply them."""
        for item in self.items:
            item["newer_versions"] = []
        if self.revision_id is None:
            self.updates_button.configure(state="disabled")
            if prefix:
                self.status.configure(text=prefix)
            return
        try:
            rows = self.library.list_newer_versions_for_revision(self.revision_id)
        except (ValueError, sqlite3.Error) as exc:
            self.updates_button.configure(state="disabled")
            self.status.configure(text=f"{prefix} Could not check newer versions: {exc}".strip())
            return

        available = []
        for row in rows:
            position = int(row["position"])
            if position >= len(self.items):
                continue
            versions = row["newer_versions"]
            self.items[position]["newer_versions"] = versions
            if versions:
                available.append(
                    f"{row['component_name']} (v{row['pinned_number']} → v{versions[-1]['number']})"
                )
        self.updates_button.configure(state="normal" if available else "disabled")
        if available:
            self.status.configure(
                text=(prefix + " Newer wording is available but has NOT been applied: "
                      + "; ".join(available)
                      + ". Choose Review updates to compare versions.").strip()
            )
        elif prefix:
            self.status.configure(text=prefix)

    def review_updates(self):
        return assembly_review_dialog.review_updates(self)

    def open_saved_assembly(self):
        return assembly_open_dialog.open_saved_assembly(self)

    def _load_revision(self, revision):
        return assembly_open_dialog.load_revision(self, revision)
