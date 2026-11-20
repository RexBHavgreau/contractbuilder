---
date: 2026-11-20
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 42
---

- **2026-11-20 — Main windows are not transient; dialogs stay modal but are resizable.** On Windows a transient window has no maximize button. The Components and Build assembly windows, plus the larger dialogs (import review, version history, review updates, saved assemblies, table editor), now use `lift()` instead. The small field-insert dialog stays transient and fixed. Consequence: none of these is checked on Windows yet (T-040 hand check).
