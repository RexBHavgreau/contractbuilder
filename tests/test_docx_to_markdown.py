"""Tests for DOCX-to-Markdown import warnings and accepted text."""
import zipfile

from docx import Document

import docx_compose
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor
import pytest
from lxml import etree

from docx_to_markdown import DocxImportError, import_docx

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
W = "{" + W_NS + "}"




def _set_numbering(paragraph, num_id, level=0):
    ppr = paragraph._p.get_or_add_pPr()
    numpr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), str(level))
    num = OxmlElement("w:numId")
    num.set(qn("w:val"), str(num_id))
    numpr.append(ilvl)
    numpr.append(num)
    ppr.append(numpr)


def _numbering_xml():
    root = etree.Element(W + "numbering", nsmap={"w": W_NS})
    definitions = {
        40: {0: "decimal", 1: "lowerLetter", 2: "lowerRoman"},
        41: {0: "bullet"},
        42: {0: "upperRoman"},
    }
    for abstract_id, levels in definitions.items():
        abstract = etree.SubElement(root, W + "abstractNum")
        abstract.set(W + "abstractNumId", str(abstract_id))
        for level_number, number_format in levels.items():
            level = etree.SubElement(abstract, W + "lvl")
            level.set(W + "ilvl", str(level_number))
            fmt = etree.SubElement(level, W + "numFmt")
            fmt.set(W + "val", number_format)
            text = etree.SubElement(level, W + "lvlText")
            text.set(W + "val", "•" if number_format == "bullet" else f"%{level_number + 1}.")
    for num_id, abstract_id in ((50, 40), (51, 41), (52, 42)):
        num = etree.SubElement(root, W + "num")
        num.set(W + "numId", str(num_id))
        abstract = etree.SubElement(num, W + "abstractNumId")
        abstract.set(W + "val", str(abstract_id))
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


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
            if info.filename not in additions:
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


def test_warnings_inside_table_cells_have_a_precise_location(tmp_path):
    doc = Document()
    cell = doc.add_table(rows=1, cols=1).cell(0, 0)
    paragraph = cell.paragraphs[0]
    paragraph.add_run("Cell text")
    paragraph._p.append(OxmlElement("w:footnoteReference"))
    path = tmp_path / "table-note.docx"
    doc.save(path)

    result = import_docx(path)

    warning = next(item for item in result.warnings if "footnote reference" in item.message)
    assert warning.location == "table 1, row 1, cell 1, paragraph 1"


def test_paragraphs_import_headings_bold_italic_and_escape_literal_markdown(tmp_path):
    doc = Document()
    doc.add_paragraph("Heading one", style="Heading 1")
    paragraph = doc.add_paragraph("A *literal* _underscore_ and # heading marker; ")
    first = paragraph.add_run("bold")
    first.bold = True
    second = paragraph.add_run(" text ")
    second.bold = True
    italic = paragraph.add_run("ita")
    italic.italic = True
    italic_split = paragraph.add_run("lic")
    italic_split.italic = True
    paragraph.add_run("ized")
    path = tmp_path / "formatting.docx"
    doc.save(path)

    result = import_docx(path)

    assert result.markdown == (
        "# Heading one\n\nA \\*literal\\* \\_underscore\\_ and \\# heading marker; "
        "**bold text** *italic*ized"
    )


def test_split_fields_remain_literal_across_three_runs(tmp_path):
    doc = Document()
    paragraph = doc.add_paragraph("Value: ")
    paragraph.add_run("{{Cli")
    middle = paragraph.add_run("ent | mon")
    middle.bold = True
    paragraph.add_run("ey}}")
    paragraph.add_run("; {{#if Include")
    paragraph.add_run(" Thing}}")
    path = tmp_path / "split-fields.docx"
    doc.save(path)

    result = import_docx(path)

    assert result.markdown == "Value: {{Client | money}}; {{#if Include Thing}}"


def test_deep_heading_is_kept_and_reported(tmp_path):
    doc = Document()
    doc.add_paragraph("Supported", style="Heading 3")
    doc.add_paragraph("Too deep", style="Heading 4")
    path = tmp_path / "deep-heading.docx"
    doc.save(path)

    result = import_docx(path)

    assert result.markdown == "### Supported\n\nToo deep"
    assert any("level 4" in item.message and item.location == "paragraph 2" for item in result.warnings)


