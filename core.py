"""
TMAI Contract Builder - the engine.
Build 4

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

BUILD = "4"
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
    "money-whole": "money-whole", "money-no-cents": "money-whole", "whole-dollars": "money-whole",
    "number": "number", "num": "number",
    "number-words": "number-words", "words": "number-words",
    "choice": "choice",
    "list": "list", "and-list": "list",
    "plural": "plural", "singular-plural": "plural",
}

# What sort of box the form shows for each format.
KIND_OF_FORMAT = {
    "": "text", "upper": "text", "long": "long",
    "date": "date", "date-formal": "date", "date-short": "date",
    "money": "money", "money-words": "money", "money-whole": "money",
    "number": "number", "number-words": "number",
    "choice": "choice",
    "list": "long",
    "plural": "count",      # follows whatever it counts; a number when used on its own
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
    """What a {{...}} is: ('if', expression), ('else', None), ('end', None),
    ('each', group name), ('endeach', None) or ('field', text)."""
    s = inner.strip()
    m = re.match(r"#\s*if\b(.*)$", s, re.I | re.S)
    if m:
        return "if", m.group(1).strip()
    low = re.sub(r"\s+", "", s.lower())
    if low in ("else", "#else"):
        return "else", None
    if low in ("/if", "endif", "#endif", "/endif"):
        return "end", None
    m = re.match(r"#\s*each\b(.*)$", s, re.I | re.S)
    if m:
        return "each", m.group(1).strip()
    if low in ("/each", "endeach", "#endeach", "/endeach"):
        return "endeach", None
    return "field", s


def parse_field(text):
    """'Fee | money-words' -> ('Fee', 'money-words', []); unknown formats come back as given."""
    name, _, fmt = text.partition("|")
    fmt = fmt.strip()
    options = []
    head = fmt.split(":", 1)[0].strip().lower()
    head = re.sub(r"[\s_]+", "-", head)
    if FORMAT_ALIASES.get(head) in ("choice", "plural"):
        rest = fmt.split(":", 1)[1] if ":" in fmt else ""
        sep = "/" if "/" in rest else ","        # a slash lets the words hold commas
        options = [o.strip() for o in rest.split(sep) if o.strip()]
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


def list_items(raw):
    """Titles typed one per line."""
    return [line.strip() for line in str(raw or "").splitlines() if line.strip()]


def count_of(raw):
    """How many: a number typed as such, or else how many lines were typed."""
    try:
        d = parse_amount(raw)
    except ValueError:
        return len(list_items(raw))
    if d != d.to_integral_value():
        raise ValueError("needs a whole number")
    return int(d)


def joined(items):
    """['A', 'B', 'C'] -> [('A', False), (', ', True), ('B', False), (', and ', True), ('C', False)].
    The True pieces are the joining words, kept out of any italics the titles have."""
    out = []
    for i, item in enumerate(items):
        if i:
            out.append((" and " if len(items) == 2 else ", and " if i == len(items) - 1 else ", ", True))
        out.append((item, False))
    return out


class Pieces(list):
    """Filled-in wording made of pieces, some of them plain joining words."""

    def __str__(self):
        return "".join(text for text, _ in self)


def format_value(fmt, raw, options=None):
    """Turn what was typed into what the contract says. Raises ValueError with a reason."""
    if isinstance(raw, str):
        raw = raw.strip()
    if fmt == "list":
        return Pieces(joined(list_items(raw)))
    if fmt == "plural":
        n = count_of(raw)
        if not options or len(options) != 2:
            return ""                          # reported when the template is checked
        return options[0] if n == 1 else options[1]
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
    if fmt == "money-whole":
        d = parse_amount(raw).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"${d:,}"
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

NOT_RELEVANT = {"not relevant": True}
NOT_RELEVANT_WORDS = ("n/a", "na", "not relevant", "not applicable")
INDEX = re.compile(r"\s\d+(?=\s|$)")


def is_excluded(raw):
    """True for a field the person marked as not relevant to this contract."""
    return isinstance(raw, dict) and bool(raw.get("not relevant"))


def is_empty(raw):
    if raw is None:
        return True
    if is_excluded(raw) or isinstance(raw, bool):
        return False
    if isinstance(raw, dict):                         # a territory
        return not raw.get("worldwide") and not str(raw.get("place", "")).strip()
    if isinstance(raw, (list, tuple)):
        return not any(str(x).strip() for x in raw)
    return not str(raw).strip()


def territory_parts(raw):
    """(worldwide?, place) from the form's {'worldwide': .., 'place': ..} or typed text."""
    if isinstance(raw, dict):
        return bool(raw.get("worldwide")), str(raw.get("place", "")).strip()
    text = str(raw or "").strip()
    if key(text) in ("worldwide", "world", "the world", "throughout the world", "everywhere"):
        return True, ""
    return False, text


