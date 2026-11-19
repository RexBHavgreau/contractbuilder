"""Read DOCX body content in document order as a plain Markdown draft.

The importer is deliberately read-only. Unsupported Word structures are
reported with locations; tracked changes use Word's accepted (final) text.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import zipfile

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
W = f"{{{W_NS}}}"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
M = f"{{{M_NS}}}"


class DocxImportError(ValueError):
    """A DOCX file could not be read, explained for an ordinary user."""


@dataclass(frozen=True)
class DocxImportWarning:
    """A non-blocking observation about content not represented in this draft."""

    message: str
    location: str


@dataclass(frozen=True)
class DocxImport:
    """Markdown draft and any non-blocking import warnings."""

    markdown: str
    warnings: tuple[DocxImportWarning, ...]


def _paragraph_text(paragraph) -> str:
    """Read accepted visible text, retaining tabs and line breaks.

    Deleted and moved-from text is excluded, matching Word's final/accepted
    view. Inserted and moved-to text is included. Field instructions are not
    visible document wording and are excluded.
    """
    pieces = []

    def visit(node, hidden=False):
        if hidden or node.tag in {W + "del", W + "moveFrom"}:
            return
        if node.tag in {W + "t", W + "delText"}:
            if node.tag == W + "t":
                pieces.append(node.text or "")
            return
        if node.tag == W + "tab":
            pieces.append("\t")
            return
        if node.tag in {W + "br", W + "cr"}:
            pieces.append("\n")
            return
        if node.tag == W + "instrText":
            return
        for child in node:
            visit(child)

    visit(paragraph)
    return "".join(pieces)


def _table_markdown(table) -> str:
    rows = []
    for row in table.findall("w:tr", NS):
        cells = []
        for cell in row.findall("w:tc", NS):
            paragraphs = cell.findall("w:p", NS)
            value = " ".join(_paragraph_text(p).strip() for p in paragraphs).strip()
            cells.append(value.replace("|", r"\|").replace("\n", " "))
        rows.append(cells)
    if not rows:
        return ""
    width = max(map(len, rows), default=0)
    if not width:
        return ""
    rows = [row + [""] * (width - len(row)) for row in rows]
    output = ["| " + " | ".join(rows[0]) + " |",
              "| " + " | ".join("---" for _ in range(width)) + " |"]
    output.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(output)


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

    if any(node.get("{" + W_NS + "}type") == "page" for node in paragraph.iter(W + "br")):
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


def import_docx(path: str | Path) -> DocxImport:
    """Read a DOCX package without modifying it; preserve paragraph/table order."""
    source = Path(path)
    try:
        with zipfile.ZipFile(source, "r") as package:
            names = set(package.namelist())
            xml = package.read("word/document.xml")
            package_warnings = list(_part_warnings(package, names))
        root = etree.fromstring(xml)
    except (OSError, KeyError, zipfile.BadZipFile, etree.XMLSyntaxError) as exc:
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
    paragraph_number = 0
    table_number = 0
    for child in body:
        if child.tag == W + "p":
            paragraph_number += 1
            _scan_paragraph(child, f"paragraph {paragraph_number}", warnings)
            value = _paragraph_text(child).strip()
            if value:
                blocks.append(value)
        elif child.tag == W + "tbl":
            table_number += 1
            for row_number, row in enumerate(child.findall("w:tr", NS), 1):
                for cell_number, cell in enumerate(row.findall("w:tc", NS), 1):
                    for para_number, paragraph in enumerate(cell.findall("w:p", NS), 1):
                        location = (f"table {table_number}, row {row_number}, cell {cell_number}, "
                                    f"paragraph {para_number}")
                        _scan_paragraph(paragraph, location, warnings)
            value = _table_markdown(child)
            if value:
                blocks.append(value)
            warnings.append(DocxImportWarning(
                "Table content is included as a basic Markdown table; complex "
                "Word table features may need review.",
                f"table {table_number}",
            ))
    return DocxImport(markdown="\n\n".join(blocks), warnings=tuple(warnings))
