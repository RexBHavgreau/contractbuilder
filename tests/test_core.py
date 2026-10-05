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
    src = make_doc(tmp_path, ["Rights to Jane’s Sample Book by “John”."])
    out = tmp_path / "made.docx"
    counts = core.make_template(src, out, [("Jane's Sample Book", "Book Title", ""),
                                           ('"John"', "Author", "")])
    assert counts == {"Jane's Sample Book": 1, '"John"': 1}
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
                 {"Publisher": "Nhà Xuất Bản Ánh Sáng", "Signatory": "Nguyễn Văn Bình"})
    assert lines == ["Nhà Xuất Bản Ánh Sáng, signed by NGUYỄN VĂN BÌNH"]


# ---------------------------- lessons from the two-book Italian MOU (Oct 2026) ---

def test_list_and_plural(tmp_path):
    paras = ["Rights to {{Titles | list}} (the {{Titles | plural: work, works}}), which "
             "{{Titles | plural: contains / contain}} no libel. Term: {{Years}} {{Years | plural: year, years}}."]
    one = fill(tmp_path, paras, {"Titles": "Book A", "Years": "1"})
    assert one == ["Rights to Book A (the work), which contains no libel. Term: 1 year."]
    two = fill(tmp_path, paras, {"Titles": "Book A\nBook B\n", "Years": "10"})
    assert two == ["Rights to Book A and Book B (the works), which contain no libel. Term: 10 years."]
    three = fill(tmp_path, paras, {"Titles": "A\nB\nC", "Years": "2"})
    assert three[0].startswith("Rights to A, B, and C (the works)")


def test_list_and_plural_kinds(tmp_path):
    t = core.Template(make_doc(tmp_path, ["{{Titles | list}} {{Titles | plural: work, works}} "
                                          "{{Years | plural: year, years}} {{Bad | plural: only}}"]))
    assert t.fields["titles"].kind == "long"
    assert t.fields["years"].kind == "number"
    assert any("needs two wordings" in p for p in t.problems)
    assert t.fields["titles"].preview("A\nB") == "A and B  |  counts as 2"


def test_list_joining_words_are_not_italic(tmp_path):
    doc = Document()
    doc.add_paragraph("Rights to ").add_run("{{Titles | list}}").italic = True
    path = tmp_path / "t.docx"
    doc.save(path)
    out = tmp_path / "o.docx"
    core.build_contract(core.Template(path), {"Titles": "Book A\nBook B"}, out)
    runs = [(r.text, bool(r.italic)) for r in Document(out).paragraphs[0].runs]
    assert runs == [("Rights to ", False), ("Book A", True), (" and ", False), ("Book B", True)]


def test_money_whole():
    assert core.format_value("money-whole", "12500") == "$12,500"
    assert core.format_value("money-whole", "$12,499.50") == "$12,500"


def test_whole_words_only(tmp_path):
    src = make_doc(tmp_path, [["The works and networks", "\t", "Jordan Smith"]])
    out = tmp_path / "made.docx"
    counts = core.make_template(src, out, [("works", "Titles", "plural: work, works"),
                                           ("Jordan Smith", "Signatory", "")])
    assert counts == {"works": 1, "Jordan Smith": 1}
    assert Document(out).paragraphs[0].text == \
        "The {{Titles | plural: work, works}} and networks\t{{Signatory}}"


def _tracked(tmp_path):
    """A contract edited with Track Changes on, with a comment, as MOUs arrive."""
    path = make_doc(tmp_path, ["Rights to the work by Alice.", "Second paragraph."])
    W = b'w:author="BH" w:date="2026-10-01T00:00:00Z"'
    _rewrite(path, "word/document.xml", lambda d: d.replace(
        b"<w:r><w:t>Rights to the work by Alice.</w:t></w:r>",
        b"<w:r><w:t>Rights to the work</w:t></w:r>"
        b'<w:ins w:id="1" ' + W + b"><w:r><w:t>s</w:t></w:r></w:ins>"
        b'<w:commentRangeStart w:id="0"/>'
        b"<w:r><w:t xml:space=\"preserve\"> by </w:t></w:r>"
        b'<w:del w:id="2" ' + W + b"><w:r><w:delText>Alice</w:delText></w:r></w:del>"
        b'<w:ins w:id="3" ' + W + b"><w:r><w:t>Bob</w:t></w:r></w:ins>"
        b'<w:commentRangeEnd w:id="0"/><w:r><w:commentReference w:id="0"/></w:r>'
        b"<w:r><w:t>.</w:t></w:r>"))
    return path


