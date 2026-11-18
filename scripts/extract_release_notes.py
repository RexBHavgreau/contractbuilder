"""Extract one version's plain-English section from CHANGES.txt."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def read_release_notes(version: str, changes_path: str | Path = "CHANGES.txt") -> str:
    """Return the non-empty notes under the exact matching version heading."""
    requested = version.strip().lstrip("vV")
    if not requested:
        raise ValueError("A release version is required.")

    lines = Path(changes_path).read_text(encoding="utf-8").splitlines()
    heading = re.compile(r"^##\s+v?([^\s]+)\s*$")
    start = None
    for index, line in enumerate(lines):
        match = heading.fullmatch(line.strip())
        if match and match.group(1).lstrip("vV") == requested:
            if start is not None:
                raise ValueError(f"CHANGES.txt has more than one section for version {requested}.")
            start = index + 1

    if start is None:
        raise ValueError(f"CHANGES.txt has no section for version {requested}.")

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    notes = "\n".join(lines[start:end]).strip()
    if not notes:
        raise ValueError(f"CHANGES.txt has an empty section for version {requested}.")
    return notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Version to extract, such as 0.3.1")
    parser.add_argument("changes_file", type=Path, help="Path to CHANGES.txt")
    parser.add_argument("output_file", type=Path, help="File to write the extracted notes to")
    args = parser.parse_args(argv)

    try:
        notes = read_release_notes(args.version, args.changes_file)
        args.output_file.write_text(notes + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
