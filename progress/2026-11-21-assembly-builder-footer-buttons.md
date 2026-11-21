---
date: 2026-11-21
task: none
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/60
ci_run: pending (update after the run on the latest commit)
size: no executable change
---

- **2026-11-21** Build an assembly window (Claude): Beaux's maximized window showed no Save assembly button. Cause: the status message shared one line with the buttons and was packed first with expand; a long message (the layout-file warnings run to several lines of text) took the whole width and pushed Close, Save assembly, Review updates and the others off the right edge. The message now has its own full-width line above the buttons and wraps to the window width, so the buttons cannot be pushed out. A window test with a very long message fails on the old layout and passes now. The warning text itself is T-060-B.
