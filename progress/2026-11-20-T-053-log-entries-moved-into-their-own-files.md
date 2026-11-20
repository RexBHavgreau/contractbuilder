---
date: 2026-11-20
task: T-053
author: Claude
pull_request: none yet (branch claude/lucid-carson-0pjh6j)
ci_run: 247
size: no executable change (run 247 on this branch: release 18,125,847 bytes (17.29 MiB); component-enabled 18,125,327 bytes (17.29 MiB); headroom 13,331,953 bytes (12.71 MiB))
---

- **2026-11-20** T-053 (Claude, branch `claude/lucid-carson-0pjh6j`): moved the 43 decision and 52 progress entries out of CLAUDE.md into one file each under `decisions/` and `progress/`, unchanged; `scripts/move_logs_out_of_claude_md.py --check` compared them word for word with CLAUDE.md at `da64a8c` and found nothing lost. CLAUDE.md now holds the standing rules and a short "Decisions that steer the work"; `scripts/show_log.py progress|decisions` prints the logs in order; `tests/test_project_log.py` (17 tests) fails when an entry lacks its date, task, author, pull request, CI run or size field. TASKS.md says to add a file instead of editing CLAUDE.md, and to claim a task with its own one-line pull request. CI run 247 (manual start on the branch, so no pull request yet) passed the tests, the window tests, the Windows build with its size check and both macOS builds. Still open: the pull request and merge; T-057 (GitHub enforcing up-to-date branches) is Beaux's.
