"""Pure helpers for assemblies: no windows, so tests and other modules can use them freely."""
from __future__ import annotations

import difflib
import hashlib
from pathlib import Path
from typing import Mapping, Sequence

from component_preview import render_markdown_preview


def included_component_markdown(revision: Mapping[str, object]) -> list[str]:
    """Return included Markdown sources in saved order, without joining them.

    Keeping each component as a separate source is important: field protection
    and Markdown parsing must happen per component so brace fragments at a
    component boundary cannot accidentally form a field.
    """
    components = revision.get("components", ())
    if not isinstance(components, Sequence) or isinstance(components, (str, bytes)):
        raise TypeError("A saved assembly must contain an ordered component list.")
    return [
        str(component["markdown"])
        for component in components
        if bool(component.get("included", True))
    ]


def preview_segments_for_components(
    components: Sequence[Mapping[str, object]],
    preview_values: Mapping[str, object] | None = None,
):
    """Render an ordered preview, optionally resolving one field's alternatives."""
    segments = []
    visible = 0
    for component in components:
        if not bool(component.get("included", True)):
            continue
        if visible:
            segments.append(("\n\n", ()))
        label = str(component.get("component_name") or "Component")
        number = component.get("component_version_number")
        if number is not None:
            label += f" · version {number}"
        segments.append((label + "\n", ("component_label",)))
        segments.extend(render_markdown_preview(
            str(component.get("markdown") or ""),
            list(component.get("paragraph_styles") or ()),
            preview_values=preview_values,
        ))
        visible += 1
    return segments


def revision_preview_segments(revision: Mapping[str, object], has_updates: bool = False):
    """The preview of one saved revision, as the builder shows it (T-063).

    Only the pinned versions are shown, never newer wording; components left out
    of the recipe are absent. ``has_updates`` adds a plain note that newer
    wording exists, so the preview is not mistaken for the latest text.
    """
    segments = []
    if has_updates:
        segments.append((
            "Newer wording is available for some components. This preview shows the "
            "versions this revision is pinned to.\n\n", ("source_text",),
        ))
    body = preview_segments_for_components(list(revision.get("components") or ()))
    if not body:
        body = [("No components are included in this revision.", ("source_text",))]
    return segments + body


def shell_file_sha256(path: str | Path) -> str:
    """Hash a shell incrementally so even a large file is not read at once."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compose_assembly_template(shell_path, components, output_path):
    """Compose a temporary DOCX, then discover its unique fields with core.Template."""
    included = list(components)
    if not included:
        raise ValueError("Include at least one component before generating a document.")
    from docx_compose import compose_document
    import core

    composition = compose_document(shell_path, included, output_path)
    return core.Template(output_path), composition


def version_diff_lines(old_markdown: str, new_markdown: str) -> list[str]:
    """Return a readable unified diff for pinned and proposed component wording."""
    return list(difflib.unified_diff(
        str(old_markdown).splitlines(),
        str(new_markdown).splitlines(),
        fromfile="Pinned wording",
        tofile="Proposed wording",
        lineterm="",
    ))


def update_component_items(items, selections):
    """Apply only explicit, validated version selections to an ordered recipe."""
    updated = []
    for original in items:
        item = dict(original)
        key = int(item["key"])
        selected = selections.get(key)
        if selected is not None:
            selected_component_id = selected.get("component_id", item["component_id"])
            if int(selected_component_id) != int(item["component_id"]):
                raise ValueError("A selected version belongs to a different component.")
            if int(selected["number"]) <= int(item["component_version_number"]):
                raise ValueError("Choose a version newer than the currently pinned wording.")
            item.update(
                component_version_id=int(selected["id"]),
                component_version_number=int(selected["number"]),
                markdown=str(selected["markdown"]),
                paragraph_styles=list(selected.get("paragraph_styles") or []),
            )
        updated.append(item)
    return updated
