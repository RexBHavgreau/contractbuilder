---
date: 2026-11-18
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 18
---

- **2026-11-18 — Word shell contract and validation.** Shells are DOCX packages
whose body wording is ignored; they supply document styles, numbering,
table formatting, headers, footers and final section properties. The checker
requires the canonical style IDs documented in `SHELL-CONTRACT.md`, a
three-level decimal outline, bullet numbering and final `w:sectPr`. Missing
styles and numbering are warnings with explicit fallbacks; an unreadable
package, missing body or missing final section properties stops generation.
The checker is read-only. Downstream composition and assembly tasks must run
it before using a shell, surface warnings and apply the returned style map.
