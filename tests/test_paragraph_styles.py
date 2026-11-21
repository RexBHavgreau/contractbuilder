"""Paragraph styles chosen per paragraph and applied when composing (T-061)."""
import pathlib
import sys
import zipfile

from docx import Document
from lxml import etree
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import docx_compose  # noqa: E402
import md_to_word  # noqa: E402
import paragraph_styles as ps  # noqa: E402
from test_shell_styles import make_shell, styles_of  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
MARKDOWN = (
    "# Heading\n\nThe title {{Name}}\n\n- item\n\nBody line one\nstill body\n\n"
    "| A | B |\n| --- | --- |\n| 1 | 2 |\n\nLast one\n"
)


def pstyles(elements):
    return [
        e.find("w:pPr/w:pStyle", NS).get("{%s}val" % W) if e.find("w:pPr/w:pStyle", NS) is not None else None
        for e in elements if e.tag == "{%s}p" % W
    ]


# ---- the pure list -------------------------------------------------------

def test_text_paragraphs_skip_headings_lists_and_tables():
    found = ps.text_paragraphs(MARKDOWN)
    assert [p.text for p in found] == ["The title {{Name}}", "Body line one\nstill body", "Last one"]


def test_paragraph_index_at_line():
    assert ps.paragraph_index_at_line(MARKDOWN, 2) == 0
    assert ps.paragraph_index_at_line(MARKDOWN, 7) == 1
    assert ps.paragraph_index_at_line(MARKDOWN, 0) is None     # the heading
    assert ps.paragraph_index_at_line(MARKDOWN, 4) is None     # the list


def test_dump_and_load_round_trip_and_default_to_all_normal():
    assert ps.dump([]) == "" and ps.dump(["", ""]) == ""
    assert ps.load(ps.dump(["Title", "", "Subtitle"])) == ["Title", "", "Subtitle"]
    assert ps.load("") == [] and ps.load("not json") == [] and ps.load('{"a": 1}') == []
    assert ps.set_style([], 2, "Title") == ["", "", "Title"]
    assert ps.set_style(["Title"], 0, "Normal") == []


@pytest.mark.parametrize(("old", "styles", "new", "expected"), [
    (["a", "b", "c"], ["Title", "", "Subtitle"], ["a", "x", "b", "c"], ["Title", "", "", "Subtitle"]),  # insert
    (["a", "b", "c"], ["Title", "", "Subtitle"], ["a", "c"], ["Title", "Subtitle"]),                  # delete
    (["a", "b"], ["Title", "Subtitle"], ["a1", "b"], ["Title", "Subtitle"]),                          # edit in place
    (["a b"], ["Title"], ["a", "b"], ["Title", "Title"]),                                              # split
    (["a", "b"], ["Title", "Subtitle"], ["ab"], ["Title"]),                                            # merge
    (["a", "b", "c"], ["Title", "", "Subtitle"], ["c", "a", "b"], ["Subtitle", "Title"]),             # move
    ([], [], ["new"], []),                                                                              # new text
    (["a"], ["Title"], [], []),                                                                         # everything deleted
])
def test_styles_stay_with_their_paragraphs_through_every_edit(old, styles, new, expected):
    assert ps.sync_styles(old, styles, new) == expected


# ---- rendering and composing --------------------------------------------

def test_render_uses_the_named_style_for_each_text_paragraph(tmp_path):
    shell = make_shell(tmp_path / "s.docx")
    result = md_to_word.render_markdown(MARKDOWN, shell, ["Title", "", "Subtitle"])
    assert result.can_generate
    ids = pstyles(result.elements)
    assert ids[0] == "Heading1"          # headings keep their own style
    assert ids[1] == "Title"             # first text paragraph
    assert ids[2] == "ListParagraph"     # list items unaffected
    assert ids[3] == "Normal"            # second text paragraph, no choice
    assert ids[-1] == "Subtitle"         # third text paragraph


def test_no_choices_renders_exactly_as_before(tmp_path):
    shell = make_shell(tmp_path / "s.docx")
    plain = md_to_word.render_markdown(MARKDOWN, shell)
    empty = md_to_word.render_markdown(MARKDOWN, shell, ["", "", ""])
    assert [etree.tostring(e) for e in plain.elements] == [etree.tostring(e) for e in empty.elements]


def test_compose_adds_centered_title_and_subtitle_when_the_file_lacks_them(tmp_path):
    shell = make_shell(tmp_path / "s.docx", remove=["Title", "Subtitle"])
    out = docx_compose.compose_document(
        shell,
        [docx_compose.ComponentText("My title\n\nMy subtitle\n\nBody", ("Title", "Subtitle"))],
        tmp_path / "o.docx",
    )
    defined = styles_of(out.output_path)
    for name in ("Title", "Subtitle"):
        assert name in defined
        assert defined[name].find("w:pPr/w:jc", NS).get("{%s}val" % W) == "center"
    assert {"Title", "Subtitle"} <= set(out.added_styles)
    Document(str(out.output_path))


def test_the_files_own_style_wins_and_is_not_replaced(tmp_path):
    shell = make_shell(tmp_path / "s.docx")
    before = styles_of(shell)["Title"]
    assert before is not None
    out = docx_compose.compose_document(
        shell, [docx_compose.ComponentText("Name here", ("Title",))], tmp_path / "o.docx"
    )
    assert "Title" not in out.added_styles
    with zipfile.ZipFile(shell) as a, zipfile.ZipFile(out.output_path) as b:
        assert a.read("word/styles.xml") == b.read("word/styles.xml")


def test_a_style_the_file_has_under_another_name_is_found_by_its_word_name(tmp_path):
    shell = make_shell(tmp_path / "s.docx", rename={"BodyText": "MyBody"})
    result = md_to_word.render_markdown("Some words", shell, ["Body Text"])
    assert pstyles(result.elements) == ["MyBody"]


def test_an_unknown_style_becomes_normal_with_a_plain_note(tmp_path):
    shell = make_shell(tmp_path / "s.docx")
    result = md_to_word.render_markdown("Some words", shell, ["Made Up Style"])
    assert pstyles(result.elements) == ["Normal"]
    warning = next(w for w in result.warnings if w.code == "style.unknown")
    assert "Made Up Style" in warning.message and "Normal is used" in warning.message


def test_a_custom_style_that_the_file_has_is_used(tmp_path):
    shell = make_shell(tmp_path / "s.docx", rename={"Quote": "QuoteX"})
    names = [s.find("w:name", NS).get("{%s}val" % W) for s in styles_of(shell).values()
             if s.get("{%s}type" % W) == "paragraph"]
    assert any(n.lower() == "quote" for n in names)
    result = md_to_word.render_markdown("Some words", shell, ["Quote"])
    assert pstyles(result.elements) == ["QuoteX"]
