# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""szl_invariants — falsifiable runtime self-consistency invariants, offline.

============================ HONEST SCOPE BOX ============================
The governance kernel below is NOT a trained model. Since surrogate v1 this
repo ALSO ships a REAL trained companion model (model.joblib, sklearn) with
MEASURED fidelity — see TRAINING_RECEIPT.json. The kernel remains the sole
ground truth; the surrogate is fast triage and NEVER replaces replay.
The kernel itself is a pure-Python, stdlib-only governance kernel: it *replays* the same eight
FALSIFIABLE runtime invariants the a11oy backbone recomputes live (see
/api/invariants) over a receipts/ledger JSONL export you hold — fully offline,
no network, no torch. `get_kernel`-discoverable purely so the family loads the
same way; it does not use tensors.

DOCTRINE (mirrors artifacts/api-server/src/routes/invariants.ts):
  - Every invariant here is genuinely FALSIFIABLE: real ledger corruption,
    receipt tamper, or a write-path regression can VIOLATE it. A check that
    cannot fail would be verification theater and is DELIBERATELY EXCLUDED.
  - Statuses are NEVER coerced: HOLDS / VIOLATED / KEY_ROTATED / NO_DATA /
    UNAVAILABLE are all first-class. NO_DATA (nothing to check) and UNAVAILABLE
    (a capability is absent, e.g. no public key supplied) are never silently
    upgraded to a pass.
  - Λ (governance trust) is NOT touched here and stays Conjecture 1 — none of
    these invariants prove or upgrade it. They check the ledger's shape and its
    cryptographic self-consistency, not runtime correctness of any answer.
  - Counts are ENUMERATED rows only, never a claimed total.
=========================================================================

Quickstart (offline):

    from kernels import get_kernel
    inv = get_kernel("SZLHOLDINGS/szl-invariants", revision="main", trust_remote_code=True)

    rows = inv.load_jsonl("runs_export.jsonl")          # your ledger export
    samples = inv.load_jsonl("training_samples.jsonl")  # optional flywheel export
    pubkey = "<SPKI base64 from /api/receipts/pubkey>"  # optional — enables ed25519

    report = inv.run_invariants(rows, samples=samples, pubkey=pubkey)
    print(report["summary"])       # {'total':8,'holds':..,'violated':..,'indeterminate':..}
    for i in report["invariants"]:
        print(i["id"], i["status"], i["detail"])
