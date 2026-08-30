from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_SOURCE = ROOT / "build" / "torch-universal" / "szl_invariants" / "__init__.py"
KERNEL_SOURCE = ROOT / "torch-ext" / "szl_invariants" / "__init__.py"
MODEL_METADATA = ROOT / "build" / "torch-universal" / "szl_invariants" / "metadata.json"
KERNEL_METADATA = ROOT / "torch-ext" / "szl_invariants" / "metadata.json"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _literal_assignment(tree: ast.Module, name: str):
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"missing top-level assignment: {name}")


def test_model_and_kernel_sources_match_after_line_normalization() -> None:
    assert _source(MODEL_SOURCE) == _source(KERNEL_SOURCE)


def test_quarantined_surrogate_disclosure_is_present_on_both_surfaces() -> None:
    for path in (MODEL_SOURCE, KERNEL_SOURCE):
        source = _source(path)
        tree = ast.parse(source, filename=str(path))
        docstring = ast.get_docstring(tree, clean=False) or ""
        provenance = _literal_assignment(tree, "PROVENANCE")

        assert "ships no\ntrained weights" in docstring
        assert "QUARANTINED" in docstring
        assert "ALSO ships a REAL trained companion model" not in docstring
        assert provenance["trained_weights_present"] is False
        assert "model.joblib" in provenance["trained_weights_role"]
        assert "QUARANTINED" in provenance["trained_weights_role"]


def test_metadata_rejects_trained_weight_presence_on_both_surfaces() -> None:
    for path in (MODEL_METADATA, KERNEL_METADATA):
        metadata = json.loads(path.read_text(encoding="utf-8"))

        assert metadata["artifact_kind"] == "kernel-code-and-configuration"
        assert metadata["trained_weights_present"] is False
