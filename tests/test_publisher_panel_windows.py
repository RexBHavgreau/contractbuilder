"""The publisher panel, details form, parties window and help text under a display (T-046, T-043)."""
import os
import pathlib
import sys
import tkinter as tk
from tkinter import ttk

from docx import Document
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import core  # noqa: E402
import party_dialog  # noqa: E402
import publisher_dialog  # noqa: E402
import publisher_detail_dialog  # noqa: E402
import publisher_panel  # noqa: E402
import simple_app  # noqa: E402
import start_screen  # noqa: E402
from library import ComponentLibrary  # noqa: E402
from publisher_profiles import PublisherProfileStore  # noqa: E402
from ui_widgets import FieldInput  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.name != "nt" and not os.environ.get("DISPLAY"),
    reason="Tk window tests need a display; CI runs window tests under xvfb-run.",
)


def quiet(monkeypatch):
    calls = {"info": [], "error": []}
    for module in (publisher_panel, party_dialog, publisher_dialog, publisher_detail_dialog, start_screen):
        box = module.messagebox
        monkeypatch.setattr(box, "showinfo", lambda *a, _c=calls, **k: _c["info"].append(a))
        monkeypatch.setattr(box, "showerror", lambda *a, _c=calls, **k: _c["error"].append(a))
        monkeypatch.setattr(box, "askyesno", lambda *a, **k: True)
    return calls


@pytest.fixture
def root():
    window = tk.Tk()
    window.geometry("300x100")
    window.update()
    yield window
    window.destroy()


def make_template(tmp_path, names):
    document = Document()
    for name in names:
        document.add_paragraph("{{" + name + "}}")
    path = tmp_path / "t.docx"
    document.save(path)
    return path


def texts(widget):
    found = []
    for child in widget.winfo_children():
        try:
            found.append(str(child.cget("text")))
        except tk.TclError:
            pass
        found.extend(texts(child))
    return found


@pytest.fixture
def panel_setup(root, tmp_path, monkeypatch):
    calls = quiet(monkeypatch)
    store = PublisherProfileStore(tmp_path / "db.sqlite3")
    store.add_detail_definition("Publisher type", ["Non-profit", "Company"])
    store.save_party("Publisher One", "Proprietor")
    store.save_party("Publisher Two")
    one = store.save_profile({"publisher_name": "Alpha Press", "city": "Lyon", "address_line1": "1 Invented Road",
                              "details": {"Publisher type": "Non-profit"}})
    two = store.save_profile({"publisher_name": "Beta Books", "city": "Paris"})
    names = ["Publisher One (Proprietor)", "Publisher One’s City", "Publisher Two’s City",
             "Publisher Two’s Publisher Type", "Fee"]
    template = core.Template(make_template(tmp_path, names))
    frame = ttk.Frame(root)
    frame.pack()
    status = []
    inputs = []
    panel = publisher_panel.PublisherPanel(
        root, frame, store, None, lambda: inputs, lambda text, color: status.append(text),
        lambda: None, "Nothing here matches.",
    )
    panel.refresh_profiles()
    panel.analyze([f.name for f in template.field_list()])
    form = ttk.Frame(root)
    form.pack()
    for row, field in enumerate(template.field_list()):
        inputs.append(FieldInput(form, field, row * 2, on_fill_from_publisher=panel.callback_for(field.name)))
    root.update()
    return panel, inputs, status, calls, (one, two)


def value(inputs, name):
    return next(c for c in inputs if c.field.name == name).get()


def test_one_publisher_choice_appears_for_each_party_in_the_document(panel_setup):
    panel, inputs, status, calls, _ids = panel_setup
    assert list(panel.party_rows) == ["Publisher One", "Publisher Two"]
    assert "Publisher One (Proprietor)" in texts(panel.frame)
    assert any(t.startswith("Fill all for Publisher One") for t in texts(panel.frame))


