---
date: 2026-11-19
task: T-023-B
author: Claude
pull_request: not recorded
ci_run: not recorded
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 27
---

- **2026-11-19** T-023-B (Claude): added `shell_selection.py`, which checks a picked shell with the T-026 checker, turns the findings into plain-English lines, and remembers the last shell that can be used in a per-user settings file. Checker messages now show Word's visible style names instead of style IDs. Added `tests/test_shell_selection.py` (17 tests, invented shells only). The file picker itself is not built yet; it belongs to the component window. Full suite: 167 passed, 1 skipped; `test_updates.py::test_successful_update_check_time_limits_only_automatic_checks` fails only because this sandbox's Python has no `tkinter` (it also fails on the untouched branch).
