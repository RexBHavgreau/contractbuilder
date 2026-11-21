---
date: 2026-11-21
task: T-051-B
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/101
ci_run: pending (update after the run on the latest commit)
size: pending; adds component_editor/clipboard_actions.py (a small Tk mixin, no dependency); confirm release and component-enabled sizes from the CI summary
---

- **2026-11-21** T-051-B and the T-051 umbrella (Claude): copy, cut and paste in the Components window. Copy and Cut take the text as shown (Tk's displayed characters), so hidden backslashes, `**` and list or heading markers are left out and fields and conditional markers are kept; a right-click menu adds Copy as stored text and Copy all wording as text; paste of ordinary text is escaped as typed text; the raw view says what it shows. Reproducing Beaux's stray backslash found two causes, both fixed with tests that fail without the fix: a selection ending between a hidden backslash and the character it escapes put the bold markers inside the escape (`snap_out_of_escapes`), and the formatted view treated escaped stars as italic markers and hid them (they now show as stars). 568 tests pass (22 new in `tests/test_clipboard_actions.py`). The Windows copy-into-Word check is in UT-003. Not done: pasting rich text from Word keeps only its plain text.
