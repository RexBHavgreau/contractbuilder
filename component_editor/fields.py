"""Pure field-placeholder helpers: build, check and list field names. No Tkinter.

The field picker and creator of T-043 belong in field_dialog.py; the rules
they use belong here.
"""
from __future__ import annotations

import re
import sqlite3

import core
from publisher_profiles import PROFILE_FIELDS


_PROFILE_FIELD_NAMES = {
    "publisher_name": "Publisher Name",
    "contact_name": "Contact Name",
    "contact_title": "Contact Title",
    "contact_email": "Contact Email",
    "contact_phone": "Contact Phone",
    "website": "Website",
    "address_line1": "Address Line 1",
    "address_line2": "Address Line 2",
    "city": "City",
    "region": "State / Province / Region",
    "postal_code": "Postal Code",
    "country": "Country",
    "notes": "Publisher Notes",
}

_FIELD_FORMATS = (
    ("Plain text", ""),
    ("Uppercase", "upper"),
    ("Long text", "long"),
    ("Date", "date"),
    ("Formal date", "date-formal"),
    ("Short date", "date-short"),
    ("Money", "money"),
    ("Money in words", "money-words"),
    ("Whole dollars", "money-whole"),
    ("Number", "number"),
    ("Number in words", "number-words"),
    ("List", "list"),
    ("Choice", "choice"),
    ("Singular or plural", "plural"),
)


def make_field_placeholder(name: str, format_name: str = "", options: str = "") -> str:
    """Build a field using the core engine's own field parser and format aliases."""
    clean_name = core.tidy_name(name or "")
    if not clean_name:
        raise ValueError("Choose or enter a field name.")
    expression = clean_name
    if format_name:
        expression += " | " + str(format_name).strip()
        if format_name in {"choice", "plural"}:
            clean_options = str(options or "").strip()
            if not clean_options:
                if format_name == "choice":
                    raise ValueError("A choice field needs at least one option.")
                raise ValueError("A singular-or-plural field needs two wordings.")
            expression += ": " + clean_options
    parsed_name, parsed_format, parsed_options = core.parse_field(expression)
    if not parsed_name:
        raise ValueError("The field name is empty. Enter a name before inserting it.")
    if format_name and parsed_format != format_name:
        raise ValueError("That field format is not supported by ContractBuilder.")
    if parsed_format == "plural" and len(parsed_options) != 2:
        raise ValueError("A singular-or-plural field needs two wordings, such as item, items.")
    if parsed_format == "choice" and not parsed_options:
        raise ValueError("A choice field needs at least one option.")
    placeholder = "{{" + expression + "}}"
    if core.TOKEN.fullmatch(placeholder) is None:
        raise ValueError("That field could not be read. Check its name and format.")
    return placeholder


def malformed_field_message(markdown: str) -> str | None:
    """Return a plain-English warning for broken or incomplete field placeholders."""
    source = str(markdown or "")
    matches = list(core.TOKEN.finditer(source))
    valid = [(match.start(), match.end()) for match in matches]
    for match in re.finditer(r"\{\{|\}\}", source):
        if not any(start <= match.start() and match.end() <= end for start, end in valid):
            line = source.count("\n", 0, match.start()) + 1
            return (
                f"Check the field placeholder on line {line}: its double braces do not "
                "match. A field should look like {{Field Name}}."
            )
    for match in matches:
        kind, argument = core.classify(match.group(1))
        if kind != "field":
            continue
        name, format_name, options = core.parse_field(argument)
        line = source.count("\n", 0, match.start()) + 1
        if not name:
            return f"Check the field placeholder on line {line}: add a field name between the braces."
        if format_name == "choice" and not options:
            return f"Check the field on line {line}: a choice field needs at least one option after 'choice:'."
        if format_name == "plural" and len(options) != 2:
            return f"Check the field on line {line}: a singular-or-plural field needs exactly two wordings after 'plural:'."
    return None


def available_field_names(library) -> list[str]:
    """Publisher-profile fields plus every field already used in saved wording."""
    names = {}
    for field in PROFILE_FIELDS:
        label = _PROFILE_FIELD_NAMES.get(
            field, field.replace("_", " ").title()
        )
        names.setdefault(core.key(label), label)
    try:
        for component in library.list_components(include_archived=True):
            for version in library.list_component_versions(component["id"]):
                for match in core.TOKEN.finditer(version["markdown"]):
                    kind, argument = core.classify(match.group(1))
                    if kind == "field":
                        name, _format_name, _options = core.parse_field(argument)
                        if name:
                            names.setdefault(core.key(name), name)
    except (OSError, sqlite3.Error):
        pass
    return sorted(names.values(), key=str.casefold)
