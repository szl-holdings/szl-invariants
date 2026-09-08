"""Closed input contracts and optional audited Ed25519 capability."""
from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "torch-ext/szl_invariants/__init__.py"
SPEC = importlib.util.spec_from_file_location("fail_closed_kernel", SOURCE)
assert SPEC is not None and SPEC.loader is not None
kernel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kernel)

# Public test vector 1 from RFC 8032 section 7.1; no private key is used.
PUBLIC = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
SIGNATURE = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555f"
    "b8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
)
ORDER = 2**252 + 27742317777372353535851937790883648493
SPKI = base64.b64encode(bytes.fromhex("302a300506032b6570032100") + PUBLIC).decode()


def encoded(signature: bytes) -> str:
    return base64.b64encode(signature).decode()


def test_audited_backend_valid_rfc_vector_and_noncanonical_scalar() -> None:
    pytest.importorskip("cryptography")
    modified = SIGNATURE[:32] + (int.from_bytes(SIGNATURE[32:], "little") + ORDER).to_bytes(32, "little")
    assert kernel.verify_ed25519("", encoded(SIGNATURE), SPKI)
    assert not kernel.verify_ed25519("tampered", encoded(SIGNATURE), SPKI)
    assert not kernel.verify_ed25519("", encoded(modified), SPKI)


def test_missing_crypto_never_uses_unqualified_fallback_or_claims_verification() -> None:
    with patch.dict("sys.modules", {"cryptography.hazmat.primitives.serialization": None}):
        assert not kernel.verify_ed25519("", encoded(SIGNATURE), SPKI)
        report = kernel.run_invariants(
            [{"id": 1, "receiptJson": "{}", "signature": encoded(SIGNATURE), "keyId": kernel.keyid_from_spki(SPKI)}],
            pubkey=SPKI,
        )
    result = next(item for item in report["invariants"] if item["id"] == "receipt-ed25519-verify")
    assert result["status"] == "UNAVAILABLE"
    assert result["checked"] == 0
    assert result["violations"] == 0
    assert "cryptography" in result["detail"]
    assert report["latentVerification"]["status"] == "UNAVAILABLE"
    assert report["latentVerification"]["verifiedRatio"] is None
    assert report["latentVerification"]["verified"] == 0


@pytest.mark.parametrize("signature, public", [("!", SPKI), (encoded(SIGNATURE) + "!", SPKI), (encoded(SIGNATURE), "!"), (encoded(SIGNATURE), base64.b64encode(PUBLIC).decode())])
def test_malformed_signature_or_spki_fails_closed(signature: str, public: str) -> None:
    assert not kernel.verify_ed25519("", signature, public)


@pytest.mark.parametrize("steps", [None, float("nan"), float("inf"), -float("inf"), True, False, "1", [], {}, 0, -1, 0.5])
def test_invalid_loop_steps_are_violated(steps: object) -> None:
    report = kernel.run_invariants([{"id": 19, "ok": True, "demo": False, "model": "fixture", "loopSteps": steps}])
    result = next(item for item in report["invariants"] if item["id"] == "loop-steps-positive")
    assert result["status"] == "VIOLATED"
    assert result["violations"] == 1
    assert result["worstRowId"] == 19


@pytest.mark.parametrize("steps", [1, 2, 1.5, 10**400])
def test_existing_finite_numeric_lower_bound_contract_is_preserved(steps: object) -> None:
    report = kernel.run_invariants([{"id": 19, "ok": True, "demo": False, "model": "fixture", "loopSteps": steps}])
    result = next(item for item in report["invariants"] if item["id"] == "loop-steps-positive")
    assert result["status"] == "HOLDS"
