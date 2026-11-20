"""Tests for scripts/overlaps.py: shared files between open tasks (T-055)."""
import pytest

from scripts import overlaps


def task(number, status, touches, heading="###"):
    return (
        f"{heading} {number} Invented task\n\n"
        f"- **Status:** {status}\n"
        "- **Size:** S\n"
        "- **Agent:** any\n"
        "- **Needs:** —\n"
        f"- **Touches:** {touches}\n\n"
        "Body text that mentions `not_a_file_here` in prose.\n\n"
    )


def write(tmp_path, *tasks):
    path = tmp_path / "TASKS.md"
    path.write_text("# TASKS\n\n" + "".join(tasks), encoding="utf-8")
    return path


def test_parses_status_and_touches_for_each_task(tmp_path):
    path = write(tmp_path, task("T-901", "open", "`alpha.py`, `beta/gamma.yml`"))
    [parsed] = overlaps.parse_tasks(path.read_text(encoding="utf-8"))
    assert parsed["id"] == "T-901"
    assert overlaps.touched_files(parsed["touches"]) == {"alpha.py", "beta/gamma.yml"}


def test_prose_in_the_body_is_not_a_touched_file(tmp_path):
    path = write(tmp_path, task("T-901", "open", "`alpha.py`"))
    [parsed] = overlaps.parse_tasks(path.read_text(encoding="utf-8"))
    assert "not_a_file_here" not in overlaps.touched_files(parsed["touches"])


def test_none_or_words_touch_no_files():
    assert overlaps.touched_files("none (a hand check)") == set()
    assert overlaps.touched_files("GitHub settings only") == set()


def test_two_open_tasks_sharing_a_file_are_listed_without_failing(tmp_path, capsys):
    path = write(
        tmp_path,
        task("T-901", "open", "`shared.py`"),
        task("T-902", "open", "`shared.py`, `other.py`"),
    )
    assert overlaps.main(["x", str(path)]) == 0
    out = capsys.readouterr().out
    assert "T-901 and T-902 both touch shared.py" in out


def test_two_claimed_tasks_sharing_a_file_fail(tmp_path, capsys):
    path = write(
        tmp_path,
        task("T-901", "claimed (Invented Agent, 2026-12-01)", "`shared.py`"),
        task("T-902", "claimed (Other Agent, 2026-12-01)", "`shared.py`"),
    )
    assert overlaps.main(["x", str(path)]) == 1
    assert "CLAIMED TOGETHER: T-901 and T-902" in capsys.readouterr().out


def test_a_claimed_task_and_an_open_one_only_warn(tmp_path):
    path = write(
        tmp_path,
        task("T-901", "claimed (Invented Agent, 2026-12-01)", "`shared.py`"),
        task("T-902", "open", "`shared.py`"),
    )
    assert overlaps.main(["x", str(path)]) == 0


def test_done_tasks_are_ignored(tmp_path):
    path = write(
        tmp_path,
        task("T-901", "done (2026-12-01, PR #1)", "`shared.py`"),
        task("T-902", "open", "`shared.py`"),
    )
    assert overlaps.find_overlaps(overlaps.parse_tasks(path.read_text(encoding="utf-8"))) == []


def test_umbrella_tasks_are_skipped(tmp_path):
    path = write(
        tmp_path,
        task("T-900", "open (umbrella; work its subtasks)", "`shared.py`", heading="##"),
        task("T-901", "open", "`shared.py`"),
    )
    assert overlaps.find_overlaps(overlaps.parse_tasks(path.read_text(encoding="utf-8"))) == []


def test_tasks_with_disjoint_files_do_not_overlap(tmp_path, capsys):
    path = write(
        tmp_path,
        task("T-901", "claimed (A, 2026-12-01)", "`one.py`"),
        task("T-902", "claimed (B, 2026-12-01)", "`two.py`"),
    )
    assert overlaps.main(["x", str(path)]) == 0
    assert "No open tasks share a file." in capsys.readouterr().out


def test_the_real_task_file_parses_and_every_open_task_has_touches():
    """Guards T-055's 'done when': each open task names its files."""
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "TASKS.md").read_text(encoding="utf-8")
    missing = [
        t["id"] for t in overlaps.parse_tasks(text)
        if overlaps.is_open(t["status"]) and "umbrella" not in t["status"].lower()
        and not t["touches"]
    ]
    assert missing == []
