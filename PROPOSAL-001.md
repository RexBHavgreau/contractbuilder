# PROPOSAL-001: Markdown-Based Contract Component Builder

**Status:** Proposed architecture, collaboratively developed by Beaux Hargrove and ChatGPT  
**Date:** 2026-11-18  
**Related decision:** T-008  
**First technical task:** T-019  
**Scope:** Add a component-based contract creation workflow without replacing or changing the existing Word-template workflow.

## 1. Executive summary

ContractBuilder should offer two independent ways to create a Word document:

1. **Word-template workflow:** Choose an existing DOCX/DOTX template, populate its custom fields, and generate a completed copy. This is the current workflow and must continue to work as it does now.
2. **Component-builder workflow:** Assemble a new contract from reusable components, populate the fields discovered in the assembled content, and generate a DOCX using a Word document shell.

The component builder should be approachable to office staff who do not know Markdown. Users should create and edit components inside ContractBuilder with a simple formatting interface, or import existing Word documents. Markdown is the canonical internal representation, not a skill users must learn.

Use Python libraries already compatible with the application and the existing lxml/WordprocessingML infrastructure. Do not require Pandoc, a separate Python installation, a system-wide converter, or another user-facing application. The target is to keep the Windows release executable at or below 30 MB. The current v0.3.0 Windows executable is 17,795,673 bytes, leaving approximately 12.2 MB of headroom. The actual size impact must be measured in release builds rather than inferred from PyPI wheel sizes.

## 2. Goals and non-goals

### Goals

- Preserve every existing feature and the current template-based workflow.
- Let users create reusable contract components inside the application.
- Store component content as Markdown text in a local SQLite database.
- Support ordinary contract formatting, including tables.
- Allow users to import existing DOCX content without manually retyping it.
- Assemble components in a deliberate order into a new Word document.
- Use a Word shell for document-level formatting.
- Reuse the existing field syntax, publisher profiles, and field-rendering engine wherever practical.
- Preserve component versions used by saved assemblies and make updates deliberate.
- Keep the application useful offline and lightweight.

### Non-goals for the first implementation

- Recreating Microsoft Word or building a full word processor.
- Supporting every feature of Word or every possible Markdown extension.
- Reproducing complex imported page layout inside an individual component.
- Requiring users to edit raw Markdown.
- Replacing the existing Word-template workflow.
- Carrying forward spreadsheet-based batch contract creation from advanced_app.py.
- Silently changing previously saved assemblies when a component is revised.

## 3. Two creation workflows

### A. Existing Word-template workflow

Keep the current process intact:

1. Choose a DOCX/DOTX template.
2. Discover its {{Field}} placeholders and conditional sections.
3. Populate the form, optionally loading a publisher profile.
4. Generate a new DOCX without modifying the source template.

Do not refactor this workflow merely to accommodate the component builder. Shared code should be extracted only when a concrete requirement justifies it and regression tests prove that existing behavior remains unchanged.

### B. New component-builder workflow

The planned process is:

1. Start a new assembly or open a saved assembly.
2. Choose a Word document shell.
3. Add components from the component library.
4. Arrange components in the desired order and omit optional components that do not apply.
5. Review the assembled content.
6. Discover all fields across the assembled components.
7. Populate the fields, optionally loading a publisher profile.
8. Generate a new DOCX using the Word shell and existing field-rendering capabilities.
9. Optionally save the assembly recipe for reuse.

An assembly is a reusable recipe, not a completed contract. It records the selected components, their order, the exact component versions, and the selected shell or shell reference.

## 4. Component content and supported Markdown

Markdown is the canonical component format. Store the Markdown source as text in SQLite, not as a separate DOCX file for every component.

Use markdown-it-py as the parser, with its table rule explicitly enabled. Its table support is not enabled by default in CommonMark mode, so tests must verify the configured parser rather than assume tables are active.

The initial supported content should include:

