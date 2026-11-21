---
date: 2026-11-21
task: none
author: Claude
pull_request: not yet opened (branch task-links)
ci_run: not yet run
size: no executable change
---

- **2026-11-21** Task files show dependencies in both directions and shared files
  (Claude). `scripts/task_links.py` writes **Needed by** (the direct dependents of
  each open task, first two by number, then "(and N more)") and "(also …)" after
  each file in Touches (the other open tasks that change it). Twelve open task
  files were updated. The tests run `--check`, and TASKS.md, tasks/README.md and
  CLAUDE.md say how to add a task now (run `--write`). Ten tests cover the rules.
  Claims in progress (T-031, T-051-B) are not on `main` yet; when they merge, run
  `python scripts/task_links.py --write`.
