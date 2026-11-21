# T-029 — component library backup and Markdown import/export

**Completed:** 2026-11-21  
**Pull request:** #96 (merged)

## Delivered
- Portable UTF-8 JSON backup of components, all wording versions, assemblies, pinned assembly revisions, and reusable field definitions.
- Transactional replace and merge restore. Merge remaps IDs while preserving references between components, versions, assemblies, and revisions.
- Publisher profiles and contact data excluded by default; explicit opt-in required both to export and to import them.
- Individual and bulk Markdown export, including archived components, with a metadata header the importer understands.
- Optional four-week reminder, disabled by default and stored locally outside the backup.
- Components-window backup/export entry point, human-readable import preview, and documented file formats.

## Validation
- Full GitHub Actions suite: **506 passed, 45 skipped**.
- Tk window smoke-test step: passed.
- Windows build and packaging: passed.
- Main Windows executable: **18,301,882 bytes (17.45 MiB)** against a **30.00 MiB** limit, leaving **12.55 MiB** of headroom.
- Component-editor measurement build with all modules forced in: **18,300,161 bytes (17.45 MiB)**. The measured delta was **−1,721 bytes (−0.00 MiB)**, effectively no measurable bundle-size increase. This build also passed the 30 MiB check with **12.55 MiB** of headroom.

The source library's full table snapshots were compared across an export/replace-import round trip in the tests, including historical versions, archived records, pinned assembly references, field definitions, and the explicitly opted-in profile tables.
