---
date: 2026-11-18
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 25
---

- **2026-11-18 — Sample generator output paths are explicit and safe.** Running `python tests/sample.py` writes `Sample Services Agreement.docx` in the current working directory; an optional positional path selects another destination. This avoids recreating the deleted `examples/` directory and makes the script safe to run from any folder.