def test_unsupported_run_formatting_is_reported_without_dropping_text(tmp_path):
    doc = Document()
    paragraph = doc.add_paragraph()
    run = paragraph.add_run("Keep this wording")
    run.underline = True
    run.font.strike = True
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    run.font.name = "Courier New"
    run.font.size = 18
    run.font.color.rgb = RGBColor(0xAA, 0x11, 0x22)
    path = tmp_path / "unsupported-formatting.docx"
    doc.save(path)

    result = import_docx(path)

    assert "Keep this wording" in result.markdown
    message = " ".join(item.message for item in result.warnings)
    for label in ("underlining", "strikethrough", "highlighting", "font changes",
                  "font-size changes", "text-colour changes"):
        assert label in message


def test_imports_word_bullets_nested_lists_and_reports_non_decimal_styles(tmp_path):
    doc = Document()
    first = doc.add_paragraph("First clause")
    nested = doc.add_paragraph("Nested clause")
    deeper = doc.add_paragraph("Deeper clause")
    roman = doc.add_paragraph("Roman clause")
    bullet = doc.add_paragraph("Bullet item")
    typed = doc.add_paragraph("3. Typed number remains text")
    _set_numbering(first, 50, 0)
    _set_numbering(nested, 50, 1)
    _set_numbering(deeper, 50, 2)
    _set_numbering(roman, 52, 0)
    _set_numbering(bullet, 51, 0)
    path = tmp_path / "lists.docx"
    doc.save(path)
    _rewrite_package(path, {"word/numbering.xml": _numbering_xml()})

    result = import_docx(path)

    assert result.markdown == (
        "1. First clause\n    1. Nested clause\n        1. Deeper clause\n\n"
        "1. Roman clause\n\n"
        "- Bullet item\n\n3\\. Typed number remains text"
    )
    messages = " ".join(item.message for item in result.warnings)
    assert "letter or Roman numbering" in messages
    assert "list number typed as ordinary text" in messages
    assert any(item.location == "paragraph 4" for item in result.warnings)
    assert any(item.location == "paragraph 6" for item in result.warnings)


def test_imports_lower_letter_numbering_as_decimal_with_warning(tmp_path):
    doc = Document()
    first = doc.add_paragraph("First")
    second = doc.add_paragraph("Second")
    _set_numbering(first, 50, 0)
    _set_numbering(second, 50, 1)
    path = tmp_path / "letter-list.docx"
    doc.save(path)
    _rewrite_package(path, {"word/numbering.xml": _numbering_xml()})

    result = import_docx(path)

    assert result.markdown == "1. First\n    1. Second"
    assert any("letter or Roman numbering" in item.message for item in result.warnings)


def test_rectangular_table_escapes_pipe_and_table_field_pipe(tmp_path):
    doc = Document()
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Name"
    table.cell(0, 1).text = "Amount"
    table.cell(1, 0).text = "A | B"
    table.cell(1, 1).text = "{{Fee | money}}"
    path = tmp_path / "pipes.docx"
    doc.save(path)

    result = import_docx(path)

    assert result.markdown == (
        "| Name | Amount |\n| --- | --- |\n| A \\| B | {{Fee \\| money}} |"
    )


def test_merged_and_complex_table_cells_are_reported_with_best_effort_text(tmp_path):
    doc = Document()
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).merge(table.cell(0, 1))
    table.cell(0, 0).text = "Merged heading"
    cell = table.cell(1, 0)
    cell.text = "First paragraph"
    _set_numbering(cell.paragraphs[0], 50, 0)
    cell.add_paragraph("Second paragraph")
    nested_cell = table.cell(1, 1)
    nested = nested_cell.add_table(rows=1, cols=1)
    nested.cell(0, 0).text = "Nested wording"
    path = tmp_path / "complex-table.docx"
    doc.save(path)

    result = import_docx(path)

    assert "Merged heading" in result.markdown
    assert "First paragraph / Second paragraph" in result.markdown
    assert "Nested wording" in result.markdown
    messages = " ".join(item.message for item in result.warnings)
    assert "merged or irregular cells" in messages
    assert "more than one paragraph" in messages
    assert "nested table" in messages
    assert "Word list" in messages


