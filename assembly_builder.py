"""User interface for arranging, previewing and saving component assemblies.

The window is loaded only when the user opens the assembly workflow. The saved
recipe pins immutable component versions and never rewrites the Word shell.
"""
from __future__ import annotations

import difflib
import hashlib
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Mapping, Sequence

from component_preview import render_markdown_preview
from library import ComponentLibrary
import shell_selection


def included_component_markdown(revision: Mapping[str, object]) -> list[str]:
    """Return included Markdown sources in saved order, without joining them.

    Keeping each component as a separate source is important: field protection
    and Markdown parsing must happen per component so brace fragments at a
    component boundary cannot accidentally form a field.
    """
    components = revision.get("components", ())
    if not isinstance(components, Sequence) or isinstance(components, (str, bytes)):
        raise TypeError("A saved assembly must contain an ordered component list.")
    return [
        str(component["markdown"])
        for component in components
        if bool(component.get("included", True))
    ]


def preview_segments_for_components(components: Sequence[Mapping[str, object]]):
    """Render one ordered preview while parsing each component independently."""
    segments = []
    visible = 0
    for component in components:
        if not bool(component.get("included", True)):
            continue
        if visible:
            segments.append(("\n\n", ()))
        label = str(component.get("component_name") or "Component")
        number = component.get("component_version_number")
        if number is not None:
            label += f" · version {number}"
        segments.append((label + "\n", ("component_label",)))
        segments.extend(render_markdown_preview(str(component.get("markdown") or "")))
        visible += 1
    return segments


