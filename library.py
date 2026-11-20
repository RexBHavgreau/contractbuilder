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
from typing import Iterator, Mapping, Sequence

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


    def save_component(
        self,
        component_id: int | None,
        name: str,
        markdown: str,
        description: str = "",
        category: str = "",
        tags: Sequence[str] | None = None,
        note: str = "",
    ) -> dict:
        """Atomically save component metadata and one new immutable wording version."""
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("Enter a component name.")
        if not isinstance(markdown, str):
            raise TypeError("Component wording must be text.")

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            is_new = component_id is None
            if is_new:
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
                saved_id = int(cursor.lastrowid)
            else:
                saved_id = int(component_id)
                existing = connection.execute(
                    "SELECT status FROM components WHERE id = ?", (saved_id,)
                ).fetchone()
                if existing is None:
                    raise ValueError("That component no longer exists.")
                if existing["status"] != "active":
                    raise ValueError("Restore the archived component before saving a new version.")
                connection.execute(
                    """
                    UPDATE components
                    SET name = ?, description = ?, category = ?, tags = ?
                    WHERE id = ?
                    """,
                    (
                        clean_name,
                        str(description or "").strip(),
                        str(category or "").strip(),
                        _tags_json(tags),
                        saved_id,
                    ),
                )

            version = self._insert_version(
                connection, saved_id, markdown, note
            )
            return {
                "component_id": saved_id,
                "version": version,
                "is_new": is_new,
            }

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

    def create_assembly(self, name: str, description: str = "") -> int:
        """Create a named assembly recipe without saving a revision yet."""
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("Enter an assembly name.")
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "INSERT INTO assemblies (name, description, status, created) "
                "VALUES (?, ?, 'active', ?)",
                (clean_name, str(description or "").strip(), created),
            )
            return int(cursor.lastrowid)

    def get_assembly(self, assembly_id: int) -> dict | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, name, description, status, created "
                "FROM assemblies WHERE id = ?",
                (int(assembly_id),),
            ).fetchone()
            return dict(row) if row is not None else None

    def list_assemblies(self, include_archived: bool = False) -> list[dict]:
        query = "SELECT id, name, description, status, created FROM assemblies"
        if not include_archived:
            query += " WHERE status = 'active'"
        query += " ORDER BY name COLLATE NOCASE, id"
        with self._connection() as connection:
            return [dict(row) for row in connection.execute(query).fetchall()]

    def save_assembly_revision(
        self,
        assembly_id: int,
        shell_path: str,
        shell_sha256: str,
        components: Sequence[int | Mapping[str, object]],
        note: str = "",
    ) -> dict:
        """Save a finalized revision pinned to explicit component version IDs.

        Each item in components is either a version ID or a mapping with
        component_version_id and optional Boolean included. Sequence order
        becomes the saved position. No revision uses a moving latest pointer.
        """
        clean_path = str(shell_path or "").strip()
        if not clean_path:
            raise ValueError("Choose a Word document shell.")
        digest = str(shell_sha256 or "").strip()
        if len(digest) != 64 or any(
            character not in "0123456789abcdefABCDEF" for character in digest
        ):
            raise ValueError("The shell SHA-256 must contain exactly 64 hexadecimal characters.")
        if isinstance(components, (str, bytes)) or not isinstance(components, Sequence):
            raise TypeError("Assembly components must be an ordered sequence.")
        if not components:
            raise ValueError("Add at least one component to the assembly.")

        normalized: list[tuple[int, bool]] = []
        for item in components:
            if isinstance(item, Mapping):
                raw_id = item.get("component_version_id")
                included = item.get("included", True)
                if not isinstance(included, bool):
                    raise TypeError("Each component's included value must be Boolean.")
            else:
                raw_id = item
                included = True
            if isinstance(raw_id, bool):
                raise TypeError("Component version IDs must be integers.")
            try:
                version_id = int(raw_id)
            except (TypeError, ValueError):
                raise TypeError("Component version IDs must be integers.") from None
            if version_id < 1:
                raise ValueError("Component version IDs must be positive.")
            normalized.append((version_id, included))
        if not any(included for _, included in normalized):
            raise ValueError("Include at least one component in the assembly.")

        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            assembly = connection.execute(
                "SELECT status FROM assemblies WHERE id = ?",
                (int(assembly_id),),
            ).fetchone()
            if assembly is None:
                raise ValueError("That assembly no longer exists.")
            if assembly["status"] != "active":
                raise ValueError("Restore the archived assembly before saving a revision.")

            for version_id, _included in normalized:
                component = connection.execute(
                    """
                    SELECT components.status
                    FROM component_versions
                    JOIN components
                      ON components.id = component_versions.component_id
                    WHERE component_versions.id = ?
                    """,
                    (version_id,),
                ).fetchone()
                if component is None:
                    raise ValueError(
                        f"Component version {version_id} no longer exists."
                    )
                if component["status"] != "active":
                    raise ValueError(
                        f"Restore the archived component for version {version_id} "
                        "before adding it to a new assembly revision."
                    )

            number = connection.execute(
                "SELECT COALESCE(MAX(number), 0) + 1 "
                "FROM assembly_versions WHERE assembly_id = ?",
                (int(assembly_id),),
            ).fetchone()[0]
            cursor = connection.execute(
                """
                INSERT INTO assembly_versions
                    (assembly_id, number, shell_path, shell_sha256, created, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    int(assembly_id),
                    int(number),
                    clean_path,
                    digest.lower(),
                    created,
                    str(note or "").strip(),
                ),
            )
            revision_id = int(cursor.lastrowid)

            for position, (version_id, included) in enumerate(normalized):
                connection.execute(
                    """
                    INSERT INTO assembly_components
                        (assembly_version_id, component_version_id, position, included)
                    VALUES (?, ?, ?, ?)
                    """,
                    (revision_id, version_id, position, int(included)),
                )

            connection.execute(
                "UPDATE assembly_versions SET finalized = 1 WHERE id = ?",
                (revision_id,),
            )

        revision = self.get_assembly_revision(revision_id)
        if revision is None:
            raise sqlite3.DatabaseError("The saved assembly revision could not be read back.")
        return revision

    def get_assembly_revision(self, revision_id: int) -> dict | None:
        """Read a saved revision with its exact component versions in order."""
        with self._connection() as connection:
            revision = connection.execute(
                """
                SELECT assembly_versions.id, assembly_versions.assembly_id,
                       assemblies.name AS assembly_name,
                       assemblies.status AS assembly_status,
                       assembly_versions.number, assembly_versions.shell_path,
                       assembly_versions.shell_sha256, assembly_versions.created,
                       assembly_versions.note, assembly_versions.finalized
                FROM assembly_versions
                JOIN assemblies ON assemblies.id = assembly_versions.assembly_id
                WHERE assembly_versions.id = ?
                """,
                (int(revision_id),),
            ).fetchone()
            if revision is None:
                return None

            rows = connection.execute(
                """
                SELECT assembly_components.id,
                       assembly_components.position,
                       assembly_components.included,
                       component_versions.id AS component_version_id,
                       component_versions.number AS component_version_number,
                       component_versions.markdown,
                       component_versions.created AS version_created,
                       component_versions.note AS version_note,
                       components.id AS component_id,
                       components.name AS component_name,
                       components.status AS component_status
                FROM assembly_components
                JOIN component_versions
                  ON component_versions.id = assembly_components.component_version_id
                JOIN components
                  ON components.id = component_versions.component_id
                WHERE assembly_components.assembly_version_id = ?
                ORDER BY assembly_components.position
                """,
                (int(revision_id),),
            ).fetchall()

        result = dict(revision)
        result["finalized"] = bool(result["finalized"])
        result["components"] = []
        for row in rows:
            item = dict(row)
            item["included"] = bool(item["included"])
            result["components"].append(item)
        return result

    def list_assembly_revisions(self, assembly_id: int) -> list[dict]:
        """List saved assembly revisions newest first."""
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, assembly_id, number, shell_path, shell_sha256,
                       created, note, finalized
                FROM assembly_versions
                WHERE assembly_id = ?
                ORDER BY number DESC
                """,
                (int(assembly_id),),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_newer_versions_for_revision(self, revision_id: int) -> list[dict]:
        """List newer wording options for each pinned component, without applying them."""
        with self._connection() as connection:
            exists = connection.execute(
                "SELECT 1 FROM assembly_versions WHERE id = ?",
                (int(revision_id),),
            ).fetchone()
            if exists is None:
                raise ValueError("That assembly revision no longer exists.")

            pinned_rows = connection.execute(
                """
                SELECT assembly_components.position,
                       assembly_components.included,
                       component_versions.id AS component_version_id,
                       component_versions.number AS pinned_number,
                       components.id AS component_id,
                       components.name AS component_name,
                       components.status AS component_status
                FROM assembly_components
                JOIN component_versions
                  ON component_versions.id = assembly_components.component_version_id
                JOIN components
                  ON components.id = component_versions.component_id
                WHERE assembly_components.assembly_version_id = ?
                ORDER BY assembly_components.position
                """,
                (int(revision_id),),
            ).fetchall()

            result = []
            for pinned in pinned_rows:
                item = dict(pinned)
                item["included"] = bool(item["included"])
                newer = connection.execute(
                    """
                    SELECT id, number, markdown, created, note
                    FROM component_versions
                    WHERE component_id = ? AND number > ?
                    ORDER BY number
                    """,
                    (item["component_id"], item["pinned_number"]),
                ).fetchall()
                item["newer_versions"] = [dict(row) for row in newer]
                result.append(item)
            return result

