---
date: 2026-11-19
task: T-019-F
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 32
---

- **2026-11-19 — T-019-F/G shell composition and field-engine hand-off.**
`docx_compose.compose_document(shell_path, components, output_path)` renders
each component independently, replaces only the shell body, and retains the
final section properties and all other shell package parts. It preserves
component and block order, leaves the shell byte-for-byte unchanged, and
writes through a temporary file. Generated numbering definitions and
instances are merged into the shell numbering part; IDs and paragraph
references are remapped per component so independent lists cannot collide.
When a shell has no numbering part, the composer creates the part, document
relationship and content-type override. The composed DOCX is then accepted by
the existing `core.Template` and `core.render` pipeline without changing
`core.py`: repeated fields are discovered once and filled in paragraphs,
lists and tables; block conditionals can cross component boundaries, and
inline conditionals work inside table cells. The tests cover both values of
each condition and the existing `money-words` and `date-formal` formats.
