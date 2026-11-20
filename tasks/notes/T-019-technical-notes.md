# T-019 technical notes: field protection and hand-off

**Field protection (T-019-A, PR #19):** Before parsing, call
`markdown_fields.protect_fields(source)` separately for each component.
It replaces each complete `{{...}}` span with a collision-free token made
only of letters and digits. Parse that component with `md_parse.create_parser()`,
then call `markdown_fields.restore_fields(tokens, replacements)` on its
token tree before rendering. Restoration visits block tokens and inline
children, so fields remain literal text inside emphasis and table cells.
Never concatenate raw component Markdown before protection or parse: two
incomplete brace fragments at adjacent component boundaries can otherwise
become one valid field. Parse components independently and append their
rendered Word blocks.

**Parser observations:** CommonMark currently leaves underscores and a single asterisk inside
these sample names literal (`{{First_Name}}`, `{{First*Name}}`), but paired
double asterisks are parsed as strong emphasis and stripped from the field
name (`{{First**Name**}}` becomes `{{FirstName}}`). Without protection, the
table rule also treats the pipe in `{{Fee | money-words}}` as a cell
delimiter and corrupts the row.
Standalone conditional markers survive parsing. Blank lines create separate
paragraphs; soft line breaks stay inside one paragraph. List items can contain
separate paragraphs. GFM table cells are inline-only: standalone markers in
different cells survive as text, but a conditional pair cannot span cells
because the existing core requires paired block markers to share a parent.
An inline conditional pair within one cell remains in that cell's text.

**Core hand-off:** `core.read_parts(path)` and `core.Template(path)` read a
DOCX from a filesystem path; neither accepts in-memory package bytes.
`core.render(template, values)` reads the template path and returns the
finished DOCX as bytes. The spike test verifies field discovery and filling
in a paragraph, a bulleted list item and a table cell; each replacement is
one clean Word run. No `core.py` change is needed.
