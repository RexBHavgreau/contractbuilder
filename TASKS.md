# TASKS.md

Open work on Word Template Filler, sized so that any agent, including a
cheap one, can pick up a task, do it, and hand it back. Read
[CLAUDE.md](CLAUDE.md) first: it has the layout, conventions, pitfalls and
decisions every task assumes.

## How to use this file

**To take a task:** change its `Status` to `claimed (your name or agent id,
date)` in the same commit or pull request that starts the work. Take only
tasks marked `Agent: any` unless you are a stronger model or a person. Do
not take a task marked `Needs: Beaux` until its decision is recorded in
CLAUDE.md, and do not take one whose `Needs` names an unfinished task.

**While working:** tick subtasks as they are done. If a task turns out
bigger than its size, split it: add new tasks below with the next free
number and say so in the original.

**When done:** set `Status: done (date, PR link)`, tick every subtask that
was done (and say why any was not), update the board below, add a line to
the Progress log in CLAUDE.md, and add a Decision log entry for any choice
you made that someone would otherwise have to rediscover. Leave done tasks
here for a month after they are done, then delete them.

**Subtasks:** a large task is an umbrella with subtasks named
`T-022-A`, `T-022-B` and so on (letters; if one itself needs splitting, use
`T-022-A-1`). Take, claim and finish subtasks one at a time, and tick them
in the umbrella's board row. The umbrella is done when all its subtasks are.
A subtask's `Needs` may name subtasks of other tasks.

**Size gate (every task, standing rule).** The Windows executable must stay
at or below 31,457,280 bytes (30 MiB). This is a design constraint on a
self-contained app, not a final check, so it applies at three points:

1. **Design.** A task that adds code, a dependency or a bundled file says in
   its first design note what it adds and how it reaches the executable.
   PyInstaller bundles only what the app imports, so a new module costs
   nothing until `simple_app.py` (or something it imports) uses it, and the
   CI comparison build must list it (T-035). Prefer the standard library and
   libraries already bundled; record a new dependency's measured size before
   adopting it.
2. **During.** Do not add a data file, font, image set or dependency "for
   later". Add it with the task that uses it.
3. **Final confirmation.** Before `Status: done`, read the CI size output for
   the release build and the component-enabled build, and put both sizes and
   the headroom in the Progress log entry. Under 3 MiB of headroom: stop and
   tell Beaux. A task is not done while the size check is red or was skipped.

The CI check also runs weekly (T-035), because build tools that are not
pinned can grow the executable without any commit.

**CI before merge (rule for every agent).** A pull request is not ready, and
nobody should merge it, until its own branch has a *completed, passing* CI
run at its latest commit: the tests, the Windows build with its size check
and, until T-035 changes it, the macOS builds. A run on an earlier commit,
a queued or in-progress run, or no run at all does not count. In practice:

