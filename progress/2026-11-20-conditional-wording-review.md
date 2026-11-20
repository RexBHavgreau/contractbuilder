---
date: 2026-11-20
task: none
author: Claude
pull_request: not recorded
ci_run: not recorded
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 50
---

- **2026-11-20** Conditional wording review (Claude, from Beaux's sample component): the inline `{{#if Publisher Type = Non-profit}} ... {{else}} ... {{/if}}` renders correctly, but (1) the form's drop-down offers only the one value used in the condition, so the `else` alternative cannot be chosen (use one block per value), (2) spaces inside the markers double up in the sentence, (3) the preview styles every `{{...}}` as a field, and (4) copying from the editor brings the stored-text backslashes. Tasks: T-043-C (field creator with kinds), T-049-A/C/E, T-050, T-051, and T-046-D (several publishers per contract).
