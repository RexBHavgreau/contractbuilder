---
date: 2026-11-21
task: T-062
author: Claude
pull_request: not yet opened (branch any-task-next)
ci_run: not yet run
size: no executable change beyond guide text
---

- **2026-11-21** T-062 (Claude): the user guide has a section "Asking once for a
  number" between FORMATS and CHOOSING THE RIGHT KIND OF FIELD. It shows the
  number and number-words formats, how to turn two fields into one by editing a
  component or a Word file, that saved assemblies keep the old version until
  Review updates, and that words without digits are not available yet. The
  engine behaviour was checked: `{{Copies | number}}` and `{{Copies | number-words}}`
  render as `7` and `seven (7)` from one answer. The Help menu reaches the section
  through the template help window. Test: `tests/test_user_guide.py`.
