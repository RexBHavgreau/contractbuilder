---
date: 2026-10-05
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 2
---

- **2026-10-05 — Templates are plain Word documents with `{{Field}}`
  placeholders; the engine edits the document's XML in place with lxml.**
  Keeps all Word formatting, numbering, tables, headers and footers; never
  rebuilds the document. The template file is never written to.
