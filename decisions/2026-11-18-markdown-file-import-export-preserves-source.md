---
date: 2026-11-18
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 16
---

- **2026-11-18 — Markdown file import/export preserves source text.** Read UTF-8
  with optional BOM support and write UTF-8 without a BOM. The importer reports
  raw HTML, images and footnotes as unsupported warnings, but retains the
  original Markdown rather than silently deleting content. This file utility
  is separate from the later DOCX importer.
