# CLAUDE.md — Word Template Filler (formerly TMAI Contract Builder)

This file is the project's memory. Read it before changing anything. When
you finish a piece of work, add to the **Progress log**, and add to the
**Decision log** for any choice a later person would otherwise have to
rediscover. Open work lives in [TASKS.md](TASKS.md).

## What it is

A desktop app (Windows first, macOS too) for a TMAI department that makes
contracts and similar documents from Word templates. A template is an
ordinary `.docx`/`.dotx`; the parts that change are written as
`{{Field Name}}`, optionally with a format (`{{Fee | money-words}}`,
`{{Start Date | date-formal}}`) or around optional wording
(`{{#if Field}} … {{/if}}`). The app finds the fields, shows a form, and
writes a new filled-in `.docx`. **The template is never changed.**

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
| `publisher_profiles.py` | Local SQLite store of publisher details, and mapping onto template fields. |
| `update_checker.py` | Asks GitHub Releases for the latest version and its attached files. |
| `self_update.py` | Downloads, verifies and swaps in a new Windows `.exe`; stores the per-user update token. |
| `version.py` | `APP_NAME`, `APP_VERSION`, `GITHUB_REPOSITORY`. The single source of the version. |
| `advanced_app.py` | The earlier contract-builder window (batch spreadsheets, template maker). Kept, **not packaged** — see TASKS.md. |
| `build-windows.bat` → `build-windows.ps1` | Local Windows build. |
| `build-mac.command` | Local macOS build. |
| `.github/workflows/build.yml` | Tests, Windows/macOS builds, releases. |
| `tests/` | `python -m pytest tests` |
| `USER-GUIDE.txt` | Shown from Help and bundled into the app. |
| `BUILD-NOTES.txt` | How to build and release, for whoever maintains it. |

## Working on it

- Python 3.9+. `pip install lxml openpyxl pytest python-docx`, then
  `python -m pytest tests`. Every change keeps the suite green and adds
  tests for new behaviour.
- To see the window on a headless Linux box: install `python3-tk`, run under
  `xvfb-run`, drive it from a script, screenshot with ImageMagick `import`.
  Stub `messagebox`/`filedialog` so nothing blocks.
- Releases: raise `APP_VERSION` in `version.py` and merge to `main`. CI then
  tags `vX.Y.Z` and publishes the release with
  `Word-Template-Filler-windows-x64.exe` attached. The updater looks for
  exactly that file name; do not rename it.
- `build-windows.bat` must keep CRLF line endings. The Windows CI job
  checks the file's bytes for CRLF (and rejects mixed endings), and parses
  `build-windows.ps1` with Windows PowerShell 5.1 before building. This
  catches syntax and line-ending slips before PyInstaller runs.
- Never put a token, password or key in the code, a template, the build or
  the repository. The update token is entered per user in the app.
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
- **The repository is private**: GitHub answers 404 to unsigned requests for
  its releases, so the updater needs a token (or the repo made public).
- A release tagged on a commit whose `version.py` disagrees fails CI and has
  no files (v0.2.0). Hence release-on-version-bump.
- Word splits text into many runs (one MOU had 917 runs in 52 paragraphs;
  "December 1, 2034" was three runs). The engine matches across runs; keep
  it that way. Real contracts also arrive with tracked changes, comments,
  curly quotes, letter-spacing from PDF conversion, and tab-aligned
  signature blocks.
- A running Windows `.exe` cannot overwrite itself: the swap is done by a
  batch script after exit. `timeout` fails without a console (use `ping`),
  and `cmd /c` needs `/s` and an outer pair of quotes for paths with spaces.

## Decision log

Newest last. Each entry: date, decision, why, consequences.

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
  `4becc60` if any of it is wanted later.
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
  settings. *Open question for Beaux: make the repository (or a releases-only
  copy) public so colleagues need no token — TASKS.md T-001.*
- **2026-11-17 — Releases publish themselves when `main` gets a new
  `APP_VERSION`.** Removes the hand-made tag that went wrong for v0.2.0.

## Progress log

Newest last.

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
