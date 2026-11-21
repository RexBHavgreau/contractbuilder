"""Which builds a CI run needs (T-035)."""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import ci_scope  # noqa: E402


@pytest.mark.parametrize("event", ["push", "schedule", "workflow_dispatch"])
def test_everything_runs_outside_pull_requests(event):
    assert ci_scope.decide(event, ["tasks/T-900.md"]) == {"windows": True, "macos": True}


def test_a_task_or_document_change_builds_nothing():
    files = ["tasks/T-900.md", "progress/2026-12-01-T-900-x.md", "TASKS.md", "CLAUDE.md", "tests/test_core.py",
             "scripts/board.py", "CHANGES.txt"]
    assert ci_scope.decide("pull_request", files) == {"windows": False, "macos": False}


def test_application_code_builds_windows_only():
    for changed in ("core.py", "component_editor/window.py", "library.py", "version.py"):
        assert ci_scope.decide("pull_request", [changed]) == {"windows": True, "macos": False}, changed


def test_files_bundled_into_the_executable_build_windows():
    for changed in ("USER-GUIDE.txt", "THIRD-PARTY-LICENSES.txt", "build-windows.ps1", "requirements.txt"):
        assert ci_scope.decide("pull_request", [changed])["windows"], changed


def test_the_size_scripts_build_windows_but_other_scripts_do_not():
    assert ci_scope.decide("pull_request", ["scripts/check_executable_size.py"])["windows"]
    assert ci_scope.decide("pull_request", ["scripts/size_report.py"])["windows"]
    assert not ci_scope.decide("pull_request", ["scripts/overlaps.py"])["windows"]


def test_macos_builds_on_a_pull_request_only_for_its_own_inputs():
    for changed in ("build-mac.command", "requirements.txt", ".github/workflows/build.yml"):
        assert ci_scope.decide("pull_request", [changed])["macos"], changed
    assert not ci_scope.decide("pull_request", ["core.py"])["macos"]


def test_the_workflow_builds_everything():
    assert ci_scope.decide("pull_request", [".github/workflows/build.yml"]) == {"windows": True, "macos": True}


def test_an_unreadable_change_list_builds_everything():
    assert ci_scope.decide("pull_request", []) == {"windows": True, "macos": True}


def test_the_output_lines_are_ready_for_github_output(capsys):
    assert ci_scope.main(["--event", "push"]) == 0
    assert capsys.readouterr().out.split() == ["windows=true", "macos=true"]
