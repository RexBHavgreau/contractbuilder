# Word Template Filler

A small desktop application for filling placeholders in Word documents. Choose a
`.docx` or `.dotx` template, and the application discovers its unique fields
and builds a form. Fill in the form and save a completed `.docx` copy. The
original template is never changed.

The main application is deliberately focused on that single-document workflow.
It can fill repeated fields throughout the document while preserving Word
formatting, numbering, tables, headers, footers, footnotes, and endnotes.

Publisher profiles can be saved locally in SQLite and loaded into matching
template fields, so organization and contact details can be reused across
contracts. The database is stored in the user's application-data directory,
separately from the application files.

## Run from source

Python 3.9 or later is required.

```bash
python -m pip install lxml
python simple_app.py
```

`app.py` is also a launcher for the focused application. The earlier
contract-oriented interface is retained in `advanced_app.py` for reference,
but it is not included in the packaged application.

## Build and releases

On Windows, double-click `build-windows.bat` to build locally. The script
selects a real installed Python interpreter and skips Microsoft Store
execution aliases, which PyInstaller cannot reliably use.

GitHub Actions runs the test suite and builds the desktop application whenever
changes are pushed to `main`. It produces Windows x64, macOS Intel, and macOS
Apple Silicon builds as workflow artifacts.

To publish a release, raise `APP_VERSION` in `version.py` and merge the change
into `main`. When `main` has a version with no matching `v` tag yet, GitHub
Actions tests, builds, tags the commit (for example `v0.3.0`) and publishes a
GitHub Release with the applications attached. Pushing a matching tag by hand
still works; a tag that disagrees with `version.py` fails the build.

The application checks for updates at startup and through **Help → Check for
updates**. On Windows it offers to download the new `.exe`, checks it against
GitHub's published size and SHA-256 digest, and swaps it in with a small
helper script once the app has closed, then reopens (`self_update.py`).
Nothing is installed without the user choosing to. On macOS, and for a release
with no Windows file, it opens the release page instead.

Before opening a downloaded copy for the first time, read the **FIRST RUN**
section in `USER-GUIDE.txt` for the Windows SmartScreen and macOS Gatekeeper
prompts.

### Private-repository update checks

This repository is private. A packaged application cannot contain a GitHub
credential safely. To check private releases, set the
`CONTRACTBUILDER_GITHUB_TOKEN` environment variable, or paste it into **Help →
Update settings** (saved per user, beside the publisher profiles), using a GitHub
fine-grained personal access token with read-only **Contents** access to this
repository.
Do not put the token in source code or distribute it with the application. If
the repository is made public, the update checker works without a token.

## Project files

| File | Purpose |
| --- | --- |
| `simple_app.py` | Focused desktop interface packaged for users |
| `core.py` | DOCX template scanning, validation, and rendering engine |
| `publisher_profiles.py` | Local SQLite publisher-profile storage and template field mapping |
| `update_checker.py` | GitHub Releases version checker |
| `self_update.py` | Downloads, verifies and swaps in a new Windows build |
| `CLAUDE.md` | Project history, conventions and decision log, for people and AI agents |
| `TASKS.md` | Open tasks, sized so they can be picked up by any agent |
| `version.py` | App version and repository settings |
| `USER-GUIDE.txt` | Instructions shown from the Help menu and bundled with the app |
| `app.py` | Default launcher for the focused application |
| `advanced_app.py` | Earlier contract-oriented interface, retained separately and not packaged |
| `.github/workflows/build.yml` | Tests, Windows/macOS builds, and tagged releases |
| `tests/` | Automated tests; run with `python -m pytest tests` |
