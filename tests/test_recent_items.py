"""Recently used files and assemblies, kept in the per-user settings file (T-048-C)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import recent_items  # noqa: E402


def t(name):
    return {"kind": recent_items.TEMPLATE, "key": f"/invented/{name}.docx", "label": f"{name}.docx"}


def a(number):
    return {"kind": recent_items.ASSEMBLY, "key": str(number), "label": f"Assembly {number}"}


def test_newest_item_comes_first_and_an_item_is_listed_once(tmp_path):
    path = tmp_path / "settings.json"
    recent_items.record(path, t("one"))
    recent_items.record(path, t("two"))
    recent_items.record(path, t("one"))
    assert [item["label"] for item in recent_items.load(path)] == ["one.docx", "two.docx"]


def test_only_the_most_recent_items_are_kept(tmp_path):
    path = tmp_path / "settings.json"
    for number in range(1, recent_items.RECENT_LIMIT + 3):
        recent_items.record(path, a(number))
    kept = recent_items.load(path)
    assert len(kept) == recent_items.RECENT_LIMIT
    assert kept[0]["key"] == str(recent_items.RECENT_LIMIT + 2)


def test_the_saved_update_token_survives_recording_and_removing(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"github_token": "invented-token-value", "last_check": 5}), encoding="utf-8")
    recent_items.record(path, t("one"))
    recent_items.remove(path, t("one"))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["github_token"] == "invented-token-value"
    assert data["last_check"] == 5
    assert data["recent"] == []


def test_damaged_or_odd_settings_mean_an_empty_list(tmp_path):
    path = tmp_path / "settings.json"
    for text in ("not json", "[1, 2]", json.dumps({"recent": "nope"}), json.dumps({"recent": [{"kind": "other", "key": "x"}]})):
        path.write_text(text, encoding="utf-8")
        assert recent_items.load(path) == []


def test_a_missing_settings_file_is_not_an_error(tmp_path):
    assert recent_items.load(tmp_path / "absent.json") == []


def test_saving_fails_quietly_when_the_folder_is_blocked(tmp_path):
    blocker = tmp_path / "file-in-the-way"
    blocker.write_text("x", encoding="utf-8")
    assert recent_items.record(blocker / "settings.json", t("one")) is False


def test_template_status_shows_a_missing_file(tmp_path):
    present = tmp_path / "present.docx"
    present.write_bytes(b"not really a document, only checked for existence")
    assert recent_items.template_status({"kind": "template", "key": str(present)}) == "ok"
    assert recent_items.template_status({"kind": "template", "key": str(tmp_path / "gone.docx")}) == "missing"


def test_assembly_status_follows_the_saved_revisions():
    assert recent_items.assembly_status(a(3), lambda item_id: item_id == 3) == "ok"
    assert recent_items.assembly_status(a(4), lambda item_id: item_id == 3) == "missing"
    assert recent_items.assembly_status({"kind": "assembly", "key": "x"}, lambda _i: True) == "missing"


def test_recording_does_not_change_the_saved_file_when_the_list_is_unchanged(tmp_path):
    path = tmp_path / "settings.json"
    recent_items.record(path, t("one"))
    before = path.read_text(encoding="utf-8")
    recent_items.record(path, t("one"))
    assert path.read_text(encoding="utf-8") == before
