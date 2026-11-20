---
date: 2026-11-20
task: T-021-A
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 39
---

- **2026-11-20 — SQLite schema upgrades are versioned and recoverable (T-021-A).** Keep `publisher_profiles.sqlite3` as the shared database. Its existing publisher layout is schema version 1; an existing database whose `PRAGMA user_version` is still zero is treated as that v1 layout, not as an empty database. Each later schema change is an ordered migration run inside one SQLite transaction. Before the first attempt to leave a version, create one verified snapshot named `<database filename>.bak-<old version>` with SQLite's backup API (so committed WAL data is included); never replace that backup. Keep it for recovery after success. A failed migration rolls back the schema changes and version marker. An older app may continue using the publisher table in a newer database, but must leave the newer schema version and unknown tables untouched.
