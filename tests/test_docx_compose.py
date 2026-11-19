"""Tests for shell-based DOCX composition and field-engine integration."""
from collections import Counter
from io import BytesIO
import pathlib
import sys
import zipfile

from docx import Document
from docx.shared import Inches
from lxml import etree
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import core  # noqa: E402
import docx_compose  # noqa: E402

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
NS = {"w": W_NS}
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
NUMBERING_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering"


def make_shell(path):
    document = Document()
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.left_margin = Inches(1.1)
    section.right_margin = Inches(0.9)
    section.header.paragraphs[0].text = "Shell header"
    section.footer.paragraphs[0].text = "Shell footer"
    document.add_paragraph("Shell wording must be replaced.")
    document.save(path)
    return path


def xml_part(path, name):
    with zipfile.ZipFile(path) as package:
        return etree.fromstring(package.read(name))


def test_composer_preserves_shell_and_component_order(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    before = shell.read_bytes()
    output = tmp_path / "assembled.docx"

    result = docx_compose.compose_document(
        shell,
        [
            "Opening paragraph.\n\n| Item | Fee |\n| --- | ---: |\n| Service | 25 |",
            "## Later section\n\n1. First clause\n2. Second clause",
        ],
        output,
    )

    assert result.output_path == output
    assert shell.read_bytes() == before
    document = Document(output)
    assert "Shell wording must be replaced." not in "\n".join(
        paragraph.text for paragraph in document.paragraphs
    )
    assert document.sections[0].page_width == Inches(8.5)
    assert document.sections[0].page_height == Inches(11)
    assert document.sections[0].left_margin == Inches(1.1)
    assert document.sections[0].right_margin == Inches(0.9)
    assert document.sections[0].header.paragraphs[0].text == "Shell header"
    assert document.sections[0].footer.paragraphs[0].text == "Shell footer"
    assert [paragraph.style.style_id for paragraph in document.paragraphs] == [
        "Normal", "Heading2", "ListParagraph", "ListParagraph"
    ]
    body = xml_part(output, "word/document.xml").find("w:body", NS)
    assert [etree.QName(child).localname for child in body] == [
        "p", "tbl", "p", "p", "p", "sectPr"
    ]
    assert [[cell.text for cell in row.cells] for row in document.tables[0].rows] == [
        ["Item", "Fee"], ["Service", "25"]
    ]


def test_numbering_ids_are_remapped_between_components(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    output = tmp_path / "lists.docx"
    docx_compose.compose_document(
        shell, ["1. First component", "1. Second component"], output
    )

    document_root = xml_part(output, "word/document.xml")
    numbering_root = xml_part(output, "word/numbering.xml")
    paragraph_ids = [
        paragraph.find("w:pPr/w:numPr/w:numId", NS).get(W + "val")
        for paragraph in document_root.findall(".//w:body/w:p", NS)
    ]
    assert len(paragraph_ids) == 2
    assert paragraph_ids[0] != paragraph_ids[1]
    instances = {
        item.get(W + "numId"): item.find("w:abstractNumId", NS).get(W + "val")
        for item in numbering_root.findall("w:num", NS)
    }
    abstract_ids = {
        item.get(W + "abstractNumId")
        for item in numbering_root.findall("w:abstractNum", NS)
    }
    assert all(number_id in instances for number_id in paragraph_ids)
    assert all(instances[number_id] in abstract_ids for number_id in paragraph_ids)
    assert len(instances) == len(set(instances))


def test_missing_numbering_part_is_created_with_relationship_and_content_type(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    stripped = tmp_path / "shell-without-numbering.docx"
    with zipfile.ZipFile(shell, "r") as source, zipfile.ZipFile(stripped, "w") as target:
        for info in source.infolist():
            if info.filename == "word/numbering.xml":
                continue
            data = source.read(info.filename)
            if info.filename == "word/_rels/document.xml.rels":
                root = etree.fromstring(data)
                for relation in list(root):
                    if relation.get("Type") == NUMBERING_REL:
                        root.remove(relation)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8")
            elif info.filename == "[Content_Types].xml":
                root = etree.fromstring(data)
                for override in list(root):
                    if override.get("PartName") == "/word/numbering.xml":
                        root.remove(override)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8")
            target.writestr(info, data)

    output = tmp_path / "created-numbering.docx"
    docx_compose.compose_document(stripped, ["1. Numbered"], output)
    with zipfile.ZipFile(output) as package:
        names = set(package.namelist())
        assert "word/numbering.xml" in names
        rels = etree.fromstring(package.read("word/_rels/document.xml.rels"))
        assert any(item.get("Type") == NUMBERING_REL for item in rels)
        types = etree.fromstring(package.read("[Content_Types].xml"))
        assert any(
            item.get("PartName") == "/word/numbering.xml"
            and item.get("ContentType", "").endswith(".numbering+xml")
            for item in types
        )
    assert Document(output).paragraphs[0].text == "Numbered"


def test_output_cannot_overwrite_the_shell(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    before = shell.read_bytes()
    with pytest.raises(ValueError, match="different file"):
        docx_compose.compose_document(shell, ["New wording"], shell)
    assert shell.read_bytes() == before


def test_composed_fields_are_discovered_once_and_filled_in_all_blocks(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    output = tmp_path / "fields.docx"
    docx_compose.compose_document(
        shell,
        [
            "Opening for {{Client Name}}.\n\n"
            "1. Pay {{Fee | money-words}} to {{Publisher Name}}.",
            "| Effective date | Client |\n| --- | --- |\n"
            "| {{Effective Date | date-formal}} | {{Client Name}} |",
        ],
        output,
    )

    template = core.Template(output)
    names = [field.name for field in template.field_list()]
    assert Counter(names) == Counter({
        "Client Name": 1, "Fee": 1, "Publisher Name": 1, "Effective Date": 1
    })
    assert template.places == 5

    data, report = core.render(template, {
        "Client Name": "Northstar Widgets",
        "Fee": "1250",
        "Publisher Name": "Example Press",
        "Effective Date": "10/5/2026",
    })
    filled = Document(BytesIO(data))
    body_text = "\n".join(paragraph.text for paragraph in filled.paragraphs)
    assert "Northstar Widgets" in body_text
    assert "One Thousand Two Hundred Fifty Dollars ($1,250.00)" in body_text
    assert "Example Press" in body_text
    assert filled.tables[0].cell(1, 0).text == "5th day of October, 2026"
    assert filled.tables[0].cell(1, 1).text == "Northstar Widgets"
    assert "{{" not in body_text
    assert report.blanks == []


@pytest.mark.parametrize(
    "include_clause,include_cell,clause_present,cell_text",
    [
        (True, True, True, "Shown"),
        (True, False, True, "Hidden"),
        (False, True, False, "Shown"),
        (False, False, False, "Hidden"),
    ],
)
def test_conditions_across_components_and_inside_cells(
    tmp_path, include_clause, include_cell, clause_present, cell_text
):
    shell = make_shell(tmp_path / "shell.docx")
    output = tmp_path / "conditions.docx"
    docx_compose.compose_document(
        shell,
        [
            "{{#if Include Clause}}",
            "Optional clause for {{Client Name}}.",
            "{{/if}}\n\n"
            "| Cell condition | Result |\n| --- | --- |\n"
            "| {{#if Include Cell}}Shown{{else}}Hidden{{/if}} | yes |",
        ],
        output,
    )
    template = core.Template(output)
    data, _ = core.render(template, {
        "Include Clause": include_clause,
        "Include Cell": include_cell,
        "Client Name": "Northstar Widgets",
    })
    filled = Document(BytesIO(data))
    body_text = "\n".join(paragraph.text for paragraph in filled.paragraphs)
    assert ("Optional clause for Northstar Widgets." in body_text) is clause_present
    assert filled.tables[0].cell(1, 0).text == cell_text
