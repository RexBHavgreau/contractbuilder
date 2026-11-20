---
date: 2026-11-20
task: T-040, T-044, T-050
author: Claude
pull_request: not recorded
ci_run: not recorded
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 51
---

- **2026-11-20** T-040, T-044 and T-050 (Claude, branch `ccr-9076da7d-zvifun`, not yet a pull request): the Components and Build assembly windows and the larger dialogs are no longer transient, so Windows can maximize them, and the editor layout fits a 1920-pixel screen. Save shows a clear result beside the footer, an Unsaved changes mark, a Version column, and no duplicate version when nothing changed. Preview markers show as plain words with a key (`component_preview.py`). Fixed a bug on `main` since commit `7b532ad`: saving an existing component raised `NameError` in `_load_component` after the database write. Tests: 256 pass and 1 is skipped under Xvfb (new: `save_feedback_text` tests and 6 preview tests). Checked headlessly under Xvfb, not on Windows. Size gate: no new module or dependency, so no new code is measured here; the CI size numbers are not yet read, and the task is not done until they are.
