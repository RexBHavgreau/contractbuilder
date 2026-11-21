"""Read and write standalone Markdown component files."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from md_parse import create_parser


@dataclass(frozen=True)
class MarkdownImport:
    """Markdown source and non-blocking warnings about unsupported constructs."""

    text: str
    warnings: tuple[str, ...]
    metadata: dict | None = None


_FOOTNOTE_REFERENCE = re.compile(r"\[\^[^\]]+\]")
_FOOTNOTE_DEFINITION = re.compile(r"^\s*\[\^[^\]]+\]:", re.MULTILINE)
_COMPONENT_HEADER = re.compile(r"\A---\r?\nContractBuilder-Component:\s*(.+?)\r?\n---\r?\n(?:\r?\n)?")
_COMPONENT_FORMAT = "contractbuilder-component"
_COMPONENT_FORMAT_VERSION = 1
_HTML_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s+[^<>]*?)?\s*/?>")


def _walk_tokens(tokens):
    """Yield block and inline child tokens from markdown-it-py."""
    for token in tokens:
        yield token
        if token.children:
            yield from _walk_tokens(token.children)


def inspect_markdown(text: str, metadata: dict | None = None) -> MarkdownImport:
    """Return source unchanged and warn about constructs outside the component subset."""
    tokens = tuple(_walk_tokens(create_parser().parse(text)))
    warnings = []
    # html=False intentionally prevents HTML from becoming renderable tokens;
    # inspect the original source as well so disabling HTML does not hide it.
    if _HTML_TAG.search(text) or any(
        token.type in {"html_block", "html_inline"} for token in tokens
    ):
        warnings.append("Raw HTML is not supported; it will be kept as source text.")
    if any(token.type == "image" for token in tokens):
        warnings.append("Images are not supported; image markup will be kept as source text.")
    if _FOOTNOTE_REFERENCE.search(text) or _FOOTNOTE_DEFINITION.search(text):
        warnings.append("Footnotes are not supported; footnote markup will be kept as source text.")
    return MarkdownImport(text=text, warnings=tuple(warnings), metadata=metadata)


def read_markdown_file(path: str | Path) -> MarkdownImport:
    """Read UTF-8 Markdown, accepting and removing an optional UTF-8 BOM."""
    source = Path(path).read_text(encoding="utf-8-sig")
    metadata = None
    header = _COMPONENT_HEADER.match(source)
    if header:
        try:
            candidate = json.loads(header.group(1))
            if (
                isinstance(candidate, dict)
                and candidate.get("format") == _COMPONENT_FORMAT
                and candidate.get("version") == _COMPONENT_FORMAT_VERSION
                and isinstance(candidate.get("component"), dict)
                and isinstance(candidate.get("saved_version"), dict)
            ):
                metadata = candidate
                source = source[header.end():]
        except (TypeError, ValueError):
            pass
    return inspect_markdown(source, metadata=metadata)


def write_markdown_file(path: str | Path, text: str) -> None:
    """Write plain Markdown as UTF-8 without a BOM, preserving source exactly."""
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        stream.write(text)


def write_component_markdown_file(
    path: str | Path,
    text: str,
    component: dict,
    saved_version: dict,
) -> None:
    """Write a component with a JSON metadata record in simple Markdown front matter."""
    metadata = {
        "format": _COMPONENT_FORMAT,
        "version": _COMPONENT_FORMAT_VERSION,
        "component": {
            key: component.get(key)
            for key in ("id", "name", "description", "category", "tags", "status")
        },
        "saved_version": {
            key: saved_version.get(key)
            for key in ("id", "number", "created", "note", "paragraph_styles")
        },
    }
    compact = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
    header = "---\nContractBuilder-Component: " + compact + "\n---\n\n"
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        stream.write(header)
        stream.write(text)
