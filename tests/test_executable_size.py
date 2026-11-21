import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_executable_size.py"


def run_check(executable, *arguments):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(executable), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_default_30_mib_limit_accepts_built_file(tmp_path):
    executable = tmp_path / "application.exe"
    executable.write_bytes(b"x" * 128)

    result = run_check(executable)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "31,457,280 bytes (30.00 MiB)" in result.stdout
    assert "PASS:" in result.stdout
    assert "headroom remain" in result.stdout


def test_deliberately_tiny_limit_fails_for_oversized_file(tmp_path):
    executable = tmp_path / "application.exe"
    executable.write_bytes(b"xx")

    result = run_check(executable, "--max-bytes", "1")

    assert result.returncode == 1
    assert "Built executable: 2 bytes" in result.stdout
    assert "exceeds the limit by 1 bytes" in result.stdout


def test_file_exactly_at_limit_passes(tmp_path):
    executable = tmp_path / "application.exe"
    executable.write_bytes(b"x" * 10)

    result = run_check(executable, "--max-bytes", "10")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: 0 bytes" in result.stdout


def test_headroom_floor_fails_below_the_minimum(tmp_path):
    executable = tmp_path / "application.exe"
    executable.write_bytes(b"x" * 90)

    result = run_check(executable, "--max-bytes", "100", "--min-headroom", "20")

    assert result.returncode == 1
    assert "only 10 bytes" in result.stdout
    assert "tell Beaux" in result.stdout


def test_headroom_floor_passes_when_there_is_enough_room(tmp_path):
    executable = tmp_path / "application.exe"
    executable.write_bytes(b"x" * 50)

    result = run_check(executable, "--max-bytes", "100", "--min-headroom", "20")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: 50 bytes" in result.stdout

