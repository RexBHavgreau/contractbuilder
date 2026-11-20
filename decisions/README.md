# Decision log

One file per decision: a choice a later person would otherwise have to
rediscover (TASKS.md T-053). Read them in order with:

    python scripts/show_log.py decisions
    python scripts/show_log.py decisions --task T-025

**To add an entry:** create `decisions/YYYY-MM-DD-T-NNN-short-title.md` in the
pull request that makes the choice. Say the decision, why, and the
consequences. Do not edit `CLAUDE.md` for it; if the decision changes how
everyday work is done, the summary in CLAUDE.md "Decisions that steer the
work" is updated by a separate, deliberate change.

```
---
date: 2026-11-21
task: T-052
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/NN
---

- **2026-11-21 — The decision in one line.** Why. Consequences.
```

Every field is required (`task: none` if no task); `not recorded` is allowed
only in entries moved from the old CLAUDE.md.
