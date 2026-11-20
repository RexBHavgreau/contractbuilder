---
date: 2026-11-18
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 19
---

- **2026-11-18 — Enforce the Windows executable size budget against the built file.** CI runs `scripts/check_executable_size.py` on the packaged release executable and fails above 31,457,280 bytes (30 MiB). The script accepts a smaller `--max-bytes` value so tests can prove the failure path without constructing a large executable.
