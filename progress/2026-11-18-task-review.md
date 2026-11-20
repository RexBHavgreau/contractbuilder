---
date: 2026-11-18
task: none
author: Claude
pull_request: not recorded
ci_run: not recorded
size: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 16
---

- **2026-11-18** Task review (Claude): v0.3.0 confirmed published by CI on its
  own, with the Windows `.exe` and both macOS builds, each with a SHA-256
  digest; CI green on every push to `main` since PR #6 (runs 44 to 60), which
  closed T-004 without a change; T-005 to T-007 checked against the code and
  86 passing tests. Found that the app and guides still call the repository
  private, that nothing tells users about the unsigned-app warnings, that
  GitHub's hourly limit now applies to update checks, and that a real
  counterparty name is still in the tests and, with a few other real details,
  in the now-public history. Added T-010 to T-017 for these.
