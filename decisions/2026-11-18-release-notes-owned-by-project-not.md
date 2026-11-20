---
date: 2026-11-18
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 27
---

- **2026-11-18 — Release notes are owned by the project, not generated from PR titles.**
  `CHANGES.txt` uses one `## X.Y.Z` section per release, newest first.
  CI verifies the running `APP_VERSION` has a non-empty section and extracts
  only that section for the GitHub release body. The updater displays up to
  15 lines of that body.
