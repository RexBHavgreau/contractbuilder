"""Styles the app adds to a new document when the shell lacks them (T-060-A)."""
import pathlib
import shutil
import sys
import zipfile

from docx import Document
from lxml import etree
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import docx_compose  # noqa: E402
import shell_check  # noqa: E402
import shell_styles  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
MARKDOWN = (
    "# Heading one\n\n## Heading two\n\n### Heading three\n\nPlain words.\n\n"
    "- a bullet\n\n1. a number\n\n| One | Two |\n| --- | --- |\n| 1 | 2 |\n"
)
ALL = list(shell_styles.SUPPLIABLE)


def make_shell(path, remove=(), rename=None):
    """An invented shell: python-docx's default styles, minus those removed."""
    document = Document()
    document.add_paragraph("Invented shell wording.")
    document.add_table(rows=1, cols=1)
    styles = document.styles.element
    for style in list(styles.findall("w:style", NS)):
        sid = style.get("{%s}styleId" % W)
        if sid in remove:
            styles.remove(style)
        elif rename and sid in rename:
            style.set("{%s}styleId" % W, rename[sid])
    document.save(path)
    return pathlib.Path(path)


def styles_of(path):
    with zipfile.ZipFile(path) as package:
        root = etree.fromstring(package.read("word/styles.xml"))
    return {
        s.get("{%s}styleId" % W): s for s in root.findall("w:style", NS)
    }


def used_styles(path):
    with zipfile.ZipFile(path) as package:
        root = etree.fromstring(package.read("word/document.xml"))
    return [e.get("{%s}val" % W) for e in root.iterfind(".//w:pStyle", NS)] + [
        e.get("{%s}val" % W) for e in root.iterfind(".//w:tblStyle", NS)
    ]


@pytest.mark.parametrize("missing", ALL)
def test_each_style_missing_in_turn_is_defined_in_the_output(tmp_path, missing):
    shell = make_shell(tmp_path / "shell.docx", remove=[missing])
    before = shell.read_bytes()
    result = docx_compose.compose_document(shell, [MARKDOWN], tmp_path / "out.docx")
    defined = styles_of(result.output_path)
    assert missing in defined
    assert result.added_styles == (shell_styles.SUPPLIABLE[missing][1],)
    assert all(style in defined for style in used_styles(result.output_path))
    assert shell.read_bytes() == before  # the source file is never changed


def test_all_styles_missing_and_no_normal_still_works(tmp_path):
    shell = make_shell(tmp_path / "shell.docx", remove=ALL + ["Normal", "BodyText"])
    result = docx_compose.compose_document(shell, [MARKDOWN], tmp_path / "out.docx")
    defined = styles_of(result.output_path)
    assert set(ALL) <= set(defined)
    assert set(result.added_styles) == {shell_styles.SUPPLIABLE[i][1] for i in ALL}
    assert all(
        style in defined or style == "Normal" for style in used_styles(result.output_path)
    )
    Document(str(result.output_path))  # python-docx can open it


def test_added_styles_are_based_on_normal_or_body_text(tmp_path):
    with_normal = make_shell(tmp_path / "a.docx", remove=["Heading1"])
    out = docx_compose.compose_document(with_normal, [MARKDOWN], tmp_path / "a-out.docx")
    based = styles_of(out.output_path)["Heading1"].find("w:basedOn", NS)
    assert based.get("{%s}val" % W) == "Normal"

    body_text_only = make_shell(
        tmp_path / "b.docx", remove=["Normal", "Heading1"], rename={"BodyText": "BodyText"}
    )
    # python-docx's default file has Body Text; with Normal gone it is the base.
    if "BodyText" in styles_of(body_text_only):
        out = docx_compose.compose_document(body_text_only, [MARKDOWN], tmp_path / "b-out.docx")
        based = styles_of(out.output_path)["Heading1"].find("w:basedOn", NS)
        assert based.get("{%s}val" % W) == "BodyText"


def test_list_styles_sit_on_list_paragraph_and_headings_look_like_headings(tmp_path):
    shell = make_shell(tmp_path / "s.docx", remove=["ListParagraph", "ListBullet", "Heading2"])
    out = docx_compose.compose_document(shell, [MARKDOWN], tmp_path / "o.docx")
    defined = styles_of(out.output_path)
    parent = defined["ListBullet"].find("w:basedOn", NS).get("{%s}val" % W)
    assert parent == "ListParagraph"
    assert defined["ListParagraph"].find("w:pPr/w:ind", NS) is not None
    heading = defined["Heading2"]
    assert heading.find("w:pPr/w:outlineLvl", NS).get("{%s}val" % W) == "1"
    assert heading.find("w:rPr/w:b", NS) is not None


