---
date: 2026-11-21
task: none
author: Claude
pull_request: not yet opened (branch user-guide-outline)
ci_run: not yet run
size: no executable change to the app's logic; the Help window is new, so the size gate needs confirming in CI
---

- **2026-11-21** The user guide (Help > User instructions) now has a contents
  tree beside the full text. Main sections and their steps or subsections are
  listed as a hierarchy; clicking one moves the text to that heading, and the
  whole guide still scrolls as one piece. The outline is found by
  `user_guide_outline.py` (pure, tested on the real guide); the window is in
  `user_guide_window.py`, a new module. The guide's title block now reads
  CONTRACT BUILDER, which the rename had missed.
