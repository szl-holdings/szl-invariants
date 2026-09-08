"""Close package discovery; install smoke is exercised in dedicated CI."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from packaging.requirements import Requirement


ROOT = Path(__file__).resolve().parents[1]


def test_explicit_package_and_metadata_discovery() -> None:
    import tomllib

    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["build-system"] == {
        "requires": [
            "setuptools==80.9.0; python_version < '3.10'",
            "setuptools==83.0.0; python_version >= '3.10'",
        ],
        "build-backend": "setuptools.build_meta",
    }
    assert config["project"]["requires-python"] == ">=3.9"
    setuptools = config["tool"]["setuptools"]
    assert setuptools["packages"] == ["szl_invariants"]
    assert setuptools["package-dir"] == {"": "torch-ext"}
    assert setuptools["package-data"] == {"szl_invariants": ["metadata.json"]}
    assert setuptools["include-package-data"] is False


@pytest.mark.parametrize(
    ("python_version", "expected_version"),
    [("3.9", "80.9.0"), ("3.10", "83.0.0"), ("3.11", "83.0.0"), ("3.12", "83.0.0")],
)
def test_exactly_one_build_backend_matches_supported_python(
    python_version: str, expected_version: str,
) -> None:
    import tomllib

    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirements = [Requirement(value) for value in config["build-system"]["requires"]]
    selected = [
        requirement for requirement in requirements
        if requirement.marker is not None
        and requirement.marker.evaluate({"python_version": python_version})
    ]
    assert len(selected) == 1
    assert selected[0].name == "setuptools"
    assert str(selected[0].specifier) == f"=={expected_version}"


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
    assert "python-version: ['3.9', '3.10']" in workflow
    assert "name: verify supported Python (${{ matrix.python-version }})" in workflow
