"""Compose Markdown components into a new DOCX based on a read-only shell."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable, Tuple, Union
import zipfile

from lxml import etree

from md_to_word import MarkdownWarning, render_markdown
from shell_check import check_shell

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
NS = {"w": W_NS}
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
NUMBERING_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering"
NUMBERING_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"
_NUMBER_ID = re.compile(r"^rId(\d+)$")


@dataclass(frozen=True)
class ComposeResult:
    """The written document and any non-fatal findings from its components."""

    output_path: Path
    warnings: Tuple[MarkdownWarning, ...] = ()


def _parse_xml(data: bytes, part_name: str):
    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
    )
    try:
        return etree.fromstring(data, parser)
    except etree.XMLSyntaxError as exc:
        raise ValueError("The Word shell has an unreadable %s part." % part_name) from exc


def _xml_bytes(root) -> bytes:
    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def _max_id(root, element_name: str, attribute_name: str) -> int:
    values = []
    for element in root.findall("w:" + element_name, NS):
        value = element.get(W + attribute_name)
        if value is not None and value.isdigit():
            values.append(int(value))
    return max(values or [-1])


def _is_decimal_outline(abstract) -> bool:
    """Whether an abstract numbering definition is the contract's decimal outline."""
    level = next(
        (item for item in abstract.findall("w:lvl", NS)
         if item.get(W + "ilvl") == "0"),
        None,
    )
    if level is None:
        return False
    number_format = level.find("w:numFmt", NS)
    return number_format is not None and number_format.get(W + "val") == "decimal"


def _merge_numbering(numbering_root, results) -> bool:
    """Merge numbering, sharing one decimal instance so clauses continue globally.

    Bulleted lists retain independent instances. Every ordered list in the
    assembled document (including lists from different components) uses one
    decimal numId, so Word continues the clause sequence across component
    boundaries and intervening paragraphs/tables.
    """
    if not any(
        item.tag == W + "num"
        for result in results for item in result.numbering
    ):
        return False

    next_abstract_id = _max_id(numbering_root, "abstractNum", "abstractNumId") + 1
    next_num_id = _max_id(numbering_root, "num", "numId") + 1
    additions_abstract = []
    additions_num = []
    shell_abstracts = {
        item.get(W + "abstractNumId"): item
        for item in numbering_root.findall("w:abstractNum", NS)
    }
    shared_decimal_abstract_id = None
    shared_decimal_num_id = None

    for result in results:
        abstract_ids = {}
        local_abstracts = dict(shell_abstracts)

        for source in result.numbering:
            if source.tag != W + "abstractNum":
                continue
            old_id = source.get(W + "abstractNumId")
            if old_id is None:
                raise ValueError("A generated numbering definition has no ID.")
            local_abstracts[old_id] = source
            if _is_decimal_outline(source):
                if shared_decimal_abstract_id is None:
                    copied = deepcopy(source)
                    shared_decimal_abstract_id = str(next_abstract_id)
                    next_abstract_id += 1
                    copied.set(W + "abstractNumId", shared_decimal_abstract_id)
                    additions_abstract.append(copied)
                abstract_ids[old_id] = shared_decimal_abstract_id
            else:
                copied = deepcopy(source)
                new_id = str(next_abstract_id)
                next_abstract_id += 1
                copied.set(W + "abstractNumId", new_id)
                abstract_ids[old_id] = new_id
                additions_abstract.append(copied)

        num_ids = {}
        for source in result.numbering:
            if source.tag != W + "num":
                continue
            old_id = source.get(W + "numId")
            if old_id is None:
                raise ValueError("A generated numbering instance has no ID.")
            abstract_ref = source.find("w:abstractNumId", NS)
            if abstract_ref is None:
                raise ValueError("A generated numbering instance has no abstract definition.")
            old_abstract_id = abstract_ref.get(W + "val")
            abstract = local_abstracts.get(old_abstract_id)
            is_decimal = abstract is not None and _is_decimal_outline(abstract)

            if is_decimal:
                mapped_abstract_id = abstract_ids.get(
                    old_abstract_id, old_abstract_id
                )
                if shared_decimal_num_id is None:
                    copied = deepcopy(source)
                    shared_decimal_num_id = str(next_num_id)
                    next_num_id += 1
                    copied.set(W + "numId", shared_decimal_num_id)
                    copied.find("w:abstractNumId", NS).set(
                        W + "val", mapped_abstract_id
                    )
                    additions_num.append(copied)
                num_ids[old_id] = shared_decimal_num_id
            else:
                copied = deepcopy(source)
                new_id = str(next_num_id)
                next_num_id += 1
                copied.set(W + "numId", new_id)
                mapped_abstract_id = abstract_ids.get(
                    old_abstract_id, old_abstract_id
                )
                copied.find("w:abstractNumId", NS).set(
                    W + "val", mapped_abstract_id
                )
                num_ids[old_id] = new_id
                additions_num.append(copied)

        remapped_references = 0
        for element in result.elements:
            for reference in element.iter():
                if reference.tag == W + "numId":
                    old_id = reference.get(W + "val")
                    if old_id in num_ids:
                        reference.set(W + "val", num_ids[old_id])
                        remapped_references += 1
        if num_ids and remapped_references == 0:
            raise ValueError("Generated list numbering could not be linked to its paragraphs.")

    first_num = numbering_root.find("w:num", NS)
    insertion_index = numbering_root.index(first_num) if first_num is not None else len(numbering_root)
    for offset, definition in enumerate(additions_abstract):
        numbering_root.insert(insertion_index + offset, definition)
    for instance in additions_num:
        numbering_root.append(instance)
    return True

