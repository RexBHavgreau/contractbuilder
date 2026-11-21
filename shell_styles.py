"""Styles the app adds to a new document when the Word shell lacks them (T-060-A).

A shell is an ordinary Word file; it should not have to contain every style
the converter uses. Where a style is missing, the **output** document gets a
simple definition based on Normal (or Body Text when there is no usable Normal),
so headings, lists and tables look right. The shell file is never changed.

Pure lxml, no UI. ``plan_styles`` says what is present, what must be added and
which existing style stands in for a requested one; ``add_missing_styles``
writes the definitions into a ``styles.xml`` tree.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
NS = {"w": W_NS}

# style id -> (type, the name Word shows). The converter asks for these ids.
SUPPLIABLE = {
    "Heading1": ("paragraph", "heading 1"),
    "Heading2": ("paragraph", "heading 2"),
    "Heading3": ("paragraph", "heading 3"),
    "ListParagraph": ("paragraph", "List Paragraph"),
    "ListBullet": ("paragraph", "List Bullet"),
    "ListNumber": ("paragraph", "List Number"),
    "TableGrid": ("table", "Table Grid"),
}

_HEADING_POINTS = {"Heading1": 16, "Heading2": 14, "Heading3": 12}

# Paragraph styles a component can ask for by name (T-061). Unlike SUPPLIABLE
# these are added only when a component uses them. Title and Subtitle are
# centered: centering comes from the style, nowhere else (T-042).
PARAGRAPH_STYLES = {
    "Title": ("Title", "Title"),
    "Subtitle": ("Subtitle", "Subtitle"),
    "Body Text": ("BodyText", "Body Text"),
    "Block Text": ("BlockText", "Block Text"),
}


@dataclass
class StylePlan:
    """What a shell's ``styles.xml`` has, and what the output must add."""

    # requested style id -> the id to use (itself, or an existing style found
    # by its Word name under a different id)
    use: Dict[str, str] = field(default_factory=dict)
    add: List[str] = field(default_factory=list)       # style ids to define
    base: Optional[str] = None                          # Normal, BodyText or None


def _name(style) -> str:
    element = style.find("w:name", NS)
    return (element.get(W + "val") if element is not None else "") or ""


def _styles(root):
    return [] if root is None else root.findall("w:style", NS)


def base_style_id(root) -> Optional[str]:
    """Normal if the file has it, else Body Text, else nothing."""
    by_id = {s.get(W + "styleId"): s.get(W + "type") for s in _styles(root)}
    for candidate in ("Normal", "BodyText"):
        if by_id.get(candidate) == "paragraph":
            return candidate
    return None


def plan_styles(root) -> StylePlan:
    """Work out, for each style the converter uses, whether it must be added.

    A style counts as present when the file has the same id and type, or a
    style of the same type with the same Word name (ignoring capitals) under
    another id: that one is used, not duplicated. A style that exists with the
    right id but the wrong type cannot be replaced by a new one with the same
    id, so it is left out of the plan (the caller falls back as before).
    """
    plan = StylePlan(base=base_style_id(root))
    styles = _styles(root)
    for style_id, (kind, name) in SUPPLIABLE.items():
        same_id = [s for s in styles if s.get(W + "styleId") == style_id]
        if same_id:
            if same_id[0].get(W + "type") == kind:
                plan.use[style_id] = style_id
            continue
        named = [
            s for s in styles
            if s.get(W + "type") == kind and _name(s).casefold() == name.casefold()
        ]
        if named:
            plan.use[style_id] = named[0].get(W + "styleId")
        else:
            plan.use[style_id] = style_id
            plan.add.append(style_id)
    return plan


def _sub(parent, tag, **attributes):
    element = etree.SubElement(parent, W + tag)
    for key, value in attributes.items():
        element.set(W + key, str(value))
    return element


def _paragraph_style(style_id, name, based_on, ppr=None, rpr=None):
    style = etree.Element(W + "style")
    style.set(W + "type", "paragraph")
    style.set(W + "styleId", style_id)
    _sub(style, "name", val=name)
    if based_on:
        _sub(style, "basedOn", val=based_on)
    _sub(style, "qFormat")
    if ppr is not None:
        style.append(ppr)
    if rpr is not None:
        style.append(rpr)
    return style


