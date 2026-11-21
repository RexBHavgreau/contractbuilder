"""The task files and the generated board (T-054)."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import board  # noqa: E402
import task_files  # noqa: E402


def write(folder, name, body):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(body, encoding="utf-8")
    return path


def task(tid, title, status="open", size="S", agent="any", needs="none", extra=""):
    return (
        f"# {tid} {title}\n\n- **Status:** {status}\n- **Size:** {size}\n"
        f"- **Agent:** {agent}\n- **Needs:** {needs}\n{extra}\nText.\n"
    )


def test_every_task_file_in_the_repository_is_well_formed():
    found = task_files.problems(task_files.load())
    assert not found, "\n".join(found)


def test_a_header_is_read_with_multi_line_values(tmp_path):
    path = write(
        tmp_path,
        "T-901.md",
        "# T-901 Invented work\n\n- **Status:** claimed (Agent A,\n  2026-12-01)\n"
        "- **Size:** M\n- **Agent:** careful\n- **Needs:** T-900\n"
        "- **Touches:** library.py, tests\n\nFree text, not a field.\n",
    )
    parsed = task_files.parse(path)
    assert parsed.id == "T-901" and parsed.title == "Invented work"
    assert parsed.status == "claimed (Agent A, 2026-12-01)"
    assert parsed.get("touches") == "library.py, tests"
    assert parsed.state == "in progress"
    assert task_files.problems([parsed]) == []


def test_a_note_above_the_bullets_is_allowed(tmp_path):
    path = write(
        tmp_path / "done",
        "T-902.md",
        "# T-902 Finished work\n\n*Note.*\n\n- **Status:** done (2026-12-01)\n\nText.\n",
    )
    parsed = task_files.parse(path)
    assert parsed.state == "done"
    assert task_files.problems([parsed]) == []  # a finished task needs only a status


def test_the_board_lists_open_work_under_its_umbrella_and_skips_done(tmp_path):
    write(tmp_path, "T-910.md", task("T-910", "An umbrella", size="umbrella"))
    write(tmp_path, "T-910-A.md", task("T-910-A", "First part", status="claimed (A, 2026-12-01)"))
    write(tmp_path, "T-910-B.md", task("T-910-B", "Second part"))
    write(tmp_path / "done", "T-910-C.md", task("T-910-C", "Third part", status="done (2026-12-01)"))
    write(tmp_path, "T-911.md", task("T-911", "Standalone", status="waiting (on someone)"))
    table = task_files.build_board(task_files.load(tmp_path))
    lines = table.splitlines()
    ids = [l.split("|")[1].strip() for l in lines[2:]]
    assert ids == ["[T-910](tasks/T-910.md)", "↳ [T-910-A](tasks/T-910-A.md)",
                   "↳ [T-910-B](tasks/T-910-B.md)", "[T-911](tasks/T-911.md)"]
    assert "T-910-C" not in table


def test_work_under_way_sorts_before_open_work(tmp_path):
    write(tmp_path, "T-920.md", task("T-920", "Open one"))
    write(tmp_path, "T-921.md", task("T-921", "Claimed one", status="claimed (A, 2026-12-01)"))
    write(tmp_path, "T-922.md", task("T-922", "In review", status="in review (PR 1)"))
    rows = task_files.build_board(task_files.load(tmp_path)).splitlines()[2:]
    assert [r.split("|")[1].strip()[1:6] for r in rows] == ["T-921", "T-922", "T-920"]


def test_a_subtask_of_a_finished_umbrella_still_shows(tmp_path):
    write(tmp_path / "done", "T-930.md", task("T-930", "Done umbrella", status="done (2026-12-01)"))
    write(tmp_path, "T-930-A.md", task("T-930-A", "Left over part"))
    table = task_files.build_board(task_files.load(tmp_path))
    assert "T-930-A" in table and "Done umbrella" not in table


def test_problems_are_reported_in_plain_english(tmp_path):
    write(tmp_path, "T-940.md", task("T-940", "Wrong place", status="done (2026-12-01)"))
    write(tmp_path / "done", "T-941.md", task("T-941", "Not done yet"))
    write(tmp_path, "T-942.md", task("T-943", "Name does not match"))
    write(tmp_path, "T-944.md", "# T-944 No fields\n\nJust text.\n")
    write(tmp_path, "notes.md", "# Not a task\n")
    found = "\n".join(task_files.problems(task_files.load(tmp_path)))
    assert "T-940.md: its status says done, so move it to tasks/done/" in found
    assert "T-941.md: it is in tasks/done/ but its status does not say done" in found
    assert "T-942.md: the file name must be T-943.md" in found
    assert "T-944.md: the bullet '- **Status:**" in found
    assert "notes.md" not in found  # only T-*.md files are tasks


def test_a_duplicate_task_number_is_reported(tmp_path):
    write(tmp_path, "T-950.md", task("T-950", "One"))
    write(tmp_path / "done", "T-950.md", task("T-950", "Two", status="done (2026-12-01)"))
    assert any("also in" in p for p in task_files.problems(task_files.load(tmp_path)))


def test_next_free_number_is_one_past_the_highest(tmp_path, monkeypatch):
    write(tmp_path, "T-007.md", task("T-007", "A"))
    write(tmp_path / "done", "T-012-A.md", task("T-012-A", "B", status="done (2026-12-01)"))
    assert board.next_free(task_files.load(tmp_path)) == "T-013"


def test_the_board_cells_escape_table_bars(tmp_path):
    write(tmp_path, "T-960.md", task("T-960", "Pipes | in a title", needs="a | b"))
    row = task_files.build_board(task_files.load(tmp_path)).splitlines()[2]
    assert "Pipes \\| in a title" in row and "a \\| b" in row


# ---- user checks (UT-) ---------------------------------------------------

def ut(tid, title, status="open", checks="T-910"):
    return (
        f"# {tid} {title}\n\n- **Status:** {status}\n- **Size:** S\n- **Agent:** human\n"
        f"- **Needs:** none\n- **Checks:** {checks}\n\nText.\n"
    )


def test_user_checks_are_listed_apart_from_coding_tasks(tmp_path):
    write(tmp_path, "T-910.md", task("T-910", "Coding work"))
    write(tmp_path, "UT-001.md", ut("UT-001", "Try it on Windows"))
    write(tmp_path / "done", "UT-002.md", "# UT-002 Old check\n\n- **Status:** done (2026-12-01)\n")
    tasks = task_files.load(tmp_path)
    assert {t.id for t in tasks} == {"T-910", "UT-001", "UT-002"}
    board_text = task_files.build_board(tasks)
    assert "T-910" in board_text and "UT-001" not in board_text
    checks = task_files.build_user_checks(tasks)
    assert "UT-001" in checks and "T-910" in checks and "UT-002" not in checks
    assert task_files.problems(tasks) == []


def test_numbers_for_user_checks_are_counted_apart(tmp_path):
    write(tmp_path, "T-910.md", task("T-910", "Coding work"))
    write(tmp_path, "UT-004.md", ut("UT-004", "A check"))
    tasks = task_files.load(tmp_path)
    assert board.next_free(tasks) == "T-911"
    assert board.next_free(tasks, "UT") == "UT-005"


def test_a_coding_task_may_not_wait_for_a_user_check(tmp_path):
    write(tmp_path, "UT-001.md", ut("UT-001", "A check"))
    write(tmp_path, "T-920.md", task("T-920", "Waits", needs="UT-001"))
    found = task_files.problems(task_files.load(tmp_path))
    assert len(found) == 1
    assert "UT-001" in found[0] and "must not wait" in found[0] and "[blocks]" in found[0]


def test_the_rare_real_dependency_is_allowed_when_marked(tmp_path):
    write(tmp_path, "UT-001.md", ut("UT-001", "A check"))
    write(tmp_path, "T-920.md", task("T-920", "Waits", needs="T-900, UT-001 [blocks]"))
    assert task_files.problems(task_files.load(tmp_path)) == []


def test_a_user_check_may_name_what_it_needs(tmp_path):
    write(tmp_path, "UT-001.md", ut("UT-001", "A check").replace("none", "UT-002"))
    assert task_files.problems(task_files.load(tmp_path)) == []
