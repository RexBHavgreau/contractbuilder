---
date: 2026-11-22
task: T-064-A
author: Claude
pull_request: not yet opened (branch any-task-3)
ci_run: not yet run
size: no executable change beyond the importer's block bookkeeping (no new module or dependency)
---

- **2026-11-22** T-064-A (Claude): `import_docx` returns `blocks`, one entry per
  block in order: its kind (heading, paragraph, list or table), Markdown, Word
  style name, heading level, body position, the body paragraph numbers it came
  from, and the warnings raised for it. The joined Markdown equals the draft's
  `markdown`, and the existing `markdown` and `paragraph_styles` are unchanged.
  Tests in `tests/test_docx_blocks.py` (8) and all 23 existing importer tests
  pass. T-064-B is now unblocked.
