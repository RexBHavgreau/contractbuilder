"""Claim a task so that no other agent can take it at the same time.

    python scripts/claim.py T-060 --who "Claude"   # claim a task
    python scripts/claim.py --list                 # tasks that are claimed
    python scripts/claim.py --new                  # reserve the next free task number
    python scripts/claim.py --release T-060        # give a claim back

Why a branch: creating a branch on GitHub either works or fails, with no gap
between looking and taking. Two agents that both push ``claim/T-060`` at the
same moment cannot both succeed; the second is refused at once and picks
another task. The claim branch holds the one-line change to the task's
``Status``. Open a pull request from it and merge it within minutes (TASKS.md),
then work on a separate branch. Delete the claim branch when the task is done.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import task_files  # noqa: E402

PREFIX = "claim/"
TASK_ID = re.compile(r"T-\d{3}(?:-[A-Z](?:-\d+)?)?")


class ClaimError(Exception):
    """A plain-English reason a claim could not be made."""


def git(repo, *args, check=True):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise ClaimError((result.stderr or result.stdout).strip() or "git failed")
    return result


def remote_claims(repo, remote="origin") -> dict:
    """{task id: commit} for every claim branch on the remote."""
    out = git(repo, "ls-remote", "--heads", remote, PREFIX + "*").stdout
    claims = {}
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        name = ref.removeprefix("refs/heads/" + PREFIX)
        if TASK_ID.fullmatch(name):
            claims[name] = sha
    return claims


def _current_branch(repo) -> str:
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def _unfinished_needs(task, tasks) -> list:
    by_id = {t.id: t for t in tasks if t.id}
    return [
        n for n in TASK_ID.findall(task.get("needs"))
        if n in by_id and by_id[n].state != "done"
    ]


def claim(task_id, who, repo=".", remote="origin", base="main", today=None) -> str:
    """Claim `task_id`; returns the claim branch name. Raises ClaimError."""
    repo = Path(repo)
    task_id = task_id.upper()
    if task_id.startswith("UT-"):
        raise ClaimError(
            f"{task_id} is a check for a person (a UT- task), not work for an agent to claim."
        )
    if not TASK_ID.fullmatch(task_id):
        raise ClaimError(f"{task_id} is not a task number such as T-043 or T-043-A.")
    if git(repo, "status", "--porcelain").stdout.strip():
        raise ClaimError("You have uncommitted changes. Commit or stash them, then claim.")
    git(repo, "fetch", "-q", remote, base)
    branch = PREFIX + task_id
    if task_id in remote_claims(repo, remote):
        raise ClaimError(f"{task_id} is already claimed (branch {branch} exists). Pick another task.")

    original = _current_branch(repo)
    git(repo, "switch", "-q", "-c", branch, f"{remote}/{base}")
    try:
        tasks = task_files.load(repo / "tasks")
        task = next((t for t in tasks if t.id == task_id), None)
        if task is None or task.in_done_folder:
            raise ClaimError(f"There is no open task {task_id} on {base}.")
        if task.state != "open":
            raise ClaimError(f"{task_id} is not open (its status is: {task.status}).")
        waiting = _unfinished_needs(task, tasks)
        if waiting:
            raise ClaimError(f"{task_id} needs {', '.join(waiting)} to be finished first.")
        text = task.path.read_text(encoding="utf-8")
        date = (today or datetime.date.today()).isoformat()
        new, count = re.subn(
            r"^(- \*\*Status:\*\*).*$", rf"\1 claimed ({who}, {date})", text, count=1, flags=re.M
        )
        if count != 1:
            raise ClaimError(f"{task_id} has no Status line to change.")
        task.path.write_text(new, encoding="utf-8")
        git(repo, "add", str(task.path))
        git(repo, "commit", "-q", "-m", f"Claim {task_id}")
        # The empty value after the colon means "only if the branch does not
        # exist yet": the push fails if anyone created it since we looked.
        pushed = git(
            repo, "push", "-q", f"--force-with-lease=refs/heads/{branch}:", remote,
            f"{branch}:refs/heads/{branch}", check=False,
        )
        if pushed.returncode != 0:
            raise ClaimError(f"Someone claimed {task_id} a moment ago. Pick another task.")
    except ClaimError:
        git(repo, "switch", "-q", original, check=False)
        git(repo, "branch", "-q", "-D", branch, check=False)
        raise
    return branch


def reserve_new(repo=".", remote="origin", base="main") -> str:
    """Reserve the next free task number so two agents never create the same one."""
    repo = Path(repo)
    git(repo, "fetch", "-q", remote, base)
    tip = git(repo, "rev-parse", f"{remote}/{base}").stdout.strip()
    # Read the task numbers on the base branch, not the working tree.
    names = git(repo, "ls-tree", "-r", "--name-only", f"{remote}/{base}", "tasks").stdout
    numbers = [int(m) for m in re.findall(r"tasks/(?:done/)?T-(\d{3})", names)]
    numbers += [int(t[2:5]) for t in remote_claims(repo, remote)]
    number = max(numbers, default=0) + 1
    for _ in range(50):
        task_id = "T-%03d" % number
        pushed = git(
            repo, "push", "-q", f"--force-with-lease=refs/heads/{PREFIX}{task_id}:", remote,
            f"{tip}:refs/heads/{PREFIX}{task_id}", check=False,
        )
        if pushed.returncode == 0:
            return task_id
        number += 1
    raise ClaimError("Could not reserve a task number; try again.")


def release(task_id, repo=".", remote="origin"):
    git(repo, "push", "-q", remote, "--delete", PREFIX + task_id.upper())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("task", nargs="?", help="the task to claim, such as T-060")
    parser.add_argument("--who", default="agent", help="your name or agent id")
    parser.add_argument("--list", action="store_true", help="show claimed tasks")
    parser.add_argument("--new", action="store_true", help="reserve the next free task number")
    parser.add_argument("--release", metavar="TASK", help="delete a claim branch")
    args = parser.parse_args(argv)
    try:
        if args.list:
            for task_id in sorted(remote_claims(".")):
                print(task_id)
        elif args.new:
            task_id = reserve_new()
            print(f"Reserved {task_id}. Create tasks/{task_id}.md in your branch.")
        elif args.release:
            release(args.release)
            print(f"Released {args.release.upper()}.")
        elif args.task:
            branch = claim(args.task, args.who)
            print(
                f"Claimed {args.task.upper()} on branch {branch}. Open a pull request into main "
                "now and merge it within minutes; then do the work on a separate branch."
            )
        else:
            parser.print_help()
            return 2
    except ClaimError as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
