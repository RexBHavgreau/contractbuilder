---
date: 2026-11-21
task: T-029
author: GPT-6
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/96
ci_run: 44931071522
size: release 18,301,882 bytes; component-editor 18,300,161 bytes; headroom 12.55 MiB
---

- **2026-11-21** T-029 (GPT-6, [PR #96](https://github.com/RexBHavgreau/contractbuilder/pull/96)): added full library backup and transactional merge/replace restore; publisher profiles are excluded by default and require opt-in on export and import. Added metadata-aware Markdown export/import for one or all components, including archived components, and an off-by-default four-week reminder.
- Validation: 506 passed, 45 skipped; Tk window smoke tests passed; Windows packaging and both size checks passed.
- Size gate: release executable 17.45 MiB against the 30 MiB limit (12.55 MiB headroom). The component-editor all-modules probe was 17.45 MiB, a measured difference of −1,721 bytes, effectively no measurable bundle-size increase.
- The test suite compares full source and restored table snapshots, including all version history, archived records, pinned assembly references, field definitions, and explicitly opted-in publisher-profile data.
