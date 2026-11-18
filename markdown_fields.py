"""Protect ContractBuilder fields while parsing Markdown.

Call protect_fields separately for each component, parse that component, then
restore_fields on its token tree before rendering. Do not concatenate raw
component source before protection: component boundaries are semantic.
"""
from __future__ import annotations

from typing import Iterable, Mapping

from core import TOKEN


def protect_fields(source: str) -> tuple[str, dict[str, str]]:
    """Replace each complete {{...}} span with collision-free plain text.

    The placeholder contains only letters and digits, so Markdown block and
    inline rules (notably table pipes and emphasis delimiters) cannot consume
    field syntax. The returned mapping restores the exact original spelling.
    """
    if not isinstance(source, str):
        raise TypeError("Markdown component source must be text")

    prefix = "CONTRACTBUILDERFIELD"
    while prefix in source:
        prefix += "X"

    replacements: dict[str, str] = {}
    pieces: list[str] = []
    cursor = 0
    for index, match in enumerate(TOKEN.finditer(source)):
        placeholder = f"{prefix}{index:06d}END"
        pieces.append(source[cursor:match.start()])
        pieces.append(placeholder)
        replacements[placeholder] = match.group(0)
        cursor = match.end()
    pieces.append(source[cursor:])
    return "".join(pieces), replacements


def restore_fields(tokens: Iterable[object], replacements: Mapping[str, str]) -> None:
    """Restore placeholders in Markdown token content, including inline children.

    Both block-level inline source and its parsed child tokens are restored.
    This keeps the field literal available to a Word renderer as ordinary text.
    """
    if not replacements:
        return

    def restore(token: object) -> None:
        content = getattr(token, "content", None)
        if isinstance(content, str):
            for placeholder, original in replacements.items():
                content = content.replace(placeholder, original)
            token.content = content

        for child in getattr(token, "children", None) or ():
            restore(child)

    for token in tokens:
        restore(token)
