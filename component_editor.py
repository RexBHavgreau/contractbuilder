"""Markdown-backed component editor with formatting, tables, fields and DOCX import review.

The editor keeps Markdown as the saved source, presents a simplified formatted
view by default, and uses the existing Markdown and DOCX conversion modules.
"""
from __future__ import annotations

import re
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

import core
from library import ComponentLibrary
from markdown_fields import protect_fields
from md_parse import create_parser
from publisher_profiles import PROFILE_FIELDS
from docx_to_markdown import DocxImportError, import_docx
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



_PROFILE_FIELD_NAMES = {
    "publisher_name": "Publisher Name",
    "contact_name": "Contact Name",
    "contact_title": "Contact Title",
    "contact_email": "Contact Email",
    "contact_phone": "Contact Phone",
    "website": "Website",
    "address_line1": "Address Line 1",
    "address_line2": "Address Line 2",
    "city": "City",
    "region": "State / Province / Region",
    "postal_code": "Postal Code",
    "country": "Country",
    "notes": "Publisher Notes",
}

_FIELD_FORMATS = (
    ("Plain text", ""),
    ("Uppercase", "upper"),
    ("Long text", "long"),
    ("Date", "date"),
    ("Formal date", "date-formal"),
    ("Short date", "date-short"),
    ("Money", "money"),
    ("Money in words", "money-words"),
    ("Whole dollars", "money-whole"),
    ("Number", "number"),
    ("Number in words", "number-words"),
    ("Choice", "choice"),
    ("Singular or plural", "plural"),
)


def make_field_placeholder(name: str, format_name: str = "", options: str = "") -> str:
    """Build a field using the core engine's own field parser and format aliases."""
    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Choose or enter a field name.")
    expression = clean_name
    if format_name:
        expression += " | " + str(format_name).strip()
        if format_name in {"choice", "plural"}:
            clean_options = str(options or "").strip()
            if not clean_options:
                if format_name == "choice":
                    raise ValueError("A choice field needs at least one option.")
                raise ValueError("A singular-or-plural field needs two wordings.")
            expression += ": " + clean_options
    parsed_name, parsed_format, parsed_options = core.parse_field(expression)
    if not parsed_name:
        raise ValueError("The field name is empty. Enter a name before inserting it.")
    if format_name and parsed_format != format_name:
        raise ValueError("That field format is not supported by ContractBuilder.")
    if parsed_format == "plural" and len(parsed_options) != 2:
        raise ValueError("A singular-or-plural field needs two wordings, such as item, items.")
    if parsed_format == "choice" and not parsed_options:
        raise ValueError("A choice field needs at least one option.")
    placeholder = "{{" + expression + "}}"
    if core.TOKEN.fullmatch(placeholder) is None:
        raise ValueError("That field could not be read. Check its name and format.")
    return placeholder


def _split_markdown_table_row(line: str) -> list[str]:
    """Split a Markdown table row without splitting escaped or field-internal pipes."""
    source = str(line or "").strip().rstrip("\r\n")
    cells: list[str] = []
    current: list[str] = []
    in_field = 0
    index = 0
    while index < len(source):
        if source.startswith("{{", index):
            in_field += 1
            current.append("{{")
            index += 2
        elif source.startswith("}}", index) and in_field:
            in_field -= 1
            current.append("}}")
            index += 2
        elif source[index] == "\\" and index + 1 < len(source):
            if source[index + 1] == "|":
                current.append("|")
                index += 2
            else:
                current.extend((source[index], source[index + 1]))
                index += 2
        elif source[index] == "|" and not in_field:
            cells.append("".join(current).strip())
            current = []
            index += 1
        else:
            current.append(source[index])
            index += 1
    cells.append("".join(current).strip())
    if source.startswith("|") and cells and not cells[0]:
        cells.pop(0)
    if source.endswith("|") and cells and not cells[-1]:
        cells.pop()
    return cells


def _is_markdown_table_separator(line: str) -> bool:
    cells = _split_markdown_table_row(line)
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) is not None
        for cell in cells
    )


def _has_markdown_table_delimiter(line: str) -> bool:
    return len(_split_markdown_table_row(line)) > 1


