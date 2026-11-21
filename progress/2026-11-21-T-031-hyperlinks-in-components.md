---
date: 2026-11-21
task: T-031
author: GPT-6
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/102
ci_run: 44933539789
size: release 18,310,704 bytes; component-editor 18,310,062 bytes; headroom 12.54 MiB
---

- **2026-11-21** T-031 (GPT-6, [PR #102](https://github.com/RexBHavgreau/contractbuilder/pull/102)): added a shared allowlist for external `http`, `https`, and `mailto` links across Markdown rendering, Word import, editor styling, and preview. Unsupported or unsafe destinations remain visible as plain text with warnings. Generated DOCX files receive correctly remapped external hyperlink relationships, while the source shell remains byte-for-byte unchanged.
- Safe links in paragraphs and table cells survive Word import to Markdown and document generation. A field token inside linked text is retained, and filling that field preserves the hyperlink element and relationship.
- Validation: 542 passed, 60 skipped; Tk-window smoke tests 2 passed; Windows build, release size check, and component-editor all-modules probe passed (GitHub Actions run 44933539789).
- Size gate: release executable 18,310,704 bytes (17.46 MiB) against the 30 MiB limit, leaving 12.54 MiB of headroom. The component-editor probe measured 18,310,062 bytes (17.46 MiB), a -642-byte difference from the release build, effectively no measurable bundle-size increase.
