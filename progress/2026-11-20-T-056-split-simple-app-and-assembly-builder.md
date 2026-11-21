---
date: 2026-11-20
task: T-056
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/49
ci_run: pending (fill in with the run on the last code commit)
size: pending (read the Windows release and component-enabled sizes from the CI run); local Linux PyInstaller build +10,176 bytes (0.05 percent) against main
---

- **2026-11-20** T-056 (Claude, [PR #49](https://github.com/RexBHavgreau/contractbuilder/pull/49)): split `simple_app.py` (1,390 lines to 479) and `assembly_builder.py` (1,082 to 673) by concern into `ui_widgets.py`, `publisher_dialog.py`, `assembly_document_window.py`, `update_dialogs.py` and `help_windows.py` (the last two as mixins of `WordTemplateFiller`), and `assembly_helpers.py`, `assembly_review_dialog.py` and `assembly_open_dialog.py` (the two dialogs as functions taking the builder). `simple_app.py` keeps its name and the entry point; `assembly_builder.py` re-exports its helpers, so no import in the tests or the build changed. A script compared every moved class, method and function with the original after parsing: 0 differences (the three dialog methods differ only by `self` becoming `builder`). All tests pass under Xvfb, window smoke tests included (this environment now has a real Tk and a virtual display: `apt-get update`, then `apt-get install python3-tk xvfb xauth`, run with `/usr/bin/python3.12`). A local PyInstaller one-file build starts and runs under Xvfb, as does the build of `main`. Not checked: the Windows build and size job; the windows by hand on Windows, which nothing here changes visibly.