def find_markdown_table(markdown: str, character_offset: int = 0) -> dict | None:
    """Find a GFM table containing an offset, returning rows and replacement bounds."""
    source = str(markdown or "")
    lines = source.splitlines(keepends=True)
    offsets = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)

    for index in range(len(lines) - 1):
        if not _has_markdown_table_delimiter(lines[index]):
            continue
        if not _is_markdown_table_separator(lines[index + 1]):
            continue
        row_end = index + 2
        while row_end < len(lines) and _has_markdown_table_delimiter(lines[row_end]):
            row_end += 1
        start = offsets[index]
        end = offsets[row_end] if row_end < len(lines) else len(source)
        if start <= character_offset <= end:
            separator = _split_markdown_table_row(lines[index + 1])
            alignments = []
            for cell in separator:
                marker = cell.replace(" ", "")
                if marker.startswith(":") and marker.endswith(":"):
                    alignments.append("center")
                elif marker.startswith(":"):
                    alignments.append("left")
                elif marker.endswith(":"):
                    alignments.append("right")
                else:
                    alignments.append(None)
            rows = [_split_markdown_table_row(lines[index])]
            rows.extend(_split_markdown_table_row(lines[row]) for row in range(index + 2, row_end))
            width = max([len(alignments)] + [len(row) for row in rows] + [1])
            alignments.extend([None] * (width - len(alignments)))
            rows = [row + [""] * (width - len(row)) for row in rows]
            return {
                "start": start,
                "end": end,
                "rows": rows,
                "alignments": alignments,
            }
    return None


def _escape_table_cell(value: str) -> str:
    """Escape literal pipes, but preserve the pipe inside a {{field | format}} token."""
    source = str(value or "")
    result = []
    cursor = 0
    for match in core.TOKEN.finditer(source):
        result.append(source[cursor:match.start()].replace("|", r"\|"))
        result.append(match.group(0))
        cursor = match.end()
    result.append(source[cursor:].replace("|", r"\|"))
    return "".join(result).replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def build_markdown_table(
    rows: list[list[str]],
    alignments: list[str | None] | None = None,
) -> str:
    """Serialize a grid whose first row is the header, preserving field placeholders."""
    clean_rows = [
        [str(value or "").strip() for value in row]
        for row in rows
    ]
    width = max((len(row) for row in clean_rows), default=0)
    if width < 1:
        raise ValueError("A table needs at least one column.")
    clean_rows = [row + [""] * (width - len(row)) for row in clean_rows]
    if not clean_rows:
        clean_rows = [[""] * width]
    header, body = clean_rows[0], clean_rows[1:]
    alignment_values = list(alignments or [])
    alignment_values.extend([None] * (width - len(alignment_values)))
    separators = []
    for alignment in alignment_values[:width]:
        separators.append({
            "left": ":---",
            "right": "---:",
            "center": ":---:",
        }.get(alignment, "---"))
    output = [
        "| " + " | ".join(_escape_table_cell(cell) for cell in header) + " |",
        "| " + " | ".join(separators) + " |",
    ]
    output.extend(
        "| " + " | ".join(_escape_table_cell(cell) for cell in row) + " |"
        for row in body
    )
    return "\n".join(output)


def malformed_field_message(markdown: str) -> str | None:
    """Return a plain-English warning for an unmatched {{ or }} marker."""
    source = str(markdown or "")
    valid = [(match.start(), match.end()) for match in core.TOKEN.finditer(source)]
    for match in re.finditer(r"\{\{|\}\}", source):
        if not any(start <= match.start() and match.end() <= end for start, end in valid):
            line = source.count("\n", 0, match.start()) + 1
            return (
                f"Check the field placeholder on line {line}: its double braces do not "
                "match. A field should look like {{Field Name}}."
            )
    return None


def _markdown_is_editable(markdown: str) -> bool:
    """Keep constructs without safe editor controls read-only."""
    protected, _replacements = protect_fields(markdown)
    tokens = create_parser().parse(protected)
    allowed_blocks = {
        "paragraph_open", "paragraph_close", "heading_open", "heading_close",
        "inline", "bullet_list_open", "bullet_list_close", "ordered_list_open",
        "ordered_list_close", "list_item_open", "list_item_close", "table_open",
        "table_close", "thead_open", "thead_close", "tbody_open", "tbody_close",
        "tr_open", "tr_close", "th_open", "th_close", "td_open", "td_close",
    }
    allowed_inline = {
        "text", "softbreak", "hardbreak", "strong_open", "strong_close",
        "em_open", "em_close",
    }
    for token in tokens:
        if token.type not in allowed_blocks:
            return False
        if token.type == "inline":
            if any(child.type not in allowed_inline for child in (token.children or [])):
                return False
    return True


