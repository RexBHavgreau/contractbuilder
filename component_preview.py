"""Lightweight, read-only Markdown preview for component wording.

This module uses the existing Markdown parser and field-protection helpers.
It returns styled text segments for a Tk Text widget; it does not render Word
pages, use a browser engine, or introduce another runtime dependency.
"""
from __future__ import annotations

from typing import Iterable, Sequence

from core import TOKEN, classify, parse_condition
from markdown_fields import protect_fields, restore_fields
from md_parse import create_parser


Segment = tuple[str, tuple[str, ...]]


def _append(segments: list[Segment], text: str, *tags: str) -> None:
    if not text:
        return
    tag_tuple = tuple(dict.fromkeys(tags))
    if segments and segments[-1][1] == tag_tuple:
        previous, previous_tags = segments[-1]
        segments[-1] = (previous + text, previous_tags)
    else:
        segments.append((text, tag_tuple))


PREVIEW_KEY = (
    "Highlighted text is a field, filled in when the document is made. "
    "Grey tags are choices in the wording, such as \u201cIf Publisher Type is "
    "Non-profit\u201d, \u201cOtherwise\u201d and \u201cEnd of choice\u201d. "
    "They are instructions and are not printed."
)


def marker_label(inner: str) -> tuple[str, str] | None:
    """Plain words for a conditional marker, or None if the text is a field.

    Returns (visible text, style tag). The raw syntax is never shown for markers.
    """
    kind, payload = classify(inner)
    if kind == "if":
        name, value, negate = parse_condition(payload)
        name = name or "this answer"
        if value is None:
            words = "is not filled in" if negate else "is filled in"
            return f"If {name} {words}", "marker_if"
        words = "is not" if negate else "is"
        return f"If {name} {words} {value}", "marker_if"
    if kind == "else":
        return "Otherwise", "marker_else"
    if kind == "end":
        return "End of choice", "marker_end"
    return None


def _field_aware_segments(text: str, styles: Sequence[str] = ()) -> list[Segment]:
    result: list[Segment] = []
    cursor = 0
    for match in TOKEN.finditer(text):
        _append(result, text[cursor:match.start()], *styles)
        marker = marker_label(match.group(1))
        if marker is None:
            _append(result, match.group(0), *styles, "field")
        else:
            label, marker_tag = marker
            # Thin spaces keep a tag from running into the words either side.
            _append(result, "\u2009" + label + "\u2009", *styles, "marker", marker_tag)
        cursor = match.end()
    _append(result, text[cursor:], *styles)
    return result


def _inline_segments(tokens: Iterable[object], styles: Sequence[str] = ()) -> list[Segment]:
    result: list[Segment] = []
    bold = False
    italic = False
    code = False
    link = False

    for token in tokens:
        kind = getattr(token, "type", "")
        content = getattr(token, "content", "")
        if kind == "strong_open":
            bold = True
        elif kind == "strong_close":
            bold = False
        elif kind == "em_open":
            italic = True
        elif kind == "em_close":
            italic = False
        elif kind == "code_inline":
            result.extend(_field_aware_segments(content, (*styles, "code")))
        elif kind == "link_open":
            link = True
        elif kind == "link_close":
            link = False
        elif kind == "text":
            effective = list(styles)
            if bold:
                effective.append("bold")
            if italic:
                effective.append("italic")
            if link:
                effective.append("link")
            result.extend(_field_aware_segments(content, effective))
        elif kind == "softbreak":
            _append(result, " ", *styles)
        elif kind == "hardbreak":
            _append(result, "\n", *styles)
        elif kind in ("html_inline", "image"):
            # HTML is disabled in the configured parser. If encountered,
            # show source text rather than interpreting it.
            visible = content or getattr(token, "content", "")
            _append(result, visible, *styles)
    return result


def _segments_text(segments: Sequence[Segment]) -> str:
    return "".join(text for text, _tags in segments)


def _table_rows(tokens: Sequence[object], start: int) -> tuple[list[list[tuple[list[Segment], bool]]], int]:
    rows: list[list[tuple[list[Segment], bool]]] = []
    row: list[tuple[list[Segment], bool]] | None = None
    cell_is_header = False
    index = start + 1

    while index < len(tokens):
        token = tokens[index]
        kind = getattr(token, "type", "")
        if kind == "table_close":
            if row:
                rows.append(row)
            return rows, index
        if kind == "tr_open":
            if row:
                rows.append(row)
            row = []
        elif kind in ("th_open", "td_open"):
            cell_is_header = kind == "th_open"
        elif kind == "inline" and row is not None:
            row.append((_inline_segments(getattr(token, "children", None) or ()), cell_is_header))
        index += 1

    if row:
        rows.append(row)
    return rows, len(tokens) - 1


