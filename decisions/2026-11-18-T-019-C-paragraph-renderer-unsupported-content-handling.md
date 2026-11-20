---
date: 2026-11-18
task: T-019-C
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 17
---

- **2026-11-18 — T-019-C paragraph renderer and unsupported-content handling.**
`md_to_word.render_markdown(source, shell_path)` checks the shell before
rendering and returns WordprocessingML blocks plus warnings and errors.
Paragraphs and heading styles come from the shell's canonical style IDs;
missing styles use the checker's explicit fallbacks. Bold, italic, their
combination and hard line breaks become native Word run properties/elements.
Unsupported inline constructs keep readable text where possible and return
warnings; unsupported block constructs are omitted with an explicit warning.
The list and table tasks extend this renderer with native Word numbering and tables.
