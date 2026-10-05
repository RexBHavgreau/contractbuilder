"""
Run with:  python -m pytest tests
"""
import datetime
import pathlib
import sys
import zipfile

import pytest
from docx import Document

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import core                                                   # noqa: E402
import sample                                                 # noqa: E402

VALUES = {
    "Client Name": "Acme Widgets, Inc.", "Effective Date": "10/5/2026",
    "Client Entity Type": "corporation", "Client Address": "100 Main St, Fort Worth, TX",
    "Scope of Services": "Line one\nLine two", "Term Months": "12", "Total Fee": "12500.5",
    "Billing Frequency": "monthly", "Late Fee": "", "Include Non-Compete": False,
    "Governing State": "Texas", "Client Contact": "Jane Doe",
    "TMAI Signatory": "Pat Smith", "Client Signatory": "Lee Jones",
}


@pytest.fixture(scope="module")
def template(tmp_path_factory):
    path = sample.build(tmp_path_factory.mktemp("t") / "Sample.docx")
    return core.Template(path)


def text_of(path):
    doc = Document(path)
    lines = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            lines.append(" | ".join(c.text for c in row.cells))
    lines.append(doc.sections[0].header.paragraphs[0].text)
    return "\n".join(lines)


def make_doc(tmp_path, paragraphs, name="t.docx"):
    doc = Document()
    for p in paragraphs:
        if isinstance(p, list):            # a list is one paragraph made of several runs
            para = doc.add_paragraph()
            for piece in p:
                para.add_run(piece)
        else:
            doc.add_paragraph(p)
    path = tmp_path / name
    doc.save(path)
    return path


def fill(tmp_path, paragraphs, values, **kw):
    path = make_doc(tmp_path, paragraphs)
    out = tmp_path / "out.docx"
    core.build_contract(core.Template(path), values, out, **kw)
    return [p.text for p in Document(out).paragraphs]


# ------------------------------------------------------------- formats ---

def test_words():
    assert core.words(0) == "zero"
    assert core.words(21) == "twenty-one"
    assert core.words(1250) == "one thousand two hundred fifty"
    assert core.words(3_000_017) == "three million seventeen"


@pytest.mark.parametrize("raw", ["10/5/2026", "10-05-26", "2026-10-05", "October 5, 2026",
                                 "Oct 5 2026", "5 October 2026", "5th day of October, 2026",
                                 "Oct. 5, 2026", datetime.datetime(2026, 10, 5)])
def test_dates_parse(raw):
    assert core.parse_date(raw) == datetime.date(2026, 10, 5)


@pytest.mark.parametrize("raw", ["13/45/2026", "soon", "February 30, 2026"])
def test_bad_dates(raw):
    with pytest.raises(ValueError):
        core.parse_date(raw)


def test_formats():
    assert core.format_value("date-formal", "11/1/2026") == "1st day of November, 2026"
    assert core.format_value("date-formal", "11/12/2026") == "12th day of November, 2026"
    assert core.format_value("date-short", "Nov 2 2026") == "11/02/2026"
    assert core.format_value("money", "$12,500") == "$12,500.00"
    assert core.format_value("money-words", "1") == "One Dollar ($1.00)"
    assert core.format_value("money-words", "21.01") == "Twenty-One Dollars and One Cent ($21.01)"
    assert core.format_value("number-words", "30") == "thirty (30)"
    assert core.format_value("number", 1250.0) == "1,250"
    assert core.format_value("upper", "Acme") == "ACME"
    with pytest.raises(ValueError):
        core.format_value("money", "twelve")
    with pytest.raises(ValueError):
        core.format_value("number-words", "2.5")


# --------------------------------------------------------- the template ---

def test_scan(template):
    assert template.problems == []
    f = template.fields
    assert f["effective date"].kind == "date"
    assert f["total fee"].kind == "money"
    assert f["include non-compete"].kind == "yesno"
    assert f["client entity type"].kind == "choice"
    assert f["governing state"].choices == ["Texas", "Oklahoma", "Louisiana"]
    assert f["scope of services"].kind == "long"
    names = [x.name for x in template.field_list()]
    assert names[:2] == ["Effective Date", "Client Name"]      # reading order


def test_full_contract(template, tmp_path):
    out = tmp_path / "c.docx"
    report = core.build_contract(template, VALUES, out)
    text = text_of(out)
    assert "{{" not in text and "}}" not in text
    assert "5th day of October, 2026" in text
    assert "Twelve Thousand Five Hundred Dollars and Fifty Cents ($12,500.50)" in text
    assert "twelve (12) months" in text
    assert "Tarrant County" in text and "State of Texas" in text
    assert "Non-Solicitation" not in text                        # switched off
    assert "Guarantee" not in text                               # no guarantor named
    assert "late fee" not in text.lower().split("fee schedule")[0]
    assert "Late fee | None" in text
    assert "ACME WIDGETS, INC." in text
    assert "Services Agreement – Acme Widgets, Inc." in text  # header
    assert report.blanks == []


