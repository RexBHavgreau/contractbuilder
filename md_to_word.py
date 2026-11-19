"""Render Markdown components as native WordprocessingML.

Supports paragraphs, headings, inline emphasis, native Word lists and tables.
Unsupported constructs are reported instead of silently discarded.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import List, Sequence, Tuple, Union
import zipfile

from lxml import etree

from markdown_fields import protect_fields, restore_fields
from md_parse import create_parser
from shell_check import ShellFinding, check_shell

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
NS = {"w": W_NS}
_HTML_TAG = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")
_ALIGN = re.compile(r"text-align\s*:\s*(left|center|right)", re.I)


@dataclass(frozen=True)
class MarkdownWarning:
    """A supported-to-display but unsupported-to-format Markdown construct."""
    code: str
    message: str


@dataclass(frozen=True)
class MarkdownRenderResult:
    """WordprocessingML blocks and findings for one component.

    numbering contains new abstract definitions, when needed, and num
    instances referenced by returned paragraphs. A document composer must
    append these to the shell numbering part and remap numIds when combining
    independently rendered components.
    """
    elements: Tuple[etree._Element, ...]
    warnings: Tuple[MarkdownWarning, ...]
    errors: Tuple[ShellFinding, ...]
    numbering: Tuple[etree._Element, ...] = ()

    @property
    def can_generate(self) -> bool:
        return not self.errors


def _warn(warnings: List[MarkdownWarning], code: str, message: str) -> None:
    warnings.append(MarkdownWarning(code, message))


def _paragraph(style_id: str | None, alignment: str | None = None) -> etree._Element:
    paragraph = etree.Element(W + "p")
    if style_id or alignment:
        ppr = etree.SubElement(paragraph, W + "pPr")
        if style_id:
            style = etree.SubElement(ppr, W + "pStyle")
            style.set(W + "val", style_id)
        if alignment in ("left", "center", "right"):
            jc = etree.SubElement(ppr, W + "jc")
            jc.set(W + "val", alignment)
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
    bold_depth = italic_depth = 0
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
    depth = 0
    index = start
    while index < len(tokens):
        depth += getattr(tokens[index], "nesting", 0)
        index += 1
        if depth <= 0:
            break
    return index


def _tag(name: str) -> str:
    return W + name


def _attr(token: object, name: str):
    getter = getattr(token, "attrGet", None)
    if getter:
        value = getter(name)
        if value is not None:
            return value
    return (getattr(token, "attrs", None) or {}).get(name)


def _fallback_abstract(abstract_id: str, kind: str) -> etree._Element:
    abstract = etree.Element(W + "abstractNum")
    abstract.set(_tag("abstractNumId"), abstract_id)
    multi = etree.SubElement(abstract, W + "multiLevelType")
    multi.set(_tag("val"), "multilevel")
    labels = ("%1.", "%1.%2", "%1.%2.%3")
    glyphs = ("•", "◦", "▪")
    for level_number in range(3):
        level = etree.SubElement(abstract, W + "lvl")
        level.set(_tag("ilvl"), str(level_number))
        start = etree.SubElement(level, W + "start")
        start.set(_tag("val"), "1")
        fmt = etree.SubElement(level, W + "numFmt")
        fmt.set(_tag("val"), "bullet" if kind == "bullet" else "decimal")
        text = etree.SubElement(level, W + "lvlText")
        text.set(_tag("val"), glyphs[level_number] if kind == "bullet" else labels[level_number])
        justification = etree.SubElement(level, W + "lvlJc")
        justification.set(_tag("val"), "left")
        ppr = etree.SubElement(level, W + "pPr")
        ind = etree.SubElement(ppr, W + "ind")
        ind.set(_tag("left"), str(720 * (level_number + 1)))
        ind.set(_tag("hanging"), "360")
        if kind == "bullet":
            rpr = etree.SubElement(level, W + "rPr")
            fonts = etree.SubElement(rpr, W + "rFonts")
            fonts.set(_tag("ascii"), "Symbol")
            fonts.set(_tag("hAnsi"), "Symbol")
    return abstract


def _numbering_source(shell_path: Union[str, Path]):
    """Read the shell's active decimal-outline and bullet definitions."""
    with zipfile.ZipFile(str(shell_path), "r") as package:
        try:
            root = etree.fromstring(package.read("word/numbering.xml"))
        except KeyError:
            root = etree.Element(W + "numbering", nsmap={"w": W_NS})
    abstracts = root.findall("w:abstractNum", NS)
    nums = root.findall("w:num", NS)
    active = {item.get(_tag("val")) for item in root.findall("w:num/w:abstractNumId", NS)}
    decimal_id = bullet_id = None
    for abstract in abstracts:
        abstract_id = abstract.get(_tag("abstractNumId"))
        if abstract_id not in active:
            continue
        levels = {}
        for level in abstract.findall("w:lvl", NS):
            raw = level.get(_tag("ilvl"))
            if raw is None or not raw.isdigit():
                continue
            fmt = level.find("w:numFmt", NS)
            text = level.find("w:lvlText", NS)
            levels[int(raw)] = (
                fmt.get(_tag("val")) if fmt is not None else None,
                text.get(_tag("val")) if text is not None else None,
            )
            if bullet_id is None and fmt is not None and fmt.get(_tag("val")) == "bullet":
                bullet_id = abstract_id
        expected = (("decimal", "%1."), ("decimal", "%1.%2"), ("decimal", "%1.%2.%3"))
        if all(levels.get(i) == value for i, value in enumerate(expected)):
            decimal_id = abstract_id
    max_abstract = max([int(x.get(_tag("abstractNumId"))) for x in abstracts
                        if (x.get(_tag("abstractNumId")) or "").isdigit()] or [-1])
    max_num = max([int(x.get(_tag("numId"))) for x in nums
                   if (x.get(_tag("numId")) or "").isdigit()] or [0])
    additions = []
    if decimal_id is None:
        decimal_id = str(max_abstract + 1)
        additions.append(_fallback_abstract(decimal_id, "decimal"))
    if bullet_id is None:
        bullet_id = str(max_abstract + 1 + len(additions))
        additions.append(_fallback_abstract(bullet_id, "bullet"))
    return decimal_id, bullet_id, max_num, additions


