# T-029 implementation and validation

**Date:** 2026-11-21  
**Pull request:** #96 (open for review)

## Delivered

- Portable UTF-8 JSON backup for all component-library records: components, every wording version, assemblies, finalized revisions, pinned component versions, and reusable field definitions.
- Transactional replace and merge restore. Merge assigns fresh database IDs and remaps version and assembly references; replace preserves IDs and historical relationships.
- Publisher profiles, saved contact details, publisher-field mappings, and named parties are excluded by default. Export and import each require the explicit profile opt-in.
- Single-component and bulk Markdown export, including archived components, with a machine-readable metadata header; importer strips the header from visible wording and uses the saved component metadata.
- Optional four-week backup reminder, disabled by default and stored locally outside the transferable database.
- Components-window entry point and import preview with a plain-language summary and merge/replace choice.
- Documented backup and Markdown formats in `LIBRARY_BACKUP_FORMAT.md`.

## Validation

- GitHub Actions: **506 passed, 45 skipped** in the full test suite.
- The Tk window smoke-test step completed successfully.
- Windows PowerShell build-script validation and Windows application packaging succeeded.
- Main Windows executable: **18,301,882 bytes (17.45 MiB)** against the **30.00 MiB** limit; **12.55 MiB** of headroom.
- Component-editor size probe with all modules forced in: **18,300,161 bytes (17.45 MiB)**. The measured difference from the release build was **−1,721 bytes (−0.00 MiB)**, effectively no measurable bundle-size increase. The probe also passed the 30 MiB check with **12.55 MiB** of headroom.

The implementation is ready for review. The task remains claimed until PR #96 is merged, then its task file should be moved to `tasks/done/`.
