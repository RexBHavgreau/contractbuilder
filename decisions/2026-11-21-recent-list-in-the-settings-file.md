---
date: 2026-11-21
task: T-048-C
author: Claude
pull_request: not yet opened (local branch t-048-c-recent-last-used)
---

- **2026-11-21 — The recent list lives in the per-user settings file, under its own key, and recording never blocks opening a document.** The task asks for the existing settings file, so the list is stored there beside the update token, which is read back and written unchanged. Recording is best effort: an unreadable file means an empty list, and a file that cannot be written is ignored. Why: a recent list is a convenience and must never stop a contract from opening. Consequence: the list is per computer and per user, and it holds only paths and assembly ids, never wording.
