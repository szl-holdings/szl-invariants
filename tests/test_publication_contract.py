from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "publishing" / "invariants-source-binding.json"

EXPECTED_ARTIFACTS = {
    "build/torch-universal/szl_invariants/__init__.py": (
        "865b34d7196a657f2b9f7cdb3aca615332592d01ebcf0cd9ffd68ad9a4c5abbf"
    ),
    "build/torch-universal/szl_invariants/metadata.json": (
        "4689bab3b861bafc7911b9e70e79e3f1685473c94fff3549116d6793f6f2f4c9"
    ),
    "torch-ext/szl_invariants/__init__.py": (
        "865b34d7196a657f2b9f7cdb3aca615332592d01ebcf0cd9ffd68ad9a4c5abbf"
    ),
    "torch-ext/szl_invariants/metadata.json": (
        "4689bab3b861bafc7911b9e70e79e3f1685473c94fff3549116d6793f6f2f4c9"
    ),
}

EXPECTED_TARGETS = {
    (
        "model",
        "build/torch-universal/szl_invariants/__init__.py",
        "build/torch-universal/szl_invariants/__init__.py",
    ),
    (
        "model",
        "build/torch-universal/szl_invariants/metadata.json",
        "build/torch-universal/szl_invariants/metadata.json",
    ),
    (
        "kernel",
        "build/torch-universal/szl_invariants/__init__.py",
        "build/torch-universal/szl_invariants/__init__.py",
    ),
    (
        "kernel",
        "build/torch-universal/szl_invariants/metadata.json",
        "build/torch-universal/szl_invariants/metadata.json",
    ),
    (
        "kernel",
        "torch-ext/szl_invariants/__init__.py",
        "build/torch-cpu/szl_invariants/__init__.py",
    ),
}


def _git_blob(path: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"HEAD:{path}"],
        cwd=ROOT,
    )


def _validate_contract(payload: dict[str, object]) -> None:
    if payload.get("schema") != "szl.invariants-source-binding/v1":
        raise AssertionError("unexpected publication-contract schema")
    if payload.get("repo_id") != "SZLHOLDINGS/szl-invariants":
        raise AssertionError("publication contract selected another Hub repository")
    if payload.get("source_repository") != "szl-holdings/szl-invariants":
        raise AssertionError("publication contract selected another source repository")

    artifacts = payload.get("artifact_files")
    if not isinstance(artifacts, list) or set(artifacts) != set(EXPECTED_ARTIFACTS):
        raise AssertionError("artifact_files must equal the closed publication set")
    if len(artifacts) != len(set(artifacts)):
        raise AssertionError("artifact_files must not contain duplicates")
    if payload.get("expected_artifact_sha256") != EXPECTED_ARTIFACTS:
        raise AssertionError("expected hashes must bind every declared artifact")

    targets = payload.get("publication_targets")
    if not isinstance(targets, list):
        raise AssertionError("publication_targets must be a list")
    observed_targets = {
        (target.get("repo_type"), target.get("source_path"), target.get("path_in_repo"))
        for target in targets
        if isinstance(target, dict)
    }
    if len(observed_targets) != len(targets) or observed_targets != EXPECTED_TARGETS:
        raise AssertionError("publication targets must equal the closed destination set")

    claims = payload.get("claims")
    if not isinstance(claims, dict) or claims.get("trained_weights_present") is not False:
        raise AssertionError("publication contract must deny trained weights")


class PublicationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_is_closed_and_hash_bound(self) -> None:
        _validate_contract(self.payload)
        for path, expected in EXPECTED_ARTIFACTS.items():
            self.assertEqual(hashlib.sha256(_git_blob(path)).hexdigest(), expected)

    def test_variants_are_identical_and_deny_trained_weights(self) -> None:
        universal = _git_blob("build/torch-universal/szl_invariants/__init__.py")
        extension = _git_blob("torch-ext/szl_invariants/__init__.py")
        self.assertEqual(universal, extension)
        self.assertIn(b'"trained_weights_present": False', universal)
        self.assertNotIn(b'"trained_weights_present": True', universal)

        universal_metadata = _git_blob(
            "build/torch-universal/szl_invariants/metadata.json"
        )
        extension_metadata = _git_blob("torch-ext/szl_invariants/metadata.json")
        self.assertEqual(universal_metadata, extension_metadata)
        self.assertIn(b'"trained_weights_present": false', universal_metadata)
        self.assertNotIn(b'"trained_weights_present": true', universal_metadata)

    def test_unlisted_artifact_fails_closed(self) -> None:
        changed = copy.deepcopy(self.payload)
        changed["artifact_files"].append("README.md")
        with self.assertRaisesRegex(AssertionError, "closed publication set"):
            _validate_contract(changed)

    def test_altered_target_fails_closed(self) -> None:
        changed = copy.deepcopy(self.payload)
        changed["publication_targets"][0]["path_in_repo"] = "README.md"
        with self.assertRaisesRegex(AssertionError, "closed destination set"):
            _validate_contract(changed)


if __name__ == "__main__":
    unittest.main()
