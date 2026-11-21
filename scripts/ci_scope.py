"""Decide which platform builds a CI run needs (T-035).

    python scripts/ci_scope.py --event pull_request --base SHA --head SHA

Prints `windows=true|false` and `macos=true|false`, ready to append to
$GITHUB_OUTPUT. Everything runs for pushes to main, tags, scheduled and manual
runs. A pull request builds only what its changed files could affect, so a
change to a task file or a document does not start three platform builds:

* Windows: application code, anything bundled into the executable, the build
  scripts and the size scripts, `requirements.txt` and the workflow;
* macOS: only `build-mac.command`, `requirements.txt` and the workflow (the
  30 MiB target is a Windows target; the macOS builds run on every merge).

The tests always run. If the changed files cannot be read, everything runs.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

WINDOWS_ALWAYS = (
    re.compile(r"^requirements\.txt$"),
    re.compile(r"^(USER-GUIDE|THIRD-PARTY-LICENSES)\.txt$"),
    re.compile(r"^build-windows\.(ps1|bat)$"),
    re.compile(r"^\.github/workflows/"),
    re.compile(r"^scripts/(check_executable_size|list_app_modules|size_report|ci_scope)\.py$"),
)
APP_CODE = re.compile(r"^(?!tests/|scripts/).*\.py$")
MACOS_ALWAYS = (
    re.compile(r"^build-mac\.command$"),
    re.compile(r"^requirements\.txt$"),
    re.compile(r"^\.github/workflows/"),
)


def decide(event: str, files) -> dict:
    """{'windows': bool, 'macos': bool} for this event and these changed files."""
    if event != "pull_request" or not files:
        return {"windows": True, "macos": True}
    files = list(files)
    windows = any(APP_CODE.match(f) or any(r.match(f) for r in WINDOWS_ALWAYS) for f in files)
    macos = any(any(r.match(f) for r in MACOS_ALWAYS) for f in files)
    return {"windows": windows, "macos": macos}


def changed_files(base: str, head: str) -> list:
    out = subprocess.run(
        ["git", "diff", "--name-only", base, head], capture_output=True, text=True, check=True
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", required=True)
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="")
    args = parser.parse_args(argv)
    files = []
    if args.event == "pull_request" and args.base and args.head:
        try:
            files = changed_files(args.base, args.head)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"Could not list the changed files ({exc}); building everything.", file=sys.stderr)
    for name, value in decide(args.event, files).items():
        print(f"{name}={'true' if value else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