def test_body_order_is_preserved_around_multiple_tables_and_lists(tmp_path):
    doc = Document()
    doc.add_paragraph("Before")
    first = doc.add_paragraph("A list item")
    _set_numbering(first, 50, 0)
    table = doc.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Middle table"
    doc.add_paragraph("After")
    path = tmp_path / "mixed-order.docx"
    doc.save(path)
    _rewrite_package(path, {"word/numbering.xml": _numbering_xml()})

    result = import_docx(path)

    assert result.markdown.startswith("Before\n\n1. A list item\n\n| Middle table |")
    assert result.markdown.endswith("\n\nAfter")


def test_imports_builtin_word_list_styles(tmp_path):
    doc = Document()
    doc.add_paragraph("Numbered item", style="List Number")
    doc.add_paragraph("Bulleted item", style="List Bullet")
    path = tmp_path / "built-in-lists.docx"
    doc.save(path)

    result = import_docx(path)

    assert result.markdown == "1. Numbered item\n\n- Bulleted item"


def test_heading_outline_level_maps_custom_style_to_markdown(tmp_path):
    doc = Document()
    paragraph = doc.add_paragraph("Custom outline heading")
    ppr = paragraph._p.get_or_add_pPr()
    outline = OxmlElement("w:outlineLvl")
    outline.set(qn("w:val"), "1")
    ppr.append(outline)
    path = tmp_path / "outline-heading.docx"
    doc.save(path)

    result = import_docx(path)

    assert result.markdown == "## Custom outline heading"


def test_vertical_merge_is_reported(tmp_path):
    doc = Document()
    table = doc.add_table(rows=2, cols=1)
    table.cell(0, 0).merge(table.cell(1, 0))
    table.cell(0, 0).text = "Shared cell"
    path = tmp_path / "vertical-merge.docx"
    doc.save(path)

    result = import_docx(path)

    assert "Shared cell" in result.markdown
    assert any("merged or irregular cells" in item.message for item in result.warnings)


def test_supported_docx_markdown_docx_round_trip_is_stable(tmp_path):
    """T-020-F: the supported body subset survives an import and composition cycle."""
    source = Document()
    source.add_heading("Service terms", level=2)
    paragraph = source.add_paragraph("The provider will act ")
    paragraph.add_run("reasonably").bold = True
    paragraph.add_run(" and ")
    paragraph.add_run("promptly").italic = True
    source.add_paragraph("First clause", style="List Number")
    source.add_paragraph("Second clause", style="List Number")
    source.add_paragraph("Bullet clause", style="List Bullet")
    table = source.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Term"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Payment"
    table.cell(1, 1).text = "Within thirty days"
    source_path = tmp_path / "invented-source.docx"
    source.save(source_path)
    source_bytes = source_path.read_bytes()

    imported = import_docx(source_path)
    assert "## Service terms" in imported.markdown
    assert "**reasonably**" in imported.markdown
    assert "*promptly*" in imported.markdown
    assert "1. First clause" in imported.markdown
    assert "1. Second clause" in imported.markdown
    assert "- Bullet clause" in imported.markdown
    assert "| Payment | Within thirty days |" in imported.markdown

    shell = Document()
    shell.sections[0].header.paragraphs[0].text = "Invented shell header"
    shell.sections[0].footer.paragraphs[0].text = "Invented shell footer"
    shell.add_paragraph("Shell wording is replaced.")
    shell_path = tmp_path / "invented-shell.docx"
    shell.save(shell_path)
    shell_bytes = shell_path.read_bytes()

    output_path = tmp_path / "round-trip.docx"
    docx_compose.compose_document(shell_path, [imported.markdown], output_path)
    second_import = import_docx(output_path)

    assert second_import.markdown == imported.markdown
    assert source_path.read_bytes() == source_bytes
    assert shell_path.read_bytes() == shell_bytes
    assert "Service terms" in second_import.markdown
    assert "First clause" in second_import.markdown
    assert "Second clause" in second_import.markdown
    assert "Bullet clause" in second_import.markdown
    assert "Within thirty days" in second_import.markdown
