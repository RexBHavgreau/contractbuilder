# CLAUDE.md — Word Template Filler (formerly TMAI Contract Builder)

This file is the project's memory. Read it before changing anything. When
you finish a piece of work, add to the **Progress log**, and add to the
**Decision log** for any choice a later person would otherwise have to
rediscover. Open work lives in [TASKS.md](TASKS.md).

## What it is

A desktop app (Windows first, macOS too) for a TMAI department that makes
contracts and similar documents in two ways:

1. **Word-template workflow:** An ordinary `.docx`/`.dotx` contains
   `{{Field Name}}` placeholders, optionally with a format
   (`{{Fee | money-words}}`, `{{Start Date | date-formal}}`) or optional
   wording (`{{#if Field}} … {{/if}}`). The app finds the fields, shows a
   form, and writes a filled-in copy. The source template is never changed.
2. **Component-builder workflow (planned):** Users create reusable contract
   components inside the app with a simple formatting editor, or import
   existing DOCX content. The app stores component wording as Markdown text
   in the local SQLite database, with metadata and version history. The
   supported content includes ordinary paragraphs, headings, emphasis,
   lists, and tables. Users assemble selected components in order; a Word
   document shell supplies page layout, styles, headers and footers. The
   assembled document then uses the existing field syntax and rendering
   engine. Users do not need to know Markdown.

The component builder is an additional workflow, not a replacement for
Word-template creation. Both workflows use the same local publisher profiles
and field-rendering capabilities.

The owner is Beaux Hargrove (GitHub: RexBHavgreau). The users are office
staff, not developers: every message, guide and dialog is written in plain
English, says what happened and what to do next, and never shows a stack
trace.

## Layout

| File | Role |
| --- | --- |
| `simple_app.py` | The packaged app: choose a template, fill in its fields, create the document. Publisher profiles, update checks and installs. |
| `app.py` | Launcher for `simple_app.py`. |
| `core.py` | The engine. Reads templates, validates values, renders the `.docx` by editing WordprocessingML with lxml. No UI. |
| `md_parse.py` | Configured CommonMark parser for components; tables are enabled and raw HTML is disabled. |
| `md_to_word.py` | Converts supported component Markdown blocks and inline formatting to WordprocessingML paragraphs, lists and tables. |
| `docx_compose.py` | Builds a new DOCX from ordered Markdown components and a validated Word shell; preserves shell parts and merges/remaps list numbering. |
| `shell_check.py` | Read-only validation of Word document shells, including style, numbering and final section requirements. |
| `shell_selection.py` | Checks a picked shell, gives plain-English findings, and remembers the last shell that can be used. Does not change the shell file. |
| `docx_to_markdown.py` | Reads DOCX body paragraphs and tables in order and produces a plain Markdown draft. |
| `markdown_files.py` | UTF-8 Markdown file import/export; reports unsupported constructs without discarding source. |
| `publisher_profiles.py` | Local SQLite store of publisher details, and mapping onto template fields. |
| `update_checker.py` | Asks GitHub Releases for the latest version and its attached files. |
| `self_update.py` | Downloads, verifies and swaps in a new Windows `.exe`; stores an optional per-user update token. |
| `version.py` | `APP_NAME`, `APP_VERSION`, `GITHUB_REPOSITORY`. The single source of the version. |
| `advanced_app.py` | The earlier contract-builder window (batch spreadsheets, template maker). Kept, **not packaged** — see TASKS.md. |
| `build-windows.bat` → `build-windows.ps1` | Local Windows build. |
| `build-mac.command` | Local macOS build. |
| `.github/workflows/build.yml` | Tests, Windows/macOS builds, releases, and side-by-side Windows package-size measurement with and without T-019 modules. |
| `scripts/check_executable_size.py` | Measures the built Windows executable and enforces the 30 MiB release limit. |
| `tests/` | `python -m pytest tests` |
| `USER-GUIDE.txt` | Shown from Help and bundled into the app. |
| `BUILD-NOTES.txt` | How to build and release, for whoever maintains it. |

## Working on it

- Python 3.9+. `pip install -r requirements.txt pytest python-docx` (the app needs lxml, openpyxl, markdown-it-py and mdurl), then
  `python -m pytest tests`. Every change keeps the suite green and adds
  tests for new behaviour.
- To see the window on a headless Linux box: install `python3-tk`, run under
  `xvfb-run`, drive it from a script, screenshot with ImageMagick `import`.
  Stub `messagebox`/`filedialog` so nothing blocks.
