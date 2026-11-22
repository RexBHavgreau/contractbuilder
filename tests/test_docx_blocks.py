"""The DOCX importer returns its content as ordered blocks (T-064-A). Invented text only."""
import pathlib
import sys

from docx import Document

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from docx_to_markdown import import_docx  # noqa: E402
from test_docx_to_markdown import (  # noqa: E402
    _numbering_xml, _rewrite_package, _set_numbering,
)


def _import(tmp_path, build):
    doc = Document()
    build(doc)
    path = tmp_path / "invented.docx"
    doc.save(path)
    return import_docx(path)


def test_joining_the_blocks_gives_the_same_markdown_as_before(tmp_path):
    def build(doc):
        doc.add_heading("Invented Title", level=1)
        doc.add_paragraph("A paragraph with a **bold** word.")
        doc.add_paragraph("Another paragraph.")
    result = _import(tmp_path, build)
    assert "\n\n".join(block.markdown for block in result.blocks) == result.markdown


def test_each_block_has_its_kind_style_and_paragraph_numbers(tmp_path):
    def build(doc):
        doc.add_heading("Invented Heading", level=2)
        doc.add_paragraph("Invented body text.")
    result = _import(tmp_path, build)
    heading, body = result.blocks
    assert heading.kind == "heading" and heading.level == 2
    assert heading.style.casefold() == "heading 2"  # the name as the file stores it
    assert heading.paragraph_numbers == (1,)
    assert body.kind == "paragraph" and body.level is None
    assert body.paragraph_numbers == (2,)
    assert body.position == 1


def test_a_table_is_its_own_block_found_by_position(tmp_path):
    def build(doc):
        doc.add_paragraph("Before the table.")
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Item"
        table.cell(0, 1).text = "Amount"
        table.cell(1, 0).text = "Invented fee"
        table.cell(1, 1).text = "100"
        doc.add_paragraph("After the table.")
    result = _import(tmp_path, build)
    kinds = [block.kind for block in result.blocks]
    assert kinds == ["paragraph", "table", "paragraph"]
    table = result.blocks[1]
    assert table.paragraph_numbers == ()
    assert table.position == 1
    assert table.markdown.startswith("| Item | Amount |")


def test_a_nested_list_is_one_block_with_all_its_paragraphs(tmp_path):
    def build(doc):
        first = doc.add_paragraph("Outer invented item")
        nested = doc.add_paragraph("Inner invented item")
        _set_numbering(first, 50, 0)
        _set_numbering(nested, 50, 1)
    doc = Document()
    build(doc)
    path = tmp_path / "list.docx"
    doc.save(path)
    _rewrite_package(path, {"word/numbering.xml": _numbering_xml()})
    result = import_docx(path)
    assert [block.kind for block in result.blocks] == ["list"]
    assert result.blocks[0].paragraph_numbers == (1, 2)
    assert "    - Inner invented item" in result.blocks[0].markdown or "    1. Inner invented item" in result.blocks[0].markdown


def test_a_heading_with_nothing_under_it_is_still_a_block(tmp_path):
    def build(doc):
        doc.add_heading("Invented Empty Heading", level=1)
        doc.add_heading("Invented Next Heading", level=1)
        doc.add_paragraph("Invented text.")
    result = _import(tmp_path, build)
    assert [block.kind for block in result.blocks] == ["heading", "heading", "paragraph"]
    assert result.blocks[0].markdown == "# Invented Empty Heading"


def test_a_document_with_no_headings_has_only_paragraph_blocks(tmp_path):
    def build(doc):
        doc.add_paragraph("Invented one.")
        doc.add_paragraph("Invented two.")
    result = _import(tmp_path, build)
    assert [block.kind for block in result.blocks] == ["paragraph", "paragraph"]
    assert all(block.level is None for block in result.blocks)


def test_warnings_belong_to_the_block_that_caused_them(tmp_path):
    def build(doc):
        plain = doc.add_paragraph("Invented plain text.")
        typed = doc.add_paragraph("1) typed by hand, not automatic numbering")
        assert plain is not None and typed is not None
    result = _import(tmp_path, build)
    typed_block = [block for block in result.blocks if "typed by hand" in block.markdown][0]
    assert any("typed as ordinary text" in warning.message for warning in typed_block.warnings)
    plain_block = [block for block in result.blocks if "plain text" in block.markdown][0]
    assert not any("typed as ordinary text" in warning.message for warning in plain_block.warnings)


def test_existing_fields_are_unchanged(tmp_path):
    def build(doc):
        doc.add_heading("Invented Heading", level=1)
        doc.add_paragraph("Invented text.")
    result = _import(tmp_path, build)
    assert result.markdown == "# Invented Heading\n\nInvented text\\."
    assert result.paragraph_styles is not None
