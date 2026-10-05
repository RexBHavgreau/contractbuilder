# TMAI Contract Builder

A small desktop app (Windows and macOS) that builds finished contracts from Word templates.
The wording that stays the same lives in the template; the parts that change each time are
written as `{{Client Name}}`, `{{Fee | money-words}}` and so on, and optional or alternative
clauses sit between `{{#if ...}}` and `{{/if}}`. The app reads the template, builds a form
for exactly those fields, and writes a new `.docx` with everything filled in, keeping the
template's formatting, numbering, tables, headers and footers.

With the built-in **Publishing agreement** field set, the form is laid out the way a publishing
contract is: parties (two by default, Party 1 remembered from last time), works (one by default,
"Add another work"), rights licensed as tick boxes, territory with a Worldwide option, term,
copies, fees. Any field can be marked not relevant, and the app warns when something a
publishing agreement is expected to have is missing. People can build and name their own field
sets from the same clusters plus fields of their own.

It also:

- shows how dates and amounts will read as you type them ("12500" becomes
  "Twelve Thousand Five Hundred Dollars ($12,500.00)")
- can highlight everything it filled in, for review
- saves and reloads answers, for renewals and amendments
- makes many contracts at once from an Excel or CSV sheet
- turns an existing contract into a template by swapping chosen wording for fields

| File | What it is |
| --- | --- |
| `app.py` | the window |
| `core.py` | the engine: reading templates, filling them in, spreadsheets |
| `fieldsets.py` | field sets: the built-in Publishing agreement, and saving people's own |
| `USER-GUIDE.txt` | for the people using it, and for whoever writes templates |
| `BUILD-NOTES.txt` | turning it into a single `.exe` / `.app` |
| `build-windows.bat`, `build-mac.command` | double-click builds |
| `examples/` | a sample publishing MOU template, a sample services agreement, and a sample spreadsheet |
| `tests/` | `python -m pytest tests` |

Run from source: `pip install lxml openpyxl`, then `python app.py`.
