---
date: 2026-11-20
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 35
---

- **2026-11-20 — Extend the existing publisher database in place.** The
  existing publisher schema is version 1; `PRAGMA user_version = 0` is
  recognized as that legacy layout and stamped version 1. Later schema
  changes use ordered transactional migrations with a verified SQLite
  backup named for the old version. An older app may keep using publisher
  profiles in a newer database, but must not downgrade the version or alter
  unknown tables. This avoids a second database and preserves existing data.
