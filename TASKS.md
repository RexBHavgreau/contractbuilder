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

**To add a task:** give it the next number and every field below. Write the
acceptance check so someone else can tell, without asking, whether it is
done. Add it to the board.

Fields:

- **Status:** `open`, `claimed (who, date)`, `blocked (why)`, `done (date, PR)`
- **Size:** S (under an hour), M (a few hours), L (a day or more; split it)
- **Agent:** `any` (well-specified; a cheap agent will do), `careful` (needs
  judgement, a strong model, or Windows/macOS hardware), `human` (only a
  person can do it)
- **Needs:** anything that must happen first, such as `Beaux` for a decision
  or another task

## Board

Reviewed 2026-11-18, revised after the history rewrite. Next free number: **T-019**.

| Task | What | Status | Agent | Needs |
| --- | --- | --- | --- | --- |
| [T-018](#t-018-push-the-cleaned-history-and-finish-the-clean-up) | **Push the cleaned history; finish the clean-up on GitHub** | open | human | Beaux |
| [T-010](#t-010-finish-going-public-stop-telling-users-the-repository-is-private) | Stop telling users the repository is private | open | any | T-018 |
| [T-011](#t-011-tell-users-what-windows-and-macos-will-say-about-an-unsigned-app) | Explain the SmartScreen / Gatekeeper warnings | open | any | T-018 |
| [T-012](#t-012-cope-with-githubs-limit-on-unsigned-update-checks) | Cope with GitHub's limit on update checks | open | any | T-018 |
| [T-014](#t-014-stop-testssamplepy-pointing-at-the-deleted-examples-folder) | Tidy `tests/sample.py` after `examples/` was deleted | open | any | T-018 |
| [T-015](#t-015-release-031-to-prove-self-update-end-to-end) | Release 0.3.1 to prove self-update end to end | open | any | T-010, T-011, T-012 |
| [T-002](#t-002-confirm-the-030-fixes-on-a-real-windows-pc) | Confirm the build and updates on a real Windows PC | open | human | T-015 for its last step |
| [T-008](#t-008-decide-what-to-do-with-advanced_apppy) | What to do with `advanced_app.py` | open | human | Beaux |
| [T-017](#t-017-show-plain-english-release-notes-in-the-update-dialog) | Plain-English "what's new" in the update dialog | open | any | T-018 |

Suggested order: **T-018 first, and nothing else until it is done**: it
force-pushes every branch, so work started on the old history would have to
be redone. Then T-010, T-011, T-012, T-014 (any order; all small, and none
touches the same lines as another except T-010 and T-012, which both edit
`update_checker.py`: do them one after the other), then T-015, then the rest
of T-002. T-008 waits for Beaux. T-017 any time after T-018.

Done and kept for the record: T-001, T-003, T-004, T-005, T-006, T-007,
T-009, T-013, T-016 (below the open tasks).

---

## Open tasks

## T-018 Push the cleaned history and finish the clean-up

- **Status:** open (prepared by Claude, 2026-11-18)
- **Size:** S
- **Agent:** human
- **Needs:** Beaux. Do this before any other task.

Beaux decided on 2026-11-18 that details from real contracts must be removed
permanently, even by rewriting history (T-016). Claude rewrote every branch
and tag and checked the result, but this session may push only its own
branch, so the final push is Beaux's. The rewritten repository, a script that
pushes it, and the list of what was removed (`BLOCKED_TERMS.txt`, private:
never commit it) were handed over in the chat, as a folder called
`contractbuilder-cleanup`.

Steps, in this order:

- [ ] **GitHub email privacy first.** On github.com: your picture > Settings >
      Emails. Tick "Keep my email addresses private" and "Block command line
      pushes that expose my email". Otherwise the next commit made on the
      website records your personal address again.
- [ ] **Allow the force-push.** Settings > Rules (or Branches): if a rule
      protects `main` against force pushes, turn that off for now, and back on
      afterwards.
- [ ] **Push.** Install Git for Windows if needed (https://git-scm.com), then
      double-click `push-cleaned-history.bat` in the handover folder. It shows
      what it will replace and asks before pushing. It refuses, changing
      nothing, if anything was pushed to GitHub after 2026-11-18 03:47 UTC.
- [ ] **Turn on the guard.** Settings > Secrets and variables > Actions > New
      repository secret. Name: `BLOCKED_TERMS`. Value: the contents of
      `BLOCKED_TERMS.txt`. From then on CI fails if any of those terms is
      committed again (`tests/test_no_private_details.py`). Keep the file
      somewhere private, such as your password manager.
- [ ] **Ask GitHub Support to purge what a push cannot reach.** The nine
      pull requests (#1 to #9) keep their own copies of the old commits, and
      old commit pages stay viewable by their address until GitHub clears its
      caches. At https://support.github.com, choose "Remove sensitive data"
      (or "Contact us" about it), and paste the request text from
      `github-support-request.txt` in the handover folder.
- [ ] **Forks.** On the repository page, Insights > Forks. There should be
      none (it was public for under a day). If there are, tell GitHub Support.
- [ ] **Old copies.** Any other clone of the repository (another computer,
      ChatGPT or Codex workspaces, an extracted ZIP) still holds the old
      history. Delete them and download or clone afresh.
- [ ] Tell Claude, or any agent, that it is done; it then reconnects its own
      working copy to the new history.

**Done when:** `main` on GitHub starts with the commit the script names, the
next CI run on `main` is green with `test_no_details_from_real_contracts`
passing (not skipped), and GitHub Support has confirmed the purge.

## T-010 Finish going public: stop telling users the repository is private

- **Status:** open
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

- [ ] Reword the Update settings window: a token is not needed; it is only
      for someone who sees "GitHub is limiting update checks" often
- [ ] 404 with no token: "GitHub has no published release for this app yet,
      or the repository has moved." Keep the `needs_token` flag off for it, so
      startup stays quiet
- [ ] Remove or rewrite the four document sections above; the guide should
      not mention tokens except as the optional setting
- [ ] Update `tests/test_updates.py` for the new 404 wording, and keep a test
      that a 404 with a saved token still names the token as a possible cause
- [ ] CLAUDE.md: the pitfall was already corrected on 2026-11-18; once the
      wording is gone, delete its sentence "Text saying so is being removed"

**Done when:** `git grep -n -i -E "repository is private|private repositor|is private, so" -- '*.py' '*.txt' README.md ':!tests'`
finds nothing, and all tests pass. (Test names and CLAUDE.md's history notes
may still say "private"; they describe the past.)

## T-011 Tell users what Windows and macOS will say about an unsigned app

- **Status:** open
- **Size:** S
- **Agent:** any

Beaux decided not to sign the app (T-009). So the first time each person
runs a downloaded copy, Windows SmartScreen shows "Windows protected your
PC", and macOS refuses to open it. Nothing in USER-GUIDE.txt or README.md
says so, and staff will reasonably think something is wrong.

- [ ] USER-GUIDE.txt, near the start: a short "FIRST RUN" section.
      Windows: click More info, then Run anyway. macOS: right-click (or
      Control-click) the app, choose Open, then confirm. Once per computer.
- [ ] README.md: one line under "Build and releases" pointing at it
- [ ] Say that updates installed by the app itself should not show the
      warning again, because a file the app downloads is not marked as coming
      from the internet. *Unconfirmed:* add it as "should not", and leave T-002
      to confirm it; T-002's result decides whether the sentence stays

**Done when:** a colleague who has never seen the app can get it open on
Windows from the guide alone.

## T-012 Cope with GitHub's limit on unsigned update checks

- **Status:** open
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

- [ ] In `check_for_update`, tell a rate-limit 403 or 429 (header
      `X-RateLimit-Remaining` is `0`, or a `Retry-After` header is present)
      from other refusals. Message: "GitHub is limiting update checks from
      your network for now. The app will try again later." It is not
      `needs_token`
- [ ] At startup, check at most once a day per user: store the time of the
      last successful check beside `update-settings.json` (see
      `self_update.settings_path()`) and skip the automatic check if it is
      under 24 hours old. Help > Check for updates always checks
- [ ] Automatic checks that hit the limit stay silent: no dialog, no status
      line
- [ ] Tests with a fake `urlopen` for: rate-limit 403, ordinary 403, and
      the once-a-day skip (with a fixed clock, not real time)

**Done when:** the tests pass, and a rate-limited automatic check shows
nothing while a rate-limited manual check shows the message above.

## T-014 Stop tests/sample.py pointing at the deleted examples folder

- **Status:** open
- **Size:** S
- **Agent:** any

Beaux deleted `examples/` from the repository on 2026-11-17. The tests do not
need it (they build their sample template in a temporary folder), but
`tests/sample.py` still says it builds `examples/Sample Services
Agreement.docx` "handed to the department as a worked example", and running
it directly would recreate the deleted file.

- [ ] Update the docstring: it builds the sample template the tests use
- [ ] Make `python tests/sample.py` write to a path given on the command
      line, or to the current folder, never to `examples/`
- [ ] Add `examples/` to `.gitignore`, so a sample is not committed back by
      accident
- [ ] Check nothing else refers to `examples/` (`git grep -n examples`)

**Done when:** `python tests/sample.py` no longer recreates `examples/`, and
all tests pass.

## T-015 Release 0.3.1 to prove self-update end to end

- **Status:** open
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

- **Status:** open
- **Size:** S to decide
- **Agent:** human
- **Needs:** Beaux

`advanced_app.py` is the earlier window. It is not packaged, but it holds
features the packaged app lacks: making many contracts from a spreadsheet,
saving and reloading answers, and "Turn a contract into a template", which
fits the decision that users build their own fields. Since T-007, the
packaged app explains how to write fields by hand; the template maker would
do it for them from an existing contract.

- [ ] Beaux chooses for each: bring into `simple_app.py`, keep as is, or delete
- [ ] Split each "bring in" into its own task, sized M or smaller

## T-017 Show plain-English release notes in the update dialog

- **Status:** open
- **Size:** M
- **Agent:** any

When an update is offered, the dialog shows only version numbers. The
release notes GitHub writes by itself list pull-request titles such as
"Claude/contract template builder j7njxm", which mean nothing to staff.

- [ ] Add a `CHANGES.txt` at the top of the repository: newest version first,
      a few plain sentences per version on what changed for the person using
      the app. Start it with 0.3.0 and 0.3.1
- [ ] In `.github/workflows/build.yml`, publish that version's section as the
      release body (`body_path` on `softprops/action-gh-release`) instead of
      `generate_release_notes`
- [ ] In `simple_app.py`, show the release body (already in
      `ReleaseInfo.notes`) under the version numbers in the update dialog,
      cut to about 15 lines
- [ ] Add to CLAUDE.md's release instructions: raising `APP_VERSION` also
      means adding its section to `CHANGES.txt`; make CI fail if the section
      is missing
- [ ] Tests for reading one version's section out of `CHANGES.txt`

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