def test_tracked_changes_accepted_when_making_template(tmp_path):
    src = _tracked(tmp_path)
    assert any("tracked change" in n for n in core.Template(src).warnings)
    out = tmp_path / "made.docx"
    notes = []
    core.make_template(src, out, [("Bob", "Author", "")], notes=notes)
    assert notes == ["accepted 3 tracked change(s)", "removed 1 comment(s)"]
    xml = zipfile.ZipFile(out).read("word/document.xml")
    for leftover in (b"<w:ins ", b"<w:del ", b"delText", b"comment"):
        assert leftover not in xml
    assert Document(out).paragraphs[0].text == "Rights to the works by {{Author}}."
    t = core.Template(out)
    assert t.warnings == [] and t.problems == []
    kept = tmp_path / "kept.docx"
    core.make_template(src, kept, [], accept_changes=False)
    assert b"<w:del " in zipfile.ZipFile(kept).read("word/document.xml")


def test_deleted_paragraph_mark_joins_paragraphs():
    from lxml import etree
    xml = (f'<w:body xmlns:w="{core.W_NS}"><w:p><w:pPr><w:rPr><w:del w:id="1" w:author="x"/></w:rPr></w:pPr>'
           '<w:r><w:t>one </w:t></w:r></w:p><w:p><w:r><w:t>two</w:t></w:r></w:p></w:body>')
    root = etree.fromstring(xml)
    core.accept_revisions(root)
    assert [core.para_text(p) for p in root.iter(core.w("p"))] == ["one two"]


def test_link_warning(tmp_path):
    path = make_doc(tmp_path, ["Email {{Email}}"])
    _rewrite(path, "word/document.xml", lambda d: d.replace(
        b"<w:r><w:t>Email {{Email}}</w:t></w:r>",
        b'<w:r><w:t xml:space="preserve">Email </w:t></w:r><w:hyperlink w:anchor="x"><w:r><w:t>{{Email}}</w:t></w:r></w:hyperlink>'))
    assert any("inside a link" in n for n in core.Template(path).warnings)


# ----------------------- field sets, works, parties, rights, territory (Build 4) ---

import fieldsets                                              # noqa: E402

PUB = fieldsets.BUILTIN[0]


@pytest.fixture(scope="module")
def mou(tmp_path_factory):
    path = sample.build_mou(tmp_path_factory.mktemp("m") / "MOU.docx")
    return core.Template(path, PUB)


def mou_values(**changes):
    v = {
        "Parties": [
            {"Party Name": fieldsets.TMAI, "Party Role": "proprietor",
             "Party Description": "the authorized representative of the author",
             "Party Address": "100 Example Street, Springfield, U.S.A.",
             "Party Signatory": "Sam Taylor", "Party Signatory Title": "Director of Publishing"},
            {"Party Name": "Nhà Xuất Bản Ánh Sáng", "Party Role": "publisher", "Party Address": "Huế",
             "Party Signatory": "Binh Nguyen", "Party Signatory Title": "Director"}],
        "Works": [{"Work Title": "Jane’s Sample Book", "Work Author": "Joan Example",
                   "Work Original Publisher": "Example Press", "Work Copyright": "©1987 by Joan Example"}],
        "Language": "Vietnamese", "Rights Licensed": ["Print"], "Territory": {"worldwide": False, "place": "Vietnam"},
        "License Type": "Exclusive", "Term Years": "1", "Expiration Date": "6/1/2031",
        "Publication Deadline Months": "18", "Copies to Proprietor": "7", "Signing Deadline": "10/15/2026",
    }
    v.update(changes)
    return v


def mou_text(template, values, tmp_path):
    out = tmp_path / "c.docx"
    report = core.build_contract(template, values, out)
    return "\n".join(p.text for p in Document(out).paragraphs), report


