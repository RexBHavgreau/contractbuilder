---
date: 2026-11-21
task: none
author: Claude
pull_request: not yet opened (local branch contract-builder-rename)
---

- **2026-11-21 — The app is called Contract Builder everywhere, including its data folder; the release file names keep their spelling.** The data folder moved from `TMAI Contract Builder` to `Contract Builder`. Beaux is the only user so far, so the folder is renamed in the code and the one existing folder is renamed by hand before the new version first runs; the guide says so. The Windows release file name is what the updater downloads, so it cannot change without breaking updates already installed. The macOS zip name matches it. Consequence: a copy of the app that runs before the folder is renamed starts with an empty library, which is why the guide asks for the rename first. Any future user needs a migration that copies the old folder and checks it before this rename is used.
