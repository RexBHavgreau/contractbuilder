---
date: 2026-11-20
task: none
author: Claude
pull_request: not recorded
ci_run: not recorded
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 46
---

- **2026-11-20** Update restart error (Claude): Beaux saw the same message updating 0.3.1 to 0.4.0. Reproduced a matching failure with a test one-file app under PyInstaller 6.22.3: a copy started from the running app with its inherited environment fails to find the old temporary folder; with `PYINSTALLER_RESET_ENVIRONMENT=1` it starts. Added `self_update.clean_restart_environment` and tests; needs release 0.4.1 (TASKS.md T-039). Confirmed the same day against Beaux's screenshot: "Failed to load Python DLL ... \_MEI...\python311.dll ... The specified module could not be found".
