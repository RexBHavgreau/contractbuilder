"""List open tasks that name the same file in their Touches field (T-055).

Usage: python scripts/overlaps.py [TASKS.md]

Every pair of open tasks that share a file is listed. The script exits with
status 1 only when two *claimed* tasks share a file: those should be done one
after the other, or the file split first. CI runs it as a warning, not a
failure. Umbrella tasks are skipped, because their subtasks are checked
instead.
"""
from __future__ import annotations

import re
import sys
from itertools import combinations
from pathlib import Path

HEADING = re.compile(r"^(#{2,4}) (T-[0-9]+(?:-[A-Z])?)\b")
FIELD = re.compile(r"^- \*\*(\w+):\*\*\s*(.*)$")
OPEN_STATUSES = ("open", "claimed", "blocked", "ready for review")


def parse_tasks(text: str) -> list[dict]:
    """Return one dict per task section with id, status and touched files."""
    tasks: list[dict] = []
    current: dict | None = None
    field = None
    for line in text.split("\n"):
        heading = HEADING.match(line)
        if heading:
            current = {"id": heading.group(2), "status": "", "touches": "", "title": line}
            tasks.append(current)
            field = None
            continue
        if not heading and (line.startswith("## ") or line.startswith("### ")):
            current = None
            field = None
            continue
        if current is None:
            continue
        match = FIELD.match(line)
        if match:
            field = match.group(1).lower()
            if field in ("status", "touches"):
                current[field] = match.group(2)
            else:
                field = None
        elif field in ("status", "touches") and line.startswith("      "):
            current[field] += " " + line.strip()
        else:
            field = None
    return tasks


def touched_files(touches: str) -> set[str]:
    """File names in backticks, e.g. `core.py` or `.github/workflows/build.yml`."""
    names = set()
    for item in re.findall(r"`([^`]+)`", touches):
        if "." in item or "/" in item:
            names.add(item.strip())
    return names


def is_open(status: str) -> bool:
    return status.lower().startswith(OPEN_STATUSES)


def is_claimed(status: str) -> bool:
    return status.lower().startswith("claimed")


def find_overlaps(tasks: list[dict]) -> list[tuple[dict, dict, set[str]]]:
    candidates = [
        task for task in tasks
        if is_open(task["status"]) and "umbrella" not in task["status"].lower()
        and task["touches"]
    ]
    pairs = []
    for first, second in combinations(candidates, 2):
        shared = touched_files(first["touches"]) & touched_files(second["touches"])
        if shared:
            pairs.append((first, second, shared))
    return pairs


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1] / "TASKS.md"
    tasks = parse_tasks(path.read_text(encoding="utf-8"))
    pairs = find_overlaps(tasks)
    if not pairs:
        print("No open tasks share a file.")
        return 0
    failed = False
    for first, second, shared in pairs:
        both_claimed = is_claimed(first["status"]) and is_claimed(second["status"])
        failed = failed or both_claimed
        label = "CLAIMED TOGETHER" if both_claimed else "overlap"
        print(f"{label}: {first['id']} and {second['id']} both touch {', '.join(sorted(shared))}")
    if failed:
        print("Two claimed tasks share a file. Finish one before starting the other, "
              "or split the file first (TASKS.md, T-055).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
