---
date: 2026-11-18
task: T-013, T-016
author: Claude
pull_request: not recorded
ci_run: not recorded
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 18
---

- **2026-11-18** History rewrite (Claude, T-013 and T-016): searched all ten
  branches, three tags, every commit message and the inside of every Word and
  Excel file for 51 details recorded from the memoranda; 22 were present.
  Replaced them, and the personal email in 90 commits, across all history;
  verified none remain, `main` changed only in the replaced words, and all
  tests pass. Added `tests/test_no_private_details.py` and the CI secret it
  reads. Pushing it was refused to this session (it may push only its own
  branch), so it is prepared for Beaux as TASKS.md T-018.