def test_mou_template_reads_cleanly(mou):
    assert mou.problems == [] and mou.warnings == []
    sections = [title for title, _ in mou.layout()]
    assert sections[:3] == ["Parties", "Works", "Edition"]
    assert mou.groups["parties"].first_count == 2          # not 3, though {{Party 3 Name}} is used
    assert mou.groups["works"].first_count == 1
    assert mou.fields["rights licensed"].kind == "checklist"
    assert mou.fields["territory"].kind == "territory"
    assert fieldsets.best_for(mou.path, fieldsets.BUILTIN) is PUB


def test_one_work_one_format_one_place(mou, tmp_path):
    text, report = mou_text(mou, mou_values(), tmp_path)
    assert "rights to Jane’s Sample Book authored by Joan Example (hereinafter the work)" in text
    assert "edition of the work in print format, in Vietnam (hereinafter the territory), for a period " \
           "of one (1) year" in text
    assert "The translated work shall be an accurate translation." in text
    assert text.count("This book was first published by") == 1
    assert "an exclusive agreement" in text
    assert "waives any licensing fee" in text and "Party 3" not in text
    assert text.count("______________________________   Date") == 2
    assert report.blanks == []


def test_several_works_and_rights(mou, tmp_path):
    works = [{"Work Title": "Sample Title", "Work Author": "Joan Example"},
             {"Work Title": "Sample Title Workbook", "Work Author": "Joan Example"}]
    text, _ = mou_text(mou, mou_values(Works=works, **{
        "Rights Licensed": ["Print", "Electronic (with appropriate digital rights management)", "Audio book"],
        "Territory": {"worldwide": True, "place": "ignored"}, "Term Years": "10"}), tmp_path)
    assert "rights to Sample Title and Sample Title Workbook authored by " \
           "Joan Example (hereinafter the works)" in text      # the author once, not twice
    assert "in print, electronic (with the appropriate digital rights management), and audio book formats, " \
           "throughout the world" in text
    assert text.count("This book was first published by") == 2
    assert "The translated works shall be accurate translations." in text


def test_all_formats_wins(mou, tmp_path):
    text, _ = mou_text(mou, mou_values(**{"Rights Licensed": ["Print", "All formats"]}), tmp_path)
    assert "in all formats," in text


def test_a_third_party(mou, tmp_path):
    parties = mou_values()["Parties"] + [{"Party Name": "Third Ministry", "Party Role": "distributor",
                                          "Party Address": "Paris", "Party Signatory": "A. B."}]
    text, _ = mou_text(mou, mou_values(Parties=parties), tmp_path)
    assert "and Third Ministry (hereinafter the distributor), Paris, witnesses" in text
    assert text.splitlines()[0] == \
        "The Master’s Academy International, Nhà Xuất Bản Ánh Sáng, and Third Ministry"
    assert text.count("______________________________   Date") == 3


def test_not_relevant_fields(mou, tmp_path):
    values = mou_values(**{"Funding Amount": "12500", "Free Copies for Training": core.NOT_RELEVANT})
    values["Parties"][0]["Party Description"] = core.NOT_RELEVANT
    text, report = mou_text(mou, values, tmp_path)
    assert "fund $12,500 US dollars" in text
    assert "training centers" not in text                    # the clause depending on it went
    assert "International (hereinafter the proprietor)" in text
    assert report.blanks == []


def test_expected_gaps(mou):
    values = mou_values(Language="", Territory=core.NOT_RELEVANT)
    values["Works"].append({"Work Title": "Second", "Work Author": ""})
    gaps = mou.expected_gaps(values)
    assert "Language (empty)" in gaps
    assert "Territory (marked not relevant)" in gaps
    assert "Work 2 Author (empty)" in gaps
    assert mou.expected_gaps(mou_values()) == []


def test_template_missing_expected_fields(tmp_path):
    t = core.Template(make_doc(tmp_path, ["Between {{Party 1 Name}} and {{Party 2 Name}} for {{Work Title}}."]), PUB)
    notes = " ".join(t.warnings)
    assert "Territory" in notes and "Rights Licensed" in notes and "Language" in notes
    assert "Party Name" not in notes and "Work Title" not in notes


