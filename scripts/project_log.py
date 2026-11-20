"""Read the project's progress and decision entries (T-053).

Each entry is its own Markdown file in ``progress/`` or ``decisions/`` so
that two pull requests that each add an entry never touch the same file.
A file starts with a small header between two ``---`` lines::

    ---
    date: 2026-11-21
    task: T-052
    author: Claude
    pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/47
    ci_run: 231
    size: release 18,095,000 bytes; component-enabled 18,096,000 bytes; headroom 12.74 MiB
    ---

    What was done, in plain words.

Entries are shown oldest first: by ``date``, then by ``sequence`` (only the
entries moved out of CLAUDE.md have one, to keep their original order within
a day), then by file name. Standard library only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = {"progress": ROOT / "progress", "decisions": ROOT / "decisions"}

# Header fields every entry must carry. A progress entry also records the CI
# run and the size numbers so the size gate stays visible (TASKS.md).
REQUIRED = {
    "progress": ("date", "task", "author", "pull_request", "ci_run", "size"),
    "decisions": ("date", "task", "author", "pull_request"),
}

# Entries moved from CLAUDE.md predate the header; only they may say a field
# was not recorded.
MIGRATED_SOURCE = "CLAUDE.md (moved 2026-11-20, T-053)"
NOT_RECORDED = "not recorded"

FILE_NAME = re.compile(
    r"^\d{4}-\d{2}-\d{2}-(?:T-\d{3}(?:-[A-Z](?:-\d+)?)?-)?[a-z0-9]+(?:-[a-z0-9]+)*\.md$"
)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Entry:
    path: Path
    header: dict = field(default_factory=dict)
    body: str = ""

    @property
    def sort_key(self):
        sequence = self.header.get("sequence", "")
        return (
            self.header.get("date", ""),
            0 if sequence else 1,
            int(sequence) if sequence.isdigit() else 0,
            self.path.name,
        )


def parse(path: Path) -> Entry:
    """Split a file into its header fields and body text."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return Entry(path, {}, text)
    header = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body = "\n".join(lines[index + 1 :]).strip("\n")
            return Entry(path, header, body)
        key, sep, value = line.partition(":")
        if sep:
            header[key.strip()] = value.strip()
    return Entry(path, {}, text)


def problems(entry: Entry, kind: str) -> list:
    """Plain-English reasons an entry file is not acceptable."""
    found = []
    name = entry.path.name
    if not FILE_NAME.match(name):
        found.append(
            f"{name}: name it YYYY-MM-DD-T-NNN-short-title.md "
            "(lower-case words joined by hyphens)"
        )
    if not entry.header:
        found.append(f"{name}: the file must start with a header between two --- lines")
        return found
    migrated = entry.header.get("source") == MIGRATED_SOURCE
    for key in REQUIRED[kind]:
        value = entry.header.get(key, "")
        if not value:
            found.append(f"{name}: header field '{key}' is missing or empty")
        elif value.lower() == NOT_RECORDED and not migrated:
            found.append(
                f"{name}: header field '{key}' says '{NOT_RECORDED}'; give the real value "
                "(for a change with no executable effect, write 'no executable change')"
            )
    date = entry.header.get("date", "")
    if date and not DATE.match(date):
        found.append(f"{name}: date must be YYYY-MM-DD")
    elif date and not name.startswith(date):
        found.append(f"{name}: the file name must start with the header date {date}")
    if not entry.body.strip():
        found.append(f"{name}: the entry has no text")
    return found


def load(kind: str, folder: Path | None = None) -> list:
    folder = folder or FOLDERS[kind]
    entries = [parse(path) for path in folder.glob("*.md") if path.name != "README.md"]
    return sorted(entries, key=lambda entry: entry.sort_key)


def render(entries) -> str:
    """The entries as one Markdown list, oldest first."""
    return "\n\n".join(entry.body for entry in entries) + "\n"