def _new_num(abstract_id: str, num_id: int) -> etree._Element:
    number = etree.Element(W + "num")
    number.set(_tag("numId"), str(num_id))
    reference = etree.SubElement(number, W + "abstractNumId")
    reference.set(_tag("val"), abstract_id)
    return number


def _add_num_pr(paragraph: etree._Element, num_id: int, level: int) -> None:
    ppr = paragraph.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(W + "pPr")
        paragraph.insert(0, ppr)
    num_pr = etree.SubElement(ppr, W + "numPr")
    ilvl = etree.SubElement(num_pr, W + "ilvl")
    ilvl.set(_tag("val"), str(level))
    num = etree.SubElement(num_pr, W + "numId")
    num.set(_tag("val"), str(num_id))


def _table(tokens: Sequence[object], start: int, style_id: str | None,
           normal_style: str | None, warnings: List[MarkdownWarning]) -> Tuple[etree._Element, int]:
    rows = []
    in_header = False
    row = cell = None
    index = start + 1
    while index < len(tokens) and tokens[index].type != "table_close":
        token = tokens[index]
        kind = token.type
        if kind == "thead_open":
            in_header = True
        elif kind == "tbody_open":
            in_header = False
        elif kind == "tr_open":
            row = {"header": in_header, "cells": []}
            rows.append(row)
        elif kind in ("th_open", "td_open"):
            cell = {"children": (), "align": None}
            row["cells"].append(cell)
            raw_style = _attr(token, "style") or ""
            match = _ALIGN.search(raw_style)
            if match:
                cell["align"] = match.group(1).lower()
        elif kind == "inline" and cell is not None:
            cell["children"] = token.children or ()
        elif kind in ("th_close", "td_close"):
            cell = None
        index += 1

    column_count = max([len(item["cells"]) for item in rows] or [0])
    if column_count == 0:
        _warn(warnings, "markdown.table_empty", "An empty Markdown table was skipped.")
        return etree.Element(W + "tbl"), index + 1
    for item in rows:
        while len(item["cells"]) < column_count:
            item["cells"].append({"children": (), "align": None})

    table = etree.Element(W + "tbl")
    properties = etree.SubElement(table, W + "tblPr")
    if style_id:
        style = etree.SubElement(properties, W + "tblStyle")
        style.set(_tag("val"), style_id)
    grid = etree.SubElement(table, W + "tblGrid")
    width = max(1, 9000 // column_count)
    for _ in range(column_count):
        column = etree.SubElement(grid, W + "gridCol")
        column.set(_tag("w"), str(width))
    for row_data in rows:
        tr = etree.SubElement(table, W + "tr")
        if row_data["header"]:
            trpr = etree.SubElement(tr, W + "trPr")
            etree.SubElement(trpr, W + "tblHeader")
        for cell_data in row_data["cells"]:
            tc = etree.SubElement(tr, W + "tc")
            tcpr = etree.SubElement(tc, W + "tcPr")
            tcw = etree.SubElement(tcpr, W + "tcW")
            tcw.set(_tag("w"), str(width))
            tcw.set(_tag("type"), "dxa")
            paragraph = _paragraph(normal_style, cell_data["align"])
            _inline(paragraph, cell_data["children"], warnings)
            tc.append(paragraph)
    return table, index + 1


def render_markdown(source: str, shell_path: Union[str, Path]) -> MarkdownRenderResult:
    """Render one Markdown component using styles and numbering from its shell.

    The shell is checked read-only. Numbering definitions and instances are
    returned separately; the document composer must merge them into the
    shell's numbering part and remap numIds across component results.
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
    decimal_id, bullet_id, next_num_id, numbering_additions = _numbering_source(shell_path)
    numbering = list(numbering_additions)
    elements: List[etree._Element] = []
    list_stack = []

    def begin_list(ordered: bool) -> None:
        nonlocal next_num_id
        parent = list_stack[-1] if list_stack else None
        kind = "ordered" if ordered else "bullet"
        if parent and parent["kind"] == kind:
            num_id = parent["num_id"]
            level = min(parent["level"] + 1, 2)
        else:
            num_id = next_num_id
            next_num_id += 1
            numbering.append(_new_num(decimal_id if ordered else bullet_id, num_id))
            level = min(parent["level"] + 1, 2) if parent and parent["kind"] == "bullet" and ordered else 0
        list_stack.append({"kind": kind, "num_id": num_id, "level": level,
                           "first_paragraph": True, "in_item": False})

    index = 0
    while index < len(tokens):
        token = tokens[index]
        kind = token.type
        if kind in ("bullet_list_open", "ordered_list_open"):
            begin_list(kind == "ordered_list_open")
            index += 1
            continue
        if kind in ("bullet_list_close", "ordered_list_close"):
            if list_stack:
                list_stack.pop()
            index += 1
            continue
        if kind == "list_item_open":
            if list_stack:
                list_stack[-1]["in_item"] = True
                list_stack[-1]["first_paragraph"] = True
            index += 1
            continue
        if kind == "list_item_close":
            if list_stack:
                list_stack[-1]["in_item"] = False
            index += 1
            continue
        if kind in ("paragraph_open", "heading_open"):
            is_heading = kind == "heading_open"
            if is_heading:
                heading_level = int(token.tag[1:]) if token.tag and token.tag[1:].isdigit() else 1
                requested_style = "Heading%d" % min(max(heading_level, 1), 3)
            elif list_stack and list_stack[-1]["in_item"]:
                requested_style = "ListParagraph"
            else:
                requested_style = "Normal"
            style_id = shell.style_fallbacks.get(requested_style, requested_style)
            paragraph = _paragraph(style_id)
            if not is_heading and list_stack and list_stack[-1]["in_item"]:
                context = list_stack[-1]
                if context["first_paragraph"]:
                    _add_num_pr(paragraph, context["num_id"], context["level"])
                    context["first_paragraph"] = False
            index += 1
            if index < len(tokens) and tokens[index].type == "inline":
                _inline(paragraph, tokens[index].children or (), warnings)
                index += 1
            if index < len(tokens) and tokens[index].type in ("paragraph_close", "heading_close"):
                index += 1
            elements.append(paragraph)
            continue
        if kind == "table_open":
            style_id = shell.style_fallbacks.get("TableGrid", "TableGrid")
            normal_style = shell.style_fallbacks.get("Normal", "Normal")
            table, index = _table(tokens, index, style_id, normal_style, warnings)
            elements.append(table)
            continue
        if kind in ("paragraph_close", "heading_close", "inline"):
            index += 1
            continue
        if kind.endswith("_open") and getattr(token, "nesting", 0) == 1:
            _warn(warnings, "markdown.block_unsupported",
                  "This component contains a Markdown block type that is not supported yet; that block was not included in the Word output.")
            index = _skip_block(tokens, index)
        else:
            _warn(warnings, "markdown.block_unsupported",
                  "This component contains a Markdown block type that is not supported yet; that block was not included in the Word output.")
            index += 1
    return MarkdownRenderResult(tuple(elements), tuple(warnings), (), tuple(numbering))
