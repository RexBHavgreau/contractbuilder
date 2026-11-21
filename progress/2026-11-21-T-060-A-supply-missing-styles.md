---
date: 2026-11-21
task: T-060-A
author: Claude
pull_request: pending (update when the PR is opened)
ci_run: pending (update after the run on the latest commit)
size: pending; adds shell_styles.py, a small pure-lxml module imported by shell_check, no dependency; confirm release and component-enabled sizes from the CI summary
---

- **2026-11-21** T-060-A (Claude): when the page layout file lacks a style the converter uses (Heading 1 to 3, List Paragraph, List Bullet, List Number, Table Grid), the **new document** now defines it, based on Normal (or Body Text if there is no Normal); a style with the same Word name under another id is used instead of duplicated; Word's "latent" styles count as missing. A file with no `styles.xml` gets one. Numbering gaps were already filled by the converter; they are now reported as notes. `check_shell(..., supply_missing=True)` (used by composition) reports all of this as plain notes ("the app will add one to the new document; your file is not changed") instead of warnings, and `ComposeResult.added_styles` names what was added; the default call is unchanged. Checked locally against a real layout file Beaux sent (not stored in the repository): it reports two notes and no warnings, and the output opens in python-docx with List Number defined. 385 tests pass, 17 of them new in `tests/test_shell_styles.py`; two older tests that encoded the fall-back-to-Normal behaviour for composed output were updated to the new rule. Open: the dialog still uses the old check until T-060-B; the real-Word hand check; CI size numbers.
