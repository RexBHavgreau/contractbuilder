---
date: 2026-11-18
task: T-018
author: not recorded
pull_request: not recorded
ci_run: 67
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 19
---

- **2026-11-18** Beaux pushed the cleaned history and sent GitHub Support the
  purge request (T-018). Verified by Claude: every branch and tag on GitHub
  matches the cleaned copy; a fresh clone has none of the removed details and
  no personal email; the `BLOCKED_TERMS` secret reaches CI and the guard
  passes (run 67); no forks. Still open: the old commits remain fetchable
  through pull requests #1 to #9 until GitHub Support purges them.
