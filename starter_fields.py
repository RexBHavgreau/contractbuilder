"""An optional, editable starting list of fields (T-043-E).

The app carries no built-in contract types or field schemas (decision of
2026-11-17). This is only a short list a user may *copy into their own field
definitions* with one click, after which every field is theirs: they can edit or
archive it like any field they made. A field the user archived is never added
again, and one that already exists is left alone.
"""
from __future__ import annotations

from typing import Sequence

import core

STARTER_FIELDS = (
    {
        "name": "Works", "group": "Your fields", "default_format": "list",
        "description": "The titles this contract covers, one per line.",
    },
    {
        "name": "Publisher type", "group": "Publisher", "default_format": "choice",
        "allowed_values": ("Non-profit", "Sole proprietor", "Company"),
        "publisher_detail_name": "Publisher type",
        "description": "What kind of organization the publisher is; used to choose alternative wording.",
    },
    {
        "name": "Territory", "group": "Your fields", "default_format": "",
        "description": "Where the rights apply, such as a country or a region.",
    },
    {
        "name": "Term in years", "group": "Your fields", "default_format": "number",
        "description": "How long the agreement lasts, in whole years.",
    },
    {
        "name": "Effective Date", "group": "Your fields", "default_format": "date",
        "description": "The day the agreement takes effect.",
    },
)


def starter_names() -> list[str]:
    return [item["name"] for item in STARTER_FIELDS]


def add_starter_fields(library, fields: Sequence[dict] = STARTER_FIELDS):
    """Copy the starter fields into the user's definitions.

    Returns ``(added, skipped)`` lists of names. A name that exists in any
    state, archived included, is skipped, so the user's choices stick.
    """
    existing = {
        core.key(definition["name"])
        for definition in library.list_field_definitions(include_archived=True)
    }
    added, skipped = [], []
    for item in fields:
        if core.key(item["name"]) in existing:
            skipped.append(item["name"])
            continue
        library.add_field_definition(
            item["name"],
            description=item.get("description", ""),
            group=item.get("group", "Your fields"),
            default_format=item.get("default_format", ""),
            allowed_values=list(item.get("allowed_values", ())),
            publisher_detail_name=item.get("publisher_detail_name"),
        )
        added.append(item["name"])
    return added, skipped
