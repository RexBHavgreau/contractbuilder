---
date: 2026-11-21
task: T-061
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/60
---

- **2026-11-21 — Paragraph styles are chosen per paragraph and stored beside the Markdown, not in it (Beaux).** A component is often several paragraphs of one theme that need different styles, so a per-component style does not fit. A marker in the text would be new syntax and would make exported components harder to reuse elsewhere, so the wording stays plain Markdown. Consequence: the style list lives in the component's stored data and the editor must keep it in step with every edit; a plain Markdown export does not carry the styles.
