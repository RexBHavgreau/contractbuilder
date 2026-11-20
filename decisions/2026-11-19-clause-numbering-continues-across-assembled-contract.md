---
date: 2026-11-19
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 34
---

- **2026-11-19 — Clause numbering continues across the assembled contract.**
  Beaux chose continuous numbering across the whole assembled document
  (T-033 option 1). Every ordered list in every component is remapped to one
  shared native Word `w:num` instance, so clauses continue across component
  boundaries, separate lists, paragraphs and tables. Nested ordered items
  retain the shell's multi-level decimal outline. There is no per-component
  restart setting; schedules or exhibits needing separate numbering require
  a future explicit feature. T-030 still requires a real-Word check on
  Windows and macOS if available.
