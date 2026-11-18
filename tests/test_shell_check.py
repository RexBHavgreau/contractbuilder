"""Tests for the read-only Word shell checker."""
import pathlib
import sys
import zipfile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import shell_check  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def _add_outline_definition(document):
    numbering = document.part.numbering_part.element
    ids = [int(item.get(qn("w:abstractNumId")))
           for item in numbering.findall(qn("w:abstractNum"))]
    abstract_id = max(ids or [0]) + 1
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "multilevel")
    abstract.append(multi)
    for level_number, label in enumerate(("%1.", "%1.%2", "%1.%2.%3")):
        level = OxmlElement("w:lvl")
        level.set(qn("w:ilvl"), str(level_number))
        start = OxmlElement("w:start")
        start.set(qn("w:val"), "1")
        level.append(start)
        fmt = OxmlElement("w:numFmt")
        fmt.set(qn("w:val"), "decimal")
        level.append(fmt)
        text = OxmlElement("w:lvlText")
        text.set(qn("w:val"), label)
        level.append(text)
        abstract.append(level)
    numbering.append(abstract)
    nums = [int(item.get(qn("w:numId"))) for item in numbering.findall(qn("w:num"))]
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(max(nums or [0]) + 1))
    ref = OxmlElement("w:abstractNumId")
    ref.set(qn("w:val"), str(abstract_id))
    num.append(ref)
    numbering.append(num)


def make_shell(path):
    """Build an invented shell in code; no real template is committed."""
    document = Document()
    document.add_paragraph("Invented shell body text is not assembled content.")
    document.add_table(rows=1, cols=1)
    _add_outline_definition(document)
    document.save(path)
    return path


def _rewrite_member(path, member, transform):
    temporary = path.with_suffix(".rewritten.docx")
    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(temporary, "w") as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == member:
                root = etree.fromstring(data)
                transform(root)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            target.writestr(info, data)
    temporary.replace(path)


def _remove_style(style_id):
    def transform(root):
        for style in list(root.findall("w:style", NS)):
            if style.get("{%s}styleId" % W) == style_id:
                root.remove(style)
    return transform


@pytest.mark.parametrize(("style_id", "fallback"), [
    ("Normal", None), ("Heading1", "Normal"), ("Heading2", "Heading1"),
    ("Heading3", "Heading2"), ("ListParagraph", "Normal"),
    ("ListBullet", "ListParagraph"), ("ListNumber", "ListParagraph"),
    ("TableGrid", "TableNormal"),
])
def test_missing_style_has_explicit_fallback(tmp_path, style_id, fallback):
    path = make_shell(tmp_path / "invented-shell.docx")
    _rewrite_member(path, "word/styles.xml", _remove_style(style_id))
    result = shell_check.check_shell(path)
    finding = next(item for item in result.warnings if item.code == "shell.style." + style_id)
    assert finding.severity == "warning"
    assert result.style_fallbacks[style_id] == fallback
    assert result.can_generate


def test_complete_shell_passes_without_warnings(tmp_path):
    result = shell_check.check_shell(make_shell(tmp_path / "shell.docx"))
    assert result.can_generate and result.warnings == () and result.errors == ()


