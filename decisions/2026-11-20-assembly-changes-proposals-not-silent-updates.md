---
date: 2026-11-20
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 38
---

- **2026-11-20 — Assembly changes are proposals, not silent updates.**
  The storage API retrieves the exact component versions pinned by a saved
  assembly revision. It can list newer versions for each pinned component,
  but that list is advisory; adopting changes requires saving a new assembly
  revision. Revision creation is atomic and sequence-number allocation is
  serialized with `BEGIN IMMEDIATE`. This lets the eventual assembly UI show
  a meaningful comparison without altering an existing contract recipe.