- Paragraphs and line breaks.
- Heading levels 1–3.
- Bold and italic text.
- Ordered and unordered lists.
- GFM-style tables, including ordinary text and inline emphasis in cells.
- Hyperlinks, if they can be handled cleanly and safely.
- Existing ContractBuilder field syntax such as {{Publisher Name}}, {{Fee}}, and {{#if Include Clause}}.

The custom Word renderer will translate parser tokens into WordprocessingML. It should create native Word paragraphs, runs, numbering, and tables, not screenshots or images of formatted text.

The Word shell supplies document-level styles. The renderer should map Markdown headings and paragraphs to styles defined by the shell, and use an agreed table style. List numbering should be represented using Word numbering definitions rather than typed numbers.

Do not attempt to support complex page layout in Markdown. Merged table cells, nested tables, floating objects, and similarly complex structures are outside the initial canonical subset unless a later design explicitly adds support.

## 5. User-facing component editor

Most users should not have to see or understand Markdown.

Build a simple contract-content editor inside ContractBuilder. It should provide:

- A normal editing area.
- A small formatting toolbar for headings, bold, italic, lists, links, and tables.
- A straightforward table editor that lets users add/remove rows and columns and enter cell text without typing pipe syntax.
- A preview of the formatted component.
- A way to insert existing ContractBuilder fields, while still allowing users to type familiar {{Field}} placeholders.
- An optional advanced Markdown source view for users who prefer direct editing.

The editing experience is a practical content editor, not a replacement for Word. The shell determines final typography and page layout. The preview should communicate structure and approximate formatting, but final pagination and page breaks are determined by Word.

## 6. Importing existing Word documents

DOCX import is a first-class way to create components. A user may choose an existing Word document, have ContractBuilder extract its content, review the result, and save it as a component.

Use the existing Python ZIP and XML capabilities (zipfile and lxml) to inspect DOCX packages. A new isolated module, such as docx_import.py, should:

1. Read the document body in its original block order, preserving the sequence of paragraphs and tables.
2. Convert supported paragraph styles into Markdown headings or paragraphs.
3. Convert bold, italic, and hyperlinks into supported inline Markdown.
4. Interpret Word numbering definitions for ordinary ordered and unordered lists.
5. Convert ordinary rectangular Word tables into Markdown tables.
6. Preserve literal ContractBuilder placeholders so the existing field engine can discover them later.
7. Return both Markdown content and a list of import warnings for anything it cannot represent faithfully.

Import means **content import**, not faithful transfer of the source document's overall appearance. The component's page size, margins, headers, footers, section layout, and document-wide typography are not imported as component formatting; the selected Word shell controls those in the final contract.

The importer must not silently discard unsupported content. At minimum, report structures such as merged cells, nested tables, images, floating shapes, equations, footnotes/endnotes, comments, tracked changes, or unusual Word fields when they cannot be converted faithfully. The user should be able to review the imported component before saving it. The initial implementation may reject or warn about these structures rather than attempting risky approximations.

Do not extract all paragraphs and then all tables separately. That would reorder mixed content. The importer must preserve the actual paragraph/table sequence from the Word document body.

Markdown import/export should also be available for portability. A user should be able to export a component as a .md file and import it again without changing its supported content.

## 7. Document shell and DOCX generation

A Word shell is a DOCX document that supplies:

- Page size and orientation.
- Margins and section properties.
- Document styles, including Normal and Heading 1–3.
- Headers and footers.
- Table styles and default table formatting.
- Relevant numbering definitions and document-level properties.

Its body content is not the source of the assembled contract wording. The composition engine should create a new document based on the shell, insert the assembled component content, and preserve the shell's document-level parts and relationships. The shell itself must never be modified.

The generation pipeline is:

1. Retrieve the selected component versions from SQLite.
2. Concatenate their Markdown in assembly order, respecting included/omitted components.
3. Parse Markdown with markdown-it-py and table support enabled.
4. Render the parsed structure as WordprocessingML using lxml and the shell's styles/numbering definitions.
5. Produce a new DOCX while retaining the shell's required package parts, relationships, styles, headers, footers, and section properties.
6. Pass the generated DOCX through the existing core.py field engine.
7. Discover fields across paragraphs and tables, collect values, apply publisher-profile values where they match, and render the completed contract.

The composition code should live in a separate module. Do not change the existing core.py template behavior as part of the initial conversion prototype.

## 8. Field handling and publisher profiles

Reuse the existing field syntax. A component can contain ordinary fields such as {{Publisher Name}} or formatted fields such as {{Fee | money-words}}. Conditional content can use the existing {{#if Field}} ... {{/if}} syntax where supported by the current engine.

After assembling the content, ContractBuilder should discover fields across the entire document. Repeated occurrences of the same field should result in one form input, not multiple independent questions. Fields appearing inside Word table cells must be discovered and filled just like fields in paragraphs.

The component builder and template workflow should use the same publisher profiles. A publisher profile may fill recognized fields, but users must review the populated values before generating the final contract.

## 9. Local storage and versioning

Use one local SQLite database for publisher profiles, components, component versions, assemblies, and assembly membership. This avoids maintaining unrelated databases for related application data.

The current database is named publisher_profiles.sqlite3. If the project changes it to a broader name such as contractbuilder.sqlite3, provide a safe one-time migration. Preserve existing publisher records, verify the migrated data, and retain a recoverable backup until migration succeeds. Do not simply create an empty new database and abandon existing profiles.

Suggested logical tables:

| Table | Purpose |
| --- | --- |
| publishers | Existing publisher and contact profiles |
| components | Stable component identity, name, description, category, tags, status |
| component_versions | Immutable Markdown content and version metadata |
| assemblies | Stable identity and name of a reusable contract recipe |
| assembly_versions | Saved revisions of an assembly recipe |
| assembly_components | Component version IDs, order, and inclusion settings for an assembly revision |

Each component has a stable identity and one or more immutable versions. Editing and saving a component creates a new version; it does not overwrite the content of a version already used by a saved assembly.

Each saved assembly revision references specific component-version IDs. Revising a component must not silently alter an existing assembly. The user can request an update, review which components have newer versions, choose which to update, inspect changes, and save a new assembly revision. The prior revision remains reproducible.

Components can be categorized and tagged for browsing. Initial categories might include parties, grant of rights, payment, warranties, termination, governing law, signatures, and schedules, but users should be free to create their own categories. Do not impose fixed contract schemas or restrict users to predefined kinds of agreement.

## 10. Lightweight distribution and licensing

The project target is a Windows release executable of no more than 30 MB. The current v0.3.0 executable is 17,795,673 bytes. Measure actual release artifacts after each dependency or packaging change and keep the size target visible in CI or release checks where practical.

Preferred implementation:

- markdown-it-py for Markdown parsing, with tables enabled.
- Its required runtime dependency, mdurl.
- Existing lxml and zipfile infrastructure for DOCX manipulation.
- Small custom Markdown-to-WordprocessingML and Word-to-Markdown modules.

Do not add Pandoc or python-docx to the first implementation. Pandoc is a separate, comparatively large executable. python-docx is not necessary for the planned path because the application already reads and writes WordprocessingML with lxml. Reconsider python-docx only if direct XML work proves substantially more difficult or fragile than expected.

markdown-it-py and mdurl are MIT-licensed. Retain required copyright and license notices, and include third-party license information in the application/repository. Do not copy or fork dependency code without a demonstrated need. Prefer a pinned, tested dependency over a private fork.

The component builder must work offline once the application is installed. It must not download a converter or require a system Python installation.

## 11. Testing and reliability requirements

Use invented test content only. The repository is public and must never contain wording, names, amounts, or other details copied from real contracts.

Tests should cover:

- Markdown paragraphs, headings, bold, italic, links, lists, and tables.
- Tables with multiple rows and columns, including placeholders inside cells.
- Mixed paragraphs and tables in the correct order.
- Word shell styles, page setup, headers, footers, and section properties.
- Ordered and unordered list numbering.
- Repeated placeholders appearing in multiple components.
- Conditional clauses after assembly.
- DOCX import preserving paragraph/table order and supported formatting.
- Import warnings for unsupported structures.
- Importing a DOCX, reviewing/saving its Markdown, assembling it, and generating a valid DOCX.
- Publisher-profile compatibility.
- Component and assembly version pinning and deliberate updates.
- No modification of the source shell, source template, or imported document.
- Existing template-workflow regression tests.

Test the generated DOCX at the XML/package level and, where feasible, open/render it with a real Word-compatible application during manual verification. A successful ZIP creation alone is not proof of a correctly formatted Word document.

## 12. Proposed implementation sequence

| Stage | Work | Purpose |
| --- | --- | --- |
| T-019 | Markdown-to-Word composition prototype, including tables | Prove the core conversion and field-rendering path |
| T-020 | DOCX-to-Markdown importer | Let users create components from existing Word content |
| T-021 | Unified SQLite schema, safe publisher migration, component/version/assembly storage | Establish durable local data structures |
| T-022 | In-app component editor, formatting toolbar, table editor, preview, and import review | Make component authoring accessible without Markdown knowledge |
| T-023 | Component library browser and contract assembly interface | Let users select, order, include, and omit components |
| T-024 | Saved assembly revisions and deliberate component updates | Make reusable recipes stable and reproducible |
| Later | Library backup, Markdown import/export, and additional supported Word features | Improve portability and long-term management |

Keep each implementation task small enough to review and test. Split large UI or storage tasks rather than combining the entire component builder into one change.

## 13. Acceptance vision

The component builder is successful when an office user who knows Word but not Markdown can:

1. Import an existing DOCX clause or create a component with the in-app editor.
2. Review and save that component in a local library.
3. Build a contract by choosing and ordering components, including tables.
4. Populate fields once even when they appear in multiple components.
5. Load publisher details where applicable.
6. Generate a correctly formatted DOCX using the selected shell.
7. Reopen the saved assembly later and reproduce it with the same component versions.
8. Deliberately update selected components without changing previous assemblies.

All of this must coexist with the existing Word-template workflow. The component builder is an additional capability, not a replacement.

---

## Technical references

- [markdown-it-py documentation and source](https://github.com/executablebooks/markdown-it-py) — Markdown parsing; enable its table rule explicitly.
- [markdown-it-py on PyPI](https://pypi.org/project/markdown-it-py/) — package metadata and dependency information.
- [python-docx documentation](https://python-docx.readthedocs.io/) — reference material for Word document structures; the first implementation does not require this dependency.
- [Microsoft Open XML documentation](https://learn.microsoft.com/en-us/office/open-xml/word/structure-of-a-wordprocessingml-document) — WordprocessingML package and document structure.
- [MIT License](https://opensource.org/license/mit/) — license terms for MIT-licensed dependencies.

**This proposal records the agreed direction. It does not authorize changes to the existing template workflow; implementation begins with the isolated proof of concept in T-019.**
