"""Choosing part of a Word document to import (T-064-C).

Pure Python, no Tkinter, so the rules are tested without a display. The
document arrives as blocks (``docx_to_markdown.DocxBlock``, T-064-A): headings,
ordinary paragraphs, whole lists and whole tables, in order. The user ticks some
of them; ``selection_import`` turns the ticked blocks into the same kind of
result as importing the whole file, so the existing review window can take it:
their Markdown joined with blank lines, their warnings, and the paragraph
styles kept beside the wording (T-061).
"""
from __future__ import annotations

from typing import Sequence

from component_editor.copy_text import visible_text
from docx_to_markdown import (
    _KNOWN_PARAGRAPH_STYLES, DocxBlock, DocxImport, DocxImportWarning, _importable_styles,
)

_IGNORED_STYLE_NAMES = ("normal", "default paragraph font")


def block_label(block: DocxBlock) -> str:
    """A short plain name for a block: Heading 2, Paragraph, List, Table."""
    if block.kind == "heading":
        return f"Heading {block.level}"
    if block.kind == "paragraph":
        offered = _KNOWN_PARAGRAPH_STYLES.get(block.style.casefold())
        return offered if offered else "Paragraph"
    return {"list": "List", "table": "Table"}.get(block.kind, block.kind.title())


def block_preview(block: DocxBlock, limit: int = 100) -> str:
    """The block's first line as it reads, without Markdown marks, shortened."""
    lines = [line.strip() for line in visible_text(block.markdown).splitlines() if line.strip()]
    text = lines[0] if lines else ""
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _block_warning_ids(blocks: Sequence[DocxBlock]) -> set:
    return {id(w) for block in blocks for w in block.warnings}


def selection_import(imported: DocxImport, chosen: Sequence[int]) -> DocxImport:
    """The import result for only the ticked blocks (indexes into ``imported.blocks``)."""
    order = sorted({int(i) for i in chosen if 0 <= int(i) < len(imported.blocks)})
    picked = [imported.blocks[i] for i in order]
    markdown = "\n\n".join(block.markdown for block in picked)

    # Document-level notes (headers, footers, comments...) still apply to a
    # part. Notes attached to a block follow that block. The whole-file note
    # about styles the editor does not offer is recomputed for just these blocks.
    attached = _block_warning_ids(imported.blocks)
    kept = [
        w for w in imported.warnings
        if id(w) not in attached and not w.location.startswith("style ")
    ]
    for block in picked:
        kept.extend(block.warnings)

    text_styles = []
    unoffered: dict = {}
    for block in picked:
        if block.kind != "paragraph":
            continue
        offered = _KNOWN_PARAGRAPH_STYLES.get(block.style.casefold(), "")
        text_styles.append(offered)
        name = block.style
        if (
            name and not offered
            and name.casefold() not in _IGNORED_STYLE_NAMES
            and not name.casefold().startswith("heading")
        ):
            unoffered[name] = unoffered.get(name, 0) + 1
    for name, count in sorted(unoffered.items()):
        kept.append(DocxImportWarning(
            "%d paragraph%s use%s the Word style '%s', which the editor does not offer, so "
            "%s imported as Normal." % (
                count, "" if count == 1 else "s", "s" if count == 1 else "", name,
                "it is" if count == 1 else "they are"),
            "style " + name,
        ))
    return DocxImport(
        markdown=markdown, warnings=tuple(kept),
        paragraph_styles=_importable_styles(markdown, text_styles),
        blocks=tuple(picked),
    )


def selection_notes(blocks: Sequence[DocxBlock], chosen: Sequence[int]) -> list[str]:
    """Plain-English things to know about this particular choice.

    Lists and tables are chosen whole. What can still surprise: blocks left out
    between the first and last one ticked, and a numbered list taken without
    the list it continued (its numbers then start again at 1).
    """
    order = sorted({int(i) for i in chosen if 0 <= int(i) < len(blocks)})
    if not order:
        return []
    notes = []
    skipped = [i for i in range(order[0], order[-1] + 1) if i not in order]
    if skipped:
        notes.append(
            f"{len(skipped)} block{'s' if len(skipped) != 1 else ''} between your first and "
            "last choice are not ticked, so they are left out of the component."
        )
    for index in order:
        block = blocks[index]
        if block.kind == "list" and block.markdown.lstrip()[:1].isdigit():
            if index > 0 and blocks[index - 1].kind == "list" and (index - 1) not in order:
                notes.append(
                    "A numbered list is taken without the list just before it, "
                    "so its numbers start again at 1."
                )
                break
    return notes
