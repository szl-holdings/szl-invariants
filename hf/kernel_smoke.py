# SPDX-License-Identifier: Apache-2.0
"""Smoke hook for hf-kernel-publish (szl-invariants).

`smoke(kernel)` receives the module that the `kernels` loader imported, from a local
build (check-local) or from the Hub (verify). Raise, or return False, to fail the run.
CPU-only, deterministic and offline. The result's repr is written to the receipt.

The checks are the same falsifiability contract scripts/verify_installed.py applies to
the PyPI wheel: a clean demo chain HOLDS, a tampered one is VIOLATED, and Ed25519
without a public key stays UNAVAILABLE (never coerced to a pass).
"""
from __future__ import annotations

import json
from pathlib import Path


def smoke(kernel):
    result = kernel.selfcheck()
    expected = {
        "clean_chain_status": "HOLDS",
        "tampered_chain_status": "VIOLATED",
        "ed25519_without_key": "UNAVAILABLE",
        "falsifiable_demonstrated": True,
        "checks_registered": 8,
    }
    wrong = {k: result.get(k) for k, v in expected.items() if result.get(k) != v}
    if wrong:
        raise AssertionError(f"selfcheck contract failed: {wrong}")
    metadata = json.loads((Path(kernel.__file__).parent / "metadata.json").read_text(encoding="utf-8"))
    if metadata["version"] != kernel.__version__ or result["version"] != kernel.__version__:
        raise AssertionError("package metadata.json, __version__ and selfcheck() disagree on the version")
    if metadata["trained_weights_present"] is not False or kernel.PROVENANCE["trained_weights_present"] is not False:
        raise AssertionError("the kernel must keep declaring that no trained weights are present")
    return {"version": kernel.__version__, **{k: result[k] for k in expected}}