- Releases: raise `APP_VERSION` in `version.py`, add a matching,
  non-empty section to `CHANGES.txt`, and merge to `main`. CI checks that
  the current version has notes, extracts that section for the GitHub release
  body, tags `vX.Y.Z`, and publishes the release with
  `Word-Template-Filler-windows-x64.exe` attached. The updater looks for
  exactly that file name; do not rename it.
- `build-windows.bat` must keep CRLF line endings. The Windows CI job
  checks the file's bytes for CRLF (and rejects mixed endings), and parses
  `build-windows.ps1` with Windows PowerShell 5.1 before building. This
  catches syntax and line-ending slips before PyInstaller runs.
- Never put a token, password or key in the code, a template, the build or
  the repository. The update token is entered per user in the app.
- **Test data is invented.** Never copy a name, address, number, title or
  term from a real contract into the repository, not even into a test or a
  task description: it is public. CI enforces this with
  `tests/test_no_private_details.py`, which checks every file against a
  private list held in the GitHub secret `BLOCKED_TERMS`. If it fails, it
  names the file and line; replace the detail, do not just reword around it.
- Work on a branch and open a pull request into `main`. Keep commits small
  and say why, not only what.

## Pitfalls already paid for

- **Windows PowerShell 5.1** (what `build-windows.bat` runs) strips embedded
  double quotes from arguments passed to programs. `python -c "...\"x\"..."`
  arrives broken. Run Python on a script *file*. This broke every local
  Windows build until 0.3.0.
- **PowerShell 5.1 `Tee-Object`/`Out-File` write UTF-16.** Mixed into a UTF-8
  log it gives "L o o k i n g". Log with `Add-Content -Encoding UTF8`.
- **CI that skips a code path proves nothing about it.** The build server
  used to bypass the Python test the local build relied on. Now it runs the
  same path, under the same PowerShell 5.1.
- LibreOffice puts its own `python.exe` (no tkinter, no pip) on PATH; the
  Microsoft Store puts empty alias `.exe`s there. Test before trusting.
- **The repository is public** (since 2026-11-17). Everything in it, and
  everything in its history, is visible to anyone. Test data must be
  invented; never commit names, addresses or terms from a real contract.

- **Removing something from a public repository means rewriting history**,
  and even that does not reach GitHub's own copies: pull requests keep the
  old commits, and old commit pages stay viewable until GitHub Support purges
  them. Real contract details had to be removed this way on 2026-11-18. The
  cheap fix is never committing them (see "Working on it").
- Commits made on the GitHub website record the account's email address
  unless "Keep my email addresses private" is on (Settings > Emails).
- **Unsigned checks to GitHub are limited to 60 an hour per internet
  address**, shared by everyone in one office. See TASKS.md T-012.
- A release tagged on a commit whose `version.py` disagrees fails CI and has
  no files (v0.2.0). Hence release-on-version-bump.
- Word splits text into many runs (one MOU had 917 runs in 52 paragraphs;
  "June 1, 2031" was three runs). The engine matches across runs; keep
  it that way. Real contracts also arrive with tracked changes, comments,
  curly quotes, letter-spacing from PDF conversion, and tab-aligned
  signature blocks.
- A running Windows `.exe` cannot overwrite itself: the swap is done by a
  batch script after exit. `timeout` fails without a console (use `ping`),
  and `cmd /c` needs `/s` and an outer pair of quotes for paths with spaces.

## Decision log

Newest last. Each entry: date, decision, why, consequences. (Some entries from 2026-11-18 sit above the older ones and are not bolded; the order is not strictly chronological.)

- **2026-11-18 — Public update checks do not require a token.** The per-user token field remains optional for users who frequently hit GitHub's unauthenticated API limit. A 404 without a token means no release is published yet or the repository has moved; it does not prompt users to configure credentials.


- **2026-11-18 — Explain first-run warnings for unsigned downloads.** The user guide tells staff how to approve the first launch in Windows SmartScreen and macOS Gatekeeper, and the README points to it before opening a download. The in-app Windows updater should not add the browser's internet-download mark, but that warning behavior remains unconfirmed until T-002 tests it on a real PC.


- **2026-11-18 — Enforce the Windows executable size budget against the built file.** CI runs `scripts/check_executable_size.py` on the packaged release executable and fails above 31,457,280 bytes (30 MiB). The script accepts a smaller `--max-bytes` value so tests can prove the failure path without constructing a large executable.


