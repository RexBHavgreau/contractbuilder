---
date: 2026-11-21
task: T-048-A
author: Claude
pull_request: pending (branch claude/kind-keller-847k6d; update when the PR is opened)
ci_run: pending (update after the run on the latest commit)
size: not yet measured; start_screen.py is a small module the main window now imports (a few kilobytes, no new dependency); confirm release and component-enabled sizes from the CI summary
---

- **2026-11-21** T-048-A (Claude): the main window opens on a **Build contract from:** box with three buttons, each with a line of explanation: Existing contract assembly, New contract assembly, Word file (the file dialog lists .docx and .dotx). The Browse row is gone; the chosen file's name shows under the buttons. Alt+E/N/W press the buttons. New module `start_screen.py` (`build_start_row`, `StartScreenMixin`) keeps the edit to `simple_app.py` small; the builder loads only when chosen. USER-GUIDE and the built-in help text updated. Six tests under a virtual display in `tests/test_start_screen.py`. Open: Windows hand check; the CI size numbers for the `size` field above.
