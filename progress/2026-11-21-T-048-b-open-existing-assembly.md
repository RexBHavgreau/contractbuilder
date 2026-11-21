---
date: 2026-11-21
task: T-048-B
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/81
ci_run: 361
size: release 18,213,045 bytes; component-enabled 18,218,113 bytes; headroom 12.63 MiB
---

- **2026-11-21** T-048-B (ChatGPT, [PR #81](https://github.com/RexBHavgreau/contractbuilder/pull/81)): Added a searchable saved-assembly picker with latest-revision default, earlier-revision selection, update indicators, and direct opening into the publisher-enabled field form. The form can reopen the saved revision in the builder or start review of newer component wording. Missing or changed shell files now prompt for a replacement without rewriting the immutable saved revision. PR CI run #361 passed 437 tests (21 display-dependent skips) and the Xvfb window smoke test; the Windows release and component-enabled executables measured 18,213,045 and 18,218,113 bytes, leaving 12.63 MiB of headroom. Post-merge main run #362 also passed Windows and both macOS builds; its measured executables were 18,216,518 and 18,217,514 bytes, with 12.63 MiB of headroom. The Windows hand check is recorded separately in UT-005.
