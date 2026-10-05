"""
TMAI Contract Builder - the engine.
Build 2

A contract template is an ordinary Word document. The wording that stays
the same is simply typed. The parts that change each time are written in
double braces, {{Client Name}}, and optional clauses sit between
{{#if ...}} and {{/if}}. This module finds those and writes a finished
copy with them filled in. The template itself is never changed.

Everything is done on the Word file's own XML, so fonts, numbering,
tables, headers and footers come through exactly as the template has them.
"""
import copy
import csv
import datetime
import io
import json
import pathlib
import re
import sys
import tempfile
import zipfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from lxml import etree

BUILD = "2"
APP_NAME = "TMAI Contract Builder"
BLANK = "__________"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def w(tag):
    return f"{{{W_NS}}}{tag}"


# The parts of a Word file that hold text people read.
CONTENT_PART = re.compile(r"^word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$")
TEMPLATE_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
DOCUMENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"

TOKEN = re.compile(r"\{\{((?:(?!\{\{|\}\}).)*)\}\}", re.S)

# Format words a template may put after the bar, {{Fee | money-words}}.
# Left: what people may type. Right: what it means.
FORMAT_ALIASES = {
    "": "", "text": "",
    "upper": "upper", "caps": "upper", "uppercase": "upper", "capitals": "upper",
    "long": "long", "multiline": "long", "paragraph": "long", "lines": "long",
    "date": "date", "date-formal": "date-formal", "formal-date": "date-formal",
    "date-short": "date-short", "short-date": "date-short",
    "money": "money", "currency": "money", "dollars": "money",
    "money-words": "money-words", "dollars-words": "money-words",
    "number": "number", "num": "number",
    "number-words": "number-words", "words": "number-words",
    "choice": "choice", "list": "choice",
}

# What sort of box the form shows for each format.
KIND_OF_FORMAT = {
    "": "text", "upper": "text", "long": "long",
    "date": "date", "date-formal": "date", "date-short": "date",
    "money": "money", "money-words": "money",
    "number": "number", "number-words": "number",
    "choice": "choice",
}

EXAMPLES = {
    "date": "10/5/2026 or October 5, 2026",
    "money": "12500 or $12,500.00",
    "number": "30",
}


class TemplateError(Exception):
    """A problem with how the template is written, explained for a person."""


# --------------------------------------------------------------- helpers ---

def key(name):
    """Field names match whatever their spacing or capitals."""
    return re.sub(r"\s+", " ", str(name).replace(" ", " ")).strip().lower()


QUOTE_FOLD = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u2032": "'",
                            "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u2033": '"', "\u00a0": " "})


def fold(text):
    """Curly and straight quotes, and non-breaking spaces, compare equal. Lengths are kept."""
    return text.translate(QUOTE_FOLD)


def tidy_name(name):
    return re.sub(r"\s+", " ", str(name).replace(" ", " ")).strip()


def snippet(text, size=70):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= size else text[:size - 1] + "…"


def part_label(name):
    base = name.split("/")[-1]
    if base.startswith("header"):
        return "a header"
    if base.startswith("footer"):
        return "a footer"
    if base.startswith("footnotes"):
        return "the footnotes"
    if base.startswith("endnotes"):
        return "the endnotes"
    return "the main text"


def classify(inner):
    """What a {{...}} is: ('if', expression), ('else', None), ('end', None) or ('field', text)."""
    s = inner.strip()
    m = re.match(r"#\s*if\b(.*)$", s, re.I | re.S)
    if m:
        return "if", m.group(1).strip()
    low = re.sub(r"\s+", "", s.lower())
    if low in ("else", "#else"):
        return "else", None
    if low in ("/if", "endif", "#endif", "/endif"):
        return "end", None
    return "field", s


def parse_field(text):
    """'Fee | money-words' -> ('Fee', 'money-words', []); unknown formats come back as given."""
    name, _, fmt = text.partition("|")
    fmt = fmt.strip()
    options = []
    head = fmt.split(":", 1)[0].strip().lower()
    head = re.sub(r"[\s_]+", "-", head)
    if FORMAT_ALIASES.get(head) == "choice":
        rest = fmt.split(":", 1)[1] if ":" in fmt else ""
        options = [o.strip() for o in rest.split(",") if o.strip()]
    return tidy_name(name), FORMAT_ALIASES.get(head, head), options


def strip_quotes(text):
    return text.strip().strip("\"'“”‘’").strip()


def parse_condition(expr):
    """'not Governing State = Texas' -> ('Governing State', 'Texas', True)."""
    e = expr.strip()
    negate = False
    m = re.match(r"not\s+(.*)$", e, re.I | re.S)
    if m:
        negate, e = True, m.group(1).strip()
    m = re.match(r"(.+?)\s*(!=|=)\s*(.+)$", e, re.S)
    if m:
        name, op, value = m.groups()
        if op == "!=":
            negate = not negate
        return tidy_name(name), strip_quotes(value), negate
    return tidy_name(e), None, negate


def as_bool(raw):
    if isinstance(raw, bool):
        return raw
    s = str(raw or "").strip().lower()
    return s in ("yes", "y", "true", "1", "x", "include", "included", "on", "✓", "✔")


# --------------------------------------------------------------- formats ---

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
        "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