def test_switches_on(template, tmp_path):
    out = tmp_path / "c.docx"
    values = dict(VALUES, **{"Include Non-Compete": True, "Governing State": "Louisiana",
                             "Late Fee": "75", "Guarantor Name": "J. Smith"})
    core.build_contract(template, values, out)
    text = text_of(out)
    assert "Non-Solicitation" in text
    assert "State of Louisiana." in text and "Tarrant" not in text
    assert "a late fee of $75.00 applies" in text
    assert "Late fee | $75.00" in text
    assert "J. Smith guarantees" in text


def test_blanks_reported(template, tmp_path):
    report = core.build_contract(template, {"Client Name": "X"}, tmp_path / "c.docx")
    assert "Effective Date" in report.blanks
    assert core.BLANK in text_of(tmp_path / "c.docx")


def test_template_untouched(template, tmp_path):
    before = template.path.read_bytes()
    core.build_contract(template, VALUES, tmp_path / "c.docx")
    assert template.path.read_bytes() == before


def test_problems_with_values(template):
    bad = dict(VALUES, **{"Effective Date": "someday", "Total Fee": "lots", "Client Entity Type": "trust"})
    names = {n for n, _ in core.problems_with(template, bad)}
    assert names == {"Effective Date", "Total Fee", "Client Entity Type"}


def test_highlight_is_valid(template, tmp_path):
    out = tmp_path / "c.docx"
    core.build_contract(template, VALUES, out, highlight=True)
    xml = zipfile.ZipFile(out).read("word/document.xml").decode()
    assert 'w:highlight w:val="yellow"' in xml
    Document(out)                                                # still opens


# ------------------------------------------------ the awkward Word cases ---

def test_split_runs(tmp_path):
    lines = fill(tmp_path, [["Hello {", "{Na", "me}", "} and {{ name }}."]], {"Name": "Ann"})
    assert lines == ["Hello Ann and Ann."]


def test_formatting_follows_the_name(tmp_path):
    path = tmp_path / "t.docx"
    doc = Document()
    p = doc.add_paragraph("To ")
    p.add_run("{{")
    p.add_run("Name").bold = True
    p.add_run("}}.")
    doc.save(path)
    out = tmp_path / "o.docx"
    core.build_contract(core.Template(path), {"Name": "Ann"}, out)
    runs = [(r.text, r.bold) for r in Document(out).paragraphs[0].runs]
    assert ("Ann", True) in runs


def test_inline_condition_whole_paragraph_goes(tmp_path):
    lines = fill(tmp_path, ["A", "{{#if Extra}}An extra clause.{{/if}}", "B"], {"Extra": False})
    assert lines == ["A", "B"]


def test_nested_blocks(tmp_path):
    paras = ["start", "{{#if Outer}}", "outer", "{{#if Inner}}", "inner", "{{/if}}", "{{/if}}", "end"]
    assert fill(tmp_path, paras, {"Outer": True, "Inner": False}) == ["start", "outer", "end"]
    assert fill(tmp_path, paras, {"Outer": False, "Inner": True}) == ["start", "end"]
    assert fill(tmp_path, paras, {"Outer": True, "Inner": True}) == ["start", "outer", "inner", "end"]


def test_not_and_not_equal(tmp_path):
    paras = ["{{#if not Rush}}normal{{else}}rush{{/if}} {{#if State != Texas}}elsewhere{{/if}}"]
    assert fill(tmp_path, paras, {"Rush": False, "State": "texas"}) == ["normal "]
    assert fill(tmp_path, paras, {"Rush": True, "State": "Ohio"}) == ["rush elsewhere"]


def test_block_removes_table(tmp_path):
    doc = Document()
    doc.add_paragraph("before")
    doc.add_paragraph("{{#if Schedule}}")
    doc.add_table(rows=1, cols=1).cell(0, 0).text = "table"
    doc.add_paragraph("{{/if}}")
    doc.add_paragraph("after")
    path = tmp_path / "t.docx"
    doc.save(path)
    out = tmp_path / "o.docx"
    core.build_contract(core.Template(path), {"Schedule": False}, out)
    d = Document(out)
    assert [p.text for p in d.paragraphs] == ["before", "after"] and not d.tables


def test_emptied_cell_keeps_a_paragraph(tmp_path):
    doc = Document()
    doc.add_table(rows=1, cols=1).cell(0, 0).text = "{{#if X}}gone{{/if}}"
    path = tmp_path / "t.docx"
    doc.save(path)
    out = tmp_path / "o.docx"
    core.build_contract(core.Template(path), {"X": False}, out)
    xml = zipfile.ZipFile(out).read("word/document.xml").decode()
    assert "<w:tc>" in xml and "<w:p" in xml.split("<w:tc>")[1]


