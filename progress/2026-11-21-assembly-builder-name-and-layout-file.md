---
date: 2026-11-21
task: none
author: Claude
pull_request: pending (branch claude/kind-keller-847k6d; update when the PR is opened)
ci_run: pending (update after the run on the latest commit)
size: no executable change
---

- **2026-11-21** Build an assembly window (Claude): the **Assembly name** box and the **Choose shell…** button were laid out in a row whose weight let Tk squeeze it to nothing when the window was short, so Beaux saw "Enter a name" with nowhere to type it, and a footer telling them to choose a "Word shell" with no button. The squeezed row's weight is removed; the layout button now sits in the page-layout row with a one-line explanation. "Word shell" is called **page layout file** in the window, its messages and the guide (the guide still says "Word shell" in brackets once). A window test fails on the old layout (name box not visible in a 640-pixel-high window) and passes now.
