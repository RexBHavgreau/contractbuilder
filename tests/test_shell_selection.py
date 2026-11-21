"""Tests for choosing a Word shell and remembering the last usable one."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import shell_selection  # noqa: E402
from test_shell_check import _remove_style, _rewrite_member, make_shell  # noqa: E402


def _remove_page_settings(*names):
    def transform(root):
        section = root.find("w:body/w:sectPr", {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"})
        for name in names:
            section.remove(section.find("w:" + name, {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}))
    return transform


def _settings(tmp_path):
    return tmp_path / "app-data" / "shell-settings.json"


def test_complete_shell_is_usable_and_remembered(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    settings = _settings(tmp_path)
    selection = shell_selection.choose_shell(shell, settings=settings)
    assert selection.usable
    assert selection.remembered
    assert not selection.needs_review
    assert selection.lines == ("This page layout file is ready to use.",)
    assert shell_selection.last_shell(settings) == shell


def test_missing_styles_give_one_calm_line_and_no_question(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    _rewrite_member(shell, "word/styles.xml", _remove_style("Heading2"))
    _rewrite_member(shell, "word/styles.xml", _remove_style("ListNumber"))
    settings = _settings(tmp_path)
    selection = shell_selection.choose_shell(shell, settings=settings)
    assert selection.usable and selection.remembered
    assert not selection.needs_review
    assert len(selection.lines) == 1
    line = selection.lines[0]
    assert "Heading 2 style and the List Number style" in line
    assert "will add them to your new document" in line
    assert "Your file is not changed" in line
    for word in ("shell", "fallback", "outline", "style id", "warning"):
        assert word not in line.lower()
    assert shell_selection.last_shell(settings) == shell


def test_a_real_warning_asks_for_review_in_plain_english(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    _rewrite_member(shell, "word/document.xml", _remove_page_settings("pgSz"))
    settings = _settings(tmp_path)
    selection = shell_selection.choose_shell(shell, settings=settings)
    assert selection.usable and selection.remembered
    assert selection.needs_review
    assert selection.lines[0] == "Please read this before you continue:"
    assert "does not set a page size" in selection.lines[1]
    assert "shell" not in " ".join(selection.lines).lower()
    assert shell_selection.last_shell(settings) == shell


def test_several_warnings_use_plural_wording(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    _rewrite_member(shell, "word/document.xml", _remove_page_settings("pgSz", "pgMar"))
    selection = shell_selection.choose_shell(shell, settings=_settings(tmp_path))
    assert selection.lines[0] == "Please read these before you continue:"
    assert len(selection.lines) == 3


def test_unusable_file_is_reported_and_not_remembered(tmp_path):
    settings = _settings(tmp_path)
    good = make_shell(tmp_path / "good.docx")
    shell_selection.choose_shell(good, settings=settings)

    bad = tmp_path / "notes.docx"
    bad.write_text("This is plain text, not a Word file.", encoding="utf-8")
    selection = shell_selection.choose_shell(bad, settings=settings)

    assert not selection.usable
    assert not selection.remembered
    assert selection.lines[0] == "This file cannot be used as the page layout, so it has not been chosen."
    assert "could not be read as a Word document" in selection.lines[1]
    assert "shell" not in " ".join(selection.lines).lower()
    assert shell_selection.last_shell(settings) == good


def test_missing_file_is_reported_in_plain_english(tmp_path):
    selection = shell_selection.choose_shell(
        tmp_path / "gone.docx", settings=_settings(tmp_path)
    )
    assert not selection.usable
    assert "could not be found" in " ".join(selection.lines)
    assert shell_selection.last_shell(_settings(tmp_path)) is None


def test_no_internal_codes_appear_in_lines(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    _rewrite_member(shell, "word/styles.xml", _remove_style("TableGrid"))
    selection = shell_selection.choose_shell(shell, settings=_settings(tmp_path))
    text = "\n".join(selection.lines)
    assert "shell." not in text
    assert "Traceback" not in text


def test_shell_file_is_not_changed(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    before = shell.read_bytes()
    shell_selection.choose_shell(shell, settings=_settings(tmp_path))
    assert shell.read_bytes() == before


def test_remember_false_writes_nothing(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    settings = _settings(tmp_path)
    selection = shell_selection.choose_shell(shell, settings=settings, remember=False)
    assert selection.usable
    assert not selection.remembered
    assert not settings.exists()
    assert shell_selection.last_shell(settings) is None


def test_last_shell_is_forgotten_when_its_file_is_removed(tmp_path):
    shell = make_shell(tmp_path / "shell.docx")
    settings = _settings(tmp_path)
    shell_selection.choose_shell(shell, settings=settings)
    shell.unlink()
    assert shell_selection.last_shell(settings) is None


def test_last_shell_is_replaced_by_the_newer_choice(tmp_path):
    settings = _settings(tmp_path)
    first = make_shell(tmp_path / "first.docx")
    second = make_shell(tmp_path / "second.docx")
    shell_selection.choose_shell(first, settings=settings)
    shell_selection.choose_shell(second, settings=settings)
    assert shell_selection.last_shell(settings) == second


@pytest.mark.parametrize("content", [
    "not json at all",
    "[1, 2, 3]",
    '{"last_shell": 42}',
    '{"last_shell": ""}',
])
def test_damaged_settings_mean_nothing_remembered(tmp_path, content):
    settings = _settings(tmp_path)
    settings.parent.mkdir(parents=True)
    settings.write_text(content, encoding="utf-8")
    assert shell_selection.last_shell(settings) is None


def test_damaged_settings_are_replaced_on_the_next_choice(tmp_path):
    settings = _settings(tmp_path)
    settings.parent.mkdir(parents=True)
    settings.write_text("not json at all", encoding="utf-8")
    shell = make_shell(tmp_path / "shell.docx")
    selection = shell_selection.choose_shell(shell, settings=settings)
    assert selection.remembered
    assert shell_selection.last_shell(settings) == shell


def test_unwritable_settings_still_allow_the_shell_to_be_used(tmp_path):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("this file is in the way", encoding="utf-8")
    settings = blocker / "shell-settings.json"
    shell = make_shell(tmp_path / "shell.docx")
    selection = shell_selection.choose_shell(shell, settings=settings)
    assert selection.usable
    assert not selection.remembered
    assert "could not be remembered" in selection.lines[-1]
    assert shell_selection.last_shell(settings) is None


def test_default_settings_path_is_in_app_folder():
    path = shell_selection.settings_path()
    assert path.name == "shell-settings.json"
    assert path.parent.name == "Contract Builder"
