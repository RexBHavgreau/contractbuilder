"""Validate a Word document shell without changing the source package.

A shell supplies the styles, numbering definitions, table style, and final
section properties used by Markdown-to-Word composition. Findings are plain
English and carry stable codes for callers and tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple, Union
import zipfile

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


@dataclass(frozen=True)
class ShellFinding:
    """One actionable shell-check result."""

    code: str
    severity: str  # "error" stops generation; "warning" permits a fallback.
    message: str


@dataclass(frozen=True)
class ShellCheckResult:
    """The complete, read-only result of checking a shell."""

    path: Path
    findings: Tuple[ShellFinding, ...]
    style_fallbacks: Mapping[str, Optional[str]]

    @property
    def can_generate(self) -> bool:
        """Whether generation may continue after the user reviews warnings."""
        return not any(item.severity == "error" for item in self.findings)

    @property
    def errors(self) -> Tuple[ShellFinding, ...]:
        return tuple(item for item in self.findings if item.severity == "error")

    @property
    def warnings(self) -> Tuple[ShellFinding, ...]:
        return tuple(item for item in self.findings if item.severity == "warning")


def _tag(local_name: str) -> str:
    return "{%s}%s" % (W_NS, local_name)


def _parse_member(package: zipfile.ZipFile, name: str):
    try:
        parser = etree.XMLParser(
            resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
        )
        return etree.fromstring(package.read(name), parser)
    except (KeyError, etree.XMLSyntaxError, ValueError) as exc:
        raise ValueError("The Word file is missing or has an unreadable %s part." % name) from exc


def _style_ids(root) -> Dict[str, str]:
    """Return styleId -> type for styles explicitly present in styles.xml."""
    result = {}
    if root is None:
        return result
    for style in root.findall("w:style", NS):
        style_id = style.get(_tag("styleId"))
        style_type = style.get(_tag("type"))
        if style_id and style_type:
            result[style_id] = style_type
    return result


def _fallback_for(style_id: str, styles: Mapping[str, str]) -> Optional[str]:
    """Choose a documented, predictable fallback for a missing style."""
    if style_id == "Normal":
        return None  # Leave the style unset; Word applies its default.
    if style_id in ("Heading1", "Heading2", "Heading3"):
        level = int(style_id[-1])
        for candidate_level in range(level - 1, 0, -1):
            candidate = "Heading%d" % candidate_level
            if styles.get(candidate) == "paragraph":
                return candidate
        return "Normal" if styles.get("Normal") == "paragraph" else None
    if style_id == "TableGrid":
        return "TableNormal" if styles.get("TableNormal") == "table" else None
    if style_id in ("ListParagraph", "ListBullet", "ListNumber"):
        if styles.get("ListParagraph") == "paragraph":
            return "ListParagraph"
        return "Normal" if styles.get("Normal") == "paragraph" else None
    return None


def _check_numbering(root) -> Tuple[bool, bool]:
    """Return (has_three_level_decimal_outline, has_bullet_definition)."""
    if root is None:
        return False, False
    abstract_ids = {
        item.get(_tag("abstractNumId"))
        for item in root.findall("w:abstractNum", NS)
        if item.get(_tag("abstractNumId")) is not None
    }
    # An abstract definition without a w:num instance cannot be selected.
    used_ids = {
        item.get(_tag("val"))
        for item in root.findall("w:num/w:abstractNumId", NS)
        if item.get(_tag("val")) is not None
    }
    active_ids = abstract_ids & used_ids
    has_decimal_outline = False
    has_bullet = False
    for abstract in root.findall("w:abstractNum", NS):
        if abstract.get(_tag("abstractNumId")) not in active_ids:
            continue
        levels = {}
        for level in abstract.findall("w:lvl", NS):
            raw_level = level.get(_tag("ilvl"))
            if raw_level is None or not raw_level.isdigit():
                continue
            fmt = level.find("w:numFmt", NS)
            text = level.find("w:lvlText", NS)
            levels[int(raw_level)] = (
                fmt.get(_tag("val")) if fmt is not None else None,
                text.get(_tag("val")) if text is not None else None,
            )
            if fmt is not None and fmt.get(_tag("val")) == "bullet":
                has_bullet = True
        multi_level = abstract.find("w:multiLevelType", NS)
        if multi_level is None or multi_level.get(_tag("val")) not in ("multilevel", "hybridMultilevel"):
            continue
        expected = {
            0: ("decimal", "%1."),
            1: ("decimal", "%1.%2"),
            2: ("decimal", "%1.%2.%3"),
        }
        if all(levels.get(level) == value for level, value in expected.items()):
            has_decimal_outline = True
    return has_decimal_outline, has_bullet


def check_shell(path: Union[str, Path]) -> ShellCheckResult:
    """Check a DOCX shell read-only and return plain-English findings.

    A missing/corrupt document or missing final section properties stops
    generation. Missing styles and numbering features are warnings because
    callers can apply the explicit fallbacks in style_fallbacks.
    """
    shell_path = Path(path)
    findings = []
    fallbacks: Dict[str, Optional[str]] = {}
    if not shell_path.is_file():
        return ShellCheckResult(
            shell_path,
            (ShellFinding("shell.not_found", "error",
                          "The selected shell file could not be found."),),
            fallbacks,
        )
    try:
        with zipfile.ZipFile(str(shell_path), "r") as package:
            names = set(package.namelist())
            if "[Content_Types].xml" not in names:
                raise ValueError("The file is not a valid Word document package.")
            document = _parse_member(package, "word/document.xml")
            styles = _parse_member(package, "word/styles.xml") if "word/styles.xml" in names else None
            numbering = _parse_member(package, "word/numbering.xml") if "word/numbering.xml" in names else None
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
        return ShellCheckResult(
            shell_path,
            (ShellFinding("shell.unreadable", "error",
                          "This file cannot be used as a Word shell: %s" % exc),),
            fallbacks,
        )

    body = document.find("w:body", NS)
    if body is None:
        findings.append(ShellFinding(
            "shell.no_body", "error",
            "This Word file has no document body, so it cannot be used as a shell.",
        ))
        return ShellCheckResult(shell_path, tuple(findings), fallbacks)

    # The final section properties must be the final body child. A sectPr
    # inside paragraph properties marks a section break, not the document's
    # final section, and cannot replace this required body-level element.
    children = list(body)
    final_sect = children[-1] if children and children[-1].tag == _tag("sectPr") else None
    if final_sect is None:
        findings.append(ShellFinding(
            "shell.no_final_section", "error",
            "This shell has no final section properties. Open it in Word, set its page layout, and save it again.",
        ))
    else:
        if final_sect.find("w:pgSz", NS) is None:
            findings.append(ShellFinding(
                "shell.no_page_size", "warning",
                "This shell does not specify a page size. Word's default page size will be used.",
            ))
        if final_sect.find("w:pgMar", NS) is None:
            findings.append(ShellFinding(
                "shell.no_page_margins", "warning",
                "This shell does not specify page margins. Word's default margins will be used.",
            ))

    styles_by_id = _style_ids(styles)
    required = {
        "Normal": "paragraph", "Heading1": "paragraph",
        "Heading2": "paragraph", "Heading3": "paragraph",
        "ListParagraph": "paragraph", "ListBullet": "paragraph",
        "ListNumber": "paragraph", "TableGrid": "table",
    }
    display_names = {
        "Normal": "Normal", "Heading1": "Heading 1",
        "Heading2": "Heading 2", "Heading3": "Heading 3",
        "ListParagraph": "List Paragraph", "ListBullet": "List Bullet",
        "ListNumber": "List Number", "TableGrid": "Table Grid",
    }
    for style_id, expected_type in required.items():
        actual_type = styles_by_id.get(style_id)
        if actual_type == expected_type:
            continue
        fallback = _fallback_for(style_id, styles_by_id)
        fallbacks[style_id] = fallback
        if actual_type is not None:
            message = (
                "This shell has a style with id '%s', but it is not a %s style. Use %s instead."
                % (style_id, expected_type, fallback or "Word's default")
            )
        else:
            message = (
                "This shell has no %s style called '%s'. Use %s instead."
                % (expected_type, display_names[style_id], fallback or "Word's default formatting")
            )
        findings.append(ShellFinding("shell.style.%s" % style_id, "warning", message))

    decimal_outline, bullet_definition = _check_numbering(numbering)
    if not decimal_outline:
        findings.append(ShellFinding(
            "shell.numbering.decimal_outline", "warning",
            "This shell has no three-level decimal outline definition (1., 1.1, 1.1.1). "
            "Numbered clauses will use the renderer's explicit decimal fallback; numbering may not match this shell.",
        ))
    if not bullet_definition:
        findings.append(ShellFinding(
            "shell.numbering.bullets", "warning",
            "This shell has no bullet numbering definition. Bulleted lists will use the renderer's explicit bullet fallback.",
        ))
    return ShellCheckResult(shell_path, tuple(findings), fallbacks)
