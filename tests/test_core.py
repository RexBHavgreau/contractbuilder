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


def test_template_authoring_examples_fill_a_real_word_template(tmp_path):
    """Every documented format and condition is exercised through a DOCX."""
    paragraphs = [
        "{{When | date}} | {{When | date-formal}} | {{When | date-short}}",
        "{{Fee | money}} | {{Fee | money-words}} | {{Fee | money-whole}}",
        "{{Count | number}} | {{Count | number-words}} | {{Name | upper}}",
        "{{Description | long}}",
        "{{Titles | list}} ({{Titles | plural: work, works}})",
        "{{State | choice: Texas, Oklahoma}}",
        "Selected state: {{State | choice: Texas, Oklahoma}}.",
        "{{#if Include Clause}}Included clause.{{/if}}",
        "{{#if State = Texas}}Texas clause.{{else}}Other-state clause.{{/if}}",
        "{{#if State != Texas}}Not Texas.{{/if}}",
        "{{#if not Guarantor}}No guarantor.{{/if}}",
        "{{#if Guarantor}}{{Guarantor}} guarantees performance.{{/if}}",
        "Payment is due{{#if Late Fee}}, with a fee of {{Late Fee | money}}{{/if}}.",
    ]
    values = {
        "When": "10/5/2026", "Fee": "12500.50", "Count": "30",
        "Name": "Acme Corporation", "Description": "First line\nSecond line",
        "Titles": "Book A\nBook B", "State": "Texas",
        "Include Clause": True, "Guarantor": "", "Late Fee": "75",
    }
    source = make_doc(tmp_path, paragraphs)
    output = tmp_path / "filled.docx"
    template = core.Template(source)
    assert template.problems == []
    core.build_contract(template, values, output)
    rendered = "\n".join(p.text for p in Document(output).paragraphs)

    for expected in (
        "October 5, 2026", "5th day of October, 2026", "10/05/2026",
        "$12,500.50", "Twelve Thousand Five Hundred Dollars and Fifty Cents ($12,500.50)",
        "$12,501", "30", "thirty (30)", "ACME CORPORATION",
        "First line", "Second line", "Book A and Book B", "(works)", "Selected state: Texas.",
        "Texas clause.", "No guarantor.", "$75.00",
    ):
        assert expected in rendered
    for omitted in ("Other-state clause.", "Not Texas.", "guarantees performance."):
        assert omitted not in rendered


# ----------------------------------------- spaces around inline wording (T-049-E) ---

INLINE = "of X, {{#if A = B}} a phrase {{else}} another {{/if}} organized"


def test_inline_wording_kept_leaves_single_spaces(tmp_path):
    assert fill(tmp_path, [INLINE], {"A": "B"}) == ["of X, a phrase organized"]


def test_inline_else_wording_leaves_single_spaces(tmp_path):
    assert fill(tmp_path, [INLINE], {"A": "C"}) == ["of X, another organized"]


def test_a_dropped_phrase_between_spaces_leaves_one_space(tmp_path):
    paras = ["Pay {{#if Rush}}promptly{{/if}} now"]
    assert fill(tmp_path, paras, {"Rush": False}) == ["Pay now"]
    assert fill(tmp_path, paras, {"Rush": True}) == ["Pay promptly now"]


def test_a_dropped_phrase_does_not_leave_a_space_before_punctuation(tmp_path):
    paras = ["Pay today {{#if Late}}with a fee{{/if}}."]
    assert fill(tmp_path, paras, {"Late": False}) == ["Pay today."]
    assert fill(tmp_path, paras, {"Late": True}) == ["Pay today with a fee."]


def test_a_phrase_that_starts_with_punctuation_joins_the_word_before(tmp_path):
    paras = ["Fee {{#if Late}}, plus a late fee{{/if}} due"]
    assert fill(tmp_path, paras, {"Late": True}) == ["Fee, plus a late fee due"]


def test_spaces_the_author_typed_elsewhere_are_not_touched(tmp_path):
    paras = ["Two  spaces here, {{#if X}}yes{{/if}} and  there"]
    assert fill(tmp_path, paras, {"X": True}) == ["Two  spaces here, yes and  there"]


def test_wording_with_no_spaces_around_the_markers_is_unchanged(tmp_path):
    paras = ["Late{{#if Late}}, with a fee{{/if}}."]
    assert fill(tmp_path, paras, {"Late": True}) == ["Late, with a fee."]
    assert fill(tmp_path, paras, {"Late": False}) == ["Late."]


def test_inline_wording_inside_a_table_cell_is_tidied(tmp_path):
    doc = Document()
    doc.add_table(rows=1, cols=1).cell(0, 0).text = "a {{#if X}} b {{else}} c {{/if}} d"
    path = tmp_path / "cell.docx"
    doc.save(path)
    out = tmp_path / "cell-out.docx"
    core.build_contract(core.Template(path), {"X": True}, out)
    assert Document(out).tables[0].cell(0, 0).text == "a b d"


def test_inline_wording_split_across_runs_is_tidied(tmp_path):
    paras = [["of X, {{#if A = B}", "} a phrase {{el", "se}} another {{/if}} next"]]
    assert fill(tmp_path, paras, {"A": "B"}) == ["of X, a phrase next"]
