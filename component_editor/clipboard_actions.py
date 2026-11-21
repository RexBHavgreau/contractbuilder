"""Copy, cut and paste in the wording box (T-051-B).

A mixin of ComponentEditorWindow. The formatted view hides Markdown syntax
(escape backslashes, ``**``, list markers) by eliding it, so the text in the
box is longer than the text on screen. Copy and cut therefore take **the text
as shown** (``-displaychars``); a paste of ordinary text is escaped, so what
was pasted stays readable and is never taken for formatting.
"""
from __future__ import annotations

import tkinter as tk

from .copy_text import visible_text
from .text_rules import plain_text_to_markdown


EDIT_FRAME_TEXT = "Edit wording"
RAW_FRAME_TEXT = "Stored text: backslashes and stars here are normal"


class ClipboardMixin:
    """Clipboard actions of the Components window's wording box."""

    def _bind_clipboard(self):
        widget = self.wording
        widget.bind("<<Copy>>", self.copy_visible)
        widget.bind("<<Cut>>", self.cut_visible)
        widget.bind("<<Paste>>", self.paste_typed_text)
        self.wording_menu = tk.Menu(widget, tearoff=False)
        self.wording_menu.add_command(label="Cut", command=self.cut_visible)
        self.wording_menu.add_command(label="Copy", command=self.copy_visible)
        self.wording_menu.add_command(label="Paste", command=self.paste_typed_text)
        self.wording_menu.add_separator()
        self.wording_menu.add_command(label="Copy as stored text", command=self.copy_stored)
        self.wording_menu.add_command(
            label="Copy all wording as text", command=self.copy_all_visible
        )
        for sequence in ("<Button-3>", "<Control-Button-1>"):
            widget.bind(sequence, self._show_wording_menu, add="+")

    def _show_wording_menu(self, event):
        has_selection = bool(self.wording.tag_ranges("sel"))
        editable = not self.protected_content
        self.wording_menu.entryconfigure("Cut", state="normal" if has_selection and editable else "disabled")
        self.wording_menu.entryconfigure("Copy", state="normal" if has_selection else "disabled")
        self.wording_menu.entryconfigure("Paste", state="normal" if editable else "disabled")
        self.wording_menu.entryconfigure(
            "Copy as stored text", state="normal" if has_selection else "disabled"
        )
        try:
            self.wording_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.wording_menu.grab_release()
        return "break"

    # -- what goes on the clipboard ----------------------------------------

    def _selection_range(self):
        ranges = self.wording.tag_ranges("sel")
        return (str(ranges[0]), str(ranges[1])) if ranges else None

    def _selected_visible_text(self, start, end) -> str:
        """The selection as shown: elided syntax is left out."""
        try:
            # tkinter's Text.get() has no displaychars option; call Tk directly.
            return self.wording.tk.call(
                str(self.wording), "get", "-displaychars", "--", start, end
            )
        except tk.TclError:           # an old Tk without -displaychars
            return visible_text(self.wording.get(start, end))

    def _put_on_clipboard(self, text: str):
        self.wording.clipboard_clear()
        self.wording.clipboard_append(text)

    def copy_visible(self, _event=None):
        selection = self._selection_range()
        if selection:
            self._put_on_clipboard(self._selected_visible_text(*selection))
        return "break"

    def cut_visible(self, _event=None):
        selection = self._selection_range()
        if not selection:
            return "break"
        self._put_on_clipboard(self._selected_visible_text(*selection))
        if not self.protected_content:
            self.wording.delete(*selection)
        return "break"

    def copy_stored(self):
        """The selection exactly as stored (Markdown), for people who want it."""
        selection = self._selection_range()
        if selection:
            self._put_on_clipboard(self.wording.get(*selection))
        return "break"

    def copy_all_visible(self):
        """All the wording as shown, with bullets and numbers, ready for Word or email."""
        self._put_on_clipboard(visible_text(self._current_markdown_text()))
        return "break"

    # -- paste ----------------------------------------------------------------

    def paste_typed_text(self, _event=None):
        """Paste ordinary text as typed text: Markdown characters are escaped.

        In the raw (stored text) view, or in a plain-text draft, the paste is
        left to Tk so it goes in exactly as copied.
        """
        if self.protected_content:
            return "break"
        if self.source_view_variable.get() or not self.editor_markdown_mode:
            return None
        try:
            clipboard = self.wording.clipboard_get()
        except tk.TclError:
            return "break"
        converted = plain_text_to_markdown(clipboard)
        selection = self._selection_range()
        if selection:
            self.wording.delete(*selection)
            self.wording.mark_set("insert", selection[0])
        self.wording.insert("insert", converted)
        self.wording.see("insert")
        return "break"
