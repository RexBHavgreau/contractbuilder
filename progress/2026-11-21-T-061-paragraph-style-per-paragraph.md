---
date: 2026-11-21
task: T-061
author: Claude
pull_request: pending (update when the PR is opened)
ci_run: pending (update after the run on the latest commit)
size: pending; adds paragraph_styles.py, component_editor/paragraph_style_control.py and a few hundred lines in existing modules, no dependency; confirm release and component-enabled sizes from the CI summary
---

- **2026-11-21** T-061 (Claude): a paragraph style can now be chosen per paragraph in the component editor, stored beside the Markdown, and applied when the document is created. Schema v6 adds `paragraph_styles` to `component_versions` (migration with `.bak-5` backup; an older app still opens the file; all existing versions mean "all Normal", so old components render unchanged). `paragraph_styles.py` holds the rules: which paragraphs count (ordinary top-level paragraphs, not headings, lists or tables) and `sync_styles`, which keeps styles with their paragraphs through insert, delete, edit, split, merge and move. `render_markdown` and `compose_document` take the list (`ComponentText`); `shell_styles` adds centered Title and Subtitle, Body Text and Block Text only when a component uses them and the file lacks them, and a name found nowhere becomes Normal with a plain note. The editor has a **Style** button (new module, three small hooks in existing ones), the preview and assembly preview show the style, and a style change alone is a new version. Import keeps Title, Subtitle, Body Text and Block Text, imports other styles as Normal with a note, and warns about hand-centered paragraphs. 431 tests pass (about 40 new). Not done: real-Word hand check (Beaux); picking styles beyond the five offered; showing a style-only difference in Review updates; CI size numbers.