- Open the pull request against `main`. A pull request whose base is another
  branch gets no CI run, which is how `main` went red on 2026-11-20 (PR #34).
  If the work is stacked, wait for the earlier pull request to merge, then
  retarget
- After pushing, wait for the run. Fix a red run on the branch. Never skip,
  delete, loosen or quarantine a test to get green
- Write the run number and the two size numbers (see Size gate) in the
  Progress log entry for the task
- After a merge, look at the run on `main`. If it is red, fixing it comes
  before any other work, and say so at the top of your report

**To add a task:** give it the next number and every field below. Write the
acceptance check so someone else can tell, without asking, whether it is
done. Add it to the board.

Fields:

- **Status:** `open`, `claimed (who, date)`, `blocked (why)`, `done (date, PR)`
- **Size:** S (under an hour), M (a few hours), L (a day or more; split it),
  or `umbrella` (a task made of subtasks, below)
- **Agent:** `any` (well-specified; a cheap agent will do), `careful` (needs
  judgement, a strong model, or Windows/macOS hardware), `human` (only a
  person can do it)
- **Needs:** anything that must happen first, such as `Beaux` for a decision
  or another task
- **Size gate:** present on any task that adds code, a dependency or a bundled
  file; see "Size gate" below. It is part of that task's `Done when`

## Board

Open and in-progress work only. Finished tasks leave this table and move to
"Done tasks" at the bottom, where they stay for a month. Reviewed 2026-11-20
(after PR #41). Next free number: **T-052**.

| Task | What | Status | Agent | Needs |
| --- | --- | --- | --- | --- |
| [T-039](#t-039-stop-the-update-restart-error-fix-in-041) | Stop the error shown when the app restarts after a self-update: cause confirmed, fix written; release 0.4.1 | open: needs a pull request, green CI, merge | careful | Beaux |
| [T-040](#t-040-let-the-components-and-assembly-windows-be-maximized) | Let the Components and assembly windows be maximized | open | any | — |
| [T-044](#t-044-make-saving-obvious) | Make saving obvious (visible confirmation, unsaved mark) | open | any | — |
| [T-041](#t-041-make-the-editors-toolbar-wrap) | Make the editor's toolbar wrap | open | careful | — |
| [T-045](#t-045-formatting-buttons-toggle) | Formatting buttons toggle on and off | open | careful | — |
| [T-047](#t-047-open-the-windows-in-ci-under-a-virtual-display) | Open the windows in CI under a virtual display | open | careful | — |
| [T-043](#t-043-field-picker-reusable-and-custom-fields-no-typing) | Field picker: reusable and custom fields (umbrella; A to D) | open | careful | — |
| [T-046](#t-046-fill-from-the-publisher-profile-with-matching-the-user-controls) | Fill from the publisher profile, with user-defined matching (umbrella; A to D) | open | careful | T-043-A |
| [T-048](#t-048-start-screen-build-contract-from) | Start screen: "Build contract from" Existing assembly / New assembly / Word file (umbrella; A to C) | open | careful | T-040 for A |
| [T-049](#t-049-conditional-and-singularplural-wording-without-typing-the-syntax) | Conditional and singular/plural wording without typing the syntax (umbrella; A to E) | open | careful | T-043-C |
| [T-050](#t-050-preview-shows-conditional-markers-as-if-they-were-fields) | Preview shows `{{else}}` and `{{/if}}` as fields: fix | open | any | — |
| [T-051](#t-051-copying-out-of-the-editor-gives-clean-text-stray-backslashes) | Copying out of the editor gives clean text; stray backslashes | open | careful | — |
| [T-042](#t-042-centering-and-other-paragraph-alignment) | Centering and other paragraph alignment | open: decision first | human | Beaux |
| [T-038](#t-038-try-the-component-builder-by-hand-on-windows) | Try the 0.4.0 release by hand on Windows, including the self-update | open, after the release | human | T-037 |
| [T-030](#t-030-check-generated-documents-in-real-word) | Check generated documents in real Word | open, ready | human | — |
| [T-035](#t-035-make-the-size-gate-complete-and-periodic) | Make the 30 MiB size gate meaningful and run weekly; cut redundant CI builds | open | careful | — |
| [T-036](#t-036-housekeeping-stale-branches-and-legacy-code) | Housekeeping: stale branches and legacy code | open, needs decisions | human | Beaux |
| [T-029](#t-029-component-library-backup-and-markdown-export-and-import) | Library backup; Markdown export and import | open | careful | — |
| [T-031](#t-031-hyperlinks-in-components-optional) | Hyperlinks in components (optional) | open | careful | — |

**Waiting, not a task:** GitHub Support's purge of the old commits behind
pull requests #1 to #9. Details under T-018. Nobody needs to do anything until
Support replies.

**Suggested order:** T-039 first: open a pull request from the branch (it
carries the restart fix and the 0.4.1 bump), wait for green CI, merge to
publish 0.4.1. Then T-038 on a PC with 0.4.0 (the update to 0.4.1 will show
the error one more time; the update after that should not) and T-030 (Word).
T-035 before the next feature lands, since the size comparison is currently
meaningless and every pull request runs three platform builds. T-029
(backup) and T-031 (links) are next features; T-036 is tidying.

Usability fixes from Beaux's hand testing (T-040 to T-047) are grouped under
"Component manager usability"; they ship as 0.5.0 after 0.4.1.

**History was rewritten on 2026-11-18.** Work from a clone or download made
after that date. A copy made earlier holds the old history; delete it rather
than pushing from it.

Done and kept for the record: T-001, T-003, T-004, T-005, T-006, T-007,
T-009, T-013, T-016 (below the open tasks).

---

## Open tasks





## T-018 Push the cleaned history and finish the clean-up

- **Status:** waiting on GitHub Support; no action for anyone else (all
  other steps done, 2026-11-18 and 2026-11-19). Not counted as a task on the
  board
- **Size:** S
- **Agent:** human
- **Needs:** GitHub Support's reply. Other tasks no longer wait for this one.

Beaux decided on 2026-11-18 that details from real contracts must be removed
permanently, even by rewriting history (T-016). Claude rewrote every branch
and tag and checked the result, but this session may push only its own
branch, so the final push is Beaux's. The rewritten repository, a script that
pushes it, and the list of what was removed (`BLOCKED_TERMS.txt`, private:
never commit it) were handed over in the chat, as a folder called
`contractbuilder-cleanup`.

Steps, in this order:

- [x] **GitHub email privacy first.** On github.com: your picture > Settings >
      Emails. Tick "Keep my email addresses private" and "Block command line
      pushes that expose my email". Otherwise the next commit made on the
      website records your personal address again. (Verified 2026-11-18:
      the merge of PR #10, made on the website, carries the noreply address.)
- [x] **Allow the force-push.** Settings > Rules (or Branches): if a rule
      protects `main` against force pushes, turn that off for now, and back on
      afterwards.
- [x] **Push.** Install Git for Windows if needed (https://git-scm.com), then
      double-click `push-cleaned-history.bat` in the handover folder. It shows
      what it will replace and asks before pushing. It refuses, changing
      nothing, if anything was pushed to GitHub after 2026-11-18 03:47 UTC.
      (Verified 2026-11-18: all twelve branches and tags on GitHub matched the
      cleaned copy exactly; a fresh clone holds 99 commits, none of the 51
      removed details, and no personal email address.)
- [x] **Turn on the guard.** Settings > Secrets and variables > Actions > New
      repository secret. Name: `BLOCKED_TERMS`. Value: the contents of
      `BLOCKED_TERMS.txt`. From then on CI fails if any of those terms is
      committed again (`tests/test_no_private_details.py`). Keep the file
      somewhere private, such as your password manager. (Verified: CI run 67
      received the secret and passed all 88 tests, the guard included, with
      none skipped.)
- [x] **Ask GitHub Support to purge what a push cannot reach.** The nine
      pull requests (#1 to #9) keep their own copies of the old commits, and
      old commit pages stay viewable by their address until GitHub clears its
      caches. At https://support.github.com, choose "Remove sensitive data"
      (or "Contact us" about it), and paste the request text from
      `github-support-request.txt` in the handover folder. (Sent by Beaux on
      2026-11-18.)
- [ ] **GitHub Support confirms the purge.** Until then the old commits can
      still be fetched through pull requests #1 to #9 (checked 2026-11-18:
      Build 2's old commit through #1, Build 4's through #6). When Support
      replies, check again: `git fetch https://github.com/RexBHavgreau/contractbuilder.git refs/pull/6/head`
      should no longer bring in commit `4becc60`. (Checked 2026-11-19: not yet
      purged. Pull request #6 still delivers `4becc60`, and #1 still delivers
      Build 2 and Build 3's old commits.) If Support declines, ask Beaux
      whether to delete and recreate the repository, the only other way to
      remove pull-request copies (it loses issues, pull requests, releases and
      stars).
- [x] **Forks.** On the repository page, Insights > Forks. There should be
      none (it was public for under a day). If there are, tell GitHub Support.
      (Verified 2026-11-18: 0 forks.)
- [x] **Old copies.** Beaux confirmed 2026-11-19 that no copies were made
      anywhere else.
- [x] Tell Claude, or any agent, that it is done; it then reconnects its own
      working copy to the new history. (Done 2026-11-18: Claude's working copy
      matches GitHub, its old commits are purged, and its scratch copies of the
      old history and of the private list are deleted.)

**Done when (only the last part is open):** `main` on GitHub starts with the commit the script names, the
next CI run on `main` is green with `test_no_details_from_real_contracts`
passing (not skipped), and GitHub Support has confirmed the purge.

## Component builder (T-020 to T-031; T-019, T-021, T-025 to T-028 and T-032 to T-033 are done)

Direction: [PROPOSAL-001.md](PROPOSAL-001.md), which is unchanged. These
tasks implement it, with the gaps found in review closed by the extra tasks
(T-019 to T-032) and by choices recorded inside the tasks below. Every task
in this section uses **invented test content only**, adds tests, keeps the
existing template workflow's tests green, and leaves `core.py`'s template
behaviour unchanged unless a subtask says otherwise and proves no regression.

Where a task here differs from or narrows the proposal, it says so:

- **Database:** add tables to the existing `publisher_profiles.sqlite3`; do
  not rename it (T-021). The proposal allowed either; renaming gains users
  nothing and risks their profiles.
- **Hyperlinks** are a separate, optional task (T-031), not part of T-019.
- **Library backup and Markdown export** move earlier (T-029).
- **The size limit** is a CI check (T-027, T-035) and a standing rule for
  every task (see "Size gate" above).
- **Clause numbering** is decided (T-025): nested ordered lists, rendered as
  a decimal outline. Other legal formatting is out of scope (T-032).

### T-039 Stop the update restart error (fix in 0.4.1)

- **Status:** open: fix and tests are on the branch `claude/kind-keller-847k6d`
  (2026-11-20), with the 0.4.1 version bump and release notes in a separate
  commit; needs a pull request, green CI and a merge (which publishes 0.4.1)
- **Size:** S
- **Agent:** careful
- **Needs:** Beaux (merge and release)
- **Size gate:** yes, but this adds no module or file; confirm the CI size
  numbers as usual

Beaux saw an error message while the app updated itself (0.3.0 to 0.3.1, and
again 0.3.1 to 0.4.0); the app ran normally afterwards. He suspected it had
to do with the new file having the same name as the old one.

**Cause (reproduced 2026-11-20 and confirmed against the message Beaux
sent: "Failed to load Python DLL" naming a `_MEI` folder and
`python311.dll`).** The update restarts the app by running a small script, which starts
the new `.exe`. A PyInstaller one-file app unpacks itself into a temporary
`_MEI...` folder and passes that folder's location to anything it starts,
through environment variables. The script, and the new app it starts,
inherited those variables, so the new app tried to reuse the old app's
temporary folder, which is deleted when the old app closes. The result is a
"Failed to load Python DLL ... _MEI..." message. It is about an app
restarting itself, which is why it looks tied to the file name, but
renaming the file would not change it. A test build of a tiny one-file app
under PyInstaller 6.22.3 (what CI installs) failed exactly this way when it
started itself with the inherited environment, and started cleanly when
`PYINSTALLER_RESET_ENVIRONMENT=1` was set.

- [x] `self_update.clean_restart_environment()` removes the inherited
      `_PYI_*` and `_MEIPASS2` values and sets
      `PYINSTALLER_RESET_ENVIRONMENT=1`; `start_swap` passes it to the script
- [x] Tests: the environment is cleaned; `start_swap` passes it
- [x] Beaux sent the message; it matches the cause above (T-034)
- [ ] Release 0.4.1 with the fix. **The fix only helps updates from 0.4.1
      onward**: the script that restarts the app is written by the version
      that is closing. So 0.4.0 to 0.4.1 will probably show the message one
      more time; 0.4.1 to the next version should not. Tell staff the message
      is harmless: click OK and start the app again from its icon
- [ ] On the 0.4.1 to next-version update, confirm there is no message

### T-038 Try the component builder by hand on Windows

- **Status:** open
- **Size:** S
- **Agent:** human
- **Needs:** Beaux (or a colleague)

The editor and assembly windows are Tkinter dialogs. CI exercises their
logic but opens no window, and Claude's environment has no display, so no
one has looked at them yet. Do this on the published 0.4.0, starting from a
PC that has 0.3.1 and real publisher profiles, so the update itself is the
first step. Use invented wording only; the repository is public and
screenshots may be shared.

- [ ] **Update:** Help > Check for updates offers 0.4.0; install it; the app
      reopens as 0.4.0 (title bar). Note whether SmartScreen warned (T-011,
      T-034) and any error message, with its words
- [ ] **Existing data:** the first start of 0.4.0 upgrades the publisher
      database in place. Publisher profiles are all still there, and a file
      ending `.bak-1` sits beside `publisher_profiles.sqlite3` in the user
      data folder (`%LOCALAPPDATA%` on Windows). Keep it for now
- [ ] Components > Manage components: make a component with a heading, a
      bold word, a numbered list with an indented sub-item, a table (use the
      Table button) and a field (use the Field button, with a format such as
      `money-words`). Save. The preview matches
- [ ] Toolbar behaves with the preview and with "Advanced: show raw text"
      switched on (the one unchecked item of T-022-C)
- [ ] Import Word: choose one of your own invented `.docx`
      files, read the warnings, edit, save. The original file is unchanged
- [ ] Save a second version; Version history shows both
- [ ] Build assembly: choose a shell (use one made in Word following the
      guide), add three components, move one, untick one, check the preview,
      Save assembly, close, Open saved
- [ ] Fill fields and create the document: each field appears once; a
      publisher profile fills what it should; the file opens in Word with
      numbered clauses continuing 1, 2, 3 across components (this is also
      T-030)
- [ ] Revise a component, open the saved assembly: Review updates shows the
      new wording and nothing changes until you tick it
- [ ] Write down anything confusing in plain words. Anything that stops you
      is a bug task; anything that is only awkward goes in a new task

## Component manager usability (found by Beaux, 2026-11-20)

Beaux used the 0.4.0 windows by hand and listed what got in the way. Each
item below was checked against the code (what the code does today is stated
in each task). Rules for all of them: invented test data only; keep logic in
plain functions that CI can test, because CI opens no window (T-047 changes
that); say in the task what it adds to the executable and confirm the CI size
numbers (see Size gate); and finish with a short hand check on Windows. The
decision in the 2026-11-17 Decision log still holds: **the app carries no
built-in schemas for kinds of contract**, so "preset" fields below means the
publisher-profile fields the app already has plus fields the user defines.

Suggested order: T-040, T-044, T-041, T-045 are quick and independent. T-047
makes the rest easier to prove. T-043 comes before T-046 (they share storage).
T-042 starts with a decision from Beaux. T-048 (the start screen) can go
anytime after T-040. T-049 and the publisher type in T-046-C need the field
store of T-043-A. These ship after 0.4.1 (T-039) as 0.5.0.

### T-040 Let the Components and assembly windows be maximized

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** —
- **Size gate:** yes (no new code reaches the executable; say so and confirm)

**Today:** the Components window and the Build assembly window are created
with `window.transient(parent)` (`component_editor.py`, `assembly_builder.py`).
On Windows a transient window has no maximize or minimize button, which is
what Beaux sees. Both are working windows, not pop-up questions.

- [ ] Stop making the two main windows transient; keep them resizable with a
      sensible minimum size, and keep them from hiding behind the main window
      (lift on open, one instance at a time as now)
- [ ] Check the larger dialogs (import review, version history, review
      updates, table editor) and decide for each: modal and fixed, or
      resizable and maximizable. Resizable if it holds a long text or a grid
- [ ] Layout uses the extra room: lists and the wording box grow, buttons stay
      put
- [ ] Hand check on Windows: maximize, restore, minimize, and the window
      returns to the front when "Manage components" is chosen again

**Done when:** both main windows can be maximized and restored on Windows, and
the layout fills the space.

### T-041 Make the editor's toolbar wrap

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** —
- **Size gate:** yes

**Today:** the formatting buttons sit in one row (`pack(side="left")`), so
anything past the window width is cut off, even when maximized if the row is
long enough.

- [ ] A wrapping toolbar: when the width changes, buttons flow onto more rows
      instead of being cut off; related buttons stay together (text style;
      lists and indent; table, field, import)
- [ ] The row computation is a plain function (button widths and available
      width in, rows out) with tests, including a width narrower than the
      widest button and one wider than all of them
- [ ] Works at the window's minimum size and when maximized; no horizontal
      scrolling anywhere
- [ ] Every button gets a plain-English tooltip or label (it is easy to guess
      what "B", "I" and "Field" do, harder for "Outdent")
- [ ] Hand check on Windows at several widths

**Done when:** at every window width, every toolbar button is reachable
without scrolling.

### T-042 Centering, and other paragraph alignment

- **Status:** open: needs a decision first
- **Size:** M after the decision
- **Agent:** human for the decision, then careful
- **Needs:** Beaux
- **Size gate:** yes

**Today:** nothing offers centering. Markdown has no centering. Table columns
can already be left, centered or right aligned (T-019-E). T-025 and T-032 set
the rule of no new Markdown syntax and no underline, page breaks or signature
blocks, so this needs a conscious choice. Beaux's wording: "if it can be an
option, it should be".

Options to decide between (Claude recommends B):

- **A. Not supported.** Say so in the guide; titles and blocks that must be
  centered belong in the Word shell or a template. Nothing to build.
- **B. A hidden marker the editor writes.** A button "Center" puts an invisible
  marker (for example an HTML comment on the line before the paragraph) in the
  stored text; the user never types it. Other Markdown tools ignore it, so
  exports degrade to a normal paragraph. The renderer reads it and sets
  centered alignment; the preview centers; the importer reads centered Word
  paragraphs back; the toggle removes it. Raw HTML stays switched off for
  everything else
- **C. A paragraph style from the shell** (for example "Centered Title") that
  the user picks by name. Needs a shell contract change (T-026) and more
  steps for the user

- [ ] Beaux chooses; record it in CLAUDE.md's Decision log
- [ ] If B or C: renderer (`md_to_word.py`), preview, editor button (a toggle,
      see T-045), importer (`docx_to_markdown.py`, so imported centered text
      stays centered; today it is dropped silently with no warning), field
      protection check, tests, guide text
- [ ] If A: warn on import when a centered paragraph loses its alignment

**Done when:** the choice is recorded and, if B or C, a centered paragraph
survives edit, save, preview, import, assembly and the Word output.

### T-043 Field picker: reusable and custom fields, no typing

- **Status:** open (umbrella; work its subtasks)
- **Size:** umbrella of T-043-A to T-043-D
- **Agent:** careful
- **Needs:** —

**Today:** the Field button opens a small dialog with a drop-down of names
already used in the library plus the publisher-profile names, a format box and
an options box (`FieldInsertDialog`). A new field means typing its name, the
list is not grouped, and a field you invent is not remembered anywhere unless
it is already in some saved component. Beaux wants fields chosen from a list,
reused without retyping, and new fields added by the user.

#### T-043-A Store field definitions

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** —
- **Size gate:** yes

- [ ] A database migration (next schema version, with the usual backup and
      transaction, as T-021-A did) adds field definitions: name, short
      description, group, default format and options, **allowed values**
      (for a field that is a choice, such as Publisher type: Non-profit, Sole
      proprietor), optional link to a publisher-profile column or detail
      (used by T-046), archived flag. Allowed values matter because the form
      rejects a value that is not one of a choice's options (`core.py`
      compares ignoring case and spacing, so "Non-profit" and "nonprofit" differ)
- [ ] `library.py` functions: list, add, edit, archive and restore. Names
      follow `core`'s field rules and are unique ignoring case and spacing;
      a clear plain-English error for a bad or duplicate name
- [ ] Nothing is deleted while any component version uses the name (archive
      only), matching the rule for components
- [ ] Tests with a temporary database, including upgrade from the current
      version and an older app opening the upgraded file

#### T-043-B Built-in publisher fields

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-043-A
- **Size gate:** yes

- [ ] The picker always offers the publisher-profile fields the app already
      has (`PROFILE_FIELDS`, plus the combined address) with readable names
      such as "Publisher name" and "Contact email", each linked to its profile
      column. No contract-type fields are built in (Decision log, 2026-11-17)
- [ ] Names used by existing components are included automatically, so the
      picker is never missing a field the library already uses
- [ ] Tests

#### T-043-C Field picker and field creator

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-043-A, T-043-B, T-040
- **Size gate:** yes

Beaux (2026-11-20): conditional syntax is hard for people who do not know it,
so the field creator should be a window where the user defines **different
kinds of field**, and a conditional field should walk the user through its
creation.

- [ ] The Field button opens a searchable list grouped as Publisher, Fields
      from your library, and Your fields. Double-click or Insert places
      `{{Name}}` at the cursor, with the field's default format
- [ ] **New field…** opens the **field creator**. Step one asks what kind of
      field it is, in plain words, with a one-line example for each:
      **Text** (a name, an address), **Long text** (several lines),
      **Date**, **Amount of money**, **Number**, **List** (one item per line,
      such as titles), **Choice** (a drop-down of values), **Optional clause**
      (include a paragraph or phrase only when ticked), **Conditional
      wording** (different wording depending on a choice, T-049-A), and
      **Singular or plural word** (T-049-B)
- [ ] Each kind then asks only the questions it needs (name, description,
      format and options, allowed values) and saves a field definition
      (T-043-A); the plain kinds finish in one step, the three wording kinds
      continue into their walk-throughs and insert the finished text
- [ ] **Edit** and **Archive** manage the list; a field that is a choice shows
      its values
- [ ] The picker stays open on request so several fields can be inserted in a
      row; the editor's preview updates
- [ ] Typing a name still works for a one-off, and a malformed one is still
      explained (`make_field_placeholder`, as today)
- [ ] The kind-to-syntax rules are plain functions with tests
- [ ] Hand check on Windows

#### T-043-D Use the same fields elsewhere

- **Status:** open
- **Size:** S
- **Agent:** careful
- **Needs:** T-043-C
- **Size gate:** yes

- [ ] The assembly field form (and the template form) show a field's
      description where one exists, so staff know what to type
- [ ] Guide section added; tests

#### T-043-E Optional starter set of fields (needs Beaux)

- **Status:** open: needs Beaux's decision
- **Size:** S
- **Agent:** human for the decision, then any
- **Needs:** Beaux, T-043-A
- **Size gate:** yes (a small text list; confirm it)

Beaux (2026-11-20): standardized fields make automatic filling and conditional
wording work, "which is another reason that building a standardized field set
is a good idea". The 2026-11-17 decision says the app carries no built-in
schemas for kinds of contract. These fit together if the standard set is
**the user's own**, kept in the field definitions of T-043-A, and any set the
app ships is only an optional, editable starting list, never a fixed schema.

- [ ] Beaux decides: (1) no shipped set, users define their own; or (2) an
      optional starter list that is copied into the user's definitions on
      first use and can be edited or archived (Claude suggests names such as
      Works (a list), Publisher type (a choice), Territory, Term; Beaux
      supplies the real list, with invented examples only in the repository)
- [ ] If (2): "Add the starter fields" in the picker, never re-adding ones the
      user archived; tests
- [ ] Record the decision in CLAUDE.md

**Done when (T-043):** a user can insert a stored field, add and reuse a custom
field, and never has to type a name, from the Components window.

### T-044 Make saving obvious

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** —
- **Size gate:** yes (no new executable content; say so and confirm)

**Today:** after Save version the only sign is a small grey line at the bottom
of the window ("Saved <name> · version N", `ComponentEditorWindow.save`), easy
to miss and out of sight when the window is short.

- [ ] A clear confirmation next to the button the moment the save completes
      (for example the button reads "Saved ✓ version 3" for a few seconds, or
      a green banner above the wording), and a failed save shows a red message
      in the same place that stays until dismissed
- [ ] An "Unsaved changes" mark that appears when the wording or details
      change and clears on save; the window title shows it too
- [ ] The component list refreshes and keeps the saved component selected, with
      its new version number visible
- [ ] The message text is built by a plain function with tests (saved, saved
      with note, failed, nothing to save)
- [ ] Hand check on Windows: nobody can miss that it saved

**Done when:** a user always sees at once whether the save worked.

### T-045 Formatting buttons toggle

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** —
- **Size gate:** yes

**Today:** bold and italic wrap the selection in markers every time; pressing
again adds a second pair. Headings and lists can be added but there is no
direct way to remove them (Outdent only reduces a level).

- [ ] **Bold and italic toggle** on the selection, and on the word at the
      cursor: pressing again removes the markers; a mixed selection becomes
      all bold first; bold plus italic is handled; markers inside a field
      placeholder or already escaped are left alone
- [ ] **Heading buttons toggle** back to a normal paragraph (pressing the
      active heading level, or choosing "Normal text"); **Bullets and
      Numbering toggle** off on the selected lines, and Numbering/Bullets
      switch between each other
- [ ] Buttons show their state for the text at the cursor (pressed or not)
- [ ] The editing rules are pure functions on Markdown text (text, selection
      and action in; text and selection out) with tests, including
      multi-line selections and the cases above
- [ ] Works in the formatted view and in the raw-text view
- [ ] Hand check on Windows

**Done when:** every formatting button can undo its own effect.

### T-046 Fill from the publisher profile, with matching the user controls

- **Status:** open (umbrella; work its subtasks)
- **Size:** umbrella of T-046-A to T-046-D
- **Agent:** careful
- **Needs:** T-043-A (shared storage)

**Today:** the template form and the assembly form each have one "Load" button
for a saved publisher. It fills every field whose name matches a fixed list of
aliases in `publisher_profiles.py` (`_FIELD_ALIASES`, for example "Publisher
Name", "Contact Email"), and nothing else; the profile has 13 fixed columns.
Fields with other names are silently skipped, the user cannot say "my field
Licensor is the publisher name", there is no way to fill a single field, and a
profile cannot hold extra details. Beaux's wording: each time publishing
information is looked for, there should be an option to fill all of it from
the profile, and it should be more customizable.

#### T-046-A Let users define the matching

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-043-A
- **Size gate:** yes

- [ ] A "Field matching" window (Publishers menu) shows each profile column
      with the field names that currently fill from it (the built-in aliases
      plus the user's own) and lets the user add or remove names; user entries
      are stored in the database and take priority over the built-ins
- [ ] A field defined in the picker (T-043) can be linked to a profile column
      there, and the same link is used here
- [ ] `values_for_template` uses the user's matching first; names stay
      matched ignoring case, spacing and apostrophes as now
- [ ] Tests, including a custom name beating a built-in one and an unknown
      name still being skipped without an error

#### T-046-B Fill from the profile wherever it applies

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-046-A
- **Size gate:** yes

- [ ] In the template form and the assembly form, every field that has a
      profile column gets a small "From publisher" control that fills just
      that field from the chosen publisher; the existing button is renamed
      "Fill all from publisher"
- [ ] After a fill, say plainly what was filled and which profile details had
      no matching field, so a missed match is visible
- [ ] If a publisher is chosen after fields were typed, ask before replacing
      (as now); an option "Fill automatically when I choose a publisher" is
      available and off by default
- [ ] Applies the same way wherever the app asks for publisher information,
      including any later screen
- [ ] Tests for the fill rules; hand check on Windows

#### T-046-C Extra publisher details, starting with Publisher type

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-043-A, T-046-A
- **Size gate:** yes

Beaux (2026-11-20) wants some wording to depend on the publisher, for example
non-profit organizations versus sole proprietors, with the choice stored in the
publisher profile and filled in automatically. Today the profile has 13 fixed
columns and no type, so this cannot be filled automatically.

- [ ] A migration adds extra details per publisher (name, value), shown and
      edited in the publisher profile window. A detail that has allowed
      values (T-043-A) is edited with a drop-down, so the stored value can
      never differ from what the wording tests for
- [ ] "Publisher type" is the first such detail, with values the user sets
      (for example Non-profit, Sole proprietor, Company)
- [ ] Details join the matching of T-046-A, so a condition such as
      `{{#if Publisher Type = Sole proprietor}}` is filled from the chosen
      publisher in the template form and the assembly form, with the
      "From publisher" controls of T-046-B
- [ ] A profile with no value for a detail leaves the field for the user to
      choose, and the form says why
- [ ] Tests, including a stored value that is not among the field's allowed
      values being caught when saving the profile, and the end-to-end case:
      two publishers of different types produce different wording from the
      same assembly

**Done when:** choosing a publisher selects the right alternative wording
without the user answering a question.

#### T-046-D More than one publisher in a contract (parties)

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-046-A, T-046-B
- **Size gate:** yes

Beaux's sample component has two parties with fields named for their role:
`{{ Publisher One (Proprietor) }}`, `{{ Publisher One’s Address }}`,
`{{ Publisher One’s State }}`, `{{ Publisher Two (Publisher) }}`,
`{{ Publisher Two’s Address }}`, `{{ Publisher Two’s Contact }}`. Today the
forms have one "Saved publisher" box, and the profile matching knows only a
single set of names ("Publisher Name", "Contact Email"...). So none of these
fields would fill from a profile, and a second party could not come from one.

- [ ] Define **parties** (a name such as "Publisher One", with an optional role
      label) in the field definitions or the field-matching window (T-046-A):
      a field is "the address of Publisher One", so every profile column
      (name, address, state, contact...) is available for each party without
      listing every combined name by hand; a name like `Publisher One’s
      Address` matches automatically
- [ ] The template form and the assembly form show **one publisher choice per
      party that appears in the document**, with the per-field and fill-all
      controls of T-046-B working per party
- [ ] A document with one publisher behaves as now; the old names keep working
- [ ] Tests: two parties filled from two profiles, one party left to type, and
      curly and straight apostrophes in the names; hand check on Windows

**Done when (T-046):** any field can be tied to a publisher detail by the user,
including a publisher type that selects alternative wording, and the user can
fill one field or all of them from the profile wherever publisher information
is asked for.

### T-047 Open the windows in CI under a virtual display

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** —
- **Size gate:** yes (CI only; say so)

**Today:** CI tests only the logic behind the windows, and Claude's own
environment has no display, so the toolbar, saving and window behaviour in
T-040 to T-045 have never been seen running before a user finds them.

- [ ] The Linux test job runs a small set of window tests under a virtual
      display (`xvfb`): open the Components window; check the toolbar fits at
      several widths (T-041); type, save and check the confirmation (T-044);
      press each formatting button twice (T-045); open the field picker
      (T-043); build an assembly
- [ ] Tests stub message boxes and file dialogs so nothing blocks, and run
      quickly; document the pattern in CLAUDE.md "Working on it"
- [ ] A window test that fails makes the job fail; the other jobs are
      unchanged
- [ ] Known limit written down: Linux cannot show Windows-only window
      behaviour such as the missing maximize button (T-040)

**Done when:** a broken toolbar or save confirmation fails CI before it ships.

### T-048 Start screen: "Build contract from"

- **Status:** open (umbrella; work its subtasks)
- **Size:** umbrella of T-048-A to T-048-C
- **Agent:** careful
- **Needs:** —

**Today:** the main window opens on "Choose a template" with a Browse button
for a Word file. Starting from a saved assembly means Components > Manage
components > Build assembly > Open saved; a new assembly starts the same way.
Two of the three ways to start a contract are buried. Beaux wants three clear
choices up front.

#### T-048-A The three choices

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-040
- **Size gate:** yes

- [ ] The top of the main window gets a **Build contract from:** row with three
      buttons, each with one plain line under it: **Existing contract
      assembly** (pick a saved recipe), **New contract assembly** (open the
      builder), **Word file** (a `.docx` or `.dotx`, as the Browse button does
      now; the file dialog lists both types)
- [ ] The existing template row and its Browse button become the Word file
      path rather than a fourth thing on the screen; the Components and
      Publishers menus stay for managing the library and profiles
- [ ] Keyboard use works (Tab, Enter, access keys) and the buttons sit well on
      a small screen; first-run help text updated
- [ ] Hand check on Windows

#### T-048-B Open an existing assembly straight to the fields

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-048-A
- **Size gate:** yes

- [ ] **Existing contract assembly** opens a list of saved assemblies (name,
      latest revision, date, and a mark where newer component wording is
      available), searchable; Enter or double-click opens it
- [ ] The latest revision opens by default; an "Earlier revisions" choice
      shows the others. Choosing one goes directly to the field form
      (`create_assembly_document` with the pinned component versions), with
      the publisher controls available, without opening the builder
- [ ] From the field form, "Edit this assembly…" opens the builder with it
      loaded, and "Review updates…" is offered when newer wording exists
- [ ] If the shell file moved or changed since the revision was saved, say so
      in plain English and let the user pick it again instead of failing
- [ ] Tests for the list and the open path; hand check on Windows

#### T-048-C Recent and last-used

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-048-B
- **Size gate:** yes

- [ ] Under the three buttons, a short "Recent" list of the last few
      assemblies and Word files used, one click to reopen; remembered per
      user in the existing settings file; a missing file is shown as such and
      removable
- [ ] Guide section "Starting a contract"; tests

**Done when (T-048):** all three ways of starting a contract are visible on the
first screen and each leads to a filled-in form in one or two steps.

### T-049 Conditional and singular/plural wording without typing the syntax

- **Status:** open (umbrella; work its subtasks)
- **Size:** umbrella of T-049-A to T-049-E
- **Agent:** careful
- **Needs:** T-043-C (field picker)

**Today:** the engine already does both, and they work inside components
(tested in T-019-G), but a user has to type the markers by hand:

- Alternative wording: `{{#if Publisher Type = Non-profit}} ... {{else}} ...
  {{/if}}` (also `!=`, `not`, and a bare field for an optional clause). The
  form turns the values used in conditions into a drop-down list. The opening
  and closing markers must be on their own lines for whole paragraphs.
- Singular or plural: a field typed one item per line, and
  `{{Works | plural: work, works}}` writes "work" for one line and "works" for
  more; the same field can also be shown as a list ("A, B, and C"). The Field
  dialog has the format and options boxes for this, but nothing says that the
  field should be a list or that the count comes from its lines.

So the same component can already serve one work or several. What is missing is
a way to build these without knowing the syntax, and the matching of the
publisher type to the profile (T-046-C).

#### T-049-A Conditional wording walk-through

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-043-C
- **Size gate:** yes

Beaux's own example (2026-11-20), typed by hand: "...of {{ Publisher One’s
Address }}, {{#if Publisher Type = Non-profit}} a non-profit corporation
{{else}} a sole proprietor {{/if}} organized in and doing business under the
laws of the State of ...". The engine accepts it and picks the right words, but
checked on 2026-11-20 it has two traps the walk-through must avoid:

- **The form can offer only one choice.** A drop-down gets its values from the
  conditions in the text. With `= Non-profit` and an `else`, the only value is
  "Non-profit"; choosing "Sole proprietor" is rejected as "must be one of:
  Non-profit", and only a blank answer gives the `else` wording. Writing one
  `{{#if Publisher Type = ...}}` block per value, as below, lists every value
- **Extra spaces.** Spaces inside the markers stay in the sentence, so the
  result reads "X,  a non-profit corporation  organized" with two spaces

- [ ] **Conditional wording** (from the field creator, and a **Choice
      wording…** toolbar button) walks the user through four steps, each on
      its own page with a plain explanation: (1) which choice field decides it,
      or create one here; (2) its values (for example Non-profit, Sole
      proprietor) and the wording for each, typed in a box with a live
      sentence preview; (3) where it goes (inside the sentence, or as its own
      paragraph; the markers go on their own lines when it is a paragraph);
      (4) a summary showing the wording the contract will read for each value
- [ ] It writes **one `{{#if Field = Value}}` block per value**, with no
      spaces inside the markers, so every value is a drop-down option and the
      sentence spacing is right. Where one alternative is "everything else",
      it still writes explicit blocks
- [ ] The field's allowed values are saved with the field definition
      (T-043-A), so the publisher profile (T-046-C) offers the same values
- [ ] The text is built by a plain function and checked by opening the result
      with `core.Template`, so a malformed block can never be inserted. Tests:
      Beaux's sample, two, three and four values, inside a list item, a field
      used in more than one component, and each value rendering with single
      spaces
- [ ] **Optional clause…** (a yes/no field and the clause it controls) and an
      **Only if blank** variant use the same walk-through pattern
- [ ] Editing an existing block reopens it in the walk-through; hand-typed
      text that does not fit (a lone `else`) is shown as it is with a warning
      from T-049-C, never rewritten silently

#### T-049-B Singular/plural helper

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-043-C
- **Size gate:** yes

- [ ] In the Field picker, **Singular/plural word…**: choose a list field
      (such as Works), type the singular and plural words, and the editor
      inserts `{{Works | plural: work, works}}`; wording with commas uses the
      slash form automatically
- [ ] The form shows a list field as a multi-line box labelled "one per line",
      and the preview shows both forms side by side so the author can see it
- [ ] Tests, including capital letters and a field used both as a list and as
      a count in the same component

#### T-049-C Show the alternatives in the preview

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-049-A
- **Size gate:** yes

- [ ] The editor and assembly previews show conditional blocks as labelled
      alternatives (for example a tinted "If Publisher type is Non-profit"
      band) instead of raw markers, and warn in plain English when a closing
      marker is missing or not on its own line
- [ ] Add the warnings the walk-through cannot give for hand-typed text: an
      `else` with only one value listed ("the form will offer only
      Non-profit; use Choice wording… to list every value"), a missing or
      misplaced closing marker, and double spaces left around a phrase
- [ ] A control to preview the assembly "as" a chosen value, so the author can
      check each alternative reads well; tests

#### T-049-D Guide and examples

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-049-A, T-049-B
- **Size gate:** no executable change (say so)

- [ ] USER-GUIDE.txt: how to build choice wording and singular/plural wording
      from the buttons, with the publisher-type and works examples using
      invented names, and the rule that choice values must match the allowed
      values exactly

#### T-049-E Tidy spaces around inline conditional wording (engine)

- **Status:** open
- **Size:** S
- **Agent:** careful
- **Needs:** —
- **Size gate:** yes (no new content; confirm)

Found 2026-11-20: `of X, {{#if A = B}} a phrase {{else}} another {{/if}} organized`
renders "of X,  a phrase  organized", with two spaces on each side, because the
spaces inside and outside the markers both stay. The engine already collapses
blank lines; extend that to a doubled space created by removing or replacing
an inline conditional.

- [ ] In `core.py`, collapse a run of spaces created where an inline
      conditional was replaced, in both the kept and the dropped case, without
      touching spaces the author typed elsewhere; a change to the engine, so
      all existing template tests stay green and new ones cover: phrase kept,
      phrase dropped, at the start and end of a sentence, next to punctuation,
      and inside table cells
- [ ] The template workflow produces the same documents as before for every
      existing test fixture

**Done when (T-049):** an author can write one clause that changes with the
publisher type and with the number of works, using only buttons and typing the
wording itself.

### T-050 Preview shows conditional markers as if they were fields

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** —
- **Size gate:** yes (no new content; confirm)

Reported by Beaux 2026-11-20 and reproduced: `component_preview.py` styles every
`{{...}}` as a field, so `{{#if ...}}`, `{{else}}` and `{{/if}}` look like field
names ("else", "/if"). The syntax is fine; the preview does not know which
markers are instructions. The editor's field suggestions already tell them
apart (`core.classify`).

- [ ] Use `core.classify` to tell fields from `if`, `else` and `/if` markers;
      give the markers their own style (a muted tag with plain words such as
      "If Publisher Type is Non-profit", "Otherwise", "End of choice") and keep
      fields highlighted as now. The same in the assembly preview
- [ ] A short key under the preview says what the colors mean
- [ ] Tests on the preview segments for a sentence with an `if`/`else`, a
      block form, an optional clause and a field inside the conditional text
- [ ] T-049-C builds on this for the fuller labelled-alternatives view

**Done when:** no instruction marker is ever shown as a field.

### T-051 Copying out of the editor gives clean text; stray backslashes

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** —
- **Size gate:** yes

Beaux (2026-11-20) copied a component and found backslashes he did not type:
`\(hereinafter the **proprietor\**)`. Two causes are known or likely:

- **Known:** the editor stores what is typed as Markdown and escapes
  punctuation that Markdown would act on, including `(`, `)`, `*`, `_`, `[`,
  `]`, `{`, `}` and `|` (`plain_text_to_markdown`, checked 2026-11-20:
  "(hereinafter the proprietor)" is stored as `\(hereinafter the
  proprietor\)`). The formatted view hides the backslashes, but copying from
  it probably brings the hidden characters along (to confirm: Tk includes
  elided text when copying unless `get -displaychars` is used)
- **Not reproduced:** the misplaced `proprietor\**)` suggests the bold button
  put its closing marker next to an escaped character; reproduce it with the
  pure formatting functions of T-045 before changing anything

- [ ] **Copy** and **Cut** from the formatted view put the visible text on the
      clipboard (no backslashes, no markers), with an option to "Copy as
      stored text" for people who want the Markdown
- [ ] **Paste** of plain text is escaped as typed text; pasting text that
      already has `**bold**` or `\(` asks nothing and keeps it readable
- [ ] Reproduce the bold-next-to-escape case, fix it, and add a test that
      toggling bold on a word next to `(` or `)` never moves a backslash or a
      marker (shares code with T-045)
- [ ] The raw-text view says what it shows ("Stored text: backslashes here are
      normal")
- [ ] Hand check on Windows: copy from the editor into Word and into an email

**Done when:** text copied from the editor reads exactly as shown, and bold or
italic never leaves a stray backslash.

### T-035 Make the size gate complete and periodic

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** —

The size gate measures the real release executable (T-027), and since T-019-H
it also builds a comparison executable that includes the component-builder
modules. Two weaknesses found 2026-11-20:

- **The comparison build lists modules by hand** (`--hidden-import` for
  `md_parse`, `markdown_fields`, `shell_check`, `md_to_word`,
  `docx_compose`, `library`, `component_editor` and `component_preview`). It
  still omits `docx_to_markdown`, `markdown_files` and `shell_selection`
  unless something imports them, and each new module has to be added by
  someone remembering to.
- **Its "added size" is measured against a baseline that already contains
  most of the component stack.** PyInstaller finds the editor's imports even
  though the app loads them lazily, so the release build is already
  17,975,160 bytes (PR #36) against v0.3.1's 17,800,891, and the "with"
  build adds only 30,359 bytes. On `main` after PR #41 it reads -148 bytes
  (run 44798337642: 18,093,944 without, 18,093,796 with): the figure is
  meaningless. Compare against the last published release instead. Growth
  since 0.3.1 (17,800,891) is 293,053 bytes, 0.28 MiB.
- **It only runs when someone pushes.** The build installs `pyinstaller` and
  `lxml` unpinned (`--upgrade`), so a new upstream release can grow the
  executable with no commit and no red build until the next push.

- [ ] A small script (for example `scripts/list_app_modules.py`) lists every
      top-level application module, excluding tests, scripts, `app.py` and
      `advanced_app.py`; CI passes that list to the comparison build as
      `--hidden-import`s instead of the hand-written list
- [ ] A test fails when a new top-level module is added that the script does
      not pick up (so a mistake cannot hide a module from the gate)
- [ ] Add a `schedule:` trigger (weekly, on `main`) and `workflow_dispatch`
      to the workflow so the Windows size job runs without a push; make it
      fail visibly
- [ ] Print the versions of Python, PyInstaller and lxml in the size summary.
      Decide whether to pin them; if pinned, say how they get upgraded
- [ ] Add the headroom to the job summary for the release build, and fail
      when headroom falls under 3 MiB with a clear message ("tell Beaux")
- [ ] Update CLAUDE.md "Working on it" with the size rule and where the
      numbers appear
- [ ] **CI cost** (found 2026-11-20): every push to a pull request runs the
      Windows build and both macOS builds. Run the macOS builds only on
      `main`, tags and manual runs (and on a PR that touches `build-mac.command`,
      `requirements.txt` or the workflow); run the Windows build on a PR only
      when `*.py`, `requirements.txt`, the build scripts, the workflow or
      `THIRD-PARTY-LICENSES.txt` change; add a `concurrency` group that
      cancels superseded runs on a PR. Check no branch rule requires the
      skipped jobs, and that the release job still waits for macOS on `main`

**Done when:** adding an invented dummy module makes it appear in the
comparison build; a scheduled run is visible in the Actions list; the
current numbers are in the Progress log. This task's own size gate: it adds
no executable code, only CI.

### T-036 Housekeeping: stale branches and legacy code

- **Status:** open, needs Beaux's decisions (found 2026-11-20)
- **Size:** S
- **Agent:** human (decisions and branch deletion); an agent can do the code
  removal once Beaux agrees
- **Needs:** Beaux

Repository clutter that no task owns. Nothing here is urgent; it makes the
project easier to read and the Actions and branch lists shorter.

- [ ] **Delete 22 merged remote branches** (every one is already in `main`):
      `ccr-9076da7d-zvifun`, `chatgpt/t-012-t-017-t-019b`,
      `chatgpt/t-014-sample-output-path`, `chatgpt/t-015-release-031`,
      `chatgpt/t-019-a-field-protection-spike`,
      `chatgpt/t-020-bcd-docx-import`, `chatgpt/t-020-e-import-warnings`,
      `chatgpt/t-020g-t-028`, `chatgpt/t-026-word-shell-contract`,
      `claude/contract-template-builder-j7njxm`,
      `claude/kind-keller-847k6d`, `docs/contract-component-builder-direction`,
      `feature/publisher-profiles`, `fix/publisher-address-commas`,
      `fix/reliable-windows-release-assets`,
      `fix/windows-python-install-manager-detection`,
      `task/t-005-windows-script-ci-checks`,
      `task/t-006-clean-stale-update-download`,
      `task/t-007-template-author-guide`, `task/t-019-d-e-lists-tables`,
      `task/t-019-d-e-lists-tables-verified`, `task/t-019-h-size-measurement`.
      To stop it recurring: on the repository page click the **Settings** tab
      (top row, far right; only an owner or admin sees it), stay on
      **General**, scroll a long way down to the **Pull Requests** section
      (below "Allow merge commits / squash / rebase"), and tick
      **Automatically delete head branches**. That only affects pull requests
      merged afterwards. The branches listed here must be deleted by hand:
      repository page > **Branches** > **All branches**, then the bin icon at
      the right of each row. (Deleting a branch does not remove its pull request
      or commits, so T-018 is unaffected.)
- [ ] **Look at two unmerged branches:** `task/t-019-d-e-lists-tables-final`
      holds one commit (`940da90`, a size-measurement step) that appears to
      duplicate what PR #27 already put in `main`; delete it if so.
      `fix/windows-vc-runtime` bundles the Windows runtime DLLs. T-034 showed the
      error was not a missing runtime, so it is not needed for that; delete it
      or keep it for its own sake
- [ ] **Decide about the legacy window.** `advanced_app.py` (not packaged) and
      the spreadsheet and saved-answer code in `core.py` (`blank_sheet`,
      `read_sheet`, `batch`, `save_answers`, `load_answers`, `templates_in`,
      `load_settings`, `remember`) are used only by it and by tests. T-008
      said the batch workflow is not carried forward and the old file can be
      removed "when the legacy window is retired". If Beaux agrees now: remove
      it and those functions and their tests, drop `openpyxl` from
      `requirements.txt` and the CI test install, delete the README and
      CLAUDE.md rows, and keep `core.py`'s template behaviour untouched with
      the existing suite green. If not, leave it and say when to ask again
- [ ] **CLAUDE.md order** (agent, no decision needed; done in this review):
      the Decision log and Progress log were out of order, with several
      unbolded entries; they are now in date order, newest last

**Done when:** the branch list holds only `main` and branches with open
work, and the legacy-code decision is written in CLAUDE.md. Size gate: any
removal must leave the size check green.

### T-029 Component library backup, and Markdown export and import

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-021-E, T-020-G
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

Moved earlier than "Later" in the proposal: the library is the staff's
accumulated work, kept on one PC. Losing it must not be possible by accident.

- [ ] Export the whole library to one file (all components, versions,
      assemblies, in a documented format) and import it back, merging or
      replacing as the user chooses, with a plain-English summary first
- [ ] Export one component or all as `.md` files, with metadata in a header
      the importer understands
- [ ] A reminder after some weeks without a backup (setting, off by
      default is acceptable)
- [ ] Never include publisher profiles unless the user ticks it

**Done when:** a library exported, deleted and imported is identical.

### T-030 Check generated documents in real Word

- **Status:** open (package-level composition and numbering tests are complete; human verification remains)
- **Size:** S
- **Agent:** human
- **Needs:** T-019-F

Package-level tests cannot prove Word will open a file and show it
correctly.

- [ ] Beaux (or a colleague) opens documents generated from the test
      fixtures in Word on Windows, and on macOS if possible: no repair
      message, headings and tables right, numbering restarts, headers and
      footers present
- [ ] Record findings here; open a task for each fault, with the file
- [ ] Repeat after T-019-D (continuous lists) and T-031 (links)

### T-031 Hyperlinks in components (optional)

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-019-F, T-020-B
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

The proposal supports links "if they can be handled cleanly and safely". They
need relationship entries in the shell's package and a safe-URL rule, so they
are separate from T-019.

- [ ] Allow only `http`, `https` and `mailto` targets; anything else is
      shown as plain text with a warning
- [ ] Render as Word hyperlinks with the right relationship ids, never
      editing the shell file
- [ ] Import links from Word (T-020-B) and show them in the editor and
      preview (T-022)
- [ ] Tests, including a link whose text contains a field

**Done when:** a link survives import, storage and generation, and Word
opens it.

---

---

---

---

## Done tasks (kept until a month after they were done)

### T-037 Release 0.4.0 (the component builder)

- **Status:** done (2026-11-20, Beaux): merged in PR #42; CI on `main` green; v0.4.0 published with the Windows `.exe` (18,095,285 bytes) and both macOS zips, each with a SHA-256 digest. The hand check continues under T-038 and the restart error under T-039
- **Size:** S
- **Agent:** human (the decision to publish)
- **Needs:** Beaux
- **Size gate:** yes. Windows `.exe` on `main` before this release:
  18,093,944 bytes (17.26 MiB), headroom 12.74 MiB; v0.3.1 was 17,800,891, so
  the component builder added about 293,000 bytes (0.28 MiB)

What 0.4.0 adds for staff: the **Components** menu (write reusable wording
with a toolbar, table editor, field inserter and live preview; import a Word
file; keep every saved version), and **Build an assembly** (choose a Word
shell, pick and order components, tick optional ones, preview, save the
recipe, fill the fields once, create the Word document; review newer wording
before adopting it). The Word-template workflow is unchanged.

- [x] `version.py` raised to `0.4.0`; `CHANGES.txt` has a `## 0.4.0` section
      (CI refuses a release without it)
- [x] `USER-GUIDE.txt` gains "COMPONENTS AND ASSEMBLED CONTRACTS" and the
      shell section no longer says the workflow is "not available yet"
- [x] Open a pull request from the branch to `main`; wait for a green CI run
      at its latest commit (CI before merge)
- [x] Merge; confirm the `v0.4.0` release has the Windows `.exe` with a
      digest and both macOS zips
- [x] On a PC with 0.3.1 installed: the update was offered, downloaded and
      installed (Beaux, 2026-11-20), with the restart error of T-039; the
      rest of the hand check is T-038
- [ ] If a fault is found: fix as 0.4.1; do not edit the 0.4.0 release
- [ ] Progress log entry with the CI run number and the two size numbers

Known gaps to tell staff or accept: real-Word display of generated documents
is T-030 (not done); the install error from T-034 is unexplained; there is
no library backup yet (T-029), so tell staff the component library lives in
the same per-user file as publisher profiles and should be copied if the PC
is replaced.

### T-034 Find out what the install error message said

*Resolved 2026-11-20: Beaux sent a screenshot of the message ("Failed to load Python DLL", a path under `AppData\Local\Temp\_MEI...`, `python311.dll`, "The specified module could not be found"). It is the inherited-temporary-folder problem described in T-039, not a missing Windows runtime, so `fix/windows-vc-runtime` is not the fix (T-036 asks Beaux whether to delete it). Left open from T-034's list: whether SmartScreen warned after the self-update, now in T-038.*

- **Status:** done (2026-11-20): the message was "Failed to load Python DLL ... \_MEI...\python311.dll ... The specified module could not be found", on both updates; cause and fix are T-039
- **Size:** S
- **Agent:** human
- **Needs:** Beaux

During T-002 (2026-11-19) Beaux saw an error message while installing. The
app ran normally afterwards, so it is not urgent, but the message could be
from the Windows build, the self-update swap, or SmartScreen, and staff will
see it too.

- [ ] **Unmerged branch to look at first:** `fix/windows-vc-runtime` (Beaux,
      2026-11-19 07:15, one commit, "Bundle the Python MSVC runtime in
      Windows builds", changes `build-windows.ps1` only). It was made the
      morning of the T-002 test and is not merged or mentioned anywhere. If
      the message was about a missing runtime DLL (for example
      VCRUNTIME140), that branch may be the fix. Decide: merge, or delete
      it. Check any change with the size gate, since it adds files
- [ ] Beaux records exactly what it said (a screenshot or the words), which
      step it came at (running the downloaded `.exe`, the update, or
      `build-windows.bat`), and whether it appears every time
- [ ] If it came during the self-update, attach `build-log.txt`, or look for
      a `.exe.new` or batch file left beside the app
- [ ] Also answer: did SmartScreen warn after the 0.3.0 app updated itself
      to 0.3.1? (settles T-011's unconfirmed sentence)
- [ ] An agent then opens a fix task, or closes this as harmless with the
      reason written down


### T-020 Import Word content as Markdown

- **Status:** done (2026-11-20; A to G, last in [PR #39](https://github.com/RexBHavgreau/contractbuilder/pull/39))
- **Size:** umbrella of T-020-A to T-020-G
- **Agent:** careful
- **Needs:** T-019-A (the field-protection method), T-019-B

See PROPOSAL-001.md section 6. A new, isolated `docx_import.py` using
zipfile and lxml. Import is content conversion, never layout; the source
file is never changed.

**Done when:** a DOCX of supported mixed content becomes reviewable Markdown
in the right order, fields intact, and every unsupported structure reported.

#### T-020-F Round trip: DOCX, Markdown, DOCX

- **Status:** done (2026-11-20, [PR #39](https://github.com/RexBHavgreau/contractbuilder/pull/39))
- **Size:** S
- **Agent:** careful
- **Needs:** T-020-C, T-020-D, T-019-F

- [x] Test: import an invented DOCX, compose it into a shell, and check the
      text, order, tables and lists match the source
- [x] Test: a second import of the composed output gives the same Markdown
      (stable round trip for the supported subset)

**Done when:** both round-trip tests pass.

### T-022 In-app component editor

- **Status:** done (2026-11-20; A to G in PRs #34, #36 and #39). GUI parts are covered only by pure-function tests in CI; the manual check is T-037
- **Size:** umbrella of T-022-A to T-022-G
- **Agent:** careful
- **Needs:** T-021-E, T-019-A

See PROPOSAL-001.md section 5. This was the largest, riskiest item, so it is
now small steps. **Choice made here:** the editor remains Markdown-backed. The Tkinter Text widget uses elided syntax and basic text tags for a formatted editing surface, with an optional raw-source view; the separate preview shows structure only, not Word pagination or final layout.

**Done when:** a user who does not know Markdown can create, import, edit and
save a component, with tables and fields, and see how it will look.

#### T-022-C Formatting toolbar

- **Status:** done (2026-11-20, [PR #39](https://github.com/RexBHavgreau/contractbuilder/pull/39))
- **Size:** M
- **Agent:** careful
- **Needs:** T-022-B
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] Buttons for heading, bold, italic, bulleted list, numbered list,
      indent and outdent; they wrap, prefix or re-indent the selection and
      write Markdown the user need not see. Indent and outdent move a
      numbered item down or up a level (1. becomes 1.1); the user never types
      indentation
- [x] The preview (T-022-B) shows the computed outline numbers (1., 1.1,
      1.1.1), not the digits stored
- [x] Keyboard shortcuts for bold and italic
- [ ] Works when the editing area shows the formatted preview and when it
      shows source (T-022-F). *Not checked by Claude on 2026-11-20: it needs a
      display; it is on the manual checklist in T-037*

#### T-022-D Table editor

- **Status:** done (2026-11-20, [PR #39](https://github.com/RexBHavgreau/contractbuilder/pull/39))
- **Size:** M
- **Agent:** careful
- **Needs:** T-022-B
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] A dialog with a grid: add or remove rows and columns, type cell text,
      mark the header row; produces the Markdown table without the user
      typing pipes
- [x] Opening an existing table in the editor (round trip)
- [x] A literal pipe or a field with a pipe in a cell is handled as in
      T-019-A

#### T-022-E Insert a field

- **Status:** done (2026-11-20, [PR #39](https://github.com/RexBHavgreau/contractbuilder/pull/39))
- **Size:** S
- **Agent:** any
- **Needs:** T-022-A
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] A button listing field names already used in the library and
      publisher-profile fields, and the formats, inserting `{{Name}}` or
      `{{Name | format}}`
- [x] Uses `core`'s own field parser to read and check names; do not write a
      second parser. A malformed `{{` is flagged in plain English

#### T-022-F Source view toggle

- **Status:** done (2026-11-20, [PR #39](https://github.com/RexBHavgreau/contractbuilder/pull/39))
- **Size:** S
- **Agent:** any
- **Needs:** T-022-A
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] An "Advanced: show raw text" switch that shows the Markdown, kept off
      by default and described plainly

#### T-022-G Import review dialog

- **Status:** done (2026-11-20, [PR #39](https://github.com/RexBHavgreau/contractbuilder/pull/39))
- **Size:** M
- **Agent:** careful
- **Needs:** T-022-B, T-020-F (round-trip acceptance test is included on this branch)
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] "Import from a Word file": choose a `.docx`, see the converted result
      in the preview with the warnings listed above it in plain English
- [x] The user can fix text, then save as a component, or cancel; nothing is
      saved before they agree
- [x] The source file is not modified

### T-023 Component library and assembly builder

- **Status:** done (2026-11-20; subtasks A–D in [PR #40](https://github.com/RexBHavgreau/contractbuilder/pull/40), subtask E in [PR #41](https://github.com/RexBHavgreau/contractbuilder/pull/41))
- **Size:** umbrella of T-023-A to T-023-E
- **Agent:** careful
- **Needs:** T-021-E, T-026

See PROPOSAL-001.md section 3B.

**Latest size gate result (CI run #227):** the release executable is
18,090,846 bytes (17.25 MiB); the component-enabled measurement build is
18,094,048 bytes (17.26 MiB), an increase of 3,202 bytes (under 0.01 MiB).
It leaves 13,363,232 bytes (12.74 MiB) below the 30 MiB limit. No runtime
dependency or bundled data file was added.
[CI run #227](https://github.com/RexBHavgreau/contractbuilder/actions/runs/44797646135).

**Done when:** a user can choose a shell, add, order, include or omit
components, review the result, fill the fields once, and create the
document.

#### T-023-A Library browser

- **Status:** done (2026-11-20, [PR #40](https://github.com/RexBHavgreau/contractbuilder/pull/40))
- **Size:** M
- **Agent:** careful
- **Needs:** T-021-E
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] List by category and tag, with search by name and wording; archived
      components hidden unless asked for
- [x] Open a component in the editor (T-022-A); see its version history

#### T-023-B Choose a shell

- **Status:** done (2026-11-20, [PR #40](https://github.com/RexBHavgreau/contractbuilder/pull/40); the checker and remembering
  were added 2026-11-19 in `shell_selection.py`)
- **Size:** S
- **Agent:** any
- **Needs:** T-026
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] Pick a shell file: the picker dialog waits for the component window
      (T-023-A / T-022-A). `shell_selection.choose_shell(path)` is what it
      calls with the file the user picked.
- [x] Validate it with T-026's checker and show its plain-English findings
      (`shell_selection.describe`, lines for errors and for each warning).
- [x] Remember the last shell used, if it can be used (`last_shell()`); a
      shell with errors is not remembered and a damaged settings file is
      treated as nothing remembered.

#### T-023-C Build and order an assembly

- **Status:** done (2026-11-20, [PR #40](https://github.com/RexBHavgreau/contractbuilder/pull/40))
- **Size:** M
- **Agent:** careful
- **Needs:** T-023-A
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] Add components, move up and down, remove, and tick "include" to omit
      an optional component without removing it
- [x] A component can be added more than once only if the user chooses

#### T-023-D Review the assembled document

- **Status:** done (2026-11-20, [PR #40](https://github.com/RexBHavgreau/contractbuilder/pull/40))
- **Size:** S
- **Agent:** careful
- **Needs:** T-023-C, T-022-B
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] One preview of everything in order, fields highlighted

#### T-023-E Fill and generate

- **Status:** done (2026-11-20, [PR #41](https://github.com/RexBHavgreau/contractbuilder/pull/41))
- **Size:** M
- **Agent:** careful
- **Needs:** T-023-D, T-019-G
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] Compose to a temporary `.docx`, then show a separate field form using
      the existing field controls and engine, with one input per unique field
      across all components
- [x] Publisher profile loading as today; values shown for review before
      creating the document
- [x] Output named and saved as the template workflow does; the shell and
      temporary composed document cannot be overwritten
- [x] The existing template workflow's screen and generation path are
      unchanged; its tests stay green

### T-024 Saved assembly revisions and deliberate updates

- **Status:** done (2026-11-20; subtask A in [PR #40](https://github.com/RexBHavgreau/contractbuilder/pull/40), subtasks B–D in [PR #41](https://github.com/RexBHavgreau/contractbuilder/pull/41))
- **Size:** umbrella of T-024-A to T-024-D
- **Agent:** careful
- **Needs:** T-021-E, T-023-C

See PROPOSAL-001.md section 9.

**Done when:** a saved assembly reopens with the same versions, and newer
component versions are used only after the user reviews and chooses them.

#### T-024-A Save and reopen

- **Status:** done (2026-11-20, [PR #40](https://github.com/RexBHavgreau/contractbuilder/pull/40))
- **Size:** M
- **Agent:** careful
- **Needs:** T-023-C
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] Save an assembly (name, shell, components, order, included flags) as
      revision 1; reopen it and produce identical Markdown

#### T-024-B List newer versions

- **Status:** done (2026-11-20, [PR #41](https://github.com/RexBHavgreau/contractbuilder/pull/41))
- **Size:** S
- **Agent:** any
- **Needs:** T-024-A
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] On opening, show (not apply) which pinned components have newer
      versions; the assembly remains pinned until the user chooses an update

#### T-024-C Review and choose updates

- **Status:** done (2026-11-20, [PR #41](https://github.com/RexBHavgreau/contractbuilder/pull/41))
- **Size:** M
- **Agent:** careful
- **Needs:** T-024-B
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] A dialog showing, per component placement, pinned and newer wording
      with additions and removals marked in a unified diff
- [x] The user ticks which placements to update and selects the target
      version; saving creates a new revision and leaves earlier revisions
      unchanged and available to reopen

#### T-024-D Reproducibility tests

- **Status:** done (2026-11-20, [PR #41](https://github.com/RexBHavgreau/contractbuilder/pull/41))
- **Size:** S
- **Agent:** any
- **Needs:** T-024-C
- **Size gate:** yes. Say what this adds to the executable and confirm the CI size result before done (see Size gate).

- [x] Revise a component twice; the saved revision still generates the old
      wording; an updated revision generates the explicitly selected new
      wording while unselected components remain pinned


## T-010 Finish going public: stop telling users the repository is private

- **Status:** done (2026-11-18, [PR #14](https://github.com/RexBHavgreau/contractbuilder/pull/14))
- **Size:** S
- **Agent:** any

Beaux made the repository public on 2026-11-17 (T-001), so update checks
need no token. But the app and the documents still say it is private, and
still steer people to a token they do not need:

- `simple_app.py`, `update_settings()`: the window opens with "This app's
  GitHub repository is private, so GitHub only shows its releases to someone
  signed in…".
- `simple_app.py`, `_finish_update_check()`: comment about a private
  repository; the status line "Automatic updates are not set up yet" can now
  only appear for the wrong reason.
- `update_checker.py`: module docstring, and the 404 message "This
  repository is private, so the app needs a read-only GitHub token…". A 404
  now means no release has been published (or the repository was renamed).
- USER-GUIDE.txt: the whole "PRIVATE REPOSITORY" section.
- README.md: "Private-repository update checks".
- BUILD-NOTES.txt: "PRIVATE REPOSITORY".
- CLAUDE.md: the Layout row for `self_update.py` ("stores the per-user
  update token"; it is now optional).

Keep the token setting itself (it still raises GitHub's limit; see T-012),
but present it as optional.

- [x] Reword the Update settings window: a token is not needed; it is only
      for someone who sees "GitHub is limiting update checks" often
- [x] 404 with no token: "GitHub has no published release for this app yet,
      or the repository has moved." Keep the `needs_token` flag off for it, so
      startup stays quiet
- [x] Remove or rewrite the four document sections above; the guide should
      not mention tokens except as the optional setting
- [x] Update `tests/test_updates.py` for the new 404 wording, and keep a test
      that a 404 with a saved token still names the token as a possible cause
- [x] CLAUDE.md: the pitfall was already corrected on 2026-11-18; once the
      wording is gone, delete its sentence "Text saying so is being removed"

**Done when:** `git grep -n -i -E "repository is private|private repositor|is private, so" -- '*.py' '*.txt' README.md ':!tests'`
finds nothing, and all tests pass. (Test names and CLAUDE.md's history notes
may still say "private"; they describe the past.)

## T-011 Tell users what Windows and macOS will say about an unsigned app

- **Status:** done (2026-11-18, [PR #14](https://github.com/RexBHavgreau/contractbuilder/pull/14))
- **Size:** S
- **Agent:** any

Beaux decided not to sign the app (T-009). So the first time each person
runs a downloaded copy, Windows SmartScreen shows "Windows protected your
PC", and macOS refuses to open it. Nothing in USER-GUIDE.txt or README.md
says so, and staff will reasonably think something is wrong.

- [x] USER-GUIDE.txt, near the start: a short "FIRST RUN" section.
      Windows: click More info, then Run anyway. macOS: right-click (or
      Control-click) the app, choose Open, then confirm. Once per computer.
- [x] README.md: one line under "Build and releases" pointing at it
- [x] Added the Windows update caveat as "should not" and explicitly marked it
      unconfirmed. T-002 ran 2026-11-19 but did not say whether SmartScreen
      warned after the self-update: ask Beaux, then keep or change the
      sentence in USER-GUIDE.txt

**Done when:** a colleague who has never seen the app can get it open on
Windows from the guide alone.

## T-012 Cope with GitHub's limit on unsigned update checks

- **Status:** done (2026-11-18, [PR #15](https://github.com/RexBHavgreau/contractbuilder/pull/15))
- **Size:** M
- **Agent:** any
- **Needs:** do it after T-010 if both are in progress (same file)

Now that checks go to GitHub without a token, GitHub allows 60 of them an
hour from one internet address. Everyone in an office usually shares one
address, and the app checks at every start, so a busy morning can use that
up. GitHub then answers 403 with the header `X-RateLimit-Remaining: 0`.
Today `update_checker.py` turns any 403 into "GitHub denied the update
check. Check the token in Help > Update settings (it may have expired)…",
which is wrong when there is no token.

- [x] In `check_for_update`, tell a rate-limit 403 or 429 (header
      `X-RateLimit-Remaining` is `0`, or a `Retry-After` header is present)
      from other refusals. Message: "GitHub is limiting update checks from
      your network for now. The app will try again later." It is not
      `needs_token`
- [x] At startup, check at most once a day per user: store the time of the
      last successful check beside `update-settings.json` (see
      `self_update.settings_path()`) and skip the automatic check if it is
      under 24 hours old. Help > Check for updates always checks
- [x] Automatic checks that hit the limit stay silent: no dialog, no status
      line
- [x] Tests with a fake `urlopen` for: rate-limit 403, ordinary 403, and
      the once-a-day skip (with a fixed clock, not real time)

**Done when:** the tests pass, and a rate-limited automatic check shows
nothing while a rate-limited manual check shows the message above.

## T-014 Stop tests/sample.py pointing at the deleted examples folder

- **Status:** done (2026-11-18, [PR #14](https://github.com/RexBHavgreau/contractbuilder/pull/14))
- **Size:** S
- **Agent:** any

Beaux deleted `examples/` from the repository on 2026-11-17. The tests do not
need it (they build their sample template in a temporary folder), but
`tests/sample.py` still says it builds `examples/Sample Services
Agreement.docx` "handed to the department as a worked example", and running
it directly would recreate the deleted file.

- [x] Update the docstring: it builds the sample template the tests use
- [x] Make `python tests/sample.py` write to a path given on the command
      line, or to the current folder, never to `examples/`
- [x] Add `examples/` to `.gitignore`, so a sample is not committed back by
      accident
- [x] Checked all tracked text files: no live code or user documentation depends on the deleted directory. The remaining matches are historical task/project notes and `core.py`'s unrelated `EXAMPLES` field-preview mapping.

**Done when:** `python tests/sample.py` no longer recreates `examples/`, and
all tests pass.

## T-015 Release 0.3.1 to prove self-update end to end

- **Status:** done (2026-11-18, [PR #17](https://github.com/RexBHavgreau/contractbuilder/pull/17))
- **Size:** S
- **Agent:** any
- **Needs:** T-010, T-011 and T-012 merged (so the release carries them)

Self-update has only been tested piecewise on Linux. The first real test is
a 0.3.0 app updating itself to a newer release, and the changes above are
worth releasing anyway.

- [x] Raise `APP_VERSION` in `version.py` to `0.3.1`, in its own pull request
- [x] After merging, confirm CI publishes the v0.3.1 release with
      `Word-Template-Filler-windows-x64.exe` attached and a `digest` on it
      (the updater checks it)
- [x] Hand over to Beaux for T-002's last step

Checked 2026-11-19: the v0.3.1 release has `Word-Template-Filler-windows-x64.exe`
(17,800,891 bytes, with a SHA-256 digest) and both macOS zips. T-002's last
step is now Beaux's.

**Done when:** the v0.3.1 release exists with all three files.

## T-002 Confirm the 0.3.0 fixes on a real Windows PC

- **Status:** done (2026-11-19, Beaux)
- **Size:** S
- **Agent:** human
- **Needs:** —

Revised 2026-11-18: the repository is public, so no token is needed, and
the token step has been removed.

- [x] CI run for the merge is green, and the GitHub release `v0.3.0` exists
      with `Word-Template-Filler-windows-x64.exe` attached (checked
      2026-11-18: run 44 green; the release also has both macOS builds, each
      with a SHA-256 digest)
- [x] On Beaux's PC, `build-windows.bat` builds `dist\Word Template Filler 0.3.0.exe`;
      `build-log.txt` reads as normal text (no "L o o k i n g") and lists
      Python 3.14 as `accepted`
- [x] Download `Word-Template-Filler-windows-x64.exe` from the v0.3.0
      release page and run it once. Note whether SmartScreen warns (T-011)
- [x] Help > Check for updates says 0.3.0 is the latest, with no token set
- [x] When v0.3.1 is out (T-015): the 0.3.0 app offers it, downloads it,
      closes and reopens as 0.3.1 (title bar shows 0.3.1). Note whether
      SmartScreen warns this time; tell whoever does T-011
- [x] Record the result in CLAUDE.md's Progress log; open a task for anything
      that failed, with `build-log.txt` or a screenshot
Report 2026-11-19: Beaux ran it on his PC. Everything checks out except there was an error message on install, but it did not affect the running of the application. The message is not yet recorded: T-034. Whether SmartScreen warned after the app updated itself was not reported either; T-011's sentence about that stays marked unconfirmed until Beaux says.

## T-008 Decide what to do with advanced_app.py

- **Status:** done (2026-11-18, collaboratively by Beaux and ChatGPT; see [PROPOSAL-001.md](PROPOSAL-001.md))
- **Size:** S
- **Agent:** human
- **Needs:** —

Beaux chose to keep the packaged application focused while adding a second,
component-based way to create contracts. The component builder is a new
workflow, not a replacement for the existing Word-template workflow.

Decisions:

- [x] **Do not merge `advanced_app.py` wholesale.** `simple_app.py` remains
      the packaged application and its current template workflow remains
      intact.
- [x] **Do not carry spreadsheet batch creation forward.** A spreadsheet is
      not the intended interface for assembling new contracts. Leave the old
      implementation un-packaged; it can be removed when the legacy window is
      retired.
- [x] **Keep saved-answer and contract-to-template code in the legacy file
      for now.** Neither is part of the first component-builder milestone.
      Revisit each separately if there is a concrete need to bring it into
      the packaged application.
- [x] **Build a component-based workflow as a separate option.** Users will
      create and manage components inside the application. Their content
      will be Markdown, stored as text in the local SQLite database with
      metadata and version history. Markdown files may be imported/exported,
      but individual components will not be stored as Word documents.
- [x] **Use a Word document shell for document-level formatting.** The shell
      supplies page layout, styles, headers and footers. The application
      assembles selected Markdown components in order, converts them to Word
      content, then uses the existing field engine to collect and populate
      `{{fields}}`.
- [x] **Make component updates deliberate.** Saved assemblies retain the
      versions they were built with. Users can review and explicitly update
      selected components to newer versions; updates never silently change
      an existing assembly.
- [x] **Keep the two creation workflows independent.** Template-based
      creation continues to use the existing `.docx` template and custom
      fields exactly as it does now. The component builder is an additional
      route to a new contract.

**Done when:** these choices are recorded in CLAUDE.md and the next
implementation task is defined. T-019 covers the first technical proof:
converting ordered Markdown content into a formatted Word document shell.

### T-019 Prototype Markdown-to-Word composition

- **Status:** done (2026-11-20; subtasks A to H all done, last in [PR #27](https://github.com/RexBHavgreau/contractbuilder/pull/27))
- **Size:** umbrella of T-019-A to T-019-H
- **Agent:** careful
- **Needs:** T-008 (done)

See PROPOSAL-001.md sections 4, 7, 8, 10 and 11. Python-native only: no
Pandoc, no python-docx. All code goes in new modules; `core.py` is read, not
changed (T-019-A may propose a small, tested addition if hand-off needs it).

**Done when:** tests generate a valid DOCX from several ordered Markdown
components and a shell, with native tables, the shell's formatting intact,
and placeholders in paragraphs and table cells filled by the existing core
engine; and the Windows executable is still within 30 MB.

#### T-019-A Spike: protect fields from Markdown, and hand off to core

- **Status:** done (2026-11-18, [PR #19](https://github.com/RexBHavgreau/contractbuilder/pull/19))
- **Size:** M
- **Agent:** careful
- **Needs:** —

The two biggest unknowns, settled before anything is built on them. Write
the findings as a short section in this file's notes for T-019 (or a
`docs/` note) and tick the boxes.

- [x] Show how `{{...}}` text behaves in markdown-it-py (tables enabled):
      underscores and asterisks inside names (`{{First_Name}}`), the pipe in
      `{{Fee | money-words}}` inside a table cell (the parser reads `|` as a
      column break), `{{#if X}}` and `{{/if}}` alone on a line, inside a list
      item, inside a table cell, and spanning two components
- [x] Choose and prove a protection method (for example: swap every
      `{{...}}` span for a placeholder token before parsing, and restore it
      as literal text in one run afterwards). It must handle every case above
- [x] Prove the hand-off: take a hand-built generated document, open it with
      `core.Template` and `core.render`, and fill a field in a paragraph, a
      list item and a table cell. Note what `core.read_parts` needs (path on
      disk or in-memory) and whether each field ends up in one clean run
- [x] Record whether any `core.py` change is needed. If so, make it a
      separate, tiny, tested change with the whole existing suite green

**Done when:** each case above has a passing throwaway test and a written
answer; T-019-C to T-019-G build on that method.

#### T-019-B Add the dependency and the configured parser

- **Status:** done (2026-11-18, [PR #15](https://github.com/RexBHavgreau/contractbuilder/pull/15))
- **Size:** S
- **Agent:** any
- **Needs:** —

- [x] Add `markdown-it-py` (pin an exact version, plus `mdurl`) to the
      project's requirements and to the PyInstaller build and CI install
      steps (`build.yml`, `build-windows.ps1`, `build-mac.command`)
- [x] New module (for example `md_parse.py`) returning a parser with the
      table rule explicitly enabled
- [x] Test that tables really are on (a pipe table yields table tokens) and
      that raw HTML is not rendered (disable it: contract text is not HTML)
- [x] Keep `import` of the new module out of `simple_app.py` until a task
      needs it

**Done when:** tests pass, and the Windows and macOS CI builds still build.

#### T-019-C Render paragraphs, headings and inline emphasis

- **Status:** done (2026-11-18, [PR #19](https://github.com/RexBHavgreau/contractbuilder/pull/19))
- **Size:** M
- **Agent:** careful
- **Needs:** T-019-A, T-019-B, T-026 (shell style names)

- [x] New module `md_to_word.py` turns parser tokens into WordprocessingML
      paragraphs and runs with lxml
- [x] Paragraphs, hard line breaks, headings 1 to 3 (shell styles from T-026),
      bold, italic and combined bold/italic
- [x] Field text preserved as in T-019-A, including inside bold and italic
- [x] Unsupported inline constructs produce warnings and retain readable
      text where possible; unsupported block constructs, including lists,
      tables and code blocks, produce warnings rather than being silently
      treated as supported content

**Done when:** tests check the XML of each construct and that styles come
from the shell, not hard-coded fonts. (Done.)

#### T-019-D Render lists with native Word numbering

- **Status:** done (2026-11-19, [PR #27](https://github.com/RexBHavgreau/contractbuilder/pull/27))
- **Size:** M
- **Agent:** careful
- **Needs:** T-019-C, T-026 (T-025 is decided; see it)

- [x] Bulleted and numbered lists, including nested lists, as real Word
      numbering (`w:numPr`), never typed numbers
- [x] Use the shell's numbering definitions (T-026); add native Word
      numbering instances and preserve bullet-list behavior
- [x] **Continue clause numbering across the assembled document.** Every
      ordered list uses one shared decimal `w:num` instance, so the sequence
      continues across separate lists, components, paragraphs and tables.
      No per-component restart setting is exposed.
- [x] Implement T-025's decision: nested ordered lists become one
      multi-level decimal outline (1., 1.1, 1.1.1) with at least three
      levels; position in the nesting decides the number, not the digits
      typed in the Markdown; read each level's format from the shell's
      definition rather than hard-coding it
- [x] A continuation paragraph indented under a list item stays with that
      clause, unnumbered
- [x] Tests: nested levels, typed digits ignored, moving items renumbers,
      fields in list items, continuation paragraphs, and continuous numbering
      across component/list boundaries

**Done when:** the assembled DOCX uses one shared decimal numbering
instance for every ordered clause list; tests inspect the paragraph
references and numbering definition. Real Word display is checked separately
under T-030.

#### T-019-E Render tables

- **Status:** done (2026-11-19, [PR #25](https://github.com/RexBHavgreau/contractbuilder/pull/25))
- **Size:** M
- **Agent:** careful
- **Needs:** T-019-C, T-026

- [x] GFM tables as native `w:tbl` with header row marked, column count
      consistent, and the shell's table style
- [x] Inline emphasis and fields inside cells; the pipe case from T-019-A
- [x] Column alignment from the Markdown (`:---`, `:---:`, `---:`) where the
      shell allows
- [x] Empty cells are valid (a cell needs a paragraph)

**Done when:** tests check structure and that a `{{Fee | money-words}}`
inside a cell survives and is fillable.

#### T-019-F Compose the document from a shell

- **Status:** done (2026-11-19, [PR #25](https://github.com/RexBHavgreau/contractbuilder/pull/25))
- **Size:** M
- **Agent:** careful
- **Needs:** T-019-C, T-019-D, T-019-E

- [x] Function taking a shell path, an ordered list of Markdown strings and
      an output path; writes a new `.docx`
- [x] Keep the shell's styles, headers, footers, page size, margins, section
      properties and relationships; replace only the body content, keeping
      the final `w:sectPr`
- [x] Order of components and of paragraphs and tables inside them preserved
- [x] The shell file is never opened for writing (test: byte-for-byte equal
      before and after)
- [x] The output has a correct content-types part and relationships, so
      Word opens it (package-level tests; the real-Word check remains T-030)

**Done when:** tests generate a document from three components and the
shell's formatting metadata is verified in the output.

#### T-019-G End-to-end through the field engine

- **Status:** done (2026-11-19, [PR #25](https://github.com/RexBHavgreau/contractbuilder/pull/25))
- **Size:** S
- **Agent:** any
- **Needs:** T-019-F

- [x] Test: compose, then `core.Template` finds the fields once each even if
      repeated across components, and `core.render` fills them in paragraphs,
      list items and table cells
- [x] Test: `{{#if X}}` blocks across components and inside cells, true and
      false (all four true/false combinations)
- [x] Test: formats (`money-words`, `date-formal`) work in the output

**Done when:** the end-to-end tests pass with the same invented values the
template workflow's tests use.

#### T-019-H Measure the release size

- **Status:** done (2026-11-19, [PR #27](https://github.com/RexBHavgreau/contractbuilder/pull/27))
- **Size:** S
- **Agent:** careful
- **Needs:** T-019-B, T-027

- [x] Build the Windows executable with and without the component-builder
      modules and record both sizes in the Decision log
- [x] Keep the component-enabled build at or below 30 MiB
      (31,457,280 bytes); record the remaining headroom

**Measurement (GitHub Actions run #166, Windows x64):** both executables use
`simple_app.py` as the entry point and the same one-file/windowed PyInstaller
configuration. The comparison build explicitly includes `md_parse`,
`markdown_fields`, `shell_check`, `md_to_word` and `docx_compose` so
PyInstaller cannot omit the component-builder stack merely because the
current application window does not import it yet.

- Without the component-builder modules: **17,801,283 bytes (16.98 MiB)**
- With the component-builder modules: **17,962,926 bytes (17.13 MiB)**
- Added bundled size: **161,643 bytes (0.15 MiB)**
- Headroom below 30 MiB with the modules included: **13,494,354 bytes
  (12.87 MiB)**

The margin is well above 3 MiB, so there is no immediate size pressure and
no next likely cost needs to be singled out. The Windows workflow retains
this side-by-side measurement and enforces the 30 MiB limit on the
component-enabled build as well as the release build.

**Done when:** both actual executable sizes are recorded and the
component-enabled executable passes the 30 MiB check.

### T-019 technical notes: field protection and hand-off

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

#### T-020-A Read the package and the body in order

- **Status:** done (2026-11-18, [PR #16](https://github.com/RexBHavgreau/contractbuilder/pull/16))
- **Size:** S
- **Agent:** any
- **Needs:** —

- [x] Open the `.docx` read-only; walk `w:body` children in document order,
      yielding paragraphs and tables as they come (never paragraphs then
      tables)
- [x] A result object holding Markdown text and a list of warnings (each
      with a plain-English message and where it was found)
- [x] A file that is not a valid `.docx` gives a plain-English error, not a
      stack trace

**Done when:** tests on an invented fixture show body order is kept.

#### T-020-B Paragraphs, headings and inline formatting

- **Status:** done (2026-11-19, [PR #28](https://github.com/RexBHavgreau/contractbuilder/pull/28))
- **Size:** M
- **Agent:** careful
- **Needs:** T-020-A

- [x] Heading styles to `#`..`###` (map by style id/name and outline level;
      deeper headings are reported, not dropped)
- [x] Bold and italic across split runs (Word splits runs freely; merge
      neighbours with the same formatting)
- [x] Escape Markdown characters in ordinary text so the round trip does not
      turn a literal `*` or `_` into emphasis
- [x] `{{Field}}` and `{{#if}}` text kept literal, even when it is split
      across runs (reuse `core`'s run-spanning logic where possible)
- [x] Underline, strikethrough, highlight, font and colour changes are
      reported as dropped formatting (these are out of scope, T-032)

**Done when:** tests cover split runs and a field split across three runs.

#### T-020-C Lists

- **Status:** done (2026-11-19, [PR #28](https://github.com/RexBHavgreau/contractbuilder/pull/28))
- **Size:** M
- **Agent:** careful
- **Needs:** T-020-B (T-025 is decided; see it)

- [x] Read `numbering.xml` to tell bulleted from numbered and find the
      nesting level
- [x] Convert lists per T-025: multi-level Word lists become nested ordered
      lists by level, whatever their numbering style; letter and Roman
      styles become decimal, with a warning saying so
- [x] Typed numbers that are not Word numbering (such as "1." typed by hand)
      are kept as text and flagged as possible list items

**Done when:** tests cover bullets, numbers, nesting and typed numbers.

#### T-020-D Tables

- **Status:** done (2026-11-19, [PR #28](https://github.com/RexBHavgreau/contractbuilder/pull/28))
- **Size:** M
- **Agent:** careful
- **Needs:** T-020-B

- [x] Rectangular tables to GFM tables; first row as header
- [x] Merged cells (horizontal or vertical), nested tables, and cells with
      more than one paragraph or a list are reported, with the best-effort
      text still included where it is safe
- [x] A literal `|` in cell text is escaped

**Done when:** tests cover a plain table, a merged-cell table, a cell with
two paragraphs, and a mixed paragraph-table-paragraph body.

#### T-020-E Warnings for everything else

- **Status:** done (2026-11-19, [PR #22](https://github.com/RexBHavgreau/contractbuilder/pull/22))
- **Size:** S
- **Agent:** careful
- **Needs:** T-020-A

- [x] Report images, drawings and floating shapes, equations, footnotes and
      endnotes, comments, tracked changes, content controls, section and
      page breaks, headers and footers (not imported, by design), and
      unusual Word fields
- [x] Tracked changes: report them and import the accepted text (final
      view), saying so
- [x] Never drop text silently: every dropped run is accounted for in a
      warning

**Done when:** one invented fixture per structure yields the expected
warning, and the warning text is plain English.

#### T-020-G Markdown file import and export

- **Status:** done (2026-11-18, [PR #16](https://github.com/RexBHavgreau/contractbuilder/pull/16))
- **Size:** S
- **Agent:** any
- **Needs:** T-019-B

- [x] Function pair to read a `.md` file (UTF-8, tolerate a BOM) and write
      one; the exported text re-imports with identical supported content
- [x] Unsupported Markdown (raw HTML, images, footnotes) reported on import

**Done when:** an export then import test passes unchanged.

### T-021 Unified local database: components, versions, assemblies

- **Status:** done (2026-11-20; subtasks A to E in [PR #29](https://github.com/RexBHavgreau/contractbuilder/pull/29) to [PR #33](https://github.com/RexBHavgreau/contractbuilder/pull/33))
- **Size:** umbrella of T-021-A to T-021-E
- **Agent:** careful
- **Needs:** —

See PROPOSAL-001.md section 9. **Choice made here:** extend the existing
`publisher_profiles.sqlite3` with new tables; do not rename or move it. No
user data migration is then needed. Add a schema version
(`PRAGMA user_version`) so later changes are safe. Beaux confirmed this
direction on 2026-11-20 when T-021-A was claimed.

**Done when:** the new tables exist, are tested, and an existing user's
publisher profiles are untouched.

#### T-021-A Schema version and safe upgrade

- **Status:** done (2026-11-20, [PR #29](https://github.com/RexBHavgreau/contractbuilder/pull/29))
- **Size:** S
- **Agent:** careful
- **Needs:** —

- [x] Add `PRAGMA user_version`; a database with no version is version 1
      (today's publisher schema)
- [x] Upgrade steps run in a transaction, after copying the file to
      `publisher_profiles.sqlite3.bak-<version>` once; the backup is kept
      until the upgrade has succeeded and been checked
- [x] Test: a database made by the current code upgrades and its publishers
      are identical; a failed step leaves the original unchanged
- [x] Test: an older app opening an upgraded database does not damage it
      (extra tables are ignored)

#### T-021-B Components and immutable versions

- **Status:** done (2026-11-20, [PR #30](https://github.com/RexBHavgreau/contractbuilder/pull/30))
- **Size:** M
- **Agent:** careful
- **Needs:** T-021-A

- [x] Tables `components` (id, name, description, category, tags, status)
      and `component_versions` (id, component_id, number, markdown, created,
      note)
- [x] Saving an edit always creates a new version; a version's Markdown is
      never updated (SQLite triggers reject updates/deletes; the API inserts
      the next number in a `BEGIN IMMEDIATE` transaction)
- [x] Categories and tags are free text; suggested categories are only
      suggestions

#### T-021-C Assemblies and revisions

- **Status:** done (2026-11-20, [PR #31](https://github.com/RexBHavgreau/contractbuilder/pull/31))
- **Size:** M
- **Agent:** careful
- **Needs:** T-021-B

- [x] Tables `assemblies`, `assembly_versions` (shell reference included)
      and `assembly_components` (component_version id, position, included
      flag)
- [x] A revision pins component version ids, never "latest"
- [x] Shell reference stores a path and a content hash, so a moved or
      changed shell is noticed (see T-026)

## T-021-D Archive instead of delete

- **Status:** done (2026-11-20, [PR #32](https://github.com/RexBHavgreau/contractbuilder/pull/32))
- **Size:** S
- **Agent:** careful
- **Needs:** T-021-B, T-021-C

- [x] Components and assemblies can be archived and restored; they are never
      hard-deleted while any assembly revision refers to them
- [x] Test: an assembly pinned to an archived component's version still
      generates the same Markdown

## T-021-E Storage module and tests

- **Status:** done (2026-11-20, [PR #33](https://github.com/RexBHavgreau/contractbuilder/pull/33))
- **Size:** S
- **Agent:** any
- **Needs:** T-021-B, T-021-C, T-021-D

- [x] A plain module (`library.py`) with the functions the UI
      will call: create/list/search components, save a version, create an
      assembly, save a revision, list newer versions available for a pinned
      revision. No Tkinter in it
- [x] Tests use a temporary database and invented data

#### T-022-A Editor window shell and save

- **Status:** done (2026-11-20, [PR #34](https://github.com/RexBHavgreau/contractbuilder/pull/34))
- **Size:** M
- **Agent:** careful
- **Needs:** T-021-E

- [x] A "Components" window, reached from the main window, separate from the
      template workflow; name, category and tags fields; Save makes a new
      version with an optional note
- [x] Unsaved-changes prompt in plain English
- [x] The existing template workflow's screen and menus are unchanged

#### T-022-B Preview

- **Status:** done (2026-11-20, [PR #36](https://github.com/RexBHavgreau/contractbuilder/pull/36))
- **Size:** M
- **Agent:** careful
- **Needs:** T-022-A, T-019-C

- [x] A read-only preview pane using Text widget tags: headings, bold,
      italic, lists, tables as aligned text, fields highlighted
- [x] Updates as the user stops typing (debounced), never blocks typing;
      refresh listens to Tk's modified event so paste, cut, undo and redo
      also update the preview
- [x] A line under it: "Word decides the final page layout"

### T-025 Decide clause numbering and legal formatting scope

- **Status:** done for numbering (2026-11-18, Beaux); extra formatting moved
  to T-032
- **Size:** S
- **Agent:** human
- **Needs:** Beaux

**Decision (Beaux, 2026-11-18): no new Markdown syntax.** Clause numbering is
a feature of the editor and the renderer, built on standard nested ordered
lists, which already carry the structure. ContractBuilder renders those
lists as a decimal outline (1., 1.1, 1.1.1). Recorded in CLAUDE.md's
Decision log. What it means:

- **Stored form:** an ordinary nested ordered list (`1.` items, with
  sub-items indented under their parent). The digits typed in the Markdown
  are not the numbers shown: position in the nesting decides them, so
  inserting or moving a clause renumbers everything.
- **Word output (T-019-D):** one multi-level numbering definition supplied
  by the shell (T-026), levels 1 to 3 at least, formatted as decimal
  outline ("1.", "1.1", "1.1.1"). Each separate list gets its own `w:num`
  so it restarts at 1. Plain bulleted lists remain bullets.
- **Clause text with more than one paragraph:** a continuation paragraph
  indented under its item belongs to that clause and is not numbered.
- **Editor (T-022):** users never type the indentation. The toolbar has
  "numbered list", "indent" (demote to 1.1) and "outdent". The preview shows
  the computed outline numbers, so users see what Word will show.
- **Import (T-020-C):** Word multi-level lists become nested ordered lists
  by level, whatever their original numbering style. Letter and Roman styles
  ((a), (i)) become decimal and the importer says so in a warning. Numbers
  typed by hand are kept as text and flagged.
- **Known limit:** a reference such as "see Section 2.1" typed into the
  wording does not update when clauses move. Say so in the guide; automatic
  cross-references are not in scope.

- [x] Decide how numbered clauses and sub-clauses are produced
- [x] Update T-019-D, T-020-C and T-022-C to match (done in this change)
- [ ] Open question for the guide, not a blocker: whether a shell may offer
      other level styles later (for example (a) at level 2). The renderer
      should read level formats from the shell's definition rather than
      hard-coding decimal, so this stays possible

Underline, page breaks, signature blocks and defined-term formatting:
out of scope (T-032).

**Done when:** the decision is in CLAUDE.md and the tasks above say what to
build. (Both done.)

### T-032 Decide extra legal formatting for components

- **Status:** done (2026-11-18, Beaux: it does not matter; out of scope)
- **Size:** S
- **Agent:** human
- **Needs:** —

**Decision (Beaux, 2026-11-18): underline, page breaks, signature blocks and
defined-term styling are not supported in components.** Components carry
paragraphs, headings 1 to 3, bold, italic, numbered outlines, bulleted lists,
tables, and fields. Notes for whoever builds on this:

- `_text_` and `*text*` mean *italic* in Markdown; there is no standard
  underline. An underlined passage in an imported Word file becomes plain
  text with a warning (T-020-B), not italic.
- A signature block is the area at the end of a contract where each party
  signs, with lines for signature, printed name, title and date, usually
  side by side. Put it in the Word **shell** or in a Word template, not in a
  component. (A simple two-column table can hold one if it is ever wanted.)
- Page breaks come from the shell and from Word's own flow.

Reopen this task only if staff find they cannot do without one of them.

- [x] Decided: all out of scope
- [x] CLAUDE.md Decision log updated

### T-033 Decide whether clause numbering continues across components

- **Status:** done (2026-11-19; Beaux's decision implemented in [PR #27](https://github.com/RexBHavgreau/contractbuilder/pull/27))
- **Size:** S
- **Agent:** human
- **Needs:** —

**Decision: option 1 — continue numbering across the whole assembled
document.** All ordered clause lists share one native Word numbering
instance. Clause numbers therefore continue across components and across
separate ordered lists, even when ordinary paragraphs or tables intervene.
There is no component-level restart option. Schedules and exhibits that need
different numbering will require a separately scoped future feature rather
than an undocumented Word-numbering side effect.

- [x] Beaux chooses; recorded in CLAUDE.md's Decision log
- [x] T-019-D implements and tests the decision
- [ ] T-030 checks the result in real Word on Windows and macOS if available

### T-026 Define the Word shell contract and ship a sample shell

- **Status:** done (2026-11-18, [PR #18](https://github.com/RexBHavgreau/contractbuilder/pull/18))
- **Size:** M
- **Agent:** careful
- **Needs:** —

The proposal says a shell supplies styles, numbering and table formatting,
but not what must be in one, nor what happens when something is missing.
Without a clear contract and a sample, the feature cannot be used on day one.

- [x] Write the plain-English user instructions and developer contract in
      `USER-GUIDE.txt` and `SHELL-CONTRACT.md`, covering canonical style IDs,
      table/list styles, numbering definitions and final section properties
- [x] Add `shell_check.py`, which reads a shell without changing it and
      returns plain-English errors and warnings with stable finding codes
- [x] Define explicit style fallbacks in the checker result; missing styles
      never pass silently. Missing numbering definitions are separately
      reported so the renderer can supply and disclose its fallback
- [x] Build the invented sample shell in the test fixture; no template file
      is committed. An in-app blank-shell creator remains a later UI task
- [x] Test a complete shell, each required style missing or mistyped, missing
      numbering definitions, absent final section properties, and byte-for-
      byte source preservation

**Done when:** the contract, checker, fallback rules and fixture tests are
implemented. T-019-C to T-019-F and T-023-B must call the checker before
using a shell, surface its warnings, stop on errors and apply its fallbacks.
This separates the prerequisite contract from the later integration work and
avoids making a prerequisite wait for the tasks that depend on it.

### T-027 Keep the Windows executable within 30 MB in CI

- **Status:** done (2026-11-18, [PR #14](https://github.com/RexBHavgreau/contractbuilder/pull/14))
- **Size:** S
- **Agent:** any
- **Needs:** —

The proposal's 30 MB target is checked by hand today. v0.3.0 is 17,795,673
bytes.

- [x] A CI step after the Windows build that fails if the executable is over
      31,457,280 bytes and prints the size and the margin otherwise
- [x] The step reads the size from the built file, not from wheels
- [x] Put the measured size in the CI log. Release-note inclusion is deferred
      until T-017 provides the project-owned release-notes mechanism.

**Done when:** a deliberately tiny limit fails CI and the real limit passes.

### T-028 Include third-party licence notices

- **Status:** done (2026-11-18, [PR #16](https://github.com/RexBHavgreau/contractbuilder/pull/16))
- **Size:** S
- **Agent:** any
- **Needs:** T-019-B

markdown-it-py and mdurl are MIT licensed; the notice must travel with the
app.

- [x] A `THIRD-PARTY-LICENSES.txt` with each package's name, version,
      copyright line and licence text (copy from the installed packages; do
      not invent the text)
- [x] Bundle it with the app (the PyInstaller `--add-data`, like the guide)
      and show it from Help
- [x] A test that fails when a runtime dependency has no entry

**Done when:** the file is in the packaged app and the test passes.

## T-017 Show plain-English release notes in the update dialog

- **Status:** done (2026-11-18, [PR #15](https://github.com/RexBHavgreau/contractbuilder/pull/15))
- **Size:** M
- **Agent:** any

When an update is offered, the dialog shows only version numbers. The
release notes GitHub writes by itself list pull-request titles such as
"Claude/contract template builder j7njxm", which mean nothing to staff.

- [x] Add a `CHANGES.txt` at the top of the repository: newest version first,
      a few plain sentences per version on what changed for the person using
      the app. Start it with 0.3.0 and 0.3.1
- [x] In `.github/workflows/build.yml`, publish that version's section as the
      release body (`body_path` on `softprops/action-gh-release`) instead of
      `generate_release_notes`
- [x] In `simple_app.py`, show the release body (already in
      `ReleaseInfo.notes`) under the version numbers in the update dialog,
      cut to about 15 lines
- [x] Add to CLAUDE.md's release instructions: raising `APP_VERSION` also
      means adding its section to `CHANGES.txt`; make CI fail if the section
      is missing
- [x] Tests for reading one version's section out of `CHANGES.txt`

**Done when:** the next release's page and its update dialog both say, in
plain English, what changed.

---


## T-013 Replace real contract details in the tests with invented ones

- **Status:** done (2026-11-18, Claude, as part of the T-016 history rewrite)
- **Size:** S
- **Agent:** any

- [x] The real publisher name, signatory, addresses, titles, book details,
      dates and amounts in `tests/test_core.py` were replaced with invented
      ones, in every commit, by the rewrite. The assertions still prove the
      same things (diacritics and capitals, curly and straight apostrophes,
      rounding), and all tests pass
- [x] No other real details are left in the current files, checked against
      the private list
- [x] CLAUDE.md says test data must be invented, and a test now enforces it
      (`tests/test_no_private_details.py`, active once T-018 sets the secret)

## T-016 Remove details of real contracts from the public history

- **Status:** done (2026-11-18, Claude; the push itself is T-018)
- **Size:** M
- **Agent:** careful
- **Needs:** Beaux (decided 2026-11-18: "removed permanently, even if that
  means rewriting history")

Making the repository public published its history too. Two old commits,
Build 2 (now `3fec39f`) and Build 4 (now `80cbe34`), and the first version
of this task list held names, an address, a title, a book's details and
amounts from real memoranda of agreement. 90 commits also recorded Beaux's
personal email address as their author.

- [x] Searched every file and commit message on all ten branches and three
      tags, including inside Word and Excel files, for 51 details recorded
      from the memoranda. 22 were present
- [x] Rewrote the history with `git filter-repo`: each detail replaced with an
      invented one; the email replaced with Beaux's GitHub "noreply" address,
      so GitHub still credits the commits to him
- [x] Checked the result: none of the 51 details in any file or message on
      any branch or tag; the email gone from all 97 commits; old and new `main`
      differ only in the replaced words; all tests pass on `main` and on this
      branch
- [x] Rehearsed the push against a stand-in copy of the repository
- [x] Pushed (T-018); only GitHub Support's purge is outstanding

Commit ids changed with the rewrite. The commit-id map is in the handover
folder (`commit-map.txt`), for anyone who needs to follow an old id.

## T-001 Decide how colleagues receive updates

- **Status:** done (2026-11-17, Beaux: made the repository public)
- **Size:** S to decide; M to carry out
- **Agent:** human (decision), then any

The repository was private, so GitHub hid its releases from anyone not
signed in, and each person had to paste a GitHub token into Help > Update
settings. Options were: make it public; publish releases to a separate
public repository; or keep per-user tokens.

- [x] Beaux chose option 1, making the repository public (2026-11-17, 21:40
      CST); recorded in CLAUDE.md's decision log on 2026-11-18
- [x] Carried out: confirmed public on 2026-11-18
- [ ] Update USER-GUIDE.txt "PRIVATE REPOSITORY" and README.md: moved to
      T-010, with the app's own wording that still says "private"

Follow-ups: T-010 (wording), T-012 (GitHub's limit on unsigned checks),
T-013 and T-016 (what being public exposes).

## T-003 Retire the empty v0.2.0 release

- **Status:** done (2026-11-17, Beaux)
- **Size:** S
- **Agent:** human

- [x] Deleted the v0.2.0 release on GitHub (checked 2026-11-18: only v0.3.0
      and v0.1.0 are listed)
- [x] Left the tag (checked 2026-11-18: `v0.2.0` is still there)

## T-004 Find out why the macOS Apple Silicon build kept getting cancelled

- **Status:** done (2026-11-18, cleared without a change)
- **Size:** M
- **Agent:** any

In CI runs 40 and 42 (2026-11-17) the "Build macOS Apple Silicon" job on
`macos-26` was cancelled after about 15 minutes.

- [x] Checked 2026-11-18: every push to `main` since run 44 (eleven runs,
      44 to 60) is green, and the job now takes under a minute. Nothing in the
      workflow changed for it, so the likely cause was a temporary shortage of
      `macos-26` runners on 2026-11-17. The logs of run 42 were not read.
- [ ] A fix was not needed. If it recurs, reopen this task: read that run's
      job log, then add `timeout-minutes: 20` to the job, or
      `continue-on-error: true` with the reason in a comment

**Done because** its own check (three consecutive green pushes to `main`)
was met eleven times over.

## T-005 Check the PowerShell build script in CI before building

- **Status:** done (2026-11-17, [PR #7](https://github.com/RexBHavgreau/contractbuilder/pull/7))
- **Size:** S
- **Agent:** any

- [x] Parse `build-windows.ps1` with
      `[System.Management.Automation.Language.Parser]::ParseFile(...)` under
      `powershell.exe` (5.1) and fail on any parse error
- [x] Fail if `build-windows.bat` lacks CRLF line endings

Verified 2026-11-18: the step "Validate Windows build scripts" runs first in
the Windows job; run 46, with a deliberately broken script, failed there.

## T-006 Clean up a leftover download if an update never started

- **Status:** done (2026-11-17, [PR #8](https://github.com/RexBHavgreau/contractbuilder/pull/8))
- **Size:** S
- **Agent:** any

- [x] At startup (Windows, built app only), delete a `<app>.exe.new` older
      than a day; leave a newer one, as a swap may still be running
      (`self_update.cleanup_stale_update_download`, called from `simple_app.py`)
- [x] Tested in `tests/test_updates.py`: age threshold, missing file, symlink

## T-007 Document how to build fields in a template, for template authors

- **Status:** done (2026-11-17, [PR #9](https://github.com/RexBHavgreau/contractbuilder/pull/9))
- **Size:** M
- **Agent:** any

- [x] "WRITING A TEMPLATE", "FORMATS", "OPTIONAL AND ALTERNATIVE WORDING" and
      "TEMPLATE CHECKS" sections in USER-GUIDE.txt, with examples checked by
      `test_template_authoring_examples_fill_a_real_word_template`
- [x] Help > How to write a template in `simple_app.py`
- [x] Plain wording

## T-009 Sign the Windows executable

- **Status:** done (2026-11-17, Beaux: decided not to sign)
- **Size:** M
- **Agent:** careful

- [x] Options weighed by Beaux: "not going to sign. too expensive to be worth
      it." Recorded in CLAUDE.md's decision log on 2026-11-18
- [ ] Signing in CI: not done, by decision

Follow-up: T-011 (tell users what the unsigned warnings look like).
