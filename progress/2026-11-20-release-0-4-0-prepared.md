---
date: 2026-11-20
task: none
author: Claude
pull_request: not recorded
ci_run: 44798337642
size: see text
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 44
---

- **2026-11-20** Release 0.4.0 prepared (Claude): `main` after PR #41 is green (run 44798337642: tests, Windows and both macOS builds). Windows executable 18,093,944 bytes (17.26 MiB), 12.74 MiB under the 30 MiB cap; v0.3.1 was 17,800,891, so the component builder added about 0.28 MiB. The size job's "added size" figure read -148 bytes and is meaningless (T-035). `version.py`, `CHANGES.txt` and a new USER-GUIDE.txt section are ready on branch `claude/kind-keller-847k6d`; merging it publishes v0.4.0. Not yet done: the hand check of the windows (T-038), a real-Word check of generated documents (T-030), the T-034 install error.
