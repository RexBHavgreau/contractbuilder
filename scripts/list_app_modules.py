"""List the application's top-level modules, one per line (T-035).

    python scripts/list_app_modules.py

CI hands this list to PyInstaller as `--hidden-import`s for the comparison
build, so a module the app does not import yet is still measured. Nothing is
listed by hand: a new `.py` file, or a new package, at the top of the
repository is picked up by itself. Only three files are left out, each for a
stated reason, and a test pins that list so leaving a module out is a
deliberate edit.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# app.py is the launcher, simple_app.py is the build's own entry point, and
# advanced_app.py is the earlier window that is not packaged (tasks/T-036.md).
EXCLUDED = frozenset({"app", "advanced_app", "simple_app"})
# Folders at the top level that are not part of the application.
NOT_APP_FOLDERS = frozenset({"tests", "scripts", "progress", "decisions", "tasks"})


def app_modules(root: Path | None = None) -> list:
    root = Path(root) if root else ROOT
    names = {p.stem for p in root.glob("*.py")}
    for folder in root.iterdir():
        if folder.is_dir() and (folder / "__init__.py").is_file() and folder.name not in NOT_APP_FOLDERS:
            names.add(folder.name)
    return sorted(names - EXCLUDED)


def main() -> int:
    sys.stdout.write("\n".join(app_modules()) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
