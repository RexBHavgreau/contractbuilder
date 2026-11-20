---
date: 2026-11-20
task: T-053
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/47
---

- **2026-11-20 — Progress and decision entries are one file each; CLAUDE.md holds only standing rules.** Every pull request used to append to the end of CLAUDE.md, so any two collided. Entries now live in `progress/` and `decisions/`, named `YYYY-MM-DD-T-NNN-short-title.md`, each with a header (date, task, author, pull request; progress entries also CI run and size numbers). The 95 existing entries were moved unchanged by `scripts/move_logs_out_of_claude_md.py`, which also proves the move word for word. CLAUDE.md keeps a short summary, "Decisions that steer the work", edited only by a deliberate rules change. `scripts/show_log.py` prints either log in order, and `tests/test_project_log.py` fails on a missing header field, so the size gate stays visible. Within one day, moved entries keep their old order through a `sequence` field and new entries sort after them by file name. A task is claimed by its own one-line pull request, merged before work starts. Consequence: reading the history is `python scripts/show_log.py progress` rather than scrolling CLAUDE.md.
