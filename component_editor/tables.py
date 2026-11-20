"""Pure Markdown table helpers: find, split and build GFM tables. No Tkinter."""
from __future__ import annotations

import re

import core


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
