"""What the formatted view shows, as plain text, for copying out (T-051).

*Pure*: no Tkinter, so its tests run without a display.

The formatted view hides Markdown syntax: escape backslashes, emphasis
markers, heading and list markers. Copying must give the text as shown. Field
placeholders such as ``{{Fee | money-words}}`` and conditional markers such as
``{{else}}`` are instructions to the document engine, not formatting, so they
are kept exactly as written.
"""
from __future__ import annotations

import re

from markdown_fields import protect_fields, restore_fields
from md_parse import create_parser

_LIST_OPEN = {"bullet_list_open": "bullet", "ordered_list_open": "ordered"}


def _inline_text(tokens) -> str:
    parts: list[str] = []
    for token in tokens or ():
        kind = getattr(token, "type", "")
        if kind in ("text", "code_inline"):
            parts.append(token.content)
        elif kind == "image":
            parts.append(token.content)
        elif kind in ("softbreak", "hardbreak"):
            parts.append("\n")
        # Emphasis, link and strikethrough markers carry no text of their own.
    return "".join(parts)


def visible_text(markdown: str) -> str:
    """Return the text a user sees in the formatted view of ``markdown``."""
    if not isinstance(markdown, str):
        raise TypeError("Component wording must be text.")

    protected, replacements = protect_fields(markdown)
    tokens = create_parser().parse(protected)
    restore_fields(tokens, replacements)

    out: list[str] = []
    lists: list[dict] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        kind = getattr(token, "type", "")
        if kind in _LIST_OPEN:
            # A nested list starts on its own line, below its parent item.
            if out and not "".join(out).endswith("\n"):
                out.append("\n")
            lists.append({"kind": _LIST_OPEN[kind], "next": 1})
        elif kind in ("bullet_list_close", "ordered_list_close"):
            if lists:
                lists.pop()
            out.append("\n")
        elif kind == "list_item_open":
            depth = max(0, len(lists) - 1)
            frame = lists[-1] if lists else {"kind": "bullet", "next": 1}
            if frame["kind"] == "ordered":
                label = f"{frame['next']}. "
                frame["next"] += 1
            else:
                label = "• "
            out.append("  " * depth + label)
        elif kind == "list_item_close":
            out.append("\n")
        elif kind == "inline":
            out.append(_inline_text(getattr(token, "children", None)))
        elif kind in ("paragraph_close", "heading_close", "blockquote_close"):
            # A paragraph inside a tight list item is hidden; its line ends at the item.
            if not getattr(token, "hidden", False):
                out.append("\n\n")
        elif kind in ("fence", "code_block"):
            out.append(token.content.rstrip("\n") + "\n\n")
        elif kind == "table_open":
            rows, index = _table_text(tokens, index)
            out.append(rows)
            continue
        index += 1

    text = "".join(out)
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)       # trailing spaces from hard breaks
    text = re.sub(r"\n{3,}", "\n\n", text)       # keep at most one blank line
    return text.strip("\n")


def _table_text(tokens, start: int) -> tuple[str, int]:
    """Rows as lines, cells separated by a tab, so a paste keeps the columns."""
    rows: list[list[str]] = []
    row: list[str] | None = None
    index = start + 1
    while index < len(tokens):
        token = tokens[index]
        kind = getattr(token, "type", "")
        if kind == "table_close":
            break
        if kind == "tr_open":
            row = []
        elif kind == "tr_close" and row is not None:
            rows.append(row)
            row = None
        elif kind == "inline" and row is not None:
            row.append(_inline_text(getattr(token, "children", None)).replace("\n", " "))
        index += 1
    text = "\n".join("\t".join(cells) for cells in rows) + "\n\n"
    return text, index + 1
