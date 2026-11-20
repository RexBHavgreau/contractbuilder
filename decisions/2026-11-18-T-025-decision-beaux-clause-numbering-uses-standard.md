---
date: 2026-11-18
task: T-025
author: Beaux
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 24
---

- **2026-11-18 — DECISION (Beaux, T-025): clause numbering uses standard
  nested ordered Markdown lists, rendered as a decimal outline; no new
  Markdown syntax.** Position in the nesting decides the number (1., 1.1,
  1.1.1), not the digits typed. The editor offers numbered list, indent and
  outdent so users never type indentation; the Word output uses one
  multi-level numbering definition from the shell; imports of Word
  multi-level lists become nested lists, and letter or Roman styles become
  decimal with a warning. Consequences: typed cross-references ("see Section
  2.1") do not follow moved clauses; underline, page breaks, signature
  blocks and defined terms are out of scope (Beaux: "shouldn't matter";
  T-032). Signature blocks belong in the Word shell or a template. Italic
  is `_text_`; Markdown has no underline, and imported underline is dropped
  with a warning.
