---
date: 2026-11-18
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 29
---

- **2026-11-18 — Protect component fields before Markdown parsing.** Each
  component is protected and parsed independently: replace complete
  `{{...}}` spans with collision-free alphanumeric placeholders, parse the
  Markdown, then restore the exact field text in the token tree (including
  inline children). This prevents table pipes and Markdown syntax from
  consuming field content and prevents fragments from adjacent components
  from combining into a field. Use `markdown_fields.protect_fields` and
  `restore_fields`; do not concatenate raw component source before parsing.
  The existing core engine already discovers and fills fields in paragraphs,
  list items and table cells, so no `core.py` change is needed. See T-019
  notes in `TASKS.md`.
