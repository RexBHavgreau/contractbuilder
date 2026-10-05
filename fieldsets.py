"""
TMAI Contract Builder - field sets.

A field set says what a kind of contract is expected to contain, in
clusters: Parties, Works, Rights and territory, and so on. It decides how
the form is laid out, what sort of box each field gets, what is filled in
by default, and what to warn about when something expected is missing.

The Publishing agreement set is built in. People can make their own by
choosing clusters and adding fields of their own; those are saved as small
.json files in a "Field sets" folder inside the templates folder, so
everyone using that folder shares them.
"""
import json
import pathlib
import re

import core

TMAI = "The Master’s Academy International"

KINDS = ["text", "long", "date", "money", "number", "choice", "checklist", "territory", "yesno"]
KIND_LABELS = {
    "text": "Text", "long": "Several lines", "date": "Date", "money": "Amount of money",
    "number": "Number", "choice": "Choose one", "checklist": "Tick any",
    "territory": "Territory (with Worldwide)", "yesno": "Yes / no switch",
}


def spec(name, kind="text", **extra):
    out = {"name": name, "kind": kind}
    out.update(extra)
    return out


def option(label, wording=None, everything=False):
    out = {"label": label, "wording": wording or label.lower()}
    if everything:
        out["all"] = True          # ticking it means every other option too
    return out


CLUSTERS = [
    {
        "name": "Parties",
        "group": {"name": "Parties", "item": "Party", "min": 2, "start": 2},
        "fields": [
            spec("Party Name", expected=True, remember=True, defaults={"1": TMAI}, file_name="2"),
            spec("Party Role", defaults={"1": "proprietor", "2": "publisher"},
                 help="How the agreement refers to them, such as proprietor or publisher."),
            spec("Party Description", "long", remember=True,
                 defaults={"1": "the authorized representative of the author"}),
            spec("Party Address", "long", expected=True, remember=True,
                 defaults={"1": "100 Example Street, Springfield, U.S.A."}),
            spec("Party Signatory", expected=True, remember=True, defaults={"1": "Sam Taylor"}),
            spec("Party Signatory Title", remember=True, defaults={"1": "Director of Publishing"}),
        ],
    },
    {
        "name": "Works",
        "group": {"name": "Works", "item": "Work", "min": 1, "start": 1},
        "fields": [
            spec("Work Title", expected=True, file_name="1"),
            spec("Work Author", expected=True),
            spec("Work Original Publisher", help="As named in the copyright notice."),
            spec("Work Copyright", help="Years and holder, such as ©1999 by Joan Example."),
            spec("Work ISBN"),
        ],
    },
    {
        "name": "Edition",
        "fields": [
            spec("Language", expected=True),
            spec("Translator"),
        ],
    },
    {
        "name": "Rights and territory",
        "fields": [
            spec("Rights Licensed", "checklist", expected=True, options=[
                option("Print"),
                option("Electronic (with appropriate digital rights management)",
                       "electronic (with the appropriate digital rights management)"),
                option("Audio book"),
                option("Digital"),
                option("All formats", "all", everything=True),
            ]),
            spec("Territory", "territory", expected=True,
                 worldwide="throughout the world", place="in {}",
                 help="Type the countries or regions, or tick Worldwide."),
            spec("License Type", "choice", default="Exclusive", options=[
                option("Exclusive", "an exclusive"),
                option("Non-exclusive", "a non-exclusive"),
            ]),
        ],
    },
    {
        "name": "Term and dates",
        "fields": [
            spec("Agreement Date", "date"),
            spec("Term Years", "number"),
            spec("Expiration Date", "date", expected=True),
            spec("Publication Deadline Months", "number", default="18"),
            spec("Signing Deadline", "date"),
        ],
    },
    {
        "name": "Copies and delivery",
        "fields": [
            spec("Print Copy Limit", "number"),
            spec("Ebook Copy Limit", "number"),
            spec("Copies to Proprietor", "number", default="7"),
            spec("Free Copies for Training", "number"),
        ],
    },
    {
        "name": "Fees and funding",
        "fields": [
            spec("One-time Fee", "money"),
            spec("Funding Amount", "money"),
        ],
    },
]

CLUSTER_NAMES = [c["name"] for c in CLUSTERS]


def cluster(name):
    for c in CLUSTERS:
        if core.key(c["name"]) == core.key(name):
            return c
    return None


