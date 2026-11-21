"""Paragraph styles chosen per paragraph, kept beside the Markdown (T-061).

The wording of a component stays plain Markdown with no new syntax. A style
such as Title or Subtitle is a separate list stored with the component
version: one entry per *text paragraph* in order, where an empty entry means
Normal. A text paragraph is an ordinary top-level paragraph; headings, list
items and tables have their own styles already and are not counted.

Pure Python, no UI. The editor keeps the list in step with the text through
``sync_styles``; the converter reads it when the document is created.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional, Sequence

from markdown_fields import protect_fields, restore_fields
from md_parse import create_parser

NORMAL = "Normal"
# What the editor offers (plain names, as Word shows them). The layout file
# may define more; any name found in the file is also accepted.
STANDARD_STYLES = ("Normal", "Title", "Subtitle", "Body Text", "Block Text")


@dataclass(frozen=True)
class TextParagraph:
    """One text paragraph: its source text and first line (0-based)."""

    text: str
    first_line: int
    last_line: int  # exclusive


def text_paragraphs(markdown: str) -> List[TextParagraph]:
    """The ordinary top-level paragraphs of ``markdown``, in order."""
    protected, replacements = protect_fields(markdown or "")
    tokens = create_parser().parse(protected)
    restore_fields(tokens, replacements)
    found = []
    for index, token in enumerate(tokens):
        if token.type != "paragraph_open" or token.level != 0:
            continue
        inline = tokens[index + 1] if index + 1 < len(tokens) else None
        start, end = token.map or (0, 0)
        found.append(TextParagraph(
            inline.content if inline is not None and inline.type == "inline" else "",
            start, end,
        ))
    return found


def paragraph_index_at_line(markdown: str, line: int) -> Optional[int]:
    """Which text paragraph holds this 0-based line? None if none does."""
    for index, paragraph in enumerate(text_paragraphs(markdown)):
        if paragraph.first_line <= line < paragraph.last_line:
            return index
    return None


def normalize(styles: Sequence[Optional[str]]) -> List[str]:
    """Plain names, "Normal" written as "", no trailing empty entries."""
    clean = []
    for item in styles or ():
        name = str(item or "").strip()
        clean.append("" if name.casefold() == NORMAL.casefold() else name)
    while clean and not clean[-1]:
        clean.pop()
    return clean


def dump(styles: Sequence[Optional[str]]) -> str:
    """The stored form: JSON, or an empty string when every paragraph is Normal."""
    clean = normalize(styles)
    return json.dumps(clean, ensure_ascii=False) if clean else ""


def load(stored: Optional[str]) -> List[str]:
    """The list from its stored form; damaged data means "all Normal"."""
    if not stored:
        return []
    try:
        data = json.loads(stored)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return normalize([item for item in data if isinstance(item, str)])


def style_for(styles: Sequence[str], index: int) -> str:
    """The style of text paragraph ``index``; Normal when none is stored."""
    if 0 <= index < len(styles) and styles[index]:
        return styles[index]
    return NORMAL


def set_style(styles: Sequence[str], index: int, name: str) -> List[str]:
    """A new list with paragraph ``index`` set to ``name``."""
    updated = list(styles) + [""] * max(0, index + 1 - len(styles))
    updated[index] = "" if name.casefold() == NORMAL.casefold() else name
    return normalize(updated)


def sync_styles(
    old_paragraphs: Sequence[str],
    old_styles: Sequence[str],
    new_paragraphs: Sequence[str],
) -> List[str]:
    """Carry styles across an edit of the text.

    Paragraphs that did not change keep their style; an edit in place keeps it
    too. A paragraph that was split gives its style to both halves, a merge
    keeps the first one's style, and a brand-new paragraph is Normal. Moving a
    paragraph keeps its style when its text is unchanged and unique.
    """
    from difflib import SequenceMatcher

    old = list(old_paragraphs)
    result = [""] * len(new_paragraphs)
    matcher = SequenceMatcher(a=old, b=list(new_paragraphs), autojunk=False)
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(b1 - b0):
                result[b0 + offset] = style_for(old_styles, a0 + offset) if (
                    style_for(old_styles, a0 + offset) != NORMAL) else ""
        elif tag == "replace":
            before, after = a1 - a0, b1 - b0
            if before == after:                      # edited in place
                for offset in range(after):
                    name = style_for(old_styles, a0 + offset)
                    result[b0 + offset] = "" if name == NORMAL else name
            elif before == 1:                        # one paragraph became several
                name = style_for(old_styles, a0)
                for offset in range(after):
                    result[b0 + offset] = "" if name == NORMAL else name
            elif after == 1:                         # several became one
                name = style_for(old_styles, a0)
                result[b0] = "" if name == NORMAL else name
            else:                                    # mixed: keep what lines up
                for offset in range(min(before, after)):
                    name = style_for(old_styles, a0 + offset)
                    result[b0 + offset] = "" if name == NORMAL else name
        # "insert" leaves new paragraphs Normal; "delete" drops them.
    # A paragraph moved elsewhere with identical, unique text keeps its style.
    for new_index, text in enumerate(new_paragraphs):
        if result[new_index]:
            continue
        if old.count(text) == 1 and list(new_paragraphs).count(text) == 1:
            name = style_for(old_styles, old.index(text))
            if name != NORMAL:
                result[new_index] = name
    return normalize(result)
