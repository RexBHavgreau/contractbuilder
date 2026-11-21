"""The CI size table (T-035)."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import size_report  # noqa: E402

MIB = 1024 * 1024


def test_table_shows_sizes_and_headroom():
    text = size_report.report(20 * MIB, 22 * MIB)
    assert "| Release build | 20,971,520 | 20.00 | 10.00 |" in text
    assert "| With component modules forced in | 23,068,672 | 22.00 | 8.00 |" in text
    assert "| Added by the component modules | 2,097,152 | 2.00 | |" in text
    assert "last release" not in text


def test_growth_since_last_release_is_signed():
    assert "+1,048,576 | +1.00" in size_report.report(21 * MIB, 22 * MIB, previous=20 * MIB)
    assert "-1,048,576 | -1.00" in size_report.report(19 * MIB, 22 * MIB, previous=20 * MIB)


def test_main_reads_file_sizes(tmp_path, capsys):
    a, b = tmp_path / "a.exe", tmp_path / "b.exe"
    a.write_bytes(b"x" * 100)
    b.write_bytes(b"x" * 150)
    assert size_report.main([str(a), str(b)]) == 0
    assert "| Release build | 100 |" in capsys.readouterr().out