def pick(options, n):
    if not options or len(options) != 2:
        return ""
    return options[0] if n == 1 else options[1]


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
        self.spec = None           # what a field set says about it
        self.section = None
        self.group = None          # the Group it repeats in, if any

    @property
    def kind(self):
        if self.spec:
            return self.spec.get("kind", "text")
        kinds = [KIND_OF_FORMAT.get(f, "text") for f in self.formats]
        if "choice" in kinds or (not self.as_value and self.compared):
            return "choice"
        if not self.as_value:
            return "yesno"
        for k in kinds:
            if k not in ("text", "count"):
                return k
        if "count" in kinds and "text" not in kinds:
            return "number"
        return "text"

    @property
    def choices(self):
        if self.spec and self.spec.get("options"):
            return [o["label"] for o in self.spec["options"]]
        out = []
        for o in self.options + self.compared:
            if key(o) not in [key(x) for x in out]:
                out.append(o)
        return out

    def option(self, text):
        """The field set's option matching a label or its wording."""
        for o in (self.spec or {}).get("options", []):
            if key(text) in (key(o["label"]), key(o.get("wording", o["label"]))):
                return o
        return None

    @property
    def expected(self):
        return bool(self.spec and self.spec.get("expected"))

    @property
    def help(self):
        return (self.spec or {}).get("help", "")

    @property
    def remember(self):
        return bool(self.spec and self.spec.get("remember"))

    def default(self, index=None):
        """What the form starts with: the field set's default, for this item of a group."""
        if not self.spec:
            return None
        if index is not None and "defaults" in self.spec:
            return self.spec["defaults"].get(str(index))
        return self.spec.get("default")

    @property
    def label(self):
        """The name without its group's word: 'Title' for Work Title, inside Work 1."""
        if self.group and self.name.lower().startswith(self.group.item.lower() + " "):
            return self.name[len(self.group.item) + 1:]
        return self.name

    @property
    def example(self):
        return EXAMPLES.get(self.kind, "")

    def preview(self, raw):
        """What the contract will say, for the hint beside the box."""
        if self.kind in ("yesno", "text", "choice", "checklist", "territory"):
            return ""
        if raw is None or is_excluded(raw) or not str(raw).strip():
            return ""
        shown = []
        for f in self.formats:
            if KIND_OF_FORMAT.get(f) == self.kind and f != "long":
                v = str(format_value(f, raw))
                if v not in shown:
                    shown.append(v)
        if self.kind in ("money", "date", "number") and not shown:
            shown.append(str(format_value({"money": "money", "date": "date"}.get(self.kind, "number"), raw)))
        if "plural" in self.formats:
            shown.append(f"counts as {count_of(raw)}")
        return "  |  ".join(shown)


class Group:
    """Fields that repeat: one set for each work, or for each party."""

    def __init__(self, name, item=None, minimum=1, start=1):
        self.name = tidy_name(name)
        self.key = key(name)
        self.item = item or (self.name[:-1] if self.name.lower().endswith("s") else self.name)
        self.minimum = minimum
        self.start = start
        self.members = []
        self.member_keys = set()
        self.highest = 0           # the largest number a template uses, as in {{Party 3 Name}}
        self.counted = False       # the template asks how many, {{Works | plural: ...}}
        self.cluster = None

    @property
    def first_count(self):
        """How many the form starts with. A field set says; otherwise as many as the template names."""
        if self.cluster is not None:
            return max(self.minimum, self.start, 1)
        return max(self.minimum, self.start, self.highest, 1)

    def indexed_name(self, field, i):
        """'Work 2 Title': how one item's field is named in templates and spreadsheets."""
        if field.name.lower().startswith(self.item.lower() + " "):
            return f"{self.item} {i} {field.name[len(self.item) + 1:]}"
        return f"{field.name} {i}"

    @property
    def used(self):
        return bool(self.members) or self.counted


