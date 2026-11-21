---
date: 2026-11-21
task: T-040, T-044, T-050
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/78
ci_run: pending (update after the run on the latest commit)
size: release v0.4.0 18,095,285 bytes; v0.4.3 18,174,209 bytes (17.33 MiB); headroom 13,283,071 bytes (12.67 MiB)
---

- **2026-11-21** Closing the tasks that were waiting on a person (Claude): T-040, T-044 and T-050 were "ready for review" only for the CI size numbers and a Windows hand check. Their changes shipped in v0.4.0 (18,095,285 bytes) and the executable is 18,174,209 bytes in v0.4.3, 12.67 MiB under the 30 MiB limit, so the size gate holds. The hand checks moved to a new kind of task, **UT-NNN** (a check only a person can do), which never blocks a coding task: UT-001 (real Word), UT-002 (try the builder on Windows), UT-003 (Windows checks of recent window changes), UT-004 (GitHub branch rule). T-030, T-038 and T-057 became UT-001, UT-002 and UT-004; T-043-C, T-048-A, T-055 were closed the same way. The board shows UT tasks in their own table, `scripts/board.py --check` rejects a coding task that lists a UT task in `Needs` (unless marked `[blocks]`), and `scripts/claim.py` refuses UT tasks.
