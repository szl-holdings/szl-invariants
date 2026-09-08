"""Close package discovery; install smoke is exercised in dedicated CI."""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_explicit_package_and_metadata_discovery() -> None:
    import tomllib

    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["build-system"] == {"requires": ["setuptools==83.0.0"], "build-backend": "setuptools.build_meta"}
    setuptools = config["tool"]["setuptools"]
    assert setuptools["packages"] == ["szl_invariants"]
    assert setuptools["package-dir"] == {"": "torch-ext"}
    assert setuptools["package-data"] == {"szl_invariants": ["metadata.json"]}
    assert setuptools["include-package-data"] is False


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
