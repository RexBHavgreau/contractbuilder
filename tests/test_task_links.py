"""The Needed by and Touches links between open tasks (scripts/task_links.py)."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import task_files  # noqa: E402
import task_links  # noqa: E402


def write_task(folder, task_id, status="open", needs="—", touches="`shared.py`", size="S", title="Invented"):
    body = (
        f"# {task_id} {title}\n\n"
        f"- **Status:** {status}\n"
        f"- **Size:** {size}\n"
        "- **Agent:** any\n"
        f"- **Needs:** {needs}\n"
        f"- **Touches:** {touches}\n"
        "- **Size gate:** no executable change\n\n"
        "Free text.\n"
    )
    path = folder / f"{task_id}.md"
    path.write_text(body, encoding="utf-8")
    return path


def load(folder):
    return task_files.load(folder)


def test_the_real_task_files_are_up_to_date():
    assert task_links.main(["x", "--check"]) == 0


def test_a_dependent_is_listed_under_the_task_it_needs(tmp_path):
    write_task(tmp_path, "T-901")
    write_task(tmp_path, "T-902", needs="T-901")
    dependents = task_links.needed_by(load(tmp_path))
    assert dependents["T-901"] == ["T-902"]
    assert dependents["T-902"] == []


def test_only_the_first_two_dependents_are_named(tmp_path):
    write_task(tmp_path, "T-901")
    for number in (902, 903, 904, 905):
        write_task(tmp_path, f"T-{number}", needs="T-901")
    tasks = load(tmp_path)
    names = task_links.needed_by(tasks)["T-901"]
    assert task_links.needed_by_text(names) == "T-902, T-903 (and 2 more)"


def test_only_direct_dependents_are_listed_not_their_dependents(tmp_path):
    write_task(tmp_path, "T-901")
    write_task(tmp_path, "T-902", needs="T-901")
    write_task(tmp_path, "T-903", needs="T-902")
    dependents = task_links.needed_by(load(tmp_path))
    assert dependents["T-901"] == ["T-902"]


def test_done_tasks_are_not_listed(tmp_path):
    write_task(tmp_path, "T-901")
    write_task(tmp_path, "T-902", status="done (2026-11-21, PR #1)", needs="T-901")
    assert task_links.needed_by(load(tmp_path))["T-901"] == []


def test_touches_names_the_other_open_tasks_that_share_a_file(tmp_path):
    first = write_task(tmp_path, "T-901", touches="`shared.py`, `alone.py`")
    write_task(tmp_path, "T-902", touches="`shared.py`")
    write_task(tmp_path, "T-903", touches="`shared.py` (new)")
    changes = dict((task.id, new) for task, new in task_links.planned(load(tmp_path)))
    assert "`shared.py` (also T-902, T-903), `alone.py`" in changes["T-901"]
    assert "`shared.py` (also T-901, T-903)" in changes["T-902"]
    assert "`shared.py` (new) (also T-901, T-902)" in changes["T-903"]


def test_umbrella_tasks_are_left_out_of_the_touch_lists(tmp_path):
    write_task(tmp_path, "T-901", status="open (umbrella; work its subtasks)", size="umbrella", touches="`shared.py`")
    write_task(tmp_path, "T-902", touches="`shared.py`")
    changes = dict((task.id, new) for task, new in task_links.planned(load(tmp_path)))
    assert "(also" not in changes.get("T-902", "")
    assert "(also" not in changes.get("T-901", "")


def test_writing_twice_changes_nothing_the_second_time(tmp_path):
    write_task(tmp_path, "T-901", touches="`shared.py`")
    write_task(tmp_path, "T-902", needs="T-901", touches="`shared.py`")
    for task, new in task_links.planned(load(tmp_path)):
        task.path.write_text(new, encoding="utf-8")
    assert task_links.planned(load(tmp_path)) == []


def test_a_file_that_no_longer_shares_a_task_loses_its_also(tmp_path):
    write_task(tmp_path, "T-901", touches="`shared.py` (also T-999)")
    for task, new in task_links.planned(load(tmp_path)):
        task.path.write_text(new, encoding="utf-8")
    text = (tmp_path / "T-901.md").read_text(encoding="utf-8")
    assert "(also T-999)" not in text
    assert "- **Touches:** `shared.py`" in text


def test_needed_by_sits_under_needs_and_is_written_once(tmp_path):
    write_task(tmp_path, "T-901")
    write_task(tmp_path, "T-902", needs="T-901")
    for task, new in task_links.planned(load(tmp_path)):
        task.path.write_text(new, encoding="utf-8")
    lines = (tmp_path / "T-901.md").read_text(encoding="utf-8").split("\n")
    assert lines.count("- **Needed by:** T-902") == 1
    assert lines.index("- **Needed by:** T-902") == lines.index("- **Needs:** —") + 1
