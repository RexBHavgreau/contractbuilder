from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_every_markdown_runtime_dependency_has_a_license_notice():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    notices = (ROOT / "THIRD-PARTY-LICENSES.txt").read_text(encoding="utf-8")

    for package, version in (("markdown-it-py", "3.0.0"), ("mdurl", "0.1.2")):
        assert f"{package}=={version}" in requirements
        assert package in notices
        assert version in notices
        assert "MIT License" in notices
        assert "Permission is hereby granted" in notices