class Template:
    """A contract template, read and checked. Fields are in reading order."""

    def __init__(self, path, fieldset=None):
        self.path = pathlib.Path(path)
        self.fieldset = fieldset
        self.fields = {}
        self.groups = {}
        self.problems = []
        self.warnings = []          # not wrong, but worth knowing before relying on it
        self.conditions = 0
        self.places = 0
        self._names = []
        self._scan()

    @property
    def name(self):
        return self.path.stem

    def field_list(self):
        return list(self.fields.values())

    def value_fields(self):
        return [f for f in self.fields.values() if f.kind != "yesno"]

    def field_for(self, name):
        """The Field a name in a template refers to, whatever its numbering."""
        return self.fields.get(self.resolve(name)[3] or "")

    def token_names(self):
        return list(self._names)

    def _field(self, name):
        k = key(name)
        if k not in self.fields:
            self.fields[k] = Field(name)
        return self.fields[k]

    def resolve(self, name):
        """
        What a name in a template refers to:
          ('count', group)               {{Works | plural: ...}}
          ('member', group, key)          {{Work Title}}: this work, or all of them
          ('indexed', group, n, key)      {{Party 2 Name}}
          ('plain', key)                  anything else
        Always returned as (mode, group, n, key).
        """
        k = key(name)
        if k in self.groups:
            return "count", self.groups[k], None, None
        for g in self.groups.values():
            if k in g.member_keys:
                return "member", g, None, k
        words_ = k.split(" ")
        for i, word in enumerate(words_):
            if word.isdigit():
                rest = " ".join(words_[:i] + words_[i + 1:])
                for g in self.groups.values():
                    if rest in g.member_keys:
                        return "indexed", g, int(word), rest
        return "plain", None, None, k

    def _scan(self):
        try:
            parts = read_parts(self.path)
        except (zipfile.BadZipFile, KeyError, OSError) as exc:
            raise TemplateError(
                f"{self.path.name} could not be opened as a Word document ({exc}). "
                "Templates must be .docx or .dotx files.") from None
        self._check_word_features(parts)
        found = []                  # (kind, name, format, options, compared value, where)
        loops = {}                  # {{#each X}} name -> names used inside it
        marked = set()
        for name, root in parts.items():
            where = part_label(name)
            open_loops = []
            for p in root.iter(w("p")):
                text = para_text(p)
                if "{" not in text and "}" not in text:
                    continue
                lone = TOKEN.fullmatch(text.strip())
                if lone:
                    kind, arg = classify(lone.group(1))
                    if kind == "each":
                        open_loops.append(arg)
                        loops.setdefault(key(arg), (arg, []))
                        continue
                    if kind == "endeach":
                        if open_loops:
                            open_loops.pop()
                        continue
                for m in TOKEN.finditer(text):
                    kind, arg = classify(m.group(1))
                    if kind == "field":
                        fname, fmt, options = parse_field(arg)
                        if not fname:
                            self.problems.append(f"Empty {{{{ }}}} in {where}: “{snippet(text)}”")
                            continue
                        holder = run_at(p, _name_start(text, m.start(), m.end()))
                        marks = run_marks(holder)
                        if holder is not None and holder.getparent().tag == w("hyperlink") \
                                and ("link", key(fname)) not in marked:
                            marked.add(("link", key(fname)))
                            self.warnings.append(
                                f"{{{{{fname}}}}} is inside a link. The wording shown is filled in, but "
                                "the address the link goes to is not. Remove the link from the field.")
                        if marks and key(fname) not in marked:
                            marked.add(key(fname))
                            self.warnings.append(
                                f"{{{{{fname}}}}} is {' and '.join(marks)} in the template, so what is "
                                "filled in will be too, in every contract. Remove that formatting from "
                                "the field in Word unless it is wanted.")
                        found.append(("field", fname, fmt, options, None, where))
                        if open_loops:
                            loops[key(open_loops[-1])][1].append(fname)
                    elif kind == "if":
                        cname, value, _ = parse_condition(arg)
                        if not cname:
                            self.problems.append(f"{{{{#if}}}} with no name in {where}: “{snippet(text)}”")
                            continue
                        self.conditions += 1
                        found.append(("if", cname, None, None, value, where))
                        if open_loops:
                            loops[key(open_loops[-1])][1].append(cname)
                rest = TOKEN.sub("", text)
                if "{{" in rest or "}}" in rest:
                    self.problems.append(
                        f"Unmatched braces in {where}: “{snippet(text)}”. "
                        "Each field needs two on each side, like {{Client Name}}.")
        self._names = [x[1] for x in found]

        # Groups: those the field set defines, then any the template repeats with {{#each}}.
        specs = {}
        if self.fieldset:
            for c, sp in self.fieldset.specs():
                specs[key(sp["name"])] = (c, sp)
            for c in self.fieldset.groups():
                g = c["group"]
                group = Group(g["name"], g.get("item"), g.get("min", 1), g.get("start", 1))
                group.cluster = c["name"]
                group.member_keys = {key(sp["name"]) for sp in c["fields"]}
                self.groups[group.key] = group
        for k, (gname, names) in loops.items():
            if k not in self.groups:
                group = Group(gname)
                group.member_keys = {key(INDEX.sub("", n)) for n in names}
                self.groups[k] = group

        for kind, fname, fmt, options, value, where in found:
            mode, group, n, k = self.resolve(fname)
            if mode == "count":
                group.counted = True
                if kind == "field":
                    self.places += 1
                    if fmt == "plural" and len(options) != 2:
                        self.problems.append(self._plural_problem(fname, where))
                continue
            if k in specs:
                display = specs[k][1]["name"]
            elif mode == "indexed":
                display = tidy_name(INDEX.sub("", fname))
            else:
                display = fname
            f = self._field(display)
            if group is not None:
                f.group = group
                if f not in group.members:
                    group.members.append(f)
                if n:
                    group.highest = max(group.highest, n)
            if kind == "field":
                f.as_value = True
                self.places += 1
                if fmt not in KIND_OF_FORMAT:
                    self.problems.append(
                        f"Unknown format “{fmt}” for {fname} in {where}; "
                        "it will be filled in as plain text.")
                    fmt = ""
                if fmt not in f.formats:
                    f.formats.append(fmt)
                if fmt == "plural":
                    if len(options) != 2:
                        self.problems.append(self._plural_problem(fname, where))
                    options = []
                for o in options:
                    if key(o) not in [key(x) for x in f.options]:
                        f.options.append(o)
            else:
                f.in_condition = True
                if value and key(value) not in [key(x) for x in f.compared]:
                    f.compared.append(value)

        for k, f in self.fields.items():
            if k in specs:
                f.section, f.spec = specs[k][0]["name"], specs[k][1]
        order = list(specs)
        for group in self.groups.values():
            group.members.sort(key=lambda f: order.index(f.key) if f.key in order else len(order))

        if self.fieldset:
            for c, sp in self.fieldset.specs():
                if sp.get("expected") and key(sp["name"]) not in self.fields:
                    g = c.get("group")
                    code = sp["name"]
                    if g and code.lower().startswith(g["item"].lower() + " "):
                        code = f"{g['item']} 1 {code[len(g['item']) + 1:]}"
                    self.warnings.append(
                        f"A {self.fieldset.name.lower()} is expected to state {sp['name']}, but this "
                        f"template has no field for it, such as {{{{{code}}}}}.")
        for f in self.fields.values():
            if f.spec:
                continue
            kinds = {KIND_OF_FORMAT.get(x, "text") for x in f.formats} - {"text", "count"}
            if len(kinds) > 1:
                self.problems.append(
                    f"{f.name} is used as more than one kind of thing ({', '.join(sorted(kinds))}). "
                    f"The form will treat it as {f.kind}.")
            if f.kind == "choice" and not f.choices:
                self.problems.append(f"{f.name} is a choice with no options listed.")
        # Trial run: structural mistakes in the {{#if}} and {{#each}} blocks show up here.
        try:
            render(self, {}, check_only=True)
        except TemplateError as exc:
            self.problems.append(str(exc))

    @staticmethod
    def _plural_problem(name, where):
        return (f"{{{{{name} | plural ...}}}} in {where} needs two wordings, one for one and one "
                "for more, like {{Books | plural: work, works}}.")

    def layout(self):
        """The form, in sections: [(title, [Field or Group])]."""
        out, placed = [], set()
        if self.fieldset:
            for c in self.fieldset.clusters():
                entries = []
                g = c.get("group")
                if g:
                    group = self.groups.get(key(g["name"]))
                    if group and group.used:
                        entries.append(group)
                        placed.update(f.key for f in group.members)
                else:
                    for sp in c["fields"]:
                        f = self.fields.get(key(sp["name"]))
                        if f is not None:
                            entries.append(f)
                            placed.add(f.key)
                if entries:
                    out.append((c["name"], entries))
        for group in self.groups.values():
            if group.cluster is None and group.used:
                out.append((group.name, [group]))
                placed.update(f.key for f in group.members)
        others = [f for f in self.fields.values() if f.key not in placed and f.kind != "yesno"]
        if others:
            out.append(("Other details" if out else "Details", others))
        switches = [f for f in self.fields.values() if f.key not in placed and f.kind == "yesno"]
        if switches:
            out.append(("Optional sections", switches))
        return out

    def normalize(self, values):
        """
        Values ready for filling in: ordinary fields by key, and each group as
        a list of {field key: value}, one per item. Takes the form's values,
        saved answers, or a spreadsheet row with columns like 'Work 2 Title';
        N/A in a spreadsheet means not relevant.
        """
        def clean(v):
            if isinstance(v, str) and v.strip().lower() in NOT_RELEVANT_WORDS:
                return dict(NOT_RELEVANT)
            return v

        out = {}
        for name, v in values.items():
            mode, group, n, k = self.resolve(name)
            if mode == "count":
                if isinstance(v, list):
                    items = out.setdefault(group.key, [])
                    for i, item in enumerate(v):
                        while len(items) <= i:
                            items.append({})
                        for ik, iv in (item or {}).items():
                            items[i][key(INDEX.sub("", ik))] = clean(iv)
                continue
            if mode == "indexed":
                items = out.setdefault(group.key, [])
                while len(items) < n:
                    items.append({})
                items[n - 1][k] = clean(v)
            elif mode == "member":
                items = out.setdefault(group.key, [])
                if not items:
                    items.append({})
                items[0][k] = clean(v)
            else:
                out[k] = clean(v)
        return out

    def expected_gaps(self, values):
        """Expected fields left empty or marked not relevant, as lines for a warning."""
        vals = self.normalize(values)
        out = []
        for f in self.fields.values():
            if not f.expected or f.kind == "yesno":
                continue
            if f.group is not None:
                items = vals.get(f.group.key) or [{}]
                pairs = [(f.group.indexed_name(f, i), item.get(f.key)) for i, item in enumerate(items, 1)]
            else:
                pairs = [(f.name, vals.get(f.key))]
            for label, raw in pairs:
                if is_excluded(raw):
                    out.append(f"{label} (marked not relevant)")
                elif is_empty(raw):
                    out.append(f"{label} (empty)")
        return out

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


