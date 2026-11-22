# T-049-B — guided singular/plural wording

Implemented on 2026-11-22 in the `work/T-049-B` branch.

- Added a **Singular/plural word…** action to the field picker. It selects an existing List field and asks for the one-item and multiple-item wording.
- The preview displays the two word forms side by side. The helper inserts the selected List field with the `plural` format; it does not create a separate field or duplicate the list's value.
- Comma-containing wording uses the engine's slash separator. Field names and displayed wording retain their capitalization.
- List fields now use a multiline input labelled **One item per line** in the assembly field-entry form. Saved help text remains below the hint rather than overlapping it.
- Added pure tests for normal and comma-containing wording, invalid values, capitalization, and using one field with both `list` and `plural` formats in one component. Added a Tk window smoke test for the multiline List input.

CI and the size-gate report are pending. This task is not marked done until those checks pass and both executable sizes are confirmed below the repository limit.