def test_long_text_line_breaks(tmp_path):
    path = make_doc(tmp_path, ["{{Scope | long}}"])
    out = tmp_path / "o.docx"
    core.build_contract(core.Template(path), {"Scope": "one\ntwo"}, out)
    xml = zipfile.ZipFile(out).read("word/document.xml").decode()
    assert "<w:br/>" in xml


def test_dotx_becomes_docx(tmp_path):
    src = make_doc(tmp_path, ["Hi {{Name}}"])
    dotx = tmp_path / "t.dotx"
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dotx, "w") as zout:
        for i in zin.infolist():
            data = zin.read(i.filename)
            if i.filename == "[Content_Types].xml":
                data = data.replace(core.DOCUMENT_TYPE.encode(), core.TEMPLATE_TYPE.encode())
            zout.writestr(i, data)
    out = tmp_path / "o.docx"
    core.build_contract(core.Template(dotx), {"Name": "Ann"}, out)
    assert core.TEMPLATE_TYPE.encode() not in zipfile.ZipFile(out).read("[Content_Types].xml")
    assert Document(out).paragraphs[0].text == "Hi Ann"


# ------------------------------------------------- mistakes in templates ---

@pytest.mark.parametrize("paras, words", [
    (["{{#if X}}", "text"], "never closed"),
    (["text", "{{/if}}"], "no {{#if ...}} line"),
    (["{{#if X}} starts here", "{{/if}}"], "line of its own"),
    (["{{#if X}} starts here", "end"], "without its partner"),
    (["Dear {{Client Name}"], "Unmatched braces"),
    (["{{Fee | dollars-and-cents}}"], "Unknown format"),
])
def test_template_mistakes_explained(tmp_path, paras, words):
    t = core.Template(make_doc(tmp_path, paras))
    assert any(words in p for p in t.problems), t.problems


def test_if_across_table_boundary(tmp_path):
    doc = Document()
    doc.add_paragraph("{{#if X}}")
    doc.add_table(rows=1, cols=1).cell(0, 0).text = "{{/if}}"
    path = tmp_path / "t.docx"
    doc.save(path)
    t = core.Template(path)
    assert any("different places" in p for p in t.problems), t.problems


# --------------------------------------------------------- the extras ---

def test_make_template(tmp_path):
    src = make_doc(tmp_path, [["Between TMAI and Acme ", "Corporation", " (Acme)."],
                              "Fee: $5,000.00 due January 2, 2027."])
    out = tmp_path / "new.docx"
    counts = core.make_template(src, out, [("Acme", "Short Name", ""),
                                           ("Acme Corporation", "Client Name", ""),
                                           ("$5,000.00", "Fee", "money")])
    assert counts == {"Acme": 1, "Acme Corporation": 1, "$5,000.00": 1}
    lines = [p.text for p in Document(out).paragraphs]
    assert lines[0] == "Between TMAI and {{Client Name}} ({{Short Name}})."
    assert lines[1] == "Fee: {{Fee | money}} due January 2, 2027."
    found = {text for text, _, _ in core.find_candidates(src)}
    assert {"$5,000.00", "January 2, 2027"} <= found


def test_spreadsheet_round_trip(template, tmp_path):
    from openpyxl import load_workbook
    sheet = tmp_path / "batch.xlsx"
    core.blank_sheet(template, sheet)
    wb = load_workbook(sheet)
    ws = wb.active
    headers = [c.value for c in ws[1]]
    assert headers[-1] == core.FILE_NAME_COLUMN
    for row in (dict(VALUES, **{"Include Non-Compete": "Yes", "Effective Date": datetime.datetime(2026, 10, 5)}),
                dict(VALUES, **{"Client Name": "Beta LLC", "Total Fee": 900, core.FILE_NAME_COLUMN: "Beta"}),
                dict(VALUES, **{"Client Name": "Bad Co", "Total Fee": "lots"})):
        ws.append([row.get(h, "") for h in headers])
    wb.save(sheet)
    out = tmp_path / "out"
    out.mkdir()
    lines = []
    made, skipped = core.batch(template, sheet, out, say=lines.append)
    assert (made, skipped) == (2, 1), lines
    names = sorted(p.name for p in out.iterdir())
    assert names == ["Beta.docx", "Sample - Acme Widgets, Inc.docx"]
    assert "Non-Solicitation" in text_of(out / names[1])
    assert "$900.00" in text_of(out / "Beta.docx")


def test_csv(template, tmp_path):
    sheet = tmp_path / "b.csv"
    sheet.write_text("Client Name,Effective Date,Unknown Column\nAcme,10/5/2026,x\n", encoding="utf-8")
    lines = []
    made, _ = core.batch(template, sheet, tmp_path, say=lines.append)
    assert made == 1
    assert any("Unknown Column" in l for l in lines)


