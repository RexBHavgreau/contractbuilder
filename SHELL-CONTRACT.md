# Word shell contract

A **shell** is a `.docx` file that supplies document-level formatting for a
component-built contract. The composition code copies its package and
replaces its body wording; the shell's original body text is not contract
content. The source file must never be modified.

## Required styles

The checker looks for these Word style IDs in `word/styles.xml`. Keep the
IDs even if you change the visible formatting in Word.

| Purpose | Style ID | Word style type |
| --- | --- | --- |
| Ordinary paragraphs | `Normal` | paragraph |
| First-level heading | `Heading1` | paragraph |
| Second-level heading | `Heading2` | paragraph |
| Third-level heading | `Heading3` | paragraph |
| List paragraph base | `ListParagraph` | paragraph |
| Bulleted list paragraph | `ListBullet` | paragraph |
| Numbered list paragraph | `ListNumber` | paragraph |
| Table formatting | `TableGrid` | table |

The visible Word names are normally “Normal”, “Heading 1”, “Heading 2”,
“Heading 3”, “List Paragraph”, “List Bullet”, “List Number” and “Table Grid”.
The checker uses the stable style IDs, not the display names. A style with the
right ID but the wrong type is treated as missing.

## Numbering definitions

`word/numbering.xml` must contain a numbered instance (`w:num`) that refers
to a three-level decimal outline definition. Its levels must use these
formats and labels:

| Level (`ilvl`) | Number format | Label pattern |
| --- | --- | --- |
| 0 | `decimal` | `%1.` |
| 1 | `decimal` | `%1.%2` |
| 2 | `decimal` | `%1.%2.%3` |

This is the structure used for clauses numbered 1., 1.1 and 1.1.1. The shell
must also contain a numbered instance that refers to a bullet definition
(`w:numFmt` value `bullet`). The renderer creates a separate numbering
instance when a new independent list starts; it must not type clause numbers
into the text.

## Final section properties

The document body must end with final section properties (`w:sectPr`), either
as the last child of `w:body` or inside the paragraph properties of the final
paragraph. Set the page size, orientation and all four margins in Word. The
checker permits missing page size or margins with a warning because Word has
defaults, but a shell with no final section properties cannot be used.

Headers, footers, page setup and other package-level parts belong to the
shell. Keep them in the file. The shell's body wording is ignored during
composition.

## Fallbacks and checker behavior

Call `shell_check.check_shell(path)` before using a shell. The result has
`errors`, `warnings`, `can_generate` and `style_fallbacks`:

- An **error** stops generation. An unreadable/non-Word file, a document
  without a body, or missing final section properties is not a usable shell.
- A **warning** permits generation only after the user is told what will
  happen. Never silently substitute a style or numbering definition.
- Missing `Heading 1` uses `Normal`; missing `Heading 2` uses the nearest
  available lower heading level, then `Normal`; missing `Heading 3` uses
  `Heading 2`, then `Heading 1`, then `Normal`.
- Missing `List Bullet` or `List Number` uses `List Paragraph`, then
  `Normal`. Missing `List Paragraph` uses `Normal`.
- Missing `Table Grid` uses `Table Normal` if present; otherwise the renderer
  uses Word's default table formatting and must tell the user.
- Missing `Normal` leaves the paragraph style unset, so Word's default
  paragraph formatting applies; the warning must be shown.
- Missing the three-level decimal outline or bullet numbering definition is
  reported separately. The renderer must use an explicit fallback and tell
  the user that shell-specific numbering is unavailable.

`style_fallbacks` maps each missing or incorrectly typed style ID to the
selected replacement ID. A value of `None` means no named fallback exists;
the caller must use the documented Word default and show the warning.

The checker reads the package only. It must not save, normalize or otherwise
change the shell. Keep the invented shell fixture in test code; do not commit
a real or sample contract template to the repository.

## Integration requirements

Markdown-to-Word rendering and shell selection must:

1. run the checker before composition;
2. stop on errors and show each warning in plain English;
3. apply the returned style fallback map rather than guessing;
4. make any numbering/table fallback explicit to the user; and
5. leave the source shell byte-for-byte unchanged.
