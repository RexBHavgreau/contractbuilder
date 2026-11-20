---
date: 2026-11-20
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 37
---

- **2026-11-20 — Assembly revisions pin exact component versions and shell bytes.**
  A revision stores ordered component-version IDs (including an explicit
  included flag) rather than following a component's latest version. It also
  records the selected shell path and SHA-256 so a later builder can detect
  a moved or changed shell. A revision is assembled as one transaction and
  finalized only after an included component exists; after finalization the
  shell metadata and membership are immutable. Archiving changes lifecycle
  status only. SQLite triggers protect historical components and assemblies
  from hard deletion even when foreign-key enforcement is disabled on a
  particular connection.
