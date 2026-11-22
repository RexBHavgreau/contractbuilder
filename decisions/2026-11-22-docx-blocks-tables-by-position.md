---
date: 2026-11-22
task: T-064-A
author: Claude
pull_request: not yet opened (branch any-task-3)
---

- **2026-11-22 — A table block is found by its position in the Word body, not by paragraph numbers.** The task asked for each block's paragraph numbers. Paragraph numbers count body paragraphs only, and a table's cell paragraphs are not counted, so a table has no paragraph numbers of its own. Each block records its body position instead, which locates a table exactly. Consequence: a cut at a table boundary uses the position; cuts at paragraphs and lists use the paragraph numbers.