def _style_markdown_widget(widget: tk.Text, raw_view: bool = False) -> None:
    """Show a simple formatted editing surface while retaining Markdown in the Text buffer."""
    for name in ("syntax", "heading_1", "heading_2", "heading_3", "bold", "italic", "field"):
        widget.tag_remove(name, "1.0", "end")
    widget.tag_configure("syntax", elide=not raw_view)
    widget.tag_configure("heading_1", font=("TkDefaultFont", 16, "bold"))
    widget.tag_configure("heading_2", font=("TkDefaultFont", 14, "bold"))
    widget.tag_configure("heading_3", font=("TkDefaultFont", 12, "bold"))
    widget.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))
    widget.tag_configure("italic", font=("TkDefaultFont", 10, "italic"))
    widget.tag_configure("field", background="#fff0c2", foreground="#714d00")

    source = widget.get("1.0", "end-1c")
    offset = 0
    for line in source.splitlines(keepends=True):
        visible = line.rstrip("\r\n")
        line_start = offset
        if not visible:
            offset += len(line)
            continue
        heading = re.match(r"^(#{1,3})[ \t]+", visible)
        if heading:
            widget.tag_add(
                "syntax",
                f"1.0 + {line_start} chars",
                f"1.0 + {line_start + heading.end()} chars",
            )
            style = f"heading_{len(heading.group(1))}"
            widget.tag_add(
                style,
                f"1.0 + {line_start + heading.end()} chars",
                f"1.0 + {line_start + len(visible)} chars",
            )

        marker = re.match(r"^[ \t]*(?:[-+*]|\d{1,4}\.)[ \t]+", visible)
        if marker:
            widget.tag_add(
                "syntax",
                f"1.0 + {line_start} chars",
                f"1.0 + {line_start + marker.end()} chars",
            )

        if _is_markdown_table_separator(visible) and "|" in visible:
            widget.tag_add(
                "syntax",
                f"1.0 + {line_start} chars",
                f"1.0 + {line_start + len(visible)} chars",
            )
        elif "|" in visible:
            field_ranges = [
                (match.start(), match.end()) for match in core.TOKEN.finditer(visible)
            ]
            for pipe in re.finditer(r"(?<!\\)\|", visible):
                if not any(start <= pipe.start() < end for start, end in field_ranges):
                    widget.tag_add(
                        "syntax",
                        f"1.0 + {line_start + pipe.start()} chars",
                        f"1.0 + {line_start + pipe.end()} chars",
                    )

        for escape in re.finditer(r"\\(?=[\\*_{}\[\]()#+\-.!|>])", visible):
            widget.tag_add(
                "syntax",
                f"1.0 + {line_start + escape.start()} chars",
                f"1.0 + {line_start + escape.end()} chars",
            )

        field_ranges = [
            (match.start(), match.end()) for match in core.TOKEN.finditer(visible)
        ]
        for start, end in field_ranges:
            widget.tag_add(
                "field",
                f"1.0 + {line_start + start} chars",
                f"1.0 + {line_start + end} chars",
            )

        patterns = (
            (r"\*\*\*(.+?)\*\*\*", 3, 3),
            (r"\*\*(.+?)\*\*", 2, 2),
            (r"(?<!\*)\*([^*\n]+)\*(?!\*)", 1, 1),
            (r"___(.+?)___", 3, 3),
            (r"__(.+?)__", 2, 2),
            (r"(?<!_)_([^_\n]+)_(?!_)", 1, 1),
        )
        for pattern, marker_width, style_width in patterns:
            for match in re.finditer(pattern, visible):
                if any(
                    start < match.end() and end > match.start()
                    for start, end in field_ranges
                ):
                    continue
                content_start = match.start() + marker_width
                content_end = match.end() - marker_width
                if style_width == 3:
                    widget.tag_add(
                        "bold", f"1.0 + {line_start + content_start} chars",
                        f"1.0 + {line_start + content_end} chars",
                    )
                    widget.tag_add(
                        "italic", f"1.0 + {line_start + content_start} chars",
                        f"1.0 + {line_start + content_end} chars",
                    )
                elif style_width == 2:
                    widget.tag_add(
                        "bold", f"1.0 + {line_start + content_start} chars",
                        f"1.0 + {line_start + content_end} chars",
                    )
                else:
                    widget.tag_add(
                        "italic", f"1.0 + {line_start + content_start} chars",
                        f"1.0 + {line_start + content_end} chars",
                    )
                widget.tag_add(
                    "syntax", f"1.0 + {line_start + match.start()} chars",
                    f"1.0 + {line_start + content_start} chars",
                )
                widget.tag_add(
                    "syntax", f"1.0 + {line_start + content_end} chars",
                    f"1.0 + {line_start + match.end()} chars",
                )
        offset += len(line)




