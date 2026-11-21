---
date: 2026-11-21
task: T-058-A
author: Claude
pull_request: not yet opened (branch t-058-a-help-text)
ci_run: not yet run
size: no executable change in the form logic; the creator's label and grid rows changed
---

- **2026-11-21** T-058-A (Claude): the field creator's "Description (optional)"
  box is now labelled **Help text (optional)** and has an example underneath. It
  stores the same description that the fill-in forms show under the field name,
  so no data changes. Rows below it moved down one, and the footer buttons moved
  with them. A window test in `tests/test_component_field_picker.py` checks the
  label, that a saved help text is shown on editing, and that editing it saves.
  The fill-in forms already showed help text (template and assembly), and matching
  was already tested; those boxes are ticked on the existing tests.
- **Correction:** `progress/2026-11-21-close-T-048-and-T-049-A.md` (on `main`) and PR #93
  said the ordinary template form never passes help text to its fields. That was
  wrong: `simple_app.py` passes it. Only T-058-A's creator box was missing.
