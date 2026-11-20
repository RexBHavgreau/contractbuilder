"""Formatting, field, table and Word-import actions on the wording box.

A mixin of ComponentEditorWindow. The dialogs are looked up through the
package (``component_editor.FieldInsertDialog`` and so on) at the moment they
open, so a test can substitute one by patching the package.
"""
from __future__ import annotations

from tkinter import filedialog, messagebox

import component_editor as _package

from .fields import available_field_names
from .styling import _style_markdown_widget
from .tables import find_markdown_table
from .text_rules import (
    plain_text_to_markdown,
    toggle_inline_format,
    toggle_markdown_block,
)


class WordingActionsMixin:
    """Wording-box actions of the Components window."""

    def _ensure_markdown_mode(self):
        """Convert a new plain-text draft once, then keep Markdown as the source of truth."""
        if self.editor_markdown_mode:
            return
        plain = self.wording.get("1.0", "end-1c")
        insert_offset = len(self.wording.get("1.0", "insert"))
        selection = self.wording.tag_ranges("sel")
        selection_offsets = None
        if selection:
            selection_offsets = (
                len(self.wording.get("1.0", str(selection[0]))),
                len(self.wording.get("1.0", str(selection[1]))),
            )

        def mapped(offset):
            sentinel = "\ue000"
            return max(0, len(plain_text_to_markdown(plain[:offset] + sentinel)) - 1)

        encoded = plain_text_to_markdown(plain)
        self.wording.delete("1.0", "end")
        self.wording.insert("1.0", encoded)
        self.editor_markdown_mode = True
        self.wording.mark_set("insert", f"1.0 + {mapped(insert_offset)} chars")
        if selection_offsets is not None:
            start, end = selection_offsets
            self.wording.tag_add(
                "sel",
                f"1.0 + {mapped(start)} chars",
                f"1.0 + {mapped(end)} chars",
            )
        self.wording.edit_modified(False)
        self._refresh_editor_styling()

    def _refresh_editor_styling(self):
        if self.editor_markdown_mode:
            _style_markdown_widget(self.wording, self.source_view_variable.get())
        else:
            for tag in ("syntax", "heading_1", "heading_2", "heading_3", "bold", "italic", "field"):
                self.wording.tag_remove(tag, "1.0", "end")

    def toggle_source_view(self):
        if self.source_view_variable.get():
            self._ensure_markdown_mode()
        self._refresh_editor_styling()

    def apply_format(self, action: str, level: int = 2):
        """Toggle a Markdown style while preserving the selection and source text."""
        if self.protected_content:
            messagebox.showinfo(
                "This wording is protected",
                "This component contains formatting the editor cannot safely change. "
                "Create a new component or import a simpler version to edit it.",
                parent=self.window,
            )
            return "break"
        self._ensure_markdown_mode()
        widget = self.wording
        selected = widget.tag_ranges("sel")
        source = widget.get("1.0", "end-1c")

        if action in {"bold", "italic"}:
            if selected:
                start_index, end_index = str(selected[0]), str(selected[1])
            else:
                start_index = widget.index("insert wordstart")
                end_index = widget.index("insert wordend")
                if widget.compare(start_index, "==", end_index):
                    marker = "**" if action == "bold" else "*"
                    widget.insert("insert", marker + marker)
                    widget.mark_set("insert", f"insert - {len(marker)} chars")
                    self._refresh_editor_styling()
                    self._schedule_preview()
                    self._update_toolbar_state()
                    widget.focus_set()
                    return "break"
            start = len(widget.get("1.0", start_index))
            end = len(widget.get("1.0", end_index))
            updated, new_start, new_end = toggle_inline_format(source, start, end, action)
        else:
            if selected:
                first_index = widget.index(f"{selected[0]} linestart")
                last_index = widget.index(f"{selected[1]} lineend")
            else:
                first_index = widget.index("insert linestart")
                last_index = widget.index("insert lineend")
            start = len(widget.get("1.0", first_index))
            end = len(widget.get("1.0", last_index))
            previous_text = widget.get("1.0", first_index)
            updated, new_start, new_end = toggle_markdown_block(
                source, start, end, action, level, previous_text
            )

        if updated != source:
            widget.delete("1.0", "end")
            widget.insert("1.0", updated)
        widget.tag_remove("sel", "1.0", "end")
        if new_end > new_start:
            widget.tag_add(
                "sel",
                f"1.0 + {new_start} chars",
                f"1.0 + {new_end} chars",
            )
        widget.mark_set("insert", f"1.0 + {new_end} chars")
        self._refresh_editor_styling()
        self._schedule_preview()
        self._update_toolbar_state()
        widget.focus_set()
        return "break"

    def _available_field_names(self):
        return available_field_names(self.library)

    def open_field_dialog(self):
        if self.protected_content:
            messagebox.showinfo(
                "This wording is protected",
                "Create a new component to insert fields into wording that can be edited safely.",
                parent=self.window,
            )
            return
        self._ensure_markdown_mode()

        def insert(value):
            selected = self.wording.tag_ranges("sel")
            start, end = (str(selected[0]), str(selected[1])) if selected else (
                self.wording.index("insert"), self.wording.index("insert")
            )
            self.wording.delete(start, end)
            self.wording.insert(start, value)
            self.wording.mark_set("insert", f"{start} + {len(value)} chars")
            self._refresh_editor_styling()
            self._schedule_preview()
            self.wording.focus_set()

        _package.FieldInsertDialog(self.window, self._available_field_names(), insert)

    def open_table_editor(self):
        if self.protected_content:
            messagebox.showinfo(
                "This wording is protected",
                "Create a new component or import a simpler Word file before editing this table.",
                parent=self.window,
            )
            return
        self._ensure_markdown_mode()
        source = self.wording.get("1.0", "end-1c")
        cursor = len(self.wording.get("1.0", "insert"))
        block = find_markdown_table(source, cursor)
        if block:
            rows = block["rows"]
            alignments = block["alignments"]
        else:
            rows = [["", ""], ["", ""]]
            alignments = [None, None]

        def save_table(markdown):
            current = self.wording.get("1.0", "end-1c")
            if block:
                start, end = block["start"], block["end"]
                before, after = current[:start], current[end:]
                replacement = markdown
                if before and not before.endswith("\n\n"):
                    replacement = "\n\n" + replacement if not before.endswith("\n") else "\n" + replacement
                if after and not after.startswith("\n"):
                    replacement += "\n\n"
                self.wording.delete(f"1.0 + {start} chars", f"1.0 + {end} chars")
                self.wording.insert(f"1.0 + {start} chars", replacement)
            else:
                selected = self.wording.tag_ranges("sel")
                if selected:
                    start_index, end_index = str(selected[0]), str(selected[1])
                else:
                    start_index = end_index = self.wording.index("insert")
                before = self.wording.get("1.0", start_index)
                after = self.wording.get(end_index, "end-1c")
                prefix = "" if not before.strip() or before.endswith("\n\n") else "\n\n"
                suffix = "" if not after.strip() or after.startswith("\n\n") else "\n\n"
                insertion = prefix + markdown + suffix
                self.wording.delete(start_index, end_index)
                self.wording.insert(start_index, insertion)
            self._refresh_editor_styling()
            self._schedule_preview()
            self.wording.focus_set()

        _package.TableEditorDialog(self.window, rows, alignments, save_table)

    def open_import_dialog(self):
        path = filedialog.askopenfilename(
            parent=self.window,
            title="Import from a Word file",
            filetypes=(("Word documents", "*.docx"), ("All files", "*.*")),
        )
        if path:
            _package.ImportReviewDialog(self, path)
