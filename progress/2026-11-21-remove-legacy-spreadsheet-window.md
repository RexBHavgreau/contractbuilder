---
date: 2026-11-21
task: T-036
author: Claude
pull_request: not yet opened (branch remove-legacy-window)
ci_run: not yet run
size: smaller executable expected (openpyxl and the legacy window removed); the CI size numbers confirm it
---

- **2026-11-21** Removed the legacy window and its spreadsheet code (Claude, for
  Beaux's decision recorded in decisions/). Deleted `advanced_app.py`; removed
  the batch, sheet, answers, settings and template-listing functions and their
  three tests from `core.py` and `tests/test_core.py`; dropped openpyxl from
  `requirements.txt` and the CI install; updated the README, BUILD-NOTES, CLAUDE.md
  and the module-list script. Tests: 539 passed, 1 skipped. T-036 stays open for the
  remote branch clean-up, which is done by hand.