PLAIN_OFF = ("i", "iCs", "u")       # what joining words do not share with titles


def _write_run(r, text, highlight):
    if isinstance(text, Pieces):
        pieces = [(t, plain) for t, plain in text if t]
        _write_run(r, pieces[0][0] if pieces else "", highlight)
        last = r
        for piece, plain in pieces[1:]:
            nr = copy.deepcopy(r)
            rpr = nr.find(w("rPr"))
            if plain and rpr is not None:
                for tag in PLAIN_OFF:
                    for el in rpr.findall(w(tag)):
                        rpr.remove(el)
            _write_run(nr, piece, highlight)
            last.addnext(nr)
            last = nr
        return
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

def picked_options(field, raw):
    """The ticked options of a checklist, as option dicts."""
    labels = raw if isinstance(raw, (list, tuple)) else re.split(r"\s*[;,]\s*", str(raw or ""))
    out = []
    for label in labels:
        if str(label).strip():
            out.append(field.option(label) if field and field.option(label)
                       else {"label": str(label).strip(), "wording": str(label).strip()})
    return out


def word_value(field, fmt, raw, options=None):
    """One value, as the contract words it."""
    kind = field.kind if field else "text"
    if kind == "checklist":
        picked = picked_options(field, raw)
        everything = [o for o in picked if o.get("all")]
        if fmt == "plural":
            return pick(options, 2 if everything else len(picked))
        return Pieces(joined([o["wording"] for o in (everything[:1] or picked)]))
    if kind == "territory":
        world, place = territory_parts(raw)
        sp = field.spec or {}
        text = sp.get("worldwide", "throughout the world") if world else sp.get("place", "{}").format(place)
        return format_value("upper" if fmt == "upper" else "", text)
    if kind == "choice" and field and field.option(raw) and fmt in ("", "choice"):
        return field.option(raw).get("wording", raw)
    return format_value(fmt, raw, options)


