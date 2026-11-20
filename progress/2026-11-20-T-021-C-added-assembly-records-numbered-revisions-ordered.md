---
date: 2026-11-20
task: T-021-C
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/31
ci_run: 189
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 35
---

- **2026-11-20** T-021-C (ChatGPT, [PR #31](https://github.com/RexBHavgreau/contractbuilder/pull/31)): added assembly records, numbered revisions and ordered membership rows that pin exact component-version IDs. Each revision stores its shell path and validated SHA-256; it is finalized once, only after at least one included component is present, and SQLite triggers prevent later membership or shell changes. Run #189 passed 215 tests and all three platform builds.
