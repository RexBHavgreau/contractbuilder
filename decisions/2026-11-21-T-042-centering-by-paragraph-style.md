---
date: 2026-11-21
task: T-042
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/70
---

- **2026-11-21 — Centering comes from the paragraph style only (Beaux).** No Align buttons and no marker in the text, which keeps exports plain Markdown. A centered paragraph is one whose style centers it (Title, Subtitle or any style in the layout file); T-061 is the mechanism for choosing the style per paragraph. Consequences: the app's own Title and Subtitle definitions (used when the file lacks them) are centered; a paragraph that was centered by hand in an imported Word file loses that centering, so the importer must warn and suggest a style; centering ordinary body text needs a style for it in the layout file. Rejected: a hidden marker the editor writes (new syntax), a separate alignment property, and no support at all.
