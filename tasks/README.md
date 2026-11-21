# Task files

One Markdown file per task or subtask (TASKS.md T-054), so that two pull
requests about different tasks never edit the same file.

```
tasks/T-043.md        an umbrella or a standalone task
tasks/T-043-A.md      a subtask
tasks/UT-001.md       a check or confirmation only a person can do (never blocks a task)
tasks/done/           finished tasks, kept for a month, then deleted
tasks/notes/          background for a group of tasks (not tasks themselves)
```

Read the open work with:

    python scripts/board.py            # the board
    python scripts/board.py --next     # the next free task number
    python scripts/board.py --check    # malformed files and misplaced files

## A task file

The first line is a heading with the task number; the bullets directly under
it are read by the board script. Everything after the first blank line is
free text (what it is, the boxes to tick, "Done when").

```
# T-043-A Store field definitions

- **Status:** open
- **Size:** M
- **Agent:** careful
- **Needs:** none
- **Needed by:** T-043-C (and 1 more)
- **Touches:** `library.py` (also T-046-A), `publisher_profiles.py` (also T-046-C)
- **Size gate:** yes

Free text...

- [ ] a box to tick
```

**Links in both directions.** `Needs` names what this task waits for, by task
number. `Needed by` names the open tasks that wait for this one, written by
`python scripts/task_links.py --write`; never type it by hand. Only direct
dependents are listed, the first two by number, then "(and N more)". Each file
in `Touches` is followed by "(also …)" naming the other open tasks that change
it, so an agent can see at once which tasks overlap. Umbrella tasks are left
out of the "also" lists. After adding or changing a task, run `task_links.py
--write`; the tests fail until the files are up to date.

- `Status` starts with one of `open`, `claimed`, `blocked`, `waiting`,
  `done`; anything after the first word is free text. A long value may
  continue on the next lines.
- The file name is the task number (`T-043-A.md`) and must match the heading.
- A finished task has `Status: done (date, PR)` and **lives in `tasks/done/`**
  (`git mv tasks/T-043-A.md tasks/done/`); the test suite fails if a done
  file is outside `done/` or a file in `done/` is not done.
- Finished tasks are deleted a month after they were done. Git keeps them.

## Claiming and finishing

Claiming a task is `python scripts/claim.py T-043-A --who NAME`, which pushes
a branch `claim/T-043-A` (only one agent can create it) with the one-line change
to that task's `Status`; open a pull request from it and merge it at once. It
changes only that task's `Status` line. Finishing it edits that file again (status, boxes, move
to `done/`), adds a file under `progress/` and, if a choice was made, one under
`decisions/`. Nothing else shared is edited, so nothing conflicts.
