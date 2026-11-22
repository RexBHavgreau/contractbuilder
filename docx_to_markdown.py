"""Read DOCX body content in document order as a plain Markdown draft.

The importer is deliberately read-only. Unsupported Word structures are
reported with locations; tracked changes use Word's accepted (final) text.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import zipfile

from lxml import etree

from safe_hyperlinks import safe_hyperlink_target


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
HYPERLINK_REL = R_NS + "/hyperlink"
NS = {"w": W_NS}
W = f"{{{W_NS}}}"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
M = f"{{{M_NS}}}"

# Keep the same token boundary rules as core.py: Word may put any part of a
# field or conditional marker in a separate run.
TOKEN = re.compile(r"\{\{((?:(?!\{\{|\}\}).)*)\}\}", re.S)
HEADING_STYLE = re.compile(r"^heading\s*([1-9])$", re.I)
TYPED_LIST_MARKER = re.compile(r"^\s*(?:\d{1,4}[.)]|[A-Za-z][.)])\s+")
LETTER_ROMAN_FORMATS = {"lowerLetter", "upperLetter", "lowerRoman", "upperRoman"}


class DocxImportError(ValueError):
    """A DOCX file could not be read, explained for an ordinary user."""


@dataclass(frozen=True)
class DocxImportWarning:
    """A non-blocking observation about content not represented in this draft."""

    message: str
    location: str


@dataclass(frozen=True)
class DocxBlock:
    """One block of the draft, with its place in the Word file (T-064-A).

    ``kind`` is "heading", "paragraph", "list" or "table". ``markdown`` is the
    block's own Markdown; joining the blocks with blank lines gives the draft's
    ``markdown``. ``position`` is the block's index among the children of the
    Word body. ``paragraph_numbers`` are the body paragraph numbers the block
    came from (empty for a table, which is found by ``position``).
    """

    kind: str
    markdown: str
    style: str
    level: int | None
    position: int
    paragraph_numbers: tuple[int, ...]
    warnings: tuple["DocxImportWarning", ...]


@dataclass(frozen=True)
class DocxImport:
    """Markdown draft and any non-blocking import warnings."""

    markdown: str
    warnings: tuple[DocxImportWarning, ...]
    # One entry per ordinary top-level paragraph, in order ("" = Normal): the
    # Word style names the app also offers (T-061). Kept beside the Markdown.
    paragraph_styles: tuple[str, ...] = ()
    # The same content as ``markdown``, one entry per block, in order (T-064-A).
    blocks: tuple[DocxBlock, ...] = ()


# Word style names (any capitals) the editor offers as paragraph styles.
_KNOWN_PARAGRAPH_STYLES = {
    "title": "Title", "subtitle": "Subtitle",
    "body text": "Body Text", "block text": "Block Text",
}


def _enabled(element) -> bool:
    return element is not None and element.get(W + "val", "true").lower() not in {
        "false", "0", "off", "none"
    }


def _value(parent, tag, default=None):
    element = parent.find("w:" + tag, NS) if parent is not None else None
    return element.get(W + "val", default) if element is not None else default


def _read_styles(xml: bytes | None) -> dict:
    """Index paragraph and character styles by their Word style IDs."""
    if not xml:
        return {}
    root = etree.fromstring(xml)
    styles = {}
    for style in root.findall("w:style", NS):
        style_id = style.get(W + "styleId")
        if not style_id:
            continue
        styles[style_id] = {
            "type": style.get(W + "type"),
            "name": _value(style, "name", ""),
            "based_on": _value(style, "basedOn"),
            "element": style,
        }
    return styles


def _style_chain(styles: dict, style_id):
    seen = set()
    while style_id and style_id not in seen:
        seen.add(style_id)
        entry = styles.get(style_id)
        if entry is None:
            break
        yield entry["element"]
        style_id = entry["based_on"]


def _style_property(styles: dict, style_id, property_name):
    for style in _style_chain(styles, style_id):
        rpr = style.find("w:rPr", NS)
        if rpr is not None:
            element = rpr.find("w:" + property_name, NS)
            if element is not None:
                return element
    return None


def _paragraph_style_id(paragraph):
    ppr = paragraph.find("w:pPr", NS)
    pstyle = ppr.find("w:pStyle", NS) if ppr is not None else None
    return pstyle.get(W + "val") if pstyle is not None else None


def _heading_level(paragraph, styles: dict):
    """Return the Word outline level as 1-based, or None for ordinary text."""
    ppr = paragraph.find("w:pPr", NS)
    direct_outline = ppr.find("w:outlineLvl", NS) if ppr is not None else None
    if direct_outline is not None:
        try:
            value = int(direct_outline.get(W + "val", "0"))
            return None if value >= 9 else value + 1
        except ValueError:
            return None

    style_id = _paragraph_style_id(paragraph)
    for style in _style_chain(styles, style_id):
        name = _value(style, "name", "")
        match = HEADING_STYLE.match(name.strip())
        if match:
            return int(match.group(1))
        style_id = style.get(W + "styleId")
        match = HEADING_STYLE.match((style_id or "").replace("_", " "))
        if match:
            return int(match.group(1))
        style_ppr = style.find("w:pPr", NS)
        outline = style_ppr.find("w:outlineLvl", NS) if style_ppr is not None else None
        if outline is not None:
            try:
                value = int(outline.get(W + "val", "0"))
                return None if value >= 9 else value + 1
            except ValueError:
                return None
    return None


def _numbering_maps(xml: bytes | None):
    """Return numId -> abstract numbering and its level definitions."""
    if not xml:
        return {}
    root = etree.fromstring(xml)
    abstracts = {}
    for abstract in root.findall("w:abstractNum", NS):
        abstract_id = abstract.get(W + "abstractNumId")
        if abstract_id is None:
            continue
        levels = {}
        for level in abstract.findall("w:lvl", NS):
            try:
                ilvl = int(level.get(W + "ilvl", "0"))
            except ValueError:
                continue
            levels[ilvl] = {
                "format": _value(level, "numFmt", "decimal"),
                "text": _value(level, "lvlText", ""),
            }
        abstracts[abstract_id] = levels

    numbers = {}
    for number in root.findall("w:num", NS):
        num_id = number.get(W + "numId")
        abstract_id = _value(number, "abstractNumId")
        overrides = {}
        for override in number.findall("w:lvlOverride", NS):
            try:
                ilvl = int(override.get(W + "ilvl", "0"))
            except ValueError:
                continue
            level = override.find("w:lvl", NS)
            if level is not None:
                overrides[ilvl] = {
                    "format": _value(level, "numFmt", "decimal"),
                    "text": _value(level, "lvlText", ""),
                }
        if num_id is not None:
            numbers[num_id] = {
                "levels": abstracts.get(abstract_id, {}),
                "overrides": overrides,
            }
    return numbers


def _paragraph_numpr(paragraph, styles: dict):
    """Merge direct numbering properties with those inherited from the style."""
    ppr = paragraph.find("w:pPr", NS)
    numpr = ppr.find("w:numPr", NS) if ppr is not None else None
    num_id = _value(numpr, "numId")
    ilvl = _value(numpr, "ilvl")

    # Word commonly puts numId on a paragraph style and only an ilvl on the
    # paragraph itself. Treating those as separate would miss a real list.
    for style in _style_chain(styles, _paragraph_style_id(paragraph)):
        style_ppr = style.find("w:pPr", NS)
        style_numpr = style_ppr.find("w:numPr", NS) if style_ppr is not None else None
        if style_numpr is None:
            continue
        if num_id is None:
            num_id = _value(style_numpr, "numId")
        if ilvl is None:
            ilvl = _value(style_numpr, "ilvl")
        if num_id is not None:
            break

    if num_id is None:
        return None
    try:
        return num_id, int(ilvl or 0)
    except ValueError:
        return None


def _list_info(paragraph, styles: dict, numbering: dict):
    numbered = _paragraph_numpr(paragraph, styles)
    if numbered is None:
        return None
    num_id, level = numbered
    if str(num_id) == "0":
        return None
    number = numbering.get(str(num_id), {})
    level_data = number.get("overrides", {}).get(level)
    if level_data is None:
        level_data = number.get("levels", {}).get(level, {})
    num_format = level_data.get("format", "decimal")
    if num_format == "none":
        return None
    return {
        "num_id": str(num_id),
        "level": max(0, min(level, 8)),
        "format": num_format,
        "kind": "bullet" if num_format == "bullet" else "ordered",
    }


def _run_flag(run, styles: dict, property_name: str) -> bool:
    rpr = run.find("w:rPr", NS)
    direct = rpr.find("w:" + property_name, NS) if rpr is not None else None
    if direct is not None:
        return _enabled(direct)
    style_id = _value(rpr, "rStyle")
    inherited = _style_property(styles, style_id, property_name)
    return _enabled(inherited)


def _read_relationships(xml: bytes | None) -> dict:
    """Index the main document's package relationships by ID."""
    if not xml:
        return {}
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    root = etree.fromstring(xml, parser)
    relationships = {}
    for item in root.findall("{%s}Relationship" % PKG_REL_NS):
        relationship_id = item.get("Id")
        if relationship_id:
            relationships[relationship_id] = {
                "type": item.get("Type"),
                "target": item.get("Target"),
                "mode": item.get("TargetMode"),
            }
    return relationships


