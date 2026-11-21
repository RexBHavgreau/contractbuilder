---
date: 2026-11-21
task: T-035
author: Claude
pull_request: pending (branch claude/kind-keller-847k6d; update when the PR is opened)
---

- **2026-11-21 — Build tools (PyInstaller, lxml) are shown in every size summary, not pinned.** Pinning would stop the executable growing by surprise, but it would also stop security fixes arriving and nobody would be assigned to raise the pins. Instead the weekly run builds with whatever is current, prints the versions and the growth since the last release, and fails under 3 MiB of headroom, so a surprise shows up within a week with the versions to blame. If one version proves harmful, pin that one then and note it here.
- **2026-11-21 — Pull requests build only what they can affect.** `scripts/ci_scope.py` decides: application code and bundled files build Windows; only `build-mac.command`, `requirements.txt` and the workflow build macOS; everything builds on `main`, tags, the weekly run and manual runs. Consequence: a branch rule (T-057) must require only the `test` job, not the build jobs, or a skipped build blocks the merge.
