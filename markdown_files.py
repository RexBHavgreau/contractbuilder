"""Read and write standalone Markdown component files."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from md_parse import create_parser


@dataclass(frozen=True)
class MarkdownImport:
    """Markdown source and non-blocking warnings about unsupported constructs."""

    text: str
    warnings: tuple[str, ...]


_FOOTNOTE_REFERENCE = re.compile(r"\[\^[^\]]+\]")
_FOOTNOTE_DEFINITION = re.compile(r"^\s*\[\^[^\]]+\]:", re.MULTILINE)


def inspect_markdown(text: str) -> MarkdownImport:
    """Return source unchanged and warn about constructs outside the component subset."""
    tokens = create_parser().parse(text)
    warnings = []
    if any(token.type in {"html_block", "html_inline"} for token in tokens):
        warnings.append("Raw HTML is not supported; it will be kept as source text.")
    if any(token.type == "image" for token in tokens):
        warnings.append("Images are not supported; image markup will be kept as source text.")
    if _FOOTNOTE_REFERENCE.search(text) or _FOOTNOTE_DEFINITION.search(text):
        warnings.append("Footnotes are not supported; footnote markup will be kept as source text.")
    return MarkdownImport(text=text, warnings=tuple(warnings))


def read_markdown_file(path: str | Path) -> MarkdownImport:
    """Read UTF-8 Markdown, accepting and removing an optional UTF-8 BOM."""
    source = Path(path).read_text(encoding="utf-8-sig")
    return inspect_markdown(source)


def write_markdown_file(path: str | Path, text: str) -> None:
    """Write Markdown as UTF-8 without a BOM, preserving the source exactly."""
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        stream.write(text)
