"""
Keeps details from real contracts out of the repository.

The repository is public. Names, addresses, numbers and terms from real
contracts were once committed and had to be removed by rewriting history
(2026-11-18, TASKS.md T-016). This test stops them coming back.

The list of what to look for is itself private, so it is not in the
repository. It lives in the GitHub Actions secret BLOCKED_TERMS, one term per
line, and CI passes it to this test. Without that variable (on your own
computer, say) the test is skipped. To check locally, set BLOCKED_TERMS
yourself for that one command.

On failure the test names the file and line, never the term, so the CI log
does not repeat what it is guarding.
"""
import os
import pathlib
import re
import subprocess
import unicodedata

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".txt", ".yml", ".yaml", ".bat", ".cmd", ".ps1", ".command",
                 ".json", ".cfg", ".toml", ".ini", ""}


def normalized(text: str) -> str:
    """Compare letters, digits and diacritics, ignoring case and punctuation."""
    text = unicodedata.normalize("NFC", text).casefold()
    return " ".join(re.findall(r"[^\W_]+", text))


def blocked_terms():
    raw = os.environ.get("BLOCKED_TERMS", "")
    return [t for t in (normalized(line) for line in raw.splitlines()) if t]


def tracked_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
        names = [n for n in out.decode("utf-8").split("\0") if n]
    except (OSError, subprocess.CalledProcessError):
        names = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
                 if p.is_file() and ".git" not in p.parts]
    return [ROOT / n for n in names if (ROOT / n).suffix.lower() in TEXT_SUFFIXES]


def find(terms, files):
    """(file, line number) for every line holding a term, matched on whole words."""
    found = []
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(lines, 1):
            padded = f" {normalized(line)} "
            if any(f" {term} " in padded for term in terms):
                found.append((path.relative_to(ROOT).as_posix(), number))
    return found


def test_finder_matches_whole_words_whatever_the_case_and_punctuation(tmp_path):
    sample = tmp_path / "notes.md"
    sample.write_text("Signed by A. Placeholder-Person\nNot a match: placeholderperson\n", encoding="utf-8")
    global ROOT
    old, ROOT = ROOT, tmp_path
    try:
        assert find([normalized("a placeholder person")], [sample]) == [("notes.md", 1)]
        assert find([normalized("PERSON")], [sample]) == [("notes.md", 1)]
        assert find([normalized("Phạm")], [sample]) == []
    finally:
        ROOT = old


@pytest.mark.skipif(not os.environ.get("BLOCKED_TERMS"),
                    reason="BLOCKED_TERMS is not set; CI sets it from a GitHub secret")
def test_no_details_from_real_contracts():
    found = find(blocked_terms(), tracked_files())
    assert not found, (
        "Details from a real contract are in the repository, which is public. "
        "Replace them with invented ones (see CLAUDE.md). Found in: "
        + ", ".join(f"{path} line {line}" for path, line in found)
    )