def _paragraph_segments(
    paragraph, styles: dict, relationships: dict | None = None,
    warnings: list | None = None, location: str = "paragraph",
):
    """Read visible text with effective emphasis and safe hyperlink targets."""
    relationships = relationships or {}
    segments = []
    warned_links = set()

    def add(value, flags, link_target):
        if value:
            segments.append({
                "text": value, "bold": flags[0], "italic": flags[1],
                "link": link_target,
            })

    def visit(node, flags=(False, False), link_target=None):
        if node.tag in {W + "del", W + "moveFrom", W + "delText", W + "instrText"}:
            return
        if node.tag == W + "hyperlink":
            relationship_id = node.get("{%s}id" % R_NS)
            relationship = relationships.get(relationship_id)
            target = (
                relationship.get("target")
                if relationship
                and relationship.get("type") == HYPERLINK_REL
                and relationship.get("mode") == "External"
                else None
            )
            link_target = safe_hyperlink_target(target)
            if link_target is None and warnings is not None:
                key = relationship_id or id(node)
                if key not in warned_links:
                    warned_links.add(key)
                    warnings.append(DocxImportWarning(
                        "This Word hyperlink has an unsupported, unsafe or missing external target. "
                        "Its visible text is kept as plain text; only http, https and mailto links are imported.",
                        location,
                    ))
        if node.tag == W + "r":
            flags = (_run_flag(node, styles, "b"), _run_flag(node, styles, "i"))
        if node.tag == W + "t":
            add(node.text or "", flags, link_target)
            return
        if node.tag == W + "tab":
            add("\t", flags, link_target)
            return
        if node.tag in {W + "br", W + "cr"}:
            add("\n", flags, link_target)
            return
        for child in node:
            visit(child, flags, link_target)

    visit(paragraph)
    return segments


