---
date: 2026-11-20
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 43
---

- **2026-11-20 — Conditional markers appear in the preview as plain words, never as raw syntax.** `component_preview.marker_label` turns `{{#if ...}}`, `{{else}}` and `{{/if}}` into "If X is Y", "Otherwise" and "End of choice", styled as a grey tag, using `core.classify` and `parse_condition`. Fields keep their highlight. The editor's own wording box still shows raw syntax, which is intended for editing. Markers are not printed in documents, and the preview key says so.
