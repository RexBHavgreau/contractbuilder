# Suggested order and standing notes

Hand-edited by whoever orders the work (Beaux or the lead agent); the board itself is generated from the task files by `python scripts/board.py`.

**Waiting, not a task:** GitHub Support's purge of the old commits behind
pull requests #1 to #9. Details under T-018. Nobody needs to do anything until
Support replies.

**Suggested order:** T-039 first: open a pull request from the branch (it
carries the restart fix and the 0.4.1 bump), wait for green CI, merge to
publish 0.4.1. Then UT-002 on a PC with 0.4.0 (the update to 0.4.1 will show
the error one more time; the update after that should not) and UT-001 (Word).
T-035 before the next feature lands, since the size comparison is currently
meaningless and every pull request runs three platform builds. T-029
(backup) and T-031 (links) are next features; T-036 is tidying.

Conflict fixes first (T-053, then T-052, with UT-004 set by Beaux at any
time), then T-055; feature work on the files they split follows. T-056 goes
before T-048 and T-046-B/D.

Usability fixes from Beaux's hand testing (T-040 to T-047) are grouped under
"Component manager usability"; they ship as 0.5.0 after 0.4.1.

**History was rewritten on 2026-11-18.** Work from a clone or download made
after that date. A copy made earlier holds the old history; delete it rather
than pushing from it.

Done and kept for the record: T-001, T-003, T-004, T-005, T-006, T-007,
T-009, T-013, T-016 (below the open tasks).
