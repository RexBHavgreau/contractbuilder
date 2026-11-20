"""Plain-text component editor window.

The editor saves a deliberately small plain-text subset as Markdown. It has no
Word-processing dependency; formatting controls and the live preview are
separate follow-on features.
"""
from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

import core
from library import ComponentLibrary
from component_preview import render_markdown_preview


_MARKDOWN_SPECIAL = frozenset(
    ("\\", chr(96), "*", "_", "{", "}", "[", "]", "(", ")", ">", "#", "+", "-", ".", "!", "|")
)
# Hyphens and periods are ordinary punctuation except in a list marker at the
# beginning of a line. Keep them in _MARKDOWN_SPECIAL for decoding older saves.
_PLAIN_TEXT_SPECIAL = _MARKDOWN_SPECIAL - {"-", "."}


def _escape_plain_segment(text: str) -> str:
    """Escape Markdown punctuation without touching field placeholders."""
    return "".join(("\\" + character) if character in _PLAIN_TEXT_SPECIAL else character
                   for character in text)


def _escape_line_marker(line: str) -> str:
    """Escape structural list markers at line start, not ordinary punctuation."""
    indent = len(line) - len(line.lstrip(" \t"))
    content = line[indent:]
    if (
        content.startswith("- ")
        or content.startswith("-\t")
        or content == "-"
        or (content.startswith("---") and not content.strip("- \t"))
    ):
        return line[:indent] + "\\-" + content[1:]

    digits = 0
    while digits < len(content) and content[digits].isdigit():
        digits += 1
    if digits and content[digits:digits + 2] in (". ", ".\t"):
        return line[:indent] + content[:digits] + "\\." + content[digits + 1:]
    return line


