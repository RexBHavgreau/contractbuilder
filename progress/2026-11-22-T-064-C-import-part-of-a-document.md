---
date: 2026-11-22
task: T-064-C
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/113
ci_run: pending (update after the run on the latest commit)
size: pending; adds import_choice_dialog.py, import_selection.py and import_selection_dialog.py (small Tk and pure modules, no dependency); confirm release and component-enabled sizes from the CI summary
---

- **2026-11-22** T-064-C (Claude): **Import Word** now asks **Whole document** or **Part of it** (the third choice, splitting into components and an assembly, appears when T-064-D provides it). Part of it lists the document's blocks (headings, paragraphs, whole lists, whole tables) with a tick box and a one-line preview, Shift-click for a range, Select all and Clear, warnings for the highlighted block and notes on the choice below (skipped blocks between the first and last choice; a numbered list taken without the list before it). Continue to review sends only the ticked blocks, with their paragraph styles, to the existing review window, which still has its own Save; the whole-document path is unchanged. The pure rules are in `import_selection.py`. Also fixed `main`'s red test: `test_a_field_without_help_looks_as_before...` expected two rows for a plain field, but T-049-B made it one (updated to one, two when it has help). 659 tests pass (23 new in `tests/test_import_selection.py`). The Windows check is in UT-003.
