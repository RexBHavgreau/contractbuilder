# Progress log

One file per finished piece of work, so that two pull requests never edit the
same file to record their progress (TASKS.md T-053). Read them in order with:

    python scripts/show_log.py progress

**To add an entry:** create `progress/YYYY-MM-DD-T-NNN-short-title.md`
(subtask: `T-NNN-X`; lower-case words joined by hyphens) in the pull request
that does the work. Do not edit `CLAUDE.md` to record progress. Every field
below is required; `tests/test_project_log.py` fails if one is missing.

```
---
date: 2026-11-21
task: T-052
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/NN
ci_run: 240
size: release 18,095,285 bytes; component-enabled 18,096,000 bytes; headroom 12.74 MiB
---

- **2026-11-21** T-052 (Claude, [PR #NN](https://github.com/RexBHavgreau/contractbuilder/pull/NN)):
  what was done, what was checked, what is still open.
```

- `size` is the size gate (TASKS.md): both CI sizes and the headroom, or
  `no executable change` for a change that adds no code to the app.
- `ci_run` is the run on the pull request's latest commit. If you write the
  entry before the run has finished, update the field before the pull request
  is merged.
- `not recorded` is allowed only in entries moved from the old CLAUDE.md.

Files sort by date, then by name. The entries moved from CLAUDE.md carry
`source` and `sequence` fields that keep their original order.
