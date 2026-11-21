# CLAUDE.md — Contract Builder (formerly Word Template Filler and TMAI Contract Builder)

This file holds the project's standing rules: read it before changing
anything. It is edited rarely, by a deliberate change, not by every pull
request. When you finish a piece of work, add a file under
[progress/](progress/README.md), and one under
[decisions/](decisions/README.md) for any choice a later person would
otherwise have to rediscover; do not add log entries here (T-053). Open work
lives in [tasks/](tasks/README.md), one file per task; the rules are in
[TASKS.md](TASKS.md) and the board is `python scripts/board.py` (T-054).

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
| `simple_app.py` | The packaged app's entry point and main window (`WordTemplateFiller`): choose a template, fill in its fields, create the document. Keeps its name; build scripts start from it. Re-exports the widgets, dialogs and windows it uses (T-056). |
| `ui_widgets.py` | `resource_path`, `ScrollableFrame` and `FieldInput`, shared by the main window and the assembly field window. |
| `publisher_dialog.py` | The publisher profile window (create, edit, delete). |
| `assembly_document_window.py` | The field-entry window for a contract assembled from components. |
| `update_dialogs.py` | `UpdateDialogsMixin`: update check, install and update settings for the main window. |
| `help_windows.py` | `HelpWindowsMixin`: the Help menu windows. |
| `assembly_builder.py` | The Build assembly window. Re-exports the helpers below. |
| `assembly_helpers.py` | Pure, Tkinter-free assembly helpers (composition, diff lines, version updates, shell fingerprint). |
| `assembly_review_dialog.py` | The Review updates window of the assembly builder (`review_updates(builder)`). |
| `assembly_open_dialog.py` | The Open saved assembly window and `load_revision(builder, revision)`. |
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
| `component_editor/` | The Components window, one module per concern (T-052); `from component_editor import ...` still works. Pure, Tkinter-free rules: `text_rules.py` (escaping, formatting, toggles), `tables.py`, `fields.py` (placeholders, known field names), `toolbar_layout.py`, `save_feedback.py`. Widgets: `styling.py` (formatted view), `toolbar.py`, `wording_actions.py` and `library_list.py` (mixins of the window), `window.py`, and one module per dialog: `table_dialog.py`, `field_dialog.py`, `import_dialog.py`, `history_dialog.py`. **A new window or dialog is a new module**, never more lines in an existing one. |
| `component_preview.py` | Renders Markdown into styled text segments for the editor's read-only preview; uses the existing parser and field helpers. |
| `library.py` | Tkinter-free component/assembly persistence, immutable versions, revision pinning, archive/restore and newer-version review; shares the publisher SQLite database. |
| `update_checker.py` | Asks GitHub Releases for the latest version and its attached files. |
| `self_update.py` | Downloads, verifies and swaps in a new Windows `.exe`; stores an optional per-user update token. |
| `version.py` | `APP_NAME`, `APP_VERSION`, `GITHUB_REPOSITORY`. The single source of the version. |
| `advanced_app.py` | The earlier contract-builder window (batch spreadsheets, template maker). Kept, **not packaged** — see tasks/T-036.md. |
| `build-windows.bat` → `build-windows.ps1` | Local Windows build. |
| `build-mac.command` | Local macOS build. |
| `.github/workflows/build.yml` | Tests, Windows/macOS builds, releases, and side-by-side Windows package-size measurement with and without the component-builder modules, including the DOCX importer. |
| `scripts/check_executable_size.py` | Measures the built Windows executable and enforces the 30 MiB release limit. |
| `scripts/show_log.py`, `scripts/project_log.py` | Print the progress or decision log in order; check entry headers. |
| `progress/`, `decisions/` | One Markdown file per progress or decision entry (T-053). |
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
- Run the real component and assembly window smoke tests with
  `xvfb-run -a python -m pytest -q tests/test_window_smoke.py`. The tests
  stub message boxes and file dialogs; CI installs `xvfb` and `xauth` and
  runs this test module separately so a window failure fails the job. Linux
  can check layout and interactions, but not Windows-only title-bar chrome
  such as the maximize button; that still needs a Windows hand check.
- Releases: raise `APP_VERSION` in `version.py`, add a matching,
  non-empty section to `CHANGES.txt`, and merge to `main`. CI checks that
  the current version has notes, extracts that section for the GitHub release
  body, tags `vX.Y.Z`, and publishes the release with
  `ContractBuilder-X.Y.Z-windows-x64.exe` attached, plus the fixed name
  `Word-Template-Filler-windows-x64.exe` for copies of 0.4.x, whose updater
  looks only for that name. The updater accepts either name, preferring the
  versioned one. Keep publishing the fixed name until no installed copy
  predates 0.4.5 (see decisions/).
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
- **CI before merge.** A pull request is not ready until its own branch has a
  completed, passing CI run at its latest commit (tests, Windows build and size
  check, macOS builds). Open it against `main`; a stacked pull request gets no
  CI run. Never skip or loosen a test to get green. After a merge, check the
  run on `main` and fix a red one first. Full rule: TASKS.md "CI before merge".
