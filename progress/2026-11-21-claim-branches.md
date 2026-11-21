---
date: 2026-11-21
task: none
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/60
ci_run: pending (update after the run on the latest commit)
size: no executable change
---

- **2026-11-21** Claiming tasks (Claude): a claim was a one-line pull request, so two agents could both start the same task and only find out at merge, and agents did not see claims that were not merged yet. `scripts/claim.py` now claims by pushing the branch `claim/T-NNN` with the one-line status change; creating a branch is atomic on GitHub, so the second agent is refused at once. It refuses tasks that are not open or whose `Needs` are unfinished, `--list` shows claims, `--release` removes one, and `--new` reserves the next task number the same way (two agents asking at once get different numbers). Seven tests use a local bare repository, including a case where the second agent looked before the first pushed. TASKS.md, CLAUDE.md and tasks/README.md updated. Not yet exercised against GitHub itself: the first real claim will be the check. The parallel-agent-build skill was never in the repository's history on `main`, so there was nothing to delete.
