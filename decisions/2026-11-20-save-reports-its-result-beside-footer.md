---
date: 2026-11-20
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 41
---

- **2026-11-20 — Save reports its result beside the footer, and saving with no changes adds no version.** A success line clears after six seconds or as soon as the draft changes; a failure stays until Dismiss is clicked. `save_feedback_text` builds the words, so the cases are tested without a window. Why: the old grey status line was easy to miss, and Save made a duplicate version when nothing had changed. Consequence: a user who wants a new version of identical wording must change something first.
