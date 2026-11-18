import pathlib
import subprocess
import sys


SCRIPT = pathlib.Path(__file__).with_name("sample.py")


def test_sample_script_defaults_to_current_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (tmp_path / "Sample Services Agreement.docx").is_file()
    assert not (tmp_path / "examples").exists()
    assert result.stdout.strip() == str(tmp_path / "Sample Services Agreement.docx")


def test_sample_script_accepts_an_explicit_output_path(tmp_path):
    output = tmp_path / "custom" / "chosen.docx"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(output)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert output.is_file()
    assert result.stdout.strip() == str(output)
