"""The section headings of the user guide, as a hierarchy (for the Help window).

Pure and Tkinter-free. The guide is plain text with two kinds of heading:

- a line in capitals, such as ``PRIVACY``, is a main section (level 1);
- a numbered capital line, such as ``2. FILL IN THE FIELDS``, or a title line
  followed by a dashed underline, such as ``A worked example``, is a step or
  subsection (level 2) that belongs to the main section above it.

The title block at the top (the lines before the first blank line) is not a
section.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_CAPITALS = re.compile(r"[A-Z0-9][A-Z0-9 ,:'’()/&.\-]{3,}")
_NUMBERED = re.compile(r"\d+\.\s+[A-Z]")
_UNDERLINE = re.compile(r"-{3,}")


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    line: int  # 1-based line number in the guide text


def outline(text: str) -> list[Heading]:
    lines = text.split("\n")
    try:
        start = lines.index("")  # the title block ends at the first blank line
    except ValueError:
        return []
    headings: list[Heading] = []
    for index in range(start + 1, len(lines)):
        line = lines[index].strip()
        if not line:
            continue
        # A heading always follows a blank line; a capitals line inside a sentence does not.
        if lines[index - 1].strip():
            continue
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if _CAPITALS.fullmatch(line) and not _UNDERLINE.fullmatch(line):
            level = 2 if _NUMBERED.match(line) else 1
            headings.append(Heading(level, line, index + 1))
        elif _UNDERLINE.fullmatch(next_line) and not _UNDERLINE.fullmatch(line):
            headings.append(Heading(2, line, index + 1))
    return headings