def _escape_markdown(text: str) -> str:
    """Escape Markdown punctuation in literal Word text."""
    escaped = re.sub(r"([\\*_{}\[\]()#+\-.!|>~])", r"\\\1", text)
    return escaped.replace(chr(96), "\\" + chr(96))


def _wrap_emphasis(text: str, bold: bool, italic: bool) -> str:
    """Wrap only non-space content; asterisks also work inside a word."""
    if not (bold or italic):
        return text
    left = len(text) - len(text.lstrip())
    right = len(text.rstrip())
    if left >= right:
        return text
    content = text[left:right]
    marker = "***" if bold and italic else "**" if bold else "*"
    return text[:left] + marker + content + marker + text[right:]


def _inline_markdown(
    paragraph, styles: dict, escape_pipe=False, relationships: dict | None = None,
    warnings: list | None = None, location: str = "paragraph",
) -> str:
    """Convert run formatting and safe hyperlinks without losing split fields."""
    segments = _paragraph_segments(paragraph, styles, relationships, warnings, location)
    raw_parts = []
    flags = []
    for segment in segments:
        value = segment["text"]
        raw_parts.append(value)
        flags.extend([(segment["bold"], segment["italic"], segment["link"])] * len(value))
    raw = "".join(raw_parts)
    if not raw:
        return ""

    left = len(raw) - len(raw.lstrip())
    right = len(raw.rstrip())
    raw = raw[left:right]
    flags = flags[left:right]
    if not raw:
        return ""

    fields = {match.start(): match.end() for match in TOKEN.finditer(raw)}
    output = []
    position = 0
    while position < len(raw):
        if position in fields:
            end = fields[position]
            # A field is one literal token even when Word split its characters
            # across differently formatted runs. Use its first run's marks.
            value = raw[position:end]
            marked = value.replace("|", r"\|") if escape_pipe else value
            bold, italic, link_target = flags[position]
            marked = _wrap_emphasis(marked, bold, italic)
            output.append("[{}](<{}>)".format(marked, link_target) if link_target else marked)
            position = end
            continue

        end = position + 1
        current_flags = flags[position]
        next_field = min((start for start in fields if start > position), default=len(raw))
        while end < next_field and flags[end] == current_flags:
            end += 1
        bold, italic, link_target = current_flags
        value = _escape_markdown(raw[position:end])
        marked = _wrap_emphasis(value, bold, italic)
        output.append("[{}](<{}>)".format(marked, link_target) if link_target else marked)
        position = end
    return "".join(output)


