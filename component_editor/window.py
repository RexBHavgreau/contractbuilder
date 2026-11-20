"""The Components window: library list, component details, wording and preview.

The saved-components list lives in library_list.py, the toolbar in toolbar.py
and the wording actions in wording_actions.py (all mixins of this class); dialogs are their own modules. A new window or
dialog is a new module, not more lines here.
"""
from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from component_preview import PREVIEW_KEY, render_markdown_preview
from library import ComponentLibrary

from .fields import malformed_field_message
from .history_dialog import open_version_history_dialog
from .library_list import LibraryListMixin
from .styling import configure_preview_tags
from .save_feedback import SAVE_FEEDBACK_COLORS, SAVE_FEEDBACK_SECONDS, save_feedback_text
from .text_rules import _markdown_is_editable, plain_text_to_markdown
from .toolbar import ToolbarMixin
from .wording_actions import WordingActionsMixin


class ComponentEditorWindow(LibraryListMixin, ToolbarMixin, WordingActionsMixin):
    """Manage saved components and create immutable wording versions."""

    def __init__(
        self, parent, library: ComponentLibrary | None = None,
        on_close=None, on_generate=None,
    ):
        self.parent = parent
        self.library = library or ComponentLibrary()
        self.on_close = on_close
        self.on_generate = on_generate
        self.current_component_id: int | None = None
        self.loaded_markdown: str | None = None
        self.loaded_plain_text = ""
        self.protected_content = False
        self.saved_snapshot = None
        self.suspend_selection = False
        self.assembly_builder_window = None
        self.save_button = None
        self.history_button = None
        self._preview_after_id = None
        self.editor_markdown_mode = False
        self.source_view_variable = None
        self.window = tk.Toplevel(parent)
        self.window.title("Components")
        self.window.geometry("1060x720")
        self.window.minsize(820, 570)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._feedback_after_id = None
        self._feedback_kind = None
        self._build_widgets()
        for variable in (
            self.name_variable, self.category_variable, self.tags_variable,
            self.description_variable, self.note_variable,
        ):
            variable.trace_add("write", lambda *_args: self._refresh_save_state())
        self.refresh_components()
        self.new_component(prompt=False)
        self.window.lift()

    def _build_widgets(self):
        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer, text="Components", font=("TkDefaultFont", 15, "bold")
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Create reusable contract wording. Each save keeps the previous "
                "version so existing assemblies can continue using it."
            ),
            wraplength=980,
        ).pack(anchor="w", pady=(3, 12))

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1, minsize=240)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        library_frame = ttk.LabelFrame(body, text="Saved components", padding=8)
        library_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        library_frame.columnconfigure(0, weight=1)
        library_frame.rowconfigure(2, weight=1)

        search_row = ttk.Frame(library_frame)
        search_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        search_row.columnconfigure(0, weight=1)
        self.search_variable = tk.StringVar(master=self.window)
        search_entry = ttk.Entry(search_row, textvariable=self.search_variable)
        search_entry.grid(row=0, column=0, sticky="ew")
        search_entry.bind("<Return>", lambda _event: self.refresh_components())
        ttk.Button(
            search_row, text="Search", command=self.refresh_components
        ).grid(row=0, column=1, padx=(5, 0))

        filter_row = ttk.Frame(library_frame)
        filter_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        self.category_filter_variable = tk.StringVar(
            master=self.window, value="All categories"
        )
        self.tag_filter_variable = tk.StringVar(
            master=self.window, value="All tags"
        )
        ttk.Label(filter_row, text="Category").grid(row=0, column=0, sticky="w")
        self.category_filter = ttk.Combobox(
            filter_row, textvariable=self.category_filter_variable,
            state="readonly", width=13,
        )
        self.category_filter.grid(row=1, column=0, sticky="ew", padx=(0, 5))
        self.category_filter.bind(
            "<<ComboboxSelected>>", lambda _event: self.refresh_components()
        )
        ttk.Label(filter_row, text="Tag").grid(row=0, column=1, sticky="w")
        self.tag_filter = ttk.Combobox(
            filter_row, textvariable=self.tag_filter_variable,
            state="readonly", width=12,
        )
        self.tag_filter.grid(row=1, column=1, sticky="ew", padx=(0, 5))
        self.tag_filter.bind(
            "<<ComboboxSelected>>", lambda _event: self.refresh_components()
        )
        self.show_archived_variable = tk.BooleanVar(master=self.window, value=False)
        ttk.Checkbutton(
            filter_row, text="Show archived",
            variable=self.show_archived_variable,
            command=self.refresh_components,
        ).grid(row=1, column=2, sticky="w")
        filter_row.columnconfigure(0, weight=1)
        filter_row.columnconfigure(1, weight=1)

        self.tree = ttk.Treeview(
            library_frame, columns=("name", "category", "version"), show="headings",
            selectmode="browse",
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("version", text="Version")
        self.tree.column("name", width=155, anchor="w")
        self.tree.column("category", width=115, anchor="w")
        self.tree.column("version", width=60, anchor="center")
        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree.tag_configure("archived", foreground="#777777")
        tree_scroll = ttk.Scrollbar(
            library_frame, orient="vertical", command=self.tree.yview
        )
        tree_scroll.grid(row=2, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.select_component)

        library_actions = ttk.Frame(library_frame)
        library_actions.grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )
        ttk.Button(
            library_actions, text="New component", command=self.new_component
        ).pack(side="left", fill="x", expand=True)
        self.history_button = ttk.Button(
            library_actions, text="Version history…",
            command=self.open_version_history, state="disabled",
        )
        self.history_button.pack(side="left", padx=(6, 0))

        form = ttk.LabelFrame(body, text="Component details", padding=10)
        form.grid(row=0, column=1, sticky="nsew")
        form.columnconfigure(1, weight=1)
        form.rowconfigure(4, weight=1)

        self.name_variable = tk.StringVar(master=self.window)
        self.category_variable = tk.StringVar(master=self.window)
        self.tags_variable = tk.StringVar(master=self.window)
        self.description_variable = tk.StringVar(master=self.window)
        self.note_variable = tk.StringVar(master=self.window)

        fields = (
            ("Name *", self.name_variable),
            ("Category", self.category_variable),
            ("Tags (comma-separated)", self.tags_variable),
            ("Description", self.description_variable),
        )
        for row, (label, variable) in enumerate(fields):
            ttk.Label(form, text=label).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=4
            )
            entry = ttk.Entry(form, textvariable=variable)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            if variable is self.name_variable:
                self.name_entry = entry

        text_label = ttk.Label(form, text="Wording *")
        text_label.grid(row=4, column=0, sticky="nw", padx=(0, 12), pady=(10, 4))

        panes = ttk.Panedwindow(form, orient="horizontal")
        panes.grid(row=4, column=1, sticky="nsew", pady=(10, 4))
        edit_frame = ttk.LabelFrame(panes, text="Edit wording", padding=4)
        preview_frame = ttk.LabelFrame(panes, text="Preview", padding=4)
        edit_frame.columnconfigure(0, weight=1)
        edit_frame.rowconfigure(1, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        panes.add(edit_frame, weight=1)
        panes.add(preview_frame, weight=1)

        self._build_toolbar(edit_frame)

        self.wording = tk.Text(
            edit_frame, wrap="word", undo=True, height=18, width=40,
            font="TkDefaultFont", relief="solid", borderwidth=1,
            padx=7, pady=6,
        )
        self.wording.grid(row=1, column=0, sticky="nsew")
        edit_scroll = ttk.Scrollbar(
            edit_frame, orient="vertical", command=self.wording.yview
        )
        edit_scroll.grid(row=1, column=1, sticky="ns")
        self.wording.configure(yscrollcommand=edit_scroll.set)
        # Tk's modified virtual event covers typing, paste, cut, undo, redo
        # and programmatic edits. Reset its flag so each later edit can notify.
        self.wording.bind("<<Modified>>", self._on_wording_modified)
        self.wording.bind("<Control-b>", lambda _event: self.apply_format("bold"))
        self.wording.bind("<Control-i>", lambda _event: self.apply_format("italic"))
        self.wording.bind("<KeyRelease>", self._update_toolbar_state, add="+")
        self.wording.bind("<ButtonRelease-1>", self._update_toolbar_state, add="+")
        self.wording.bind("<B1-Motion>", self._update_toolbar_state, add="+")
        self.wording.bind("<FocusIn>", self._update_toolbar_state, add="+")
        self._schedule_toolbar_layout()

        self.preview = tk.Text(
            preview_frame, wrap="word", height=18, width=40, state="disabled",
            font="TkDefaultFont", relief="solid", borderwidth=1,
            padx=7, pady=6, cursor="arrow",
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
            text="Word decides the final page layout",
            foreground="#555555",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))
        ttk.Label(
            preview_frame, text=PREVIEW_KEY, foreground="#555555", wraplength=330,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(3, 0))

        note_row = ttk.Frame(form)
        note_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        note_row.columnconfigure(1, weight=1)
        ttk.Label(note_row, text="Version note (optional)").grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )
        ttk.Entry(note_row, textvariable=self.note_variable).grid(
            row=0, column=1, sticky="ew"
        )

        self.content_notice = ttk.Label(
            form,
            text="",
            foreground="#8a5a00",
            wraplength=650,
        )
        self.content_notice.grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        feedback_row = ttk.Frame(outer)
        feedback_row.pack(fill="x", pady=(10, 0))
        self.dirty_label = ttk.Label(
            feedback_row, text="", foreground="#8a5a00"
        )
        self.dirty_label.pack(side="left", padx=(0, 10))
        self.save_feedback = ttk.Label(feedback_row, text="", foreground="#555555")
        self.save_feedback.pack(side="left", fill="x", expand=True)
        self.dismiss_button = ttk.Button(
            feedback_row, text="Dismiss", command=self._clear_save_feedback
        )

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        self.status = ttk.Label(footer, text="", foreground="#555555")
        self.status.pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Close", command=self.close).pack(side="right")
        ttk.Button(
            footer, text="Build assembly…", command=self.open_assembly_builder
        ).pack(side="right", padx=(0, 8))
        self.save_button = ttk.Button(
            footer, text="Save version", command=self.save_component
        )
        self.save_button.pack(side="right", padx=(0, 8))

    def _configure_preview_tags(self):
        configure_preview_tags(self.preview)

    def _on_wording_modified(self, _event=None):
        if not self.wording.edit_modified():
            return
        self.wording.edit_modified(False)
        self._refresh_editor_styling()
        self._refresh_save_state()
        self._update_toolbar_state()
        source = self.wording.get("1.0", "end-1c")
        if not self.editor_markdown_mode:
            source = plain_text_to_markdown(source)
        warning = malformed_field_message(source)
        if warning:
            self.content_notice.configure(text=warning)
        elif not self.protected_content:
            self.content_notice.configure(text="")
        self._schedule_preview()

    def _schedule_preview(self, _event=None):
        """Refresh after a short idle interval so keystrokes are never blocked."""
        if self._preview_after_id is not None:
            try:
                self.window.after_cancel(self._preview_after_id)
            except tk.TclError:
                pass
        try:
            self._preview_after_id = self.window.after(260, self._update_preview)
        except tk.TclError:
            self._preview_after_id = None

    def _update_preview(self):
        self._preview_after_id = None
        if not self.window.winfo_exists():
            return
        raw = self.wording.get("1.0", "end-1c")
        source = raw if self.editor_markdown_mode else plain_text_to_markdown(raw)
        warning = malformed_field_message(source)
        if warning:
            self.content_notice.configure(text=warning)
        elif not self.protected_content:
            self.content_notice.configure(text="")
        try:
            segments = render_markdown_preview(source)
        except (TypeError, ValueError) as exc:
            segments = [(f"Preview unavailable: {exc}", ("source_text",))]
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        if not segments:
            self.preview.insert("1.0", "Start typing to see a preview.", ("source_text",))
        else:
            for text, tags in segments:
                self.preview.insert("end", text, tags)
        self.preview.configure(state="disabled")

    def _state(self) -> tuple:
        return (
            self.name_variable.get(),
            self.category_variable.get(),
            self.tags_variable.get(),
            self.description_variable.get(),
            self.wording.get("1.0", "end-1c"),
            self.note_variable.get(),
        )

    def _has_unsaved_changes(self) -> bool:
        current = self._state()
        if self.saved_snapshot is None:
            return any(str(value).strip() for value in current)
        return current != self.saved_snapshot

    def _confirm_pending_changes(self, action: str) -> bool:
        if not self._has_unsaved_changes():
            return True
        save_first = messagebox.askyesnocancel(
            "Unsaved component changes",
            (
                f"You have unsaved changes. Save them before {action}?\n\n"
                "Choose Yes to save, No to discard the changes, or Cancel to stay here."
            ),
            parent=self.window,
        )
        if save_first is None:
            return False
        if save_first:
            return self.save_component()
        return True

    def _load_component(self, component_id: int):
        component = self.library.get_component(component_id)
        versions = self.library.list_component_versions(component_id)
        if component is None or not versions:
            messagebox.showerror(
                "Could not open component",
                "The selected component or its saved wording is no longer available.",
                parent=self.window,
            )
            self.refresh_components()
            return
        latest = versions[0]
        self.current_component_id = component_id
        if self.history_button is not None:
            self.history_button.configure(state="normal")
        if self.save_button is not None:
            self.save_button.configure(
                state="disabled" if component["status"] == "archived" else "normal"
            )
        self.loaded_markdown = latest["markdown"]
        self.loaded_plain_text = self.loaded_markdown
        self.editor_markdown_mode = True
        self.source_view_variable.set(False)
        self.protected_content = not _markdown_is_editable(self.loaded_markdown)
        self.name_variable.set(component["name"])
        self.category_variable.set(component["category"])
        self.tags_variable.set(", ".join(component["tags"]))
        self.description_variable.set(component["description"])
        self.note_variable.set("")
        self.wording.configure(state="normal")
        self.wording.delete("1.0", "end")
        self.wording.insert("1.0", self.loaded_markdown)
        self.wording.edit_modified(False)
        if self.protected_content:
            self.wording.configure(state="disabled")
            self.content_notice.configure(
                text=(
                    "This component includes content without safe editing controls. "
                    "Its wording is protected; create a new component or use the original Word file."
                )
            )
        else:
            self.content_notice.configure(text="")
        self._refresh_editor_styling()
        self.saved_snapshot = self._state()
        self.status.configure(
            text=f"Editing {component['name']} · version {latest['number']}."
        )
        self._schedule_preview()
        # Keep the loaded component selected, so a save shows its new version in the list.
        self.refresh_components(component_id)
        self._refresh_save_state()

    def new_component(self, prompt: bool = True):
        if prompt and not self._confirm_pending_changes("starting a new component"):
            return
        self.current_component_id = None
        self.loaded_markdown = None
        self.loaded_plain_text = ""
        self.editor_markdown_mode = False
        self.source_view_variable.set(False)
        self.protected_content = False
        self.name_variable.set("")
        self.category_variable.set("")
        self.tags_variable.set("")
        self.description_variable.set("")
        self.note_variable.set("")
        self.wording.configure(state="normal")
        self.wording.delete("1.0", "end")
        self.wording.edit_modified(False)
        self.content_notice.configure(text="")
        self._refresh_editor_styling()
        self.saved_snapshot = self._state()
        self._schedule_preview()
        selection = self.tree.selection()
        if selection:
            self.suspend_selection = True
            try:
                self.tree.selection_remove(*selection)
            finally:
                self.suspend_selection = False
        self.status.configure(text="New component.")
        self._refresh_save_state()
        if self.history_button is not None:
            self.history_button.configure(state="disabled")
        if self.save_button is not None:
            self.save_button.configure(state="normal")
        self.name_entry_focus()

    def name_entry_focus(self):
        self.name_entry.focus_set()

    def save_component(self) -> bool:
        name = self.name_variable.get().strip()
        body = self.wording.get("1.0", "end-1c")
        if not name:
            self._show_save_feedback(
                save_feedback_text("failed", error="Enter a name for this component."),
                "failed",
            )
            return False
        if not body.strip():
            self._show_save_feedback(
                save_feedback_text("failed", error="Enter the component wording before saving."),
                "failed",
            )
            return False

        if self.current_component_id is not None and not self._has_unsaved_changes():
            versions = self.library.list_component_versions(self.current_component_id)
            latest = versions[0]["number"] if versions else ""
            self._show_save_feedback(
                save_feedback_text("unchanged", name=name, version=latest), "unchanged"
            )
            return True

        if self.protected_content and body == self.loaded_plain_text:
            markdown = self.loaded_markdown or ""
        else:
            if self.protected_content:
                proceed = messagebox.askyesno(
                    "Replace existing formatting?",
                    (
                        "This component includes content the editor cannot preserve. "
                        "Saving these changes will replace that content. Continue?"
                    ),
                    parent=self.window,
                )
                if not proceed:
                    return False
            markdown = body if self.editor_markdown_mode else plain_text_to_markdown(body)
        warning = malformed_field_message(markdown)
        if warning and not messagebox.askyesno(
            "Check field placeholder", warning + "\n\nSave the wording anyway?",
            parent=self.window,
        ):
            return False

        tags = [item.strip() for item in self.tags_variable.get().split(",") if item.strip()]
        note = self.note_variable.get()
        try:
            result = self.library.save_component(
                self.current_component_id,
                name,
                markdown,
                description=self.description_variable.get(),
                category=self.category_variable.get(),
                tags=tags,
                note=note,
            )
        except (ValueError, TypeError, OSError, sqlite3.Error) as exc:
            self._show_save_feedback(save_feedback_text("failed", error=str(exc)), "failed")
            return False

        self.current_component_id = result["component_id"]
        self.note_variable.set("")
        self._load_component(self.current_component_id)
        version_number = result["version"]["number"]
        self.status.configure(text=f"Saved {name} · version {version_number}.")
        self._show_save_feedback(
            save_feedback_text("saved", name=name, version=version_number, note=note),
            "saved",
        )
        return True

    def _show_save_feedback(self, text: str, kind: str) -> None:
        """Show the result beside the footer. Failures stay until dismissed."""
        if self._feedback_after_id is not None:
            try:
                self.window.after_cancel(self._feedback_after_id)
            except tk.TclError:
                pass
            self._feedback_after_id = None
        self._feedback_kind = kind
        self.save_feedback.configure(text=text, foreground=SAVE_FEEDBACK_COLORS[kind])
        if kind == "failed":
            self.dismiss_button.pack(side="right")
        else:
            self.dismiss_button.pack_forget()
            self._feedback_after_id = self.window.after(
                SAVE_FEEDBACK_SECONDS * 1000, self._clear_save_feedback
            )

    def _clear_save_feedback(self) -> None:
        if self._feedback_after_id is not None:
            try:
                self.window.after_cancel(self._feedback_after_id)
            except tk.TclError:
                pass
            self._feedback_after_id = None
        self._feedback_kind = None
        self.save_feedback.configure(text="")
        self.dismiss_button.pack_forget()

    def _refresh_save_state(self) -> None:
        """Show an Unsaved changes mark in the footer and the window title."""
        if getattr(self, "dirty_label", None) is None:
            return
        dirty = self._has_unsaved_changes()
        # A "saved" or "nothing to save" message is out of date once the draft changes.
        # A failure stays until it is dismissed.
        if dirty and getattr(self, "_feedback_kind", None) in ("saved", "unchanged"):
            self._clear_save_feedback()
        self.dirty_label.configure(text="● Unsaved changes" if dirty else "")
        self.window.title("Components · Unsaved changes" if dirty else "Components")

    def open_version_history(self):
        """Show immutable wording versions for the currently selected component."""
        if self.current_component_id is None:
            return
        component = self.library.get_component(self.current_component_id)
        versions = self.library.list_component_versions(self.current_component_id)
        if component is None or not versions:
            messagebox.showinfo(
                "No version history",
                "This component has no saved wording versions.",
                parent=self.window,
            )
            return

        open_version_history_dialog(self.window, component, versions)

    def open_assembly_builder(self):
        """Open the separate assembly workflow after resolving editor changes."""
        was_dirty = self._has_unsaved_changes()
        if not self._confirm_pending_changes("opening the assembly builder"):
            return
        if was_dirty and self._has_unsaved_changes():
            # The user chose to discard. Reload the saved wording so the
            # assembly builder cannot appear to include an unsaved draft.
            if self.current_component_id is None:
                self.new_component(prompt=False)
            else:
                self._load_component(self.current_component_id)
        if self.assembly_builder_window is not None:
            try:
                if self.assembly_builder_window.window.winfo_exists():
                    self.assembly_builder_window.window.lift()
                    return
            except tk.TclError:
                self.assembly_builder_window = None
        try:
            from assembly_builder import AssemblyBuilderWindow

            self.assembly_builder_window = AssemblyBuilderWindow(
                self.window, self.library, on_generate=self.on_generate
            )
        except (ImportError, OSError, sqlite3.Error, tk.TclError, ValueError) as exc:
            messagebox.showerror(
                "Assembly builder unavailable",
                f"Could not open the assembly builder.\n\n{exc}",
                parent=self.window,
            )

    def close(self):
        if not self._confirm_pending_changes("closing the Components window"):
            return
        if self._preview_after_id is not None:
            try:
                self.window.after_cancel(self._preview_after_id)
            except tk.TclError:
                pass
            self._preview_after_id = None
        try:
            if self.on_close is not None:
                self.on_close()
        finally:
            self.window.destroy()
