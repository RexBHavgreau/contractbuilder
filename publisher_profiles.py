"""Local SQLite storage for reusable publisher profiles.

The database is kept in the user's application-data directory, not beside the
executable or in the source repository, so application updates do not replace it.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sqlite3
import sys
from typing import Iterator, Mapping, Sequence


PROFILE_FIELDS = (
    "publisher_name",
    "contact_name",
    "contact_title",
    "contact_email",
    "contact_phone",
    "website",
    "address_line1",
    "address_line2",
    "city",
    "region",
    "postal_code",
    "country",
    "notes",
)

_FIELD_ALIASES = {
    "international publisher name": "publisher_name",
    "publisher name": "publisher_name",
    "international publisher": "publisher_name",
    "publisher": "publisher_name",
    "international publisher contact": "contact_name",
    "international publisher contact name": "contact_name",
    "international publisher contact person": "contact_name",
    "publisher contact": "contact_name",
    "publisher contact person": "contact_name",
    "contact person": "contact_name",
    "contact name": "contact_name",
    "international publisher contact title": "contact_title",
    "publisher contact title": "contact_title",
    "contact title": "contact_title",
    "international publisher email": "contact_email",
    "international publisher contact email": "contact_email",
    "publisher email": "contact_email",
    "contact email": "contact_email",
    "email": "contact_email",
    "international publisher phone": "contact_phone",
    "international publisher contact phone": "contact_phone",
    "publisher phone": "contact_phone",
    "contact phone": "contact_phone",
    "phone": "contact_phone",
    "international publisher website": "website",
    "publisher website": "website",
    "website": "website",
    "international publisher address": "formatted_address",
    "international publisher mailing address": "formatted_address",
    "publisher address": "formatted_address",
    "mailing address": "formatted_address",
    "address": "formatted_address",
    "international publisher address line 1": "address_line1",
    "publisher address line 1": "address_line1",
    "address line 1": "address_line1",
    "international publisher address line 2": "address_line2",
    "publisher address line 2": "address_line2",
    "address line 2": "address_line2",
    "international publisher city": "city",
    "publisher city": "city",
    "city": "city",
    "international publisher state": "region",
    "international publisher province": "region",
    "publisher state": "region",
    "publisher province": "region",
    "state province": "region",
    "state": "region",
    "province": "region",
    "international publisher postal code": "postal_code",
    "international publisher zip code": "postal_code",
    "publisher postal code": "postal_code",
    "postal code": "postal_code",
    "zip code": "postal_code",
    "international publisher country": "country",
    "publisher country": "country",
    "country": "country",
}


def default_database_path() -> Path:
    """Return a per-user, OS-appropriate location for the profile database."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "TMAI Contract Builder" / "publisher_profiles.sqlite3"


def _normalize_field_name(value: str) -> str:
    value = re.sub(r"['’]s\b", "", str(value).casefold())
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def format_address(profile: Mapping[str, object]) -> str:
    """Format saved address components as a conventional multiline postal address."""
    lines = [
        str(profile.get("address_line1") or "").strip(),
        str(profile.get("address_line2") or "").strip(),
    ]
    lines = [line for line in lines if line]
    city = str(profile.get("city") or "").strip()
    region = str(profile.get("region") or "").strip()
    postal_code = str(profile.get("postal_code") or "").strip()
    locality = ", ".join(part for part in (city, region) if part)
    if postal_code:
        locality = f"{locality} {postal_code}".strip()
    if locality:
        lines.append(locality)
    country = str(profile.get("country") or "").strip()
    if country:
        lines.append(country)
    return "\n".join(lines)


def values_for_template(
    profile: Mapping[str, object], field_names: Sequence[str]
) -> dict[str, str]:
    """Return non-empty publisher values keyed by the template's exact field names.

    A small alias table connects common placeholder labels to profile properties.
    Unrecognized fields are deliberately left untouched for the user to complete.
    """
    result: dict[str, str] = {}
    for field_name in field_names:
        property_name = _FIELD_ALIASES.get(_normalize_field_name(field_name))
        if not property_name:
            continue
        value = format_address(profile) if property_name == "formatted_address" else profile.get(property_name)
        if value is not None and str(value).strip():
            result[field_name] = str(value).strip()
    return result


class PublisherProfileStore:
    """CRUD access to publisher profiles in a local SQLite database."""

    def __init__(self, path: str | Path | None = None):
        use_default_path = path is None
        self.path = Path(path) if path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if use_default_path and os.name != "nt":
            # Publisher contact details are personal/business data; keep the
            # per-user database directory private on POSIX systems.
            self.path.parent.chmod(0o700)
        self._initialize()
        if use_default_path and os.name != "nt":
            self.path.chmod(0o600)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS publishers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    publisher_name TEXT NOT NULL,
                    publisher_name_key TEXT NOT NULL UNIQUE,
                    contact_name TEXT NOT NULL DEFAULT '',
                    contact_title TEXT NOT NULL DEFAULT '',
                    contact_email TEXT NOT NULL DEFAULT '',
                    contact_phone TEXT NOT NULL DEFAULT '',
                    website TEXT NOT NULL DEFAULT '',
                    address_line1 TEXT NOT NULL DEFAULT '',
                    address_line2 TEXT NOT NULL DEFAULT '',
                    city TEXT NOT NULL DEFAULT '',
                    region TEXT NOT NULL DEFAULT '',
                    postal_code TEXT NOT NULL DEFAULT '',
                    country TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_publishers_name "
                "ON publishers(publisher_name_key)"
            )

    def list_profiles(self) -> list[dict[str, object]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM publishers ORDER BY publisher_name COLLATE NOCASE"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_profile(self, profile_id: int) -> dict[str, object] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM publishers WHERE id = ?", (int(profile_id),)
            ).fetchone()
            return dict(row) if row else None

    def save_profile(
        self, profile: Mapping[str, object], profile_id: int | None = None
    ) -> int:
        """Insert a profile or update the requested profile; return its database ID."""
        name = str(profile.get("publisher_name") or "").strip()
        if not name:
            raise ValueError("Enter a publisher name.")

        values = {field: str(profile.get(field) or "").strip() for field in PROFILE_FIELDS}
        values["publisher_name"] = name
        # Python's casefold handles international scripts more consistently than
        # SQLite's built-in NOCASE collation, which is limited to ASCII letters.
        name_key = " ".join(name.casefold().split())
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            with self._connection() as connection:
                if profile_id is None:
                    columns = ", ".join((*PROFILE_FIELDS, "publisher_name_key", "created_at", "updated_at"))
                    placeholders = ", ".join("?" for _ in range(len(PROFILE_FIELDS) + 3))
                    cursor = connection.execute(
                        f"INSERT INTO publishers ({columns}) VALUES ({placeholders})",
                        (*[values[field] for field in PROFILE_FIELDS], name_key, now, now),
                    )
                    return int(cursor.lastrowid)
                assignments = ", ".join(f"{field} = ?" for field in PROFILE_FIELDS)
                cursor = connection.execute(
                    f"UPDATE publishers SET {assignments}, publisher_name_key = ?, "
                    "updated_at = ? WHERE id = ?",
                    (*[values[field] for field in PROFILE_FIELDS], name_key, now, int(profile_id)),
                )
                if cursor.rowcount == 0:
                    raise ValueError("That publisher profile no longer exists.")
                return int(profile_id)
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "A publisher with that name already exists. Use a distinct name or edit the existing profile."
            ) from exc

    def delete_profile(self, profile_id: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM publishers WHERE id = ?", (int(profile_id),)
            )
            return cursor.rowcount > 0
