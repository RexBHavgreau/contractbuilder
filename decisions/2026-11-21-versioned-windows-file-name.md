---
date: 2026-11-21
task: none
author: Claude
pull_request: not yet opened (local branch contract-builder-rename)
---

- **2026-11-21 — The Windows download carries its version in the name (`ContractBuilder-X.Y.Z-windows-x64.exe`); the fixed name stays published until no 0.4.x copy is installed.** Installed 0.4.x copies look only for `Word-Template-Filler-windows-x64.exe`, so a release that dropped it would stop them updating. The new updater accepts either name and prefers the versioned one. The build copies the one file under both names. Consequence: each Windows release carries two copies of the same file; the fixed one can be dropped once every installed copy is 0.4.5 or later, which is a decision for Beaux.
