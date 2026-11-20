"""Progress and decision entries are one file each with a complete header (T-053)."""

import pytest

from scripts import project_log
from scripts.show_log import main as show_log


@pytest.mark.parametrize("kind", sorted(project_log.FOLDERS))
def test_every_entry_in_the_repository_is_well_formed(kind):
    entries = project_log.load(kind)
    assert entries, f"no {kind} entries found"
    found = [p for entry in entries for p in project_log.problems(entry, kind)]
    assert not found, "\n".join(found)


def write(folder, name, header, body="- **2026-12-01** Invented entry."):
    lines = ["---"] + [f"{k}: {v}" for k, v in header.items()] + ["---", "", body, ""]
    path = folder / name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


FULL = {
    "date": "2026-12-01",
    "task": "T-900",
    "author": "Test Agent",
    "pull_request": "https://example.invalid/pull/1",
    "ci_run": "1",
    "size": "no executable change",
}


def test_a_complete_progress_entry_passes(tmp_path):
    entry = project_log.parse(write(tmp_path, "2026-12-01-T-900-invented-work.md", FULL))
    assert project_log.problems(entry, "progress") == []


@pytest.mark.parametrize("missing", ["task", "pull_request", "ci_run", "size"])
def test_a_progress_entry_without_a_required_field_fails(tmp_path, missing):
    header = {k: v for k, v in FULL.items() if k != missing}
    entry = project_log.parse(write(tmp_path, "2026-12-01-T-900-invented-work.md", header))
    assert any(missing in p for p in project_log.problems(entry, "progress"))


def test_an_empty_size_field_fails(tmp_path):
    entry = project_log.parse(
        write(tmp_path, "2026-12-01-T-900-invented-work.md", dict(FULL, size=""))
    )
    assert any("size" in p for p in project_log.problems(entry, "progress"))


def test_not_recorded_is_only_for_moved_entries(tmp_path):
    header = dict(FULL, ci_run="not recorded")
    entry = project_log.parse(write(tmp_path, "2026-12-01-T-900-new.md", header))
    assert any("ci_run" in p for p in project_log.problems(entry, "progress"))
    moved = dict(header, source=project_log.MIGRATED_SOURCE, sequence="1")
    entry = project_log.parse(write(tmp_path, "2026-12-01-T-900-moved.md", moved))
    assert project_log.problems(entry, "progress") == []


def test_decisions_need_no_ci_run_or_size(tmp_path):
    header = {k: FULL[k] for k in ("date", "task", "author", "pull_request")}
    entry = project_log.parse(write(tmp_path, "2026-12-01-T-900-a-choice.md", header))
    assert project_log.problems(entry, "decisions") == []


@pytest.mark.parametrize(
    "name",
    ["Invented Work.md", "2026-12-01_T-900.md", "2026-12-02-T-900-wrong-date.md", "notes.md"],
)
def test_badly_named_files_fail(tmp_path, name):
    entry = project_log.parse(write(tmp_path, name, FULL))
    assert project_log.problems(entry, "progress")


def test_a_file_without_a_header_fails(tmp_path):
    path = tmp_path / "2026-12-01-T-900-no-header.md"
    path.write_text("Just text.\n", encoding="utf-8")
    assert project_log.problems(project_log.parse(path), "progress")


def test_entries_sort_by_date_then_moved_order_then_name(tmp_path):
    write(tmp_path, "2026-12-02-T-900-b.md", FULL, "second day")
    write(tmp_path, "2026-12-01-T-900-z.md", dict(FULL, sequence="1"), "moved first")
    write(tmp_path, "2026-12-01-T-900-a.md", dict(FULL, sequence="2"), "moved second")
    write(tmp_path, "2026-12-01-T-900-new.md", FULL, "added later the same day")
    (tmp_path / "README.md").write_text("not an entry", encoding="utf-8")
    entries = project_log.load("progress", tmp_path)
    assert [e.body for e in entries] == [
        "moved first",
        "moved second",
        "added later the same day",
        "second day",
    ]
    assert project_log.render(entries).startswith("moved first\n\nmoved second\n\n")


def test_show_log_prints_entries_and_checks(capsys):
    assert show_log(["decisions", "--task", "T-025"]) == 0
    assert "clause numbering" in capsys.readouterr().out
    assert show_log(["progress", "--check"]) == 0
    assert "0 problems" in capsys.readouterr().out
