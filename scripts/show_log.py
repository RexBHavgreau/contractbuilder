"""Print the progress log or decision log, oldest first (T-053).

    python scripts/show_log.py progress
    python scripts/show_log.py decisions
    python scripts/show_log.py decisions --task T-052
    python scripts/show_log.py progress --check     # report malformed files
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import project_log  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=sorted(project_log.FOLDERS))
    parser.add_argument("--task", help="only entries whose task field names this task")
    parser.add_argument("--since", help="only entries on or after this date (YYYY-MM-DD)")
    parser.add_argument("--check", action="store_true", help="list malformed files and exit")
    args = parser.parse_args(argv)

    entries = project_log.load(args.kind)
    if args.check:
        found = [p for entry in entries for p in project_log.problems(entry, args.kind)]
        for line in found:
            print(line)
        print(f"{len(entries)} {args.kind} entries, {len(found)} problems")
        return 1 if found else 0
    if args.task:
        entries = [e for e in entries if args.task in e.header.get("task", "")]
    if args.since:
        entries = [e for e in entries if e.header.get("date", "") >= args.since]
    sys.stdout.write(project_log.render(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
