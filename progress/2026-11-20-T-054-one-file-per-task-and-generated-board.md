---
date: 2026-11-20
task: T-054
author: Claude
pull_request: pending (pull request not yet opened; fill in before merging)
ci_run: pending (fill in with the run on the last code commit)
size: no executable change (scripts, tests and a workflow only)
---

- **2026-11-20** T-054 (Claude, pull request pending): split `TASKS.md` into one file per task and subtask under `tasks/` (40 open, 70 in `tasks/done/`), with group notes in `tasks/notes/`, and added `scripts/task_files.py` and `scripts/board.py` (the board, `--next`, `--check`), `tests/test_board.py` (10 tests, including a check of every real task file) and the workflow `.github/workflows/board.yml`. `TASKS.md` now holds only the rules. A one-off script proved conservation: every non-blank line of the old task sections is in exactly one new file (2,186 of 2,188; the two lines left out are the headings "Open tasks" and "Done tasks"). The files keep the old bullet format, so the board reads them without a rewrite. The workflow publishes the board as the run summary and an artifact and commits `BOARD.md` only when the repository variable `BOARD_BOT_COMMIT` is `true`; Beaux has not decided that yet. Not checked: the workflow (it runs only on `main`) and the CI run of the pull request.