"""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "run_invariants",
    "load_jsonl",
    "sha256_hex",
    "canonical_json",
    "recompute_row_hash",
    "content_hash",
    "verify_ed25519",
    "keyid_from_spki",
    "selfcheck",
    "list_checks",
    "INVARIANT_IDS",
    "DOCTRINE",
    "NOTE",
    "LATENT_VERIFICATION_NOTE",
    "PROVENANCE",
    "DOCTRINE_FOOTER",
    "__version__",
]

__version__ = "0.1.0"

Status = str  # "HOLDS" | "VIOLATED" | "KEY_ROTATED" | "NO_DATA" | "UNAVAILABLE"

DOCTRINE = (
    "Runtime self-consistency invariants — MEASURED, recomputed over the "
    "enumerated ledger export. DISTINCT from the Lean proof corpus: none of "
    "them prove or upgrade Λ, which stays Conjecture 1. The Ouroboros closes "
    "on its own tail — the receipt chain recomputes its own prior hashes, and "
    "the flywheel consumes only its own verified own-metal serves."
)

NOTE = (
    "Every invariant shown is FALSIFIABLE: it can be VIOLATED by real ledger "
    "corruption, receipt tamper, or a write-path regression. A check that "
    "cannot fail would be verification theater and is deliberately excluded. "
    "Count is enumerated rows only, never a claimed total."
)

LATENT_VERIFICATION_NOTE = (
    "MEASURED coverage — fraction of the enumerated export whose trust is "
    "established purely in hash/signature space (ed25519 over sha256 canonical "
    "bytes, never plaintext). ANALOGY to the JEPA latent-space objective "
    "(verify over a compact derived space, not the raw object); the mechanism "
    "is a cryptographic digest + signature, NOT a learned embedding — nothing "
    "here is trained or predictive, and this does not prove or upgrade Λ. "
    "tamperFailed lowers the ratio; rotated (signed under a rotated key) and "
    "unsigned (rows predating signing) are honest complements, never failures."
)

PROVENANCE = {
    "mirrors": "a11oy backbone /api/invariants (artifacts/api-server/src/routes/invariants.ts)",
    "lean_repo": "szl-holdings/lutar-lean",
    "doi_lutar_lean": "10.5281/zenodo.20434308",
    "lambda_status": "Conjecture 1 (open) — uniqueness unproven; advisory only",
    "trained_weights_present": True,
    "trained_weights_role": "surrogate v1 (model.joblib) — structural triage; kernel stays ground truth; fidelity MEASURED in TRAINING_RECEIPT.json",
}

DOCTRINE_FOOTER = (
    "SZL Holdings · falsifiable invariants only (theater excluded) · statuses "
    "never coerced · Λ untouched = Conjecture 1 · honesty over checklist"
)

INVARIANT_IDS = [
    "receipt-chain-continuity",
    "ledger-failure-shape",
    "served-run-has-model",
    "signed-columns-atomic",
    "loop-steps-positive",
    "receipt-ed25519-verify",
    "receipt-columns-consistent",
    "flywheel-lineage",
]


# --------------------------------------------------------------------------- #
# Canonical hashing — EXACTLY mirrors the a11oy runLedger + receipts helpers   #
# (sha256 hex; canonical JSON = recursively key-sorted, no whitespace).        #
# --------------------------------------------------------------------------- #
def sha256_hex(text: str) -> str:
    """sha256 hex of a UTF-8 string (mirror of receipts.sha256Hex)."""
    return sha256(text.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    """Recursively key-sorted, whitespace-free JSON — mirror of
    receipts.canonicalJson. `None` (JS null) is kept; keys mapping to `None`
    that represent an absent field are still serialized as null (the a11oy
    core-facts object never carries `undefined`)."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonical_json(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = sorted(k for k in value.keys() if value[k] is not _UNDEFINED)
        return "{" + ",".join(
            json.dumps(k, ensure_ascii=False, separators=(",", ":"))
            + ":"
            + canonical_json(value[k])
            for k in keys
        ) + "}"
    raise TypeError(f"cannot canonicalize {type(value)!r}")


class _Undefined:
    __slots__ = ()


_UNDEFINED = _Undefined()


def content_hash(row: Dict[str, Any]) -> str:
    """Recompute a row's contentHash exactly as runLedger.insertRow does: the
    signed canonical receipt when present, else canonical core-facts."""
    receipt_json = row.get("receiptJson")
    if receipt_json is not None:
        return sha256_hex(receipt_json)
    core = {
        "endpoint": row.get("endpoint"),
        "mode": row.get("mode"),
        "requestedProvider": row.get("requestedProvider"),
        "servedProvider": row.get("servedProvider"),
        "model": row.get("model"),
        "servedNode": row.get("servedNode"),
        "demo": row.get("demo"),
        "ok": row.get("ok"),
        "latencyMs": row.get("latencyMs"),
        "error": row.get("error"),
    }
    return sha256_hex(canonical_json(core))


def recompute_row_hash(prev_hash: str, row: Dict[str, Any]) -> str:
    """rowHash = sha256Hex(`${prevHash}|${contentHash}`) — mirror of insertRow."""
    return sha256_hex(f"{prev_hash}|{content_hash(row)}")


def keyid_from_spki(spki_base64: str) -> str:
    """keyId = first 16 hex of sha256(SPKI DER) — mirror of receipts.deriveKeys."""
    import base64

    der = base64.b64decode(spki_base64)
    return sha256(der).hexdigest()[:16]
