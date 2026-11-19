"""Render the supported Markdown component subset as WordprocessingML.

The renderer deliberately handles only paragraphs, headings 1--3, line
breaks, bold and italic. Other constructs are reported as warnings instead
of being silently treated as supported content.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import List, Sequence, Tuple, Union

from lxml import etree

from markdown_fields import protect_fields, restore_fields
from md_parse import create_parser
from shell_check import ShellFinding, check_shell

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
NS = {"w": W_NS}
_HTML_TAG = re.compile(r"<\\s*/?\\s*[A-Za-z][^>]*>")


@dataclass(frozen=True)
class MarkdownWarning:
    """A supported-to-display but unsupported-to-format Markdown construct."""

    code: str
    message: str


@dataclass(frozen=True)
class MarkdownRenderResult:
    """WordprocessingML blocks and all findings from one component."""

    elements: Tuple[etree._Element, ...]
    warnings: Tuple[MarkdownWarning, ...]
    errors: Tuple[ShellFinding, ...]

    @property
    def can_generate(self) -> bool:
        return not self.errors


def _warn(warnings: List[MarkdownWarning], code: str, message: str) -> None:
    warnings.append(MarkdownWarning(code, message))


def _paragraph(style_id: str | None) -> etree._Element:
    paragraph = etree.Element(W + "p")
    if style_id:
        ppr = etree.SubElement(paragraph, W + "pPr")
        style = etree.SubElement(ppr, W + "pStyle")
        style.set(W + "val", style_id)
    return paragraph


def _run(paragraph: etree._Element, text: str, bold: bool, italic: bool) -> None:
    if not text:
        return
    run = etree.SubElement(paragraph, W + "r")
    if bold or italic:
        properties = etree.SubElement(run, W + "rPr")
        if bold:
            etree.SubElement(properties, W + "b")
        if italic:
            etree.SubElement(properties, W + "i")
    node = etree.SubElement(run, W + "t")
    if text[:1].isspace() or text[-1:].isspace():
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    node.text = text


def _line_break(paragraph: etree._Element) -> None:
    run = etree.SubElement(paragraph, W + "r")
    etree.SubElement(run, W + "br")


def _inline(paragraph: etree._Element, children: Sequence[object],
            warnings: List[MarkdownWarning]) -> None:
    bold_depth = 0
    italic_depth = 0
    for token in children:
        kind = getattr(token, "type", "")
        content = getattr(token, "content", "")
        if kind == "strong_open":
            bold_depth += 1
        elif kind == "strong_close":
            bold_depth = max(0, bold_depth - 1)
        elif kind == "em_open":
            italic_depth += 1
        elif kind == "em_close":
            italic_depth = max(0, italic_depth - 1)
        elif kind == "text":
            if _HTML_TAG.search(content):
                _warn(warnings, "markdown.raw_html",
                      "HTML-like text is kept as plain text; HTML formatting is not supported.")
            _run(paragraph, content, bold_depth > 0, italic_depth > 0)
        elif kind == "softbreak":
            _run(paragraph, " ", bold_depth > 0, italic_depth > 0)
        elif kind == "hardbreak":
            _line_break(paragraph)
        elif kind == "code_inline":
            _warn(warnings, "markdown.inline_code",
                  "Inline code formatting is not supported; the text is kept without code styling.")
            _run(paragraph, content, bold_depth > 0, italic_depth > 0)
        elif kind == "image":
            _warn(warnings, "markdown.image",
                  "Images are not supported in components; only the image's alternative text is kept.")
            alt = "".join(getattr(child, "content", "") for child in (getattr(token, "children", None) or ()))
            _run(paragraph, alt or content, bold_depth > 0, italic_depth > 0)
        elif kind == "link_open":
            _warn(warnings, "markdown.link",
                  "Links are not supported in components yet; the link text is kept without a link.")
        elif kind == "html_inline":
            _warn(warnings, "markdown.raw_html",
                  "HTML formatting is not supported; the text is kept without HTML formatting.")
            _run(paragraph, content, bold_depth > 0, italic_depth > 0)
        elif kind == "link_close":
            continue
        elif content:
            _warn(warnings, "markdown.inline_unsupported",
                  "A Markdown inline feature is not supported; its text is kept without special formatting.")
            _run(paragraph, content, bold_depth > 0, italic_depth > 0)


def _skip_block(tokens: Sequence[object], start: int) -> int:
    """Return the index after an unsupported block and its nested tokens."""
    depth = 0
    index = start
    while index < len(tokens):
        depth += getattr(tokens[index], "nesting", 0)
        index += 1
        if depth <= 0:
            break
    return index


def render_markdown(source: str, shell_path: Union[str, Path]) -> MarkdownRenderResult:
    """Render one Markdown component using style IDs validated in its shell.

    The shell is checked read-only. An unusable shell returns errors and no
    blocks. Shell warnings are retained alongside Markdown warnings so the
    caller can show every fallback before generating a document.
    """
    if not isinstance(source, str):
        raise TypeError("Markdown component source must be text")

    shell = check_shell(shell_path)
    if not shell.can_generate:
        return MarkdownRenderResult((), (), shell.errors)

    warnings = [MarkdownWarning(item.code, item.message) for item in shell.warnings]
    protected, replacements = protect_fields(source)
    tokens = create_parser().parse(protected)
    restore_fields(tokens, replacements)

    elements: List[etree._Element] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        kind = token.type
        if kind in ("paragraph_open", "heading_open"):
            is_heading = kind == "heading_open"
            if is_heading:
                level = int(token.tag[1:]) if token.tag and token.tag[1:].isdigit() else 1
                requested_style = "Heading%d" % min(max(level, 1), 3)
            else:
                requested_style = "Normal"
            style_id = shell.style_fallbacks.get(requested_style, requested_style)
            paragraph = _paragraph(style_id)
            index += 1
            if index < len(tokens) and tokens[index].type == "inline":
                _inline(paragraph, tokens[index].children or (), warnings)
                index += 1
            if index < len(tokens) and tokens[index].type in ("paragraph_close", "heading_close"):
                index += 1
            elements.append(paragraph)
            continue

        if kind in ("paragraph_close", "heading_close", "inline"):
            index += 1
            continue

        # Lists, tables, quotes, code blocks, raw HTML and thematic breaks are
        # intentionally deferred to their own tasks. Never silently discard.
        if kind.endswith("_open") and getattr(token, "nesting", 0) == 1:
            _warn(warnings, "markdown.block_unsupported",
                  "This component contains a Markdown block type that is not supported yet; that block was not included in the Word output.")
            index = _skip_block(tokens, index)
        else:
            _warn(warnings, "markdown.block_unsupported",
                  "This component contains a Markdown block type that is not supported yet; that block was not included in the Word output.")
            index += 1

    return MarkdownRenderResult(tuple(elements), tuple(warnings), ())
