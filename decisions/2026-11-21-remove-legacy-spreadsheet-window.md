---
date: 2026-11-21
task: T-036
author: Claude (for Beaux's decision)
pull_request: not yet opened (branch remove-legacy-window)
---

- **2026-11-21 — The legacy window (`advanced_app.py`) and its spreadsheet code are removed.** Beaux decided the legacy window is no longer relevant, given how the application has developed. The removed code was the batch spreadsheet workflow, which used openpyxl (a Python library for reading and writing Excel .xlsx files), and the saved-answer and template-listing helpers only that window used. Removed: `advanced_app.py`, the spreadsheet, answers, settings and batch functions in `core.py`, their tests, and the openpyxl requirement and CI install. Kept: the template engine and the functions the live app uses. Consequence: the saved-answer feature of the old window is gone; the component builder and publisher profiles replace it. Expect a smaller Windows executable; confirm the size numbers in CI.
