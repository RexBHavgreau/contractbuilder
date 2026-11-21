"""Keep the links between open coding tasks up to date (T-056 workflow).

Two things are written into each open coding task file (not done, not a UT check):

- ``**Needed by:**`` the open tasks that name this task in their Needs. Only
  the immediate dependents are listed (one level), the first two by ID, then
  "(and N more)". So a task needed by 3, 4, 5 and 6 shows ``T-003, T-004 (and 2 more)``.
- ``**Touches:**`` each file this task changes, followed by "(also …)" listing
  the other open tasks that touch the same file. Umbrella tasks are left out
  of these lists, because their Touches is the union of their subtasks.

    python scripts/task_links.py --write   # update the files
    python scripts/task_links.py --check   # exit 1 if any file is out of date
    python scripts/task_links.py           # print the links

The tests run ``--check``, so a task file that is out of date fails CI until
``--write`` is run.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import task_files  # noqa: E402

DEP = re.compile(r"T-\d{3}(?:-[A-Z](?:-\d+)?)?")
MAX_NAMED = 2
ALSO = re.compile(r"\s*\(also [^)]*\)")
ITEM = re.compile(r"`([^`]+)`((?:\s*\([^)]*\))?)")


def open_coding_tasks(tasks):
    return [
        t for t in tasks
        if t.id and t.state != "done" and not t.is_user_check
    ]


def is_umbrella(task) -> bool:
    return "umbrella" in task.status.lower()


def needs_of(task) -> set[str]:
    return set(DEP.findall(task.get("needs")))


def needed_by(tasks) -> dict[str, list[str]]:
    """For each open task id, the open tasks whose Needs name it directly."""
    open_tasks = open_coding_tasks(tasks)
    result: dict[str, list[str]] = {t.id: [] for t in open_tasks}
    for dependent in open_tasks:
        for dependency in needs_of(dependent):
            if dependency in result and dependency != dependent.id:
                result[dependency].append(dependent.id)
    return {key: sorted(set(value)) for key, value in result.items()}


def needed_by_text(names: list[str]) -> str:
    if not names:
        return "none"
    shown = ", ".join(names[:MAX_NAMED])
    if len(names) > MAX_NAMED:
        shown += f" (and {len(names) - MAX_NAMED} more)"
    return shown


def files_of(value: str) -> list[str]:
    """Files named in backticks in a Touches value, in order, without duplicates."""
    seen: list[str] = []
    for name, _rest in ITEM.findall(value):
        if ("." in name or "/" in name) and name not in seen:
            seen.append(name)
    return seen


def touched_by(tasks) -> dict[str, set[str]]:
    """{file: ids of open, non-umbrella tasks that touch it}."""
    index: dict[str, set[str]] = {}
    for task in open_coding_tasks(tasks):
        if is_umbrella(task):
            continue
        for name in files_of(task.get("touches")):
            index.setdefault(name, set()).add(task.id)
    return index


def touches_text(task, index) -> str:
    value = ALSO.sub("", task.get("touches"))
    if is_umbrella(task):
        return value

    def annotate(match):
        name, rest = match.group(1), match.group(2)
        others = sorted(index.get(name, set()) - {task.id})
        if not others or ("." not in name and "/" not in name):
            return match.group(0)
        return f"`{name}`{rest} (also {', '.join(others)})"

    return ITEM.sub(annotate, value)


def rewrite(task, needed: str, touches: str) -> str:
    """The file text with its Needed by and Touches lines set.

    The bullets are the run of ``- **Field:**`` lines after the heading (a
    blank line may come between). Only that run is edited.
    """
    lines = task.path.read_text(encoding="utf-8").split("\n")
    first = next((i for i in range(1, len(lines)) if lines[i].startswith("- **")), None)
    if first is None:
        raise ValueError(f"{task.path.name} has no bullets under its heading")
    last = first
    while last < len(lines) and lines[last].strip():
        last += 1
    block = [line for line in lines[first:last] if not line.startswith("- **Needed by:**")]
    needs_at = next((i for i, line in enumerate(block) if line.startswith("- **Needs:**")), None)
    if needs_at is None:
        raise ValueError(f"{task.path.name} has no Needs line to place Needed by under")
    block.insert(needs_at + 1, f"- **Needed by:** {needed}")
    touches_at = next((i for i, line in enumerate(block) if line.startswith("- **Touches:**")), None)
    if touches_at is None:
        raise ValueError(f"{task.path.name} has no Touches line")
    stop = touches_at + 1
    while stop < len(block) and block[stop].startswith("      "):
        stop += 1
    block[touches_at:stop] = [f"- **Touches:** {touches}"]
    return "\n".join(lines[:first] + block + lines[last:])


def planned(tasks):
    """[(task, new text)] for each open coding task whose file would change."""
    dependents = needed_by(tasks)
    index = touched_by(tasks)
    changes = []
    for task in open_coding_tasks(tasks):
        if not task.get("touches") or not task.get("needs"):
            continue  # a waiting task with no files to link (for example T-018)
        new = rewrite(task, needed_by_text(dependents.get(task.id, [])), touches_text(task, index))
        if new != task.path.read_text(encoding="utf-8"):
            changes.append((task, new))
    return changes


def print_links(tasks):
    dependents = needed_by(tasks)
    index = touched_by(tasks)
    for task in sorted(open_coding_tasks(tasks), key=lambda t: t.id):
        print(f"{task.id}")
        print(f"  needed by: {needed_by_text(dependents.get(task.id, []))}")
        for name in files_of(task.get("touches")):
            others = sorted(index.get(name, set()) - {task.id})
            if others and not is_umbrella(task):
                print(f"  {name}: also {', '.join(others)}")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    tasks = task_files.load()
    if "--write" in argv:
        changes = planned(tasks)
        for task, new in changes:
            task.path.write_text(new, encoding="utf-8")
        print(f"Updated {len(changes)} task file(s).")
        return 0
    if "--check" in argv:
        stale = [task.path.name for task, _new in planned(tasks)]
        if stale:
            print("Out of date (run python scripts/task_links.py --write):")
            for name in stale:
                print(f"  {name}")
            return 1
        print("Task links are up to date.")
        return 0
    print_links(tasks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