def test_each_party_fills_from_its_own_publisher(panel_setup):
    panel, inputs, status, calls, _ids = panel_setup
    panel.party_rows["Publisher One"][0].set("Alpha Press")
    panel.party_rows["Publisher Two"][0].set("Beta Books")
    panel.fill("Publisher One")
    panel.fill("Publisher Two")
    assert value(inputs, "Publisher One (Proprietor)") == "Alpha Press"
    assert value(inputs, "Publisher One’s City") == "Lyon"
    assert value(inputs, "Publisher Two’s City") == "Paris"
    assert value(inputs, "Fee") == ""                                # never touched
    assert "Choose these yourself" in status[-1] or "Filled for Publisher Two" in status[-1]


def test_a_publisher_with_no_value_for_a_detail_leaves_it_and_says_why(panel_setup):
    panel, inputs, status, calls, _ids = panel_setup
    panel.party_rows["Publisher Two"][0].set("Beta Books")          # Beta has no Publisher type saved
    panel.fill("Publisher Two")
    assert value(inputs, "Publisher Two’s Publisher Type") == ""
    assert "Publisher Two’s Publisher Type (Publisher type)" in status[-1]
    assert "no value saved" in status[-1]


def test_a_detail_the_publisher_has_is_filled(panel_setup):
    panel, inputs, status, calls, _ids = panel_setup
    # Alpha is Non-profit; ask Publisher Two's detail field to fill from Alpha.
    panel.party_rows["Publisher Two"][0].set("Alpha Press")
    panel.fill("Publisher Two")
    assert value(inputs, "Publisher Two’s Publisher Type") == "Non-profit"


def test_a_single_field_button_fills_just_that_field(panel_setup):
    panel, inputs, status, calls, _ids = panel_setup
    panel.party_rows["Publisher One"][0].set("Alpha Press")
    panel.callback_for("Publisher One’s City")()
    assert value(inputs, "Publisher One’s City") == "Lyon"
    assert value(inputs, "Publisher One (Proprietor)") == ""
    assert panel.callback_for("Fee") is None


def test_filling_without_choosing_a_publisher_asks_for_one(panel_setup):
    panel, inputs, status, calls, _ids = panel_setup
    panel.fill("Publisher One")
    assert calls["info"] and "Choose a saved publisher for Publisher One" in calls["info"][-1][1]


def test_choosing_a_publisher_fills_automatically_when_asked(panel_setup):
    panel, inputs, status, calls, _ids = panel_setup
    panel.auto_fill.set(True)
    panel.party_rows["Publisher One"][0].set("Alpha Press")
    panel.party_rows["Publisher One"][1].event_generate("<<ComboboxSelected>>")
    panel.frame.update()
    assert value(inputs, "Publisher One’s City") == "Lyon"


def test_a_document_without_parties_shows_only_the_one_choice(root, tmp_path, monkeypatch):
    quiet(monkeypatch)
    store = PublisherProfileStore(tmp_path / "db.sqlite3")
    store.save_party("Publisher One")
    frame = ttk.Frame(root)
    frame.pack()
    panel = publisher_panel.PublisherPanel(root, frame, store, None, lambda: [], lambda *a: None, lambda: None, "x")
    panel.analyze(["Publisher Name", "City"])
    assert panel.party_rows == {}


# ---- the profile window, details and parties -----------------------------

def test_the_profile_window_edits_a_detail_with_a_drop_down(root, tmp_path, monkeypatch):
    quiet(monkeypatch)
    store = PublisherProfileStore(tmp_path / "db.sqlite3")
    store.add_detail_definition("Publisher type", ["Non-profit", "Company"])
    dialog = publisher_dialog.PublisherProfileDialog(root, store)
    root.update()
    combo = next(w for w in dialog.details_form.frame.winfo_children() if isinstance(w, ttk.Combobox))
    assert str(combo.cget("state")) == "readonly" and "Company" in combo.cget("values")
    dialog.variables["publisher_name"].set("Gamma House")
    dialog.details_form.variables["Publisher type"].set("Company")
    dialog.save_profile()
    saved = store.get_profile_with_details(store.list_profiles()[0]["id"])
    assert saved["details"] == {"Publisher type": "Company"}
    assert not dialog._has_unsaved_changes()
    dialog.details_form.variables["Publisher type"].set("Non-profit")
    assert dialog._has_unsaved_changes()                              # a detail change counts