- **2026-11-18 — Word shell contract and validation.** Shells are DOCX packages
whose body wording is ignored; they supply document styles, numbering,
table formatting, headers, footers and final section properties. The checker
requires the canonical style IDs documented in `SHELL-CONTRACT.md`, a
three-level decimal outline, bullet numbering and final `w:sectPr`. Missing
styles and numbering are warnings with explicit fallbacks; an unreadable
package, missing body or missing final section properties stops generation.
The checker is read-only. Downstream composition and assembly tasks must run
it before using a shell, surface warnings and apply the returned style map.

- **2026-11-18 — T-019-C paragraph renderer and unsupported-content handling.**
`md_to_word.render_markdown(source, shell_path)` checks the shell before
rendering and returns WordprocessingML blocks plus warnings and errors.
Paragraphs and heading styles come from the shell's canonical style IDs;
missing styles use the checker's explicit fallbacks. Bold, italic, their
combination and hard line breaks become native Word run properties/elements.
Unsupported inline constructs keep readable text where possible and return
warnings; unsupported block constructs are omitted with an explicit warning.
The list and table tasks extend this renderer with native Word numbering and tables.

- **2026-11-18 — Markdown file import/export preserves source text.** Read UTF-8
  with optional BOM support and write UTF-8 without a BOM. The importer reports
  raw HTML, images and footnotes as unsupported warnings, but retains the
  original Markdown rather than silently deleting content. This file utility
  is separate from the later DOCX importer.

- **2026-11-18 — Bundle third-party licence notices as a readable Help item.**
  The exact MIT notices for markdown-it-py 3.0.0 and mdurl 0.1.2 travel in
  `THIRD-PARTY-LICENSES.txt`, included in Windows and macOS packages. Help
  opens the notice file directly; tests ensure the pinned parser dependencies
  remain represented.

- **2026-10-05 — Desktop app in Python + Tkinter, built with PyInstaller.**
  Same shape as the department's existing CBM Article Converter, so it is
  familiar to build and run. Plain-text guides beside it.
- **2026-10-05 — Templates are plain Word documents with `{{Field}}`
  placeholders; the engine edits the document's XML in place with lxml.**
  Keeps all Word formatting, numbering, tables, headers and footers; never
  rebuilds the document. The template file is never written to.
- **2026-10-05 (Builds 2–3) — Lessons from two real MOUs built into the
  engine:** quote-insensitive and whole-word matching, accept tracked
  changes and strip comments when making a template, `list`/`plural`/
  `money-whole` formats, blank-line collapsing, template warnings.
- **2026-10-05 (Build 4, not merged) — Built-in "field sets" for publishing
  agreements** (parties, works, rights, territory…). Superseded by the
  2026-11-17 decision below; the work remains in git history at commit
  `80cbe34` (`4becc60` before the 2026-11-18 history rewrite) if any of it is
  wanted later.
- **2026-11-17 — Renamed Word Template Filler, with a focused single-document
  window (`simple_app.py`).** (Made with ChatGPT.) The earlier window lives in
  `advanced_app.py`, not packaged.
- **2026-11-17 — Publisher profiles in a local per-user SQLite database.**
  Reusable publisher details; nothing leaves the computer.
- **2026-11-17 — GitHub Actions builds Windows and macOS; `version.py` is the
  one version number.**
- **2026-11-17 — DECISION (Beaux): the contract builder bases its build on a
  template with fields built by the user.** The template the user writes
  defines what the form asks for; the app does not carry built-in schemas
  for kinds of contract. Consequences: Build 4 field sets are not merged;
  improvements go into helping users build fields in their templates
  (documentation, checks, tools), not into hard-coded contract types.
- **2026-11-17 — The Windows build tests each Python from a script file and
  logs in UTF-8; the build server runs the same test.** Fixes the build
  failing on every PC with Windows PowerShell 5.1.
- **2026-11-17 — The Windows app installs its own updates** after the user
  agrees: download beside the `.exe`, verify size and GitHub's SHA-256
  digest, swap after exit, reopen. Falls back to Downloads if the folder is
  read-only. Private repository → per-user read-only token in Help > Update
  settings. (The open question this raised was settled the same day: the
  repository was made public, below.)
- **2026-11-17 — Releases publish themselves when `main` gets a new
  `APP_VERSION`.** Removes the hand-made tag that went wrong for v0.2.0.
- **2026-11-17 — DECISION (Beaux): the repository is public** (TASKS.md
  T-001, option 1 of three). Colleagues' copies find and install updates
  with no setup. Consequences: the update token becomes optional (wording:
  T-010); unsigned checks meet GitHub's hourly limit (T-012); everything in
  the repository and its history is public (T-013, T-016).