- **Size gate.** The Windows executable must stay at or below 31,457,280
  bytes (30 MiB). Every task that adds code, a dependency or a bundled file
  states its size effect in its design, and confirms the CI size numbers
  (release build and component-enabled build) before it is called done. See
  TASKS.md "Size gate"; the weekly check is T-035. The numbers (release
  build, all-modules build, headroom, growth since the last release, tool
  versions) are in the Windows job's run summary; under 3 MiB of headroom
  fails the job.
- **Claiming.** Take a task only with `python scripts/claim.py T-NNN --who
  NAME`, which creates the branch `claim/T-NNN`; GitHub refuses a second
  creation, so two agents never hold one task. Full rule: TASKS.md "To take a
  task".
- **Touches.** Each open task file in `tasks/` names the files it will change.
  `python scripts/overlaps.py` lists tasks that share one; two claimed tasks
  never share a file (T-055). A new window or dialog goes in a new module.
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
- **A PyInstaller one-file app that starts a copy of itself must reset its
  environment.** The app passes the location of its temporary `_MEI` folder to
  whatever it starts; a restarted copy **at the same path** (as in a
  self-update) then reuses a folder that is deleted when the first one closes and fails with "Failed to load Python DLL". Set
  `PYINSTALLER_RESET_ENVIRONMENT=1` and drop `_PYI_*`/`_MEIPASS2` (see
  `self_update.clean_restart_environment`, TASKS.md T-039). The restart script
  is written by the *old* version, so a fix helps only from the version after.
- A running Windows `.exe` cannot overwrite itself: the swap is done by a
  batch script after exit. `timeout` fails without a console (use `ping`),
  and `cmd /c` needs `/s` and an outer pair of quotes for paths with spaces.

## Decisions that steer the work

A summary of the decisions that shape everyday work, newest rules folded in.
The full entries, with dates, reasons and consequences, are one file each in
[decisions/](decisions/); print them in order with
`python scripts/show_log.py decisions` (add `--task T-025` for one task).

- **Templates are ordinary Word files with `{{Field}}` placeholders.** The
  engine edits the WordprocessingML in place with lxml, matches across runs,
  and never writes to the template. Improvements help users build fields in
  their own templates; the app carries **no built-in contract types or field
  schemas** (Beaux, 2026-11-17).
- **Two workflows, one engine.** The component builder (PROPOSAL-001) is in
  addition to Word templates. Component wording is Markdown, stored in the
  same per-user SQLite database as publisher profiles; users never need to
  know Markdown, and the editor keeps no second rich-text format. No Pandoc or
  python-docx at run time; markdown-it-py 3.0.0 and mdurl 0.1.2 are pinned for
  Python 3.9.
- **Fields are protected before Markdown parsing, one component at a time**
  (`markdown_fields`); never concatenate raw component source. `core.py` field
  syntax stays unchanged and fills composed documents as it fills templates.
- **A Word shell supplies layout, styles, headers and footers, not wording.**
  Run `shell_check` before using one (`SHELL-CONTRACT.md`); the shell file is
  never modified. The last usable shell is remembered per user.
- **Clause numbering is nested ordered lists**, a decimal outline (1., 1.1,
  1.1.1) continuous across the whole assembled contract; no new syntax, no
  underline (Beaux, T-025, T-033).
- **Versions are immutable and updates are never silent.** Saving a component
  adds a version (nothing if the wording is unchanged); an assembly revision
  pins exact versions plus the shell path and SHA-256; adopting newer wording
  saves a new revision after the user reviews it.
- **One database, versioned migrations.** `publisher_profiles.sqlite3`; each
  schema change is an ordered transactional migration with a verified
  `.bak-<old version>` backup; an older app must not downgrade the schema.
- **The repository is public, the app is not code-signed, and there are no
  sample templates in the repository.** Test data is invented.
- **Releases publish themselves** when `main` gets a new `APP_VERSION` with a
  `CHANGES.txt` section. Update checks need no token and run automatically at
  most once a day; the Windows app installs its own updates.
- **Main windows are not transient**, so Windows can maximize them; small
  dialogs may be.
- **The Windows executable stays at or below 30 MiB**, measured on the built
  file (TASKS.md "Size gate").

## Logs

- **Progress:** one file per entry in [progress/](progress/README.md);
  `python scripts/show_log.py progress` prints them oldest first.
- **Decisions:** one file per entry in [decisions/](decisions/README.md);
  `python scripts/show_log.py decisions`.

The 95 entries that used to be at the end of this file were moved there
unchanged on 2026-11-20 (T-053); `scripts/move_logs_out_of_claude_md.py
OLD_CLAUDE.md --check` repeats the word-for-word comparison against any
earlier copy, such as `git show da64a8c:CLAUDE.md`.
