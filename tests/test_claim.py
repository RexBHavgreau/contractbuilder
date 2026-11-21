"""Claiming a task so that no other agent can take it (scripts/claim.py)."""
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import claim  # noqa: E402

TASK = """# T-001 First

- **Status:** open
- **Size:** S
- **Agent:** any
- **Needs:** none
"""


def run(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


@pytest.fixture
def repos(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", "-q", str(origin), str(seed)], check=True, capture_output=True)
    for key, value in (("user.email", "a@example.invalid"), ("user.name", "Agent")):
        run(seed, "config", key, value)
    (seed / "tasks" / "done").mkdir(parents=True)
    (seed / "tasks" / "T-001.md").write_text(TASK, encoding="utf-8")
    (seed / "tasks" / "T-002.md").write_text(
        TASK.replace("T-001 First", "T-002 Second").replace("none", "T-001"), encoding="utf-8")
    (seed / "tasks" / "T-003.md").write_text(
        TASK.replace("T-001 First", "T-003 Third").replace("open", "claimed (Other, 2026-01-01)"),
        encoding="utf-8")
    run(seed, "add", "-A")
    run(seed, "commit", "-q", "-m", "tasks")
    run(seed, "push", "-q", "origin", "HEAD:main")
    clones = []
    for name in ("one", "two"):
        clone = tmp_path / name
        subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
        for key, value in (("user.email", "a@example.invalid"), ("user.name", name)):
            run(clone, "config", key, value)
        clones.append(clone)
    return clones


def test_claim_creates_a_branch_with_the_status_change(repos):
    one, _ = repos
    assert claim.claim("T-001", "Agent One", repo=one) == "claim/T-001"
    assert "T-001" in claim.remote_claims(one)
    text = (one / "tasks" / "T-001.md").read_text(encoding="utf-8")
    assert "- **Status:** claimed (Agent One, " in text


def test_second_agent_is_refused_and_left_on_its_branch(repos):
    one, two = repos
    claim.claim("T-001", "One", repo=one)
    before = claim._current_branch(two)
    with pytest.raises(claim.ClaimError, match="already claimed"):
        claim.claim("T-001", "Two", repo=two)
    assert claim._current_branch(two) == before


def test_simultaneous_claims_have_one_winner(repos, monkeypatch):
    """Agent two looked before agent one pushed: the push itself must fail."""
    one, two = repos
    real = claim.remote_claims
    monkeypatch.setattr(claim, "remote_claims", lambda *a, **k: {})  # two sees nothing taken
    claim.claim("T-001", "One", repo=one)
    with pytest.raises(claim.ClaimError, match="a moment ago"):
        claim.claim("T-001", "Two", repo=two)
    monkeypatch.setattr(claim, "remote_claims", real)
    assert claim._current_branch(two) == "main"
    assert "claim/T-001" not in subprocess.run(
        ["git", "-C", str(two), "branch"], capture_output=True, text=True).stdout


def test_only_open_tasks_with_finished_needs_can_be_claimed(repos):
    one, _ = repos
    with pytest.raises(claim.ClaimError, match="not open"):
        claim.claim("T-003", "One", repo=one)
    with pytest.raises(claim.ClaimError, match="needs T-001"):
        claim.claim("T-002", "One", repo=one)
    with pytest.raises(claim.ClaimError, match="no open task"):
        claim.claim("T-009", "One", repo=one)
    with pytest.raises(claim.ClaimError, match="not a task number"):
        claim.claim("nonsense", "One", repo=one)
    assert claim.remote_claims(one) == {}


def test_uncommitted_changes_stop_a_claim(repos):
    one, _ = repos
    (one / "tasks" / "T-001.md").write_text("changed", encoding="utf-8")
    with pytest.raises(claim.ClaimError, match="uncommitted"):
        claim.claim("T-001", "One", repo=one)


def test_reserved_numbers_are_never_handed_out_twice(repos):
    one, two = repos
    first = claim.reserve_new(repo=one)
    second = claim.reserve_new(repo=two)
    assert (first, second) == ("T-004", "T-005")


def test_release_removes_the_claim(repos):
    one, _ = repos
    claim.claim("T-001", "One", repo=one)
    claim.release("T-001", repo=one)
    assert claim.remote_claims(one) == {}
