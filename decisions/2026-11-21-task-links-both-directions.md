---
date: 2026-11-21
task: none
author: Claude
pull_request: not yet opened (branch task-links)
---

- **2026-11-21 — Each open task shows what it needs and what needs it, and the files it shares with other open tasks; a script writes these and the tests check them.** Beaux asked for both dependency directions and shared-file lists so an agent does not have to read several task files to find one that fits. The lists are written by `scripts/task_links.py --write` rather than by hand, because a hand-kept list goes stale as tasks change; `--check` in the test suite fails until the files are up to date. Interpretation: "Needed by" lists the direct dependents only (one level), the first two by number, then "(and N more)"; a second level is not shown. Umbrella tasks are left out of the shared-file lists because their Touches is the union of their subtasks. Consequence: a task file changes whenever a task it touches or depends on changes, so claims branched before this change must run `--write` when they are merged.
