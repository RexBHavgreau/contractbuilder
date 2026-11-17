# Word Template Filler

A small desktop application for filling placeholders in Word documents. Choose a
`.docx` or `.dotx` template, and the application discovers its unique fields
and builds a form. Fill in the form and save a completed `.docx` copy. The
original template is never changed.

The main application is deliberately focused on that single-document workflow.
It can fill repeated fields throughout the document while preserving Word
formatting, numbering, tables, headers, footers, footnotes, and endnotes.

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

To publish a versioned release, update `APP_VERSION` in `version.py`, commit
the change, and push a matching tag such as `v0.1.0`. The tag must match the
version in `version.py`. GitHub Actions then builds the applications and
attaches them to a GitHub Release.

The application checks for updates at startup and through **Help → Check for
updates**. When a newer release is found, it opens the GitHub release page so
the user can download the appropriate build. Updates are not installed
silently.

### Private-repository update checks

This repository is private. A packaged application cannot contain a GitHub
credential safely. To check private releases, set the
`CONTRACTBUILDER_GITHUB_TOKEN` environment variable to a GitHub fine-grained
personal access token with read-only **Contents** access to this repository.
Do not put the token in source code or distribute it with the application. If
the repository is made public, the update checker works without a token.

## Project files

| File | Purpose |
| --- | --- |
| `simple_app.py` | Focused desktop interface packaged for users |
| `core.py` | DOCX template scanning, validation, and rendering engine |
| `update_checker.py` | GitHub Releases version checker |
| `version.py` | App version and repository settings |
| `USER-GUIDE.txt` | Instructions shown from the Help menu and bundled with the app |
| `app.py` | Default launcher for the focused application |
| `advanced_app.py` | Earlier contract-oriented interface, retained separately and not packaged |
| `.github/workflows/build.yml` | Tests, Windows/macOS builds, and tagged releases |
| `tests/` | Automated tests; run with `python -m pytest tests` |
