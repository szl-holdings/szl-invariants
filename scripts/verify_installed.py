#!/usr/bin/env python3
"""Smoke the installed distribution from outside its source checkout with -I."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.resources
import json
from pathlib import Path
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("wheel", "editable"))
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    current = Path.cwd().resolve()
    if not sys.flags.isolated:
        raise RuntimeError("must run Python with -I")
    if current == root or root in current.parents:
        raise RuntimeError("must run from outside the source checkout")

    # Deliberately no sys.path mutation or source-path import fallback.
    import szl_invariants as kernel

    module_path = Path(kernel.__file__).resolve()
    if args.mode == "wheel":
        if root in module_path.parents or Path(sys.prefix).resolve() not in module_path.parents:
            raise RuntimeError("wheel smoke imported a source checkout, not the installed environment")
    elif module_path != (root / "torch-ext/szl_invariants/__init__.py").resolve():
        raise RuntimeError("editable smoke did not resolve the declared package directory")

    contract = json.loads((root / "publishing/invariants-source-binding.json").read_text(encoding="utf-8"))
    metadata_bytes = importlib.resources.files("szl_invariants").joinpath("metadata.json").read_bytes()
    for path, content in [("torch-ext/szl_invariants/__init__.py", module_path.read_bytes()),
                          ("torch-ext/szl_invariants/metadata.json", metadata_bytes)]:
        observed = hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()
        if observed != contract["expected_artifact_sha256"][path]:
            raise RuntimeError(f"installed canonical LF hash mismatch: {path}")
    metadata = json.loads(metadata_bytes)
    version = importlib.metadata.version("szl-invariants")
    if metadata["version"] != version or metadata["trained_weights_present"] is not False:
        raise RuntimeError("installed metadata identity/weight declaration mismatch")
    result = kernel.selfcheck()
    if (result["clean_chain_status"], result["tampered_chain_status"], result["ed25519_without_key"]) != ("HOLDS", "VIOLATED", "UNAVAILABLE"):
        raise RuntimeError("installed selfcheck contract failed")
    print(json.dumps({"status": "PASS", "mode": args.mode, "version": version,
                      "module": str(module_path), "metadata_present": True,
                      "canonical_source_and_metadata_hashes": "MATCH", "selfcheck": result}))


if __name__ == "__main__":
    main()
