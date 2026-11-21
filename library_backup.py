"""Portable, validated backups for the Contract Builder component library.

Publisher profiles are separate business/contact data and are excluded unless
the user explicitly opts in. The backup format is documented JSON so it can
be inspected and recovered without Contract Builder.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Mapping

FORMAT = "contractbuilder-library-backup"
FORMAT_VERSION = 1
APP_TABLES = (
    "components",
    "component_versions",
    "assemblies",
    "assembly_versions",
    "assembly_components",
    "field_definitions",
)
PROFILE_TABLES = (
    "publishers",
    "publisher_details",
    "publisher_field_matches",
    "publisher_parties",
)
INSERT_ORDER = APP_TABLES
DELETE_ORDER = (
    "assembly_components",
    "assembly_versions",
    "assemblies",
    "component_versions",
    "components",
    "field_definitions",
)
PROFILE_DELETE_ORDER = (
    "publisher_details",
    "publishers",
    "publisher_field_matches",
    "publisher_parties",
)
_AUTO_ID_TABLES = (
    "components", "component_versions", "assemblies", "assembly_versions",
    "assembly_components", "field_definitions", "publishers",
    "publisher_field_matches", "publisher_parties",
)


def _connect(database_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(database_path), timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _database_connection(database_path: str | Path):
    connection = _connect(database_path)
    try:
        yield connection
    finally:
        connection.close()


def _table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")')]


def _has_table(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def export_library_backup(
    database_path: str | Path,
    destination: str | Path,
    include_publisher_profiles: bool = False,
) -> dict:
    """Write a consistent JSON snapshot of all library records."""
    database_path, destination = Path(database_path), Path(destination)
    tables = APP_TABLES + (PROFILE_TABLES if include_publisher_profiles else ())
    with _database_connection(database_path) as connection:
        connection.execute("BEGIN")
        schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        payload_tables = {}
        counts = {}
        for table in tables:
            if not _has_table(connection, table):
                raise sqlite3.DatabaseError(f"The database is missing the {table} table.")
            columns = _table_columns(connection, table)
            rows = [
                list(row)
                for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid')
            ]
            payload_tables[table] = {"columns": columns, "rows": rows}
            counts[table] = len(rows)

    payload = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "schema_version": schema_version,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "includes_publisher_profiles": bool(include_publisher_profiles),
        "tables": payload_tables,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=destination.parent,
            prefix=destination.name + ".", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(destination)
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise
    record_backup_completed(database_path)
    return {
        "path": str(destination),
        "counts": counts,
        "includes_publisher_profiles": bool(include_publisher_profiles),
    }


def _read_backup(source: str | Path | Mapping) -> dict:
    if isinstance(source, Mapping):
        payload = dict(source)
    else:
        try:
            payload = json.loads(Path(source).read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read the backup file: {exc}") from None
    if not isinstance(payload, dict):
        raise ValueError("The backup root must be a JSON object.")
    if payload.get("format") != FORMAT:
        raise ValueError("This is not a Contract Builder library backup.")
    if payload.get("format_version") != FORMAT_VERSION:
        raise ValueError(
            f"This backup format version ({payload.get('format_version')}) is not supported."
        )
    if type(payload.get("schema_version")) is not int:
        raise ValueError("The backup does not contain a valid database schema version.")
    if not isinstance(payload.get("tables"), dict):
        raise ValueError("The backup does not contain its table data.")
    if type(payload.get("includes_publisher_profiles", False)) is not bool:
        raise ValueError("The publisher-profile option in the backup is malformed.")
    includes_profiles = payload.get("includes_publisher_profiles", False)
    expected = set(APP_TABLES + (PROFILE_TABLES if includes_profiles else ()))
    actual = set(payload["tables"])
    if actual != expected:
        missing, extra = sorted(expected - actual), sorted(actual - expected)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unexpected " + ", ".join(extra))
        raise ValueError("The backup table list is invalid (" + "; ".join(detail) + ").")
    for table, record in payload["tables"].items():
        if not isinstance(record, dict) or not isinstance(record.get("columns"), list) or not isinstance(record.get("rows"), list):
            raise ValueError(f"The backup data for {table} is malformed.")
        columns = record["columns"]
        if any(not isinstance(c, str) for c in columns) or len(columns) != len(set(columns)):
            raise ValueError(f"The backup column list for {table} is malformed.")
        for row in record["rows"]:
            if not isinstance(row, list) or len(row) != len(columns):
                raise ValueError(f"The backup contains a malformed row in {table}.")
    return payload


def _validated_payload(connection: sqlite3.Connection, source: str | Path | Mapping) -> dict:
    payload = _read_backup(source)
    current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if payload["schema_version"] != current_version:
        raise ValueError(
            f"This backup uses database schema {payload['schema_version']}, but this "
            f"installation uses schema {current_version}. Open it with a compatible app version."
        )
    for table, record in payload["tables"].items():
        if not _has_table(connection, table):
            raise ValueError(f"This database does not have the {table} table required by the backup.")
        actual = _table_columns(connection, table)
        if record["columns"] != actual:
            raise ValueError(f"The {table} table has a different structure from this backup.")
    return payload


def _rows(payload: dict, table: str) -> list[dict]:
    record = payload["tables"].get(table)
    if record is None:
        return []
    return [dict(zip(record["columns"], values)) for values in record["rows"]]


def _conflict_counts(connection: sqlite3.Connection, payload: dict, include_profiles: bool) -> dict:
    result = {}
    if "field_definitions" in payload["tables"]:
        result["field_definitions"] = sum(
            connection.execute(
                "SELECT 1 FROM field_definitions WHERE name_key=?", (row["name_key"],)
            ).fetchone() is not None
            for row in _rows(payload, "field_definitions")
        )
    if include_profiles and "publishers" in payload["tables"]:
        result["publishers"] = sum(
            connection.execute(
                "SELECT 1 FROM publishers WHERE publisher_name_key=?",
                (row["publisher_name_key"],),
            ).fetchone() is not None
            for row in _rows(payload, "publishers")
        )
        result["publisher_field_matches"] = sum(
            connection.execute(
                "SELECT 1 FROM publisher_field_matches WHERE field_name_key=?",
                (row["field_name_key"],),
            ).fetchone() is not None
            for row in _rows(payload, "publisher_field_matches")
        )
        result["publisher_parties"] = sum(
            connection.execute(
                "SELECT 1 FROM publisher_parties WHERE name_key=?", (row["name_key"],)
            ).fetchone() is not None
            for row in _rows(payload, "publisher_parties")
        )
    return result


def _summary(payload: dict, mode: str, include_profiles: bool, conflicts: dict) -> str:
    titles = {
        "components": "components",
        "component_versions": "saved wording versions",
        "assemblies": "assemblies",
        "assembly_versions": "assembly revisions",
        "assembly_components": "pinned assembly items",
        "field_definitions": "reusable field definitions",
        "publishers": "publisher profiles",
        "publisher_details": "saved publisher details",
        "publisher_field_matches": "publisher field matches",
        "publisher_parties": "named publisher parties",
    }
    rows = []
    for table, label in titles.items():
        if table not in payload["tables"] or (table in PROFILE_TABLES and not include_profiles):
            continue
        count = len(_rows(payload, table))
        if count:
            rows.append(f"• {count} {label}")
    if not rows:
        rows.append("• No records")
    if mode == "merge":
        skipped = sum(conflicts.values())
        rows.append(f"\nMerge keeps existing records when a name conflicts. "
                    f"{skipped} duplicate definition/profile names will be kept from this computer.")
    else:
        rows.append("\nReplace removes the current component library and replaces it with this backup.")
    if payload.get("includes_publisher_profiles") and not include_profiles:
        rows.append("Publisher profiles are in the file but will NOT be imported because the option is off.")
    elif include_profiles and payload.get("includes_publisher_profiles"):
        rows.append("Publisher profiles and contact details will also be imported.")
    else:
        rows.append("Publisher profiles are not part of this backup.")
    return ("This backup contains:\n" + "\n".join(rows))


def preview_library_import(
    database_path: str | Path,
    source: str | Path | Mapping,
    mode: str = "merge",
    include_publisher_profiles: bool = False,
) -> dict:
    """Describe an import without changing the database."""
    if mode not in {"merge", "replace"}:
        raise ValueError("Choose merge or replace.")
    payload = _read_backup(source)
    if include_publisher_profiles and not payload.get("includes_publisher_profiles"):
        include_publisher_profiles = False
    with _database_connection(database_path) as connection:
        payload = _validated_payload(connection, payload)
        conflicts = _conflict_counts(connection, payload, include_publisher_profiles)
    counts = {
        table: len(_rows(payload, table))
        for table in payload["tables"]
        if table not in PROFILE_TABLES or include_publisher_profiles
    }
    return {
        "mode": mode,
        "counts": counts,
        "conflicts": conflicts if mode == "merge" else {},
        "includes_publisher_profiles": bool(
            include_publisher_profiles and payload.get("includes_publisher_profiles")
        ),
        "summary": _summary(payload, mode, include_publisher_profiles, conflicts if mode == "merge" else {}),
    }


def _insert_row(connection: sqlite3.Connection, table: str, row: dict, overrides: dict | None = None) -> int:
    values = dict(row)
    values.update(overrides or {})
    values.pop("id", None)
    columns = list(values)
    cursor = connection.execute(
        f'INSERT INTO "{table}" ({", ".join(chr(34) + c + chr(34) for c in columns)}) '
        f'VALUES ({", ".join("?" for _ in columns)})',
        [values[column] for column in columns],
    )
    return int(cursor.lastrowid)


def _insert_preserving_id(connection: sqlite3.Connection, table: str, row: dict) -> None:
    columns = list(row)
    connection.execute(
        f'INSERT INTO "{table}" ({", ".join(chr(34) + c + chr(34) for c in columns)}) '
        f'VALUES ({", ".join("?" for _ in columns)})',
        [row[column] for column in columns],
    )


def _drop_triggers(connection: sqlite3.Connection, tables: set[str]) -> list[str]:
    rows = connection.execute(
        "SELECT name, sql, tbl_name FROM sqlite_master "
        "WHERE type='trigger' ORDER BY name"
    ).fetchall()
    selected = [row for row in rows if row["tbl_name"] in tables and row["sql"]]
    for row in selected:
        safe_name = row["name"].replace('"', '""')
        connection.execute(f'DROP TRIGGER "{safe_name}"')
    return [row["sql"] for row in selected]


def _reset_sequences(connection: sqlite3.Connection, tables: tuple[str, ...]) -> None:
    if not _has_table(connection, "sqlite_sequence"):
        return
    for table in tables:
        connection.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
        if _has_table(connection, table) and "id" in _table_columns(connection, table):
            maximum = connection.execute(f'SELECT COALESCE(MAX(id),0) FROM "{table}"').fetchone()[0]
            if maximum:
                connection.execute(
                    "INSERT INTO sqlite_sequence(name,seq) VALUES (?,?)", (table, maximum)
                )


def _replace(connection: sqlite3.Connection, payload: dict, include_profiles: bool) -> dict:
    tables = set(APP_TABLES)
    if include_profiles and payload.get("includes_publisher_profiles"):
        tables.update(PROFILE_TABLES)
    trigger_sql = _drop_triggers(connection, tables)
    for table in DELETE_ORDER:
        connection.execute(f'DELETE FROM "{table}"')
    if include_profiles and payload.get("includes_publisher_profiles"):
        for table in PROFILE_DELETE_ORDER:
            connection.execute(f'DELETE FROM "{table}"')
    inserted = {}
    for table in INSERT_ORDER:
        rows = _rows(payload, table)
        for row in rows:
            _insert_preserving_id(connection, table, row)
        inserted[table] = len(rows)
    if include_profiles and payload.get("includes_publisher_profiles"):
        for table in ("publishers", "publisher_field_matches", "publisher_parties", "publisher_details"):
            rows = _rows(payload, table)
            for row in rows:
                _insert_preserving_id(connection, table, row)
            inserted[table] = len(rows)
    for sql in trigger_sql:
        connection.execute(sql)
    sequence_tables = _AUTO_ID_TABLES if include_profiles and payload.get("includes_publisher_profiles") else tuple(
        table for table in _AUTO_ID_TABLES
        if table not in {"publishers", "publisher_field_matches", "publisher_parties"}
    )
    _reset_sequences(connection, sequence_tables)
    return {"inserted": inserted, "skipped": {}}


def _merge(connection: sqlite3.Connection, payload: dict, include_profiles: bool) -> dict:
    inserted = {}
    skipped = {}
    trigger_sql = _drop_triggers(connection, {"assembly_components"})
    try:
        component_ids = {}
        for row in _rows(payload, "components"):
            component_ids[row["id"]] = _insert_row(connection, "components", row)
        inserted["components"] = len(component_ids)

        version_ids = {}
        for row in _rows(payload, "component_versions"):
            version_ids[row["id"]] = _insert_row(
                connection, "component_versions", row,
                {"component_id": component_ids[row["component_id"]]},
            )
        inserted["component_versions"] = len(version_ids)

        assembly_ids = {}
        for row in _rows(payload, "assemblies"):
            assembly_ids[row["id"]] = _insert_row(connection, "assemblies", row)
        inserted["assemblies"] = len(assembly_ids)

        revision_ids = {}
        for row in _rows(payload, "assembly_versions"):
            revision_ids[row["id"]] = _insert_row(
                connection, "assembly_versions", row,
                {"assembly_id": assembly_ids[row["assembly_id"]]},
            )
        inserted["assembly_versions"] = len(revision_ids)

        assembly_items = 0
        for row in _rows(payload, "assembly_components"):
            _insert_row(connection, "assembly_components", row, {
                "assembly_version_id": revision_ids[row["assembly_version_id"]],
                "component_version_id": version_ids[row["component_version_id"]],
            })
            assembly_items += 1
        inserted["assembly_components"] = assembly_items

        definitions = 0
        definition_skips = 0
        for row in _rows(payload, "field_definitions"):
            exists = connection.execute(
                "SELECT 1 FROM field_definitions WHERE name_key=?", (row["name_key"],)
            ).fetchone()
            if exists:
                definition_skips += 1
            else:
                _insert_row(connection, "field_definitions", row)
                definitions += 1
        inserted["field_definitions"] = definitions
        if definition_skips:
            skipped["field_definitions"] = definition_skips

        if include_profiles and payload.get("includes_publisher_profiles"):
            profile_ids = {}
            publisher_skips = 0
            for row in _rows(payload, "publishers"):
                existing = connection.execute(
                    "SELECT id FROM publishers WHERE publisher_name_key=?",
                    (row["publisher_name_key"],),
                ).fetchone()
                if existing:
                    profile_ids[row["id"]] = int(existing["id"])
                    publisher_skips += 1
                else:
                    profile_ids[row["id"]] = _insert_row(connection, "publishers", row)
            inserted["publishers"] = len(profile_ids) - publisher_skips
            if publisher_skips:
                skipped["publishers"] = publisher_skips

            details = 0
            detail_skips = 0
            for row in _rows(payload, "publisher_details"):
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO publisher_details "
                    "(publisher_id, detail_key, detail_name, value) VALUES (?, ?, ?, ?)",
                    (profile_ids[row["publisher_id"]], row["detail_key"],
                     row["detail_name"], row["value"]),
                )
                if cursor.rowcount:
                    details += 1
                else:
                    detail_skips += 1
            inserted["publisher_details"] = details
            if detail_skips:
                skipped["publisher_details"] = detail_skips

            for table, key in (("publisher_field_matches", "field_name_key"),
                               ("publisher_parties", "name_key")):
                count = skip = 0
                for row in _rows(payload, table):
                    if connection.execute(
                        f'SELECT 1 FROM "{table}" WHERE "{key}"=?', (row[key],)
                    ).fetchone():
                        skip += 1
                    else:
                        _insert_row(connection, table, row)
                        count += 1
                inserted[table] = count
                if skip:
                    skipped[table] = skip
    finally:
        for sql in trigger_sql:
            connection.execute(sql)
    return {"inserted": inserted, "skipped": skipped}


def import_library_backup(
    database_path: str | Path,
    source: str | Path | Mapping,
    mode: str = "merge",
    include_publisher_profiles: bool = False,
) -> dict:
    """Import a validated backup transactionally, merging or replacing library data."""
    preview = preview_library_import(
        database_path, source, mode=mode,
        include_publisher_profiles=include_publisher_profiles,
    )
    payload = _read_backup(source)
    profiles = bool(include_publisher_profiles and payload.get("includes_publisher_profiles"))
    with _database_connection(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        payload = _validated_payload(connection, payload)
        try:
            result = (
                _replace(connection, payload, profiles)
                if mode == "replace" else _merge(connection, payload, profiles)
            )
            errors = connection.execute("PRAGMA foreign_key_check").fetchall()
            if errors:
                raise sqlite3.IntegrityError("The imported records contain broken links.")
            unfinished = connection.execute(
                """
                SELECT assembly_versions.id
                FROM assembly_versions
                WHERE assembly_versions.finalized = 1
                  AND NOT EXISTS (
                      SELECT 1 FROM assembly_components
                      WHERE assembly_components.assembly_version_id = assembly_versions.id
                        AND assembly_components.included = 1
                  )
                LIMIT 1
                """
            ).fetchone()
            if unfinished:
                raise sqlite3.IntegrityError(
                    "The imported data contains a finalized assembly with no included components."
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    result.update({
        "mode": mode,
        "summary": preview["summary"],
        "includes_publisher_profiles": profiles,
    })
    return result


def reminder_settings_path(database_path: str | Path) -> Path:
    path = Path(database_path)
    return path.with_name(path.stem + ".backup-reminder.json")


def get_backup_reminder_settings(database_path: str | Path) -> dict:
    """Reminder is disabled by default and kept outside the transferable library."""
    path = reminder_settings_path(database_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    return {
        "enabled": bool(data.get("enabled", False)),
        "last_backup": data.get("last_backup"),
    }


def set_backup_reminder_enabled(database_path: str | Path, enabled: bool) -> None:
    path = reminder_settings_path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = get_backup_reminder_settings(database_path)
    data = {"enabled": bool(enabled), "last_backup": current["last_backup"]}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def record_backup_completed(database_path: str | Path) -> None:
    path = reminder_settings_path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = get_backup_reminder_settings(database_path)
    current["last_backup"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


def backup_reminder_due(
    database_path: str | Path,
    now: datetime | None = None,
    interval_days: int = 28,
) -> bool:
    settings = get_backup_reminder_settings(database_path)
    if not settings["enabled"]:
        return False
    last = settings.get("last_backup")
    if not last:
        return True
    try:
        previous = datetime.fromisoformat(last)
        if previous.tzinfo is None:
            previous = previous.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return True
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current - previous >= timedelta(days=max(1, int(interval_days)))


def safe_markdown_filename(name: str, identifier: int | str) -> str:
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", str(name)).strip(" .-")
    stem = re.sub(r"\s+", " ", stem)[:100] or "Component"
    return f"{stem} [{identifier}].md"
