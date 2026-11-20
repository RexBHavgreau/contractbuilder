"""Non-UI access to reusable components in the shared local SQLite database.

This module deliberately depends only on the standard library and the
publisher database module. It is safe to import from the desktop UI, tests,
or other application code; it contains no Tkinter code.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence

from publisher_profiles import PublisherProfileStore, default_database_path


def _tags_json(tags: Sequence[str] | None) -> str:
    """Serialize user-defined tag labels without imposing a fixed taxonomy."""
    if tags is None:
        values = []
    elif isinstance(tags, str):
        values = [tags]
    else:
        values = list(tags)

    result = []
    seen = set()
    for value in values:
        label = str(value).strip()
        key = label.casefold()
        if label and key not in seen:
            result.append(label)
            seen.add(key)
    return json.dumps(result, ensure_ascii=False)


def _component_from_row(row: sqlite3.Row | dict) -> dict:
    component = dict(row)
    try:
        tags = json.loads(component.get("tags") or "[]")
    except (TypeError, ValueError):
        tags = []
    component["tags"] = tags if isinstance(tags, list) else []
    return component


class ComponentLibrary:
    """CRUD access to components and their immutable Markdown versions.

    The publisher profiles and component library share one database file.
    Passing a path is useful for tests; normal application code should omit it
    so the platform's per-user application-data location is used.
    """

    def __init__(self, database_path: str | Path | None = None):
        if database_path is None:
            self.path = default_database_path()
            # Let the existing store initialize and secure the per-user file.
            self._profile_store = PublisherProfileStore()
        else:
            self.path = Path(database_path)
            self._profile_store = PublisherProfileStore(self.path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _insert_version(
        connection: sqlite3.Connection,
        component_id: int,
        markdown: str,
        note: str = "",
    ) -> dict:
        component = connection.execute(
            "SELECT status FROM components WHERE id = ?", (int(component_id),)
        ).fetchone()
        if component is None:
            raise ValueError("That component no longer exists.")
        if component["status"] != "active":
            raise ValueError("Restore the archived component before saving a new version.")

        number = connection.execute(
            "SELECT COALESCE(MAX(number), 0) + 1 "
            "FROM component_versions WHERE component_id = ?",
            (int(component_id),),
        ).fetchone()[0]
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cursor = connection.execute(
            "INSERT INTO component_versions "
            "(component_id, number, markdown, created, note) VALUES (?, ?, ?, ?, ?)",
            (int(component_id), int(number), markdown, created, str(note or "").strip()),
        )
        row = connection.execute(
            "SELECT id, component_id, number, markdown, created, note "
            "FROM component_versions WHERE id = ?",
            (int(cursor.lastrowid),),
        ).fetchone()
        return dict(row)

    def create_component(
        self,
        name: str,
        markdown: str = "",
        description: str = "",
        category: str = "",
        tags: Sequence[str] | None = None,
        note: str = "",
    ) -> int:
        """Create a component and its first immutable wording version."""
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("Enter a component name.")
        if not isinstance(markdown, str):
            raise TypeError("Component wording must be text.")

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "INSERT INTO components (name, description, category, tags, status) "
                "VALUES (?, ?, ?, ?, 'active')",
                (
                    clean_name,
                    str(description or "").strip(),
                    str(category or "").strip(),
                    _tags_json(tags),
                ),
            )
            component_id = int(cursor.lastrowid)
            self._insert_version(connection, component_id, markdown, note)
            return component_id

    def get_component(self, component_id: int) -> dict | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, name, description, category, tags, status "
                "FROM components WHERE id = ?",
                (int(component_id),),
            ).fetchone()
            return _component_from_row(row) if row is not None else None

    def list_components(
        self,
        category: str | None = None,
        tag: str | None = None,
        include_archived: bool = False,
    ) -> list[dict]:
        """List components, optionally filtered by free-text category or tag."""
        query = "SELECT id, name, description, category, tags, status FROM components"
        if not include_archived:
            query += " WHERE status = 'active'"
        query += " ORDER BY name COLLATE NOCASE, id"
        with self._connection() as connection:
            rows = connection.execute(query).fetchall()

        wanted_category = str(category).strip().casefold() if category is not None else None
        wanted_tag = str(tag).strip().casefold() if tag is not None else None
        result = []
        for row in rows:
            component = _component_from_row(row)
            if wanted_category is not None and component["category"].casefold() != wanted_category:
                continue
            if wanted_tag is not None and wanted_tag not in {
                str(value).casefold() for value in component["tags"]
            }:
                continue
            result.append(component)
        return result

    def search_components(
        self, wording: str, include_archived: bool = False
    ) -> list[dict]:
        """Search metadata and every saved wording version, newest or historical."""
        needle = str(wording or "").strip().casefold()
        if not needle:
            return self.list_components(include_archived=include_archived)

        components = self.list_components(include_archived=include_archived)
        matches = []
        with self._connection() as connection:
            for component in components:
                metadata = (
                    component["name"],
                    component["description"],
                    component["category"],
                    *component["tags"],
                )
                found = any(needle in str(value).casefold() for value in metadata)
                if not found:
                    rows = connection.execute(
                        "SELECT markdown FROM component_versions "
                        "WHERE component_id = ? ORDER BY number DESC",
                        (component["id"],),
                    ).fetchall()
                    found = any(needle in row["markdown"].casefold() for row in rows)
                if found:
                    matches.append(component)
        return matches

    def get_component_version(self, version_id: int) -> dict | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, component_id, number, markdown, created, note "
                "FROM component_versions WHERE id = ?",
                (int(version_id),),
            ).fetchone()
            return dict(row) if row is not None else None

    def list_component_versions(self, component_id: int) -> list[dict]:
        """Return immutable versions newest first."""
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, component_id, number, markdown, created, note "
                "FROM component_versions WHERE component_id = ? "
                "ORDER BY number DESC",
                (int(component_id),),
            ).fetchall()
            return [dict(row) for row in rows]

    def save_component_version(
        self, component_id: int, markdown: str, note: str = ""
    ) -> dict:
        """Save an edit as the next version; never update an existing version."""
        if not isinstance(markdown, str):
            raise TypeError("Component wording must be text.")
        with self._connection() as connection:
            # Serializes version-number allocation across simultaneous app
            # instances, preventing two edits from receiving the same number.
            connection.execute("BEGIN IMMEDIATE")
            return self._insert_version(connection, component_id, markdown, note)

    def _set_status(self, table: str, record_id: int, status: str) -> bool:
        """Change only the lifecycle status of a component or assembly."""
        if table not in {"components", "assemblies"}:
            raise ValueError("Unsupported archive record type.")
        if status not in {"active", "archived"}:
            raise ValueError("Unsupported archive status.")
        with self._connection() as connection:
            cursor = connection.execute(
                f"UPDATE {table} SET status = ? WHERE id = ?",
                (status, int(record_id)),
            )
            return cursor.rowcount == 1

    def archive_component(self, component_id: int) -> bool:
        """Hide a component from normal browsing without deleting its history."""
        return self._set_status("components", component_id, "archived")

    def restore_component(self, component_id: int) -> bool:
        """Return an archived component to normal browsing."""
        return self._set_status("components", component_id, "active")

    def archive_assembly(self, assembly_id: int) -> bool:
        """Hide an assembly while preserving every saved revision."""
        return self._set_status("assemblies", assembly_id, "archived")

    def restore_assembly(self, assembly_id: int) -> bool:
        """Return an archived assembly to normal browsing."""
        return self._set_status("assemblies", assembly_id, "active")

