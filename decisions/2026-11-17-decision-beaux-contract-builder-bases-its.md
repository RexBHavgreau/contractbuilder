---
date: 2026-11-17
task: none
author: Beaux
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 8
---

- **2026-11-17 — DECISION (Beaux): the contract builder bases its build on a
  template with fields built by the user.** The template the user writes
  defines what the form asks for; the app does not carry built-in schemas
  for kinds of contract. Consequences: Build 4 field sets are not merged;
  improvements go into helping users build fields in their templates
  (documentation, checks, tools), not into hard-coded contract types.
