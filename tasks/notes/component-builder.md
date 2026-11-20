# Component builder (T-020 to T-031; T-019, T-021, T-025 to T-028 and T-032 to T-033 are done)

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
