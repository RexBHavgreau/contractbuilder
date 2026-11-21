# Task files

One Markdown file per task or subtask (TASKS.md T-054), so that two pull
requests about different tasks never edit the same file.

```
tasks/T-043.md        an umbrella or a standalone task
tasks/T-043-A.md      a subtask
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
- **Touches:** library.py, publisher_profiles.py
- **Size gate:** yes

Free text...

- [ ] a box to tick
```

- `Status` starts with one of `open`, `claimed`, `blocked`, `waiting`,
  `done`; anything after the first word is free text. A long value may
  continue on the next lines.
- The file name is the task number (`T-043-A.md`) and must match the heading.
- A finished task has `Status: done (date, PR)` and **lives in `tasks/done/`**
  (`git mv tasks/T-043-A.md tasks/done/`); the test suite fails if a done
  file is outside `done/` or a file in `done/` is not done.
- Finished tasks are deleted a month after they were done. Git keeps them.

## Claiming and finishing

Claiming a task is its own one-line pull request that changes only that
task's `Status` line. Finishing it edits that file again (status, boxes, move
to `done/`), adds a file under `progress/` and, if a choice was made, one under
`decisions/`. Nothing else shared is edited, so nothing conflicts.
