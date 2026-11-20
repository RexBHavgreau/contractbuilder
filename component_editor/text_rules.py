"""Pure Markdown text rules for the component editor: no Tkinter.

Escaping plain text, block formatting (headings, bullets, numbering, indent),
bold/italic toggles, and whether stored wording can be edited safely.
"""
from __future__ import annotations

import re

import core
from markdown_fields import protect_fields
from md_parse import create_parser


_MARKDOWN_SPECIAL = frozenset(
    ("\\", chr(96), "*", "_", "{", "}", "[", "]", "(", ")", ">", "#", "+", "-", ".", "!", "|")
)
# Hyphens and periods are ordinary punctuation except in a list marker at the
# beginning of a line. Keep them in _MARKDOWN_SPECIAL for decoding older saves.
_PLAIN_TEXT_SPECIAL = _MARKDOWN_SPECIAL - {"-", "."}


def _escape_plain_segment(text: str) -> str:
    """Escape Markdown punctuation without touching field placeholders."""
    return "".join(("\\" + character) if character in _PLAIN_TEXT_SPECIAL else character
                   for character in text)


def _escape_line_marker(line: str) -> str:
    """Escape structural list markers at line start, not ordinary punctuation."""
    indent = len(line) - len(line.lstrip(" \t"))
    content = line[indent:]
    if (
        content.startswith("- ")
        or content.startswith("-\t")
        or content == "-"
        or (content.startswith("---") and not content.strip("- \t"))
    ):
        return line[:indent] + "\\-" + content[1:]

    digits = 0
    while digits < len(content) and content[digits].isdigit():
        digits += 1
    if digits and content[digits:digits + 2] in (". ", ".\t"):
        return line[:indent] + content[:digits] + "\\." + content[digits + 1:]
    return line


