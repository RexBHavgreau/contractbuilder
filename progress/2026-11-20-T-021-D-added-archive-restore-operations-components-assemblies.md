---
date: 2026-11-20
task: T-021-D
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/32
ci_run: 193
size: see text
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 34
---

- **2026-11-20** T-021-D (ChatGPT, [PR #32](https://github.com/RexBHavgreau/contractbuilder/pull/32)): added archive/restore operations for components and assemblies. Normal component browsing hides archived records; pinned revisions continue to resolve their original Markdown. Delete-protection triggers prevent removing components with version history or assemblies with revisions even when a caller has not enabled SQLite foreign keys. Run #193 passed 217 tests and all three platform builds. The Windows component-stack executable measured 17,976,977 bytes (17.14 MiB), leaving 13,480,303 bytes (12.86 MiB) below the 30 MiB cap.
