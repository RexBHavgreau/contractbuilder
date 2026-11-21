# Word shell contract

A **shell** is a `.docx` file that supplies document-level formatting for a
component-built contract. The composition code copies its package and
replaces its body wording; the shell's original body text is not contract
content. The source file must never be modified.

## Styles the app adds when they are missing

The converter uses these styles. A file does not have to contain them: when
one is missing, the **new document** gets a simple definition (based on
Normal, or Body Text if there is no Normal) and the shell file is never
changed (`shell_styles.py`, T-060-A). A style that is already there, under the
same Word name even if its internal ID differs, is used as it is.

| Purpose | Style ID | Word name | Type |
| --- | --- | --- | --- |
| Ordinary paragraphs | `Normal` | Normal | paragraph |
| First-level heading | `Heading1` | Heading 1 | paragraph |
| Second-level heading | `Heading2` | Heading 2 | paragraph |
| Third-level heading | `Heading3` | Heading 3 | paragraph |
| List paragraph base | `ListParagraph` | List Paragraph | paragraph |
| Bulleted list paragraph | `ListBullet` | List Bullet | paragraph |
| Numbered list paragraph | `ListNumber` | List Number | paragraph |
| Table formatting | `TableGrid` | Table Grid | table |

Word lists some of these in its gallery without writing them into the file
until they are used ("latent" styles); the app treats those as missing and
adds them. Define a style in the file if you want it to look different from
the app's default; the file's own style always wins.

A style with the right ID but the wrong type (for example a character style
called `ListBullet`) cannot be replaced, so it is reported as a warning and the
older fallbacks below apply.

## Numbering definitions

Clause numbering uses a three-level decimal outline and bulleted lists use a
bullet definition. If the file's `word/numbering.xml` has them, the converter
uses them; if not, it adds its own to the new document, so nothing is
required of the file.

The outline definition it looks for has these levels:

| Level (`ilvl`) | Number format | Label pattern |
| --- | --- | --- |
| 0 | `decimal` | `%1.` |
| 1 | `decimal` | `%1.%2` |
| 2 | `decimal` | `%1.%2.%3` |

The renderer creates a separate numbering instance when a new independent list
starts; it must not type clause numbers into the text.

## Final section properties

The document body must end with final section properties (`w:sectPr`) as the
last child of `w:body`. A `w:sectPr` inside a paragraph's properties marks a
section break; it does not replace the final body-level section properties.
Set the page size, orientation and all four margins in Word. The
checker permits missing page size or margins with a warning because Word has
defaults, but a shell with no final section properties cannot be used.

Headers, footers, page setup and other package-level parts belong to the
shell. Keep them in the file. The shell's body wording is ignored during
composition.

## Checker behavior

Call `shell_check.check_shell(path, supply_missing=True)` before using a file
for composition (the plain `check_shell(path)` keeps the older, stricter
behaviour below). The result has `errors`, `warnings`, `notes`, `can_generate`
and `style_fallbacks`:

- A **note** says what the app will add to the new document (a missing style
  or numbering definition). It needs no question; the window shows one calm
  line, worded by `shell_selection.describe`.
- An **error** stops generation. An unreadable/non-Word file, a document
  without a body, or missing final section properties cannot be used; the
  message says what is wrong and what to do, in plain words.
- A **warning** permits generation only after the user is told what will
  happen and chooses **Use this file** or **Choose another** (for example, a
  file with no page size). Never silently substitute a style or numbering
  definition.

Without `supply_missing`, missing styles and numbering are warnings, and these
fallbacks apply:

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
