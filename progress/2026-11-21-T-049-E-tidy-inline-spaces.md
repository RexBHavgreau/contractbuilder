---
date: 2026-11-21
task: T-049-E
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/58
ci_run: pending (update after the run on the latest commit)
size: no executable change
---

- **2026-11-21** T-049-E (Claude): `core.Renderer._tidy_spaces` removes the doubled space (or the space before `. , ; : ! ? )`) left where an inline `{{#if}}` block is dropped or replaced; spaces the author typed elsewhere are untouched. Nine new tests in `tests/test_core.py` (kept, else, dropped, punctuation, table cell, split across runs, author spaces); the whole suite passes (339). Not seen yet: the CI run.
