"""Read DOCX body content in document order as a plain Markdown draft."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import zipfile

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


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
    """Read visible paragraph text, retaining tabs and line breaks."""
    pieces = []
    for node in paragraph.iter():
        if node.tag == f"{{{W_NS}}}t":
            pieces.append(node.text or "")
        elif node.tag == f"{{{W_NS}}}tab":
            pieces.append("\t")
        elif node.tag in {f"{{{W_NS}}}br", f"{{{W_NS}}}cr"}:
            pieces.append("\n")
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


def import_docx(path: str | Path) -> DocxImport:
    """Read a DOCX package without modifying it; preserve paragraph/table order."""
    source = Path(path)
    try:
        with zipfile.ZipFile(source, "r") as package:
            xml = package.read("word/document.xml")
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
    warnings = []
    paragraph_number = 0
    table_number = 0
    for child in body:
        if child.tag == f"{{{W_NS}}}p":
            paragraph_number += 1
            value = _paragraph_text(child).strip()
            if value:
                blocks.append(value)
        elif child.tag == f"{{{W_NS}}}tbl":
            table_number += 1
            value = _table_markdown(child)
            if value:
                blocks.append(value)
            warnings.append(DocxImportWarning(
                "Table content is included as a basic Markdown table; complex "
                "Word table features may need review.",
                f"table {table_number}",
            ))
    return DocxImport(markdown="\n\n".join(blocks), warnings=tuple(warnings))
