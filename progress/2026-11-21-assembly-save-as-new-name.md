---
date: 2026-11-21
task: none
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/90
ci_run: pending (update after the run on the latest commit)
size: no executable change
---

- **2026-11-21** Build an assembly window (Claude): the Assembly name box is no longer locked once an assembly is saved or opened with Open saved. Saving an opened assembly under a **different name** now creates a **new assembly** with its own first revision, pinned to the same component versions, and leaves the original untouched; the status line says so before saving ("Saving will create a new assembly named X; Y will stay as it is") and after ("Saved as a new assembly... Y was not changed"). A change of capitals or spacing alone is the same assembly, and saving under the same name still adds a revision. The unsaved-changes check already counted the name. Six window tests in `tests/test_assembly_save_as.py`. Also fixed `main`'s board check, which was red because `tasks/T-048-C.md` said done but was not in `tasks/done/`, and added T-063 (preview pane in the saved-assemblies list) and T-064 (Import Word: a selection, or a whole document as components and an assembly; umbrella with four subtasks).