def _formatting_warnings(paragraph, location: str, warnings: list, styles: dict):
    dropped = set()
    for run in paragraph.iter(W + "r"):
        rpr = run.find("w:rPr", NS)
        style_id = _value(rpr, "rStyle")
        is_hyperlink = run.getparent() is not None and run.getparent().tag == W + "hyperlink"

        def prop(name):
            direct = rpr.find("w:" + name, NS) if rpr is not None else None
            return direct if direct is not None else _style_property(styles, style_id, name)

        if not is_hyperlink and _enabled(prop("u")):
            dropped.add("underlining")
        if _enabled(prop("strike")) or _enabled(prop("dstrike")):
            dropped.add("strikethrough")
        if _enabled(prop("highlight")) or _enabled(prop("shd")):
            dropped.add("highlighting")
        fonts = prop("rFonts")
        if fonts is not None and any(fonts.get(W + key) for key in ("ascii", "hAnsi", "eastAsia", "cs")):
            dropped.add("font changes")
        if prop("sz") is not None or prop("szCs") is not None:
            dropped.add("font-size changes")
        color = prop("color")
        if not is_hyperlink and color is not None and color.get(W + "val", "auto").lower() != "auto":
            dropped.add("text-colour changes")

    if dropped:
        labels = ", ".join(sorted(dropped))
        warnings.append(DocxImportWarning(
            f"Markdown does not preserve {labels}; the text is kept without that formatting.",
            location,
        ))


def _paragraph_text(paragraph) -> str:
    """Read accepted visible text, retaining tabs and line breaks."""
    return "".join(segment["text"] for segment in _paragraph_segments(paragraph, {}))


def _paragraph_markdown(
    paragraph, styles: dict, warnings: list, location: str, *,
    in_table=False, relationships: dict | None = None,
) -> str:
    _scan_paragraph(paragraph, location, warnings)
    _formatting_warnings(paragraph, location, warnings, styles)
    value = _inline_markdown(
        paragraph, styles, escape_pipe=in_table, relationships=relationships,
        warnings=warnings, location=location,
    )
    if not value or in_table:
        return value
    level = _heading_level(paragraph, styles)
    if level is not None:
        if level <= 3:
            return "#" * level + " " + value
        warnings.append(DocxImportWarning(
            f"This is a level {level} Word heading. Markdown import supports heading levels 1 to 3; "
            "the text is kept as an ordinary paragraph.",
            location,
        ))
    return value


def _part_warnings(package: zipfile.ZipFile, names: set[str]):
    """Yield warnings for package-level content that is outside the body draft."""
    for part in sorted(names):
        if part.startswith("word/header") and part.endswith(".xml"):
            yield DocxImportWarning(
                "Headers are not imported into the Markdown draft; their wording remains in the original Word file.",
                part.rsplit("/", 1)[-1],
            )
        elif part.startswith("word/footer") and part.endswith(".xml"):
            yield DocxImportWarning(
                "Footers are not imported into the Markdown draft; their wording remains in the original Word file.",
                part.rsplit("/", 1)[-1],
            )
    for part, label, message in (
        ("word/footnotes.xml", "footnotes", "Footnotes are not imported into the Markdown draft."),
        ("word/endnotes.xml", "endnotes", "Endnotes are not imported into the Markdown draft."),
        ("word/comments.xml", "comments", "Comments are not imported into the Markdown draft."),
    ):
        if part in names:
            yield DocxImportWarning(message, label)


