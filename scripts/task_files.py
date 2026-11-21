"""Read the task files under tasks/ (T-054).

Each task or subtask is one Markdown file, ``tasks/T-043.md`` or
``tasks/T-043-A.md``. Finished tasks live in ``tasks/done/``. A file starts
with a heading ``# T-043-A Title`` and a block of bullets directly below it::

    - **Status:** open
    - **Size:** M
    - **Agent:** careful
    - **Needs:** T-043-A
    - **Touches:** library.py, publisher_profiles.py
    - **Size gate:** yes

A value may continue on the following lines. Everything after the first blank
line is free text. Nothing in a file is generated, so claiming or finishing a
task edits only that task's own file, and the board is built from the files by
``scripts/board.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parent.parent / "tasks"

ID = re.compile(r"^T-\d{3}(?:-[A-Z](?:-\d+)?)?$")
HEADING = re.compile(r"^# (T-\d{3}(?:-[A-Z](?:-\d+)?)?)\b\s*(.*)$")
FIELD_LINE = re.compile(r"^- \*\*([A-Za-z ]+):\*\*\s*(.*)$")

REQUIRED = ("status", "size", "agent", "needs")
KNOWN = REQUIRED + ("touches", "size gate")

# Order on the board: work under way first, then work waiting to be taken.
STATE_ORDER = ("in progress", "open", "blocked", "waiting", "other")


@dataclass
class Task:
    path: Path
    id: str = ""
    title: str = ""
    fields: dict = field(default_factory=dict)
    in_done_folder: bool = False
    problems: list = field(default_factory=list)

    @property
    def status(self) -> str:
        return self.fields.get("status", "")

    @property
    def state(self) -> str:
        return state_of(self.status)

    @property
    def umbrella(self) -> str:
        """The task this one is a subtask of, or ''."""
        parts = self.id.split("-")
        return "-".join(parts[:2]) if len(parts) > 2 else ""

    def get(self, name: str, default: str = "") -> str:
        return self.fields.get(name, default)


def state_of(status: str) -> str:
    """A small set of states from the free-text status, by its first words."""
    s = status.strip().lower()
    if s.startswith("done"):
        return "done"
    if s.startswith(("claimed", "in review", "in progress", "merged but not done")):
        return "in progress"
    if s.startswith("open"):
        return "open"
    if s.startswith("blocked"):
        return "blocked"
    if s.startswith("waiting"):
        return "waiting"
    return "other"


def parse(path: Path) -> Task:
    path = Path(path)
    task = Task(path=path, in_done_folder=path.parent.name == "done")
    lines = path.read_text(encoding="utf-8").split("\n")
    match = HEADING.match(lines[0]) if lines else None
    if not match:
        task.problems.append(
            f"{path.name}: the first line must be '# T-NNN title' (for a subtask '# T-NNN-X title')"
        )
        return task
    task.id, task.title = match.group(1), match.group(2).strip()
    i = 1
    # The bullets normally follow the heading directly; a short note above them
    # (as in a few finished tasks) is allowed. Stop at the next heading.
    while i < len(lines) and not FIELD_LINE.match(lines[i]) and not lines[i].startswith("#"):
        i += 1
    current = None
    while i < len(lines) and lines[i].strip():
        m = FIELD_LINE.match(lines[i])
        if m:
            current = m.group(1).strip().lower()
            task.fields[current] = m.group(2).strip()
        elif current is not None:
            task.fields[current] = (task.fields[current] + " " + lines[i].strip()).strip()
        i += 1
    return task


def load(folder: Path | None = None) -> list:
    folder = Path(folder) if folder else TASK_DIR
    paths = sorted(folder.glob("T-*.md")) + sorted((folder / "done").glob("T-*.md"))
    return [parse(p) for p in paths]


def problems(tasks) -> list:
    """Plain-English reasons the task files are not acceptable."""
    found = []
    seen = {}
    for task in tasks:
        name = task.path.name
        found.extend(task.problems)
        if not task.id:
            continue
        if task.path.stem != task.id:
            found.append(f"{name}: the file name must be {task.id}.md to match its heading")
        if task.id in seen:
            found.append(f"{name}: {task.id} is also in {seen[task.id]}")
        seen[task.id] = name
        done = task.state == "done"
        # Tasks finished before the board existed only ever had a status.
        for key in (("status",) if done else REQUIRED):
            if not task.fields.get(key):
                found.append(f"{name}: the bullet '- **{key.title()}:** ...' is missing or empty")
        if done and not task.in_done_folder:
            found.append(
                f"{name}: its status says done, so move it to tasks/done/ "
                f"(git mv tasks/{name} tasks/done/{name})"
            )
        if task.in_done_folder and not done:
            found.append(f"{name}: it is in tasks/done/ but its status does not say done")
    return found


def build_board(tasks) -> str:
    """The open work as one Markdown table, grouped under umbrella tasks."""
    live = [t for t in tasks if t.id and t.state != "done"]
    by_id = {t.id: t for t in live}
    subs = {}
    for t in live:
        if t.umbrella and t.umbrella in by_id:
            subs.setdefault(t.umbrella, []).append(t)
    # A subtask whose umbrella is finished still shows, as its own row.
    tops = [t for t in live if not t.umbrella or t.umbrella not in by_id]

    def rank(t):
        return (STATE_ORDER.index(t.state), t.id)

    def cell(text):
        return (text or "—").replace("|", "\\|").replace("\n", " ")

    def row(t, prefix=""):
        link = f"[{t.id}](tasks/{t.id}.md)"
        return (
            f"| {prefix}{link} | {cell(t.title)} | {cell(t.status)} | {cell(t.get('agent'))} "
            f"| {cell(t.get('needs'))} | {cell(t.get('touches'))} |"
        )

    rows = []
    for t in sorted(tops, key=rank):
        rows.append(row(t))
        for s in sorted(subs.get(t.id, []), key=lambda x: x.id):
            rows.append(row(s, "↳ "))
    head = [
        "| Task | What | Status | Agent | Needs | Touches |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    return "\n".join(head + rows) + "\n"