def shell_file_sha256(path: str | Path) -> str:
    """Hash a shell incrementally so even a large file is not read at once."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compose_assembly_template(shell_path, components, output_path):
    """Compose a temporary DOCX, then discover its unique fields with core.Template."""
    included = list(components)
    if not included:
        raise ValueError("Include at least one component before generating a document.")
    from docx_compose import compose_document
    import core

    composition = compose_document(shell_path, included, output_path)
    return core.Template(output_path), composition


def version_diff_lines(old_markdown: str, new_markdown: str) -> list[str]:
    """Return a readable unified diff for pinned and proposed component wording."""
    return list(difflib.unified_diff(
        str(old_markdown).splitlines(),
        str(new_markdown).splitlines(),
        fromfile="Pinned wording",
        tofile="Proposed wording",
        lineterm="",
    ))


def update_component_items(items, selections):
    """Apply only explicit, validated version selections to an ordered recipe."""
    updated = []
    for original in items:
        item = dict(original)
        key = int(item["key"])
        selected = selections.get(key)
        if selected is not None:
            if int(selected["component_id"]) != int(item["component_id"]):
                raise ValueError("A selected version belongs to a different component.")
            if int(selected["number"]) <= int(item["component_version_number"]):
                raise ValueError("Choose a version newer than the currently pinned wording.")
            item.update(
                component_version_id=int(selected["id"]),
                component_version_number=int(selected["number"]),
                markdown=str(selected["markdown"]),
            )
        updated.append(item)
    return updated


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
        self.window.transient(parent)

        self.assembly_id: int | None = None
        self.revision_id: int | None = None
        self.assembly_name = ""
        self.shell_digest = ""
        self.items: list[dict] = []
        self._next_item_key = 1
        self.saved_snapshot = None

        self.name_variable = tk.StringVar(master=self.window)
        self.shell_variable = tk.StringVar(master=self.window, value="No shell chosen")
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
                "Choose a Word shell, add and order saved components, and omit "
                "optional wording without removing it from the recipe."
            ),
            wraplength=1100,
        ).grid(row=1, column=0, sticky="w", pady=(3, 10))

        details = ttk.Frame(outer)
        details.grid(row=2, column=0, sticky="nsew")
        details.columnconfigure(0, weight=1)
        details.rowconfigure(0, weight=1)

        top = ttk.Frame(details)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Assembly name").grid(row=0, column=0, sticky="w")
        self.name_entry = ttk.Entry(top, textvariable=self.name_variable)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=(8, 16))
        ttk.Button(top, text="Choose shell…", command=self.choose_shell).grid(
            row=0, column=2, sticky="e"
        )

        shell_row = ttk.Frame(details)
        shell_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        shell_row.columnconfigure(1, weight=1)
        ttk.Label(shell_row, text="Word shell").grid(row=0, column=0, sticky="w")
        ttk.Label(
            shell_row, textvariable=self.shell_variable, wraplength=850
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))

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
        preview_frame.rowconfigure(0, weight=1)
        right_panes.add(preview_frame, weight=3)
        self.preview = tk.Text(
            preview_frame, wrap="word", state="disabled",
            font="TkDefaultFont", relief="solid", borderwidth=1,
            padx=8, pady=7, cursor="arrow",
        )
        self.preview.grid(row=0, column=0, sticky="nsew")
        preview_scroll = ttk.Scrollbar(
            preview_frame, orient="vertical", command=self.preview.yview
        )
        preview_scroll.grid(row=0, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=preview_scroll.set)
        self._configure_preview_tags()
        ttk.Label(
            preview_frame,
            text="Word decides the final page layout. Fields are highlighted.",
            foreground="#555555",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))

        footer = ttk.Frame(outer)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.status = ttk.Label(footer, text="Choose a Word shell to begin.")
        self.status.pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Close", command=self.window.destroy).pack(side="right")
        ttk.Button(
            footer, text="Save assembly…", command=self.save_assembly
        ).pack(side="right", padx=(0, 7))
        self.updates_button = ttk.Button(
            footer, text="Review updates…", command=self.review_updates, state="disabled"
        )
        self.updates_button.pack(side="right", padx=(0, 7))
        self.generate_button = ttk.Button(
            footer, text="Fill fields and create document…",
            command=self.generate_document,
            state="normal" if self.on_generate is not None else "disabled",
        )
        self.generate_button.pack(side="right", padx=(0, 7))
        ttk.Button(
            footer, text="Open saved…", command=self.open_saved_assembly
        ).pack(side="right", padx=(0, 7))

    def _configure_preview_tags(self):
        self.preview.tag_configure(
            "heading_1", font=("TkDefaultFont", 17, "bold"),
            spacing1=10, spacing3=6,
        )
        self.preview.tag_configure(
            "heading_2", font=("TkDefaultFont", 14, "bold"),
            spacing1=8, spacing3=5,
        )
        self.preview.tag_configure(
            "heading_3", font=("TkDefaultFont", 12, "bold"),
            spacing1=6, spacing3=4,
        )
        self.preview.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))
        self.preview.tag_configure("italic", font=("TkDefaultFont", 10, "italic"))
        self.preview.tag_configure(
            "field", background="#fff0c2", foreground="#714d00"
        )
        self.preview.tag_configure("list_marker", foreground="#555555")
        self.preview.tag_configure(
            "table_header", font=("TkDefaultFont", 9, "bold"),
            background="#eeeeee",
        )
        self.preview.tag_configure("table_cell", font=("TkFixedFont", 9))
        self.preview.tag_configure(
            "table_border", foreground="#777777", font=("TkFixedFont", 9)
        )
        self.preview.tag_configure(
            "code", font=("TkFixedFont", 9), background="#f1f1f1"
        )
        self.preview.tag_configure(
            "code_block", font=("TkFixedFont", 9), background="#f4f4f4",
            lmargin1=8, lmargin2=8,
        )
        self.preview.tag_configure("blockquote", foreground="#555555", lmargin1=12)
        self.preview.tag_configure("link", underline=True, foreground="#245a8d")
        self.preview.tag_configure("rule", foreground="#888888")
        self.preview.tag_configure("source_text", foreground="#666666")
        self.preview.tag_configure(
            "component_label", foreground="#555555",
            font=("TkDefaultFont", 9, "bold"), spacing1=9, spacing3=3,
        )

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
            self.status.configure(text="Shell ready. Add components to the assembly.")

    def choose_shell(self):
        selected = filedialog.askopenfilename(
            parent=self.window,
            title="Choose a Word document shell",
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
                    "This shell cannot be used",
                    "\n".join(check.lines),
                    parent=self.window,
                )
                return
            if check.result.warnings and not messagebox.askyesno(
                "Review shell warnings",
                "\n".join(check.lines) + "\n\nUse this shell anyway?",
                parent=self.window,
            ):
                return
            chosen = shell_selection.choose_shell(selected, remember=True)
            self._set_shell(selected, chosen.lines)
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror(
                "Could not choose this shell", str(exc), parent=self.window
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

    def _refresh_preview(self):
        segments = preview_segments_for_components(self.items)
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
        if not self.shell_digest or not shell_text or shell_text == "No shell chosen":
            messagebox.showerror(
                "Choose a shell first",
                "Choose a usable Word shell before generating the document.",
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
        components = [str(item["markdown"]) for item in self.items if item["included"]]
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
        if not self.shell_digest or not shell_text or shell_text == "No shell chosen":
            messagebox.showerror(
                "Choose a shell first",
                "Choose a usable Word shell before saving the assembly.",
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
        new_assembly = self.assembly_id is None
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
        self.name_entry.configure(state="readonly")
        self.saved_snapshot = self._snapshot()
        self._refresh_newer_versions(f"Saved {name} · revision {revision['number']}.")
        return True



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
        """Compare pinned wording with newer options; save only checked choices."""
        pending = [item for item in self.items if item.get("newer_versions")]
        if not pending:
            messagebox.showinfo(
                "No newer versions",
                "Every component in this revision is already at its latest saved version.",
                parent=self.window,
            )
            return

        dialog = tk.Toplevel(self.window)
        dialog.title("Review component updates")
        dialog.geometry("980x650")
        dialog.minsize(760, 480)
        dialog.transient(self.window)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        ttk.Label(
            dialog,
            text=("New wording is available for the pinned components below. "
                  "Nothing changes unless you tick an item and save the selected updates."),
            wraplength=940,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

        body = ttk.Panedwindow(dialog, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew", padx=12)
        left = ttk.LabelFrame(body, text="Pinned components", padding=7)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        body.add(left, weight=2)
        tree = ttk.Treeview(
            left, columns=("update", "component", "pinned", "latest"),
            show="headings", selectmode="browse",
        )
        for column, label, width in (
            ("update", "Update", 62), ("component", "Component", 170),
            ("pinned", "Pinned", 66), ("latest", "Latest", 66),
        ):
            tree.heading(column, text=label)
            tree.column(
                column, width=width,
                anchor="center" if column != "component" else "w",
                stretch=column == "component",
            )
        tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(left, orient="vertical", command=tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=tree_scroll.set)

        right = ttk.LabelFrame(body, text="Wording changes", padding=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        body.add(right, weight=3)
        ttk.Label(right, text="Compare the pinned wording with a newer version:").grid(
            row=0, column=0, sticky="w"
        )
        version_variable = tk.StringVar(master=dialog)
        version_combo = ttk.Combobox(
            right, textvariable=version_variable, state="readonly", width=36
        )
        version_combo.grid(row=1, column=0, sticky="w", pady=(5, 7))
        diff_text = tk.Text(
            right, wrap="none", state="disabled", font="TkFixedFont", padx=7, pady=6
        )
        diff_text.grid(row=2, column=0, sticky="nsew")
        diff_y = ttk.Scrollbar(right, orient="vertical", command=diff_text.yview)
        diff_y.grid(row=2, column=1, sticky="ns")
        diff_text.configure(yscrollcommand=diff_y.set)
        diff_x = ttk.Scrollbar(right, orient="horizontal", command=diff_text.xview)
        diff_x.grid(row=3, column=0, sticky="ew")
        diff_text.configure(xscrollcommand=diff_x.set)
        diff_text.tag_configure("added", foreground="#16733b", background="#eaf6ee")
        diff_text.tag_configure("removed", foreground="#a32626", background="#faeeee")
        diff_text.tag_configure(
            "header", foreground="#555555", font=("TkFixedFont", 9, "bold")
        )

        by_key = {int(item["key"]): item for item in pending}
        choices = {key: item["newer_versions"][-1] for key, item in by_key.items()}
        checked: set[int] = set()

        def show_diff(_event=None):
            selection = tree.selection()
            if not selection:
                return
            key = int(selection[0])
            item = by_key.get(key)
            if item is None:
                return
            versions = item["newer_versions"]
            labels = [
                f"v{version['number']} · {version['created'][:10]}"
                for version in versions
            ]
            by_label = dict(zip(labels, versions))
            version_combo.configure(values=labels)
            chosen = choices.get(key, versions[-1])
            version_variable.set(next(
                (label for label, version in by_label.items()
                 if int(version["id"]) == int(chosen["id"])),
                labels[-1],
            ))

            def draw():
                selected = by_label.get(version_variable.get(), versions[-1])
                choices[key] = selected
                diff_text.configure(state="normal")
                diff_text.delete("1.0", "end")
                lines = version_diff_lines(item["markdown"], selected["markdown"])
                for line in lines or ["No wording changes."]:
                    if line.startswith("+") and not line.startswith("+++"):
                        tag = "added"
                    elif line.startswith("-") and not line.startswith("---"):
                        tag = "removed"
                    elif line.startswith(("---", "+++", "@@")):
                        tag = "header"
                    else:
                        tag = ""
                    diff_text.insert("end", line + "\n", (tag,) if tag else ())
                diff_text.configure(state="disabled")

            draw()
            version_combo.bind("<<ComboboxSelected>>", draw)

        def toggle_update(event):
            if (tree.identify_region(event.x, event.y) != "cell"
                    or tree.identify_column(event.x) != "#1"):
                return
            row = tree.identify_row(event.y)
            if not row:
                return
            key = int(row)
            if key in checked:
                checked.remove(key)
            else:
                checked.add(key)
            tree.set(key, "update", "☑" if key in checked else "☐")

        for item in pending:
            key = int(item["key"])
            tree.insert(
                "", "end", iid=str(key),
                values=(
                    "☐", item["component_name"],
                    f"v{item['component_version_number']}",
                    f"v{item['newer_versions'][-1]['number']}",
                ),
            )
        tree.bind("<<TreeviewSelect>>", show_diff)
        tree.bind("<Button-1>", toggle_update)
        tree.selection_set(str(pending[0]["key"]))
        show_diff()

        def save_selected():
            if not checked:
                messagebox.showinfo(
                    "No updates selected",
                    "Tick at least one component whose newer wording you want to use.",
                    parent=dialog,
                )
                return
            try:
                revised = update_component_items(
                    self.items, {key: choices[key] for key in checked}
                )
            except (KeyError, TypeError, ValueError) as exc:
                messagebox.showerror("Could not apply updates", str(exc), parent=dialog)
                return
            previous = self.items
            self.items = revised
            if not self.save_assembly():
                self.items = previous
                self._render_items()
                return
            dialog.destroy()

        actions = ttk.Frame(dialog, padding=12)
        actions.grid(row=2, column=0, sticky="ew")
        ttk.Label(
            actions,
            text="Saving creates a new revision; earlier revisions remain unchanged.",
            foreground="#555555",
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(actions, text="Cancel", command=dialog.destroy).pack(side="right")
        ttk.Button(
            actions, text="Save selected updates", command=save_selected
        ).pack(side="right", padx=(0, 7))


    def open_saved_assembly(self):
        if not self._confirm_replace():
            return
        choices = []
        for assembly in self.library.list_assemblies():
            for revision in self.library.list_assembly_revisions(assembly["id"]):
                if revision["finalized"]:
                    choices.append(
                        {
                            "assembly": assembly,
                            "revision": revision,
                        }
                    )
        if not choices:
            messagebox.showinfo(
                "No saved assemblies",
                "Save an assembly first. Saved assemblies will appear here.",
                parent=self.window,
            )
            return

        dialog = tk.Toplevel(self.window)
        dialog.title("Open a saved assembly")
        dialog.geometry("680x420")
        dialog.minsize(500, 300)
        dialog.transient(self.window)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        tree = ttk.Treeview(
            dialog, columns=("assembly", "revision", "saved"),
            show="headings", selectmode="browse",
        )
        tree.heading("assembly", text="Assembly")
        tree.heading("revision", text="Revision")
        tree.heading("saved", text="Saved")
        tree.column("assembly", width=300, anchor="w")
        tree.column("revision", width=90, anchor="center", stretch=False)
        tree.column("saved", width=140, anchor="w", stretch=False)
        tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        scroll = ttk.Scrollbar(dialog, orient="vertical", command=tree.yview)
        scroll.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        tree.configure(yscrollcommand=scroll.set)
        by_id = {}
        for choice in choices:
            assembly = choice["assembly"]
            revision = choice["revision"]
            key = str(revision["id"])
            by_id[key] = choice
            tree.insert(
                "", "end", iid=key,
                values=(
                    assembly["name"],
                    f"Revision {revision['number']}",
                    str(revision["created"])[:10],
                ),
            )

        def open_selected(_event=None):
            selected = tree.selection()
            if not selected:
                return
            choice = by_id.get(selected[0])
            if choice is None:
                return
            revision = self.library.get_assembly_revision(choice["revision"]["id"])
            if revision is None:
                messagebox.showerror(
                    "Assembly unavailable",
                    "That saved revision could not be read.",
                    parent=dialog,
                )
                return
            self._load_revision(revision)
            dialog.destroy()

        tree.bind("<Double-1>", open_selected)
        actions = ttk.Frame(dialog, padding=(12, 0, 12, 12))
        actions.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttk.Button(actions, text="Cancel", command=dialog.destroy).pack(side="right")
        ttk.Button(
            actions, text="Open", command=open_selected
        ).pack(side="right", padx=(0, 7))
        tree.selection_set(str(choices[0]["revision"]["id"]))

    def _load_revision(self, revision: Mapping[str, object]):
        self.assembly_id = int(revision["assembly_id"])
        self.revision_id = int(revision["id"])
        self.assembly_name = str(revision["assembly_name"])
        self.name_variable.set(self.assembly_name)
        self.name_entry.configure(state="readonly")

        shell_path = Path(str(revision["shell_path"]))
        expected_digest = str(revision["shell_sha256"])
        if shell_path.is_file():
            try:
                actual_digest = shell_file_sha256(shell_path)
            except OSError:
                actual_digest = ""
        else:
            actual_digest = ""
        if actual_digest and actual_digest == expected_digest:
            self.shell_digest = expected_digest
            self.shell_variable.set(str(shell_path))
            self.status.configure(
                text=f"Opened {self.assembly_name} · revision {revision['number']}."
            )
        else:
            self.shell_digest = ""
            self.shell_variable.set(str(shell_path))
            self.status.configure(
                text=(
                    f"Opened {self.assembly_name} · revision {revision['number']}. "
                    "Its shell is missing or has changed; choose a usable shell before saving."
                )
            )

        self.items = []
        for component in revision["components"]:
            self.items.append(
                {
                    "key": self._next_item_key,
                    "component_id": int(component["component_id"]),
                    "component_version_id": int(component["component_version_id"]),
                    "component_name": str(component["component_name"]),
                    "component_version_number": int(component["component_version_number"]),
                    "markdown": str(component["markdown"]),
                    "included": bool(component["included"]),
                }
            )
            self._next_item_key += 1
        self._render_items(self.items[0]["key"] if self.items else None)
        self.saved_snapshot = self._snapshot()
        self._refresh_newer_versions(
            f"Opened {self.assembly_name} · revision {revision['number']}."
        )