class Report:
    def __init__(self):
        self.filled = 0
        self.blanks = []
        self.left_out = []
        self.kept = 0
        self.removed = 0

    def blank(self, name):
        if name not in self.blanks:
            self.blanks.append(name)

    def leave_out(self, name):
        if name not in self.left_out:
            self.left_out.append(name)


class Renderer:
    def __init__(self, template, values, highlight=False, check_only=False):
        self.template = template
        self.values = template.normalize(values)
        self.highlight = highlight
        self.check_only = check_only
        self.report = Report()
        self.context = None         # (group, item values, number) inside {{#each}}
        self.done = set()           # paragraphs already filled in by {{#each}}

    # -- finding values --
    def items(self, group):
        """A group's items, leaving out any with nothing in them."""
        return [it for it in self.values.get(group.key, [])
                if any(not is_empty(v) and not is_excluded(v) for v in it.values())]

    def lookup(self, name):
        """(how, value, field): how is 'one', 'many' (every item of a group) or 'count'."""
        mode, group, n, k = self.template.resolve(name)
        field = self.template.fields.get(k) if k else None
        if mode == "count":
            return "count", len(self.items(group)), field
        if mode == "member":
            if self.context and self.context[0] is group:
                return "one", self.context[1].get(k), field
            return "many", [it.get(k) for it in self.items(group)], field
        if mode == "indexed":
            items = self.values.get(group.key, [])
            return "one", (items[n - 1].get(k) if n <= len(items) else None), field
        return "one", self.values.get(k), field

    picked = staticmethod(lambda field, raw: picked_options(field, raw))

    def holds(self, field, raw, value):
        """Whether a condition is true for one value."""
        if raw is None or is_excluded(raw):
            return False
        kind = field.kind if field else "text"
        if kind == "checklist":
            picked = self.picked(field, raw)
            if value is None:
                return bool(picked)
            if any(o.get("all") for o in picked):
                return True
            return any(key(value) in (key(o["label"]), key(o["wording"])) for o in picked)
        if kind == "territory":
            world, place = territory_parts(raw)
            if value is None:
                return world or bool(place)
            if key(value) in ("worldwide", "world", "the world"):
                return world
            return not world and key(place) == key(value)
        if value is not None:
            return key(str(raw)) == key(value)
        if kind == "yesno":
            return as_bool(raw)
        return not is_empty(raw)

    def truth(self, expr):
        if self.check_only:
            return True
        name, value, negate = parse_condition(expr)
        how, raw, field = self.lookup(name)
        if how == "count":
            result = raw > 0 if value is None else str(raw) == value.strip()
        elif how == "many":
            result = any(self.holds(field, r, value) for r in raw)
        else:
            result = self.holds(field, raw, value)
        result = result != negate
        if result:
            self.report.kept += 1
        else:
            self.report.removed += 1
        return result

    @staticmethod
    def one(field, fmt, raw, options):
        return word_value(field, fmt, raw, options)

    def value(self, text):
        name, fmt, options = parse_field(text)
        if fmt not in KIND_OF_FORMAT:
            fmt = ""
        how, raw, field = self.lookup(name)
        try:
            if how == "count":
                out = pick(options, raw) if fmt == "plural" else format_value(
                    fmt if fmt in ("number", "number-words") else "number", raw)
            elif how == "many":
                live = [r for r in raw if not is_excluded(r) and not is_empty(r)]
                if fmt == "plural":
                    out = pick(options, len(live))
                elif not live:
                    if raw and all(is_excluded(r) for r in raw):
                        self.report.leave_out(name)
                        return ""
                    self.report.blank(name)
                    return BLANK
                else:
                    shown = []
                    for r in live:
                        v = str(self.one(field, "" if fmt == "list" else fmt, r, options))
                        if key(v) not in [key(x) for x in shown]:
                            shown.append(v)
                    out = Pieces(joined(shown))
            elif is_excluded(raw):
                self.report.leave_out(name)
                return ""
            elif is_empty(raw):
                if fmt != "plural":
                    self.report.blank(name)
                    return BLANK
                out = pick(options, 0)
            else:
                out = self.one(field, fmt, raw, options)
        except ValueError as exc:
            raise TemplateError(f"{name}: {exc}") from None
        self.report.filled += 1
        return out

    # -- optional clauses, and repeated ones, that are whole paragraphs --
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
            if kind == "each" and (self.context is not None or any(b["kind"] == "each" for b in stack)):
                raise TemplateError(f"\u201c{line}\u201d in {where} is inside another {{{{#each}}}}; "
                                    "one repeat cannot sit inside another.")
            if kind in ("if", "each"):
                stack.append({"kind": kind, "start": p, "expr": arg, "else": None, "line": line,
                              "n": len(found) + len(stack)})
            elif kind == "else":
                if not stack or stack[-1]["kind"] != "if":
                    raise TemplateError(f"An {{{{else}}}} in {where} has no {{{{#if ...}}}} before it.")
                if stack[-1]["else"] is not None:
                    raise TemplateError(f"“{stack[-1]['line']}” in {where} has two {{{{else}}}} lines.")
                stack[-1]["else"] = p
            elif kind == "endeach":
                if not stack or stack[-1]["kind"] != "each":
                    raise TemplateError(f"A {{{{/each}}}} line in {where} has no {{{{#each ...}}}} line "
                                        "before it, or an {{#if}} inside it is not closed first.")
                b = stack.pop()
                b["end"] = p
                found.append(b)
            else:
                if not stack:
                    raise TemplateError(
                        f"A {{{{/if}}}} line in {where} has no {{{{#if ...}}}} line before it. "
                        "An {{#if ...}} that shares its paragraph with other words only covers that "
                        "paragraph; to cover several, put it on a line of its own.")
                if stack[-1]["kind"] != "if":
                    raise TemplateError(f"“{stack[-1]['line']}” in {where} needs its {{{{/each}}}} "
                                        "before the next {{/if}}.")
                b = stack.pop()
                b["end"] = p
                found.append(b)
        if stack:
            closer = "{{/each}}" if stack[-1]["kind"] == "each" else "{{/if}}"
            raise TemplateError(f"“{stack[-1]['line']}” in {where} is never closed with {closer}.")
        for b in sorted(found, key=lambda b: b["n"]):
            start, mid, end = b["start"], b["else"], b["end"]
            if not _attached(start, root):
                continue                     # inside a section already removed
            parent = start.getparent()
            closer = "{{/each}}" if b["kind"] == "each" else "{{/if}}"
            if end.getparent() is not parent or (mid is not None and mid.getparent() is not parent):
                raise TemplateError(
                    f"“{b['line']}” in {where} and its {closer} are in different places, "
                    "for example one inside a table and one outside it. Put both in the main text, "
                    "or both in the same table cell.")
            if b["kind"] == "each":
                if self.context is not None:
                    raise TemplateError(f"“{b['line']}” in {where} is inside another "
                                        "{{#each}}; one repeat cannot sit inside another.")
                if not self.check_only:
                    self.repeat(b, where)
                continue
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

    def repeat(self, b, where):
        """{{#each Works}} ... {{/each}}: the part between, once for each work."""
        start, end = b["start"], b["end"]
        group = self.template.groups.get(key(b["expr"]))
        if group is None:
            raise TemplateError(f"“{b['line']}” in {where}: nothing called {b['expr']} repeats.")
        region = _siblings(start, end)[1:-1]
        for i, item in enumerate(self.items(group), 1):
            holder = etree.Element(w("body"))
            for el in region:
                holder.append(copy.deepcopy(el))
            self.context = (group, item, i)
            try:
                self.blocks(holder, where)
                for p in list(holder.iter(w("p"))):
                    if _attached(p, holder):
                        self.paragraph(p, where)
            finally:
                self.context = None
            for el in list(holder):
                end.addprevious(el)
                self.done.update(el.iter(w("p")))
        gap = (start.getprevious(), end.getnext())
        nothing = not self.items(group)
        for el in [start] + region + [end]:
            _drop(el)
        if nothing:
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
            if kind in ("each", "endeach"):
                raise TemplateError(f"In {where}, “{snippet(text)}”: {{{{#each ...}}}} and "
                                    "{{/each}} must each be on a line of their own.")
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
            if p not in self.done and _attached(p, root):
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
    vals = template.normalize(values)

    def check(f, raw, label):
        if raw is None or is_excluded(raw) or is_empty(raw):
            return
        kind = f.kind
        try:
            if kind == "date":
                parse_date(raw)
            elif kind in ("money", "number"):
                parse_amount(raw)
            for fmt in f.formats:
                if fmt == "plural" and kind not in ("checklist", "territory"):
                    count_of(raw)
                elif KIND_OF_FORMAT.get(fmt) == kind and kind in ("date", "money", "number"):
                    format_value(fmt, raw)
        except ValueError as exc:
            out.append((label, str(exc)))
            return
        if kind == "choice" and f.choices and not isinstance(raw, (list, dict)) \
                and key(raw) not in [key(c) for c in f.choices]:
            out.append((label, f"must be one of: {', '.join(f.choices)}"))
        if kind == "checklist" and f.spec:
            labels = raw if isinstance(raw, (list, tuple)) else re.split(r"\s*[;,]\s*", str(raw))
            bad = [str(x) for x in labels if str(x).strip() and not f.option(x)]
            if bad:
                out.append((label, f"not one of the options: {', '.join(bad)}"))

    for f in template.fields.values():
        if f.kind == "yesno":
            continue
        if f.group is not None:
            for i, item in enumerate(vals.get(f.group.key, []), 1):
                check(f, item.get(f.key), f.group.indexed_name(f, i))
        else:
            check(f, vals.get(f.key), f.name)
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


