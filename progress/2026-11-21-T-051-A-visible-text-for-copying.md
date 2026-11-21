---
date: 2026-11-21
task: T-051-A
author: Claude
pull_request: not yet opened (branch ccr-9076da7d-zvifun)
ci_run: not yet run
size: no executable change
---

- **2026-11-21** T-051-A (Claude): added `component_editor/copy_text.py`, a
  pure function that returns the text the formatted view shows: escape
  backslashes, emphasis and heading markers are gone; list labels, hard breaks
  and tab-separated table cells are kept; fields and conditional markers stay
  exactly as written. Tests in `tests/test_copy_text.py` (13) include the
  2026-11-20 case of bold next to an escaped bracket. T-051 is now an umbrella:
  T-051-B wires Copy and Cut into the window and needs the Windows hand check.
