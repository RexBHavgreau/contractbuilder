"""Tests for Markdown-to-Word paragraph and inline rendering."""
import pathlib
import sys

from docx import Document

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import md_to_word  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def make_shell(path):
    """Build a disposable shell; no Word template is committed."""
    document = Document()
    document.add_paragraph("Invented shell wording.")
    document.save(path)
    return path


def test_paragraph_and_heading_use_shell_styles(tmp_path):
    result = md_to_word.render_markdown(
        "A paragraph.\n\n# First\n\n## Second\n\n### Third",
        make_shell(tmp_path / "shell.docx"),
    )
    assert result.can_generate
    assert [item.find("w:pPr/w:pStyle", NS).get("{%s}val" % W) for item in result.elements] == [
        "Normal", "Heading1", "Heading2", "Heading3"
    ]
    assert ["".join(item.xpath(".//w:t/text()", namespaces=NS)) for item in result.elements] == [
        "A paragraph.", "First", "Second", "Third"
    ]


def test_bold_italic_and_combined_emphasis_are_word_run_properties(tmp_path):
    result = md_to_word.render_markdown(
        "Plain **bold** _italic_ ***both***.",
        make_shell(tmp_path / "shell.docx"),
    )
    runs = result.elements[0].findall("w:r", NS)
    by_text = {"".join(run.xpath(".//w:t/text()", namespaces=NS)): run for run in runs}
    assert by_text["bold"].find("w:rPr/w:b", NS) is not None
    assert by_text["italic"].find("w:rPr/w:i", NS) is not None
    assert by_text["both"].find("w:rPr/w:b", NS) is not None
    assert by_text["both"].find("w:rPr/w:i", NS) is not None


def test_field_spelling_survives_inside_emphasis(tmp_path):
    result = md_to_word.render_markdown(
        "**{{First_Name}}** and _{{Fee | money-words}}_",
        make_shell(tmp_path / "shell.docx"),
    )
    text = "".join(result.elements[0].xpath(".//w:t/text()", namespaces=NS))
    assert text == "{{First_Name}} and {{Fee | money-words}}"
    runs = result.elements[0].findall("w:r", NS)
    assert runs[0].find("w:rPr/w:b", NS) is not None
    assert runs[2].find("w:rPr/w:i", NS) is not None


def test_hard_line_break_becomes_word_break(tmp_path):
    result = md_to_word.render_markdown(
        "First line  \nsecond line", make_shell(tmp_path / "shell.docx")
    )
    assert result.elements[0].find(".//w:br", NS) is not None


def test_unsupported_image_and_code_are_reported_and_text_is_kept(tmp_path):
    result = md_to_word.render_markdown(
        "An ![invented diagram](image.png) and `code`.",
        make_shell(tmp_path / "shell.docx"),
    )
    codes = {item.code for item in result.warnings}
    assert "markdown.image" in codes
    assert "markdown.inline_code" in codes
    text = "".join(result.elements[0].xpath(".//w:t/text()", namespaces=NS))
    assert "invented diagram" in text and "code" in text


def test_unsupported_table_is_reported_not_silently_rendered(tmp_path):
    result = md_to_word.render_markdown(
        "| A | B |\n| --- | --- |\n| 1 | 2 |",
        make_shell(tmp_path / "shell.docx"),
    )
    assert result.elements == ()
    assert any(item.code == "markdown.block_unsupported" for item in result.warnings)


def test_shell_error_stops_rendering(tmp_path):
    result = md_to_word.render_markdown("Some text", tmp_path / "missing.docx")
    assert not result.can_generate
    assert result.elements == ()
    assert result.errors[0].code == "shell.not_found"


def test_shell_style_fallback_is_applied_and_warning_returned(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    document = Document(path)
    style = document.styles["Heading 2"]
    style._element.getparent().remove(style._element)
    document.save(path)
    result = md_to_word.render_markdown("## Heading", path)
    pstyle = result.elements[0].find("w:pPr/w:pStyle", NS)
    assert pstyle.get("{%s}val" % W) == "Heading1"
    assert any(item.code == "shell.style.Heading2" for item in result.warnings)


def test_raw_html_like_text_is_reported_and_kept_as_text(tmp_path):
    result = md_to_word.render_markdown(
        "Text <b>not bold</b>.", make_shell(tmp_path / "shell.docx")
    )
    assert any(item.code == "markdown.raw_html" for item in result.warnings)
    assert "<b>not bold</b>" in "".join(
        result.elements[0].xpath(".//w:t/text()", namespaces=NS)
    )
