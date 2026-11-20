---
date: 2026-11-20
task: T-055
author: Claude
pull_request: not yet opened (branch ccr-9076da7d-zvifun)
ci_run: not yet run
size: no executable change
---

- **2026-11-20** T-055 (Claude): every open task in TASKS.md now has a
  **Touches** line naming the files it will change (umbrellas list their
  subtasks' files). `scripts/overlaps.py` lists pairs of open tasks that share
  a file, and exits 1 only when two claimed tasks share one; the test job runs
  it as a warning step. The migration-numbering rule is in TASKS.md's rules
  and the Touches rule is pointed to from CLAUDE.md. Tests: `tests/test_overlaps.py`
  (10 tests, invented task text, plus a check that every open task has Touches).
  Today the checker flags T-041 and T-045 as claimed together, both on
  `component_editor.py`; PR #44 already landed both, so their claims need closing
  by whoever holds them. Not opened as a pull request yet.
