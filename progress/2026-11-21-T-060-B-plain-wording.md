---
date: 2026-11-21
task: T-060-B
author: Claude
pull_request: pending (update when the PR is opened)
ci_run: pending (update after the run on the latest commit)
size: pending; adds layout_file_dialog.py (a small Tk dialog) and message text, no dependency; confirm release and component-enabled sizes from the CI summary
---

- **2026-11-21** T-060-B (Claude): choosing a page layout file no longer asks a Yes/No question about missing styles. `shell_selection.choose_shell` uses `check_shell(..., supply_missing=True)`, so a file that only lacks styles or numbering gets one calm line ("This file is missing the List Number style. The app will add it to your new document. Your file is not changed.") and is taken. Errors (not a Word document, no document body, no page settings) say what is wrong and what to do, with no mention of shells, outlines or fallbacks. When a warning remains (no page size or margins), a new dialog (`layout_file_dialog.py`) offers **Use this file** and **Choose another**, with Escape meaning Choose another. SHELL-CONTRACT.md is rewritten from "required styles" to "styles the app adds if missing", and the guide's page layout section says the same. 392 tests pass; older tests that asserted the old wording were updated, and new ones cover the calm line, the real-warning path, the dialog buttons and the window flow. Open: Windows hand check of the dialog; CI size numbers.
