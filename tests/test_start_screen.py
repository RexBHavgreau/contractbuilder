"""The "Build contract from" row of the main window (T-048-A)."""
import os
import sys
import tkinter as tk
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import simple_app  # noqa: E402
import start_screen  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk window tests need a display; CI runs window tests under xvfb-run.",
)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(start_screen.messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(simple_app.WordTemplateFiller, "check_for_updates", lambda *a, **k: None)
    monkeypatch.setattr(simple_app.WordTemplateFiller, "_report_failed_update", lambda *a, **k: None)
    root = tk.Tk()
    root.update()
    window = simple_app.WordTemplateFiller(root)
    root.update()
    yield window
    for child in root.winfo_children():
        try:
            child.destroy()
        except tk.TclError:
            pass
    root.destroy()


def _texts(widget):
    found = []
    for child in widget.winfo_children():
        try:
            found.append(child.cget("text"))
        except tk.TclError:
            pass
        found.extend(_texts(child))
    return found


def test_the_three_choices_are_shown_with_a_line_each(app):
    texts = _texts(app.root)
    assert "Build contract from:" in texts
    for label, caption, _method, _key in start_screen.CHOICES:
        assert label in texts and caption in texts
    assert [b.cget("text") for b in app.start_buttons] == [c[0] for c in start_screen.CHOICES]
    assert "Browse…" not in texts


def test_word_file_button_runs_the_file_dialog(app, monkeypatch):
    seen = {}
    monkeypatch.setattr(
        simple_app.filedialog, "askopenfilename", lambda **k: seen.update(k) or ""
    )
    app.start_buttons[2].invoke()
    assert ("Word documents and templates", "*.docx *.dotx") in seen["filetypes"]


def test_new_assembly_opens_the_builder_once(app):
    app.start_buttons[1].invoke()
    app.root.update()
    first = app.assembly_builder_window
    assert first is not None and first.window.winfo_exists()
    app.start_buttons[1].invoke()
    assert app.assembly_builder_window is first


def test_existing_assembly_opens_the_saved_list(app, monkeypatch):
    # The saved list is a modal window that waits for the user, so the test
    # replaces the opener itself (T-048-B opens the list directly).
    import assembly_open_dialog

    calls = []
    monkeypatch.setattr(
        assembly_open_dialog, "open_saved_assembly_direct", lambda _app: calls.append(1)
    )
    app.start_buttons[0].invoke()
    app.root.update()
    assert calls == [1]
    app.start_buttons[0].invoke()
    assert calls == [1, 1]


def test_access_keys_press_the_buttons(app, monkeypatch):
    seen = []
    monkeypatch.setattr(
        simple_app.filedialog, "askopenfilename", lambda **k: seen.append(1) or ""
    )
    app.root.update()
    app.root.event_generate("<Alt-w>")
    app.root.update()
    assert seen == [1]
    assert [b.cget("underline") for b in app.start_buttons] == [0, 0, 0]


def test_loading_a_word_file_names_it(app, tmp_path):
    from docx import Document

    path = tmp_path / "Invented Letter.docx"
    document = Document()
    document.add_paragraph("Dear {{Recipient Name}},")
    document.save(path)
    app.load_template(path)
    assert app.template_name.cget("text") == "Invented Letter.docx"


def test_builder_shows_name_box_and_layout_button(app):
    app.start_buttons[1].invoke()
    app.root.update()
    window = app.assembly_builder_window.window
    window.update()
    texts = _texts(window)
    assert "Choose page layout file…" in texts and "Assembly name" in texts

    def visible(widget):
        return widget.winfo_ismapped() and widget.winfo_height() > 5

    entry = app.assembly_builder_window.name_entry
    assert visible(entry)
    # Even in a short window the name box must not be squeezed away.
    window.geometry("1000x640")
    window.update()
    assert visible(entry)


def test_buttons_stay_visible_when_the_status_message_is_very_long(app):
    app.start_buttons[1].invoke()
    app.root.update()
    builder = app.assembly_builder_window
    window = builder.window
    window.geometry("900x640")
    builder.status.configure(text="Warning: this layout file has a problem. " * 40)
    window.update()
    window_right = window.winfo_rootx() + window.winfo_width()
    for button in (builder.generate_button, builder.updates_button):
        assert button.winfo_ismapped()
        assert button.winfo_rootx() + button.winfo_width() <= window_right
    texts = _texts(window)
    assert "Save assembly…" in texts and "Close" in texts

    def find(widget, label):
        for child in widget.winfo_children():
            try:
                if child.cget("text") == label:
                    return child
            except tk.TclError:
                pass
            found = find(child, label)
            if found is not None:
                return found

    save = find(window, "Save assembly…")
    assert save.winfo_rootx() + save.winfo_width() <= window_right


def test_recent_list_shows_a_missing_file_and_lets_it_be_removed(app, tmp_path):
    from recent_items import TEMPLATE, record

    gone = str(tmp_path / "Invented Gone.docx")
    record(app._recent_settings_path(), {"kind": TEMPLATE, "key": gone, "label": "Invented Gone.docx"})
    app.refresh_recent_list()
    texts = _texts(app.recent_frame)
    assert any("file not found" in text for text in texts)
    remove = [b for b in _buttons(app.recent_frame) if b.cget("text") == "Remove from list"]
    assert len(remove) == 1
    remove[0].invoke()
    assert not any("file not found" in text for text in _texts(app.recent_frame))


def test_recent_word_file_reopens_in_one_click(app, tmp_path):
    from docx import Document
    from recent_items import TEMPLATE, record

    path = tmp_path / "Invented Recent.docx"
    Document().save(path)
    record(app._recent_settings_path(), {"kind": TEMPLATE, "key": str(path), "label": "Invented Recent.docx"})
    app.refresh_recent_list()
    button = [b for b in _buttons(app.recent_frame) if b.cget("text") == "Word file: Invented Recent.docx"]
    assert len(button) == 1
    button[0].invoke()
    assert app.template_name.cget("text") == "Invented Recent.docx"


def _buttons(widget):
    found = []
    for child in widget.winfo_children():
        if child.winfo_class() == "TButton":
            found.append(child)
        found.extend(_buttons(child))
    return found