REVISION_MARKS = ("rPrChange", "pPrChange", "sectPrChange", "tblPrChange", "tblPrExChange", "trPrChange",
                  "tcPrChange", "tblGridChange", "numberingChange", "moveFromRangeStart", "moveFromRangeEnd",
                  "moveToRangeStart", "moveToRangeEnd", "cellIns", "cellDel", "cellMerge")
COMMENT_PARTS = ("word/comments.xml", "word/commentsExtended.xml", "word/commentsIds.xml",
                 "word/commentsExtensible.xml")


def accept_revisions(root):
    """
    Accept every tracked change, as Word's Accept All Changes does: inserted
    wording stays, deleted wording goes, new formatting stays. Returns how
    many changes there were.
    """
    n = 0
    for p in list(root.iter(w("p"))):              # a deleted paragraph mark joins it to the next
        mark = p.find(f"{w('pPr')}/{w('rPr')}/{w('del')}")
        if mark is None:
            continue
        mark.getparent().remove(mark)
        n += 1
        nxt = p.getnext()
        if nxt is not None and nxt.tag == w("p"):
            at = 1 if nxt.find(w("pPr")) is not None else 0
            for i, c in enumerate([c for c in p if c.tag != w("pPr")]):
                nxt.insert(at + i, c)
            p.getparent().remove(p)
    for tag in ("del", "moveFrom"):
        for el in list(root.iter(w(tag))):
            parent = el.getparent()
            if parent is None:
                continue
            if parent.tag == w("trPr"):             # a deleted table row
                row = parent.getparent()
                if row.getparent() is not None:
                    row.getparent().remove(row)
            else:
                parent.remove(el)
            n += 1
    for tag in ("ins", "moveTo"):
        for el in list(root.iter(w(tag))):
            parent = el.getparent()
            if parent is None:
                continue
            if parent.tag in (w("rPr"), w("trPr")) or len(el) == 0:
                parent.remove(el)                   # an inserted paragraph mark or row
            else:
                at = parent.index(el)
                for i, c in enumerate(list(el)):
                    parent.insert(at + i, c)
                parent.remove(el)
            n += 1
    for tag in REVISION_MARKS:
        for el in list(root.iter(w(tag))):
            el.getparent().remove(el)
            n += 1
    return n


