---
date: 2026-11-18
task: none
author: not recorded
pull_request: not recorded
source: CLAUDE.md (moved 2026-11-20, T-053)
sequence: 28
---

- **2026-11-18 — Pin markdown-it-py 3.0.0 and mdurl 0.1.2.**
  The project still supports Python 3.9; markdown-it-py 4.x requires Python
  3.10 or later, while 3.0.0 supports Python 3.8 and later. The parser uses
  the CommonMark preset, explicitly enables tables, and disables raw HTML.
  Keep this import out of `simple_app.py` until a component-builder task
  needs it.
