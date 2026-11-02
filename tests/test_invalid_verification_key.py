"""An unusable verification key cannot establish a key-rotation verdict."""
from __future__ import annotations

import base64
import importlib.util
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "torch-ext/szl_invariants/__init__.py"
SPEC = importlib.util.spec_from_file_location("verification_key_kernel", SOURCE)
assert SPEC is not None and SPEC.loader is not None
kernel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kernel)


def encoded(raw):
    return base64.b64encode(raw).decode("ascii")


def signature_check(report):
    return next(item for item in report["invariants"] if item["id"] == "receipt-ed25519-verify")


def assert_unusable_key_is_unavailable(public):
    # Preserve an independently detectable ledger error while the crypto
    # capability is unavailable. Bad key input must not suppress that check.
    row = {"id": 9, "ok": False, "servedProvider": "unexpected",
           "receiptJson": "{}", "signature": "AA==", "keyId": "old-key"}
    report = kernel.run_invariants([row], pubkey=public)
    result = signature_check(report)
    assert result["status"] == "UNAVAILABLE"
    assert result["checked"] == result["violations"] == 0
    assert "public key" in result["detail"]
    latent = report["latentVerification"]
    assert latent["status"] == "UNAVAILABLE"
    assert latent["verifiedRatio"] is None
    assert latent["verified"] == latent["rotated"] == latent["tamperFailed"] == 0
    failure_shape = next(item for item in report["invariants"] if item["id"] == "ledger-failure-shape")
    assert failure_shape["status"] == "VIOLATED"
    assert failure_shape["worstRowId"] == 9


@pytest.mark.parametrize("public", ["", "!!!!", "not base64", encoded(b"not an SPKI key"), encoded(bytes(32))])
def test_malformed_public_key_does_not_claim_rotation_or_crash(public):
    pytest.importorskip("cryptography")
    assert_unusable_key_is_unavailable(public)


def test_wrong_algorithm_is_not_an_ed25519_verification_capability():
    ec = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ec")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    public = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assert_unusable_key_is_unavailable(encoded(public))


def test_valid_verification_and_real_key_rotation_remain_distinct():
    ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    signer = ed25519.Ed25519PrivateKey.generate()

    def spki(key):
        return encoded(key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    public = spki(signer)
    row = {"id": 1, "receiptJson": "{}", "signature": encoded(signer.sign(b"{}")),
           "keyId": kernel.keyid_from_spki(public)}
    valid = kernel.run_invariants([row], pubkey=public)
    assert signature_check(valid)["status"] == "HOLDS"
    assert valid["latentVerification"]["verifiedRatio"] == 1.0

    assert_unusable_key_is_unavailable(public + "!")
    current = spki(ed25519.Ed25519PrivateKey.generate())
    rotated = kernel.run_invariants([row], pubkey=current)
    assert signature_check(rotated)["status"] == "KEY_ROTATED"
    assert rotated["latentVerification"]["rotated"] == 1