class FieldSet:
    """A named choice of clusters, plus fields of its own."""

    def __init__(self, name, clusters=(), custom=(), builtin=False, path=None):
        self.name = name
        self.cluster_names = [c for c in clusters if cluster(c)]
        self.custom = [dict(c) for c in custom]
        self.builtin = builtin
        self.path = path

    def clusters(self):
        """Clusters in order, with the set's own fields gathered under their section names."""
        out = [cluster(n) for n in self.cluster_names]
        sections = {}
        for f in self.custom:
            section = f.get("section") or "Other details"
            if section not in sections:
                sections[section] = {"name": section, "fields": []}
                out.append(sections[section])
            sections[section]["fields"].append(f)
        return out

    def specs(self):
        """(cluster, field spec) in order."""
        return [(c, f) for c in self.clusters() for f in c["fields"]]

    def groups(self):
        return [c for c in self.clusters() if c.get("group")]

    def to_dict(self):
        return {"app": core.APP_NAME, "name": self.name, "clusters": self.cluster_names,
                "fields": self.custom}

    def codes(self):
        """The {{...}} codes for a template, for whoever writes it."""
        lines = [f"FIELD CODES: {self.name}", "",
                 "Copy these into the Word template where each should appear.", ""]
        for c in self.clusters():
            lines.append(c["name"].upper())
            g = c.get("group")
            if g:
                item = g["item"]
                lines.append(f"  This can repeat: one {item.lower()} or several "
                             f"(the form starts with {g['start']}).")
                lines.append(f"  How many:        {{{{{g['name']} | plural: {item.lower()}, "
                             f"{g['name'].lower()}}}}}")
            for f in c["fields"]:
                lines.extend("  " + x for x in _codes_for(f, g))
            lines.append("")
        lines += ["Any code can also go in a condition, so a clause only appears when the field",
                  "is filled in or relevant:  {{#if Funding Amount}} ... {{/if}}"]
        return "\n".join(lines)


def _codes_for(f, g):
    name, kind = f["name"], f.get("kind", "text")
    star = "  (expected)" if f.get("expected") else ""
    if g:
        item = g["item"]
        rest = name[len(item) + 1:] if name.startswith(item + " ") else name
        return [f"{name}{star}:",
                f"    one by number:  {{{{{item} 1 {rest}}}}}, {{{{{item} 2 {rest}}}}} ...",
                f"    all of them:    {{{{{name} | list}}}}   (“A and B”)",
                f"    each in turn:   {{{{#each {g['name']}}}}} ... {{{{{name}}}}} ... {{{{/each}}}}"]
    if kind == "date":
        return [f"{{{{{name} | date}}}}{star}   or  | date-formal  or  | date-short"]
    if kind == "money":
        return [f"{{{{{name} | money}}}}{star}   or  | money-words  or  | money-whole"]
    if kind == "number":
        return [f"{{{{{name}}}}}{star}   or  {{{{{name} | number-words}}}}"]
    if kind == "checklist":
        return [f"{{{{{name}}}}}{star}   (the ticked ones: “print and audio book”)",
                f"    {{{{{name} | plural: format, formats}}}}   follows how many are ticked",
                f"    {{{{#if {name} = {f['options'][0]['label']}}}}} ... {{{{/if}}}}   when that one is ticked"]
    if kind == "territory":
        return [f"{{{{{name}}}}}{star}   (“{f.get('worldwide', 'throughout the world')}” when "
                f"Worldwide is ticked, otherwise “{f.get('place', 'in {}').format('Italy')}”)"]
    if kind == "yesno":
        return [f"{{{{#if {name}}}}} ... {{{{/if}}}}{star}   a switch for an optional clause"]
    return [f"{{{{{name}}}}}{star}"]


BUILTIN = [FieldSet("Publishing agreement", CLUSTER_NAMES, builtin=True)]


# ---------------------------------------------------------------- storage ---

def sets_folder(templates_folder=None):
    if templates_folder and pathlib.Path(templates_folder).is_dir():
        return pathlib.Path(templates_folder) / "Field sets"
    return pathlib.Path.home() / ".tmai-contract-builder-field-sets"


def load_all(templates_folder=None):
    """The built-in sets, then any saved ones, by name."""
    out = list(BUILTIN)
    folder = sets_folder(templates_folder)
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                out.append(FieldSet(data["name"], data.get("clusters", []), data.get("fields", []),
                                    path=path))
            except (ValueError, KeyError, OSError):
                continue
    return out


def find(sets, name):
    for s in sets:
        if core.key(s.name) == core.key(name or ""):
            return s
    return None


def save(fieldset, templates_folder=None):
    folder = sets_folder(templates_folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (re.sub(r'[<>:"/\\|?*]', "", fieldset.name).strip() + ".json")
    if fieldset.path and pathlib.Path(fieldset.path) != path and pathlib.Path(fieldset.path).exists():
        pathlib.Path(fieldset.path).unlink()                  # renamed
    path.write_text(json.dumps(fieldset.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    fieldset.path = path
    return path


def delete(fieldset):
    if fieldset.path and pathlib.Path(fieldset.path).exists():
        pathlib.Path(fieldset.path).unlink()


def best_for(path, sets):
    """The set whose fields a template uses most, if it uses at least two of them."""
    names = core.Template(path).token_names()
    best, score = None, 1
    for s in sets:
        known ={core.key(f["name"]) for _, f in s.specs()}
        groups = {core.key(c["group"]["name"]) for c in s.groups()}
        hits = 0
        for n in names:
            k = core.key(n)
            plain = core.key(re.sub(r"\s\d+(?=\s|$)", "", n))
            if k in known or plain in known or k in groups:
                hits += 1
        if hits > score:
            best, score = s, hits
    return best
