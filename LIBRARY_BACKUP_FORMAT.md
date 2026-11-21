# Library backup and Markdown export format

## Full-library JSON backup (format version 1)

A full backup is UTF-8 JSON. Its top-level object has these properties:

- `format`: the literal `contractbuilder-library-backup`
- `format_version`: the integer `1`
- `schema_version`: the SQLite `PRAGMA user_version` used by the source database
- `created_at`: an ISO 8601 UTC timestamp
- `includes_publisher_profiles`: `true` only when the user opted in
- `tables`: a mapping from table name to `columns` and `rows`

Each table's `columns` array gives the exact SQLite column order. Each item in
`rows` is an array of values in that order. UTF-8 text is not escaped to ASCII.

Every backup contains these component-library tables:

- `components`
- `component_versions` (including paragraph styles and every historical version)
- `assemblies`
- `assembly_versions` (including shell path, SHA-256 and finalization state)
- `assembly_components` (the exact pinned version, order and inclusion state)
- `field_definitions`

When the user checks **Include publisher profiles**, the backup also contains
`publishers`, `publisher_details`, `publisher_field_matches`, and
`publisher_parties`. These records can contain contact information and are
never exported by default. Reminder preferences are local application settings
and are never part of a backup.

A restore requires the same SQLite schema version and table structure. The
importer validates the format, schema, columns and row lengths before it
changes the database. The import itself is one transaction.

### Merge

Merge adds components, versions, assemblies and revisions with new database
IDs, then remaps their internal references. It does not overwrite existing
wording or history. Field definitions, publisher profiles, field matches and
parties that have a matching unique name/key are kept from the destination;
other records are added. Publisher data is considered only when the user
explicitly checks its import option.

### Replace

Replace substitutes the component library and field definitions with the
backup, retaining their original IDs and all version/assembly relationships.
It is destructive to the current component library. Existing publisher data
is untouched unless the backup contains it and the user explicitly checks
**Include publisher profiles**.

## Component Markdown export

A component Markdown file begins with YAML-style front matter containing one
JSON value:

```markdown
---
ContractBuilder-Component: {"format":"contractbuilder-component","version":1,...}
---

The component's Markdown wording appears here.
```

The `component` object records the source ID, name, description, category,
tags and archived/active status. The `saved_version` object records the source
version ID and number, timestamp, note and paragraph styles. The importer
recognizes this header, removes it from the wording, and uses its metadata when
creating a new component. A Markdown export represents the latest saved
version of each component; a full JSON backup is required to preserve the
complete version history and assembly references.