def plain_text_to_markdown(text: str) -> str:
    """Convert plain text to safe Markdown paragraphs and hard line breaks.

    Complete ContractBuilder fields are preserved byte-for-byte. All other
    Markdown syntax is escaped, while ordinary hyphens and periods remain
    readable. Leading list markers are escaped so they do not create lists.
    """
    if not isinstance(text, str):
        raise TypeError("Component text must be a string.")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    pieces: list[str] = []
    cursor = 0
    for match in core.TOKEN.finditer(normalized):
        pieces.append(_escape_plain_segment(normalized[cursor:match.start()]))
        pieces.append(match.group(0))
        cursor = match.end()
    pieces.append(_escape_plain_segment(normalized[cursor:]))
    escaped = "".join(pieces)
    escaped = "\n".join(_escape_line_marker(line) for line in escaped.split("\n"))

    paragraphs: list[str] = []
    current: list[str] = []
    for line in escaped.split("\n"):
        if not line.strip():
            if current:
                paragraphs.append("  \n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append("  \n".join(current))
    return "\n\n".join(paragraphs)


def markdown_to_plain_text(markdown: str) -> str:
    """Reverse the editor's own plain-text Markdown encoding."""
    if not isinstance(markdown, str):
        raise TypeError("Component wording must be a string.")
    output: list[str] = []
    index = 0
    while index < len(markdown):
        if markdown.startswith("  \n", index):
            output.append("\n")
            index += 3
        elif (
            markdown[index] == "\\"
            and index + 1 < len(markdown)
            and markdown[index + 1] in _MARKDOWN_SPECIAL
        ):
            output.append(markdown[index + 1])
            index += 2
        else:
            output.append(markdown[index])
            index += 1
    return "".join(output)



def format_markdown_block(
    markdown: str,
    action: str,
    level: int = 2,
    previous_text: str = "",
) -> str:
    """Toggle or apply a block toolbar operation to Markdown lines."""
    if action not in {"heading", "normal", "bullet", "numbered", "indent", "outdent"}:
        raise ValueError(f"Unsupported block-format action: {action}")
    lines = str(markdown or "").splitlines()
    if not lines:
        return ""

    marker = re.compile(r"^([ \t]*)(?:[-+*]|\d{1,4}\.)[ \t]+(.*)$")
    numbered = re.compile(r"^([ \t]*)(\d{1,4}\.)[ \t]+(.*)$")
    heading = re.compile(r"^([ \t]*)(#{1,3})[ \t]+(.*)$")
    nonempty = [line for line in lines if line.strip()]

    if action in {"heading", "normal"}:
        requested = max(1, min(3, int(level)))
        same_heading = bool(nonempty) and all(
            (match := heading.match(line)) is not None
            and (action == "normal" or len(match.group(2)) == requested)
            for line in nonempty
        )
        result = []
        for line in lines:
            if not line.strip():
                result.append(line)
                continue
            match = heading.match(line)
            indent = re.match(r"^[ \t]*", line).group(0)
            content = match.group(3) if match else line[len(indent):]
            if same_heading or action == "normal":
                result.append(indent + content)
            else:
                result.append(indent + "#" * requested + " " + content)
        return "\n".join(result)

    if action in {"bullet", "numbered"}:
        already_target = bool(nonempty) and all(
            (match := marker.match(line)) is not None
            and (
                (action == "bullet" and line[match.start():].lstrip().startswith(("-", "+", "*")))
                or (action == "numbered" and numbered.match(line) is not None)
            )
            for line in nonempty
        )
        result = []
        for line in lines:
            if not line.strip():
                result.append(line)
                continue
            indent = re.match(r"^[ \t]*", line).group(0)
            match = marker.match(line)
            content = match.group(2) if match else line[len(indent):]
            if already_target:
                result.append(indent + content)
            else:
                prefix = "- " if action == "bullet" else "1. "
                result.append(indent + prefix + content)
        return "\n".join(result)

    if action == "indent":
        first = next((line for line in lines if line.strip()), "")
        first_match = numbered.match(first)
        if first_match is None:
            return markdown
        previous = next(
            (line for line in reversed(str(previous_text).splitlines()) if line.strip()),
            "",
        )
        previous_match = numbered.match(previous)
        if previous_match is None:
            return markdown
        current_depth = len(first_match.group(1).expandtabs(4))
        parent_depth = len(previous_match.group(1).expandtabs(4))
        if parent_depth > current_depth:
            return markdown

    result = []
    for line in lines:
        if not line.strip():
            result.append(line)
            continue
        if action == "indent":
            item = numbered.match(line)
            if item:
                depth = len(item.group(1).expandtabs(4)) + 4
                result.append(" " * depth + "1. " + item.group(3))
            else:
                result.append(line)
        else:  # outdent
            item = numbered.match(line)
            if item:
                depth = max(0, len(item.group(1).expandtabs(4)) - 4)
                result.append(" " * depth + "1. " + item.group(3))
            else:
                result.append(line)
    return "\n".join(result)


def _protected_markdown_spans(source: str) -> list[tuple[int, int]]:
    """Ranges that must not be mistaken for user-authored emphasis markers."""
    spans = [(match.start(), match.end()) for match in core.TOKEN.finditer(source)]
    spans.extend(
        (match.start(), match.end())
        for match in re.finditer(r"\\(?:\\|[\x60*_{}\[\]()#+\-.!|>])", source)
    )
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start < merged[-1][1]:
            continue
        merged.append((start, end))
    return merged


def _emphasis_matches(source: str):
    pattern = re.compile(r"(?<!\\)(\*\*\*|\*\*|\*|___|__|_)(.+?)(?<!\\)\1", re.DOTALL)
    return pattern.finditer(source)


def _strip_emphasis(source: str, action: str) -> str:
    """Remove one emphasis dimension, preserving the other and literal spans."""
    protected = _protected_markdown_spans(source)
    protected_source = source
    sentinels = []
    for index, (start, end) in enumerate(reversed(protected)):
        token = source[start:end]
        sentinel = f"\ue000{index}\ue001"
        protected_source = protected_source[:start] + sentinel + protected_source[end:]
        sentinels.append((sentinel, token))

    if action == "bold":
        pattern = re.compile(
            r"(?<!\\)(?<!\*)\*\*\*(.+?)(?<!\\)\*\*\*(?!\*)"
            r"|(?<!\\)(?<!\*)\*\*(.+?)(?<!\\)\*\*(?!\*)"
            r"|(?<!\\)(?<!_)___(.+?)(?<!\\)___(?!_)"
            r"|(?<!\\)(?<!_)__(.+?)(?<!\\)__(?!_)",
            re.DOTALL,
        )
        def replace(match):
            if match.group(1) is not None:
                return "*" + match.group(1) + "*"
            if match.group(2) is not None:
                return match.group(2)
            if match.group(3) is not None:
                return "_" + match.group(3) + "_"
            return match.group(4)
    elif action == "italic":
        pattern = re.compile(
            r"(?<!\\)(?<!\*)\*\*\*(.+?)(?<!\\)\*\*\*(?!\*)"
            r"|(?<!\\)(?<!\*)\*([^*\n]+?)(?<!\\)\*(?!\*)"
            r"|(?<!\\)(?<!_)___(.+?)(?<!\\)___(?!_)"
            r"|(?<!\\)(?<!_)_([^_\n]+?)(?<!\\)_(?!_)",
            re.DOTALL,
        )
        def replace(match):
            if match.group(1) is not None:
                return "**" + match.group(1) + "**"
            if match.group(2) is not None:
                return match.group(2)
            if match.group(3) is not None:
                return "__" + match.group(3) + "__"
            return match.group(4)
    else:
        raise ValueError(f"Unsupported inline-format action: {action}")

    changed = pattern.sub(replace, protected_source)
    for sentinel, token in sentinels:
        changed = changed.replace(sentinel, token)
    return changed


def toggle_inline_format(
    markdown: str, start: int, end: int, action: str
) -> tuple[str, int, int]:
    """Toggle bold or italic over a selected Markdown source range."""
    if action not in {"bold", "italic"}:
        raise ValueError(f"Unsupported inline-format action: {action}")
    source = str(markdown)
    start = max(0, min(len(source), int(start)))
    end = max(start, min(len(source), int(end)))
    if start == end:
        return source, start, end

    # A selection wholly inside one field or escaped literal is not editable syntax.
    if any(left <= start and end <= right for left, right in _protected_markdown_spans(source)):
        return source, start, end

    for match in _emphasis_matches(source):
        marker = match.group(1)
        content_start = match.start() + len(marker)
        content_end = match.end() - len(marker)
        selected_content = (start, end) == (content_start, content_end)
        selected_markup = (start, end) == (match.start(), match.end())
        if not (selected_content or selected_markup):
            continue
        if marker == "***":
            retained = "*" if action == "bold" else "**"
        elif action == "bold" and marker in {"**", "__"}:
            retained = ""
        elif action == "italic" and marker in {"*", "_"}:
            retained = ""
        else:
            continue
        content = match.group(2)
        new_source = source[:match.start()] + retained + content + retained + source[match.end():]
        new_start = match.start() + len(retained)
        return new_source, new_start, new_start + len(content)

    selected = source[start:end]
    normalized = _strip_emphasis(selected, action)
    marker = "**" if action == "bold" else "*"
    replacement = marker + normalized + marker
    result = source[:start] + replacement + source[end:]
    for match in _emphasis_matches(result):
        if match.start() == start and match.end() == start + len(replacement):
            new_start = match.start() + len(match.group(1))
            return result, new_start, match.end() - len(match.group(1))
    new_start = start + len(marker)
    return result, new_start, new_start + len(normalized)


def inline_format_active(markdown: str, start: int, end: int, action: str) -> bool:
    """Whether the cursor or the complete selection is inside the requested style."""
    source = str(markdown)
    start = max(0, min(len(source), int(start)))
    end = max(start, min(len(source), int(end)))
    protected = _protected_markdown_spans(source)
    for match in _emphasis_matches(source):
        marker = match.group(1)
        is_active = (
            (action == "bold" and marker in {"***", "**", "__"})
            or (action == "italic" and marker in {"***", "*", "_"})
        )
        if not is_active:
            continue
        if any(left < match.end() and right > match.start() for left, right in protected):
            continue
        content_start = match.start() + len(marker)
        content_end = match.end() - len(marker)
        if (start, end) == (match.start(), match.end()):
            return True
        if start == end and content_start <= start <= content_end:
            return True
        if start < end and content_start <= start and end <= content_end:
            return True
    return False


def toggle_markdown_block(
    markdown: str, start: int, end: int, action: str,
    level: int = 2, previous_text: str = "",
) -> tuple[str, int, int]:
    """Apply a block toggle to the lines touched by a source selection."""
    source = str(markdown)
    start = max(0, min(len(source), int(start)))
    end = max(start, min(len(source), int(end)))
    block_start = source.rfind("\n", 0, start) + 1
    if end > start and source[end - 1:end] == "\n":
        block_end = end - 1
    else:
        newline = source.find("\n", end)
        block_end = len(source) if newline < 0 else newline
    block = source[block_start:block_end]
    previous = source[:block_start] if previous_text == "" else previous_text
    replacement = format_markdown_block(block, action, level, previous)
    result = source[:block_start] + replacement + source[block_end:]
    return result, block_start, block_start + len(replacement)


def markdown_block_state(markdown: str, start: int, end: int) -> dict:
    """Describe the heading/list formatting shared by the selected lines."""
    source = str(markdown)
    start = max(0, min(len(source), int(start)))
    end = max(start, min(len(source), int(end)))
    block_start = source.rfind("\n", 0, start) + 1
    if end > start and source[end - 1:end] == "\n":
        block_end = end - 1
    else:
        newline = source.find("\n", end)
        block_end = len(source) if newline < 0 else newline
    lines = [line for line in source[block_start:block_end].splitlines() if line.strip()]
    if not lines:
        return {"heading": None, "bullet": False, "numbered": False}
    headings = [re.match(r"^[ \t]*(#{1,3})[ \t]+", line) for line in lines]
    heading_levels = {len(match.group(1)) for match in headings if match}
    heading = heading_levels.pop() if len(heading_levels) == 1 and all(headings) else None
    bullets = all(re.match(r"^[ \t]*[-+*][ \t]+", line) for line in lines)
    numbered = all(re.match(r"^[ \t]*\d{1,4}\.[ \t]+", line) for line in lines)
    return {"heading": heading, "bullet": bullets, "numbered": numbered}


def _markdown_is_editable(markdown: str) -> bool:
    """Keep constructs without safe editor controls read-only."""
    protected, _replacements = protect_fields(markdown)
    tokens = create_parser().parse(protected)
    allowed_blocks = {
        "paragraph_open", "paragraph_close", "heading_open", "heading_close",
        "inline", "bullet_list_open", "bullet_list_close", "ordered_list_open",
        "ordered_list_close", "list_item_open", "list_item_close", "table_open",
        "table_close", "thead_open", "thead_close", "tbody_open", "tbody_close",
        "tr_open", "tr_close", "th_open", "th_close", "td_open", "td_close",
    }
    allowed_inline = {
        "text", "softbreak", "hardbreak", "strong_open", "strong_close",
        "em_open", "em_close",
    }
    for token in tokens:
        if token.type not in allowed_blocks:
            return False
        if token.type == "inline":
            if any(child.type not in allowed_inline for child in (token.children or [])):
                return False
    return True
