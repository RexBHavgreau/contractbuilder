# Working in parallel without conflicts (T-052 to T-057)

Several agents work on different tasks at once and their pull requests keep
conflicting. Measured on 2026-11-20 over the pull requests merged since
2026-11-18: `TASKS.md` changed 41 times and `CLAUDE.md` 35 times (every task
edits its own status line, a board row and the end of the progress log, all
at the same spot), and `component_editor.py` 26 times (it is now 2,360 lines
and eight open tasks touch it). Two kinds of fix, done in this order: separate
the documents from each other, separate the code, and set rules for who works
where. None of these tasks changes what the app does.

Until T-053 and T-054 are done, the interim rules in "How to use this file"
apply.
