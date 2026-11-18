"""Configured Markdown parser for contract components.

Start with CommonMark, explicitly enable GitHub-style tables, and never parse
raw HTML. Component text is contract content, not trusted markup.
"""
from markdown_it import MarkdownIt


def create_parser() -> MarkdownIt:
    """Return the project's table-enabled, raw-HTML-disabled Markdown parser."""
    return MarkdownIt("commonmark", {"html": False}).enable("table")