SCALES = [(10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")]

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
MONTHS = {}
for _i, _m in enumerate(MONTH_NAMES, 1):
    MONTHS[_m.lower()] = _i
    MONTHS[_m[:3].lower()] = _i
MONTHS["sept"] = 9


def words(n):
    """1250 -> 'one thousand two hundred fifty'."""
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")
    if n < 1000:
        rest = n % 100
        return ONES[n // 100] + " hundred" + (" " + words(rest) if rest else "")
    for size, label in SCALES:
        if n >= size:
            rest = n % size
            return words(n // size) + " " + label + (" " + words(rest) if rest else "")
    raise ValueError("too large")


def title_words(text):
    return " ".join("-".join(p.capitalize() for p in part.split("-")) for part in text.split(" "))


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def parse_date(raw):
    if isinstance(raw, datetime.datetime):
        return raw.date()
    if isinstance(raw, datetime.date):
        return raw
    s = str(raw).strip().lower()
    if s == "today":
        return datetime.date.today()
    s = re.sub(r"\s+0?0:00(:00)?$", "", s)                 # spreadsheet times
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s)
    s = re.sub(r"\b(the|day|of)\b", " ", s)
    s = re.sub(r"[,\s]+", " ", s).strip()
    try:
        m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
        if m:
            y, mo, d = map(int, m.groups())
            return datetime.date(y, mo, d)
        m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})", s)
        if m:                                              # US order: month first
            mo, d, y = map(int, m.groups())
            return datetime.date(y + 2000 if y < 100 else y, mo, d)
        parts = re.findall(r"[a-z]+|\d+", s)
        months = [MONTHS[p.rstrip(".")] for p in parts if p.isalpha() and p in MONTHS]
        others = [p for p in parts if p.isalpha() and p not in MONTHS]
        nums = [p for p in parts if p.isdigit()]
        if len(months) == 1 and not others and len(nums) == 2:
            years = [n for n in nums if len(n) == 4]
            days = [n for n in nums if len(n) <= 2]
            if len(years) == 1 and len(days) == 1:
                return datetime.date(int(years[0]), months[0], int(days[0]))
    except ValueError:
        raise ValueError("that day does not exist") from None
    raise ValueError("not a date it recognizes; try 10/5/2026 or October 5, 2026")


def parse_amount(raw):
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        raw = repr(raw)
    s = re.sub(r"[\s$,]|usd", "", str(raw).strip().lower())
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError("not a number; type it like 12500 or 12,500.00") from None
    if not d.is_finite():
        raise ValueError("not a number")
    if d < 0:
        raise ValueError("cannot be negative")
    return d


def fmt_money(d):
    d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"${d:,.2f}"


def fmt_money_words(d):
    d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    dollars = int(d)
    cents = int((d - dollars) * 100)
    text = title_words(words(dollars)) + (" Dollar" if dollars == 1 else " Dollars")
    if cents:
        text += " and " + title_words(words(cents)) + (" Cent" if cents == 1 else " Cents")
    return f"{text} ({fmt_money(d)})"


def format_value(fmt, raw):
    """Turn what was typed into what the contract says. Raises ValueError with a reason."""
    if isinstance(raw, str):
        raw = raw.strip()
    if fmt in ("", "choice", "long"):
        return str(raw)
    if fmt == "upper":
        return str(raw).upper()
    if fmt.startswith("date"):
        d = parse_date(raw)
        if fmt == "date-formal":
            return f"{ordinal(d.day)} day of {MONTH_NAMES[d.month - 1]}, {d.year}"
        if fmt == "date-short":
            return f"{d.month:02d}/{d.day:02d}/{d.year}"
        return f"{MONTH_NAMES[d.month - 1]} {d.day}, {d.year}"
    if fmt == "money":
        return fmt_money(parse_amount(raw))
    if fmt == "money-words":
        return fmt_money_words(parse_amount(raw))
    if fmt in ("number", "number-words"):
        d = parse_amount(raw)
        if d != d.to_integral_value():
            if fmt == "number-words":
                raise ValueError("written-out numbers need a whole number")
            return f"{d.normalize():,f}"
        n = int(d)
        return f"{words(n)} ({n:,})" if fmt == "number-words" else f"{n:,}"
    return str(raw)


# ------------------------------------------------------------- the model ---

class Field:
    """One thing that changes from contract to contract."""

    def __init__(self, name):
        self.name = name
        self.key = key(name)
        self.formats = []          # every format it is shown in, in order
        self.options = []          # for choices
        self.as_value = False      # printed somewhere in the contract
        self.in_condition = False  # decides whether a clause appears
        self.compared = []         # values conditions compare it with

    @property
    def kind(self):
        kinds = [KIND_OF_FORMAT.get(f, "text") for f in self.formats]
        if "choice" in kinds or (not self.as_value and self.compared):
            return "choice"
        if not self.as_value:
            return "yesno"
        for k in kinds:
            if k != "text":
                return k
        return "text"

    @property
    def choices(self):
        out = []
        for o in self.options + self.compared:
            if key(o) not in [key(x) for x in out]:
                out.append(o)
        return out

    @property
    def example(self):
        return EXAMPLES.get(self.kind, "")

    def preview(self, raw):
        """What the contract will say, for the hint beside the box."""
        if self.kind in ("yesno", "long", "text", "choice"):
            return ""
        if raw is None or not str(raw).strip():
            return ""
        shown = []
        for f in self.formats:
            if KIND_OF_FORMAT.get(f) == self.kind:
                v = format_value(f, raw)
                if v not in shown:
                    shown.append(v)
        return "  |  ".join(shown)


class Template:
    """A contract template, read and checked. Fields are in reading order."""

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.fields = {}
        self.problems = []
        self.warnings = []          # not wrong, but worth knowing before relying on it
        self.conditions = 0
        self.places = 0
        self._scan()

    @property
    def name(self):
        return self.path.stem

    def field_list(self):
        return list(self.fields.values())

    def value_fields(self):
        return [f for f in self.fields.values() if f.kind != "yesno"]

    def _field(self, name):
        k = key(name)
        if k not in self.fields:
            self.fields[k] = Field(name)
        return self.fields[k]

    def _scan(self):
        try:
            parts = read_parts(self.path)
        except (zipfile.BadZipFile, KeyError, OSError) as exc:
            raise TemplateError(
                f"{self.path.name} could not be opened as a Word document ({exc}). "
                "Templates must be .docx or .dotx files.") from None
        self._check_word_features(parts)
        marked = set()
        for name, root in parts.items():
            where = part_label(name)
            for p in root.iter(w("p")):
                text = para_text(p)
                if "{" not in text and "}" not in text:
                    continue
                for m in TOKEN.finditer(text):
                    kind, arg = classify(m.group(1))
                    if kind == "field":
                        fname, fmt, options = parse_field(arg)
                        if not fname:
                            self.problems.append(f"Empty {{{{ }}}} in {where}: \u201c{snippet(text)}\u201d")
                            continue
                        marks = run_marks(run_at(p, _name_start(text, m.start(), m.end())))
                        if marks and key(fname) not in marked:
                            marked.add(key(fname))
                            self.warnings.append(
                                f"{{{{{fname}}}}} is {' and '.join(marks)} in the template, so what is "
                                "filled in will be too, in every contract. Remove that formatting from "
                                "the field in Word unless it is wanted.")
                        f = self._field(fname)
                        f.as_value = True
                        self.places += 1
                        if fmt not in KIND_OF_FORMAT:
                            self.problems.append(
                                f"Unknown format “{fmt}” for {fname} in {where}; "
                                "it will be filled in as plain text.")
                            fmt = ""
                        if fmt not in f.formats:
                            f.formats.append(fmt)
                        for o in options:
                            if key(o) not in [key(x) for x in f.options]:
                                f.options.append(o)
                    elif kind == "if":
                        self.conditions += 1
                        cname, value, _ = parse_condition(arg)
                        if not cname:
                            self.problems.append(f"{{{{#if}}}} with no name in {where}: “{snippet(text)}”")
                            continue
                        f = self._field(cname)
                        f.in_condition = True
                        if value and key(value) not in [key(x) for x in f.compared]:
                            f.compared.append(value)
                rest = TOKEN.sub("", text)
                if "{{" in rest or "}}" in rest:
                    self.problems.append(
                        f"Unmatched braces in {where}: “{snippet(text)}”. "
                        "Each field needs two on each side, like {{Client Name}}.")
        for f in self.fields.values():
            kinds = {KIND_OF_FORMAT.get(x, "text") for x in f.formats} - {"text"}
            if len(kinds) > 1:
                self.problems.append(
                    f"{f.name} is used as more than one kind of thing ({', '.join(sorted(kinds))}). "
                    f"The form will treat it as {f.kind}.")
            if f.kind == "choice" and not f.choices:
                self.problems.append(f"{f.name} is a choice with no options listed.")
        # Trial run: structural mistakes in the {{#if}} blocks show up here.
        try:
            render(self, {}, check_only=True)
        except TemplateError as exc:
            self.problems.append(str(exc))

    def _check_word_features(self, parts):
        revisions = comments = 0
        struck = []
        for root in parts.values():
            for tag in ("ins", "del", "moveFrom", "moveTo", "rPrChange", "pPrChange"):
                revisions += sum(1 for _ in root.iter(w(tag)))
            comments += sum(1 for _ in root.iter(w("commentReference")))
            for r in root.iter(w("r")):
                if "struck through" in run_marks(r):
                    text = "".join(t.text or "" for t in r.findall(w("t")))
                    if text.strip():
                        struck.append(text)
        if revisions:
            self.warnings.append(
                f"The template has {revisions} tracked change(s) not yet accepted. Anything filled in "
                "inside them shows as a tracked change in every contract. In Word: Review \u2192 "
                "Accept \u2192 Accept All Changes, then save.")
        if comments:
            self.warnings.append(f"The template has {comments} comment(s); they are copied into every contract.")
        if struck:
            self.warnings.append(
                f"Some wording is formatted as struck through ({quoted_list(struck)}). This is "
                "formatting, not a tracked change, so it appears struck through in every contract. "
                "Delete it, or make it an optional clause with {{#if}}.")
        with zipfile.ZipFile(self.path) as z:
            if "word/settings.xml" in z.namelist():
                settings = z.read("word/settings.xml")
                if re.search(rb"<w:trackRevisions(?![^>]*w:val=\"(false|0|off)\")", settings):
                    self.warnings.append(
                        "Track Changes is switched on in this template, so every contract starts with "
                        "it on, and edits made to the template itself are tracked. Turn it off in Word "
                        "(Review \u2192 Track Changes) unless that is wanted.")

    def summary(self):
        lines = [f"{len(self.value_fields())} thing(s) to fill in, used in {self.places} place(s)."]
        yesno = [f for f in self.fields.values() if f.kind == "yesno"]
        if yesno:
            lines.append(f"{len(yesno)} optional section switch(es).")
        if self.conditions:
            lines.append(f"{self.conditions} optional or alternative section(s).")
        return lines


# ------------------------------------------------------ reading the XML ---

def read_parts(path):
    parts = {}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "word/document.xml" not in names:
            raise KeyError("word/document.xml is missing")
        ordered = ["word/document.xml"] + sorted(n for n in names
                                                 if CONTENT_PART.match(n) and n != "word/document.xml")
        for name in ordered:
            parts[name] = etree.fromstring(z.read(name))
    return parts


def para_texts(p):
    """The w:t elements belonging to this paragraph, not to a text box inside it."""
    out = []
    for t in p.iter(w("t")):
        anc = t.getparent()
        while anc is not None and anc.tag != w("p"):
            anc = anc.getparent()
        if anc is p:
            out.append(t)
    return out


def para_text(p):
    return "".join(t.text or "" for t in para_texts(p))


def run_at(p, pos):
    """The run holding character pos of a paragraph."""
    off = 0
    for t in para_texts(p):
        n = len(t.text or "")
        if off <= pos < off + n:
            return t.getparent()
        off += n
    return None


def _on(el):
    return el is not None and el.get(w("val"), "true").lower() not in ("false", "0", "off", "none")


def run_marks(r):
    """Formatting on a run that would follow filled-in wording around."""
    out = []
    rpr = r.find(w("rPr")) if r is not None else None
    if rpr is None:
        return out
    if _on(rpr.find(w("strike"))) or _on(rpr.find(w("dstrike"))):
        out.append("struck through")
    if _on(rpr.find(w("highlight"))):
        out.append("highlighted")
    shd = rpr.find(w("shd"))
    if shd is not None and shd.get(w("fill"), "auto").lower() not in ("auto", "ffffff", "none"):
        out.append("shaded")
    return out


def quoted_list(texts, most=4):
    shown = ", ".join("\u201c" + snippet(t, 40) + "\u201d" for t in texts[:most])
    return shown + (f" and {len(texts) - most} more" if len(texts) > most else "")


def _set_text(t, text):
    t.text = text
    if text != text.strip() or "  " in text:
        t.set(XML_SPACE, "preserve")


def _split_run(r, t, k):
    """Split run r at character k of its text element t; the second half follows it."""
    kids = list(r)
    i = kids.index(t)
    r2 = copy.deepcopy(r)
    kids2 = list(r2)
    for c in kids[i + 1:]:
        r.remove(c)
    for c in kids2[:i]:
        if c.tag != w("rPr"):
            r2.remove(c)
    text = t.text or ""
    head, tail = text[:k], text[k:]
    _set_text(t, head)
    _set_text(kids2[i], tail)
    if not head:
        r.remove(t)
    if not tail:
        r2.remove(kids2[i])
    r.addnext(r2)


def _content_before(t):
    return any(c.tag != w("rPr") for c in t.itersiblings(preceding=True))


def _content_after(t):
    return any(True for _ in t.itersiblings())


def _boundary(p, pos):
    """Make sure a run starts exactly at character pos of the paragraph."""
    while True:
        off = 0
        for t in para_texts(p):
            n = len(t.text or "")
            if off < pos < off + n:
                _split_run(t.getparent(), t, pos - off)
                break
            if n and pos == off and _content_before(t):
                _split_run(t.getparent(), t, 0)
                break
            if n and pos == off + n and _content_after(t):
                _split_run(t.getparent(), t, n)
                break
            off += n
        else:
            return


def _runs_between(p, start, end):
    _boundary(p, end)
    _boundary(p, start)
    runs, off = [], 0
    for t in para_texts(p):
        n = len(t.text or "")
        if n and off >= start and off + n <= end:
            r = t.getparent()
            if not any(r is x for x, _ in runs):
                runs.append((r, off))
        off += n
    return runs


# Order of run properties Word insists on, from w:highlight onwards.
AFTER_HIGHLIGHT = ["u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em",
                   "lang", "eastAsianLayout", "specVanish", "oMath", "rPrChange"]


def _highlight(r):
    rpr = r.find(w("rPr"))
    if rpr is None:
        rpr = etree.Element(w("rPr"))
        r.insert(0, rpr)
    old = rpr.find(w("highlight"))
    if old is not None:
        rpr.remove(old)
    mark = etree.Element(w("highlight"))
    mark.set(w("val"), "yellow")
    later = {w(x) for x in AFTER_HIGHLIGHT}
    for i, c in enumerate(rpr):
        if c.tag in later:
            rpr.insert(i, mark)
            return
    rpr.append(mark)


def _write_run(r, text, highlight):
    for c in list(r):
        if c.tag != w("rPr"):
            r.remove(c)
    for i, line in enumerate(text.split("\n")):
        if i:
            etree.SubElement(r, w("br"))
        for j, piece in enumerate(line.split("\t")):
            if j:
                etree.SubElement(r, w("tab"))
            if piece:
                _set_text(etree.SubElement(r, w("t")), piece)
    if highlight:
        _highlight(r)


def replace_span(p, start, end, text, highlight=False, style_at=None):
    """
    Replace characters start..end of a paragraph. The new text takes the
    formatting found at character style_at (by default, the first one), so
    {{Client Name}} with only the name in bold comes out bold.
    """
    runs = _runs_between(p, start, end)
    if not runs:
        return
    at = start if style_at is None else style_at
    keep = runs[0][0]
    for r, off in runs:
        if off <= at:
            keep = r
    for r, _ in runs:
        if r is not keep:
            r.getparent().remove(r)
    if text:
        _write_run(keep, text, highlight)
    else:
        keep.getparent().remove(keep)


def _name_start(text, start, end):
    """Where the name begins inside {{ ... }}, for its formatting."""
    i = start + 2
    while i < end - 2 and text[i] in " \t\u00a0":
        i += 1
    return i


def _attached(el, root):
    while el is not None:
        if el is root:
            return True
        el = el.getparent()
    return False


def _siblings(a, b):
    out, el = [], a
    while el is not None:
        out.append(el)
        if el is b:
            return out
        el = el.getnext()
    return out


def _drop(el):
    """Remove an element. A paragraph carrying a section break is emptied instead."""
    if el.tag == w("p") and el.find(f"{w('pPr')}/{w('sectPr')}") is not None:
        for c in list(el):
            if c.tag != w("pPr"):
                el.remove(c)
        return
    parent = el.getparent()
    if parent is not None:
        parent.remove(el)


def _is_blank(el):
    return (el is not None and el.tag == w("p") and not para_text(el).strip()
            and not _has_objects(el) and el.find(f"{w('pPr')}/{w('sectPr')}") is None)


def _close_gap(prev, nxt):
    """
    After a clause is removed, the blank lines that stood either side of it
    would now sit together. Keep one, so removed clauses leave no hole.
    """
    if _is_blank(prev) and _is_blank(nxt) and prev.getnext() is nxt:
        _drop(nxt)


def _has_objects(p):
    for tag in ("drawing", "pict", "object", "sym", "fldChar", "fldSimple"):
        if p.find(f".//{w(tag)}") is not None:
            return True
    return False


# ------------------------------------------------------------- rendering ---

class Report:
    def __init__(self):
        self.filled = 0
        self.blanks = []
        self.kept = 0
        self.removed = 0

    def blank(self, name):
        if name not in self.blanks:
            self.blanks.append(name)


class Renderer:
    def __init__(self, template, values, highlight=False, check_only=False):
        self.template = template
        self.values = {key(k): v for k, v in values.items()}
        self.highlight = highlight
        self.check_only = check_only
        self.report = Report()

    def truth(self, expr):
        if self.check_only:
            return True
        name, value, negate = parse_condition(expr)
        raw = self.values.get(key(name))
        f = self.template.fields.get(key(name))
        if value is not None:
            result = key(str(raw or "")) == key(value)
        elif f is not None and f.kind == "yesno":
            result = as_bool(raw)
        else:
            result = bool(str(raw if raw is not None else "").strip())
        result = result != negate
        if result:
            self.report.kept += 1
        else:
            self.report.removed += 1
        return result

    def value(self, text):
        name, fmt, _ = parse_field(text)
        if fmt not in KIND_OF_FORMAT:
            fmt = ""
        raw = self.values.get(key(name))
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            self.report.blank(name)
            return BLANK
        try:
            out = format_value(fmt, raw)
        except ValueError as exc:
            raise TemplateError(f"{name}: {exc}") from None
        self.report.filled += 1
        return out

    # -- optional clauses that are whole paragraphs, tables and all --
    def blocks(self, root, where):
        markers = []
        for p in root.iter(w("p")):
            m = TOKEN.fullmatch(para_text(p).strip())
            if m:
                kind, arg = classify(m.group(1))
                if kind != "field":
                    markers.append((p, kind, arg))
        stack, found = [], []
        for p, kind, arg in markers:
            line = snippet(para_text(p))
            if kind == "if":
                stack.append({"start": p, "expr": arg, "else": None, "line": line, "n": len(found) + len(stack)})
            elif kind == "else":
                if not stack:
                    raise TemplateError(f"An {{{{else}}}} in {where} has no {{{{#if ...}}}} before it.")
                if stack[-1]["else"] is not None:
                    raise TemplateError(f"“{stack[-1]['line']}” in {where} has two {{{{else}}}} lines.")
                stack[-1]["else"] = p
            else:
                if not stack:
                    raise TemplateError(
                        f"A {{{{/if}}}} line in {where} has no {{{{#if ...}}}} line before it. "
                        "An {{#if ...}} that shares its paragraph with other words only covers that "
                        "paragraph; to cover several, put it on a line of its own.")
                b = stack.pop()
                b["end"] = p
                found.append(b)
        if stack:
            raise TemplateError(f"“{stack[-1]['line']}” in {where} is never closed with {{{{/if}}}}.")
        for b in sorted(found, key=lambda b: b["n"]):
            start, mid, end = b["start"], b["else"], b["end"]
            if not _attached(start, root):
                continue                     # inside a section already removed
            parent = start.getparent()
            if end.getparent() is not parent or (mid is not None and mid.getparent() is not parent):
                raise TemplateError(
                    f"“{b['line']}” in {where} and its {{{{/if}}}} are in different places, "
                    "for example one inside a table and one outside it. Put both in the main text, "
                    "or both in the same table cell.")
            if self.check_only:
                continue
            if self.truth(b["expr"]):
                doomed = [start] + (_siblings(mid, end) if mid is not None else [end])
            else:
                doomed = _siblings(start, mid if mid is not None else end)
                if mid is not None:
                    doomed.append(end)
            gap = (doomed[0].getprevious(), doomed[-1].getnext())
            only_markers = all(el.tag == w("p") and TOKEN.fullmatch(para_text(el).strip()) for el in doomed)
            for el in doomed:
                _drop(el)
            if not only_markers:
                _close_gap(*gap)

    # -- fields, and optional words within a single paragraph --
    def paragraph(self, p, where):
        text = para_text(p)
        if "{{" not in text:
            return
        lone = TOKEN.fullmatch(text.strip())
        if self.check_only and lone and classify(lone.group(1))[0] != "field":
            return                           # a block marker, already checked
        toks = [(m.start(), m.end(), *classify(m.group(1))) for m in TOKEN.finditer(text)]
        deletions, stack = [], []
        for start, end, kind, arg in toks:
            if kind == "if":
                stack.append([start, end, arg, None])
            elif kind == "else":
                if not stack or stack[-1][3] is not None:
                    raise TemplateError(self._stray(where, text))
                stack[-1][3] = (start, end)
            elif kind == "end":
                if not stack:
                    raise TemplateError(self._stray(where, text))
                s0, s1, expr, mid = stack.pop()
                if self.truth(expr):
                    deletions.append((s0, s1))
                    deletions.append((mid[0], end) if mid else (start, end))
                else:
                    deletions.append((s0, mid[1]) if mid else (s0, end))
                    if mid:
                        deletions.append((start, end))
        if stack:
            raise TemplateError(self._stray(where, text))
        merged = []
        for s, e in sorted(deletions):
            if merged and s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        edits = [(s, e, "", False, None) for s, e in merged]
        for start, end, kind, arg in toks:
            if kind == "field" and not any(s <= start < e for s, e in merged):
                edits.append((start, end, self.value(arg), True, _name_start(text, start, end)))
        if self.check_only:
            return
        all_gone = sum(e - s for s, e in merged) == len(text) and len(edits) == len(merged)
        for start, end, new, is_value, style_at in sorted(edits, key=lambda e: e[0], reverse=True):
            replace_span(p, start, end, new, highlight=is_value and self.highlight, style_at=style_at)
        if all_gone and not _has_objects(p):
            parent = p.getparent()
            if parent is not None and not (parent.tag == w("tc") and len(parent.findall(w("p"))) == 1):
                gap = (p.getprevious(), p.getnext())
                _drop(p)
                _close_gap(*gap)

    @staticmethod
    def _stray(where, text):
        return (f"In {where}, “{snippet(text)}” has an {{{{#if}}}}, {{{{else}}}} or {{{{/if}}}} "
                "without its partner. Either put the whole optional part in one paragraph, "
                "or put {{#if ...}} and {{/if}} each on a line of their own.")

    def part(self, root, where):
        self.blocks(root, where)
        for p in list(root.iter(w("p"))):
            if _attached(p, root):
                self.paragraph(p, where)
        for tc in root.iter(w("tc")):            # a table cell must keep one paragraph
            if tc.find(w("p")) is None:
                tc.append(etree.Element(w("p")))


def render(template, values, highlight=False, check_only=False):
    """Fill in the template. Returns (bytes of the finished .docx, Report)."""
    if not isinstance(template, Template):
        template = Template(template)
    r = Renderer(template, values, highlight, check_only)
    out = None if check_only else io.BytesIO()
    with zipfile.ZipFile(template.path) as zin:
        zout = None if check_only else zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
        for info in zin.infolist():
            data = zin.read(info.filename)
            if CONTENT_PART.match(info.filename):
                root = etree.fromstring(data)
                r.part(root, part_label(info.filename))
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif info.filename == "[Content_Types].xml":
                data = data.replace(TEMPLATE_TYPE.encode(), DOCUMENT_TYPE.encode())
            elif info.filename == "docProps/core.xml" and not check_only:
                data = fresh_properties(data)
            if zout is not None:
                zout.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
        if zout is not None:
            zout.close()
    return (None if check_only else out.getvalue()), r.report



def fresh_properties(data):
    """A new contract is a new document: its created date is now, not the template's."""
    try:
        root = etree.fromstring(data)
    except etree.XMLSyntaxError:
        return data
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for el in list(root):
        name = etree.QName(el).localname
        if name in ("created", "modified"):
            el.text = now
        elif name == "revision":
            el.text = "1"
        elif name == "lastPrinted":
            root.remove(el)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def problems_with(template, values):
    """Typed values that cannot be used, as [(field name, reason)]."""
    out = []
    vals = {key(k): v for k, v in values.items()}
    for f in template.value_fields():
        raw = vals.get(f.key)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        for fmt in f.formats:
            try:
                format_value(fmt, raw)
            except ValueError as exc:
                out.append((f.name, str(exc)))
                break
        if f.kind == "choice" and f.choices and key(raw) not in [key(c) for c in f.choices]:
            out.append((f.name, f"must be one of: {', '.join(f.choices)}"))
    return out


def build_contract(template, values, out_path, highlight=False):
    data, report = render(template, values, highlight)
    pathlib.Path(out_path).write_bytes(data)
    return report


# ------------------------------------------------ making a new template ---

def find_candidates(path):
    """Dollar amounts and dates in an existing contract, to suggest as fields."""
    patterns = [
        ("money", re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")),
        ("date", re.compile(r"\b(?:%s)\.? \d{1,2},? \d{4}\b" % "|".join(MONTH_NAMES + [m[:3] for m in MONTH_NAMES]))),
        ("date", re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")),
        ("date-formal", re.compile(r"\b\d{1,2}(?:st|nd|rd|th) day of (?:%s),? \d{4}\b" % "|".join(MONTH_NAMES))),
    ]
    found = {}
    for root in read_parts(path).values():
        for p in root.iter(w("p")):
            text = para_text(p)
            for fmt, pat in patterns:
                for m in pat.finditer(text):
                    s = m.group(0)
                    if s not in found:
                        found[s] = [fmt, 0]
                    found[s][1] += 1
    return [(text, fmt, n) for text, (fmt, n) in found.items()]


def make_template(source, out_path, swaps, reset_spacing=True):
    """
    Copy an existing contract with chosen wording swapped for fields.
    swaps: [(text to find, field name, format)]. Returns {text: times replaced}.
    Longest text first, so 'Acme Corporation' is taken before 'Acme'.
    Curly and straight quotes match each other, since a typed God's must find
    the God\u2019s that Word wrote.

    The new template also has Track Changes switched off, so adding fields
    and {{#if}} lines to it is not recorded as revisions. With reset_spacing
    it loses the squeezed and stretched letter spacing left by hand-fitting
    lines or by converting from PDF, which would otherwise leave odd gaps
    once filled-in wording changes the line lengths.
    """
    counts = {find: 0 for find, _, _ in swaps}
    order = sorted([s for s in swaps if s[0]], key=lambda s: len(s[0]), reverse=True)
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if CONTENT_PART.match(info.filename):
                root = etree.fromstring(data)
                if reset_spacing:
                    for sp in list(root.iter(w("spacing"))):
                        if sp.getparent().tag == w("rPr"):
                            sp.getparent().remove(sp)
                for p in root.iter(w("p")):
                    for find, name, fmt in order:
                        token = "{{" + name + (f" | {fmt}" if fmt else "") + "}}"
                        target = fold(find)
                        while True:
                            text = fold(para_text(p))
                            hits = [m.start() for m in re.finditer(re.escape(target), text)
                                    if not _inside_token(text, m.start())]
                            if not hits:
                                break
                            start = hits[-1]
                            replace_span(p, start, start + len(target), token)
                            counts[find] += 1
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif info.filename == "word/settings.xml":
                root = etree.fromstring(data)
                for el in root.findall(w("trackRevisions")):
                    root.remove(el)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            zout.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    return counts


def _inside_token(text, pos):
    for m in TOKEN.finditer(text):
        if m.start() <= pos < m.end():
            return True
    return False


# ----------------------------------------------------------- spreadsheets ---

FILE_NAME_COLUMN = "File Name"


def blank_sheet(template, out_path):
    """A spreadsheet with one column per field, ready for many contracts at once."""
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "Contracts"
    fields = template.field_list()
    headers = [f.name for f in fields] + [FILE_NAME_COLUMN]
    ws.append(headers)
    for col, name in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDEBF7")
        letter = cell.column_letter
        ws.column_dimensions[letter].width = max(14, min(40, len(name) + 4))
        if col > len(fields):
            cell.comment = Comment("Optional. The name for this contract's file. "
                                   "Left empty, one is made up from the template and the first column.", APP_NAME)
            continue
        f = fields[col - 1]
        note = {"yesno": "Yes or No: include this section?",
                "date": "A date, such as 10/5/2026.",
                "money": "An amount, such as 12500.",
                "number": "A number.",
                "long": "Several lines allowed: Alt+Enter starts a new line in a cell.",
                "choice": "One of: " + ", ".join(f.choices)}.get(f.kind, "Text.")
        cell.comment = Comment(note, APP_NAME)
        allowed = {"yesno": ["Yes", "No"], "choice": f.choices}.get(f.kind)
        if allowed and len(",".join(allowed)) < 250 and not any("," in a for a in allowed):
            dv = DataValidation(type="list", formula1='"' + ",".join(allowed) + '"', allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f"{letter}2:{letter}1000")
    ws.freeze_panes = "A2"
    wb.save(out_path)


def read_sheet(path):
    """Rows of a .xlsx or .csv as a list of {header: value}."""
    path = pathlib.Path(path)
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
    else:
        from openpyxl import load_workbook
        wb = load_workbook(path, data_only=True, read_only=True)
        rows = [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
        wb.close()
    if not rows:
        return [], []
    headers = [tidy_name(h) if h is not None else "" for h in rows[0]]
    out = []
    for row in rows[1:]:
        values = {}
        for h, v in zip(headers, row):
            if not h:
                continue
            if isinstance(v, float) and v.is_integer():
                v = int(v)
            values[h] = "" if v is None else v
        if any(str(v).strip() for v in values.values()):
            out.append(values)
    return headers, out


def safe_filename(text):
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(text)).strip().rstrip(".")
    return re.sub(r"\s+", " ", text)[:120] or "Contract"


def unique_path(folder, stem, suffix=".docx"):
    folder = pathlib.Path(folder)
    candidate = folder / f"{stem}{suffix}"
    n = 2
    while candidate.exists():
        candidate = folder / f"{stem} ({n}){suffix}"
        n += 1
    return candidate


def suggested_name(template, values):
    vals = {key(k): v for k, v in values.items()}
    for f in template.value_fields():
        v = vals.get(f.key)
        if f.kind in ("text", "choice") and v and str(v).strip():
            return safe_filename(f"{template.name} - {v}")
    return safe_filename(f"{template.name} - {datetime.date.today():%Y-%m-%d}")


def batch(template, sheet_path, out_folder, highlight=False, say=print):
    """One contract per spreadsheet row. Returns (made, skipped)."""
    headers, rows = read_sheet(sheet_path)
    known = {f.key for f in template.field_list()} | {key(FILE_NAME_COLUMN)}
    unknown = [h for h in headers if h and key(h) not in known]
    if unknown:
        say("Columns that match nothing in the template, ignored: " + ", ".join(unknown))
    missing = [f.name for f in template.field_list() if f.key not in {key(h) for h in headers}]
    if missing:
        say("Not in the spreadsheet, so left blank or switched off: " + ", ".join(missing))
    made = skipped = 0
    for n, row in enumerate(rows, 2):
        values = {k: v for k, v in row.items() if key(k) != key(FILE_NAME_COLUMN)}
        label = f"Row {n}"
        bad = problems_with(template, values)
        if bad:
            say(f"{label}: skipped. " + "; ".join(f"{name}: {why}" for name, why in bad))
            skipped += 1
            continue
        chosen = next((v for k, v in row.items() if key(k) == key(FILE_NAME_COLUMN) and str(v).strip()), None)
        stem = safe_filename(chosen) if chosen else suggested_name(template, values)
        if stem.lower().endswith(".docx"):
            stem = stem[:-5]
        out = unique_path(out_folder, stem)
        try:
            report = build_contract(template, values, out, highlight)
        except TemplateError as exc:
            say(f"{label}: skipped. {exc}")
            skipped += 1
            continue
        line = f"{label}: wrote {out.name}"
        if report.blanks:
            line += f"  (left blank: {', '.join(report.blanks)})"
        say(line)
        made += 1
    return made, skipped


# ---------------------------------------------------------------- answers ---

def save_answers(template, values, path):
    names = {f.key: f.name for f in template.field_list()}
    data = {
        "app": APP_NAME, "build": BUILD, "template": template.path.name,
        "saved": datetime.datetime.now().isoformat(timespec="minutes"),
        "values": {names.get(key(k), k): v for k, v in values.items()},
    }
    pathlib.Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_answers(path):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("values"), dict):
        raise ValueError("this is not a saved answers file")
    return data


# --------------------------------------------------------------- settings ---

SETTINGS_FILE = pathlib.Path.home() / ".tmai-contract-builder.json"


def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:                                      # noqa: BLE001
        return {}


def save_settings(data):
    try:
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except Exception:                                      # noqa: BLE001
        return False


def remember(**items):
    data = load_settings()
    data.update({k: (str(v) if isinstance(v, pathlib.Path) else v) for k, v in items.items()})
    save_settings(data)


def templates_in(folder):
    folder = pathlib.Path(folder)
    if not folder.is_dir():
        return []
    found = [p for p in folder.iterdir()
             if p.suffix.lower() in (".docx", ".dotx") and not p.name.startswith("~$")]
    return sorted(found, key=lambda p: p.name.lower())


def running_from_temp():
    """
    True when loose source files were launched from inside a zip, which cannot
    work because the other files are not really there. A built app is exempt:
    PyInstaller unpacks itself to a temporary folder every time.
    """
    if getattr(sys, "frozen", False):
        return False
    try:
        here = pathlib.Path(__file__).resolve().parent
    except NameError:
        return False
    temp = pathlib.Path(tempfile.gettempdir()).resolve()
    try:
        here.relative_to(temp)
        return True
    except ValueError:
        pass
    return bool(re.match(r"(?i)^Temp\d*_", here.name))


CHEAT_SHEET = """\
WRITING A CONTRACT TEMPLATE

A template is an ordinary Word document (.docx or .dotx).
Type the wording that never changes. Wherever something
changes, type its name in double braces:

    This Agreement is made between TMAI and {{Client Name}}.

Use the same name everywhere it appears; it is asked for once.
Capitals and spacing in the name do not matter.

FORMATS: add a bar and a format word

    {{Start Date | date}}           October 5, 2026
    {{Start Date | date-formal}}    5th day of October, 2026
    {{Start Date | date-short}}     10/05/2026
    {{Fee | money}}                 $12,500.00
    {{Fee | money-words}}           Twelve Thousand Five Hundred
                                    Dollars ($12,500.00)
    {{Term | number}}               1,250
    {{Notice Days | number-words}}  thirty (30)
    {{Client Name | upper}}         ACME CORPORATION
    {{Scope | long}}                several lines of text
    {{State | choice: Texas, Oklahoma, Louisiana}}
                                    a drop-down list

The same field can appear in different formats in
different places: {{Fee | money-words}} in the body and
{{Fee | money}} in a table.

OPTIONAL CLAUSES

Put {{#if ...}} and {{/if}} each on a line of its own, around
any number of paragraphs or tables:

    {{#if Include Non-Compete}}
    7. Non-Competition. ...
    {{/if}}

A name used only like this becomes a tick box on the form.

ALTERNATIVE CLAUSES

    {{#if Governing State = Texas}}
    This Agreement is governed by the laws of Texas ...
    {{else}}
    This Agreement is governed by the laws of Oklahoma ...
    {{/if}}

Comparing a name with values makes it a drop-down list of
those values. Also allowed: {{#if not Name}} and
{{#if Name != Value}}.

A field name on its own in an {{#if}} is true when it has
been filled in, so {{#if Guarantor Name}} ... {{/if}} shows
a guarantee only when a guarantor was named.

A short optional phrase can sit inside one paragraph:

    Payment is due in 30 days{{#if Late Fee}}, with a late fee
    of {{Late Fee | money}}{{/if}}.

Use Word's automatic numbering for clauses, and removed
clauses renumber themselves.
"""
