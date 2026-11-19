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


def test_table_is_rendered_as_native_word_table(tmp_path):
    result = md_to_word.render_markdown(
        "| A | B |\n| --- | --- |\n| 1 | 2 |",
        make_shell(tmp_path / "shell.docx"),
    )
    assert result.can_generate
    assert len(result.elements) == 1
    assert result.elements[0].tag == "{%s}tbl" % W


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

def _append_rendered(path, result):
    """Put renderer output into an invented DOCX so core can inspect it."""
    document = Document(path)
    numbering = document.part.numbering_part.element
    for item in result.numbering:
        numbering.append(item)
    body = document._element.body
    for item in result.elements:
        body.insert(len(body) - 1, item)
    output = path.with_name("rendered.docx")
    document.save(output)
    return output


def _num_pr(paragraph):
    return paragraph.find("w:pPr/w:numPr", NS)


def test_separate_ordered_lists_get_separate_restarting_instances(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    result = md_to_word.render_markdown(
        "7. First list item\n8. Second item\n\nA break.\n\n1. New list starts",
        shell,
    )
    paragraphs = [item for item in result.elements if item.tag == "{%s}p" % W]
    numbered = [_num_pr(item) for item in paragraphs]
    assert numbered[0] is not None and numbered[1] is not None
    assert numbered[2] is None  # the paragraph between lists is ordinary text
    assert numbered[3] is not None
    ids = [numbered[i].find("w:numId", NS).get("{%s}val" % W) for i in (0, 1, 3)]
    assert ids[0] == ids[1]
    assert ids[2] != ids[0]
    instances = {item.get("{%s}numId" % W): item for item in result.numbering
                 if item.tag == "{%s}num" % W}
    assert ids[0] in instances and ids[2] in instances


def test_nested_ordered_lists_use_three_decimal_outline_levels(tmp_path):
    result = md_to_word.render_markdown(
        "1. Parent\n   1. Child\n      1. Grandchild\n2. Next parent",
        make_shell(tmp_path / "shell.docx"),
    )
    paragraphs = [item for item in result.elements if item.tag == "{%s}p" % W]
    levels = [_num_pr(item).find("w:ilvl", NS).get("{%s}val" % W)
              for item in paragraphs]
    assert levels == ["0", "1", "2", "0"]
    assert len({_num_pr(item).find("w:numId", NS).get("{%s}val" % W)
                for item in paragraphs}) == 1
    abstract = next(item for item in result.numbering
                    if item.tag == "{%s}abstractNum" % W)
    level_text = [item.find("w:lvlText", NS).get("{%s}val" % W)
                  for item in abstract.findall("w:lvl", NS)]
    assert level_text == ["%1.", "%1.%2", "%1.%2.%3"]


def test_list_continuation_paragraph_is_not_numbered(tmp_path):
    result = md_to_word.render_markdown(
        "1. First paragraph\n\n   Continuation paragraph.\n\n2. Second item",
        make_shell(tmp_path / "shell.docx"),
    )
    paragraphs = [item for item in result.elements if item.tag == "{%s}p" % W]
    assert _num_pr(paragraphs[0]) is not None
    assert _num_pr(paragraphs[1]) is None
    assert _num_pr(paragraphs[2]) is not None


def test_fields_in_list_items_remain_fillable(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    result = md_to_word.render_markdown(
        "1. Pay **{{Fee | money-words}}** to {{Publisher Name}}.",
        shell,
    )
    output = _append_rendered(shell, result)
    import core
    template = core.Template(output)
    names = {field.name for field in template.field_list()}
    assert names == {"Fee", "Publisher Name"}


def test_table_header_alignment_empty_cells_and_fields(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    result = md_to_word.render_markdown(
        "| Item | Fee | Notes |\n| :--- | ---: | :---: |\n"
        "| A | {{Fee | money-words}} | **Bold** |\n| B |  | C |",
        shell,
    )
    table = result.elements[0]
    assert table.tag == "{%s}tbl" % W
    assert len(table.findall("w:tblGrid/w:gridCol", NS)) == 3
    rows = table.findall("w:tr", NS)
    assert len(rows) == 3
    assert rows[0].find("w:trPr/w:tblHeader", NS) is not None
    cells = rows[0].findall("w:tc", NS)
    assert [cell.find("w:p/w:pPr/w:jc", NS).get("{%s}val" % W)
            for cell in cells] == ["left", "right", "center"]
    assert rows[2].findall("w:tc", NS)[1].find("w:p", NS) is not None
    text = "".join(table.xpath(".//w:t/text()", namespaces=NS))
    assert "{{Fee | money-words}}" in text
    assert rows[1].find("w:tc[3]/w:p/w:r/w:rPr/w:b", NS) is not None


def test_table_fields_are_fillable_by_existing_template_engine(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    result = md_to_word.render_markdown(
        "| Fee |\n| --- |\n| {{Fee | money-words}} |",
        shell,
    )
    output = _append_rendered(shell, result)
    import core
    template = core.Template(output)
    assert [field.name for field in template.field_list()] == ["Fee"]


def test_renderer_never_changes_shell_file(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    before = shell.read_bytes()
    md_to_word.render_markdown(
        "1. List\n\n| A |\n| --- |\n| B |", shell
    )
    assert shell.read_bytes() == before


def test_bulleted_lists_use_word_numbering(tmp_path):
    result = md_to_word.render_markdown(
        "- First\n  - Nested bullet\n- Second",
        make_shell(tmp_path / "shell.docx"),
    )
    paragraphs = [item for item in result.elements if item.tag == "{%s}p" % W]
    assert len(paragraphs) == 3
    assert all(_num_pr(item) is not None for item in paragraphs)
    assert len({item.find("w:numId", NS).get("{%s}val" % W)
                for item in (_num_pr(p) for p in paragraphs)}) == 1
    # The shell's bullet definition may contain only level zero. Nested
    # bullets keep that valid definition and gain direct paragraph indents.
    assert _num_pr(paragraphs[0]).find("w:ilvl", NS).get("{%s}val" % W) == "0"
    assert _num_pr(paragraphs[1]).find("w:ilvl", NS).get("{%s}val" % W) == "0"
    first_indent = paragraphs[0].find("w:pPr/w:ind", NS)
    nested_indent = paragraphs[1].find("w:pPr/w:ind", NS)
    assert nested_indent is not None
    assert int(nested_indent.get("{%s}left" % W)) > (
        int(first_indent.get("{%s}left" % W)) if first_indent is not None else 0
    )


def test_ordered_lists_reuse_shell_decimal_outline(tmp_path):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    path = make_shell(tmp_path / "shell-with-outline.docx")
    document = Document(path)
    numbering = document.part.numbering_part.element
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), "99")
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "multilevel")
    abstract.append(multi)
    for level_number, label in enumerate(("%1.", "%1.%2", "%1.%2.%3")):
        level = OxmlElement("w:lvl")
        level.set(qn("w:ilvl"), str(level_number))
        fmt = OxmlElement("w:numFmt")
        fmt.set(qn("w:val"), "decimal")
        text = OxmlElement("w:lvlText")
        text.set(qn("w:val"), label)
        level.extend((fmt, text))
        abstract.append(level)
    numbering.append(abstract)
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), "99")
    abstract_ref = OxmlElement("w:abstractNumId")
    abstract_ref.set(qn("w:val"), "99")
    num.append(abstract_ref)
    numbering.append(num)
    document.save(path)

    result = md_to_word.render_markdown("1. First\\n   1. Nested", path)
    assert not any(item.tag == "{%s}abstractNum" % W for item in result.numbering)
    instance = next(item for item in result.numbering if item.tag == "{%s}num" % W)
    assert instance.find("w:abstractNumId", NS).get("{%s}val" % W) == "99"


