---
date: 2026-11-20
task: T-023-E, T-024-B, T-024-D
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/41
ci_run: 227
size: see text
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 42
---

- **2026-11-20** T-023-E and T-024-B through T-024-D (ChatGPT, [PR #41](https://github.com/RexBHavgreau/contractbuilder/pull/41)): completed the assembly-to-document workflow. The builder composes included components into a temporary DOCX, discovers unique fields across the whole document, and opens a separate field form reusing the existing input controls, validation, publisher-profile mapping, highlight option, blank-field confirmation and save flow. The existing template workflow is unchanged. Opening a saved assembly now lists newer wording without applying it; a review dialog compares pinned and newer wording with a unified diff and lets the user choose which component placements and versions to update. Saving creates a new immutable assembly revision, leaving previous revisions reproducible. End-to-end tests revise wording twice and confirm that the original revision still generates the original text, while the new revision uses only the selected wording. No runtime dependency or bundled data file was added. CI run #227 passed 243 tests and built Windows x64, macOS Intel and macOS Apple Silicon. The Windows release executable measured 18,090,846 bytes (17.25 MiB); the component-enabled build measured 18,094,048 bytes (17.26 MiB), an increase of 3,202 bytes, leaving 13,363,232 bytes (12.74 MiB) below the 30 MiB cap.
