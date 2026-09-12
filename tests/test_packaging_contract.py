"""Close package discovery; install smoke is exercised in dedicated CI."""
from __future__ import annotations

import ast
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9 and 3.10 use the test-only backport.
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_explicit_package_and_metadata_discovery() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["build-system"] == {
        "requires": [
            "setuptools==82.0.1; python_version < '3.10'",
            "setuptools==83.0.0; python_version >= '3.10'",
        ],
        "build-backend": "setuptools.build_meta",
    }
    setuptools = config["tool"]["setuptools"]
    assert setuptools["packages"] == ["szl_invariants"]
    assert setuptools["package-dir"] == {"": "torch-ext"}
    assert setuptools["package-data"] == {"szl_invariants": ["metadata.json"]}
    assert setuptools["include-package-data"] is False


def test_python39_support_has_conditional_test_parser_and_ci_coverage() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]
    assert project["requires-python"] == ">=3.9"
    assert project.get("dependencies", []) == []
    assert project["optional-dependencies"]["dev"] == [
        "tomli==2.4.1; python_version < '3.11'"
    ]
    workflow = (ROOT / ".github/workflows/base-python-ci.yml").read_text(
        encoding="utf-8"
    )
    assert 'python-version: ["3.9", "3.11", "3.12"]' in workflow
    assert 'python -m pip install -e ".[dev]"' in workflow


def test_installed_smoke_has_no_source_path_fallback() -> None:
    source = (ROOT / "scripts/verify_installed.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert "sys.path.insert" not in source
    assert "spec_from_file_location" not in source
    assert "sys.flags.isolated" in source
    assert "metadata.json" in source
    workflow = (ROOT / ".github/workflows/cpu-contract.yml").read_text(encoding="utf-8")
    assert "--mode wheel" in workflow
    assert "--mode editable" in workflow
    assert 'cd "$RUNNER_TEMP"' in workflow
