---
date: 2026-11-21
task: none
author: Claude
pull_request: not yet opened (local branch contract-builder-rename)
ci_run: not yet run
size: no executable change in the rename itself; the build names are changed, so the size gate needs confirming in CI
---

- **2026-11-21** Renamed the app to Contract Builder (Claude). The display name
  in `version.py`, the engine's name in `core.py`, the window title, Help > About,
  the build names in `build-windows.ps1`, `build-mac.command` and
  `.github/workflows/build.yml` (which finds the built file by name), the release
  title, the download name the updater uses, the guide and the README now say
  Contract Builder. The data folder is now `Contract Builder`; the one existing folder must be
  renamed by hand before the new version first runs (the guide says so). Kept on
  purpose: the Windows release file `Word-Template-Filler-windows-x64.exe` (the updater looks
  for that exact name); the macOS zip name, which matches it; and the history in
  CHANGES.txt, progress and decisions. Tests: 525 pass, 1 skipped.
