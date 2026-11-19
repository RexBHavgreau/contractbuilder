"""Tests for DOCX-to-Markdown import warnings and accepted text."""
import zipfile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import pytest

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
        "First paragraph\n\n| Heading A | Heading B |\n| --- | --- |\n"
        "| Value A | Value B |\n\nLast paragraph"
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
    path = tmp_path / "missing-body.docx"
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("not-the-document.xml", "<root/>")
    with pytest.raises(DocxImportError, match="valid Word .docx"):
        import_docx(path)


def _append_revision(paragraph, wrapper_tag, text, text_tag="w:t"):
    wrapper = OxmlElement(wrapper_tag)
    run = OxmlElement("w:r")
    value = OxmlElement(text_tag)
    value.text = text
    run.append(value)
    wrapper.append(run)
    paragraph._p.append(wrapper)


def _rewrite_package(path, additions):
    temporary = path.with_suffix(".rewritten.docx")
    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(temporary, "w") as target:
        for info in source.infolist():
            target.writestr(info, source.read(info.filename))
        for name, value in additions.items():
            target.writestr(name, value)
    temporary.replace(path)


def test_tracked_changes_import_accepted_text_and_warn(tmp_path):
    doc = Document()
    paragraph = doc.add_paragraph("Before ")
    _append_revision(paragraph, "w:ins", "inserted")
    _append_revision(paragraph, "w:del", "deleted", "w:delText")
    _append_revision(paragraph, "w:moveFrom", "moved away", "w:delText")
    _append_revision(paragraph, "w:moveTo", "moved here")
    paragraph.add_run(" after")
    path = tmp_path / "revisions.docx"
    doc.save(path)
    result = import_docx(path)
    assert result.markdown == "Before insertedmoved here after"
    warning = next(item for item in result.warnings if "tracked changes" in item.message)
    assert warning.location == "paragraph 1"
    assert "accepted text" in warning.message


def test_warns_for_drawings_fields_controls_comments_and_section_breaks(tmp_path):
    doc = Document()
    paragraph = doc.add_paragraph("Keep ")
    for tag in ("w:drawing", "w:object", "w:footnoteReference",
                "w:endnoteReference", "w:commentRangeStart", "w:commentReference",
                "w:sdt", "w:fldSimple", "w:sectPr"):
        node = OxmlElement(tag)
        if tag == "w:sdt":
            content = OxmlElement("w:sdtContent")
            run = OxmlElement("w:r")
            text = OxmlElement("w:t")
            text.text = "controlled"
            run.append(text)
            content.append(run)
            node.append(content)
        if tag == "w:fldSimple":
            run = OxmlElement("w:r")
            text = OxmlElement("w:t")
            text.text = "field result"
            run.append(text)
            node.append(run)
        paragraph._p.append(node)
    paragraph.add_run(" text")
    path = tmp_path / "structures.docx"
    doc.save(path)
    result = import_docx(path)
    messages = [item.message for item in result.warnings]
    assert result.markdown == "Keep controlledfield result text"
    assert any("drawings" in message for message in messages)
    assert any("footnote reference" in message for message in messages)
    assert any("endnote reference" in message for message in messages)
    assert any("Commented text" in message for message in messages)
    assert any("Content controls" in message for message in messages)
    assert any("Word field" in message for message in messages)
    assert any("Section breaks" in message for message in messages)


def test_warns_for_equations_and_page_breaks(tmp_path):
    doc = Document()
    paragraph = doc.add_paragraph("Before")
    math = OxmlElement("m:oMath")
    math_run = OxmlElement("m:r")
    math_text = OxmlElement("m:t")
    math_text.text = "x + y"
    math_run.append(math_text)
    math.append(math_run)
    paragraph._p.append(math)
    run = OxmlElement("w:r")
    page_break = OxmlElement("w:br")
    page_break.set(qn("w:type"), "page")
    run.append(page_break)
    paragraph._p.append(run)
    paragraph.add_run("After")
    path = tmp_path / "equation-page-break.docx"
    doc.save(path)
    result = import_docx(path)
    messages = [item.message for item in result.warnings]
    assert result.markdown == "Before\nAfter"
    assert any("Equations" in message for message in messages)
    assert any("Page breaks" in message for message in messages)


def test_warns_for_package_level_notes_comments_headers_and_footers(tmp_path):
    doc = Document()
    doc.add_paragraph("Body")
    path = tmp_path / "package-parts.docx"
    doc.save(path)
    _rewrite_package(path, {
        "word/footnotes.xml": "<w:footnotes xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>",
        "word/endnotes.xml": "<w:endnotes xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>",
        "word/comments.xml": "<w:comments xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>",
        "word/header1.xml": "<w:hdr xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>",
        "word/footer1.xml": "<w:ftr xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>",
    })
    result = import_docx(path)
    messages = [item.message for item in result.warnings]
    assert any("Footnotes are not imported" in message for message in messages)
    assert any("Endnotes are not imported" in message for message in messages)
    assert any("Comments are not imported" in message for message in messages)
    assert any("Headers are not imported" in message for message in messages)
    assert any("Footers are not imported" in message for message in messages)
