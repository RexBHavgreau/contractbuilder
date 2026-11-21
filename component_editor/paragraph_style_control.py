"""The Paragraph style control of the Components window (T-061).

A mixin of ComponentEditorWindow. The choice is kept beside the Markdown, one
name per ordinary top-level paragraph (``paragraph_styles``); nothing is
written into the wording. The list is kept in step with every edit by
``paragraph_styles.sync_styles``.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import paragraph_styles as styles_rules

from .text_rules import plain_text_to_markdown


class ParagraphStyleMixin:
    """Choose, keep and show the style of the paragraph at the cursor."""

    def _build_paragraph_style_control(self, toolbar):
        self.paragraph_styles: list[str] = []
        self._synced_paragraphs: list[str] = []
        # A short, fixed label keeps the toolbar layout stable; the menu marks the
        # style of the paragraph at the cursor.
        self.paragraph_style_variable = tk.StringVar(master=self.window, value="Normal")
        self.paragraph_style_button = ttk.Menubutton(toolbar, text="Style")
        self.paragraph_style_menu = tk.Menu(self.paragraph_style_button, tearoff=False)
        for name in styles_rules.STANDARD_STYLES:
            self.paragraph_style_menu.add_radiobutton(
                label=name, value=name, variable=self.paragraph_style_variable,
                command=lambda chosen=name: self.set_paragraph_style(chosen),
            )
        self.paragraph_style_button["menu"] = self.paragraph_style_menu
        self.paragraph_style_button.configure(state="disabled")
        return self.paragraph_style_button

    # -- the wording as Markdown ------------------------------------------

    def _current_markdown_text(self) -> str:
        raw = self.wording.get("1.0", "end-1c")
        return raw if self.editor_markdown_mode else plain_text_to_markdown(raw)

    def _paragraph_texts(self, markdown: str) -> list[str]:
        return [p.text for p in styles_rules.text_paragraphs(markdown)]

    # -- keeping the list in step ----------------------------------------

    def _reset_paragraph_styles(self, markdown: str, stored=()):
        """Start from a saved version (or a blank component)."""
        self.paragraph_styles = styles_rules.normalize(stored)
        self._synced_paragraphs = self._paragraph_texts(markdown)

    def _sync_paragraph_styles(self):
        """Carry the styles across an edit of the wording."""
        if self.protected_content:
            return
        texts = self._paragraph_texts(self._current_markdown_text())
        self.paragraph_styles = styles_rules.sync_styles(
            self._synced_paragraphs, self.paragraph_styles, texts
        )
        self._synced_paragraphs = texts

    # -- choosing ----------------------------------------------------------

    def _paragraph_index_at_cursor(self):
        try:
            line = int(self.wording.index("insert").split(".")[0]) - 1
        except (tk.TclError, ValueError):
            return None
        return styles_rules.paragraph_index_at_line(self._current_markdown_text(), line)

    def set_paragraph_style(self, name: str):
        """Give the paragraph at the cursor this style (a plain Word style name)."""
        index = self._paragraph_index_at_cursor()
        if index is None or self.protected_content:
            return
        self._sync_paragraph_styles()
        self.paragraph_styles = styles_rules.set_style(self.paragraph_styles, index, name)
        self._refresh_save_state()
        self._update_paragraph_style_control()
        self._schedule_preview()

    def _update_paragraph_style_control(self):
        """Show the style at the cursor; disable the control where it does not apply."""
        button = getattr(self, "paragraph_style_button", None)
        if button is None or not self.wording.winfo_exists():
            return
        index = None if self.protected_content else self._paragraph_index_at_cursor()
        if index is None:
            button.configure(state="disabled")
            return
        name = styles_rules.style_for(self.paragraph_styles, index)
        self.paragraph_style_variable.set(name if name in styles_rules.STANDARD_STYLES else "")
        button.configure(state="normal")

    def _paragraph_styles_signature(self) -> str:
        """A string for the unsaved-changes check; empty when every paragraph is Normal."""
        return styles_rules.dump(self.paragraph_styles)
