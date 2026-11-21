---
date: 2026-11-21
task: T-043-E
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/87
---

- **2026-11-21 — The app offers an optional starter list of fields, copied into the user's own definitions (Beaux).** Chosen over shipping nothing. The list is five invented, generic fields (Works, Publisher type, Territory, Term in years, Effective Date) and is only ever copied on request through "Add starter fields…" in the field picker; after that each field is the user's, editable and archivable like any other. A name that exists in any state, archived included, is never added again, so the user's choices stick. This keeps the 2026-11-17 rule that the app carries no built-in contract types or field schemas: nothing is fixed, and nothing is added unasked. To change the list later, edit `starter_fields.py` (invented examples only; the repository is public).
