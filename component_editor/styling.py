"""Formatted view of the Markdown in a Tk Text widget.

Works on a widget passed in; imports no Tkinter itself.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import core
from component_preview import configure_paragraph_style_tags

from .tables import _is_markdown_table_separator
from safe_hyperlinks import safe_hyperlink_target

if TYPE_CHECKING:
    import tkinter as tk


def _style_markdown_widget(widget: tk.Text, raw_view: bool = False) -> None:
    """Show a simple formatted editing surface while retaining Markdown in the Text buffer."""
    for name in (
        "syntax", "heading_1", "heading_2", "heading_3", "bold", "italic",
        "field", "link", "link_warning",
    ):
        widget.tag_remove(name, "1.0", "end")
    widget.tag_configure("syntax", elide=not raw_view)
    widget.tag_configure("heading_1", font=("TkDefaultFont", 16, "bold"))
    widget.tag_configure("heading_2", font=("TkDefaultFont", 14, "bold"))
    widget.tag_configure("heading_3", font=("TkDefaultFont", 12, "bold"))
    widget.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))
    widget.tag_configure("italic", font=("TkDefaultFont", 10, "italic"))
    widget.tag_configure("field", background="#fff0c2", foreground="#714d00")
    widget.tag_configure("link", underline=True, foreground="#245a8d")
    widget.tag_configure("link_warning", underline=True, foreground="#a05a00")

    source = widget.get("1.0", "end-1c")
    offset = 0
    for line in source.splitlines(keepends=True):
        visible = line.rstrip("\r\n")
        line_start = offset
        if not visible:
            offset += len(line)
            continue
        for match in re.finditer(r"(?<!\\)\\[([^]\\n]+)\\]\\((<[^>\\n]+>|[^)\\s]+)\\)", visible):
            raw_target = match.group(2)
            target = raw_target[1:-1] if raw_target.startswith("<") and raw_target.endswith(">") else raw_target
            style = "link" if safe_hyperlink_target(target) else "link_warning"
            widget.tag_add(
                style,
                f"1.0 + {line_start + match.start(1)} chars",
                f"1.0 + {line_start + match.end(1)} chars",
            )
            widget.tag_add(
                "syntax",
                f"1.0 + {line_start + match.start()} chars",
                f"1.0 + {line_start + match.start(1)} chars",
            )
            widget.tag_add(
                "syntax",
                f"1.0 + {line_start + match.end(1)} chars",
                f"1.0 + {line_start + match.end()} chars",
            )

        heading = re.match(r"^(#{1,3})[ \t]+", visible)
        if heading:
            widget.tag_add(
                "syntax",
                f"1.0 + {line_start} chars",
                f"1.0 + {line_start + heading.end()} chars",
            )
            style = f"heading_{len(heading.group(1))}"
            widget.tag_add(
                style,
                f"1.0 + {line_start + heading.end()} chars",
                f"1.0 + {line_start + len(visible)} chars",
            )

        marker = re.match(r"^[ \t]*(?:[-+*]|\d{1,4}\.)[ \t]+", visible)
        if marker:
            widget.tag_add(
                "syntax",
                f"1.0 + {line_start} chars",
                f"1.0 + {line_start + marker.end()} chars",
            )

        if _is_markdown_table_separator(visible) and "|" in visible:
            widget.tag_add(
                "syntax",
                f"1.0 + {line_start} chars",
                f"1.0 + {line_start + len(visible)} chars",
            )
        elif "|" in visible:
            field_ranges = [
                (match.start(), match.end()) for match in core.TOKEN.finditer(visible)
            ]
            for pipe in re.finditer(r"(?<!\\)\|", visible):
                if not any(start <= pipe.start() < end for start, end in field_ranges):
                    widget.tag_add(
                        "syntax",
                        f"1.0 + {line_start + pipe.start()} chars",
                        f"1.0 + {line_start + pipe.end()} chars",
                    )

        for escape in re.finditer(r"\\(?=[\\*_{}\[\]()#+\-.!|>])", visible):
            widget.tag_add(
                "syntax",
                f"1.0 + {line_start + escape.start()} chars",
                f"1.0 + {line_start + escape.end()} chars",
            )

        field_ranges = [
            (match.start(), match.end()) for match in core.TOKEN.finditer(visible)
        ]
        for start, end in field_ranges:
            widget.tag_add(
                "field",
                f"1.0 + {line_start + start} chars",
                f"1.0 + {line_start + end} chars",
            )

        patterns = (
            (r"\*\*\*(.+?)\*\*\*", 3, 3),
            (r"\*\*(.+?)\*\*", 2, 2),
            (r"(?<!\*)\*([^*\n]+)\*(?!\*)", 1, 1),
            (r"___(.+?)___", 3, 3),
            (r"__(.+?)__", 2, 2),
            (r"(?<!_)_([^_\n]+)_(?!_)", 1, 1),
        )
        for pattern, marker_width, style_width in patterns:
            for match in re.finditer(pattern, visible):
                if any(
                    start < match.end() and end > match.start()
                    for start, end in field_ranges
                ):
                    continue
                content_start = match.start() + marker_width
                content_end = match.end() - marker_width
                if style_width == 3:
                    widget.tag_add(
                        "bold", f"1.0 + {line_start + content_start} chars",
                        f"1.0 + {line_start + content_end} chars",
                    )
                    widget.tag_add(
                        "italic", f"1.0 + {line_start + content_start} chars",
                        f"1.0 + {line_start + content_end} chars",
                    )
                elif style_width == 2:
                    widget.tag_add(
                        "bold", f"1.0 + {line_start + content_start} chars",
                        f"1.0 + {line_start + content_end} chars",
                    )
                else:
                    widget.tag_add(
                        "italic", f"1.0 + {line_start + content_start} chars",
                        f"1.0 + {line_start + content_end} chars",
                    )
                widget.tag_add(
                    "syntax", f"1.0 + {line_start + match.start()} chars",
                    f"1.0 + {line_start + content_start} chars",
                )
                widget.tag_add(
                    "syntax", f"1.0 + {line_start + content_end} chars",
                    f"1.0 + {line_start + match.end()} chars",
                )
        offset += len(line)


def configure_preview_tags(widget) -> None:
    """Text tags for the Components window's preview pane."""
    widget.tag_configure(
        "heading_1", font=("TkDefaultFont", 17, "bold"),
        spacing1=10, spacing3=6,
    )
    widget.tag_configure(
        "heading_2", font=("TkDefaultFont", 14, "bold"),
        spacing1=8, spacing3=5,
    )
    widget.tag_configure(
        "heading_3", font=("TkDefaultFont", 12, "bold"),
        spacing1=6, spacing3=4,
    )
    widget.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))
    widget.tag_configure("italic", font=("TkDefaultFont", 10, "italic"))
    widget.tag_configure(
        "field", background="#fff0c2", foreground="#714d00"
    )
    widget.tag_configure(
        "list_marker", foreground="#555555", lmargin1=10
    )
    widget.tag_configure(
        "table_header", font=("TkDefaultFont", 9, "bold"),
        background="#eeeeee",
    )
    widget.tag_configure("table_cell", font=("TkFixedFont", 9))
    widget.tag_configure(
        "table_border", foreground="#777777", font=("TkFixedFont", 9)
    )
    widget.tag_configure(
        "code", font=("TkFixedFont", 9), background="#f1f1f1"
    )
    widget.tag_configure(
        "code_block", font=("TkFixedFont", 9), background="#f4f4f4",
        lmargin1=8, lmargin2=8,
    )
    widget.tag_configure("blockquote", foreground="#555555", lmargin1=12)
    widget.tag_configure("link", underline=True, foreground="#245a8d")
    widget.tag_configure("link_warning", underline=True, foreground="#a05a00")
    widget.tag_configure("rule", foreground="#888888")
    widget.tag_configure("source_text", foreground="#666666")
    configure_paragraph_style_tags(widget)
    widget.tag_configure(
        "marker", foreground="#4f4f4f", background="#e6e6e6",
        font=("TkDefaultFont", 9, "italic"),
    )
