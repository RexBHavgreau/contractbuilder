---
date: 2026-11-22
task: T-049-D
author: Claude
pull_request: not yet opened (branch any-task-4)
ci_run: not yet run
size: no executable change
---

- **2026-11-22** T-049-D (Claude): the user guide has a section "Building choice
  and singular or plural wording with the buttons": the Choice wording steps, the
  Singular/plural word steps, invented publisher-type and works examples, and the
  rule that a condition's value must be one of the field's choices. Test in
  `tests/test_user_guide.py`.
  Also fixed a red test on `main`: `test_a_field_without_help_looks_as_before…`
  expected a plain field without help to take two rows. T-049-B made it one row
  (no blank row under it), without updating the test. The test now records the
  one-row rule; the layout change itself came from T-049-B.
  Also refreshed the links in T-049-C (`task_links.py --write`) because T-049-B
  closed. T-049-C is claimed, so its branch may need the same refresh when it merges.