def _render_table(rows: Sequence[Sequence[tuple[list[Segment], bool]]]) -> list[Segment]:
    if not rows:
        return []
    column_count = max((len(row) for row in rows), default=0)
    if not column_count:
        return []

    widths = [1] * column_count
    for row in rows:
        for column, (cell, _header) in enumerate(row):
            widths[column] = max(widths[column], len(_segments_text(cell)))

    result: list[Segment] = []

    def emit_row(row: Sequence[tuple[list[Segment], bool]]) -> None:
        _append(result, "| ", "table_border")
        for column in range(column_count):
            if column:
                _append(result, " | ", "table_border")
            if column < len(row):
                cell, header = row[column]
                style = "table_header" if header else "table_cell"
                _append(result, "", style)
                for value, tags in cell:
                    _append(result, value, *tags, style)
                padding = widths[column] - len(_segments_text(cell))
                _append(result, " " * padding, style)
            else:
                _append(result, " " * widths[column], "table_cell")
        _append(result, " |\n", "table_border")

    for index, row in enumerate(rows):
        emit_row(row)
        if index == 0 and any(header for _cell, header in row):
            _append(result, "|", "table_border")
            for column in range(column_count):
                if column:
                    _append(result, "+", "table_border")
                _append(result, "-" * (widths[column] + 2), "table_border")
            _append(result, "|\n", "table_border")

    _append(result, "\n")
    return result


def render_markdown_preview(markdown: str) -> list[Segment]:
    """Return a list of (text, style-tags) segments for a Tk Text widget."""
    if not isinstance(markdown, str):
        raise TypeError("Component wording must be text.")

    protected, replacements = protect_fields(markdown)
    parser = create_parser()
    tokens = parser.parse(protected)
    restore_fields(tokens, replacements)

    result: list[Segment] = []
    lists: list[dict[str, object]] = []
    heading_style: str | None = None
    in_blockquote = False

    def newline(blank: bool = False) -> None:
        existing = _segments_text(result)
        suffix = "\n\n" if blank else "\n"
        if existing.endswith("\n\n"):
            return
        if existing.endswith("\n"):
            if blank:
                _append(result, "\n")
        else:
            _append(result, suffix)

    index = 0
    while index < len(tokens):
        token = tokens[index]
        kind = getattr(token, "type", "")
        tag = getattr(token, "tag", "")

        if kind == "heading_open":
            heading_style = f"heading_{tag[1:]}" if tag.startswith("h") else "heading_2"
        elif kind == "heading_close":
            heading_style = None
            newline(blank=True)
        elif kind in ("bullet_list_open", "ordered_list_open"):
            attrs = getattr(token, "attrs", None) or {}
            start_number = 1
            if isinstance(attrs, dict):
                try:
                    start_number = int(attrs.get("start", 1))
                except (TypeError, ValueError):
                    start_number = 1
            lists.append({
                "kind": "ordered" if kind == "ordered_list_open" else "bullet",
                "next": start_number,
                "current": None,
            })
        elif kind in ("bullet_list_close", "ordered_list_close"):
            if lists:
                lists.pop()
            newline()
        elif kind == "list_item_open":
            depth = max(0, len(lists) - 1)
            if lists and lists[-1]["kind"] == "ordered":
                current = int(lists[-1]["next"])
                lists[-1]["current"] = current
                lists[-1]["next"] = current + 1
                outline = [
                    str(frame["current"])
                    for frame in lists
                    if frame["kind"] == "ordered" and frame["current"] is not None
                ]
                prefix = ".".join(outline) + ". "
            else:
                prefix = "  " * depth + "• "
            _append(result, prefix, "list_marker")
        elif kind == "list_item_close":
            newline()
        elif kind == "blockquote_open":
            in_blockquote = True
            _append(result, "│ ", "blockquote")
        elif kind == "blockquote_close":
            in_blockquote = False
            newline(blank=True)
        elif kind == "paragraph_close":
            newline(blank=not bool(lists))
        elif kind == "inline":
            styles = []
            if heading_style:
                styles.append(heading_style)
            if in_blockquote:
                styles.append("blockquote")
            for value, tags in _inline_segments(
                getattr(token, "children", None) or (), styles
            ):
                _append(result, value, *tags)
        elif kind in ("fence", "code_block"):
            if result and not _segments_text(result).endswith("\n"):
                newline()
            for line in getattr(token, "content", "").splitlines():
                for value, tags in _field_aware_segments(line, ("code_block",)):
                    _append(result, value, *tags)
                _append(result, "\n")
            newline(blank=True)
        elif kind == "hr":
            _append(result, "─" * 36 + "\n\n", "rule")
        elif kind == "table_open":
            rows, end_index = _table_rows(tokens, index)
            for value, tags in _render_table(rows):
                _append(result, value, *tags)
            index = end_index
        elif kind in ("html_block",):
            _append(result, getattr(token, "content", ""), "source_text")
            newline(blank=True)
        index += 1

    text = _segments_text(result)
    while text.endswith("\n\n\n"):
        # Keep the preview compact at block boundaries.
        last_text, last_tags = result[-1]
        result[-1] = (last_text.rstrip("\n") + "\n\n", last_tags)
        text = _segments_text(result)
    return result