def test_answers_round_trip(template, tmp_path):
    path = tmp_path / "a.json"
    core.save_answers(template, {"client name": "Acme", "Include Non-Compete": True}, path)
    data = core.load_answers(path)
    assert data["values"] == {"Client Name": "Acme", "Include Non-Compete": True}


# ------------------------------------- lessons from the sample MOU (Oct 2026) ---

def _rewrite(path, name, change):
    """Apply change(bytes) -> bytes to one part of a .docx, in place."""
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for i in zin.infolist():
            data = zin.read(i.filename)
            zout.writestr(i, change(data) if i.filename == name else data)
    tmp.replace(path)


def test_straight_quotes_find_curly_ones(tmp_path):
    src = make_doc(tmp_path, ["Rights to God’s High Calling for Women by “John”."])
    out = tmp_path / "made.docx"
    counts = core.make_template(src, out, [("God's High Calling for Women", "Book Title", ""),
                                           ('"John"', "Author", "")])
    assert counts == {"God's High Calling for Women": 1, '"John"': 1}
    assert Document(out).paragraphs[0].text == "Rights to {{Book Title}} by {{Author}}."


def test_new_template_is_cleaned(tmp_path):
    src = make_doc(tmp_path, ["Between TMAI and Acme."])
    _rewrite(src, "word/settings.xml",
             lambda d: d.replace(b"</w:settings>", b"<w:trackRevisions/></w:settings>"))
    _rewrite(src, "word/document.xml",
             lambda d: d.replace(b"<w:t>Between", b'<w:rPr><w:spacing w:val="53"/></w:rPr><w:t>Between'))
    assert any("Track Changes is switched on" in n for n in core.Template(src).warnings)
    out = tmp_path / "made.docx"
    core.make_template(src, out, [("Acme", "Client", "")])
    z = zipfile.ZipFile(out)
    assert b"trackRevisions" not in z.read("word/settings.xml")
    assert b"w:spacing" not in z.read("word/document.xml")
    kept = tmp_path / "kept.docx"
    core.make_template(src, kept, [("Acme", "Client", "")], reset_spacing=False)
    assert b'w:spacing w:val="53"' in zipfile.ZipFile(kept).read("word/document.xml")


def test_warnings_for_struck_shaded_and_tracked(tmp_path):
    doc = Document()
    p = doc.add_paragraph("Pay ")
    p.add_run("the one-time fee").font.strike = True
    p.add_run(" to ")
    p.add_run("{{Address}}")
    doc.add_paragraph("Hello {{Name}}")
    path = tmp_path / "t.docx"
    doc.save(path)
    _rewrite(path, "word/document.xml", lambda d: d.replace(
        b"<w:t>{{Address}}</w:t>",
        b'<w:rPr><w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/></w:rPr><w:t>{{Address}}</w:t>').replace(
        b"<w:t>Hello {{Name}}</w:t></w:r>",
        b'<w:t>Hello {{Name}}</w:t></w:r><w:ins w:id="1" w:author="x"><w:r><w:t>!</w:t></w:r></w:ins>'))
    t = core.Template(path)
    notes = " ".join(t.warnings)
    assert "struck through" in notes and "one-time fee" in notes
    assert "{{Address}} is shaded" in notes
    assert "tracked change(s) not yet accepted" in notes
    assert t.problems == []                     # notes, not problems


def test_removed_clause_leaves_one_blank_line(tmp_path):
    paras = ["A", "", "{{#if X}}", "clause", "{{/if}}", "", "B"]
    assert fill(tmp_path, paras, {"X": False}) == ["A", "", "B"]
    assert fill(tmp_path, paras, {"X": True}) == ["A", "", "clause", "", "B"]
    inline = ["A", "", "{{#if X}}clause{{/if}}", "", "B"]
    assert fill(tmp_path, inline, {"X": False}) == ["A", "", "B"]
    spaced = ["A", "", "", "B"]                 # blank lines the author typed are left alone
    assert fill(tmp_path, spaced, {}) == spaced


def test_contract_gets_its_own_dates(template, tmp_path):
    out = tmp_path / "c.docx"
    core.build_contract(template, VALUES, out)
    xml = zipfile.ZipFile(out).read("docProps/core.xml").decode()
    assert datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d") in xml


def test_vietnamese_names(tmp_path):
    lines = fill(tmp_path, ["{{Publisher}}, signed by {{Signatory | upper}}"],
                 {"Publisher": "Trích Dẫn Tin Lành", "Signatory": "Phạm Thị Anh Thư"})
    assert lines == ["Trích Dẫn Tin Lành, signed by PHẠM THỊ ANH THƯ"]
