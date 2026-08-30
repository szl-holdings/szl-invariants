# SPDX-License-Identifier: Apache-2.0
# © 2026 SZL Holdings · Stephen P. Lutar · ORCID 0009-0001-0110-4173
"""szl_invariants — falsifiable runtime self-consistency invariants, offline.

============================ HONEST SCOPE BOX ============================
The governance kernel below is NOT a trained model. This repository ships no
trained weights. Historical model.joblib/sklearn surrogate artifacts are
QUARANTINED because pickle is not an approved load path; see SECURITY.md.
The kernel source is the only approved load surface and remains the sole
ground truth. It is a pure-Python, stdlib-only governance kernel that replays the same eight
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
    "trained_weights_present": False,
    "trained_weights_role": "QUARANTINED — model.joblib/pickle is not an approved load path; kernel source remains authoritative",
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


def verify_ed25519(
    canonical: str,
    signature_base64: str,
    spki_base64: str,
) -> bool:
    """ed25519 verify over the EXACT canonical bytes. Prefers the audited
    `cryptography` backend; falls back to a stdlib-only pure-Python RFC 8032
    verifier when `cryptography` is not installed (so verification is genuinely
    offline-capable). Returns False on any failure — never coerced True."""
    import base64

    try:
        sig = base64.b64decode(signature_base64)
        der = base64.b64decode(spki_base64)
    except Exception:
        return False
    msg = canonical.encode("utf-8")
    try:  # audited backend first
        from cryptography.hazmat.primitives.serialization import (
            load_der_public_key,
        )
        from cryptography.exceptions import InvalidSignature

        pub = load_der_public_key(der)
        try:
            pub.verify(sig, msg)  # type: ignore[call-arg]
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False
    except Exception:
        pass
    # stdlib-only fallback: raw key is the trailing 32 bytes of the SPKI DER.
    if len(der) < 32 or len(sig) != 64:
        return False
    raw = der[-32:]
    try:
        return _ed25519_verify_pure(raw, msg, sig)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Pure-Python ed25519 verify (RFC 8032 reference form; stdlib hashlib only).   #
# Used ONLY when `cryptography` is unavailable — keeps the kernel stdlib-only.  #
# --------------------------------------------------------------------------- #
_p = 2 ** 255 - 19
_d = (-121665 * pow(121666, _p - 2, _p)) % _p
_I = pow(2, (_p - 1) // 4, _p)
_L = 2 ** 252 + 27742317777372353535851937790883648493


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * pow(_d * y * y + 1, _p - 2, _p)
    x = pow(xx, (_p + 3) // 8, _p)
    if (x * x - xx) % _p != 0:
        x = (x * _I) % _p
    if x % 2 != 0:
        x = _p - x
    return x


_By = (4 * pow(5, _p - 2, _p)) % _p
_Bx = _xrecover(_By)
_B = (_Bx % _p, _By % _p, 1, (_Bx * _By) % _p)


def _edwards_add(P, Q):
    x1, y1, z1, t1 = P
    x2, y2, z2, t2 = Q
    a = ((y1 - x1) * (y2 - x2)) % _p
    b = ((y1 + x1) * (y2 + x2)) % _p
    c = (2 * t1 * t2 * _d) % _p
    dd = (2 * z1 * z2) % _p
    e = b - a
    f = dd - c
    g = dd + c
    h = b + a
    return ((e * f) % _p, (g * h) % _p, (f * g) % _p, (e * h) % _p)


def _scalarmult(P, e):
    if e == 0:
        return (0, 1, 1, 0)
    Q = _scalarmult(P, e // 2)
    Q = _edwards_add(Q, Q)
    if e & 1:
        Q = _edwards_add(Q, P)
    return Q


def _to_affine(P):
    x, y, z, _t = P
    zi = pow(z, _p - 2, _p)
    return (x * zi) % _p, (y * zi) % _p


def _decodeint(s: bytes) -> int:
    return int.from_bytes(s, "little")


def _decodepoint(s: bytes):
    y = int.from_bytes(s, "little") & ((1 << 255) - 1)
    x = _xrecover(y)
    if x & 1 != (s[31] >> 7) & 1:
        x = _p - x
    P = (x, y, 1, (x * y) % _p)
    return P


def _ed25519_verify_pure(public: bytes, msg: bytes, sig: bytes) -> bool:
    A = _decodepoint(public)
    R = _decodepoint(sig[:32])
    S = _decodeint(sig[32:])
    h = _decodeint(sha256_512(sig[:32] + public + msg))
    left = _to_affine(_scalarmult(_B, S))
    right = _to_affine(_edwards_add(R, _scalarmult(A, h)))
    return left == right


def sha256_512(b: bytes) -> bytes:
    from hashlib import sha512

    return sha512(b).digest()


# --------------------------------------------------------------------------- #
# I/O helper                                                                   #
# --------------------------------------------------------------------------- #
def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Parse a JSONL export into a list of dict rows. One JSON object per line;
    blank lines skipped. No coercion — a malformed line raises."""
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


