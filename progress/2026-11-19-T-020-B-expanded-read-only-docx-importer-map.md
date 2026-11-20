---
date: 2026-11-19
task: T-020-B, T-020-C, T-020-D
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/28
ci_run: 172
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 32
---

- **2026-11-19** T-020-B, T-020-C and T-020-D (ChatGPT, [PR #28](https://github.com/RexBHavgreau/contractbuilder/pull/28)): expanded the read-only DOCX importer to map Word heading styles and outline levels, preserve split-run bold and italic, escape literal Markdown punctuation, and keep split component fields intact. It now reads style-level and package numbering to import bullets and nested lists, converts letter/Roman numbering to decimal with a warning, and flags typed list markers. Rectangular tables become GFM tables; merged cells, nested tables, multi-paragraph cells and lists in cells produce located warnings while retaining best-effort text. Added fixtures for the supported subset and edge cases; the focused importer suite passes all 21 tests locally. GitHub Actions run #172 passed the full test job and Windows x64, macOS Intel and macOS Apple Silicon builds. No runtime dependency was added.
