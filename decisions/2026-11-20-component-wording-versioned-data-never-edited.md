---
date: 2026-11-20
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 36
---

- **2026-11-20 — Component wording is versioned data, never an edited row.**
  `components` holds mutable descriptive metadata; each save inserts a
  numbered `component_versions` row. SQLite triggers reject updates and
  deletes, while `BEGIN IMMEDIATE` serializes the next-version allocation
  across application instances. Tags are JSON-encoded lists so arbitrary
  Unicode labels round-trip safely; categories and tags are not constrained
  to a built-in taxonomy. `library.py` contains no UI code or third-party
  dependency, and CI explicitly imports it in the Windows size probe.
  Searches include historical wording so an earlier clause remains findable.
