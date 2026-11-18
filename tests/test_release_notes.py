from pathlib import Path

import pytest

from scripts.extract_release_notes import read_release_notes
from version import APP_VERSION


def test_reads_the_requested_version_only(tmp_path):
    changes = tmp_path / "CHANGES.txt"
    changes.write_text(
        "# What's new\n\n"
        "## 0.3.1\nNewest changes.\n\n"
        "## 0.3.0\nEarlier changes.\n",
        encoding="utf-8",
    )

    assert read_release_notes("0.3.1", changes) == "Newest changes."
    assert read_release_notes("v0.3.0", changes) == "Earlier changes."


def test_missing_or_empty_release_notes_are_errors(tmp_path):
    changes = tmp_path / "CHANGES.txt"
    changes.write_text("## 0.3.0\nExisting notes.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no section for version 0.3.1"):
        read_release_notes("0.3.1", changes)

    changes.write_text("## 0.3.1\n\n## 0.3.0\nEarlier changes.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty section for version 0.3.1"):
        read_release_notes("0.3.1", changes)


def test_current_application_version_has_release_notes():
    root = Path(__file__).resolve().parents[1]
    notes = read_release_notes(APP_VERSION, root / "CHANGES.txt")
    assert notes.strip()
