---
date: 2026-11-22
task: T-063
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/108
ci_run: pending (update after the run on the latest commit)
size: pending; adds assembly_picker_window.py (a small Tk module, no dependency) and moves the preview tag setup into one shared function; confirm release and component-enabled sizes from the CI summary
---

- **2026-11-22** T-063 (Claude): the Existing contract assembly list now has a preview pane beside the highlighted assembly, showing the contract as the builder previews it (pinned versions only, fields highlighted, labelled alternatives, paragraph styles such as a centered Title, components left out of the recipe absent, and a plain note when newer wording exists). The preview is drawn once the highlight rests; "Earlier revisions…" previews an older revision before opening; a revision that cannot be read shows a message instead of an error; the window is resizable and not transient, with the preview pane growing; "Edit in Build an assembly…" opens the builder. New module `assembly_picker_window.py`; `open_saved_assembly_direct` keeps its name and behaviour for callers. There is no second preview renderer: the builder's `preview_segments_for_components` is reused, and the three slightly different copies of the preview tag setup (Components window, builder, import review) are now one function, `component_preview.configure_preview_tags`. 626 tests pass (13 new in `tests/test_assembly_picker_preview.py`). The Windows check is in UT-003. Not done: the preview does not show the layout file's own formatting (Word decides the final layout).