def strip_comments(root):
    n = sum(1 for _ in root.iter(w("commentRangeStart")))
    for tag in ("commentRangeStart", "commentRangeEnd"):
        for el in list(root.iter(w(tag))):
            el.getparent().remove(el)
    for ref in list(root.iter(w("commentReference"))):
        r = ref.getparent()
        if r.tag == w("r") and all(c.tag in (w("rPr"), w("commentReference")) for c in r):
            r.getparent().remove(r)
        else:
            r.remove(ref)
    return n


def make_template(source, out_path, swaps, reset_spacing=True, accept_changes=True, notes=None):
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

    With accept_changes, tracked changes are accepted and comments removed
    first, so the template starts from the wording as it was finally agreed,
    and no contract made from it carries old redlines. What was done is
    added to notes, if given.
    """
    revisions = comments = 0
    counts = {find: 0 for find, _, _ in swaps}
    order = sorted([s for s in swaps if s[0]], key=lambda s: len(s[0]), reverse=True)
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if CONTENT_PART.match(info.filename):
                root = etree.fromstring(data)
                if accept_changes:
                    comments += strip_comments(root)
                    revisions += accept_revisions(root)
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
                            gaps = para_gaps(p)
                            hits = [m.start() for m in re.finditer(re.escape(target), text)
                                    if whole_word(text, m.start(), m.end(), gaps)
                                    and not _inside_token(text, m.start())]
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
            elif accept_changes and info.filename in COMMENT_PARTS:
                root = etree.fromstring(data)
                for c in list(root):
                    root.remove(c)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            zout.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    if notes is not None:
        if revisions:
            notes.append(f"accepted {revisions} tracked change(s)")
        if comments:
            notes.append(f"removed {comments} comment(s)")
    return counts


def para_gaps(p):
    """
    Places in a paragraph's text where a tab or line break sits. They are not
    part of the text, but they still separate words: 'Publications<tab>Jordan'.
    """
    gaps, off = set(), 0
    for el in p.iter(w("t"), w("tab"), w("br"), w("cr")):
        anc = el.getparent()
        while anc is not None and anc.tag != w("p"):
            anc = anc.getparent()
        if anc is not p:
            continue
        if el.tag == w("t"):
            off += len(el.text or "")
        elif el.getparent().tag == w("r"):       # not a tab stop definition in pPr
            gaps.add(off)
    return gaps


def whole_word(text, start, end, gaps=()):
    """True unless the match is part of a longer word: 'works' is not found in 'networks'."""
    def joined(a, b):
        return a.isalnum() and b.isalnum()
    if start > 0 and start not in gaps and joined(text[start - 1], text[start]):
        return False
    if end < len(text) and end not in gaps and joined(text[end - 1], text[end]):
        return False
    return True


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
    columns = []                                  # (heading, field)
    for _, entries in template.layout():
        for entry in entries:
            if isinstance(entry, Group):
                for i in range(1, entry.first_count + 2):     # one spare, for another work or party
                    columns += [(entry.indexed_name(f, i), f) for f in entry.members]
            else:
                columns.append((entry.name, entry))
    fields = [f for _, f in columns]
    headers = [h for h, _ in columns] + [FILE_NAME_COLUMN]
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
                "choice": "One of: " + ", ".join(f.choices),
                "checklist": "Any of these, separated by commas: " + ", ".join(f.choices),
                "territory": "Worldwide, or the countries or regions."}.get(f.kind, "Text.")
        if f.kind != "yesno":
            note += " Type N/A if it does not apply to this contract."
        if f.expected:
            note = "Expected. " + note
        if f.group is not None:
            note += f" Leave a whole {f.group.item.lower()} empty if there is no such {f.group.item.lower()}."
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
    vals = template.normalize(values)
    parts = []
    for f in template.value_fields():             # what the field set says names a file
        which = (f.spec or {}).get("file_name")
        if not which:
            continue
        if f.group is not None:
            items = vals.get(f.group.key, [])
            v = items[int(which) - 1].get(f.key) if len(items) >= int(which) else None
        else:
            v = vals.get(f.key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip().splitlines()[0])
    if parts:
        return safe_filename(" - ".join([template.name] + parts))
    for f in template.value_fields():
        v = vals.get(f.key)
        if f.group is None and f.kind in ("text", "choice") and isinstance(v, str) and v.strip():
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
    names.update({g.key: g.name for g in template.groups.values()})
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
    {{Fee | money-whole}}           $12,500 (no cents)
    {{Titles | list}}               one per line, joined:
                                    A and B / A, B, and C
    {{Titles | plural: work, works}}
                                    "work" for one title,
                                    "works" for more
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

ONE BOOK OR SEVERAL

Type the titles one per line in a single field, show them
with {{Titles | list}}, and let every word that changes with
the number follow it:

    the translated {{Titles | plural: work, works}}
    {{Titles | plural: contains, contain}} no matter ...

Use a slash when the wording holds a comma:
    {{Titles | plural: it, as written / them, as written}}

FIELD SETS (Publishing agreement)

With a field set chosen beside the template, use its names;
Template tools > Field codes lists them all. Works and
parties repeat:

    {{Party 1 Name}}  {{Party 2 Name}}   one by number
    {{Work Title | list}}                 all the titles
    {{Works | plural: work, works}}       follows how many

Wording written once for each work, or each party:

    {{#each Works}}
    ... {{Work Title}} ... {{Work Copyright}} ...
    {{/each}}

    {{Rights Licensed}}   the ticked rights, in words
    {{Territory}}         "throughout the world" or "in ..."
"""
