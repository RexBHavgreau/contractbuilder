---
date: 2026-11-18
task: T-019-A
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/19
ci_run: not recorded
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 24
---

- **2026-11-18** T-019-A (ChatGPT, [PR #19](https://github.com/RexBHavgreau/contractbuilder/pull/19)): added per-component Markdown field protection using collision-free alphanumeric placeholders, with token-tree restoration. Tests demonstrate that unprotected table pipes split cells and paired double asterisks corrupt field names, preserve conditional markers in paragraphs, lists and table cells, guard component boundaries and placeholder collisions, and prove that the existing core engine fills fields in paragraphs, list items and table cells without a core.py change. GitHub Actions test job passed all 143 tests.
