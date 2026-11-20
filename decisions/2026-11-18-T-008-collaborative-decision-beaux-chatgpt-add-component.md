---
date: 2026-11-18
task: T-008
author: Beaux and ChatGPT
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 22
---

- **2026-11-18 — COLLABORATIVE DECISION (Beaux and ChatGPT, T-008):
  add a component-based contract-building workflow without replacing Word
  templates.** The complete agreed proposal is in
  [PROPOSAL-001.md](PROPOSAL-001.md). Keep `simple_app.py` as the packaged
  app; do not merge `advanced_app.py` wholesale. Do not carry its spreadsheet
  batch workflow forward. Leave its saved-answer and contract-to-template
  features un-packaged for now and revisit them separately if needed. Users
  should author components inside the application without needing to know
  Markdown, and should also be able to import existing DOCX content. Markdown
  is the canonical component representation, stored as text in the same
  local SQLite database as publisher profiles, with metadata and version
  history. Support ordinary contract content including paragraphs, headings,
  bold, italic, lists, and tables. Use markdown-it-py with table support
  enabled and the existing lxml/zipfile infrastructure to render native
  WordprocessingML; do not add Pandoc or python-docx to the initial design.
  A Word document shell supplies document-level formatting (page setup,
  styles, headers, footers); it is not the source of assembled contract body
  wording. DOCX import converts supported content to Markdown in document
  order and reports unsupported structures rather than silently discarding
  them. An assembly pins the component versions it uses. Users may review
  and deliberately update selected components to newer versions; updates
  are never silent. Keep the existing template workflow and `core.py` field
  syntax intact. Target a Windows release executable no larger than 30 MB;
  measure actual packaged output rather than relying on source or wheel
  sizes. T-019 proves Markdown-to-Word conversion and field filling; T-020
  handles DOCX-to-Markdown import before the editor and library are built.
