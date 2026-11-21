---
date: 2026-11-21
task: T-051
author: Claude
pull_request: not yet opened (branch ccr-9076da7d-zvifun)
---

- **2026-11-21 — Copying gives the text as shown, and fields and conditional markers are copied as written.** The formatted view hides Markdown syntax, so copying must not bring the syntax along. Fields and conditional markers are instructions to the document engine, not formatting; a copy that turned `{{else}}` into words would corrupt the component when pasted back as text. The pure function lives in its own module so it is tested without a display and does not touch `component_editor/window.py`, which other tasks change. Consequence: a copy of a conditional sentence still shows the `{{#if ...}}` markers, unlike the preview.
