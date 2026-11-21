---
date: 2026-11-21
task: T-041, T-045, T-046-A, T-046-B, T-047, T-051-A, T-060
author: Claude
pull_request: not yet opened (branch ccr-9076da7d-zvifun)
ci_run: not yet run
size: no executable change
---

- **2026-11-21** Closed tasks that were finished on `main` but still marked
  open or claimed (Claude): T-041 (toolbar wrap), T-045 (formatting toggles)
  and T-047 (window tests under Xvfb) landed with PR #44; T-046-A (field
  matching) with PRs #56 and #71; T-046-B (fill from the profile) with PR #75;
  T-051-A (visible text for copying) is on `main`, and its Copy and Cut
  wiring stays with T-051-B; the T-060 umbrella closes because both subtasks
  are done. Each was checked against the code and tests on `main`. The
  Windows hand checks are not ticked: they are now items in UT-003 (T-041,
  T-045, T-046-B), and T-060's real-Word check is in UT-001. Not closed:
  T-048-B, which opens the builder's Open saved list rather than going straight
  to a revision's field form.
