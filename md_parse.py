"""Configured Markdown parser for contract components.

Start with CommonMark, explicitly enable GitHub-style tables, and never parse
raw HTML. Component text is contract content, not trusted markup.
"""
from markdown_it import MarkdownIt


def create_parser(*, allow_unsafe_links: bool = False) -> MarkdownIt:
    """Return the table-enabled parser, optionally exposing unsafe links to callers.

    MarkdownIt normally drops links with dangerous schemes during parsing.
    Components need to preserve their visible text *and* warn users, so their
    renderers opt in here and validate every target before generating Word or
    showing a supported-link style. Other parser callers retain the safe
    default behavior.
    """
    parser = MarkdownIt("commonmark", {"html": False}).enable("table")
    if allow_unsafe_links:
        # Do not make these links trusted. This only ensures the renderer can
        # keep their labels and issue its own scheme/target warning.
        parser.validateLink = lambda _url: True
    return parser
