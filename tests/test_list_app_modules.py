"""The comparison build lists every application module by itself (T-035)."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import list_app_modules  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_known_modules_are_listed_and_the_three_exclusions_are_not():
    names = list_app_modules.app_modules()
    for wanted in ("core", "library", "component_editor", "docx_to_markdown",
                   "markdown_files", "shell_selection", "assembly_builder", "field_matching"):
        assert wanted in names
    for left_out in ("app", "simple_app", "tests", "scripts"):
        assert left_out not in names


def test_the_exclusions_are_exactly_the_three_documented_ones():
    # Adding a name here hides a module from the size gate: do it on purpose.
    assert list_app_modules.EXCLUDED == {"app", "simple_app"}


def test_every_top_level_module_in_the_repository_is_listed_or_excluded():
    names = set(list_app_modules.app_modules())
    for path in ROOT.glob("*.py"):
        assert path.stem in names or path.stem in list_app_modules.EXCLUDED, path.name
    for folder in ROOT.iterdir():
        if folder.is_dir() and (folder / "__init__.py").is_file():
            assert folder.name in names or folder.name in list_app_modules.NOT_APP_FOLDERS


def test_a_new_module_or_package_is_picked_up_without_editing_anything(tmp_path):
    (tmp_path / "invented_module.py").write_text("X = 1\n")
    (tmp_path / "invented_package").mkdir()
    (tmp_path / "invented_package" / "__init__.py").write_text("")
    (tmp_path / "simple_app.py").write_text("")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "__init__.py").write_text("")
    (tmp_path / "docs").mkdir()          # a folder without __init__.py is not a package
    assert list_app_modules.app_modules(tmp_path) == ["invented_module", "invented_package"]