def _scan_paragraph(paragraph, location: str, warnings: list):
    """Report Word features whose formatting or separate content is not imported."""
    checks = (
        (W + "drawing", "Images, drawings and floating shapes are not imported; surrounding paragraph text is kept."),
        (W + "pict", "Legacy images and drawing objects are not imported; surrounding paragraph text is kept."),
        (W + "object", "Embedded objects are not imported; surrounding paragraph text is kept."),
        (M + "oMath", "Equations are not converted to Markdown; surrounding paragraph text is kept."),
        (M + "oMathPara", "Equations are not converted to Markdown; surrounding paragraph text is kept."),
        (W + "footnoteReference", "A footnote reference is not imported; the footnote text is not included."),
        (W + "endnoteReference", "An endnote reference is not imported; the endnote text is not included."),
        (W + "commentRangeStart", "Commented text is kept, but its comment and annotation are not imported."),
        (W + "commentReference", "Comment references and their annotations are not imported."),
        (W + "sdt", "Content controls are flattened to their visible text; their controls and prompts are not imported."),
        (W + "fldSimple", "A Word field is not converted; only its displayed result is kept."),
        (W + "fldChar", "A complex Word field is not converted; only displayed text is kept."),
        (W + "instrText", "A Word field instruction is not imported; only its displayed result is kept."),
        (W + "sectPr", "Section breaks and section-specific page layout are not imported."),
    )
    for tag, message in checks:
        count = sum(1 for _ in paragraph.iter(tag))
        for _ in range(count):
            warnings.append(DocxImportWarning(message, location))

    if any(node.get(W + "type") == "page" for node in paragraph.iter(W + "br")):
        warnings.append(DocxImportWarning(
            "Page breaks are not preserved in Markdown; the text on both sides is kept.",
            location,
        ))
    if any(node.tag == W + "lastRenderedPageBreak" for node in paragraph.iter()):
        warnings.append(DocxImportWarning(
            "A displayed page break is not preserved in Markdown; the text is kept.",
            location,
        ))
    if any(node.tag in {W + "ins", W + "del", W + "moveFrom", W + "moveTo"}
           for node in paragraph.iter()):
        warnings.append(DocxImportWarning(
            "This paragraph contains tracked changes. The draft uses the accepted text (insertions kept, deletions removed); review it in Word.",
            location,
        ))


def _table_markdown(
    table, table_number: int, styles: dict, numbering: dict, warnings: list,
    relationships: dict | None = None,
) -> str:
    rows = table.findall("w:tr", NS)
    if not rows:
        return ""

    grid = []
    merged = False
    row_widths = []
    for row_number, row in enumerate(rows, 1):
        cells = row.findall("w:tc", NS)
        row_widths.append(len(cells))
        rendered_cells = []
        for cell_number, cell in enumerate(cells, 1):
            location = f"table {table_number}, row {row_number}, cell {cell_number}"
            tcpr = cell.find("w:tcPr", NS)
            if tcpr is not None:
                span = tcpr.find("w:gridSpan", NS)
                if span is not None and int(span.get(W + "val", "1")) > 1:
                    merged = True
                if tcpr.find("w:vMerge", NS) is not None or tcpr.find("w:hMerge", NS) is not None:
                    merged = True

            direct_paragraphs = cell.findall("w:p", NS)
            content_paragraphs = [p for p in direct_paragraphs if _paragraph_text(p).strip()]
            nested_tables = list(cell.iter(W + "tbl"))
            all_paragraphs = list(cell.iter(W + "p"))
            if len(content_paragraphs) > 1:
                warnings.append(DocxImportWarning(
                    "This cell contains more than one paragraph. The paragraphs are joined with spaces in the Markdown table.",
                    location,
                ))
            if nested_tables:
                warnings.append(DocxImportWarning(
                    "This cell contains a nested table. Its text is included as a best-effort reading, but its rows and columns are not preserved.",
                    location,
                ))

            pieces = []
            for paragraph_number, paragraph in enumerate(all_paragraphs, 1):
                paragraph_location = f"{location}, paragraph {paragraph_number}"
                _scan_paragraph(paragraph, paragraph_location, warnings)
                _formatting_warnings(paragraph, paragraph_location, warnings, styles)
                if _list_info(paragraph, styles, numbering):
                    warnings.append(DocxImportWarning(
                        "This cell contains a Word list. Its text is kept, but the list structure is flattened inside the table cell.",
                        paragraph_location,
                    ))
                value = _inline_markdown(
                    paragraph, styles, escape_pipe=True, relationships=relationships,
                    warnings=warnings, location=paragraph_location,
                )
                if value:
                    pieces.append(value)
            rendered_cells.append(" / ".join(pieces).replace("\n", " ").replace("\t", " "))
        grid.append(rendered_cells)

    if len(set(row_widths)) > 1:
        merged = True
    width = max((len(row) for row in grid), default=0)
    if width == 0:
        return ""
    if merged:
        warnings.append(DocxImportWarning(
            "This table has merged or irregular cells. Markdown cannot retain the cell layout; a best-effort rectangular table is included.",
            f"table {table_number}",
        ))
    grid = [row + [""] * (width - len(row)) for row in grid]
    output = ["| " + " | ".join(grid[0]) + " |",
              "| " + " | ".join("---" for _ in range(width)) + " |"]
    output.extend("| " + " | ".join(row) + " |" for row in grid[1:])
    warnings.append(DocxImportWarning(
        "Table content is included as a basic Markdown table; review its structure and layout in the original Word file.",
        f"table {table_number}",
    ))
    return "\n".join(output)


