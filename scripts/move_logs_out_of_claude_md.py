"""Move CLAUDE.md's Decision log and Progress log into one file per entry.

One-off migration for T-053, kept so the move can be repeated and checked.

    python scripts/move_logs_out_of_claude_md.py OLD_CLAUDE.md          # write files
    python scripts/move_logs_out_of_claude_md.py OLD_CLAUDE.md --check  # compare only

The entry text is copied unchanged, including its list marker and
indentation. ``--check`` proves nothing was lost: every entry in the old
file appears, word for word and in the same order, in the folders, and
the two sections hold no other text apart from their one-line introductions.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import project_log  # noqa: E402

SECTIONS = {"decisions": "## Decision log", "progress": "## Progress log"}
INTROS = {
    "decisions": "Newest last. Each entry: date, decision, why, consequences.",
    "progress": "Newest last.",
}
TASK_ID = re.compile(r"\bT-\d{3}(?:-[A-Z](?:-\d+)?)?\b")
PULL = re.compile(r"\[PR #(\d+)\]\((https://github\.com/[^)]+)\)")
RUN = re.compile(r"\b[Rr]un #?(\d{2,})\b")
ENTRY_START = re.compile(r"^- \*\*(\d{4}-\d{2}-\d{2})")
STOP_WORDS = {"the", "a", "an", "and", "of", "to", "for", "in", "on", "is", "are", "with"}


def section_text(text: str, heading: str) -> str:
    start = text.index(heading + "\n") + len(heading) + 1
    following = text.find("\n## ", start)
    return text[start:] if following == -1 else text[start : following + 1]


def split_entries(section: str, intro: str):
    """Return (entries, leftover lines). An entry runs from its '- **date' line
    to the line before the next one, without trailing blank lines."""
    entries, current, leftover = [], None, []
    for line in section.splitlines():
        if ENTRY_START.match(line):
            if current:
                entries.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
        elif line.strip() and line.strip() != intro:
            leftover.append(line)
    if current:
        entries.append(current)
    return ["\n".join(lines).rstrip() for lines in entries], leftover


def lead(entry: str, kind: str) -> str:
    """The part of an entry that names it: a decision's bold title, or the
    words of a progress entry before its first colon."""
    flat = " ".join(entry.split())
    if kind == "decisions":
        bold = re.match(r"^- \*\*\d{4}-\d{2}-\d{2}(.*?)\*\*", flat)
        return bold.group(1) if bold else flat
    rest = re.sub(r"^- \*\*\d{4}-\d{2}-\d{2}\*\*\s*", "", flat)
    return rest.split(": ", 1)[0]


def title_words(entry: str, kind: str) -> str:
    flat = " ".join(entry.split())
    if kind == "decisions":
        words = re.sub(r"^[^—]*—\s*", "", lead(entry, kind))
    else:
        head = lead(entry, kind)
        words = re.sub(r"\(.*?\)", "", head)
        if not re.sub(r"[^a-z]|and|through", "", TASK_ID.sub("", words).lower()):
            # "T-005 (ChatGPT, PR #7): CI now parses..." -> words after the colon
            words = re.sub(r"^- \*\*\d{4}-\d{2}-\d{2}\*\*\s*", "", flat)
            words = words.split(": ", 1)[-1]
    words = TASK_ID.sub("", words)
    tokens = [t for t in re.findall(r"[a-z0-9]+", words.lower()) if t not in STOP_WORDS]
    return "-".join(tokens[:6]) or "entry"


def author_of(entry: str) -> str:
    flat = " ".join(entry.split())
    for name in ("Beaux and ChatGPT", "ChatGPT", "Claude", "Beaux"):
        if re.search(rf"\({re.escape(name)}\b", flat) or re.search(
            rf"DECISION \({re.escape(name)}\b", flat
        ):
            return name
    return project_log.NOT_RECORDED


def header_for(entry: str, kind: str, sequence: int) -> dict:
    flat = " ".join(entry.split())
    date = ENTRY_START.match(entry).group(1)
    tasks = list(dict.fromkeys(TASK_ID.findall(lead(entry, kind))))
    pulls = list(dict.fromkeys(url for _, url in PULL.findall(flat)))
    runs = list(dict.fromkeys(RUN.findall(flat)))
    header = {
        "date": date,
        "task": ", ".join(tasks) or "none",
        "author": author_of(entry),
        "pull_request": ", ".join(pulls) or project_log.NOT_RECORDED,
    }
    if kind == "progress":
        header["ci_run"] = ", ".join(runs) or project_log.NOT_RECORDED
        header["size"] = (
            "see text" if re.search(r"\d bytes|MiB", flat) else project_log.NOT_RECORDED
        )
    header["source"] = project_log.MIGRATED_SOURCE
    header["sequence"] = str(sequence)
    return header


def file_name(entry: str, header: dict, kind: str, used: set) -> str:
    task = header["task"].split(",")[0].strip()
    task = task[:5] + task[5:].upper() if task != "none" else task
    stem = header["date"] + ("-" + task if task != "none" else "") + "-" + title_words(entry, kind)
    name, counter = stem + ".md", 2
    while name in used:
        name, counter = f"{stem}-{counter}.md", counter + 1
    used.add(name)
    return name


def write_entry(path: Path, header: dict, entry: str) -> None:
    lines = ["---"] + [f"{key}: {value}" for key, value in header.items()] + ["---", "", entry, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def check(old_text: str) -> list:
    found = []
    for kind, heading in SECTIONS.items():
        old, leftover = split_entries(section_text(old_text, heading), INTROS[kind])
        for line in leftover:
            found.append(f"{kind}: text outside any entry: {line[:70]}")
        new = [entry.body for entry in project_log.load(kind)]
        migrated = [
            e.body for e in project_log.load(kind)
            if e.header.get("source") == project_log.MIGRATED_SOURCE
        ]
        if migrated != old:
            for index, (a, b) in enumerate(zip(old, migrated)):
                if a != b:
                    found.append(f"{kind}: entry {index + 1} differs: {a[:70]}")
                    break
            if len(old) != len(migrated):
                found.append(f"{kind}: {len(old)} entries in CLAUDE.md, {len(migrated)} moved")
        print(f"{kind}: {len(old)} entries in the old CLAUDE.md, {len(new)} files")
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("claude_md", type=Path, help="a copy of CLAUDE.md that still holds the logs")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    old_text = args.claude_md.read_text(encoding="utf-8")
    if not args.check:
        for kind, heading in SECTIONS.items():
            entries, _ = split_entries(section_text(old_text, heading), INTROS[kind])
            folder = project_log.FOLDERS[kind]
            folder.mkdir(exist_ok=True)
            used = set()
            for sequence, entry in enumerate(entries, start=1):
                header = header_for(entry, kind, sequence)
                write_entry(folder / file_name(entry, header, kind, used), header, entry)
    found = check(old_text)
    for line in found:
        print(line)
    print("nothing lost" if not found else f"{len(found)} problems")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
