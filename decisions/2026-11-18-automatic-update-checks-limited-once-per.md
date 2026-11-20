---
date: 2026-11-18
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 26
---

- **2026-11-18 — Automatic update checks are limited to once per day per user.**
  The app records the time of the last successful check in the existing
  per-user update settings file, without replacing the optional token.
  Successful manual checks count too; a manual check always bypasses the
  throttle. Failed checks do not postpone the next automatic attempt.