def _flush_list(items, blocks):
    if items:
        blocks.append("\n".join(items))
        items.clear()


def _flush_list_block(items, numbers, start, position, blocks, block_info, warnings):
    """Close the open list run as one block; returns None for the next run's start."""
    if items:
        blocks.append("\n".join(items))
        block_info.append(DocxBlock(
            "list", blocks[-1], "", None, position, tuple(numbers),
            tuple(warnings[start:]) if start is not None else (),
        ))
        items.clear()
        numbers.clear()
    return None


def _paragraph_style_name(paragraph, styles: dict) -> str:
    """The Word display name of the paragraph's style, or "" for none."""
    style_id = _paragraph_style_id(paragraph)
    entry = styles.get(style_id) if style_id else None
    return (entry["name"] if entry else "") or (style_id or "")


def _direct_alignment(paragraph) -> str:
    """"center" or "right" when set on the paragraph itself, else ""."""
    ppr = paragraph.find("w:pPr", NS)
    value = _value(ppr, "jc") if ppr is not None else None
    return value if value in ("center", "right") else ""


def import_docx(path: str | Path) -> DocxImport:
    """Read a DOCX package without modifying it; preserve paragraph/table order."""
    source = Path(path)
    try:
        with zipfile.ZipFile(source, "r") as package:
            names = set(package.namelist())
            xml = package.read("word/document.xml")
            styles_xml = package.read("word/styles.xml") if "word/styles.xml" in names else None
            numbering_xml = package.read("word/numbering.xml") if "word/numbering.xml" in names else None
            relationships_xml = (
                package.read("word/_rels/document.xml.rels")
                if "word/_rels/document.xml.rels" in names else None
            )
            package_warnings = list(_part_warnings(package, names))
        root = etree.fromstring(xml)
        styles = _read_styles(styles_xml)
        numbering = _numbering_maps(numbering_xml)
        relationships = _read_relationships(relationships_xml)
    except (OSError, KeyError, zipfile.BadZipFile, etree.XMLSyntaxError, ValueError) as exc:
        raise DocxImportError(
            f"Could not read '{source.name}' as a valid Word .docx file. "
            "Choose an unencrypted .docx document and try again."
        ) from exc

    body = root.find("w:body", NS)
    if body is None:
        raise DocxImportError(
            f"Could not read '{source.name}' as a valid Word .docx file: "
            "the document body is missing."
        )

    blocks = []
    warnings = package_warnings
    list_items = []
    active_list_id = None
    previous_level = 0
    changed_number_formats = set()
    paragraph_number = 0
    table_number = 0
    text_styles = []            # style of each ordinary paragraph, in order
    unoffered = {}              # Word style name -> paragraphs given Normal
    block_info = []             # DocxBlock for each entry of ``blocks``
    list_numbers = []           # body paragraph numbers in the open list run
    list_start = None           # warnings index where the open list run began
    list_position = 0           # body position where the open list run began

    for position, child in enumerate(body):
        if child.tag == W + "p":
            paragraph_number += 1
            location = f"paragraph {paragraph_number}"
            mark = len(warnings)
            list_info = _list_info(child, styles, numbering)
            value = _paragraph_markdown(
                child, styles, warnings, location, relationships=relationships
            )
            if list_info is not None:
                if active_list_id is not None and list_info["num_id"] != active_list_id:
                    list_start = _flush_list_block(
                        list_items, list_numbers, list_start, list_position, blocks, block_info, warnings)
                    previous_level = 0
                active_list_id = list_info["num_id"]
                level = list_info["level"]
                # Word can skip a level. Markdown cannot express an item at
                # level 3 without level 2, so keep the nearest valid nesting.
                if list_items:
                    level = min(level, previous_level + 1)
                if list_info["format"] in LETTER_ROMAN_FORMATS:
                    key = (list_info["num_id"], list_info["level"], list_info["format"])
                    if key not in changed_number_formats:
                        changed_number_formats.add(key)
                        warnings.append(DocxImportWarning(
                            "This Word list uses letter or Roman numbering. Markdown imports it as a decimal list, so its displayed numbering will change.",
                            location,
                        ))
                marker = "- " if list_info["kind"] == "bullet" else "1. "
                if value:
                    if not list_items:
                        list_start = mark
                        list_position = position
                    list_items.append("    " * level + marker + value)
                    list_numbers.append(paragraph_number)
                previous_level = level
            else:
                list_start = _flush_list_block(
                    list_items, list_numbers, list_start, list_position, blocks, block_info, warnings)
                active_list_id = None
                previous_level = 0
                if value:
                    plain_text = "".join(segment["text"] for segment in _paragraph_segments(child, styles)).strip()
                    if TYPED_LIST_MARKER.match(plain_text):
                        warnings.append(DocxImportWarning(
                            "This paragraph begins with a list number typed as ordinary text, not Word automatic numbering. It is kept as written and may be intended as a list item.",
                            location,
                        ))
                    blocks.append(value)
                    level = _heading_level(child, styles)
                    is_heading = level is not None and level <= 3
                    block_style = _paragraph_style_name(child, styles)
                    if level is None or level > 3:
                        name = _paragraph_style_name(child, styles)
                        offered = _KNOWN_PARAGRAPH_STYLES.get(name.casefold(), "")
                        text_styles.append(offered)
                        if name and not offered and name.casefold() not in (
                            "normal", "default paragraph font"
                        ) and not name.casefold().startswith("heading"):
                            unoffered[name] = unoffered.get(name, 0) + 1
                        alignment = _direct_alignment(child)
                        if alignment:
                            warnings.append(DocxImportWarning(
                                "This paragraph is %s by hand in Word. A component keeps "
                                "alignment only through a paragraph style, so it is not kept. "
                                "Choose the Title or Subtitle style for it in the editor if it "
                                "is a title."
                                % ("centered" if alignment == "center" else "right-aligned"),
                                location,
                            ))
                    block_info.append(DocxBlock(
                        "heading" if is_heading else "paragraph", value, block_style,
                        level if is_heading else None, position, (paragraph_number,),
                        tuple(warnings[mark:]),
                    ))
        elif child.tag == W + "tbl":
            list_start = _flush_list_block(
                list_items, list_numbers, list_start, list_position, blocks, block_info, warnings)
            active_list_id = None
            previous_level = 0
            table_number += 1
            mark = len(warnings)
            value = _table_markdown(
                child, table_number, styles, numbering, warnings, relationships
            )
            if value:
                blocks.append(value)
                block_info.append(DocxBlock(
                    "table", value, "", None, position, (), tuple(warnings[mark:]),
                ))

    _flush_list_block(list_items, list_numbers, list_start, list_position, blocks, block_info, warnings)
    markdown = "\n\n".join(blocks)
    for name, count in sorted(unoffered.items()):
        warnings.append(DocxImportWarning(
            "%d paragraph%s use%s the Word style '%s', which the editor does not offer, so "
            "%s imported as Normal." % (
                count, "" if count == 1 else "s", "s" if count == 1 else "", name,
                "it is" if count == 1 else "they are"),
            "style " + name,
        ))
    styles_list = _importable_styles(markdown, text_styles)
    return DocxImport(
        markdown=markdown, warnings=tuple(warnings), paragraph_styles=styles_list,
        blocks=tuple(block_info),
    )


def _importable_styles(markdown: str, text_styles) -> tuple[str, ...]:
    """The style list, only when it lines up with the paragraphs Markdown will show.

    If a typed list marker or other markup changed how the text parses, the
    counts differ; then the styles are dropped rather than put on the wrong
    paragraphs.
    """
    import paragraph_styles as rules

    if len(rules.text_paragraphs(markdown)) != len(text_styles):
        return ()
    return tuple(rules.normalize(text_styles))
