from markdown_files import read_markdown_file, write_markdown_file


def test_utf8_markdown_round_trips_without_changing_supported_content(tmp_path):
    source = "# Notice\n\nA **clear** clause with café and a table:\n\n| A | B |\n| - | - |\n| 1 | 2 |\n"
    path = tmp_path / "component.md"
    write_markdown_file(path, source)

    imported = read_markdown_file(path)
    assert imported.text == source
    assert imported.warnings == ()


def test_import_accepts_utf8_bom(tmp_path):
    path = tmp_path / "bom.md"
    path.write_bytes(b"\xef\xbb\xbf# Heading\n")
    assert read_markdown_file(path).text == "# Heading\n"


def test_import_reports_html_images_and_footnotes_without_destroying_source(tmp_path):
    source = (
        "A paragraph.\n\n"
        "<div>raw HTML</div>\n\n"
        "![diagram](diagram.png)\n\n"
        "A note[^one].\n\n"
        "[^one]: Footnote text.\n"
    )
    path = tmp_path / "unsupported.md"
    path.write_text(source, encoding="utf-8")

    imported = read_markdown_file(path)
    assert imported.text == source
    assert len(imported.warnings) == 3
    assert any("Raw HTML" in warning for warning in imported.warnings)
    assert any("Images" in warning for warning in imported.warnings)
    assert any("Footnotes" in warning for warning in imported.warnings)


def test_export_uses_utf8_without_a_bom(tmp_path):
    path = tmp_path / "export.md"
    write_markdown_file(path, "שלום\n")
    assert path.read_bytes() == "שלום\n".encode("utf-8")


def test_component_markdown_metadata_round_trips_without_becoming_visible_wording(tmp_path):
    from markdown_files import write_component_markdown_file

    source = "## Payment\n\nPayment is due within thirty days.\n"
    component = {
        "id": 42, "name": "Payment terms", "description": "Due date",
        "category": "Commercial", "tags": ["billing"], "status": "archived",
    }
    version = {
        "id": 88, "number": 3, "created": "2026-11-21T10:00:00+00:00",
        "note": "Clarified timing", "paragraph_styles": ["Normal"],
    }
    path = tmp_path / "payment.md"
    write_component_markdown_file(path, source, component, version)

    imported = read_markdown_file(path)
    assert imported.text == source
    assert imported.warnings == ()
    assert imported.metadata == {
        "format": "contractbuilder-component",
        "version": 1,
        "component": component,
        "saved_version": version,
    }


def test_component_markdown_keeps_unsupported_content_warning_after_header(tmp_path):
    from markdown_files import write_component_markdown_file

    path = tmp_path / "component.md"
    write_component_markdown_file(
        path, "An image: ![diagram](diagram.png)", {"name": "Illustration"}, {"number": 1}
    )
    imported = read_markdown_file(path)
    assert imported.text == "An image: ![diagram](diagram.png)"
    assert any("Images" in warning for warning in imported.warnings)