def test_problems_with_publishing_values(mou):
    bad = mou_values(**{"Expiration Date": "someday", "Rights Licensed": ["Print", "Hologram"]})
    bad["Works"][0]["Work Title"] = core.NOT_RELEVANT          # not relevant is not a problem
    names = {n for n, _ in core.problems_with(mou, bad)}
    assert names == {"Expiration Date", "Rights Licensed"}


def test_each_without_field_set(tmp_path):
    paras = ["Books: {{Book Title | list}}.", "{{#each Books}}", "{{Book Title}} by {{Book Author}}",
             "{{/each}}", "End."]
    t = core.Template(make_doc(tmp_path, paras))
    assert t.problems == [] and "books" in t.groups
    lines = fill(tmp_path, paras, {"Books": [{"Book Title": "A", "Book Author": "X"},
                                             {"Book Title": "B", "Book Author": "Y"}]})
    assert lines == ["Books: A and B.", "A by X", "B by Y", "End."]


@pytest.mark.parametrize("paras, words", [
    (["{{#each Works}}", "x"], "never closed with {{/each}}"),
    (["x", "{{/each}}"], "no {{#each"),
    (["{{#each A}}", "{{#each B}}", "x", "{{/each}}", "{{/each}}"], "inside another"),
    (["Titles {{#each Works}} here"], "line of their own"),
])
def test_each_mistakes(tmp_path, paras, words):
    t = core.Template(make_doc(tmp_path, paras))
    assert any(words in p for p in t.problems), t.problems


def test_spreadsheet_with_works_and_parties(mou, tmp_path):
    from openpyxl import load_workbook
    sheet = tmp_path / "s.xlsx"
    core.blank_sheet(mou, sheet)
    ws = load_workbook(sheet).active
    headers = [c.value for c in ws[1]]
    assert {"Party 1 Name", "Party 3 Name", "Work 1 Title", "Work 2 Title", "Rights Licensed",
            "Territory"} <= set(headers)
    row = {"Party 1 Name": "TMAI", "Party 1 Role": "proprietor", "Party 2 Name": "Pub", "Party 2 Role": "publisher",
           "Work 1 Title": "One", "Work 1 Author": "Example", "Work 2 Title": "Two", "Work 2 Author": "Example",
           "Language": "Italian", "Rights Licensed": "Print, Audio book", "Territory": "Worldwide",
           "Expiration Date": datetime.datetime(2036, 9, 18), "One-time Fee": "N/A"}
    wb = load_workbook(sheet)
    wb.active.append([row.get(h, "") for h in headers])
    wb.save(sheet)
    lines = []
    made, skipped = core.batch(mou, sheet, tmp_path, say=lines.append)
    assert (made, skipped) == (1, 0), lines
    out = next(tmp_path.glob("MOU - *.docx"))
    assert out.name == "MOU - Pub - One.docx"
    text = "\n".join(p.text for p in Document(out).paragraphs)
    assert "rights to One and Two" in text and "in print and audio book formats, throughout the world" in text


def test_field_sets_saved_and_loaded(tmp_path):
    fs = fieldsets.FieldSet("Audio rights", ["Parties", "Rights and territory"],
                            [{"name": "Narrator", "kind": "text", "expected": True, "section": "Recording"}])
    path = fieldsets.save(fs, tmp_path)
    assert path.parent.name == "Field sets"
    loaded = fieldsets.find(fieldsets.load_all(tmp_path), "audio rights")
    assert [c["name"] for c in loaded.clusters()] == ["Parties", "Rights and territory", "Recording"]
    t = core.Template(make_doc(tmp_path, ["{{Party 1 Name}} {{Narrator}} {{Territory}}"]), loaded)
    assert any("Rights Licensed" in n for n in t.warnings)
    assert t.fields["narrator"].expected
    assert "{{Narrator}}  (expected)" in loaded.codes()
    fieldsets.delete(loaded)
    assert fieldsets.find(fieldsets.load_all(tmp_path), "audio rights") is None


def test_answers_with_groups_round_trip(mou, tmp_path):
    path = tmp_path / "a.json"
    core.save_answers(mou, mou_values(), path)
    again = core.load_answers(path)["values"]
    assert mou.normalize(again) == mou.normalize(mou_values())
