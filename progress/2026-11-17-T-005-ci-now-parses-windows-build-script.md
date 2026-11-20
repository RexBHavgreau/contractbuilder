---
date: 2026-11-17
task: T-005
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/7
ci_run: not recorded
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 6
---

- **2026-11-17** T-005 (ChatGPT, [PR #7](https://github.com/RexBHavgreau/contractbuilder/pull/7)): CI now parses the Windows build script with PowerShell 5.1 and rejects invalid batch-file line endings. A deliberately broken PowerShell copy failed the new step before Python setup; restoring it produced a green Windows build.