class TableEditorDialog:
    """Grid editor that serializes a table without requiring Markdown pipes."""

    def __init__(self, parent, rows, alignments, on_save):
        self.window = tk.Toplevel(parent)
        self.window.title("Edit table")
        self.window.geometry("760x520")
        self.window.minsize(520, 360)
        self.window.transient(parent)
        self.on_save = on_save
        self.alignments = list(alignments or [])
        self.rows = [list(row) for row in rows] or [["", ""], ["", ""]]
        width = max((len(row) for row in self.rows), default=2)
        self.rows = [row + [""] * (width - len(row)) for row in self.rows]
        self.entries = []

        outer = ttk.Frame(self.window, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer,
            text="Enter text in the cells. ContractBuilder will create the table for you.",
            wraplength=700,
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            outer,
            text="The first row is the table's column-heading row.",
        ).pack(anchor="w", pady=(0, 8))
        self.grid_frame = ttk.Frame(outer)
        self.grid_frame.pack(fill="both", expand=True)
        self._draw_grid()

        row_buttons = ttk.Frame(outer)
        row_buttons.pack(fill="x", pady=(8, 0))
        for label, command in (
            ("Add row", self.add_row),
            ("Remove last row", self.remove_row),
            ("Add column", self.add_column),
            ("Remove last column", self.remove_column),
        ):
            ttk.Button(row_buttons, text=label, command=command).pack(side="left", padx=(0, 5))
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(footer, text="Cancel", command=self.window.destroy).pack(side="right")
        ttk.Button(footer, text="Use table", command=self.save).pack(side="right", padx=(0, 8))
        self.window.grab_set()

    def _values(self):
        return [[entry.get() for entry in row] for row in self.entries]

    def _draw_grid(self):
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.entries = []
        width = max((len(row) for row in self.rows), default=1)
        for column in range(width):
            ttk.Label(self.grid_frame, text=f"Column {column + 1}").grid(
                row=0, column=column, sticky="w", padx=3, pady=(0, 4)
            )
            self.grid_frame.columnconfigure(column, weight=1, minsize=90)
        for row_index, row in enumerate(self.rows, 1):
            entries = []
            for column_index in range(width):
                value = row[column_index] if column_index < len(row) else ""
                entry = ttk.Entry(self.grid_frame, width=18)
                entry.insert(0, value)
                entry.grid(row=row_index, column=column_index, sticky="ew", padx=3, pady=3)
                entries.append(entry)
            self.entries.append(entries)

    def _capture(self):
        self.rows = self._values()

    def add_row(self):
        self._capture()
        self.rows.append([""] * max(1, len(self.rows[0]) if self.rows else 1))
        self._draw_grid()

    def remove_row(self):
        self._capture()
        if len(self.rows) > 1:
            self.rows.pop()
            self._draw_grid()

    def add_column(self):
        self._capture()
        for row in self.rows:
            row.append("")
        self.alignments.append(None)
        self._draw_grid()

    def remove_column(self):
        self._capture()
        if self.rows and len(self.rows[0]) > 1:
            for row in self.rows:
                row.pop()
            if self.alignments:
                self.alignments.pop()
            self._draw_grid()

    def save(self):
        try:
            markdown = build_markdown_table(
                self._values(),
                alignments=self.alignments,
            )
        except ValueError as exc:
            messagebox.showerror("Could not create table", str(exc), parent=self.window)
            return
        self.on_save(markdown)
        self.window.destroy()


