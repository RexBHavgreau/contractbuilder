---
date: 2026-11-19
task: T-019-D
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 31
---

- **2026-11-19 — T-019-D/E native list and table rendering.** Lists use real Word
numbering. Each independent list gets a new numbering instance; ordered
sub-lists share the shell's multi-level decimal definition, and their level
determines the outline number. If a shell has only one bullet level, nested
bullets reuse that valid level and use direct paragraph indentation rather
than referencing missing numbering levels. Tables use native Word table,
row, cell and grid elements; header rows repeat, alignment is mapped to
paragraph alignment, and every cell contains a paragraph. The renderer
returns new numbering definitions/instances separately from body elements.
`docx_compose.compose_document` merges them into the shell numbering part,
remaps abstract and instance IDs per component, and updates paragraph
references before insertion. It creates a numbering part, relationship and
content-type override when a shell lacks numbering. The shell is never
modified; only its document body wording is replaced in the new output.
