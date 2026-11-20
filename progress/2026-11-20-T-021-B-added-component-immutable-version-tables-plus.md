---
date: 2026-11-20
task: T-021-B
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/30
ci_run: 183
size: see text
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 36
---

- **2026-11-20** T-021-B (ChatGPT, [PR #30](https://github.com/RexBHavgreau/contractbuilder/pull/30)): added the component and immutable-version tables plus `library.py`, a Tkinter-free, standard-library storage API. Component creation creates version 1; later saves allocate the next number in a write-serialized transaction. SQLite triggers prevent rewriting or deleting saved versions. Tags are stored as a JSON array to preserve arbitrary user-defined labels; categories remain unrestricted text. CI run #183 passed 214 tests and all three platform builds; the Windows component-stack build measured 17,972,861 bytes (17.14 MiB), with 13,484,419 bytes (12.86 MiB) below the 30 MiB cap.
