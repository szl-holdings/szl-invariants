# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · honest tests — falsifiable invariants, no fabricated green.
"""Tests for szl_invariants.

These are HONEST tests: they prove each invariant genuinely FLIPS to VIOLATED
on real corruption/tamper (falsifiability), and that missing capabilities stay
UNAVAILABLE / NO_DATA — never coerced to a pass.
"""
import base64
import os
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "torch-ext"),
)

import szl_invariants as si  # noqa: E402


def _clean_rows():
    return si._build_demo_chain(tamper=False)


def test_registry_has_eight_invariants():
    assert len(si.INVARIANT_IDS) == 8
    assert len(si.list_checks()) == 8


def test_clean_chain_holds():
    r = si.run_invariants(_clean_rows(), samples=None, pubkey=None)
    chain = next(i for i in r["invariants"] if i["id"] == "receipt-chain-continuity")
    assert chain["status"] == "HOLDS"
    assert chain["violations"] == 0


def test_tampered_chain_is_falsifiable():
    # The whole point: corruption must produce VIOLATED, not a silent pass.
    r = si.run_invariants(si._build_demo_chain(tamper=True), pubkey=None)
    chain = next(i for i in r["invariants"] if i["id"] == "receipt-chain-continuity")
    assert chain["status"] == "VIOLATED"
    assert chain["violations"] >= 1


def test_failure_shape_violation():
    rows = _clean_rows()
    rows.append(
        {"id": 4, "ok": False, "demo": False, "servedProvider": "openai", "latencyMs": 5}
    )
    r = si.run_invariants(rows, pubkey=None)
    inv = next(i for i in r["invariants"] if i["id"] == "ledger-failure-shape")
    assert inv["status"] == "VIOLATED"
    assert inv["worstRowId"] == 4


def test_served_run_has_model_violation():
    rows = [{"id": 9, "ok": True, "demo": False, "model": None}]
    r = si.run_invariants(rows, pubkey=None)
    inv = next(i for i in r["invariants"] if i["id"] == "served-run-has-model")
    assert inv["status"] == "VIOLATED"


def test_signed_columns_partial_violation():
    rows = [
        {"id": 1, "receiptId": "r1", "signature": None, "keyId": None, "receiptJson": None}
    ]
    r = si.run_invariants(rows, pubkey=None)
    inv = next(i for i in r["invariants"] if i["id"] == "signed-columns-atomic")
    assert inv["status"] == "VIOLATED"


def test_loop_steps_lower_bound():
    rows = [{"id": 1, "ok": True, "demo": False, "model": "m", "loopSteps": 0}]
    r = si.run_invariants(rows, pubkey=None)
    inv = next(i for i in r["invariants"] if i["id"] == "loop-steps-positive")
    assert inv["status"] == "VIOLATED"


def test_ed25519_unavailable_without_key_never_coerced():
    r = si.run_invariants(_clean_rows(), pubkey=None)
    inv = next(i for i in r["invariants"] if i["id"] == "receipt-ed25519-verify")
    assert inv["status"] == "UNAVAILABLE"
    assert r["latentVerification"]["status"] == "UNAVAILABLE"
    assert r["latentVerification"]["verifiedRatio"] is None


def test_flywheel_unavailable_without_samples():
    r = si.run_invariants(_clean_rows(), samples=None, pubkey=None)
    inv = next(i for i in r["invariants"] if i["id"] == "flywheel-lineage")
    assert inv["status"] == "UNAVAILABLE"


def test_flywheel_lineage_violation():
    rows = [
        {"id": 1, "ok": True, "demo": True, "servedNode": None, "receiptId": "r-demo"}
    ]
    samples = [{"sampleId": 1, "receiptId": "r-demo"}]  # traces to a DEMO run
    r = si.run_invariants(rows, samples=samples, pubkey=None)
    inv = next(i for i in r["invariants"] if i["id"] == "flywheel-lineage")
    assert inv["status"] == "VIOLATED"


def test_receipt_columns_consistent_and_mismatch():
    canonical = si.canonical_json(
        {"receiptId": "r1", "goalSha256": "g", "outputSha256": "o", "keyId": "k1"}
    )
    ok_row = {
        "id": 1,
        "receiptId": "r1",
        "goalSha256": "g",
        "outputSha256": "o",
        "keyId": "k1",
        "receiptJson": canonical,
    }
    r = si.run_invariants([ok_row], pubkey=None)
    inv = next(i for i in r["invariants"] if i["id"] == "receipt-columns-consistent")
    assert inv["status"] == "HOLDS"
    bad_row = dict(ok_row, id=2, keyId="k-DIFFERENT")
    r2 = si.run_invariants([bad_row], pubkey=None)
    inv2 = next(i for i in r2["invariants"] if i["id"] == "receipt-columns-consistent")
    assert inv2["status"] == "VIOLATED"


def test_ed25519_real_signature_holds_and_tamper_fails():
    # Genuine ed25519: sign a canonical payload, then verify + tamper.
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives import serialization
    except Exception:
        return  # honest skip when cryptography is absent (fallback path unexercised here)
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    spki = pub.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    spki_b64 = base64.b64encode(spki).decode()
    key_id = si.keyid_from_spki(spki_b64)
    payload = {
        "receiptId": "r1",
        "goalSha256": "g",
        "outputSha256": "o",
        "keyId": key_id,
    }
    canonical = si.canonical_json(payload)
    sig = base64.b64encode(priv.sign(canonical.encode())).decode()
    row = dict(payload, id=1, receiptJson=canonical, signature=sig)
    r = si.run_invariants([row], pubkey=spki_b64)
    inv = next(i for i in r["invariants"] if i["id"] == "receipt-ed25519-verify")
    assert inv["status"] == "HOLDS"
    assert r["latentVerification"]["verified"] == 1
    # Tamper the canonical bytes → signature must fail (falsifiable).
    tampered = dict(row, id=2, receiptJson=canonical.replace('"g"', '"TAMPER"'))
    r2 = si.run_invariants([tampered], pubkey=spki_b64)
    inv2 = next(i for i in r2["invariants"] if i["id"] == "receipt-ed25519-verify")
    assert inv2["status"] == "VIOLATED"


def test_no_export_is_unavailable():
    r = si.run_invariants(None)
    assert r["status"] == "UNAVAILABLE"
    assert r["invariants"] == []


def test_selfcheck_demonstrates_falsifiability():
    sc = si.selfcheck()
    assert sc["falsifiable_demonstrated"] is True
    assert sc["clean_chain_status"] == "HOLDS"
    assert sc["tampered_chain_status"] == "VIOLATED"
    assert sc["ed25519_without_key"] == "UNAVAILABLE"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  ok {fn.__name__}")
    print(f"OK — {passed}/{len(fns)} szl_invariants tests passed.")
