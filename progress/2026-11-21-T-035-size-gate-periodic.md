---
date: 2026-11-21
task: T-035
author: Claude
pull_request: https://github.com/RexBHavgreau/contractbuilder/pull/58
ci_run: pending (update after the run on the latest commit)
size: no executable change
---

- **2026-11-21** T-035 (Claude): the size gate now runs weekly (Mondays) and on manual runs; the comparison build gets its `--hidden-import` list from `scripts/list_app_modules.py` (a test fails if a module is missed); `--min-headroom 3145728` fails either build under 3 MiB of headroom with a "tell Beaux" message; the run summary shows both sizes, headroom, growth since the last published release and the Python, PyInstaller and lxml versions (`scripts/size_report.py`); pull requests build Windows/macOS only when their files could matter (`scripts/ci_scope.py`) and a newer push cancels the older PR run. Tests added for each script. Not yet seen: the first CI run with these workflow changes. Open: T-057 must require only `test` in the branch rule.
