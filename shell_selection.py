"""Choose a Word shell for component assembly and remember the last usable one.

The picker itself belongs to the component window (T-023). This module takes
the file the user picked, runs the read-only checker from T-026, turns the
findings into plain-English lines, and stores the path of the last shell that
can be used. Nothing here changes the shell file.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union
import json
import os
import sys

import shell_check


SETTINGS_FILE_NAME = "shell-settings.json"
_LAST_SHELL_KEY = "last_shell"


@dataclass(frozen=True)
class ShellSelection:
    """What the window shows after the user picks a shell."""

    path: Path
    usable: bool
    remembered: bool
    lines: Tuple[str, ...]
    result: shell_check.ShellCheckResult


def settings_path() -> Path:
    """Beside the publisher profiles and update settings, per user."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "TMAI Contract Builder" / SETTINGS_FILE_NAME


def last_shell(path: Union[str, Path, None] = None) -> Optional[Path]:
    """Return the remembered shell if it still exists, otherwise None.

    A damaged settings file is treated as "nothing remembered" rather than an
    error, so the user is simply asked to pick a shell again.
    """
    try:
        data = json.loads((Path(path) if path else settings_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    remembered = data.get(_LAST_SHELL_KEY)
    if not isinstance(remembered, str) or not remembered:
        return None
    candidate = Path(remembered)
    return candidate if candidate.is_file() else None


def _remember(shell: Path, path: Optional[Path]) -> bool:
    """Store the shell path. Returns False if the settings cannot be written."""
    target = path or settings_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({_LAST_SHELL_KEY: str(shell)}), encoding="utf-8")
    except OSError:
        return False
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return True


def describe(result: shell_check.ShellCheckResult) -> Tuple[str, ...]:
    """Plain-English lines for a checker result, without internal codes."""
    if not result.can_generate:
        messages = [item.message for item in result.errors]
        return tuple(
            ["This file cannot be used as a shell, so it has not been chosen."] + messages
        )
    if not result.findings:
        return ("This shell is ready to use. No problems were found.",)
    count = len(result.warnings)
    noun = "warning" if count == 1 else "warnings"
    lines = [
        "This shell can be used, but it has %d %s. Read them before creating documents."
        % (count, noun)
    ]
    lines.extend("Warning: " + item.message for item in result.warnings)
    return tuple(lines)


def choose_shell(
    path: Union[str, Path],
    settings: Union[str, Path, None] = None,
    remember: bool = True,
) -> ShellSelection:
    """Check the picked file and, if it can be used, remember it as the last shell.

    A shell with errors is never remembered, and an earlier remembered shell is
    left as it was. A shell with only warnings is remembered, because the user
    is told about the warnings and can still choose to continue.
    """
    shell = Path(path)
    result = shell_check.check_shell(shell)
    lines = list(describe(result))
    usable = result.can_generate
    remembered = False
    if usable and remember:
        settings_file = Path(settings) if settings else None
        remembered = _remember(shell, settings_file)
        if not remembered:
            lines.append(
                "This shell can be used for now, but it could not be remembered. "
                "You will need to pick it again next time."
            )
    return ShellSelection(
        path=shell,
        usable=usable,
        remembered=remembered,
        lines=tuple(lines),
        result=result,
    )
