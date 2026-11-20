---
date: 2026-11-20
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 40
---

- **2026-11-20 — The component editor stores Markdown, not a second rich-text format.** The Tk text widget keeps Markdown as the source of truth. Its default presentation elides syntax markers and applies simple heading/emphasis tags; “Advanced: show raw text” reveals the stored source. Toolbar actions write standard Markdown, and numbered-list indenting requires a preceding list item so a top-level item cannot accidentally become a code block. The preview computes decimal outline numbers from list nesting. The table grid uses GFM's first row as its heading row and preserves literal pipes separately from pipes inside {{field | format}} tokens. Field suggestions combine names already used in library versions with PROFILE_FIELDS; insertion and validation use core's own field parser. DOCX import calls the read-only importer, displays the draft and warnings before saving, and creates a component only after the user chooses “Save as component”. T-020-F's invented DOCX–Markdown–DOCX round-trip test is included as the prerequisite for this import dialog.
