"""Review a Word import before it is saved as a component."""
from __future__ import annotations

import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from component_preview import configure_paragraph_style_tags, render_markdown_preview
from docx_to_markdown import DocxImportError, import_docx
import paragraph_styles as styles_rules

from .fields import malformed_field_message
from .styling import _style_markdown_widget


class ImportReviewDialog:
    """Review a read-only DOCX conversion; save only after an explicit choice."""

    def __init__(self, editor, path):
        self.editor = editor
        self.path = path
        try:
            imported = import_docx(path)
        except (DocxImportError, OSError) as exc:
            messagebox.showerror(
                "Could not import Word file",
                f"{exc}\n\nChoose an unencrypted .docx file and try again.",
                parent=editor.window,
            )
            return

        # The styles found in the Word file stay with their paragraphs while the
        # wording is reviewed and edited here (T-061).
        self.paragraph_styles = list(imported.paragraph_styles)
        self._synced_paragraphs = [
            p.text for p in styles_rules.text_paragraphs(imported.markdown)
        ]
        self.window = tk.Toplevel(editor.window)
        self.window.title("Review Word import")
        self.window.geometry("1080x720")
        self.window.minsize(820, 560)
        self.window.lift()
        outer = ttk.Frame(self.window, padding=12)
        outer.pack(fill="both", expand=True)
        name_row = ttk.Frame(outer)
        name_row.pack(fill="x", pady=(0, 8))
        ttk.Label(name_row, text="Component name").pack(side="left")
        self.name_variable = tk.StringVar(master=self.window, value=Path(path).stem)
        ttk.Entry(name_row, textvariable=self.name_variable).pack(
            side="left", fill="x", expand=True, padx=(10, 0)
        )

        warning_frame = ttk.LabelFrame(outer, text="Import warnings — review before saving")
        warning_frame.pack(fill="x", pady=(0, 8))
        self.warning_text = tk.Text(warning_frame, height=5, wrap="word", state="normal")
        warning_scroll = ttk.Scrollbar(
            warning_frame, orient="vertical", command=self.warning_text.yview
        )
        self.warning_text.configure(yscrollcommand=warning_scroll.set)
        self.warning_text.pack(side="left", fill="both", expand=True)
        warning_scroll.pack(side="right", fill="y")
        if imported.warnings:
            for warning in imported.warnings:
                self.warning_text.insert(
                    "end", f"• {warning.location}: {warning.message}\n"
                )
        else:
            self.warning_text.insert(
                "end", "No unsupported Word structures were found in the document body."
            )
        self.warning_text.configure(state="disabled")

        ttk.Label(
            outer,
            text="Review the result below. Edit the wording on the left; the preview updates as you type.",
            wraplength=1000,
        ).pack(anchor="w", pady=(0, 5))
        panes = ttk.Panedwindow(outer, orient="horizontal")
        panes.pack(fill="both", expand=True)
        edit_frame = ttk.LabelFrame(panes, text="Imported wording", padding=4)
        preview_frame = ttk.LabelFrame(panes, text="Preview", padding=4)
        edit_frame.columnconfigure(0, weight=1)
        edit_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        panes.add(edit_frame, weight=1)
        panes.add(preview_frame, weight=1)
        self.source = tk.Text(edit_frame, wrap="word", undo=True, height=18)
        self.source.grid(row=0, column=0, sticky="nsew")
        edit_scroll = ttk.Scrollbar(edit_frame, orient="vertical", command=self.source.yview)
        edit_scroll.grid(row=0, column=1, sticky="ns")
        self.source.configure(yscrollcommand=edit_scroll.set)
        self.source.insert("1.0", imported.markdown)
        self.preview = tk.Text(
            preview_frame, wrap="word", height=18, state="disabled",
            font="TkDefaultFont", padx=7, pady=6,
        )
        self.preview.grid(row=0, column=0, sticky="nsew")
        preview_scroll = ttk.Scrollbar(
            preview_frame, orient="vertical", command=self.preview.yview
        )
        preview_scroll.grid(row=0, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=preview_scroll.set)
        self._configure_preview()
        configure_paragraph_style_tags(self.preview)
        self.source_view_variable = tk.BooleanVar(master=self.window, value=False)
        ttk.Checkbutton(
            outer,
            text="Advanced: show raw text",
            variable=self.source_view_variable,
            command=self._style_source,
        ).pack(anchor="w", pady=(5, 0))
        self.source.bind("<<Modified>>", self._source_modified)
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(8, 0))
        ttk.Button(footer, text="Cancel", command=self.close).pack(side="right")
        ttk.Button(footer, text="Save as component", command=self.save).pack(
            side="right", padx=(0, 8)
        )
        self._preview_after_id = None
        self._style_source()
        self._update_preview()
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.source.edit_modified(False)
        self.window.grab_set()

    def close(self):
        if self._preview_after_id is not None:
            try:
                self.window.after_cancel(self._preview_after_id)
            except tk.TclError:
                pass
            self._preview_after_id = None
        self.window.destroy()

    def _configure_preview(self):
        self.preview.tag_configure("heading_1", font=("TkDefaultFont", 16, "bold"))
        self.preview.tag_configure("heading_2", font=("TkDefaultFont", 14, "bold"))
        self.preview.tag_configure("heading_3", font=("TkDefaultFont", 12, "bold"))
        self.preview.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))
        self.preview.tag_configure("italic", font=("TkDefaultFont", 10, "italic"))
        self.preview.tag_configure("field", background="#fff0c2", foreground="#714d00")
        self.preview.tag_configure("list_marker", foreground="#555555")
        self.preview.tag_configure(
            "marker", foreground="#4f4f4f", background="#e6e6e6",
            font=("TkDefaultFont", 9, "italic"),
        )
        self.preview.tag_configure("table_header", font=("TkDefaultFont", 9, "bold"))
        self.preview.tag_configure("table_cell", font=("TkFixedFont", 9))
        self.preview.tag_configure("table_border", foreground="#777777")
        self.preview.tag_configure("code", font=("TkFixedFont", 9))
        self.preview.tag_configure("code_block", font=("TkFixedFont", 9))
        self.preview.tag_configure("blockquote", foreground="#555555")
        self.preview.tag_configure("link", underline=True, foreground="#245a8d")
        self.preview.tag_configure("rule", foreground="#888888")
        self.preview.tag_configure("source_text", foreground="#666666")

    def _style_source(self):
        _style_markdown_widget(self.source, self.source_view_variable.get())

    def _source_modified(self, _event=None):
        if not self.source.edit_modified():
            return
        self.source.edit_modified(False)
        self._style_source()
        if self._preview_after_id is not None:
            try:
                self.window.after_cancel(self._preview_after_id)
            except tk.TclError:
                pass
        self._preview_after_id = self.window.after(220, self._update_preview)

    def _update_preview(self):
        self._preview_after_id = None
        source = self.source.get("1.0", "end-1c")
        try:
            self._sync_styles(source)
            segments = render_markdown_preview(source, self.paragraph_styles)
        except (TypeError, ValueError) as exc:
            segments = [(f"Preview unavailable: {exc}", ("source_text",))]
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        if not segments:
            self.preview.insert("1.0", "Start typing to see a preview.", ("source_text",))
        else:
            for value, tags in segments:
                self.preview.insert("end", value, tags)
        self.preview.configure(state="disabled")

    def _sync_styles(self, source: str):
        texts = [p.text for p in styles_rules.text_paragraphs(source)]
        self.paragraph_styles = styles_rules.sync_styles(
            self._synced_paragraphs, self.paragraph_styles, texts
        )
        self._synced_paragraphs = texts

    def save(self):
        name = self.name_variable.get().strip()
        markdown = self.source.get("1.0", "end-1c")
        self._sync_styles(markdown)
        if not name:
            messagebox.showerror(
                "A name is required", "Enter a name for this component.",
                parent=self.window,
            )
            return
        if not markdown.strip():
            messagebox.showerror(
                "No wording to save",
                "The Word file did not contain any importable body wording.",
                parent=self.window,
            )
            return
        warning = malformed_field_message(markdown)
        if warning and not messagebox.askyesno(
            "Check field placeholder", warning + "\n\nSave the wording anyway?",
            parent=self.window,
        ):
            return
        try:
            component_id = self.editor.library.create_component(
                name, markdown=markdown, paragraph_styles=self.paragraph_styles
            )
        except (ValueError, TypeError, OSError, sqlite3.Error) as exc:
            messagebox.showerror("Could not save component", str(exc), parent=self.window)
            return
        self.editor.refresh_components(component_id)
        self.editor._load_component(component_id)
        if self._preview_after_id is not None:
            try:
                self.window.after_cancel(self._preview_after_id)
            except tk.TclError:
                pass
        self.window.destroy()
        messagebox.showinfo(
            "Component saved",
            f"{name} was saved as a new component. The original Word file was not changed.",
            parent=self.editor.window,
        )