- **2026-11-17 — DECISION (Beaux): the app is not code-signed** (T-009):
  "too expensive to be worth it." Consequences: Windows SmartScreen and
  macOS Gatekeeper warn the first time each person runs a downloaded copy;
  the user guide must say what to click (T-011).
- **2026-11-18 — COLLABORATIVE DECISION (Beaux and ChatGPT, T-008):
  add a component-based contract-building workflow without replacing Word
  templates.** The complete agreed proposal is in
  [PROPOSAL-001.md](PROPOSAL-001.md). Keep `simple_app.py` as the packaged
  app; do not merge `advanced_app.py` wholesale. Do not carry its spreadsheet
  batch workflow forward. Leave its saved-answer and contract-to-template
  features un-packaged for now and revisit them separately if needed. Users
  should author components inside the application without needing to know
  Markdown, and should also be able to import existing DOCX content. Markdown
  is the canonical component representation, stored as text in the same
  local SQLite database as publisher profiles, with metadata and version
  history. Support ordinary contract content including paragraphs, headings,
  bold, italic, lists, and tables. Use markdown-it-py with table support
  enabled and the existing lxml/zipfile infrastructure to render native
  WordprocessingML; do not add Pandoc or python-docx to the initial design.
  A Word document shell supplies document-level formatting (page setup,
  styles, headers, footers); it is not the source of assembled contract body
  wording. DOCX import converts supported content to Markdown in document
  order and reports unsupported structures rather than silently discarding
  them. An assembly pins the component versions it uses. Users may review
  and deliberately update selected components to newer versions; updates
  are never silent. Keep the existing template workflow and `core.py` field
  syntax intact. Target a Windows release executable no larger than 30 MB;
  measure actual packaged output rather than relying on source or wheel
  sizes. T-019 proves Markdown-to-Word conversion and field filling; T-020
  handles DOCX-to-Markdown import before the editor and library are built.
- **2026-11-18 — DECISION (Beaux): details of real contracts are removed
  permanently, "even if that means rewriting history"** (TASKS.md T-016).
  Every branch and tag was rewritten with `git filter-repo`: each real detail
  replaced with an invented one, and Beaux's personal email in 90 commits
  replaced with his GitHub noreply address. Consequences: all commit ids
  changed (old ids map to new in `commit-map.txt`, handed to Beaux); every
  clone made before the rewrite is stale and must be replaced; the
  force-push, GitHub Support's purge of pull-request copies and the
  `BLOCKED_TERMS` secret are Beaux's (T-018), because this session may push
  only its own branch. A test keeps such details out from now on.