def plain_text_to_markdown(text: str) -> str:
    """Convert plain text to safe Markdown paragraphs and hard line breaks.

    Complete ContractBuilder fields are preserved byte-for-byte. All other
    Markdown syntax is escaped, while ordinary hyphens and periods remain
    readable. Leading list markers are escaped so they do not create lists.
    """
    if not isinstance(text, str):
        raise TypeError("Component text must be a string.")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    pieces: list[str] = []
    cursor = 0
    for match in core.TOKEN.finditer(normalized):
        pieces.append(_escape_plain_segment(normalized[cursor:match.start()]))
        pieces.append(match.group(0))
        cursor = match.end()
    pieces.append(_escape_plain_segment(normalized[cursor:]))
    escaped = "".join(pieces)
    escaped = "\n".join(_escape_line_marker(line) for line in escaped.split("\n"))

    paragraphs: list[str] = []
    current: list[str] = []
    for line in escaped.split("\n"):
        if not line.strip():
            if current:
                paragraphs.append("  \n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append("  \n".join(current))
    return "\n\n".join(paragraphs)


def markdown_to_plain_text(markdown: str) -> str:
    """Reverse the editor's own plain-text Markdown encoding."""
    if not isinstance(markdown, str):
        raise TypeError("Component wording must be a string.")
    output: list[str] = []
    index = 0
    while index < len(markdown):
        if markdown.startswith("  \n", index):
            output.append("\n")
            index += 3
        elif (
            markdown[index] == "\\"
            and index + 1 < len(markdown)
            and markdown[index + 1] in _MARKDOWN_SPECIAL
        ):
            output.append(markdown[index + 1])
            index += 2
        else:
            output.append(markdown[index])
            index += 1
    return "".join(output)


class ComponentEditorWindow:
    """Manage saved components and create immutable wording versions."""

    def __init__(self, parent, library: ComponentLibrary | None = None, on_close=None):
        self.parent = parent
        self.library = library or ComponentLibrary()
        self.on_close = on_close
        self.current_component_id: int | None = None
        self.loaded_markdown: str | None = None
        self.loaded_plain_text = ""
        self.protected_content = False
        self.saved_snapshot = None
        self.suspend_selection = False
        self._preview_after_id = None
        self.window = tk.Toplevel(parent)
        self.window.title("Components")
        self.window.geometry("1060x720")
        self.window.minsize(820, 570)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._build_widgets()
        self.refresh_components()
        self.new_component(prompt=False)

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
        library_frame.rowconfigure(1, weight=1)

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

        self.tree = ttk.Treeview(
            library_frame, columns=("name", "category"), show="headings",
            selectmode="browse",
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("category", text="Category")
        self.tree.column("name", width=155, anchor="w")
        self.tree.column("category", width=115, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(
            library_frame, orient="vertical", command=self.tree.yview
        )
        tree_scroll.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.select_component)

        ttk.Button(
            library_frame, text="New component", command=self.new_component
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))

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
        edit_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        panes.add(edit_frame, weight=1)
        panes.add(preview_frame, weight=1)

        self.wording = tk.Text(
            edit_frame, wrap="word", undo=True, height=18,
            font="TkDefaultFont", relief="solid", borderwidth=1,
            padx=7, pady=6,
        )
        self.wording.grid(row=0, column=0, sticky="nsew")
        edit_scroll = ttk.Scrollbar(
            edit_frame, orient="vertical", command=self.wording.yview
        )
        edit_scroll.grid(row=0, column=1, sticky="ns")
        self.wording.configure(yscrollcommand=edit_scroll.set)
        # Tk's modified virtual event covers typing, paste, cut, undo, redo
        # and programmatic edits. Reset its flag so each later edit can notify.
        self.wording.bind("<<Modified>>", self._on_wording_modified)

        self.preview = tk.Text(
            preview_frame, wrap="word", height=18, state="disabled",
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

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        self.status = ttk.Label(footer, text="", foreground="#555555")
        self.status.pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Close", command=self.close).pack(side="right")
        ttk.Button(
            footer, text="Save version", command=self.save_component
        ).pack(side="right", padx=(0, 8))

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
        self.preview.tag_configure(
            "list_marker", foreground="#555555", lmargin1=10
        )
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

    def _on_wording_modified(self, _event=None):
        if not self.wording.edit_modified():
            return
        self.wording.edit_modified(False)
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
        source = self.wording.get("1.0", "end-1c")
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

    def refresh_components(self, selected_id: int | None = None):
        query = self.search_variable.get().strip()
        components = (
            self.library.search_components(query)
            if query
            else self.library.list_components()
        )
        self.suspend_selection = True
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
            for component in components:
                item_id = str(component["id"])
                self.tree.insert(
                    "", "end", iid=item_id,
                    values=(component["name"], component["category"]),
                )
            target = str(selected_id) if selected_id is not None else None
            if target and self.tree.exists(target):
                self.tree.selection_set(target)
                self.tree.focus(target)
                self.tree.see(target)
            elif self.current_component_id is not None and self.tree.exists(
                str(self.current_component_id)
            ):
                self.tree.selection_set(str(self.current_component_id))
        finally:
            self.suspend_selection = False

    def select_component(self, _event=None):
        if self.suspend_selection:
            return
        selection = self.tree.selection()
        if not selection:
            return
        selected_id = int(selection[0])
        if selected_id == self.current_component_id:
            return
        if not self._confirm_pending_changes("opening another component"):
            self.suspend_selection = True
            try:
                if self.current_component_id is not None and self.tree.exists(
                    str(self.current_component_id)
                ):
                    self.tree.selection_set(str(self.current_component_id))
                    self.tree.focus(str(self.current_component_id))
                else:
                    self.tree.selection_remove(*selection)
            finally:
                self.suspend_selection = False
            return
        self._load_component(selected_id)

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
        self.loaded_markdown = latest["markdown"]
        self.loaded_plain_text = markdown_to_plain_text(self.loaded_markdown)
        # This editor owns a reversible plain-text encoding. Other Markdown
        # constructs are displayed for reference but may not be round-tripped
        # by the first editor step.
        self.protected_content = (
            plain_text_to_markdown(self.loaded_plain_text) != self.loaded_markdown
        )
        self.name_variable.set(component["name"])
        self.category_variable.set(component["category"])
        self.tags_variable.set(", ".join(component["tags"]))
        self.description_variable.set(component["description"])
        self.note_variable.set("")
        self.wording.configure(state="normal")
        self.wording.delete("1.0", "end")
        self.wording.insert("1.0", self.loaded_plain_text)
        if self.protected_content:
            self.wording.configure(state="disabled")
            self.content_notice.configure(
                text=(
                    "This component contains formatting that this first editor "
                    "cannot safely change yet. Its wording is protected; create "
                    "a new component or wait for the formatting tools."
                )
            )
        else:
            self.content_notice.configure(text="")
        self.saved_snapshot = self._state()
        self.status.configure(
            text=f"Editing {component['name']} · version {latest['number']}."
        )
        self._schedule_preview()
        self.refresh_components(selected_id)

    def new_component(self, prompt: bool = True):
        if prompt and not self._confirm_pending_changes("starting a new component"):
            return
        self.current_component_id = None
        self.loaded_markdown = None
        self.loaded_plain_text = ""
        self.protected_content = False
        self.name_variable.set("")
        self.category_variable.set("")
        self.tags_variable.set("")
        self.description_variable.set("")
        self.note_variable.set("")
        self.wording.configure(state="normal")
        self.wording.delete("1.0", "end")
        self.content_notice.configure(text="")
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
        self.name_entry_focus()

    def name_entry_focus(self):
        self.name_entry.focus_set()

    def save_component(self) -> bool:
        name = self.name_variable.get().strip()
        body = self.wording.get("1.0", "end-1c")
        if not name:
            messagebox.showerror(
                "A name is required", "Enter a name for this component.",
                parent=self.window,
            )
            return False
        if not body.strip():
            messagebox.showerror(
                "Wording is required", "Enter the component wording before saving.",
                parent=self.window,
            )
            return False

        if self.protected_content and body == self.loaded_plain_text:
            markdown = self.loaded_markdown or ""
        else:
            if (
                self.current_component_id is not None
                and self.loaded_markdown is not None
                and body != self.loaded_plain_text
                and self.protected_content
            ):
                proceed = messagebox.askyesno(
                    "Replace existing formatting?",
                    (
                        "This component contains formatting that the plain-text "
                        "editor cannot preserve. Saving these text changes will "
                        "replace that formatting. Continue?"
                    ),
                    parent=self.window,
                )
                if not proceed:
                    return False
            markdown = plain_text_to_markdown(body)

        tags = [item.strip() for item in self.tags_variable.get().split(",") if item.strip()]
        try:
            result = self.library.save_component(
                self.current_component_id,
                name,
                markdown,
                description=self.description_variable.get(),
                category=self.category_variable.get(),
                tags=tags,
                note=self.note_variable.get(),
            )
        except (ValueError, TypeError, OSError, sqlite3.Error) as exc:
            messagebox.showerror("Could not save component", str(exc), parent=self.window)
            return False

        self.current_component_id = result["component_id"]
        self.note_variable.set("")
        self._load_component(self.current_component_id)
        version_number = result["version"]["number"]
        self.status.configure(text=f"Saved {name} · version {version_number}.")
        return True

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
