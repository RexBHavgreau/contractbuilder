# TASKS.md

Open work on Word Template Filler, sized so that any agent, including a
cheap one, can pick up a task, do it, and hand it back. Read
[CLAUDE.md](CLAUDE.md) first: it has the layout, conventions, pitfalls and
decisions every task assumes.

## Where the tasks are

**One file per task and per subtask**, in [tasks/](tasks/): `tasks/T-043.md`
(an umbrella or a standalone task) and `tasks/T-043-A.md` (a subtask).
Finished tasks are in `tasks/done/`. Background that belongs to a group of
tasks is in `tasks/notes/`, and [tasks/README.md](tasks/README.md) says how a
file is laid out. This file holds only the rules.

- **The board** (open and in-progress work, with each task's status, agent,
  needs and touches) is built from the files, never edited by hand:

      python scripts/board.py

  After each merge to `main` a workflow publishes it as the run summary and
  as a downloadable artifact (and as `BOARD.md` if the repository variable
  `BOARD_BOT_COMMIT` is set to `true`; see T-054 and T-057).
- **The next free task number:** `python scripts/board.py --next`
- **A check** that every file is well formed and in the right folder runs in
  the tests (`python scripts/board.py --check` shows the same).
- **Suggested order and standing notes:** [tasks/notes/suggested-order.md](tasks/notes/suggested-order.md).

## How to use this file

**To take a task:** look at the open pull requests first, then claim the
task with **its own one-line pull request** that changes only that task's
file: its `Status` becomes `claimed (your name or agent id, date)`. Merge it
within minutes and before any other work starts; if someone else's claim
merged first, pick another task. Two agents then never take the same task.
Take only tasks marked `Agent: any` unless you are a stronger model or a
person. Do not take a task marked `Needs: Beaux` until its decision is
recorded in `decisions/`, and do not take one whose `Needs` names an
unfinished task.

**While working:** tick boxes in your task's own file. If a task turns out
bigger than its size, split it: add new task files with the next free number
and say so in the original.

**When done:** in your task's file set `Status: done (date, PR link)`, tick
every box that was done (and say why any was not), and **move the file to
`tasks/done/`** (`git mv tasks/T-043-A.md tasks/done/`). **Add a file under
`progress/`** (see [progress/README.md](progress/README.md)), and a file under
`decisions/` for any choice you made that someone would otherwise have to
rediscover. **Do not edit `CLAUDE.md`, this file or any other task's file**;
`CLAUDE.md` changes only by a deliberate rules change. Done tasks stay in
`tasks/done/` for a month and are then deleted (their history stays in git).

**Subtasks:** a large task is an umbrella (`tasks/T-022.md`) with subtasks
named `T-022-A`, `T-022-B` and so on (letters; if one itself needs splitting,
use `T-022-A-1`), each its own file. Take, claim and finish subtasks one at a
time. The umbrella is done when all its subtasks are. A subtask's `Needs` may
name subtasks of other tasks.

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
   the headroom in the `size` field of the task's `progress/` file (a test
   fails if the field is missing). Under 3 MiB of headroom: stop and
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
  `ci_run` and `size` fields of the task's `progress/` file
- Before opening or merging a pull request, merge the latest `main` into
  your branch and read both sides of any conflict (GitHub will enforce this
  once T-057 is set)
- After a merge, look at the run on `main`. If it is red, fixing it comes
  before any other work, and say so at the top of your report

**Parallel work.** Progress entries, decision entries and task files are all
separate files, so two pull requests about different tasks no longer edit the
same lines. What is left is code:
(1) claim a task by its own one-line pull request (above); (2) **before
opening or merging a pull request, merge the latest `main` into your branch**;
(3) edit only your own task's file here, plus the new `progress/` and
`decisions/` files; (4) **do not start a task whose "Touches" files another
claimed task is changing**; and (5) a task that splits a file (such as T-052 or
T-056) freezes it: leave that file alone until the split merges. See
[tasks/notes/working-in-parallel.md](tasks/notes/working-in-parallel.md).

**To add a task:** run `python scripts/board.py --next`, create
`tasks/T-NNN.md` with every field below, and write the acceptance check so
someone else can tell, without asking, whether it is done. The board picks it
up by itself.

Fields (bullets directly under the `# T-NNN title` heading of the file):

- **Status:** `open`, `claimed (who, date)`, `blocked (why)`, `waiting (on
  whom)`, `done (date, PR)`. The first word decides where the board shows it
- **Size:** S (under an hour), M (a few hours), L (a day or more; split it),
  or `umbrella` (a task made of subtasks, below)
- **Agent:** `any` (well-specified; a cheap agent will do), `careful` (needs
  judgement, a strong model, or Windows/macOS hardware), `human` (only a
  person can do it)
- **Needs:** anything that must happen first, such as `Beaux` for a decision
  or another task
- **Touches:** the files (or modules) the task will change, from T-055; two
  claimed tasks that share a file are done one after the other
- **Schema migrations** are numbered in merge order: only one open task adds
  a migration at a time, so a second one never renumbers on top of the first
  (T-043-A, then T-046-C...). `scripts/overlaps.py` reads the Touches fields
  of the task files and lists tasks that share one.
- **Size gate:** present on any task that adds code, a dependency or a bundled
  file; see "Size gate" above. It is part of that task's `Done when`
