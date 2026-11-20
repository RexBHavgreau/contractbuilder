---
date: 2026-11-20
task: T-022-B
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/36
ci_run: 212, 210
size: see text
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 38
---

- **2026-11-20** T-022-B (ChatGPT, [PR #36](https://github.com/RexBHavgreau/contractbuilder/pull/36)): added a read-only Tk Text preview backed by the existing table-enabled, raw-HTML-disabled Markdown parser and field-protection helpers. Preview segments cover headings, emphasis, lists, tables, code, links, blockquotes and field highlighting, including placeholders inside inline code. Updates are debounced and subscribe to Tk's modified event so paste, cut, undo and redo refresh too. No new runtime dependency is added. CI run #212 passed 228 tests and built Windows x64 and macOS Apple Silicon; the macOS Intel build passed in run #210 on the same code (the run #212 Intel job was still active when this entry was written). The Windows editor-plus-preview executable measured 18,004,832 bytes (17.17 MiB), leaving 13,452,448 bytes (12.83 MiB) below the 30 MiB cap.
