"""Which saved-publisher detail fills which field, including parties (T-046-C, T-046-D).

Pure Python, no UI. A field can be filled from:

* a publisher column, by the built-in names or the user's matches (T-046-A);
* an extra publisher detail the user defined (such as Publisher type); or
* the same two things for a **party**, a named publisher in a contract with
  more than one ("Publisher One", "Publisher Two"). A field named for a party
  followed by a detail ("Publisher One's Address", "Publisher Two Contact") is
  matched automatically, without listing every combined name by hand.

Apostrophes and capitals do not matter, as elsewhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from publisher_profiles import (
    _FIELD_ALIASES, _normalize_field_name, publisher_column_for_field, values_for_template,
)


@dataclass(frozen=True)
class Resolution:
    """Where a field's value comes from."""

    party: Optional[str]          # the party's name, or None for the single-publisher form
    column: Optional[str] = None  # a publisher column ("city", "formatted_address", ...)
    detail: Optional[str] = None  # an extra detail's name ("Publisher type")


def _column_for_party_rest(rest: str) -> Optional[str]:
    """The column named by what follows a party name: address, state, contact..."""
    if rest in ("", "name"):
        return "publisher_name"
    for candidate in (rest, "publisher " + rest, "contact " + rest):
        column = _FIELD_ALIASES.get(candidate)
        if column:
            return column
    return None


def resolve_field(
    field_name: str,
    *,
    parties: Sequence[Mapping[str, object]] = (),
    user_matches: Mapping[str, str] | None = None,
    detail_links: Mapping[str, str] | None = None,
) -> Optional[Resolution]:
    """Work out what fills ``field_name``; None when nothing does."""
    key = _normalize_field_name(field_name)
    links = detail_links or {}
    # Longest party name first, so "Publisher Two" is never mistaken for "Publisher".
    for party in sorted(parties, key=lambda p: -len(str(p["name_key"]))):
        party_key = str(party["name_key"])
        role_key = _normalize_field_name(str(party.get("role") or ""))
        if key == party_key or (role_key and key == f"{party_key} {role_key}"):
            return Resolution(str(party["name"]), column="publisher_name")
        if key.startswith(party_key + " "):
            rest = key[len(party_key) + 1:]
            if role_key and rest == role_key:
                return Resolution(str(party["name"]), column="publisher_name")
            if rest in links:
                return Resolution(str(party["name"]), detail=links[rest])
            column = _column_for_party_rest(rest)
            if column:
                return Resolution(str(party["name"]), column=column)
    column = publisher_column_for_field(field_name, user_matches)
    if column:
        return Resolution(None, column=column)
    if key in links:
        return Resolution(None, detail=links[key])
    return None


def resolutions_for(
    field_names: Sequence[str], **kwargs
) -> dict[str, Resolution]:
    """{field name: Resolution} for every field something can fill."""
    found = {}
    for name in field_names:
        resolution = resolve_field(name, **kwargs)
        if resolution is not None:
            found[name] = resolution
    return found


def parties_in(resolutions: Mapping[str, Resolution]) -> list[str]:
    """The party names that appear, in the order their first field appears."""
    seen = []
    for resolution in resolutions.values():
        if resolution.party and resolution.party not in seen:
            seen.append(resolution.party)
    return seen


@dataclass
class FillResult:
    values: dict           # field name -> text to put in the form
    no_value: list         # [(field name, what is missing)] the profile has nothing for


def fill_values(
    profile: Mapping[str, object],
    resolutions: Mapping[str, Resolution],
    party: Optional[str],
    only_field: Optional[str] = None,
) -> FillResult:
    """Values from one saved publisher for the fields of one party (or of no party)."""
    details = {
        _normalize_field_name(name): value
        for name, value in (profile.get("details") or {}).items()
    }
    values: dict = {}
    no_value: list = []
    for name, resolution in resolutions.items():
        if resolution.party != party or (only_field and name != only_field):
            continue
        if resolution.detail is not None:
            value = details.get(_normalize_field_name(resolution.detail), "")
            if str(value).strip():
                values[name] = str(value).strip()
            else:
                no_value.append((name, resolution.detail))
            continue
        filled = values_for_template(profile, [name], {name: resolution.column})
        if filled:
            values.update(filled)
    return FillResult(values, no_value)