def _ensure_numbering_relationship(rels_root) -> None:
    relationships = rels_root.findall("{%s}Relationship" % REL_NS)
    if any(item.get("Type") == NUMBERING_REL for item in relationships):
        return
    next_id = max(
        [int(match.group(1)) for item in relationships
         if (match := _NUMBER_ID.match(item.get("Id", "")))] or [0]
    ) + 1
    relation = etree.SubElement(rels_root, "{%s}Relationship" % REL_NS)
    relation.set("Id", "rId%d" % next_id)
    relation.set("Type", NUMBERING_REL)
    relation.set("Target", "numbering.xml")


def _ensure_numbering_content_type(types_root) -> None:
    overrides = types_root.findall("{%s}Override" % CT_NS)
    if any(item.get("PartName") == "/word/numbering.xml" for item in overrides):
        return
    override = etree.SubElement(types_root, "{%s}Override" % CT_NS)
    override.set("PartName", "/word/numbering.xml")
    override.set("ContentType", NUMBERING_TYPE)


def compose_document(
    shell_path: Union[os.PathLike, str],
    components: Iterable[str],
    output_path: Union[os.PathLike, str],
) -> ComposeResult:
    """Write ordered Markdown components into a new DOCX based on a Word shell.

    The shell's body wording is replaced, but its final section properties and
    all other package parts are retained. Generated numbering definitions are
    merged and their IDs remapped per component. The input shell is never
    opened for writing.
    """
    shell = Path(shell_path)
    output = Path(output_path)
    if shell.resolve() == output.resolve():
        raise ValueError("The output document must be a different file from the shell.")
    if output.suffix.lower() != ".docx":
        raise ValueError("The output file name must end in .docx.")

    component_texts = list(components)
    if any(not isinstance(item, str) for item in component_texts):
        raise TypeError("Each component must be Markdown text.")

    shell_check = check_shell(shell)
    if not shell_check.can_generate:
        details = " ".join(item.message for item in shell_check.errors)
        raise ValueError("The selected Word shell cannot be used. " + details)

    rendered = []
    warnings = []
    for source in component_texts:
        result = render_markdown(source, shell)
        if not result.can_generate:
            details = " ".join(item.message for item in result.errors)
            raise ValueError("A component could not be rendered. " + details)
        rendered.append(result)
        warnings.extend(result.warnings)

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix="." + output.stem + "-", suffix=".tmp", dir=str(output.parent)
    )
    os.close(fd)
    temporary = Path(temporary_name)

    try:
        with zipfile.ZipFile(str(shell), "r") as source_package:
            names = set(source_package.namelist())
            replacements = {}

            if "word/numbering.xml" in names:
                numbering_root = _parse_xml(
                    source_package.read("word/numbering.xml"), "word/numbering.xml"
                )
            else:
                numbering_root = etree.Element(
                    W + "numbering", nsmap={"w": W_NS}
                )

            # Remap the component-local references before their XML nodes are
            # moved into the final document body.
            has_numbering = _merge_numbering(numbering_root, rendered)
            if has_numbering:
                replacements["word/numbering.xml"] = _xml_bytes(numbering_root)

                rels_name = "word/_rels/document.xml.rels"
                if rels_name in names:
                    rels_root = _parse_xml(source_package.read(rels_name), rels_name)
                else:
                    rels_root = etree.Element(
                        "{%s}Relationships" % REL_NS, nsmap={None: REL_NS}
                    )
                _ensure_numbering_relationship(rels_root)
                replacements[rels_name] = _xml_bytes(rels_root)

                types_root = _parse_xml(
                    source_package.read("[Content_Types].xml"), "[Content_Types].xml"
                )
                _ensure_numbering_content_type(types_root)
                replacements["[Content_Types].xml"] = _xml_bytes(types_root)

            document_root = _parse_xml(
                source_package.read("word/document.xml"), "word/document.xml"
            )
            body = document_root.find("w:body", NS)
            if body is None:
                raise ValueError("The Word shell has no document body.")
            children = list(body)
            if not children or children[-1].tag != W + "sectPr":
                raise ValueError("The Word shell has no final section properties.")
            for child in children[:-1]:
                body.remove(child)
            for result in rendered:
                for element in result.elements:
                    body.insert(len(body) - 1, element)
            replacements["word/document.xml"] = _xml_bytes(document_root)

            with zipfile.ZipFile(str(temporary), "w", zipfile.ZIP_DEFLATED) as target:
                for info in source_package.infolist():
                    data = replacements.get(info.filename)
                    if data is None:
                        data = source_package.read(info.filename)
                    target.writestr(info, data)
                for name in ("word/numbering.xml", "word/_rels/document.xml.rels"):
                    if name in replacements and name not in names:
                        target.writestr(name, replacements[name], compress_type=zipfile.ZIP_DEFLATED)

        os.replace(str(temporary), str(output))
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise

    unique_warnings = []
    seen = set()
    for warning in warnings:
        key = (warning.code, warning.message)
        if key not in seen:
            seen.add(key)
            unique_warnings.append(warning)
    return ComposeResult(output, tuple(unique_warnings))
