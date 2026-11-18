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

## Board

Reviewed 2026-11-18, revised for the component-builder proposal. Next free number: **T-033**.

| Task | What | Status | Agent | Needs |
| --- | --- | --- | --- | --- |
| [T-018](#t-018-push-the-cleaned-history-and-finish-the-clean-up) | Clean-up done except GitHub Support's purge | open, waiting for Support | human | GitHub Support |
| [T-010](#t-010-finish-going-public-stop-telling-users-the-repository-is-private) | Stop telling users the repository is private | done | any | — |
| [T-011](#t-011-tell-users-what-windows-and-macos-will-say-about-an-unsigned-app) | Explain the SmartScreen / Gatekeeper warnings | done | any | — |
| [T-012](#t-012-cope-with-githubs-limit-on-unsigned-update-checks) | Cope with GitHub's limit on update checks | done (2026-11-18, [PR #15](https://github.com/RexBHavgreau/contractbuilder/pull/15)) | any | — |
| [T-014](#t-014-stop-testssamplepy-pointing-at-the-deleted-examples-folder) | Tidy `tests/sample.py` after `examples/` was deleted | done | any | — |
| [T-015](#t-015-release-031-to-prove-self-update-end-to-end) | Release 0.3.1 to prove self-update end to end | open | any | T-010, T-011, T-012 |
| [T-002](#t-002-confirm-the-030-fixes-on-a-real-windows-pc) | Confirm the build and updates on a real Windows PC | open | human | T-015 for its last step |
| [T-008](#t-008-decide-what-to-do-with-advanced_apppy) | Decide the future of `advanced_app.py` | done | human | — |
| [T-025](#t-025-decide-clause-numbering-and-legal-formatting-scope) | Clause numbering: nested lists as decimal outline | done for numbering (2026-11-18) | human | — |
| [T-032](#t-032-decide-extra-legal-formatting-for-components) | Extra legal formatting (underline, page break, signature blocks): out of scope | done (2026-11-18) | human | — |
| [T-026](#t-026-define-the-word-shell-contract-and-ship-a-sample-shell) | Define the Word shell contract and checker | done (2026-11-18, [PR #18](https://github.com/RexBHavgreau/contractbuilder/pull/18)) | careful | — |
| [T-027](#t-027-keep-the-windows-executable-within-30-mb-in-ci) | Fail CI if the Windows executable passes 30 MB | done | any | — |
| [T-019](#t-019-prototype-markdown-to-word-composition) | Prototype Markdown-to-Word composition (umbrella) | open | careful | — |
| ↳ [T-019-A](#t-019-a-spike-protect-fields-from-markdown-and-hand-off-to-core) | Spike: protect fields from Markdown; hand off to core | open | careful | — |
| ↳ [T-019-B](#t-019-b-add-the-dependency-and-the-configured-parser) | Add markdown-it-py and the table-enabled parser | done (2026-11-18, [PR #15](https://github.com/RexBHavgreau/contractbuilder/pull/15)) | any | — |
| ↳ [T-019-C](#t-019-c-render-paragraphs-headings-and-inline-emphasis) | Paragraphs, headings, bold, italic | open | careful | A, B, T-026 |
| ↳ [T-019-D](#t-019-d-render-lists-with-native-word-numbering) | Lists as decimal outline, native numbering | open | careful | C, T-026 |
| ↳ [T-019-E](#t-019-e-render-tables) | Tables | open | careful | C, T-026 |
| ↳ [T-019-F](#t-019-f-compose-the-document-from-a-shell) | Compose the document from a shell | open | careful | C, D, E |
| ↳ [T-019-G](#t-019-g-end-to-end-through-the-field-engine) | End to end through the field engine | open | any | F |
| ↳ [T-019-H](#t-019-h-measure-the-release-size) | Measure the release size | open | careful | B, T-027 |
| [T-028](#t-028-include-third-party-licence-notices) | Third-party licence notices | claimed (ChatGPT, 2026-11-18) | any | T-019-B |
| [T-020](#t-020-import-word-content-as-markdown) | Import Word content as Markdown (umbrella) | open | careful | T-019-A, T-019-B |
| ↳ [T-020-A](#t-020-a-read-the-package-and-the-body-in-order) | Read the package and body in order | open | any | — |
| ↳ [T-020-B](#t-020-b-paragraphs-headings-and-inline-formatting) | Paragraphs, headings, inline formatting | open | careful | A |
| ↳ [T-020-C](#t-020-c-lists) | Lists | open | careful | B |
| ↳ [T-020-D](#t-020-d-tables) | Tables | open | careful | B |
| ↳ [T-020-E](#t-020-e-warnings-for-everything-else) | Warnings for everything else | open | careful | A |
| ↳ [T-020-F](#t-020-f-round-trip-docx-markdown-docx) | Round trip DOCX, Markdown, DOCX | open | careful | C, D, T-019-F |
| ↳ [T-020-G](#t-020-g-markdown-file-import-and-export) | Markdown file import and export | claimed (ChatGPT, 2026-11-18) | any | T-019-B |
| [T-021](#t-021-unified-local-database-components-versions-assemblies) | Unified local database (umbrella) | open | careful | — |
| ↳ T-021-A to T-021-E | Schema version and backup; components and versions; assemblies; archive; storage module | open | careful | in order |
| [T-022](#t-022-in-app-component-editor) | In-app component editor (umbrella) | open | careful | T-021-E, T-019-A |
| ↳ T-022-A to T-022-G | Editor window; preview; toolbar; table editor; insert field; source toggle; import review | open | careful | see task |
| [T-023](#t-023-component-library-and-assembly-builder) | Library browser and assembly builder (umbrella) | open | careful | T-021-E, T-026 |
| ↳ T-023-A to T-023-E | Browser; choose shell; order components; review; fill and generate | open | careful | see task |
| [T-024](#t-024-saved-assembly-revisions-and-deliberate-updates) | Saved revisions and deliberate updates (umbrella) | open | careful | T-021-E, T-023-C |
| ↳ T-024-A to T-024-D | Save and reopen; list newer; review and choose; reproducibility tests | open | careful | see task |
| [T-029](#t-029-component-library-backup-and-markdown-export-and-import) | Library backup; Markdown export and import | open | careful | T-021-E, T-020-G |
| [T-030](#t-030-check-generated-documents-in-real-word) | Check generated documents in real Word | open | human | T-019-F |
| [T-031](#t-031-hyperlinks-in-components-optional) | Hyperlinks in components (optional) | open | careful | T-019-F, T-020-B |
| [T-017](#t-017-show-plain-english-release-notes-in-the-update-dialog) | Plain-English "what's new" in the update dialog | done (2026-11-18, [PR #15](https://github.com/RexBHavgreau/contractbuilder/pull/15)) | any | — |

Suggested order: T-010, T-011, T-012, T-014 (any order; all small, and none
touches the same lines as another except T-010 and T-012, which both edit
`update_checker.py`: do them one after the other), then T-015, then the rest
of T-002. T-008 is complete; see [PROPOSAL-001.md](PROPOSAL-001.md) for the
agreed component-builder direction. Component builder order: first the three
things nothing waits on, T-019-A (the spike), T-026 (shell contract) and
T-027 (size check); T-025 (numbering) is already decided; then T-019-B to
T-019-H, with T-020 (importer) starting once T-019-A and T-019-B are done;
T-021 (storage) can run alongside either; T-028 after T-019-B; then T-022,
T-023, T-024; T-029 and T-031 last. T-030 is Beaux's, once T-019-F exists.
T-017 any time. T-018 needs nothing from an agent until GitHub Support replies.

**History was rewritten on 2026-11-18.** Work from a clone or download made
after that date. A copy made earlier holds the old history; delete it rather
than pushing from it.

Done and kept for the record: T-001, T-003, T-004, T-005, T-006, T-007,
T-009, T-013, T-016 (below the open tasks).

---

## Open tasks

## T-018 Push the cleaned history and finish the clean-up

- **Status:** open, waiting only for GitHub Support (pushed by Beaux and
  verified by Claude, 2026-11-18)
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
      should no longer bring in commit `4becc60`. If Support declines, ask Beaux
      whether to delete and recreate the repository, the only other way to
      remove pull-request copies (it loses issues, pull requests, releases and
      stars).
- [x] **Forks.** On the repository page, Insights > Forks. There should be
      none (it was public for under a day). If there are, tell GitHub Support.
      (Verified 2026-11-18: 0 forks.)
- [ ] **Old copies.** Any other clone of the repository (another computer,
      ChatGPT or Codex workspaces, an extracted ZIP) still holds the old
      history. Delete them and download or clone afresh.
- [x] Tell Claude, or any agent, that it is done; it then reconnects its own
      working copy to the new history. (Done 2026-11-18: Claude's working copy
      matches GitHub, its old commits are purged, and its scratch copies of the
      old history and of the private list are deleted.)

**Done when:** `main` on GitHub starts with the commit the script names, the
next CI run on `main` is green with `test_no_details_from_real_contracts`
passing (not skipped), and GitHub Support has confirmed the purge.

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
      unconfirmed; T-002 will verify it on a real PC and decide whether the
      sentence stays.

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

- **Status:** claimed (ChatGPT, 2026-11-18)
- **Size:** S
- **Agent:** any
- **Needs:** T-010, T-011 and T-012 merged (so the release carries them)

Self-update has only been tested piecewise on Linux. The first real test is
a 0.3.0 app updating itself to a newer release, and the changes above are
worth releasing anyway.

- [ ] Raise `APP_VERSION` in `version.py` to `0.3.1`, in its own pull request
- [ ] After merging, confirm CI publishes the v0.3.1 release with
      `Word-Template-Filler-windows-x64.exe` attached and a `digest` on it
      (the updater checks it)
- [ ] Hand over to Beaux for T-002's last step

**Done when:** the v0.3.1 release exists with all three files.

## T-002 Confirm the 0.3.0 fixes on a real Windows PC

- **Status:** open (first step confirmed 2026-11-18)
- **Size:** S
- **Agent:** human
- **Needs:** T-015 for the last step only

Revised 2026-11-18: the repository is public, so no token is needed, and
the token step has been removed.

- [x] CI run for the merge is green, and the GitHub release `v0.3.0` exists
      with `Word-Template-Filler-windows-x64.exe` attached (checked
      2026-11-18: run 44 green; the release also has both macOS builds, each
      with a SHA-256 digest)
- [ ] On Beaux's PC, `build-windows.bat` builds `dist\Word Template Filler 0.3.0.exe`;
      `build-log.txt` reads as normal text (no "L o o k i n g") and lists
      Python 3.14 as `accepted`
- [ ] Download `Word-Template-Filler-windows-x64.exe` from the v0.3.0
      release page and run it once. Note whether SmartScreen warns (T-011)
- [ ] Help > Check for updates says 0.3.0 is the latest, with no token set
- [ ] When v0.3.1 is out (T-015): the 0.3.0 app offers it, downloads it,
      closes and reopens as 0.3.1 (title bar shows 0.3.1). Note whether
      SmartScreen warns this time; tell whoever does T-011
- [ ] Record the result in CLAUDE.md's Progress log; open a task for anything
      that failed, with `build-log.txt` or a screenshot

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

## Component builder (T-019 to T-032)

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
- **The size limit** becomes a CI check (T-027).
- **Clause numbering** is decided (T-025): nested ordered lists, rendered as
  a decimal outline. Other legal formatting is out of scope (T-032).

### T-019 Prototype Markdown-to-Word composition

- **Status:** open (umbrella; work its subtasks)
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

- **Status:** claimed (ChatGPT, 2026-11-18)
- **Size:** M
- **Agent:** careful
- **Needs:** —

The two biggest unknowns, settled before anything is built on them. Write
the findings as a short section in this file's notes for T-019 (or a
`docs/` note) and tick the boxes.

- [ ] Show how `{{...}}` text behaves in markdown-it-py (tables enabled):
      underscores and asterisks inside names (`{{First_Name}}`), the pipe in
      `{{Fee | money-words}}` inside a table cell (the parser reads `|` as a
      column break), `{{#if X}}` and `{{/if}}` alone on a line, inside a list
      item, inside a table cell, and spanning two components
- [ ] Choose and prove a protection method (for example: swap every
      `{{...}}` span for a placeholder token before parsing, and restore it
      as literal text in one run afterwards). It must handle every case above
- [ ] Prove the hand-off: take a hand-built generated document, open it with
      `core.Template` and `core.render`, and fill a field in a paragraph, a
      list item and a table cell. Note what `core.read_parts` needs (path on
      disk or in-memory) and whether each field ends up in one clean run
- [ ] Record whether any `core.py` change is needed. If so, make it a
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

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-019-A, T-019-B, T-026 (shell style names)

- [ ] New module (for example `md_to_word.py`) turning tokens into
      WordprocessingML paragraphs and runs with lxml
- [ ] Paragraphs, line breaks, headings 1 to 3 (shell styles from T-026),
      bold, italic and both together
- [ ] Field text preserved as in T-019-A, including when it sits inside bold
      or italic
- [ ] Never emit raw HTML, images, or anything outside the supported subset;
      an unsupported construct produces a clear warning in the return value,
      not a silent drop

**Done when:** tests check the XML of each construct and that styles come
from the shell, not hard-coded fonts.

#### T-019-D Render lists with native Word numbering

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-019-C, T-026 (T-025 is decided; see it)

- [ ] Bulleted and numbered lists, including nested lists, as real Word
      numbering (`w:numPr`), never typed numbers
- [ ] Use the shell's numbering definitions (T-026); add new `w:num`
      instances so each numbered list restarts correctly
- [ ] Implement T-025's decision: nested ordered lists become one
      multi-level decimal outline (1., 1.1, 1.1.1) with at least three
      levels; position in the nesting decides the number, not the digits
      typed in the Markdown; read each level's format from the shell's
      definition rather than hard-coding it
- [ ] A continuation paragraph indented under a list item stays with that
      clause, unnumbered
- [ ] Tests: two separate numbered lists both start at 1; nesting to three
      levels gives 1, 1.1, 1.1.1; items typed as `7.` still number from 1;
      moving an item renumbers; a field in a list item; a continuation
      paragraph

**Done when:** tests inspect `numbering.xml` and the paragraph properties,
and the numbering restarts as expected.

#### T-019-E Render tables

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-019-C, T-026

- [ ] GFM tables as native `w:tbl` with header row marked, column count
      consistent, and the shell's table style
- [ ] Inline emphasis and fields inside cells; the pipe case from T-019-A
- [ ] Column alignment from the Markdown (`:---`, `:---:`, `---:`) where the
      shell allows
- [ ] Empty cells are valid (a cell needs a paragraph)

**Done when:** tests check structure and that a `{{Fee | money-words}}`
inside a cell survives and is fillable.

#### T-019-F Compose the document from a shell

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-019-C, T-019-D, T-019-E

- [ ] Function taking a shell path, an ordered list of Markdown strings and
      an output path; writes a new `.docx`
- [ ] Keep the shell's styles, headers, footers, page size, margins, section
      properties and relationships; replace only the body content, keeping
      the final `w:sectPr`
- [ ] Order of components and of paragraphs and tables inside them preserved
- [ ] The shell file is never opened for writing (test: byte-for-byte equal
      before and after)
- [ ] The output has a correct content-types part and relationships, so
      Word opens it (see T-030 for a real-Word check)

**Done when:** tests generate a document from three components and the
shell's formatting metadata is verified in the output.

#### T-019-G End-to-end through the field engine

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-019-F

- [ ] Test: compose, then `core.Template` finds the fields once each even if
      repeated across components, and `core.render` fills them in paragraphs,
      list items and table cells
- [ ] Test: `{{#if X}}` blocks across components and inside cells, true and
      false
- [ ] Test: formats (`money-words`, `date-formal`) work in the output

**Done when:** the end-to-end tests pass with the same invented values the
template workflow's tests use.

#### T-019-H Measure the release size

- **Status:** open
- **Size:** S
- **Agent:** careful
- **Needs:** T-019-B, T-027

- [ ] Build the Windows executable with and without the new module (CI or
      locally) and record both sizes in the Decision log
- [ ] Stay at or below 30 MB (31,457,280 bytes); if the margin is under
      3 MB, say so and name the next likely cost

**Done when:** the measured numbers are in CLAUDE.md and T-027's check is
green.

### T-020 Import Word content as Markdown

- **Status:** open (umbrella; work its subtasks)
- **Size:** umbrella of T-020-A to T-020-G
- **Agent:** careful
- **Needs:** T-019-A (the field-protection method), T-019-B

See PROPOSAL-001.md section 6. A new, isolated `docx_import.py` using
zipfile and lxml. Import is content conversion, never layout; the source
file is never changed.

**Done when:** a DOCX of supported mixed content becomes reviewable Markdown
in the right order, fields intact, and every unsupported structure reported.

#### T-020-A Read the package and the body in order

- **Status:** claimed (ChatGPT, 2026-11-18)
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

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-020-A

- [ ] Heading styles to `#`..`###` (map by style id/name and outline level;
      deeper headings are reported, not dropped)
- [ ] Bold and italic across split runs (Word splits runs freely; merge
      neighbours with the same formatting)
- [ ] Escape Markdown characters in ordinary text so the round trip does not
      turn a literal `*` or `_` into emphasis
- [ ] `{{Field}}` and `{{#if}}` text kept literal, even when it is split
      across runs (reuse `core`'s run-spanning logic where possible)
- [ ] Underline, strikethrough, highlight, font and colour changes are
      reported as dropped formatting (these are out of scope, T-032)

**Done when:** tests cover split runs and a field split across three runs.

#### T-020-C Lists

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-020-B (T-025 is decided; see it)

- [ ] Read `numbering.xml` to tell bulleted from numbered and find the
      nesting level
- [ ] Convert lists per T-025: multi-level Word lists become nested ordered
      lists by level, whatever their numbering style; letter and Roman
      styles become decimal, with a warning saying so
- [ ] Typed numbers that are not Word numbering (such as "1." typed by hand)
      are kept as text and flagged as possible list items

**Done when:** tests cover bullets, numbers, nesting and typed numbers.

#### T-020-D Tables

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-020-B

- [ ] Rectangular tables to GFM tables; first row as header
- [ ] Merged cells (horizontal or vertical), nested tables, and cells with
      more than one paragraph or a list are reported, with the best-effort
      text still included where it is safe
- [ ] A literal `|` in cell text is escaped

**Done when:** tests cover a plain table, a merged-cell table, a cell with
two paragraphs, and a mixed paragraph-table-paragraph body.

#### T-020-E Warnings for everything else

- **Status:** open
- **Size:** S
- **Agent:** careful
- **Needs:** T-020-A

- [ ] Report images, drawings and floating shapes, equations, footnotes and
      endnotes, comments, tracked changes, content controls, section and
      page breaks, headers and footers (not imported, by design), and
      unusual Word fields
- [ ] Tracked changes: report them and import the accepted text (final
      view), saying so
- [ ] Never drop text silently: every dropped run is accounted for in a
      warning

**Done when:** one invented fixture per structure yields the expected
warning, and the warning text is plain English.

#### T-020-F Round trip: DOCX, Markdown, DOCX

- **Status:** open
- **Size:** S
- **Agent:** careful
- **Needs:** T-020-C, T-020-D, T-019-F

- [ ] Test: import an invented DOCX, compose it into a shell, and check the
      text, order, tables and lists match the source
- [ ] Test: a second import of the composed output gives the same Markdown
      (stable round trip for the supported subset)

**Done when:** both round-trip tests pass.

#### T-020-G Markdown file import and export

- **Status:** claimed (ChatGPT, 2026-11-18)
- **Size:** S
- **Agent:** any
- **Needs:** T-019-B

- [x] Function pair to read a `.md` file (UTF-8, tolerate a BOM) and write
      one; the exported text re-imports with identical supported content
- [x] Unsupported Markdown (raw HTML, images, footnotes) reported on import

**Done when:** an export then import test passes unchanged.

### T-021 Unified local database: components, versions, assemblies

- **Status:** open (umbrella; work its subtasks)
- **Size:** umbrella of T-021-A to T-021-E
- **Agent:** careful
- **Needs:** —

See PROPOSAL-001.md section 9. **Choice made here:** extend the existing
`publisher_profiles.sqlite3` with new tables; do not rename or move it. No
user data migration is then needed. Add a schema version
(`PRAGMA user_version`) so later changes are safe. Beaux to confirm when
claiming the task.

**Done when:** the new tables exist, are tested, and an existing user's
publisher profiles are untouched.

#### T-021-A Schema version and safe upgrade

- **Status:** open
- **Size:** S
- **Agent:** careful
- **Needs:** —

- [ ] Add `PRAGMA user_version`; a database with no version is version 1
      (today's publisher schema)
- [ ] Upgrade steps run in a transaction, after copying the file to
      `publisher_profiles.sqlite3.bak-<version>` once; the backup is kept
      until the upgrade has succeeded and been checked
- [ ] Test: a database made by the current code upgrades and its publishers
      are identical; a failed step leaves the original unchanged
- [ ] Test: an older app opening an upgraded database does not damage it
      (extra tables are ignored)

#### T-021-B Components and immutable versions

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-021-A

- [ ] Tables `components` (id, name, description, category, tags, status)
      and `component_versions` (id, component_id, number, markdown, created,
      note)
- [ ] Saving an edit always creates a new version; a version's Markdown is
      never updated (enforce with a trigger and test it)
- [ ] Categories and tags are free text; suggested categories are only
      suggestions

#### T-021-C Assemblies and revisions

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-021-B

- [ ] Tables `assemblies`, `assembly_versions` (shell reference included)
      and `assembly_components` (component_version id, position, included
      flag)
- [ ] A revision pins component version ids, never "latest"
- [ ] Shell reference stores a path and a content hash, so a moved or
      changed shell is noticed (see T-026)

#### T-021-D Archive instead of delete

- **Status:** open
- **Size:** S
- **Agent:** careful
- **Needs:** T-021-B, T-021-C

- [ ] Components and assemblies can be archived and restored; they are never
      hard-deleted while any assembly revision refers to them
- [ ] Test: an assembly pinned to an archived component's version still
      generates the same Markdown

#### T-021-E Storage module and tests

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-021-B, T-021-C, T-021-D

- [ ] A plain module (for example `library.py`) with the functions the UI
      will call: create/list/search components, save a version, create an
      assembly, save a revision, list newer versions available for a pinned
      revision. No Tkinter in it
- [ ] Tests use a temporary database and invented data

### T-022 In-app component editor

- **Status:** open (umbrella; work its subtasks)
- **Size:** umbrella of T-022-A to T-022-G
- **Agent:** careful
- **Needs:** T-021-E, T-019-A

See PROPOSAL-001.md section 5. This was the largest, riskiest item, so it is
now small steps. **Choice made here:** the first working editor is plain
text plus a rendered preview, and the toolbar and table editor follow. A
Tkinter Text widget cannot be a faithful Word view; the preview shows
structure only, and the guide says so.

**Done when:** a user who does not know Markdown can create, import, edit and
save a component, with tables and fields, and see how it will look.

#### T-022-A Editor window shell and save

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-021-E

- [ ] A "Components" window, reached from the main window, separate from the
      template workflow; name, category and tags fields; Save makes a new
      version with an optional note
- [ ] Unsaved-changes prompt in plain English
- [ ] The existing template workflow's screen and menus are unchanged

#### T-022-B Preview

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-022-A, T-019-C

- [ ] A read-only preview pane using Text widget tags: headings, bold,
      italic, lists, tables as aligned text, fields highlighted
- [ ] Updates as the user stops typing (debounced), never blocks typing
- [ ] A line under it: "Word decides the final page layout"

#### T-022-C Formatting toolbar

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-022-B

- [ ] Buttons for heading, bold, italic, bulleted list, numbered list,
      indent and outdent; they wrap, prefix or re-indent the selection and
      write Markdown the user need not see. Indent and outdent move a
      numbered item down or up a level (1. becomes 1.1); the user never types
      indentation
- [ ] The preview (T-022-B) shows the computed outline numbers (1., 1.1,
      1.1.1), not the digits stored
- [ ] Keyboard shortcuts for bold and italic
- [ ] Works when the editing area shows the formatted preview and when it
      shows source (T-022-F)

#### T-022-D Table editor

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-022-B

- [ ] A dialog with a grid: add or remove rows and columns, type cell text,
      mark the header row; produces the Markdown table without the user
      typing pipes
- [ ] Opening an existing table in the editor (round trip)
- [ ] A literal pipe or a field with a pipe in a cell is handled as in
      T-019-A

#### T-022-E Insert a field

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-022-A

- [ ] A button listing field names already used in the library and
      publisher-profile fields, and the formats, inserting `{{Name}}` or
      `{{Name | format}}`
- [ ] Uses `core`'s own field parser to read and check names; do not write a
      second parser. A malformed `{{` is flagged in plain English

#### T-022-F Source view toggle

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-022-A

- [ ] An "Advanced: show raw text" switch that shows the Markdown, kept off
      by default and described plainly

#### T-022-G Import review dialog

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-022-B, T-020-F

- [ ] "Import from a Word file": choose a `.docx`, see the converted result
      in the preview with the warnings listed above it in plain English
- [ ] The user can fix text, then save as a component, or cancel; nothing is
      saved before they agree
- [ ] The source file is not modified

### T-023 Component library and assembly builder

- **Status:** open (umbrella; work its subtasks)
- **Size:** umbrella of T-023-A to T-023-E
- **Agent:** careful
- **Needs:** T-021-E, T-026

See PROPOSAL-001.md section 3B.

**Done when:** a user can choose a shell, add, order, include or omit
components, review the result, fill the fields once, and create the
document.

#### T-023-A Library browser

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-021-E

- [ ] List by category and tag, with search by name and wording; archived
      components hidden unless asked for
- [ ] Open a component in the editor (T-022-A); see its version history

#### T-023-B Choose a shell

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-026

- [ ] Pick a shell file; validate it with T-026's checker and show its
      plain-English findings; remember the last shell used

#### T-023-C Build and order an assembly

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-023-A

- [ ] Add components, move up and down, remove, and tick "include" to omit
      an optional component without removing it
- [ ] A component can be added more than once only if the user chooses

#### T-023-D Review the assembled document

- **Status:** open
- **Size:** S
- **Agent:** careful
- **Needs:** T-023-C, T-022-B

- [ ] One preview of everything in order, fields highlighted

#### T-023-E Fill and generate

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-023-D, T-019-G

- [ ] Compose to a temporary `.docx`, then show the existing form (same code
      path as the template workflow) with one input per field across all
      components
- [ ] Publisher profile loading as today; values shown for review before
      creating the document
- [ ] Output named and saved as the template workflow does
- [ ] No change to the template workflow's behaviour; its tests stay green

### T-024 Saved assembly revisions and deliberate updates

- **Status:** open (umbrella; work its subtasks)
- **Size:** umbrella of T-024-A to T-024-D
- **Agent:** careful
- **Needs:** T-021-E, T-023-C

See PROPOSAL-001.md section 9.

**Done when:** a saved assembly reopens with the same versions, and newer
component versions are used only after the user reviews and chooses them.

#### T-024-A Save and reopen

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-023-C

- [ ] Save an assembly (name, shell, components, order, included flags) as
      revision 1; reopen it and produce identical Markdown

#### T-024-B List newer versions

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-024-A

- [ ] On opening, show (not apply) which pinned components have newer
      versions; nothing changes without a click

#### T-024-C Review and choose updates

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-024-B

- [ ] A dialog showing, per component, old and new wording with changes
      marked (a simple line difference is enough)
- [ ] The user ticks which to update; saves a new revision; the previous
      revision remains and can be opened

#### T-024-D Reproducibility tests

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** T-024-C

- [ ] Revise a component twice; the saved revision still generates the old
      wording; an updated revision generates the new

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

- **Status:** claimed (ChatGPT, 2026-11-18)
- **Size:** S
- **Agent:** any
- **Needs:** T-019-B

markdown-it-py and mdurl are MIT licensed; the notice must travel with the
app.

- [ ] A `THIRD-PARTY-LICENSES.txt` with each package's name, version,
      copyright line and licence text (copy from the installed packages; do
      not invent the text)
- [ ] Bundle it with the app (the PyInstaller `--add-data`, like the guide)
      and show it from Help
- [ ] A test that fails when a runtime dependency has no entry

**Done when:** the file is in the packaged app and the test passes.

### T-029 Component library backup, and Markdown export and import

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-021-E, T-020-G

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

- **Status:** open
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
- [ ] Repeat after T-019-D (lists) and T-031 (links)

### T-031 Hyperlinks in components (optional)

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** T-019-F, T-020-B

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

## Done tasks (kept until a month after they were done)

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
- [ ] Push it, and the rest of the clean-up only Beaux can do: T-018

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
