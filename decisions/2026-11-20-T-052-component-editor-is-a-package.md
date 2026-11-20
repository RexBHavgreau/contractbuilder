---
date: 2026-11-20
task: T-052
author: Claude
pull_request: none yet (branch claude/lucid-carson-0pjh6j)
---

- **2026-11-20 — `component_editor` is a package, one module per concern; the window is built from mixins.** Pure rules that import no Tkinter (`text_rules`, `tables`, `fields`, `toolbar_layout`, `save_feedback`) are separate from widgets, each dialog is its own module, and `ComponentEditorWindow` in `window.py` combines `LibraryListMixin`, `ToolbarMixin` and `WordingActionsMixin`, so every attribute the app and tests use (`editor.bold_button`, `editor._update_toolbar_state`) is still on the window. `__init__.py` re-exports every name the single file had. Dialogs are looked up through the package when they open (`component_editor.FieldInsertDialog`), so a test can still replace one by patching the package. Consequence: a new window or dialog is a new module, not more lines in `window.py`; a pure rule goes in a pure module and gets a test that needs no display. T-056 follows the same pattern for `simple_app.py` and `assembly_builder.py`.