def _definition(style_id, plan, root):
    kind, name = SUPPLIABLE[style_id]
    if style_id.startswith("Heading"):
        level = int(style_id[-1])
        ppr = etree.Element(W + "pPr")
        _sub(ppr, "keepNext")
        _sub(ppr, "keepLines")
        _sub(ppr, "spacing", before=240 if level == 1 else 200, after=120)
        _sub(ppr, "outlineLvl", val=level - 1)
        rpr = etree.Element(W + "rPr")
        _sub(rpr, "b")
        _sub(rpr, "bCs")
        _sub(rpr, "sz", val=_HEADING_POINTS[style_id] * 2)
        _sub(rpr, "szCs", val=_HEADING_POINTS[style_id] * 2)
        return _paragraph_style(style_id, name, plan.base, ppr, rpr)
    if style_id in ("ListParagraph", "ListBullet", "ListNumber"):
        ppr = etree.Element(W + "pPr")
        if style_id == "ListParagraph":
            _sub(ppr, "ind", left=720)
        _sub(ppr, "contextualSpacing")
        # Bullet and number styles sit on List Paragraph, whichever id it has.
        parent = plan.base
        if style_id != "ListParagraph":
            parent = plan.use.get("ListParagraph", "ListParagraph")
        return _paragraph_style(style_id, name, parent, ppr)
    # Table Grid: thin borders all round, on Normal Table when the file has it.
    style = etree.Element(W + "style")
    style.set(W + "type", "table")
    style.set(W + "styleId", style_id)
    _sub(style, "name", val=name)
    table_types = {s.get(W + "styleId"): s.get(W + "type") for s in _styles(root)}
    if table_types.get("TableNormal") == "table":
        _sub(style, "basedOn", val="TableNormal")
    _sub(style, "uiPriority", val=59)
    properties = _sub(style, "tblPr")
    borders = _sub(properties, "tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        _sub(borders, side, val="single", sz=4, space=0, color="auto")
    return style


def new_styles_root():
    """An empty ``styles.xml`` for a shell that has none."""
    return etree.Element(W + "styles", nsmap={"w": W_NS})


def add_missing_styles(root, plan: Optional[StylePlan] = None) -> List[str]:
    """Append the definitions the plan lists to ``root``; return the ids added."""
    plan = plan or plan_styles(root)
    for style_id in plan.add:
        root.append(_definition(style_id, plan, root))
    return list(plan.add)


@dataclass
class ParagraphStylePlan:
    """How the paragraph style names a component asks for resolve in a file."""

    ids: Dict[str, str] = field(default_factory=dict)   # name -> style id to use
    add: List[str] = field(default_factory=list)        # names whose style is added
    unknown: List[str] = field(default_factory=list)    # names found nowhere


def plan_paragraph_styles(root, names) -> ParagraphStylePlan:
    """Resolve each requested name: use the file's style, add ours, or give up.

    A name resolves to a paragraph style in the file with that Word name (or
    id). One of the app's own names (Title, Subtitle, Body Text, Block Text)
    that is missing is added. Any other name that is missing is unknown, and
    the caller falls back to Normal with a plain note: nothing is dropped
    silently. "Normal" resolves to the file's Normal when it has one.
    """
    plan = ParagraphStylePlan()
    styles = [s for s in _styles(root) if s.get(W + "type") == "paragraph"]
    for name in dict.fromkeys(n for n in names if n and n.casefold() != "normal"):
        wanted_id, word_name = PARAGRAPH_STYLES.get(name, (None, name))
        match = [
            s for s in styles
            if s.get(W + "styleId") == wanted_id
            or _name(s).casefold() == word_name.casefold()
            or s.get(W + "styleId", "").casefold() == name.replace(" ", "").casefold()
        ]
        if match:
            plan.ids[name] = match[0].get(W + "styleId")
        elif name in PARAGRAPH_STYLES:
            plan.ids[name] = wanted_id
            plan.add.append(name)
        else:
            plan.unknown.append(name)
    return plan


def _paragraph_definition(name, base):
    style_id, word_name = PARAGRAPH_STYLES[name]
    ppr = etree.Element(W + "pPr")
    rpr = None
    if name in ("Title", "Subtitle"):
        _sub(ppr, "keepNext")
        _sub(ppr, "spacing", before=0, after=240 if name == "Title" else 200)
        _sub(ppr, "jc", val="center")
        rpr = etree.Element(W + "rPr")
        if name == "Title":
            _sub(rpr, "b")
            _sub(rpr, "bCs")
        else:
            _sub(rpr, "i")
            _sub(rpr, "iCs")
        size = 40 if name == "Title" else 28
        _sub(rpr, "sz", val=size)
        _sub(rpr, "szCs", val=size)
    elif name == "Block Text":
        _sub(ppr, "spacing", after=120)
        _sub(ppr, "ind", left=720, right=720)
    else:  # Body Text
        _sub(ppr, "spacing", after=120)
    return _paragraph_style(style_id, word_name, base, ppr, rpr)


def add_paragraph_styles(root, plan: ParagraphStylePlan) -> List[str]:
    """Append the app's own definitions the plan lists; return the names added."""
    base = base_style_id(root)
    for name in plan.add:
        root.append(_paragraph_definition(name, base))
    return list(plan.add)