def test_typed_ordered_digits_are_not_rendered_as_text(tmp_path):
    result = md_to_word.render_markdown(
        "7. First item\\n9. Second item",
        make_shell(tmp_path / "shell.docx"),
    )
    paragraphs = [item for item in result.elements if item.tag == "{%s}p" % W]
    assert ["".join(item.xpath(".//w:t/text()", namespaces=NS))
            for item in paragraphs] == ["First item", "Second item"]
    abstract = next(item for item in result.numbering
                    if item.tag == "{%s}abstractNum" % W)
    assert abstract.find("w:lvl/w:start", NS).get("{%s}val" % W) == "1"


def test_reordered_list_items_remain_native_and_follow_source_order(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    first = md_to_word.render_markdown("1. Alpha\\n2. Beta", shell)
    moved = md_to_word.render_markdown("2. Beta\\n1. Alpha", shell)
    def texts(result):
        return ["".join(item.xpath(".//w:t/text()", namespaces=NS))
                for item in result.elements if item.tag == "{%s}p" % W]
    assert texts(first) == ["Alpha", "Beta"]
    assert texts(moved) == ["Beta", "Alpha"]
    assert all(_num_pr(item) is not None for item in moved.elements)
    assert len({_num_pr(item).find("w:numId", NS).get("{%s}val" % W)
                for item in moved.elements if item.tag == "{%s}p" % W}) == 1
