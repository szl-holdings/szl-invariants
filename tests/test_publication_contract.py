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
        "3f7c7afb5143c08cde920493ad1e61613ac990cea334b0159c933d4fb2a7ee90"
    ),
    "build/torch-universal/szl_invariants/metadata.json": (
        "4e645a7b019a3893a2cb64be6471f19f3c7572e1f1b29e799035f1d298a55039"
    ),
    "torch-ext/szl_invariants/__init__.py": (
        "3f7c7afb5143c08cde920493ad1e61613ac990cea334b0159c933d4fb2a7ee90"
    ),
    "torch-ext/szl_invariants/metadata.json": (
        "4e645a7b019a3893a2cb64be6471f19f3c7572e1f1b29e799035f1d298a55039"
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
    (
        "kernel",
        "torch-ext/szl_invariants/metadata.json",
        "build/torch-cpu/szl_invariants/metadata.json",
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


def _validate_package_publication(payload: dict[str, object]) -> None:
    """Derive completeness from installed package members, not EXPECTED_TARGETS."""
    import tomllib

    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    setuptools = config["tool"]["setuptools"]
    expected = set()
    for package in setuptools["packages"]:
        package_path = Path(*package.split("."))
        source_path = Path(setuptools["package-dir"][""]) / package_path
        source_root = ROOT / source_path
        members = {path.name for path in source_root.glob("*.py")}
        for pattern in setuptools["package-data"].get(package, []):
            matches = list(source_root.glob(pattern))
            if not matches:
                raise AssertionError("declared package data must exist")
            members.update(path.relative_to(source_root).as_posix() for path in matches)
        for member in members:
            for repo_type, variant in (
                ("model", "torch-universal"),
                ("kernel", "torch-universal"),
                ("kernel", "torch-cpu"),
            ):
                destination = Path("build") / variant / package_path / member
                source = (
                    source_path / member if variant == "torch-cpu" else destination
                )
                expected.add((repo_type, source.as_posix(), destination.as_posix()))

    targets = payload["publication_targets"]
    observed = [
        (target["repo_type"], target["source_path"], target["path_in_repo"])
        for target in targets
    ]
    if len(observed) != len(expected) or set(observed) != expected:
        raise AssertionError("every publication variant must contain the complete package")
    sources = {source for _repo_type, source, _destination in expected}
    if sources != set(payload["artifact_files"]):
        raise AssertionError("every published package member must be hash-bound")


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

    def test_every_packaged_file_is_published_in_every_variant(self) -> None:
        _validate_package_publication(self.payload)

    def test_each_missing_target_fails_both_contracts(self) -> None:
        for index, target in enumerate(self.payload["publication_targets"]):
            with self.subTest(target=target):
                changed = copy.deepcopy(self.payload)
                del changed["publication_targets"][index]
                with self.assertRaisesRegex(AssertionError, "closed destination set"):
                    _validate_contract(changed)
                with self.assertRaisesRegex(AssertionError, "complete package"):
                    _validate_package_publication(changed)

    def test_cpu_metadata_cannot_be_replaced_by_another_source(self) -> None:
        changed = copy.deepcopy(self.payload)
        target = next(
            target for target in changed["publication_targets"]
            if target["path_in_repo"] == "build/torch-cpu/szl_invariants/metadata.json"
        )
        target["source_path"] = "build/torch-universal/szl_invariants/metadata.json"
        with self.assertRaisesRegex(AssertionError, "closed destination set"):
            _validate_contract(changed)
        with self.assertRaisesRegex(AssertionError, "complete package"):
            _validate_package_publication(changed)

    def test_duplicate_target_cannot_hide_a_missing_package_member(self) -> None:
        changed = copy.deepcopy(self.payload)
        changed["publication_targets"][-1] = copy.deepcopy(
            changed["publication_targets"][-2]
        )
        with self.assertRaisesRegex(AssertionError, "closed destination set"):
            _validate_contract(changed)
        with self.assertRaisesRegex(AssertionError, "complete package"):
            _validate_package_publication(changed)


if __name__ == "__main__":
    unittest.main()