# --------------------------------------------------------------------------- #
# Invariant builders                                                           #
# --------------------------------------------------------------------------- #
def _inv(
    id: str,
    title: str,
    predicate: str,
    doctrine_ref: str,
    status: Status,
    checked: int,
    violations: int,
    worst_row_id: Optional[Any],
    detail: str,
) -> Dict[str, Any]:
    return {
        "id": id,
        "title": title,
        "predicate": predicate,
        "doctrineRef": doctrine_ref,
        "basis": "MEASURED",
        "status": status,
        "checked": checked,
        "violations": violations,
        "worstRowId": worst_row_id,
        "detail": detail,
    }


def _receipt_chain_continuity(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Order newest-first by id, mirroring the app's `order by id desc`.
    ordered = sorted(
        rows, key=lambda r: (r.get("id") is None, r.get("id")), reverse=True
    )
    entries = []
    for r in ordered:
        verified: Optional[bool] = None
        rh, ph = r.get("rowHash"), r.get("prevHash")
        if rh is not None and ph is not None:
            verified = rh == recompute_row_hash(ph, r)
        entries.append({"prevHash": ph, "rowHash": rh, "verified": verified})
    links_ok = True
    for i in range(len(entries) - 1):
        cur, older = entries[i], entries[i + 1]
        if cur["prevHash"] is not None and older["rowHash"] is not None:
            if cur["prevHash"] != older["rowHash"]:
                links_ok = False
    checked = sum(1 for e in entries if e["verified"] is not None)
    failed = sum(1 for e in entries if e["verified"] is False)
    predate = sum(1 for e in entries if e["verified"] is None)
    if not entries:
        cs = "EMPTY"
    elif any(e["verified"] is False for e in entries) or not links_ok:
        cs = "BROKEN"
    elif any(e["verified"] is None for e in entries):
        cs = "PARTIAL"
    else:
        cs = "VERIFIED"
    status = "NO_DATA" if cs == "EMPTY" else "VIOLATED" if cs == "BROKEN" else "HOLDS"
    detail = {
        "VERIFIED": f"all {checked} hashed links recompute exactly",
        "PARTIAL": f"{checked} link(s) recompute; {predate} row(s) predate the hash chain (stated, not a failure)",
        "BROKEN": f"chain BROKEN — {failed} link(s) failed to recompute or a prev/row hash mismatched",
        "EMPTY": "no rows in the export",
    }[cs]
    return _inv(
        "receipt-chain-continuity",
        "Receipt chain recomputes over its own tail (Ouroboros closure)",
        "for every ledger row with a stored hash: rowHash === sha256(prevHash | contentHash), and each row's prevHash === the next-older row's rowHash",
        "notarized receipt chain — tamper-evident, recomputed per request",
        status,
        checked,
        failed,
        None,
        detail,
    )


def _ledger_failure_shape(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    subject = [r for r in rows if not r.get("ok")]
    bad = [
        r
        for r in subject
        if r.get("servedProvider") is not None or r.get("latencyMs") is not None
    ]
    status = "NO_DATA" if not subject else "VIOLATED" if bad else "HOLDS"
    detail = (
        f"{len(bad)} failed row(s) carry a served-provider or latency claim — ledger corruption or a write-path regression"
        if bad
        else f"{len(subject)} failed row(s), all shaped honestly (catches corruption/regression, not runtime correctness)"
    )
    return _inv(
        "ledger-failure-shape",
        "Failed runs claim no serving provider or latency",
        "for every row where ok = false: servedProvider IS NULL and latencyMs IS NULL",
        "honest failure — a failed run never fabricates a serve",
        status,
        len(subject),
        len(bad),
        (bad[0].get("id") if bad else None),
        detail,
    )


def _served_run_has_model(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    subject = [r for r in rows if r.get("ok") and not r.get("demo")]
    bad = [r for r in subject if r.get("model") is None]
    status = "NO_DATA" if not subject else "VIOLATED" if bad else "HOLDS"
    detail = (
        f"{len(bad)} live-served row(s) name no model — provenance gap"
        if bad
        else f"{len(subject)} live-served row(s), all name a model"
    )
    return _inv(
        "served-run-has-model",
        "Live-served runs name the model that served them",
        "for every row where ok = true and demo = false: model IS NOT NULL",
        "provenance — a real serve always records its model",
        status,
        len(subject),
        len(bad),
        (bad[0].get("id") if bad else None),
        detail,
    )


def _signed_columns_atomic(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    bad = []
    for r in rows:
        flags = [
            r.get("receiptId") is not None,
            r.get("signature") is not None,
            r.get("keyId") is not None,
            r.get("receiptJson") is not None,
        ]
        if not (all(flags) or not any(flags)):
            bad.append(r)
    status = "NO_DATA" if not rows else "VIOLATED" if bad else "HOLDS"
    detail = (
        f"{len(bad)} row(s) have a partial receipt column set — write-path regression or tamper"
        if bad
        else f"{len(rows)} row(s), each fully signed or honestly unsigned"
    )
    return _inv(
        "signed-columns-atomic",
        "Receipt columns are all-present or all-absent",
        "for every row: (receiptId, signature, keyId, receiptJson) are ALL present or ALL absent",
        "no partial receipts — a row is signed or honestly unsigned, never half",
        status,
        len(rows),
        len(bad),
        (bad[0].get("id") if bad else None),
        detail,
    )


def _loop_steps_positive(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    subject = [r for r in rows if r.get("ok") and not r.get("demo")]
    bad = [
        r
        for r in subject
        if r.get("loopSteps") is None or (r.get("loopSteps") or 0) < 1
    ]
    status = "NO_DATA" if not subject else "VIOLATED" if bad else "HOLDS"
    detail = (
        f"{len(bad)} served row(s) recorded no loop step"
        if bad
        else f"{len(subject)} served row(s), each took at least one step"
    )
    return _inv(
        "loop-steps-positive",
        "Every live-served run took at least one loop step",
        "for every row where ok = true and demo = false: loopSteps >= 1 (lower bound only — the per-run upper bound targets.length is not persisted, so it is not asserted)",
        "LOOP_DOCTRINE — bounded, terminating, receipt-closed",
        status,
        len(subject),
        len(bad),
        (bad[0].get("id") if bad else None),
        detail,
    )


def _receipt_ed25519_verify(
    rows: List[Dict[str, Any]],
    signed_rows: List[Dict[str, Any]],
    tally: Dict[str, Any],
) -> Dict[str, Any]:
    if tally["keyId"] is None:
        return _inv(
            "receipt-ed25519-verify",
            "Each signed receipt verifies under ed25519",
            "for every signed row: ed25519_verify(receiptJson, signature) === true under the supplied key",
            "notarized receipts — signature checks the exact canonical bytes",
            "UNAVAILABLE",
            0,
            0,
            None,
            "no public key supplied — signatures cannot be verified offline (honest UNAVAILABLE, not a judgment on the receipts)",
        )
    if not signed_rows:
        status = "NO_DATA"
        detail = "no signed rows in the export"
    elif tally["hardFail"]:
        status = "VIOLATED"
        detail = f"{tally['hardFail']} signed receipt(s) fail ed25519 verification — tamper or drift"
    elif tally["rotated"]:
        status = "KEY_ROTATED"
        detail = f"all {len(signed_rows)} signed; {tally['rotated']} were signed under a rotated key (honest KEY_ROTATED, not a tamper verdict)"
    else:
        status = "HOLDS"
        detail = f"all {len(signed_rows)} signed receipts verify under the supplied key"
    return _inv(
        "receipt-ed25519-verify",
        "Each signed receipt verifies under ed25519",
        "for every signed row: ed25519_verify(receiptJson, signature) === true under the supplied key",
        "notarized receipts — signature checks the exact canonical bytes",
        status,
        len(signed_rows),
        tally["hardFail"],
        tally["worst"],
        detail,
    )


def _receipt_columns_consistent(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    with_receipt = [r for r in rows if r.get("receiptJson") is not None]
    bad = 0
    worst = None
    for r in with_receipt:
        try:
            p = json.loads(r["receiptJson"])
        except Exception:
            bad += 1
            worst = worst if worst is not None else r.get("id")
            continue
        mismatch = (
            p.get("receiptId") != r.get("receiptId")
            or p.get("goalSha256") != r.get("goalSha256")
            or (p.get("outputSha256") if p.get("outputSha256") is not None else None)
            != r.get("outputSha256")
            or p.get("keyId") != r.get("keyId")
        )
        if mismatch:
            bad += 1
            worst = worst if worst is not None else r.get("id")
    status = "NO_DATA" if not with_receipt else "VIOLATED" if bad else "HOLDS"
    detail = (
        f"{bad} receipt(s) disagree with their indexed columns — canonical/column drift or tamper"
        if bad
        else f"{len(with_receipt)} receipt(s), each agreeing exactly with its columns"
    )
    return _inv(
        "receipt-columns-consistent",
        "Receipt payload matches its indexed columns",
        "for every row with a stored receipt: parse(receiptJson).{receiptId, goalSha256, outputSha256, keyId} === the row's indexed columns",
        "canonical/column consistency — the signed payload and the columns cannot disagree",
        status,
        len(with_receipt),
        bad,
        worst,
        detail,
    )


def _flywheel_lineage(
    rows: List[Dict[str, Any]],
    samples: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    title = "Flywheel eats only its own verified tail (own-metal, never demo/cloud)"
    predicate = "every training sample with a receiptId joins to a runs row with demo = false and servedNode IS NOT NULL"
    doctrine = "sovereign flywheel lineage — samples come only from real own-metal serves"
    if samples is None:
        return _inv(
            "flywheel-lineage",
            title,
            predicate,
            doctrine,
            "UNAVAILABLE",
            0,
            0,
            None,
            "no flywheel training-sample export supplied — lineage cannot be replayed (honest UNAVAILABLE)",
        )
    # Offline replay of the SQL left-join by receiptId.
    by_receipt = {
        r.get("receiptId"): r for r in rows if r.get("receiptId") is not None
    }
    lineage = []
    for s in samples:
        rid = s.get("receiptId")
        if "runFound" in s:  # pre-joined export
            lineage.append(s)
            continue
        row = by_receipt.get(rid) if rid is not None else None
        lineage.append(
            {
                "sampleId": s.get("sampleId", s.get("id")),
                "receiptId": rid,
                "runFound": row is not None,
                "runDemo": (row.get("demo") if row else None),
                "runServedNode": (row.get("servedNode") if row else None),
            }
        )
    linkable = [s for s in lineage if s.get("receiptId") is not None]
    unlinkable = len(lineage) - len(linkable)
    bad = [
        s
        for s in linkable
        if not s.get("runFound")
        or s.get("runDemo") is True
        or s.get("runServedNode") is None
    ]
    status = "NO_DATA" if not linkable else "VIOLATED" if bad else "HOLDS"
    if bad:
        detail = f"{len(bad)} sample(s) trace to a demo/cloud/missing run — the lineage claim is violated"
    else:
        detail = f"{len(linkable)} sample(s) all trace to a real own-metal serve" + (
            f"; {unlinkable} sample(s) have no receiptId to join (excluded, stated)"
            if unlinkable
            else ""
        )
    return _inv(
        "flywheel-lineage",
        title,
        predicate,
        doctrine,
        status,
        len(linkable),
        len(bad),
        (bad[0].get("sampleId") if bad else None),
        detail,
    )


def _ed25519_tally(
    signed_rows: List[Dict[str, Any]], pubkey: Optional[str]
) -> Dict[str, Any]:
    """Verify every signed row ONCE; reused by invariant #6 and the latent
    coverage metric (no second verification pass — mirrors the app)."""
    if pubkey is None:
        return {"keyId": None, "verified": 0, "hardFail": 0, "rotated": 0, "worst": None}
    cur_key = keyid_from_spki(pubkey)
    verified = hard_fail = rotated = 0
    worst = None
    for r in signed_rows:
        ok = verify_ed25519(r["receiptJson"], r["signature"], pubkey)
        if ok:
            verified += 1
            continue
        if r.get("keyId") and r.get("keyId") != cur_key:
            rotated += 1
        else:
            hard_fail += 1
            worst = worst if worst is not None else r.get("id")
    return {
        "keyId": cur_key,
        "verified": verified,
        "hardFail": hard_fail,
        "rotated": rotated,
        "worst": worst,
    }


def run_invariants(
    rows: Optional[Sequence[Dict[str, Any]]],
    samples: Optional[Sequence[Dict[str, Any]]] = None,
    pubkey: Optional[str] = None,
) -> Dict[str, Any]:
    """Replay all eight falsifiable invariants + the latent-verification
    coverage metric over an offline ledger export.

    - `rows=None` → the entire report is UNAVAILABLE (mirrors "ledger DB
      unreachable"): nothing is fabricated.
    - `samples=None` → the flywheel-lineage invariant is UNAVAILABLE.
    - `pubkey=None` → the ed25519 invariant + latent coverage are UNAVAILABLE.

    Returns a dict with `label`, `status`, `summary`, `latentVerification`,
    `invariants`, `doctrine`, `note`.
    """
    if rows is None:
        return {
            "label": "MEASURED",
            "status": "UNAVAILABLE",
            "reason": "no ledger export supplied",
            "window": {"runsEnumerated": 0, "samplesEnumerated": 0},
            "summary": {"total": 0, "holds": 0, "violated": 0, "indeterminate": 0},
            "latentVerification": {
                "status": "UNAVAILABLE",
                "reason": "no ledger export supplied",
                "enumerated": 0,
                "verified": 0,
                "verifiedRatio": None,
                "rotated": 0,
                "unsigned": 0,
                "tamperFailed": 0,
                "note": LATENT_VERIFICATION_NOTE,
            },
            "invariants": [],
            "doctrine": DOCTRINE,
            "note": NOTE,
        }
    rows = list(rows)
    samples_list = list(samples) if samples is not None else None
    signed_rows = [
        r
        for r in rows
        if r.get("receiptJson") is not None and r.get("signature") is not None
    ]
    tally = _ed25519_tally(signed_rows, pubkey)

    invariants = [
        _receipt_chain_continuity(rows),
        _ledger_failure_shape(rows),
        _served_run_has_model(rows),
        _signed_columns_atomic(rows),
        _loop_steps_positive(rows),
        _receipt_ed25519_verify(rows, signed_rows, tally),
        _receipt_columns_consistent(rows),
        _flywheel_lineage(rows, samples_list),
    ]

    holds = sum(1 for i in invariants if i["status"] == "HOLDS")
    violated = sum(1 for i in invariants if i["status"] == "VIOLATED")
    indeterminate = len(invariants) - holds - violated

    if pubkey is None:
        latent = {
            "status": "UNAVAILABLE",
            "reason": "no public key supplied — hash/signature-space verification cannot run",
            "enumerated": len(rows),
            "verified": 0,
            "verifiedRatio": None,
            "rotated": 0,
            "unsigned": len(rows) - len(signed_rows),
            "tamperFailed": 0,
            "note": LATENT_VERIFICATION_NOTE,
        }
    else:
        latent = {
            "status": "MEASURED",
            "enumerated": len(rows),
            "verified": tally["verified"],
            "verifiedRatio": (tally["verified"] / len(rows)) if rows else None,
            "rotated": tally["rotated"],
            "unsigned": len(rows) - len(signed_rows),
            "tamperFailed": tally["hardFail"],
            "note": LATENT_VERIFICATION_NOTE,
        }

    return {
        "label": "MEASURED",
        "status": "OK",
        "window": {
            "runsEnumerated": len(rows),
            "samplesEnumerated": len(samples_list) if samples_list is not None else 0,
        },
        "summary": {
            "total": len(invariants),
            "holds": holds,
            "violated": violated,
            "indeterminate": indeterminate,
        },
        "latentVerification": latent,
        "invariants": invariants,
        "doctrine": DOCTRINE,
        "note": NOTE,
    }


def list_checks() -> List[Dict[str, str]]:
    """The eight falsifiable invariant ids + one-line titles (registry)."""
    return [
        {"id": "receipt-chain-continuity", "title": "Receipt chain recomputes over its own tail"},
        {"id": "ledger-failure-shape", "title": "Failed runs claim no serving provider or latency"},
        {"id": "served-run-has-model", "title": "Live-served runs name the model that served them"},
        {"id": "signed-columns-atomic", "title": "Receipt columns are all-present or all-absent"},
        {"id": "loop-steps-positive", "title": "Every live-served run took at least one loop step"},
        {"id": "receipt-ed25519-verify", "title": "Each signed receipt verifies under ed25519"},
        {"id": "receipt-columns-consistent", "title": "Receipt payload matches its indexed columns"},
        {"id": "flywheel-lineage", "title": "Flywheel eats only its own verified tail"},
    ]


def selfcheck() -> Dict[str, Any]:
    """One-shot CPU health check on a tiny synthetic ledger: proves the kernel
    computes real HOLDS / VIOLATED / UNAVAILABLE verdicts (falsifiable). NOT a
    proof of anything about Λ, which is untouched (Conjecture 1)."""
    good = _build_demo_chain(tamper=False)
    bad = _build_demo_chain(tamper=True)
    r_good = run_invariants(good, samples=None, pubkey=None)
    r_bad = run_invariants(bad, samples=None, pubkey=None)
    chain_good = next(
        i for i in r_good["invariants"] if i["id"] == "receipt-chain-continuity"
    )
    chain_bad = next(
        i for i in r_bad["invariants"] if i["id"] == "receipt-chain-continuity"
    )
    return {
        "version": __version__,
        "checks_registered": len(INVARIANT_IDS),
        "clean_chain_status": chain_good["status"],  # HOLDS
        "tampered_chain_status": chain_bad["status"],  # VIOLATED (falsifiable!)
        "ed25519_without_key": next(
            i for i in r_good["invariants"] if i["id"] == "receipt-ed25519-verify"
        )["status"],  # UNAVAILABLE, never coerced
        "falsifiable_demonstrated": chain_good["status"] == "HOLDS"
        and chain_bad["status"] == "VIOLATED",
        "lambda_status": "Conjecture 1 (open) — untouched by these invariants",
    }


def _build_demo_chain(tamper: bool) -> List[Dict[str, Any]]:
    """Build a tiny genesis→2 chain the same way runLedger does, for selfcheck
    and tests. When tamper=True the newest row's contentHash is altered so the
    recompute genuinely fails."""
    rows: List[Dict[str, Any]] = []
    prev = "genesis"
    for i in range(1, 4):
        row = {
            "id": i,
            "endpoint": "/api/run",
            "mode": "planner",
            "requestedProvider": "auto",
            "servedProvider": "sovereign",
            "model": "own-metal",
            "servedNode": "tower",
            "demo": False,
            "ok": True,
            "latencyMs": 100 + i,
            "error": None,
            "loopSteps": 1,
            "receiptId": None,
            "receiptJson": None,
            "signature": None,
            "keyId": None,
            "goalSha256": None,
            "outputSha256": None,
            "prevHash": prev,
        }
        row["rowHash"] = recompute_row_hash(prev, row)
        prev = row["rowHash"]
        rows.append(row)
    if tamper:
        rows[-1]["model"] = "TAMPERED"  # contentHash now mismatches stored rowHash
    return rows
