---
date: 2026-11-20
task: T-043-A
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/51
---

- **2026-11-20 — Keep field definitions in the existing publisher database.** Add them as schema version 4 rather than create a second database, preserving the established transactional migration and backup behavior. Use `core.key` for the unique field-name key so stored definitions follow the contract engine's comparison rules. Store default options and allowed values as JSON arrays, with choice allowed values kept distinct from format options. Retain definitions through archive/restore instead of physical deletion, and prevent renaming a field once an immutable component version refers to it.
