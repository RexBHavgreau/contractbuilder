---
date: 2026-11-20
task: T-056
author: Claude
pull_request: pending (pull request not yet opened; fill in before merging)
---

- **2026-11-20 — Big windows are split with mixins and module functions, not by rewriting them.** `WordTemplateFiller` keeps one class and takes the update and help methods from `UpdateDialogsMixin` and `HelpWindowsMixin`, moved without changes; the two large inline dialogs of the assembly builder became `review_updates(builder)` and `open_saved_assembly(builder)` / `load_revision(builder, revision)` in their own modules, with thin methods left in the window class. Why: a move that changes no line of logic can be proved identical by comparing parsed code, and tests that call `simple_app.WordTemplateFiller` or `AssemblyBuilderWindow` still work. Consequences: `simple_app.py` and `assembly_builder.py` re-export what they used to define; new dialogs and windows go in new modules (T-055 rule); `simple_app.py` stays the PyInstaller entry point.
