---
date: 2026-11-20
task: T-023-A, T-023-D, T-024-A
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/40
ci_run: 223
size: see text
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 41
---

- **2026-11-20** T-023-A through T-023-D and T-024-A (ChatGPT, [PR #40](https://github.com/RexBHavgreau/contractbuilder/pull/40)): completed the component library browser with category/tag filters, wording search, archived-item visibility and read-only version history; added shell selection using the existing checker and per-user last-shell setting; built the ordered include/omit assembly editor with duplicate confirmation and a component-by-component preview; and saved/reopened assembly revisions pinned to exact component versions, shell path and SHA-256. The preview parses each component separately, preventing fields from forming across component boundaries. No runtime dependency was added. CI run #223 passed 238 tests and built Windows x64, macOS Intel and macOS Apple Silicon. The Windows release executable measured 18,055,954 bytes (17.22 MiB); the component-enabled build measured 18,077,987 bytes (17.24 MiB), an increase of 22,033 bytes (0.02 MiB), leaving 13,379,293 bytes (12.76 MiB) below the 30 MiB cap.