- **2026-11-18 — DECISION (Beaux, T-025): clause numbering uses standard
  nested ordered Markdown lists, rendered as a decimal outline; no new
  Markdown syntax.** Position in the nesting decides the number (1., 1.1,
  1.1.1), not the digits typed. The editor offers numbered list, indent and
  outdent so users never type indentation; the Word output uses one
  multi-level numbering definition from the shell; imports of Word
  multi-level lists become nested lists, and letter or Roman styles become
  decimal with a warning. Consequences: typed cross-references ("see Section
  2.1") do not follow moved clauses; underline, page breaks, signature
  blocks and defined terms are out of scope (Beaux: "shouldn't matter";
  T-032). Signature blocks belong in the Word shell or a template. Italic
  is `_text_`; Markdown has no underline, and imported underline is dropped
  with a warning.
- **2026-11-17 — DECISION (Beaux): no sample templates in the repository.**
  `examples/` was deleted. Tests build their own sample in a temporary
  folder (`tests/sample.py`; tidy-up is T-014).

- **2026-11-18 — Sample generator output paths are explicit and safe.** Running `python tests/sample.py` writes `Sample Services Agreement.docx` in the current working directory; an optional positional path selects another destination. This avoids recreating the deleted `examples/` directory and makes the script safe to run from any folder.

- **2026-11-18 — Automatic update checks are limited to once per day per user.**
  The app records the time of the last successful check in the existing
  per-user update settings file, without replacing the optional token.
  Successful manual checks count too; a manual check always bypasses the
  throttle. Failed checks do not postpone the next automatic attempt.

- **2026-11-18 — Release notes are owned by the project, not generated from PR titles.**
  `CHANGES.txt` uses one `## X.Y.Z` section per release, newest first.
  CI verifies the running `APP_VERSION` has a non-empty section and extracts
  only that section for the GitHub release body. The updater displays up to
  15 lines of that body.

- **2026-11-18 — Pin markdown-it-py 3.0.0 and mdurl 0.1.2.**
  The project still supports Python 3.9; markdown-it-py 4.x requires Python
  3.10 or later, while 3.0.0 supports Python 3.8 and later. The parser uses
  the CommonMark preset, explicitly enables tables, and disables raw HTML.
  Keep this import out of `simple_app.py` until a component-builder task
  needs it.

- **2026-11-18 — Protect component fields before Markdown parsing.** Each
  component is protected and parsed independently: replace complete
  `{{...}}` spans with collision-free alphanumeric placeholders, parse the
  Markdown, then restore the exact field text in the token tree (including
  inline children). This prevents table pipes and Markdown syntax from
  consuming field content and prevents fragments from adjacent components
  from combining into a field. Use `markdown_fields.protect_fields` and
  `restore_fields`; do not concatenate raw component source before parsing.
  The existing core engine already discovers and fills fields in paragraphs,
  list items and table cells, so no `core.py` change is needed. See T-019
  notes in `TASKS.md`.

- **2026-11-19 — The last usable shell is remembered; a shell with errors never is.** `shell_selection.choose_shell` runs the T-026 checker on the file the user picked. A shell with warnings is remembered, because the user has read them and may continue; a shell with errors is reported and does not replace the remembered one. The path is stored in `shell-settings.json` in the per-user app folder, beside the update settings, and a missing, moved or damaged file means nothing is remembered rather than an error. If the settings cannot be written, the shell still works for this session and the user is told it was not remembered. Consequence: the picker dialog belongs to the component window (T-023-A/T-022-A), which calls this function; it is not in `simple_app.py` yet. Checker messages now name the Word style as users see it ("Heading 1", "Normal Table") rather than its internal ID; the IDs remain in finding codes and `style_fallbacks`.

**2026-11-19 — T-019-D/E native list and table rendering.** Lists use real Word
numbering. Each independent list gets a new numbering instance; ordered
sub-lists share the shell's multi-level decimal definition, and their level
determines the outline number. If a shell has only one bullet level, nested
bullets reuse that valid level and use direct paragraph indentation rather
than referencing missing numbering levels. Tables use native Word table,
row, cell and grid elements; header rows repeat, alignment is mapped to
paragraph alignment, and every cell contains a paragraph. The renderer
returns new numbering definitions/instances separately from body elements.
`docx_compose.compose_document` merges them into the shell numbering part,
remaps abstract and instance IDs per component, and updates paragraph
references before insertion. It creates a numbering part, relationship and
content-type override when a shell lacks numbering. The shell is never
modified; only its document body wording is replaced in the new output.

**2026-11-19 — T-019-F/G shell composition and field-engine hand-off.**
`docx_compose.compose_document(shell_path, components, output_path)` renders
each component independently, replaces only the shell body, and retains the
final section properties and all other shell package parts. It preserves
component and block order, leaves the shell byte-for-byte unchanged, and
writes through a temporary file. Generated numbering definitions and
instances are merged into the shell numbering part; IDs and paragraph
references are remapped per component so independent lists cannot collide.
When a shell has no numbering part, the composer creates the part, document
relationship and content-type override. The composed DOCX is then accepted by
the existing `core.Template` and `core.render` pipeline without changing
`core.py`: repeated fields are discovered once and filled in paragraphs,
lists and tables; block conditionals can cross component boundaries, and
inline conditionals work inside table cells. The tests cover both values of
each condition and the existing `money-words` and `date-formal` formats.

**2026-11-19 — T-019-H measured Windows package size with the component
stack included.** GitHub Actions run #166 built the same `simple_app.py`
entry point twice with the same one-file/windowed PyInstaller configuration.
The ordinary build was 17,801,283 bytes (16.98 MiB). The comparison build
explicitly included `md_parse`, `markdown_fields`, `shell_check`,
`md_to_word` and `docx_compose` and was 17,962,926 bytes (17.13 MiB).
The component-builder stack therefore adds 161,643 bytes (0.15 MiB).
The expanded build leaves 13,494,354 bytes (12.87 MiB) below the 30 MiB
limit. This is not close to the 3 MiB warning margin, so there is no
immediate packaging constraint. The Windows CI workflow retains this
comparison and checks the expanded build against the size limit on future
runs.

- **2026-11-19 — Clause numbering continues across the assembled contract.**
  Beaux chose continuous numbering across the whole assembled document
  (T-033 option 1). Every ordered list in every component is remapped to one
  shared native Word `w:num` instance, so clauses continue across component
  boundaries, separate lists, paragraphs and tables. Nested ordered items
  retain the shell's multi-level decimal outline. There is no per-component
  restart setting; schedules or exhibits needing separate numbering require
  a future explicit feature. T-030 still requires a real-Word check on
  Windows and macOS if available.

## Progress log

Newest last.

- **2026-11-19** T-019-D and T-033 (ChatGPT, [PR #27](https://github.com/RexBHavgreau/contractbuilder/pull/27)): Beaux chose continuous clause numbering across the assembled contract. The composer now remaps all ordered lists across all components to one shared native Word numbering instance, while retaining the shell's multi-level decimal outline and separate bullet-list instances. Regression coverage checks continuity across separate lists, component boundaries, intervening paragraphs and tables. T-019 is complete; real-Word verification remains T-030.

- **2026-11-19** T-002 (Beaux): ran the v0.3.0 build and the 0.3.0 to 0.3.1 self-update on a Windows PC. Everything worked; an error message appeared during install without affecting the app (details: TASKS.md T-034). T-018: Beaux confirmed no other copies of the old history exist; GitHub Support's purge is the only thing outstanding, and a check on 2026-11-19 shows pull requests #1 and #6 still serve the old commits.

- **2026-11-18** T-019-C (ChatGPT, [PR #19](https://github.com/RexBHavgreau/contractbuilder/pull/19)): added `md_to_word.py` to render paragraphs, headings 1–3, hard line breaks, bold, italic and combined emphasis as WordprocessingML. Field placeholders are restored before rendering, shell style fallbacks are applied, and unsupported Markdown is surfaced as warnings. Added XML-level tests for each supported construct and fallback/error behavior.

- **2026-11-18** T-015 (ChatGPT, [PR #17](https://github.com/RexBHavgreau/contractbuilder/pull/17)): raised `APP_VERSION` to 0.3.1. The matching `CHANGES.txt` release notes were already present; merging this PR should trigger the configured release workflow. The v0.3.1 release was published with the Windows `.exe` and both macOS zips (checked 2026-11-19); real-Windows self-update validation remains T-002.

- **2026-11-18** T-020-A (ChatGPT, [PR #16](https://github.com/RexBHavgreau/contractbuilder/pull/16)): added a read-only DOCX importer that walks body paragraphs and tables in source order, returns a Markdown draft with located warnings, and gives a plain-English error for invalid packages. Tests use invented documents and verify the source file is unchanged.

- **2026-11-18** T-020-G and T-028 (ChatGPT, [PR #16](https://github.com/RexBHavgreau/contractbuilder/pull/16)): added UTF-8 Markdown
  file import/export with BOM support and non-destructive warnings for raw
  HTML, images and footnotes; added bundled MIT notices for markdown-it-py
  and mdurl, displayed through Help and included in Windows/macOS builds.

- **2026-11-18** T-012, T-017 and T-019-B (ChatGPT, [PR #15](https://github.com/RexBHavgreau/contractbuilder/pull/15)): rate-limited update responses now have a clear message; automatic checks run no more than once a day, while manual checks remain available; versioned plain-English notes are published and shown in the update prompt; and the table-enabled, raw-HTML-disabled Markdown parser is installed and tested. GitHub Actions run 87 passed all 103 tests and built Windows x64, macOS Intel and macOS Apple Silicon.

- **2026-11-18** T-026 (ChatGPT, [PR #18](https://github.com/RexBHavgreau/contractbuilder/pull/18)): defined the DOCX shell contract,
  added a read-only checker with explicit style fallbacks and numbering/
  section checks, and added an invented shell fixture with tests. See
  `SHELL-CONTRACT.md`. Downstream renderer and assembly tasks must call the
  checker before generation.

- **2026-10-05** Build 1: TMAI Contract Builder — template engine, form,
  previews, highlights, saved answers, spreadsheet batches, template maker.
- **2026-10-05** Builds 2–3: real-MOU fixes (see decision log). Merged as PR #1.
- **2026-10-05** Build 4: publishing field sets — on branch, not merged.
- **2026-11-17** v0.1.0–v0.2.0 (ChatGPT): Word Template Filler, focused
  window, publisher profiles, update check, CI builds. v0.2.0's release was
  published with no files because its tag disagreed with `version.py`.
- **2026-11-17** v0.3.0 (Claude): local Windows build fixed (PowerShell 5.1
  quoting and UTF-16 log); Windows self-update with verification; update
  token setting; release on version bump; CLAUDE.md and TASKS.md added.
  80 tests pass. Not yet confirmed on a real Windows PC — TASKS.md T-002.

- **2026-11-17** T-005 (ChatGPT, [PR #7](https://github.com/RexBHavgreau/contractbuilder/pull/7)): CI now parses the Windows build script with PowerShell 5.1 and rejects invalid batch-file line endings. A deliberately broken PowerShell copy failed the new step before Python setup; restoring it produced a green Windows build.

- **2026-11-17** T-006 (ChatGPT, [PR #8](https://github.com/RexBHavgreau/contractbuilder/pull/8)): the built Windows app now removes an abandoned `.exe.new` update download only when it is older than 24 hours. Recent files, symlinks, missing files and inaccessible files are left alone. CI tests passed.

- **2026-11-17** T-007 (ChatGPT, [PR #9](https://github.com/RexBHavgreau/contractbuilder/pull/9)): expanded the template-author guide with examples for every format and condition, added a dedicated Help menu window, and added a DOCX rendering test for the documented syntax.

- **2026-11-17** Beaux: v0.2.0's empty release deleted, its tag kept (T-003);
  repository made public (T-001); code signing declined (T-009); `examples/`
  deleted.

- **2026-11-18** Task review (Claude): v0.3.0 confirmed published by CI on its
  own, with the Windows `.exe` and both macOS builds, each with a SHA-256
  digest; CI green on every push to `main` since PR #6 (runs 44 to 60), which
  closed T-004 without a change; T-005 to T-007 checked against the code and
  86 passing tests. Found that the app and guides still call the repository
  private, that nothing tells users about the unsigned-app warnings, that
  GitHub's hourly limit now applies to update checks, and that a real
  counterparty name is still in the tests and, with a few other real details,
  in the now-public history. Added T-010 to T-017 for these.

- **2026-11-18** T-008 decision (Beaux and ChatGPT, collaborative):
  retain the existing Word-template workflow and add a separate Markdown-based
  component builder. Users will author content in-app or import DOCX content;
  tables are part of the supported Markdown subset. A Word shell supplies
  document-level formatting, and component versions are pinned in saved
  assemblies with deliberate updates. The Windows release target is 30 MB.
  Full architecture and implementation plan: [PROPOSAL-001.md](PROPOSAL-001.md).
  T-019 covers Markdown-to-Word composition; T-020 covers DOCX import.
  Spreadsheet batch creation from `advanced_app.py` is not being carried forward.
- **2026-11-18** History rewrite (Claude, T-013 and T-016): searched all ten
  branches, three tags, every commit message and the inside of every Word and
  Excel file for 51 details recorded from the memoranda; 22 were present.
  Replaced them, and the personal email in 90 commits, across all history;
  verified none remain, `main` changed only in the replaced words, and all
  tests pass. Added `tests/test_no_private_details.py` and the CI secret it
  reads. Pushing it was refused to this session (it may push only its own
  branch), so it is prepared for Beaux as TASKS.md T-018.

- **2026-11-18** Beaux pushed the cleaned history and sent GitHub Support the
  purge request (T-018). Verified by Claude: every branch and tag on GitHub
  matches the cleaned copy; a fresh clone has none of the removed details and
  no personal email; the `BLOCKED_TERMS` secret reaches CI and the guard
  passes (run 67); no forks. Still open: the old commits remain fetchable
  through pull requests #1 to #9 until GitHub Support purges them.


- **2026-11-18** T-014 (ChatGPT, [PR #14](https://github.com/RexBHavgreau/contractbuilder/pull/14)): corrected the sample generator's description and output path, added an optional command-line destination, ignored generated sample files and the old `examples/` directory, and added CLI regression tests for both output modes. The full Python test job passed in CI.

- **2026-11-18** T-027 (ChatGPT, [PR #14](https://github.com/RexBHavgreau/contractbuilder/pull/14)): added a tested executable-size checker and a Windows CI step that measures the packaged `.exe`, logs its size and remaining headroom, and fails above 30 MiB. Tests verify the normal limit, an intentionally tiny failing limit, and the exact boundary.

- **2026-11-18** T-011 (ChatGPT, [PR #14](https://github.com/RexBHavgreau/contractbuilder/pull/14)): added first-run SmartScreen and Gatekeeper instructions near the start of the user guide, linked to them from the README, and documented the unconfirmed expectation for Windows in-app updates. T-002 is responsible for confirming that behavior on a real PC.

- **2026-11-18** T-010 (ChatGPT, [PR #14](https://github.com/RexBHavgreau/contractbuilder/pull/14)): removed mandatory private-repository update instructions, made the saved token explicitly optional for users who often hit GitHub's API limit, corrected the no-token 404 message and its `needs_token` flag, removed the obsolete startup status message, and updated tests and project documentation.

- **2026-11-18** T-019-A (ChatGPT, [PR #19](https://github.com/RexBHavgreau/contractbuilder/pull/19)): added per-component Markdown field protection using collision-free alphanumeric placeholders, with token-tree restoration. Tests demonstrate that unprotected table pipes split cells and paired double asterisks corrupt field names, preserve conditional markers in paragraphs, lists and table cells, guard component boundaries and placeholder collisions, and prove that the existing core engine fills fields in paragraphs, list items and table cells without a core.py change. GitHub Actions test job passed all 143 tests.

- **2026-11-19** T-023-B (Claude): added `shell_selection.py`, which checks a picked shell with the T-026 checker, turns the findings into plain-English lines, and remembers the last shell that can be used in a per-user settings file. Checker messages now show Word's visible style names instead of style IDs. Added `tests/test_shell_selection.py` (17 tests, invented shells only). The file picker itself is not built yet; it belongs to the component window. Full suite: 167 passed, 1 skipped; `test_updates.py::test_successful_update_check_time_limits_only_automatic_checks` fails only because this sandbox's Python has no `tkinter` (it also fails on the untouched branch).

- **2026-11-19** T-020-E (ChatGPT): DOCX import now reports unsupported body structures and package-level content with plain-English locations. Tracked changes are explicitly reported and read in Word's accepted view (insertions/move-to retained; deletions/move-from excluded). Added invented fixtures for drawings, equations, fields, content controls, notes, comments, page/section breaks, headers and footers; import remains read-only. Full suite: 173 passed.

- **2026-11-19** T-019-D and T-019-E (ChatGPT, [PR #25](https://github.com/RexBHavgreau/contractbuilder/pull/25)): added native Word numbering for ordered and bulleted lists, independent list restart instances, three-level decimal outlines, unnumbered continuation paragraphs, nested bullet indentation, and native GFM tables with header rows, shell table styles, alignment, inline emphasis, protected fields and empty cells. The renderer returns numbering definitions/instances for the composer to merge; the shell remains read-only.

- **2026-11-19** T-019-F and T-019-G (ChatGPT, [PR #25](https://github.com/RexBHavgreau/contractbuilder/pull/25)): added `docx_compose.py` to assemble ordered Markdown components into a new DOCX while preserving shell styles, headers, footers, page setup, relationships and final section properties. Numbering IDs are merged and remapped across components, including a generated numbering part when the shell lacks one. End-to-end tests prove field discovery and filling in paragraphs, lists and tables, conditional blocks across components and inside cells, and existing money/date formats. The shell remains byte-for-byte unchanged. CI run #160: 194 tests passed; Windows x64, macOS Intel and macOS Apple Silicon builds passed.
- **2026-11-19** T-019-H (ChatGPT, [PR #27](https://github.com/RexBHavgreau/contractbuilder/pull/27)): added a Windows CI comparison build that forces the T-019 modules into the same `simple_app.py` executable, then measures the actual files and checks both against 30 MiB. CI run #166 measured 17,801,283 bytes without the component stack and 17,962,926 bytes with it: a 161,643-byte (0.15 MiB) increase. The component-enabled build remains at 17.13 MiB with 12.87 MiB of headroom. The project remains open at the umbrella level because T-019-D has one separate numbering-continuity item reopened pending Beaux's T-033 decision.

- **2026-11-19** T-020-B, T-020-C and T-020-D (ChatGPT, [PR #28](https://github.com/RexBHavgreau/contractbuilder/pull/28)): expanded the read-only DOCX importer to map Word heading styles and outline levels, preserve split-run bold and italic, escape literal Markdown punctuation, and keep split component fields intact. It now reads style-level and package numbering to import bullets and nested lists, converts letter/Roman numbering to decimal with a warning, and flags typed list markers. Rectangular tables become GFM tables; merged cells, nested tables, multi-paragraph cells and lists in cells produce located warnings while retaining best-effort text. Added fixtures for the supported subset and edge cases; the focused importer suite passes all 21 tests locally. No runtime dependency was added.
