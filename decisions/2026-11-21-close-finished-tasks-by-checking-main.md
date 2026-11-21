---
date: 2026-11-21
task: none
author: Claude
pull_request: not yet opened (branch ccr-9076da7d-zvifun)
---

- **2026-11-21 — A task is closed when its code and tests are on `main`; a Windows check that code cannot make becomes a UT task.** Several tasks had merged work but stayed claimed or open, so the board and the overlap check reported claims that were no longer true. The rule now is to check each item against `main` before closing, and to move the human hand check into a UT file (UT-003 for the window tasks) rather than leave the task open. Consequence: a task can be done while its Windows check is still pending; that check is tracked in the UT file, which does not block coding work.
