---
date: 2026-11-19
task: T-019-H
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 33
---

- **2026-11-19 — T-019-H measured Windows package size with the component
stack included.** GitHub Actions run #166 built the same `simple_app.py`
entry point twice with the same one-file/windowed PyInstaller configuration.
The ordinary build was 17,801,283 bytes (16.98 MiB). The comparison build
explicitly included `md_parse`, `markdown_fields`, `shell_check`,
`md_to_word` and `docx_compose` and was 17,962,926 bytes (17.13 MiB).
The component-builder stack therefore adds 161,643 bytes (0.15 MiB).
The expanded build leaves 13,494,354 bytes (12.87 MiB) below the 30 MiB
limit. This is not close to the 3 MiB warning margin, so there is no
immediate packaging constraint. The Windows CI workflow retains this
comparison and checks the expanded build against the size limit on future
runs.