class FieldInsertDialog:
    """Choose a known field and optional format before inserting its placeholder."""

    def __init__(self, parent, field_names, on_insert):
        self.window = tk.Toplevel(parent)
        self.window.title("Insert a field")
        self.window.transient(parent)
        self.window.resizable(False, False)
        self.on_insert = on_insert
        frame = ttk.Frame(self.window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Field name").grid(row=0, column=0, sticky="w", pady=4)
        self.name_variable = tk.StringVar(master=self.window)
        self.name_entry = ttk.Combobox(
            frame, textvariable=self.name_variable, values=field_names, width=38
        )
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=4)
        self.name_entry.focus_set()

        ttk.Label(frame, text="Format").grid(row=1, column=0, sticky="w", pady=4)
        self.format_variable = tk.StringVar(master=self.window, value="Plain text")
        self.format_values = {label: value for label, value in _FIELD_FORMATS}
        self.format_entry = ttk.Combobox(
            frame,
            textvariable=self.format_variable,
            values=[label for label, _value in _FIELD_FORMATS],
            state="readonly",
            width=38,
        )
        self.format_entry.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Options (for choice or singular/plural)").grid(
            row=2, column=0, sticky="w", pady=4
        )
        self.options_variable = tk.StringVar(master=self.window)
        ttk.Entry(frame, textvariable=self.options_variable, width=40).grid(
            row=2, column=1, sticky="ew", pady=4
        )
        self.status = ttk.Label(frame, text="", foreground="#8a5a00", wraplength=400)
        self.status.grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 8))
        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Cancel", command=self.window.destroy).pack(side="right")
        ttk.Button(buttons, text="Insert field", command=self.insert).pack(
            side="right", padx=(0, 8)
        )
        self.window.grab_set()

    def insert(self):
        label = self.format_variable.get()
        format_name = self.format_values.get(label, "")
        try:
            placeholder = make_field_placeholder(
                self.name_variable.get(), format_name, self.options_variable.get()
            )
        except ValueError as exc:
            self.status.configure(text=str(exc))
            return
        self.on_insert(placeholder)
        self.window.destroy()


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

        self.window = tk.Toplevel(editor.window)
        self.window.title("Review Word import")
        self.window.geometry("1080x720")
        self.window.minsize(820, 560)
        self.window.transient(editor.window)
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
        ttk.Button(footer, text="Cancel", command=self.window.destroy).pack(side="right")
        ttk.Button(footer, text="Save as component", command=self.save).pack(
            side="right", padx=(0, 8)
        )
        self._preview_after_id = None
        self._style_source()
        self._update_preview()
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        self.window.grab_set()

    def _configure_preview(self):
        self.preview.tag_configure("heading_1", font=("TkDefaultFont", 16, "bold"))
        self.preview.tag_configure("heading_2", font=("TkDefaultFont", 14, "bold"))
        self.preview.tag_configure("heading_3", font=("TkDefaultFont", 12, "bold"))
        self.preview.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))
        self.preview.tag_configure("italic", font=("TkDefaultFont", 10, "italic"))
        self.preview.tag_configure("field", background="#fff0c2", foreground="#714d00")
        self.preview.tag_configure("list_marker", foreground="#555555")
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
            segments = render_markdown_preview(source)
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

    def save(self):
        name = self.name_variable.get().strip()
        markdown = self.source.get("1.0", "end-1c")
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
            component_id = self.editor.library.create_component(name, markdown=markdown)
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
        self.editor_markdown_mode = False
        self.source_view_variable = None
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
        edit_frame.rowconfigure(1, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        panes.add(edit_frame, weight=1)
        panes.add(preview_frame, weight=1)

        toolbar = ttk.Frame(edit_frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        ttk.Button(toolbar, text="B", width=3, command=lambda: self.apply_format("bold")).pack(side="left", padx=(0, 2))
        ttk.Button(toolbar, text="I", width=3, command=lambda: self.apply_format("italic")).pack(side="left", padx=(0, 2))
        heading_button = ttk.Menubutton(toolbar, text="Heading")
        heading_menu = tk.Menu(heading_button, tearoff=False)
        for level in (1, 2, 3):
            heading_menu.add_command(
                label=f"Heading {level}",
                command=lambda selected=level: self.apply_format("heading", selected),
            )
        heading_button["menu"] = heading_menu
        heading_button.pack(side="left", padx=(0, 3))
        for label, action in (
            ("Bullets", "bullet"),
            ("Numbering", "numbered"),
            ("Indent", "indent"),
            ("Outdent", "outdent"),
            ("Table", "table"),
            ("Field", "field"),
            ("Import Word", "import"),
        ):
            command = {
                "table": self.open_table_editor,
                "field": self.open_field_dialog,
                "import": self.open_import_dialog,
            }.get(action)
            if command is None:
                command = lambda selected=action: self.apply_format(selected)
            ttk.Button(toolbar, text=label, command=command).pack(side="left", padx=(0, 2))
        self.source_view_variable = tk.BooleanVar(master=self.window, value=False)
        ttk.Checkbutton(
            toolbar,
            text="Advanced: show raw text",
            variable=self.source_view_variable,
            command=self.toggle_source_view,
        ).pack(side="left", padx=(5, 0))

        self.wording = tk.Text(
            edit_frame, wrap="word", undo=True, height=18,
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
        """Apply a toolbar operation to Markdown without asking the user to type syntax."""
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
        if action in {"bold", "italic"}:
            if selected:
                start, end = str(selected[0]), str(selected[1])
            else:
                start = widget.index("insert wordstart")
                end = widget.index("insert wordend")
                if widget.compare(start, "==", end):
                    marker = "**" if action == "bold" else "*"
                    widget.insert("insert", marker + marker)
                    widget.mark_set("insert", f"insert - {len(marker)} chars")
                    self._refresh_editor_styling()
                    self._schedule_preview()
                    widget.focus_set()
                    return "break"
            marker = "**" if action == "bold" else "*"
            value = widget.get(start, end)
            widget.delete(start, end)
            widget.insert(start, marker + value + marker)
            content_start = widget.index(f"{start} + {len(marker)} chars")
            content_end = widget.index(f"{content_start} + {len(value)} chars")
            widget.tag_remove("sel", "1.0", "end")
            widget.tag_add("sel", content_start, content_end)
            widget.mark_set("insert", content_end)
        else:
            if selected:
                first = widget.index(f"{selected[0]} linestart")
                last = widget.index(f"{selected[1]} lineend")
            else:
                first = widget.index("insert linestart")
                last = widget.index("insert lineend")
            block = widget.get(first, last)
            lines = block.splitlines()
            if not lines:
                return "break"

            def remove_marker(line):
                return re.sub(r"^([ \t]*)(?:[-+*]|\d{1,4}\.)[ \t]+", r"\1", line)

            transformed = []
            for line in lines:
                if not line.strip():
                    transformed.append(line)
                    continue
                indent = re.match(r"^[ \t]*", line).group(0)
                content = line[len(indent):]
                if action == "heading":
                    content = re.sub(r"^#{1,3}[ \t]+", "", content)
                    content = "#" * max(1, min(3, int(level))) + " " + content
                elif action == "bullet":
                    transformed.append(indent + "- " + remove_marker(content))
                    continue
                elif action == "numbered":
                    transformed.append(indent + "1. " + remove_marker(content))
                    continue
                elif action in {"indent", "outdent"}:
                    match = re.match(r"^(\d{1,4}\.)[ \t]+(.*)$", content)
                    if match:
                        if action == "indent":
                            indent += "    "
                        else:
                            indent = indent[4:] if indent.startswith("    ") else ""
                        transformed.append(indent + "1. " + match.group(2))
                        continue
                    transformed.append(line)
                    continue
                transformed.append(indent + content)
            replacement = "\n".join(transformed)
            widget.delete(first, last)
            widget.insert(first, replacement)
            widget.mark_set("insert", widget.index(f"{first} + {len(replacement)} chars"))
        self._refresh_editor_styling()
        self._schedule_preview()
        widget.focus_set()
        return "break"

    def _available_field_names(self):
        names = set(_PROFILE_FIELD_NAMES.values())
        try:
            for component in self.library.list_components():
                for version in self.library.list_component_versions(component["id"]):
                    for match in core.TOKEN.finditer(version["markdown"]):
                        kind, argument = core.classify(match.group(1))
                        if kind == "field":
                            name, _format_name, _options = core.parse_field(argument)
                            if name:
                                names.add(name)
        except (OSError, sqlite3.Error):
            pass
        return sorted(names, key=str.casefold)

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

        FieldInsertDialog(self.window, self._available_field_names(), insert)

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

        TableEditorDialog(self.window, rows, alignments, save_table)

    def open_import_dialog(self):
        path = filedialog.askopenfilename(
            parent=self.window,
            title="Import from a Word file",
            filetypes=(("Word documents", "*.docx"), ("All files", "*.*")),
        )
        if path:
            ImportReviewDialog(self, path)

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
        self._refresh_editor_styling()
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
        self.refresh_components(selected_id)

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
