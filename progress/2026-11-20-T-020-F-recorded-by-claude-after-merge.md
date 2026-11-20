---
date: 2026-11-20
task: T-020-F, T-022-C, T-022-G
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/39
ci_run: not recorded
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 43
---

- **2026-11-20** T-020-F and T-022-C to T-022-G (ChatGPT, [PR #39](https://github.com/RexBHavgreau/contractbuilder/pull/39)), recorded by Claude after the merge: the Components window gained a formatting toolbar (bold, italic, headings, bullets, numbering, indent and outdent, with Ctrl+B and Ctrl+I), a table grid editor, a field inserter built from the publisher schema and fields already used, a raw-text toggle, and a Word import review dialog; a DOCX to Markdown to DOCX round-trip test was added. CI on the merge to `main` passed. These dialogs are covered in CI only through their pure functions; nobody has opened them on a real display yet (TASKS.md T-038).
