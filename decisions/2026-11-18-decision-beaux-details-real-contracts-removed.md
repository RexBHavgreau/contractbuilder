---
date: 2026-11-18
task: none
author: Beaux
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 23
---

- **2026-11-18 — DECISION (Beaux): details of real contracts are removed
  permanently, "even if that means rewriting history"** (TASKS.md T-016).
  Every branch and tag was rewritten with `git filter-repo`: each real detail
  replaced with an invented one, and Beaux's personal email in 90 commits
  replaced with his GitHub noreply address. Consequences: all commit ids
  changed (old ids map to new in `commit-map.txt`, handed to Beaux); every
  clone made before the rewrite is stale and must be replaced; the
  force-push, GitHub Support's purge of pull-request copies and the
  `BLOCKED_TERMS` secret are Beaux's (T-018), because this session may push
  only its own branch. A test keeps such details out from now on.
