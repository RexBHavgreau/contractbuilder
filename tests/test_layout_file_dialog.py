"""Choosing a page layout file: calm notes, a plain two-button question (T-060-B)."""
import os
import pathlib
import sys
import tkinter as tk

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assembly_builder  # noqa: E402
import layout_file_dialog  # noqa: E402
from assembly_builder import NO_SHELL, AssemblyBuilderWindow  # noqa: E402
from library import ComponentLibrary  # noqa: E402
from test_shell_check import _remove_style, _rewrite_member, make_shell  # noqa: E402
from test_shell_selection import _remove_page_settings  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk window tests need a display; CI runs window tests under xvfb-run.",
)


@pytest.fixture
def root():
    window = tk.Tk()
    window.geometry("200x100")
    window.update()
    yield window
    window.destroy()


def _press(root, label, event=None):
    """Find the dialog's button by its text and invoke it (or send a key)."""
    def find(widget):
        for child in widget.winfo_children():
            try:
                if child.cget("text") == label:
                    return child
            except tk.TclError:
                pass
            found = find(child)
            if found is not None:
                return found
    dialog = [c for c in root.winfo_children() if isinstance(c, tk.Toplevel)][-1]
    if event:
        dialog.focus_force()
        dialog.update()
        dialog.event_generate(event)
    else:
        find(dialog).invoke()


def test_dialog_has_two_plain_buttons_and_returns_the_choice(root):
    root.after(100, lambda: _press(root, "Use this file"))
    assert layout_file_dialog.confirm_layout_file(root, ["Read this."]) is True
    root.after(100, lambda: _press(root, "Choose another"))
    assert layout_file_dialog.confirm_layout_file(root, ["Read this."]) is False


def test_escape_means_choose_another(root):
    root.after(100, lambda: _press(root, "", event="<Escape>"))
    # Safety net so a missed key cannot hang the run: close like the title-bar X.
    root.after(3000, lambda: [c.destroy() for c in root.winfo_children() if isinstance(c, tk.Toplevel)])
    assert layout_file_dialog.confirm_layout_file(root, ["Read this."]) is False


@pytest.fixture
def builder(root, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "data"))
    monkeypatch.setattr(assembly_builder.messagebox, "showerror", lambda *a, **k: None)
    window = AssemblyBuilderWindow(root, ComponentLibrary(tmp_path / "db.sqlite3"))
    root.update()
    return window


def _choose(builder, monkeypatch, path):
    monkeypatch.setattr(
        assembly_builder.filedialog, "askopenfilename", lambda **k: str(path)
    )
    builder.choose_shell()


def test_a_file_that_only_lacks_styles_is_taken_without_a_question(
    builder, tmp_path, monkeypatch
):
    shell = make_shell(tmp_path / "layout.docx")
    _rewrite_member(shell, "word/styles.xml", _remove_style("ListNumber"))
    monkeypatch.setattr(
        assembly_builder, "confirm_layout_file",
        lambda *a, **k: pytest.fail("no question should be asked"),
    )
    _choose(builder, monkeypatch, shell)
    assert builder.shell_variable.get() == str(shell)
    status = builder.status.cget("text")
    assert "missing the List Number style" in status
    assert "will add it to your new document" in status
    assert "Your file is not changed" in status


def test_a_file_with_a_real_warning_asks_and_respects_the_answer(
    builder, tmp_path, monkeypatch
):
    shell = make_shell(tmp_path / "layout.docx")
    _rewrite_member(shell, "word/document.xml", _remove_page_settings("pgSz"))
    asked = []
    monkeypatch.setattr(
        assembly_builder, "confirm_layout_file",
        lambda parent, lines: asked.append(lines) or False,
    )
    _choose(builder, monkeypatch, shell)
    assert len(asked) == 1 and "page size" in " ".join(asked[0])
    assert builder.shell_variable.get() == NO_SHELL

    monkeypatch.setattr(assembly_builder, "confirm_layout_file", lambda *a, **k: True)
    _choose(builder, monkeypatch, shell)
    assert builder.shell_variable.get() == str(shell)
