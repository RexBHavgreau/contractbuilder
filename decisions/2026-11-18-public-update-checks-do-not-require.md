---
date: 2026-11-18
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 21
---

- **2026-11-18 — Public update checks do not require a token.** The per-user token field remains optional for users who frequently hit GitHub's unauthenticated API limit. A 404 without a token means no release is published yet or the repository has moved; it does not prompt users to configure credentials.