def test_adding_a_detail_from_the_profile_window(root, tmp_path, monkeypatch):
    quiet(monkeypatch)
    store = PublisherProfileStore(tmp_path / "db.sqlite3")
    dialog = publisher_dialog.PublisherProfileDialog(root, store)
    assert any("No extra details yet" in t for t in texts(dialog.details_form.frame))
    form = publisher_detail_dialog.PublisherDetailDialog(root, store, lambda: dialog.details_form.rebuild({}))
    form.name.set("Publisher type")
    form.values.insert("1.0", "Non-profit\nSole proprietor\nCompany")
    form.save()
    assert [d["name"] for d in store.list_detail_definitions()] == ["Publisher type"]
    assert "Publisher type" in dialog.details_form.variables


def test_the_parties_window_adds_renames_and_deletes(root, tmp_path, monkeypatch):
    quiet(monkeypatch)
    store = PublisherProfileStore(tmp_path / "db.sqlite3")
    window = party_dialog.PartyDialog(root, store)
    window.name.set("Publisher One")
    window.role.set("Proprietor")
    window.save()
    assert [(p["name"], p["role"]) for p in store.list_parties()] == [("Publisher One", "Proprietor")]
    window.name.set("First Publisher")
    window.save()                                                     # same row renamed
    assert [p["name"] for p in store.list_parties()] == ["First Publisher"]
    window.delete()
    assert store.list_parties() == []


# ---- the two forms ---------------------------------------------------------

def test_the_main_form_shows_party_choices_help_text_and_forgets_them(root, tmp_path, monkeypatch):
    quiet(monkeypatch)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "data"))
    monkeypatch.setattr(simple_app.WordTemplateFiller, "check_for_updates", lambda *a, **k: None)
    monkeypatch.setattr(simple_app.WordTemplateFiller, "_report_failed_update", lambda *a, **k: None)
    app = simple_app.WordTemplateFiller(root)
    store = app.publisher_store
    store.save_party("Publisher One")
    ComponentLibrary(store.path).add_field_definition("Signing Deadline", description="Thirty days after the effective date.")
    app.load_template(make_template(tmp_path, ["Publisher One’s City", "Signing Deadline"]))
    root.update()
    assert list(app.publisher_panel.party_rows) == ["Publisher One"]
    assert "Thirty days after the effective date." in texts(app.scroll.inner)
    app.load_template(make_template(tmp_path, ["City"]))
    root.update()
    assert app.publisher_panel.party_rows == {}                       # no stale party rows
    assert "Thirty days after the effective date." not in texts(app.scroll.inner)


def test_a_field_without_help_looks_as_before_and_help_is_not_in_the_document(root):
    class F:
        def __init__(self, name, kind):
            self.name, self.kind, self.choices = name, kind, []
    frame = ttk.Frame(root)
    plain = FieldInput(frame, F("Name", "text"), 0)
    helped = FieldInput(frame, F("Name", "text"), 2, help_text="Type the full name.")
    yesno = FieldInput(frame, F("Include", "yesno"), 4)
    yesno_help = FieldInput(frame, F("Include", "yesno"), 6, help_text="Tick to include.")
    # T-049-B made a plain field use one row, two when it has help text.
    assert (plain.rows_used, helped.rows_used, yesno.rows_used, yesno_help.rows_used) == (1, 2, 1, 2)
    assert plain.help_label is None and helped.help_label is not None
    assert helped.get() == ""                                         # help is guidance, never a value


def test_the_picker_adds_the_starter_fields_on_request(root, tmp_path, monkeypatch):
    from component_editor import field_picker
    monkeypatch.setattr(field_picker.messagebox, "askyesno", lambda *a, **k: True)
    library = ComponentLibrary(tmp_path / "db.sqlite3")
    dialog = field_picker.FieldPickerDialog(root, library, lambda text: None)
    root.update()
    dialog.add_starter()
    names = {d["name"] for d in library.list_field_definitions()}
    assert {"Works", "Publisher type", "Territory"} <= names
    assert "Added:" in dialog.details.cget("text")
    dialog.add_starter()
    assert "Nothing new to add" in dialog.details.cget("text")
