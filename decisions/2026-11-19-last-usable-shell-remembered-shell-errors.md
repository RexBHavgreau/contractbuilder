---
date: 2026-11-19
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 30
---

- **2026-11-19 — The last usable shell is remembered; a shell with errors never is.** `shell_selection.choose_shell` runs the T-026 checker on the file the user picked. A shell with warnings is remembered, because the user has read them and may continue; a shell with errors is reported and does not replace the remembered one. The path is stored in `shell-settings.json` in the per-user app folder, beside the update settings, and a missing, moved or damaged file means nothing is remembered rather than an error. If the settings cannot be written, the shell still works for this session and the user is told it was not remembered. Consequence: the picker dialog belongs to the component window (T-023-A/T-022-A), which calls this function; it is not in `simple_app.py` yet. Checker messages now name the Word style as users see it ("Heading 1", "Normal Table") rather than its internal ID; the IDs remain in finding codes and `style_fallbacks`.