def test_table_grid_gets_borders(tmp_path):
    shell = make_shell(tmp_path / "s.docx", remove=["TableGrid"])
    out = docx_compose.compose_document(shell, [MARKDOWN], tmp_path / "o.docx")
    grid = styles_of(out.output_path)["TableGrid"]
    assert grid.get("{%s}type" % W) == "table"
    assert len(grid.findall("w:tblPr/w:tblBorders/*", NS)) == 6


def test_style_with_the_word_name_but_another_id_is_used_not_duplicated(tmp_path):
    shell = make_shell(tmp_path / "s.docx", rename={"ListParagraph": "MyListStyle"})
    plan = shell_styles.plan_styles(
        etree.fromstring(zipfile.ZipFile(shell).read("word/styles.xml"))
    )
    assert plan.use["ListParagraph"] == "MyListStyle"
    assert "ListParagraph" not in plan.add
    out = docx_compose.compose_document(shell, [MARKDOWN], tmp_path / "o.docx")
    assert "MyListStyle" in used_styles(out.output_path)
    assert "ListParagraph" not in styles_of(out.output_path)
    assert out.added_styles == ()


def test_a_file_that_has_everything_keeps_its_styles_part_unchanged(tmp_path):
    shell = make_shell(tmp_path / "s.docx")
    out = docx_compose.compose_document(shell, [MARKDOWN], tmp_path / "o.docx")
    assert out.added_styles == ()
    with zipfile.ZipFile(shell) as a, zipfile.ZipFile(out.output_path) as b:
        assert a.read("word/styles.xml") == b.read("word/styles.xml")


def test_a_package_with_no_styles_part_gets_one(tmp_path):
    source = make_shell(tmp_path / "full.docx")
    bare = tmp_path / "bare.docx"
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(bare, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "word/styles.xml":
                continue
            if info.filename == "[Content_Types].xml":
                data = data.replace(
                    b'<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>',
                    b"",
                )
            if info.filename == "word/_rels/document.xml.rels":
                root = etree.fromstring(data)
                for rel in list(root):
                    if rel.get("Type", "").endswith("/styles"):
                        root.remove(rel)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            dst.writestr(info, data)
    out = docx_compose.compose_document(bare, [MARKDOWN], tmp_path / "o.docx")
    assert set(ALL) <= set(styles_of(out.output_path))
    Document(str(out.output_path))


def test_checker_reports_supplied_styles_as_notes_not_warnings(tmp_path):
    shell = make_shell(tmp_path / "s.docx", remove=["ListNumber", "Heading2"])
    default = shell_check.check_shell(shell)
    assert {"shell.style.ListNumber", "shell.style.Heading2"} <= {w.code for w in default.warnings}
    supplied = shell_check.check_shell(shell, supply_missing=True)
    assert supplied.warnings == ()
    assert {n.code for n in supplied.notes} >= {"shell.style.ListNumber", "shell.style.Heading2"}
    assert supplied.can_generate
    assert all("Your file is not changed" in n.message for n in supplied.notes)
    assert supplied.style_fallbacks["Heading2"] == "Heading2"


def test_a_style_with_the_right_id_but_the_wrong_type_is_still_a_warning(tmp_path):
    shell = make_shell(tmp_path / "s.docx")
    document = Document(str(shell))
    document.styles.element.find(
        "w:style[@w:styleId='ListBullet']", NS
    ).set("{%s}type" % W, "character")
    document.save(str(shell))
    result = shell_check.check_shell(shell, supply_missing=True)
    assert "shell.style.ListBullet" in {w.code for w in result.warnings}


def test_composing_never_writes_to_the_shell_even_when_adding_styles(tmp_path):
    shell = make_shell(tmp_path / "s.docx", remove=ALL)
    copy = tmp_path / "copy.docx"
    shutil.copy(shell, copy)
    docx_compose.compose_document(shell, [MARKDOWN], tmp_path / "o.docx")
    assert shell.read_bytes() == copy.read_bytes()