def test_missing_final_section_stops_generation(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    def remove(root):
        body = root.find("w:body", NS)
        body.remove(body.find("w:sectPr", NS))
    _rewrite_member(path, "word/document.xml", remove)
    result = shell_check.check_shell(path)
    assert not result.can_generate
    assert any(item.code == "shell.no_final_section" for item in result.errors)


def test_section_break_properties_do_not_replace_final_section(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    def move(root):
        body = root.find("w:body", NS)
        section = body.find("w:sectPr", NS)
        body.remove(section)
        paragraph = OxmlElement("w:p")
        body.append(paragraph)
        ppr = OxmlElement("w:pPr")
        ppr.append(section)
        paragraph.append(ppr)
    _rewrite_member(path, "word/document.xml", move)
    result = shell_check.check_shell(path)
    assert not result.can_generate
    assert any(item.code == "shell.no_final_section" for item in result.errors)


def test_final_section_properties_must_be_last_body_child(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    def append_after_section(root):
        body = root.find("w:body", NS)
        body.append(OxmlElement("w:p"))
    _rewrite_member(path, "word/document.xml", append_after_section)
    result = shell_check.check_shell(path)
    assert not result.can_generate
    assert any(item.code == "shell.no_final_section" for item in result.errors)


def _remove_outline(root):
    ids = set()
    for abstract in list(root.findall("w:abstractNum", NS)):
        levels = abstract.findall("w:lvl", NS)
        if len(levels) >= 3 and all(
            level.find("w:numFmt", NS) is not None
            and level.find("w:numFmt", NS).get("{%s}val" % W) == "decimal"
            for level in levels[:3]
        ):
            ids.add(abstract.get("{%s}abstractNumId" % W))
            root.remove(abstract)
    for num in list(root.findall("w:num", NS)):
        ref = num.find("w:abstractNumId", NS)
        if ref is not None and ref.get("{%s}val" % W) in ids:
            root.remove(num)


def _remove_bullets(root):
    ids = set()
    for abstract in list(root.findall("w:abstractNum", NS)):
        if any(
            level.find("w:numFmt", NS) is not None
            and level.find("w:numFmt", NS).get("{%s}val" % W) == "bullet"
            for level in abstract.findall("w:lvl", NS)
        ):
            ids.add(abstract.get("{%s}abstractNumId" % W))
            root.remove(abstract)
    for num in list(root.findall("w:num", NS)):
        ref = num.find("w:abstractNumId", NS)
        if ref is not None and ref.get("{%s}val" % W) in ids:
            root.remove(num)


def test_missing_decimal_outline_warns(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    _rewrite_member(path, "word/numbering.xml", _remove_outline)
    result = shell_check.check_shell(path)
    assert result.can_generate
    assert any(item.code == "shell.numbering.decimal_outline" for item in result.warnings)


def test_missing_bullet_definition_warns(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    _rewrite_member(path, "word/numbering.xml", _remove_bullets)
    result = shell_check.check_shell(path)
    assert result.can_generate
    assert any(item.code == "shell.numbering.bullets" for item in result.warnings)


def test_missing_numbering_part_reports_both_warnings(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    temporary = path.with_suffix(".without-numbering.docx")
    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(temporary, "w") as target:
        for info in source.infolist():
            if info.filename != "word/numbering.xml":
                target.writestr(info, source.read(info.filename))
    temporary.replace(path)
    result = shell_check.check_shell(path)
    codes = {item.code for item in result.warnings}
    assert {"shell.numbering.decimal_outline", "shell.numbering.bullets"} <= codes


def test_missing_page_setup_warns(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    def remove(root):
        section = root.find("w:body/w:sectPr", NS)
        section.remove(section.find("w:pgSz", NS))
        section.remove(section.find("w:pgMar", NS))
    _rewrite_member(path, "word/document.xml", remove)
    result = shell_check.check_shell(path)
    codes = {item.code for item in result.warnings}
    assert {"shell.no_page_size", "shell.no_page_margins"} <= codes


def test_checker_does_not_modify_shell(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    before = path.read_bytes()
    shell_check.check_shell(path)
    assert path.read_bytes() == before


def test_invalid_file_returns_plain_english_error(tmp_path):
    path = tmp_path / "not-a-word-file.docx"
    path.write_text("not a Word document", encoding="utf-8")
    result = shell_check.check_shell(path)
    assert not result.can_generate
    assert result.errors[0].code == "shell.unreadable"
    assert "cannot be used as a Word shell" in result.errors[0].message



def test_style_with_wrong_type_is_reported(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    def change_type(root):
        for style in root.findall("w:style", NS):
            if style.get("{%s}styleId" % W) == "Heading2":
                style.set("{%s}type" % W, "character")
    _rewrite_member(path, "word/styles.xml", change_type)
    result = shell_check.check_shell(path)
    finding = next(item for item in result.warnings if item.code == "shell.style.Heading2")
    assert "not a paragraph style" in finding.message
    assert result.style_fallbacks["Heading2"] == "Heading1"


def test_single_level_definition_is_not_a_decimal_outline(tmp_path):
    path = make_shell(tmp_path / "shell.docx")
    def make_single_level(root):
        for abstract in root.findall("w:abstractNum", NS):
            levels = abstract.findall("w:lvl", NS)
            if len(levels) >= 3 and all(
                level.find("w:numFmt", NS) is not None
                and level.find("w:numFmt", NS).get("{%s}val" % W) == "decimal"
                for level in levels[:3]
            ):
                multi = abstract.find("w:multiLevelType", NS)
                multi.set("{%s}val" % W, "singleLevel")
    _rewrite_member(path, "word/numbering.xml", make_single_level)
    result = shell_check.check_shell(path)
    assert any(item.code == "shell.numbering.decimal_outline" for item in result.warnings)
