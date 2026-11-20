---
date: 2026-11-19
task: T-019-H
author: ChatGPT
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/27
ci_run: 166
size: see text
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 31
---

- **2026-11-19** T-019-H (ChatGPT, [PR #27](https://github.com/RexBHavgreau/contractbuilder/pull/27)): added a Windows CI comparison build that forces the T-019 modules into the same `simple_app.py` executable, then measures the actual files and checks both against 30 MiB. CI run #166 measured 17,801,283 bytes without the component stack and 17,962,926 bytes with it: a 161,643-byte (0.15 MiB) increase. The component-enabled build remains at 17.13 MiB with 12.87 MiB of headroom. The project remains open at the umbrella level because T-019-D has one separate numbering-continuity item reopened pending Beaux's T-033 decision.
