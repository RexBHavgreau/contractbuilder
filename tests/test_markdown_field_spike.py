"""T-019-A spike: Markdown field protection and hand-off to core.py."""
import io
import pathlib
import sys
import zipfile

from docx import Document
from lxml import etree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import core  # noqa: E402
from markdown_fields import protect_fields, restore_fields  # noqa: E402
from md_parse import create_parser  # noqa: E402


def _inline_text(token):
    return "".join(
        child.content for child in (token.children or [])
        if child.type in ("text", "code_inline", "html_inline")
    )


def _restore_parse(source):
    protected, replacements = protect_fields(source)
    tokens = create_parser().parse(protected)
    restore_fields(tokens, replacements)
    return tokens


def test_field_names_with_underscores_and_asterisks_survive_as_literal_text():
    parser = create_parser()
    # In the current CommonMark parser these characters are already literal
    # between the braces, but protection makes that behavior explicit and safe.
    for field in ("{{First_Name}}", "{{First*Name}}", "{{First**Name**}}"):
        tokens = _restore_parse(field)
        inline = next(token for token in tokens if token.type == "inline")
        assert _inline_text(inline) == field
        assert not any(child.type in ("em_open", "strong_open") for child in inline.children)


def test_unprotected_pipe_is_treated_as_a_table_column_break():
    source = (
        "| Fee | Notes |\n"
        "| --- | --- |\n"
        "| {{Fee | money-words}} | payable later |\n"
    )
    tokens = create_parser().parse(source)
    data_cells = [token for token in tokens if token.type == "td_open"]
    inline = [token for token in tokens if token.type == "inline"][-2:]
    assert len(data_cells) == 2
    assert [_inline_text(token) for token in inline] == ["{{Fee", "money-words}}"]


def test_pipe_in_field_does_not_split_a_markdown_table_cell():
    source = (
        "| Fee | Notes |\n"
        "| --- | --- |\n"
        "| {{Fee | money-words}} | payable later |\n"
    )
    tokens = _restore_parse(source)
    cells = [token for token in tokens if token.type == "td_open"]
    inline = [token for token in tokens if token.type == "inline"]
    data_cells = inline[-2:]
    assert len(cells) == 2
    assert [_inline_text(token) for token in data_cells] == [
        "{{Fee | money-words}}", "payable later"
    ]


def test_if_markers_on_their_own_lines_survive_as_literal_text():
    source = "{{#if Include Clause}}\\n\\nWording\\n\\n{{/if}}"
    tokens = _restore_parse(source)
    inline = [token for token in tokens if token.type == "inline"]
    assert [token.content for token in inline] == [
        "{{#if Include Clause}}", "Wording", "{{/if}}"
    ]


def test_if_markers_on_separate_paragraphs_inside_a_list_item_survive():
    source = "- {{#if Include Clause}}\\n\\n  Wording\\n\\n  {{/if}}"
    tokens = _restore_parse(source)
    assert any(token.type == "bullet_list_open" for token in tokens)
    inline = [token for token in tokens if token.type == "inline"]
    assert [token.content for token in inline] == [
        "{{#if Include Clause}}", "Wording", "{{/if}}"
    ]

def test_if_markers_in_separate_table_cells_survive_as_literal_text():
    source = (
        "| Start | End |\\n"
        "| --- | --- |\\n"
        "| {{#if Include Clause}} | {{/if}} |\\n"
    )
    tokens = _restore_parse(source)
    inline = [token for token in tokens if token.type == "inline"]
    assert [_inline_text(token) for token in inline[-2:]] == [
        "{{#if Include Clause}}", "{{/if}}"
    ]


def test_field_and_inline_if_pair_inside_a_table_cell_survive():
    source = (
        "| Clause | Condition |\\n"
        "| --- | --- |\\n"
        "| {{Clause_Name}} | {{#if Include Clause}}wording{{/if}} |\\n"
    )
    tokens = _restore_parse(source)
    inline = [token for token in tokens if token.type == "inline"]
    assert [_inline_text(token) for token in inline[-2:]] == [
        "{{Clause_Name}}", "{{#if Include Clause}}wording{{/if}}"
    ]

def test_component_boundaries_are_protected_by_parsing_each_component_separately():
    # If raw components are concatenated before field protection, their edge
    # fragments can accidentally become one valid field.
    left = "{{Fee |"
    right = "money-words}}"
    assert core.TOKEN.search(left + right)  # unsafe if components are joined first
    left_protected, left_map = protect_fields(left)
    right_protected, right_map = protect_fields(right)
    assert not left_map
    assert not right_map

    left_tokens = create_parser().parse(left_protected)
    right_tokens = create_parser().parse(right_protected)
    restore_fields(left_tokens, left_map)
    restore_fields(right_tokens, right_map)
    left_inline = next(token for token in left_tokens if token.type == "inline")
    right_inline = next(token for token in right_tokens if token.type == "inline")
    assert _inline_text(left_inline) == left
    assert _inline_text(right_inline) == right
    assert not core.TOKEN.search(_inline_text(left_inline))
    assert not core.TOKEN.search(_inline_text(right_inline))


def test_protection_placeholder_cannot_collide_with_source_text():
    source = "CONTRACTBUILDERFIELD000000END {{Fee}}"
    protected, replacements = protect_fields(source)
    assert "CONTRACTBUILDERFIELD000000END" in protected
    assert "CONTRACTBUILDERFIELDX000000END" in protected
    tokens = create_parser().parse(protected)
    restore_fields(tokens, replacements)
    inline = next(token for token in tokens if token.type == "inline")
    assert _inline_text(inline) == source


def test_core_reads_and_fills_fields_in_paragraph_list_and_table(tmp_path):
    doc = Document()
    doc.add_paragraph("{{Paragraph Field}}")
    doc.add_paragraph("{{List Field}}", style="List Bullet")
    table = doc.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "{{Table Field}}"
    source = tmp_path / "generated-by-spike.docx"
    doc.save(source)

    # core.read_parts and core.Template currently take a filesystem path.
    parts = core.read_parts(source)
    assert "word/document.xml" in parts
    template = core.Template(source)
    assert [field.name for field in template.field_list()] == [
        "Paragraph Field", "List Field", "Table Field"
    ]

    rendered, report = core.render(template, {
        "Paragraph Field": "Paragraph value",
        "List Field": "List value",
        "Table Field": "Table value",
    })
    assert report.filled == 3

    # render returns DOCX bytes in memory; inspect those bytes without writing
    # an intermediate output file.
    with zipfile.ZipFile(io.BytesIO(rendered)) as package:
        root = etree.fromstring(package.read("word/document.xml"))

    ns = {"w": core.W_NS}
    paragraphs = root.findall(".//w:p", ns)
    text_by_paragraph = [
        "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
        for paragraph in paragraphs
    ]
    for expected in ("Paragraph value", "List value", "Table value"):
        matches = [p for p, text in zip(paragraphs, text_by_paragraph) if text == expected]
        assert len(matches) == 1
        runs = matches[0].findall("w:r", ns)
        assert len(runs) == 1
        assert "".join(node.text or "" for node in runs[0].findall("w:t", ns)) == expected
