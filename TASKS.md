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
CLAUDE.md.

**While working:** tick subtasks as they are done. If a task turns out
bigger than its size, split it: add new tasks below with the next free
number and say so in the original.

**When done:** set `Status: done (date, PR link)`, add a line to the
Progress log in CLAUDE.md, and add a Decision log entry for any choice you
made that someone would otherwise have to rediscover. Leave done tasks here
for a month, then delete them.

**To add a task:** give it the next number and every field below. Write the
acceptance check so someone else can tell, without asking, whether it is
done.

Fields:

- **Status:** `open`, `claimed (who, date)`, `blocked (why)`, `done (date, PR)`
- **Size:** S (under an hour), M (a few hours), L (a day or more; split it)
- **Agent:** `any` (well-specified; a cheap agent will do), `careful` (needs
  judgement, a strong model, or Windows/macOS hardware), `human` (only a
  person can do it)
- **Needs:** anything that must happen first, such as `Beaux` for a decision

---

## T-001 Decide how colleagues receive updates

- **Status:** open
- **Size:** S to decide; M to carry out
- **Agent:** human (decision), then any
- **Needs:** Beaux

The repository is private, so GitHub hides its releases from anyone not
signed in, and each person must paste a GitHub token into Help > Update
settings. That suits one maintainer, not a department. Options:

1. Make the repository public. Simplest; nothing else changes. Check first
   that nothing in it is confidential (templates in `examples/`, names,
   addresses).
2. Keep the code private and publish releases to a separate public
   repository (for example `contractbuilder-releases`). CI pushes there with
   a token stored as an Actions secret; `GITHUB_REPOSITORY` in `version.py`
   points the updater at it.
3. Keep per-user tokens.

- [ ] Beaux chooses, and the choice goes in the CLAUDE.md decision log
- [ ] Carry it out; for option 2, split it into its own task first
- [ ] Update USER-GUIDE.txt "PRIVATE REPOSITORY" and README.md

**Done when:** a colleague's copy finds and installs a new release without
setting anything up, or the chosen alternative is documented.

## T-002 Confirm the 0.3.0 fixes on a real Windows PC

- **Status:** open
- **Size:** S
- **Agent:** human
- **Needs:** the 0.3.0 pull request merged into `main`

- [ ] CI run for the merge is green, and the GitHub release `v0.3.0`
      exists with `Word-Template-Filler-windows-x64.exe` attached
- [ ] On Beaux's PC, `build-windows.bat` builds `dist\Word Template Filler 0.3.0.exe`;
      `build-log.txt` reads as normal text (no "L o o k i n g") and lists
      Python 3.14 as `accepted`
- [ ] Install 0.3.0 once by hand (older versions cannot update themselves)
- [ ] Help > Update settings: paste the token; "Save and check now" says
      0.3.0 is the latest
- [ ] Release a 0.3.1 (raise `APP_VERSION`, merge); the 0.3.0 app offers it,
      downloads it, closes and reopens as 0.3.1
- [ ] Record the result in CLAUDE.md's Progress log; open a task for anything
      that failed, with the build log or a screenshot

## T-003 Retire the empty v0.2.0 release

- **Status:** open
- **Size:** S
- **Agent:** human
- **Needs:** T-002's v0.3.0 release published

v0.2.0 was tagged on a commit whose `version.py` said 0.1.0, so CI refused
to build it and its release has no files.

- [ ] Delete the v0.2.0 release on GitHub, or edit its notes to say it has
      no downloads and to use v0.3.0
- [ ] Leave the tag, so history still makes sense

## T-004 Find out why the macOS Apple Silicon build keeps getting cancelled

- **Status:** open
- **Size:** M
- **Agent:** any

In CI runs 40 and 42 (2026-11-17) the "Build macOS Apple Silicon" job on
`macos-26` was cancelled after about 15 minutes, marking the whole run red
although Windows and macOS Intel built. Releases still publish (Windows is
the only required file), but red runs hide real failures.

- [ ] Read the job logs (GitHub Actions run 44180008956, job "Build macOS
      Apple Silicon") and find whether it waited for a runner, timed out, or
      hung in PyInstaller
- [ ] Fix it: a runner label that exists, a `timeout-minutes`, or
      `continue-on-error` for that job only, with the reason in a comment
- [ ] Note the cause in CLAUDE.md's pitfalls

**Done when:** three consecutive pushes to `main` show a green run, or the
job is deliberately optional with the reason written down.

## T-005 Check the PowerShell build script in CI before building

- **Status:** open
- **Size:** S
- **Agent:** any

A syntax slip in `build-windows.ps1` only shows when someone builds. Add a
step at the start of the Windows CI job:

- [ ] Parse `build-windows.ps1` with
      `[System.Management.Automation.Language.Parser]::ParseFile(...)` under
      `powershell.exe` (5.1) and fail on any parse error
- [ ] Fail if `build-windows.bat` lacks CRLF line endings

**Done when:** a deliberately broken copy of the script fails that step
(try it on a branch, then revert).

## T-006 Clean up a leftover download if an update never started

- **Status:** open
- **Size:** S
- **Agent:** any

If the app is killed between finishing a download and starting the swap,
`<app>.exe.new` is left beside the app. `self_update.py` already reports a
failed swap through `<app>.exe.update-failed.txt`.

- [ ] At startup (Windows, built app only), delete a `<app>.exe.new` older
      than a day; leave a newer one, as a swap may still be running
- [ ] Test it in `tests/test_updates.py` with a fake executable path

## T-007 Document how to build fields in a template, for template authors

- **Status:** open
- **Size:** M
- **Agent:** any
- **Needs:** nothing (follows the 2026-11-17 decision in CLAUDE.md)

The decision is that contracts are built from templates whose fields the
user builds. USER-GUIDE.txt says only that "some templates may use
specialized fields", without saying how to write them. `core.py` supports
formats (`date`, `date-formal`, `date-short`, `money`, `money-words`,
`money-whole`, `number`, `number-words`, `upper`, `long`, `list`, `plural:`,
`choice:`) and conditions (`{{#if}}`, `{{else}}`, `{{/if}}`, `=`, `!=`,
`not`). `CHEAT_SHEET` in `core.py` is a terse summary.

- [ ] Add a "WRITING A TEMPLATE" section to USER-GUIDE.txt: one example per
      format and condition, each checked by filling a real template in a test
- [ ] Add "Help > How to write a template" to `simple_app.py`, showing that
      section (or `core.CHEAT_SHEET`)
- [ ] Keep the wording plain; no developer terms

**Done when:** a new member of staff can write a template with a date, an
amount in words and an optional clause using only the guide.

## T-008 Decide what to do with advanced_app.py

- **Status:** open
- **Size:** S to decide
- **Agent:** human
- **Needs:** Beaux

`advanced_app.py` is the earlier window. It is not packaged, but it holds
features the packaged app lacks: making many contracts from a spreadsheet,
saving and reloading answers, and "Turn a contract into a template", which
fits the decision that users build their own fields.

- [ ] Beaux chooses for each: bring into `simple_app.py`, keep as is, or delete
- [ ] Split each "bring in" into its own task, sized M or smaller

## T-009 Sign the Windows executable

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** Beaux (it costs money)

Windows SmartScreen warns on every new unsigned `.exe`, including each
update. A code-signing certificate removes that.

- [ ] Price the options (an OV certificate, or Azure Trusted Signing) and put
      them to Beaux
- [ ] If approved: sign in CI with the certificate held as an Actions
      secret, never in the repository
