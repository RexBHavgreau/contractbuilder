from pathlib import Path

import pytest
from docx import Document

from docx_to_markdown import DocxImportError, import_docx


def test_import_keeps_paragraph_and_table_order(tmp_path):
    doc = Document()
    doc.add_paragraph("First paragraph")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Heading A"
    table.cell(0, 1).text = "Heading B"
    table.cell(1, 0).text = "Value A"
    table.cell(1, 1).text = "Value B"
    doc.add_paragraph("Last paragraph")
    path = tmp_path / "ordered.docx"
    doc.save(path)

    result = import_docx(path)

    assert result.markdown == (
        "First paragraph\n\n"
        "| Heading A | Heading B |\n"
        "| --- | --- |\n"
        "| Value A | Value B |\n\n"
        "Last paragraph"
    )
    assert result.warnings[0].location == "table 1"


def test_import_reads_docx_without_changing_it(tmp_path):
    doc = Document()
    doc.add_paragraph("Read only")
    path = tmp_path / "readonly.docx"
    doc.save(path)
    before = path.read_bytes()

    import_docx(path)

    assert path.read_bytes() == before


def test_invalid_docx_has_plain_english_error(tmp_path):
    path = tmp_path / "not-a-document.docx"
    path.write_text("not a zip file", encoding="utf-8")

    with pytest.raises(DocxImportError, match="valid Word .docx"):
        import_docx(path)


def test_missing_document_xml_has_plain_english_error(tmp_path):
    import zipfile

    path = tmp_path / "missing-body.docx"
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("not-the-document.xml", "<root/>")

    with pytest.raises(DocxImportError, match="valid Word .docx"):
        import_docx(path)
