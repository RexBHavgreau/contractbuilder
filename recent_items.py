"""Recently used Word files and contract assemblies, kept per user (T-048-C).

Pure and Tkinter-free. The list lives under the key ``recent`` in the same
per-user settings file as the update settings, so the saved update token is
kept exactly as it was: every other key is read back and written unchanged.
Recording is best effort; a settings file that cannot be read or written
never stops a document from opening.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Optional

RECENT_LIMIT = 5
_KEY = "recent"
TEMPLATE = "template"
ASSEMBLY = "assembly"


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load(path: Path) -> list[dict]:
    """The remembered items, newest first. Damaged data gives an empty list."""
    items = _read(path).get(_KEY)
    if not isinstance(items, list):
        return []
    clean = []
    for item in items:
        if not isinstance(item, dict) or item.get("kind") not in (TEMPLATE, ASSEMBLY):
            continue
        if not isinstance(item.get("key"), str) or not item["key"]:
            continue
        clean.append({
            "kind": item["kind"],
            "key": item["key"],
            "label": str(item.get("label") or item["key"]),
        })
    return clean[:RECENT_LIMIT]


def remember(items: list[dict], entry: dict) -> list[dict]:
    """Put ``entry`` first, drop any earlier copy of it, keep the newest few."""
    same = lambda item: item["kind"] == entry["kind"] and item["key"] == entry["key"]
    return ([dict(entry)] + [item for item in items if not same(item)])[:RECENT_LIMIT]


def forget(items: list[dict], entry: dict) -> list[dict]:
    return [item for item in items if not (item["kind"] == entry["kind"] and item["key"] == entry["key"])]


def save(path: Path, items: list[dict]) -> bool:
    """Write the list, keeping every other key. Returns False if it cannot be saved."""
    data = _read(path)
    data[_KEY] = list(items)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except OSError:
        return False
    return True


def record(path: Path, entry: dict) -> bool:
    return save(path, remember(load(path), entry))


def remove(path: Path, entry: dict) -> bool:
    return save(path, forget(load(path), entry))


def template_status(entry: dict) -> str:
    """'ok' while the file is there, otherwise 'missing'."""
    return "ok" if Path(entry["key"]).is_file() else "missing"


def assembly_status(entry: dict, has_revision: Callable[[int], bool]) -> str:
    """'ok' while the assembly still has a saved revision, otherwise 'missing'."""
    try:
        return "ok" if has_revision(int(entry["key"])) else "missing"
    except (TypeError, ValueError):
        return "missing"


def status(entry: dict, has_revision: Optional[Callable[[int], bool]] = None) -> str:
    if entry["kind"] == TEMPLATE:
        return template_status(entry)
    return assembly_status(entry, has_revision or (lambda _id: False))
