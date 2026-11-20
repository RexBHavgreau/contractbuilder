---
date: 2026-11-20
task: T-052
author: Claude
pull_request: none yet (branch claude/lucid-carson-0pjh6j)
ci_run: 247
size: release 18,125,847 bytes (17.29 MiB); component-enabled 18,125,327 bytes (17.29 MiB); headroom 13,331,953 bytes (12.71 MiB)
---

- **2026-11-20** T-052 (Claude, branch `claude/lucid-carson-0pjh6j`): split the 2,481-line `component_editor.py` into the `component_editor/` package: five pure, Tkinter-free modules, widget styling, four dialog modules, three window mixins and `window.py` (656 lines, the largest). Code moved by line range; a line-by-line comparison shows the only changes are the planned renames. `__init__.py` re-exports every name the old file defined. The existing tests pass unchanged (279 pass, 1 skipped locally under Xvfb, the skip being the private-details guard, which needs the CI secret); a new test loads the pure modules with tkinter blocked. A local PyInstaller build found all 14 submodules from `simple_app.py`'s existing import. CI run 247 passed everything. Windows sizes: release 18,125,847 bytes, component-enabled 18,125,327 bytes, 12.71 MiB headroom. The "added size" line reads -520 bytes, which means nothing (T-035). Not checked: the windows by hand on Windows, which nothing here changes visibly.
