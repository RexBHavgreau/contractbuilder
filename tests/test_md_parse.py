from md_parse import create_parser


def test_parser_enables_pipe_tables():
    tokens = create_parser().parse(
        "| Clause | Requirement |\n"
        "| --- | --- |\n"
        "| One | Notice |\n"
    )
    token_types = [token.type for token in tokens]
    assert "table_open" in token_types
    assert "th_open" in token_types
    assert "td_open" in token_types


def test_parser_escapes_raw_html_instead_of_rendering_it():
    rendered = create_parser().render("<script>alert('not markup')</script>")
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
