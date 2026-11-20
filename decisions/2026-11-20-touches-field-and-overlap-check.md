---
date: 2026-11-20
task: T-055
author: Claude
pull_request: not yet opened (branch ccr-9076da7d-zvifun)
---

- **2026-11-20 — Every open task names the files it will change, and two claimed tasks never share one.** The Touches field is the list agreed in T-055's map, extended to every open task; umbrellas list the union of their subtasks. `scripts/overlaps.py` reads it. Why: parallel tasks that edit the same large file (`component_editor.py`, `simple_app.py`, `publisher_profiles.py`) produce conflicts that cost more than the work. Consequences: a task that changes a new file lists it, and a new window or dialog goes in a new module; the checker's exit code fails only for two claimed tasks, while the CI step only warns, because a stale claim should be closed, not block `main`. Schema migrations are numbered in merge order, one open migration at a time.
