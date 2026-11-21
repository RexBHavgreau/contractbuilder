---
date: 2026-11-21
task: T-048-C
author: Claude
pull_request: not yet opened (local branch t-048-c-recent-last-used)
ci_run: not yet run
size: no executable change until the branch is merged; the new module is small and pure
---

- **2026-11-21** T-048-C (Claude): the start screen shows a Recent list under the
  three choices: Word files and assemblies used most recently, one click to reopen,
  up to five items. A file that has moved shows "file not found" and an
  assembly with no saved revision shows as such; both can be removed from the list.
  The list is recorded in the per-user settings file under `recent`, and every
  other key there (including the update token) is kept unchanged. Pure rules in
  `recent_items.py`; tests in `tests/test_recent_items.py` and
  `tests/test_start_screen.py`. The guide has a "Starting a contract" section.
  Also fixed two tests that were already failing on `main` after PR #81 and #82:
  the existing-assembly test waited on a modal list, and the picker's Enter test
  sent the key to an unfocused, withdrawn window.
