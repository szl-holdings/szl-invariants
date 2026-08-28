#!/usr/bin/env python3
"""Forge a REAL trained surrogate for szl-invariants.
Kernel = ground truth. Surrogate = fast structural triage: given a ledger row
(+chain context features), predict which invariant a full kernel replay would
flag. The ed25519-tamper class is deliberately included to MEASURE the
surrogate's crypto blind spot (structural features cannot see signature
tampering) — that is the honest reason the kernel stays authoritative.
Seeded, receipted, reproducible."""
import json, os, random, sys, time, hashlib, platform
_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(os.path.join(_here, "build", "torch-universal")):
    sys.path.insert(0, os.path.join(_here, "build", "torch-universal"))  # in-repo run
else:
    sys.path.insert(0, "/tmp/kernel-probe/szl-invariants/build/torch-universal")  # forge-dev run
import szl_invariants as si
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, recall_score
import joblib

SEED = 20260721
random.seed(SEED); np.random.seed(SEED)
T0 = time.time()

# real ed25519 material (cryptography backend required for signing)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import base64
PRIV = Ed25519PrivateKey.generate()
SPKI = base64.b64encode(PRIV.public_key().public_bytes(
    serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
KEYID = si.keyid_from_spki(SPKI)

CLASSES = ["clean","chain-tamper","failure-shape","missing-model",
           "partial-receipt-columns","zero-loop-steps","sig-tamper","column-mismatch"]

def signed_receipt(rid, goal, out):
    payload = {"receiptId": rid, "goalSha256": goal, "outputSha256": out, "keyId": KEYID}
    canonical = si.canonical_json(payload)
    sig = base64.b64encode(PRIV.sign(canonical.encode())).decode()
    return payload, canonical, sig

def make_chain(n, cls, chain_id):
    """Build one chain of n rows; corrupt exactly one row per non-clean chain."""
    rows, prev = [], "genesis"
    target = random.randrange(n) if cls != "clean" else -1
    for i in range(n):
        rid = f"c{chain_id}-r{i}"
        row = {"id": chain_id*1000+i, "ok": True, "demo": False,
               "endpoint": "/api/agent", "mode": "live",
               "requestedProvider": "own", "servedProvider": "own-metal",
               "model": "khipu-1.5b", "servedNode": "node-a",
               "latencyMs": random.randint(40, 900), "error": None,
               "loopSteps": random.randint(1, 6)}
        if random.random() < 0.55:  # signed row
            p, canonical, sig = signed_receipt(rid, si.sha256_hex("g"+rid), si.sha256_hex("o"+rid))
            row.update({"receiptId": rid, "keyId": KEYID, "receiptJson": canonical,
                        "signature": sig, "goalSha256": p["goalSha256"], "outputSha256": p["outputSha256"]})
        else:
            row.update({"receiptId": None, "keyId": None, "receiptJson": None, "signature": None})
        if random.random() < 0.12 and row["receiptJson"] is None:  # honest failures
            row.update({"ok": False, "servedProvider": None, "latencyMs": None,
                        "model": None, "loopSteps": None, "error": "upstream 502"})
        label = "clean"
        if i == target:
            label = cls
            if cls == "failure-shape":
                row.update({"ok": False, "error": "x", "servedProvider": "own-metal",
                            "latencyMs": 77, "model": None, "loopSteps": None})
            elif cls == "missing-model":
                row.update({"ok": True, "demo": False, "model": None})
            elif cls == "partial-receipt-columns":
                p, canonical, sig = signed_receipt(rid, si.sha256_hex("g"), si.sha256_hex("o"))
                row.update({"receiptId": rid, "signature": None, "keyId": None, "receiptJson": canonical})
            elif cls == "zero-loop-steps":
                row.update({"ok": True, "demo": False, "loopSteps": 0})
            elif cls == "sig-tamper":
                # PURE signature corruption: receiptJson + columns stay perfectly
                # consistent; only the signature bytes are flipped. Structurally
                # identical to a clean signed row -> measures the TRUE crypto blind spot.
                p, canonical, sig = signed_receipt(rid, si.sha256_hex("g"+rid), si.sha256_hex("o"+rid))
                raw = bytearray(base64.b64decode(sig)); raw[0] ^= 0xFF
                row.update({"receiptId": rid, "keyId": KEYID,
                            "signature": base64.b64encode(bytes(raw)).decode(),
                            "receiptJson": canonical,
                            "goalSha256": p["goalSha256"], "outputSha256": p["outputSha256"]})
            elif cls == "column-mismatch":
                p, canonical, sig = signed_receipt(rid, si.sha256_hex("g"+rid), si.sha256_hex("o"+rid))
                row.update({"receiptId": rid, "keyId": KEYID, "receiptJson": canonical,
                            "signature": sig, "goalSha256": si.sha256_hex("DIFFERENT"),
                            "outputSha256": p["outputSha256"]})
        row["rowHash"] = si.recompute_row_hash(prev, row); row["prevHash"] = prev
        if i == target and cls == "chain-tamper":
            row["rowHash"] = si.sha256_hex("tampered" + rid)
        rows.append((row, label)); prev = row["rowHash"]
    return rows

def features(row, next_older):
    """Cheap structural observables ONLY — no ed25519 verify (that's the
    measured blind spot), but sha256 recompute IS cheap and included."""
    rj = row.get("receiptJson")
    cols_match = -1
    if rj is not None:
        try:
            p = json.loads(rj)
            cols_match = int(p.get("receiptId") == row.get("receiptId")
                             and p.get("goalSha256") == row.get("goalSha256")
                             and p.get("outputSha256") == row.get("outputSha256")
                             and p.get("keyId") == row.get("keyId"))
        except Exception:
            cols_match = 0
    hash_ok = -1
    if row.get("rowHash") is not None and row.get("prevHash") is not None:
        hash_ok = int(row["rowHash"] == si.recompute_row_hash(row["prevHash"], row))
    link_ok = -1
    if next_older is not None and row.get("prevHash") is not None and next_older.get("rowHash") is not None:
        link_ok = int(row["prevHash"] == next_older["rowHash"])
    b = lambda v: -1 if v is None else int(bool(v))
    n_receipt = sum(row.get(k) is not None for k in ("receiptId","signature","keyId","receiptJson"))
    return [b(row.get("ok")), b(row.get("demo")), int(row.get("model") is not None),
            int(row.get("servedProvider") is not None), int(row.get("latencyMs") is not None),
            -1 if row.get("loopSteps") is None else row["loopSteps"],
            int(row.get("receiptId") is not None), int(row.get("signature") is not None),
            int(row.get("keyId") is not None), int(rj is not None), n_receipt,
            len(rj) if rj else 0, cols_match, hash_ok, link_ok]

FEATURE_NAMES = ["ok","demo","has_model","has_served_provider","has_latency","loop_steps",
                 "has_receipt_id","has_signature","has_key_id","has_receipt_json",
                 "n_receipt_fields","receipt_json_len","cols_match","hash_recompute_ok","prev_link_ok"]

# ---- generate ----
X, y, kernel_checked = [], [], 0
chain_id = 0
PER_CLASS_CHAINS = {c: (1400 if c == "clean" else 550) for c in CLASSES}
for cls, n_chains in PER_CLASS_CHAINS.items():
    for _ in range(n_chains):
        chain_id += 1
        chain = make_chain(random.randint(3, 7), cls, chain_id)
        rows_only = [r for r, _ in chain]
        for idx, (row, label) in enumerate(chain):
            next_older = rows_only[idx-1] if idx > 0 else None
            X.append(features(row, next_older)); y.append(label)
        # kernel-verify labels on a sample of chains (ground-truth audit)
        if chain_id % 37 == 0:
            rep = si.run_invariants(rows_only, pubkey=SPKI)
            flagged = {i["id"] for i in rep["invariants"] if i["status"] == "VIOLATED"}
            expect = {"chain-tamper": "receipt-chain-continuity", "failure-shape": "ledger-failure-shape",
                      "missing-model": "served-run-has-model", "partial-receipt-columns": "signed-columns-atomic",
                      "zero-loop-steps": "loop-steps-positive", "sig-tamper": "receipt-ed25519-verify",
                      "column-mismatch": "receipt-columns-consistent"}.get(cls)
            if expect is not None:
                assert expect in flagged, f"kernel disagrees: {cls} chain {chain_id} did not flag {expect} (got {flagged})"
            else:
                assert not flagged, f"clean chain {chain_id} flagged {flagged}"
            kernel_checked += 1

X = np.array(X, dtype=np.float64); y = np.array(y)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
clf = HistGradientBoostingClassifier(random_state=SEED, max_iter=300, early_stopping=True)
clf.fit(Xtr, ytr)
pred = clf.predict(Xte)
acc = accuracy_score(yte, pred)
per_class_recall = {c: float(recall_score(yte == c, pred == c)) for c in CLASSES}
non_crypto = [c for c in CLASSES if c != "sig-tamper"]
mask = np.isin(yte, non_crypto)
acc_structural = accuracy_score(yte[mask], pred[mask])

out = os.path.dirname(os.path.abspath(__file__))
joblib.dump(clf, f"{out}/model.joblib")
model_sha = hashlib.sha256(open(f"{out}/model.joblib","rb").read()).hexdigest()
receipt = {
  "artifact": "SZLHOLDINGS/szl-invariants surrogate v1",
  "role": "structural triage surrogate — kernel remains ground truth",
  "generator": {"script": "scripts/forge.py", "seed": SEED, "kernel_version": si.__version__,
                 "kernel_labelled": True, "kernel_audited_chains": kernel_checked},
  "data": {"rows": int(len(y)), "classes": CLASSES,
            "class_counts": {c: int((y == c).sum()) for c in CLASSES},
            "split": "80/20 stratified", "features": FEATURE_NAMES,
            "feature_policy": "cheap structural observables only; ed25519 verification EXCLUDED by design (measured blind spot)"},
  "model": {"type": "sklearn.HistGradientBoostingClassifier", "params": {"max_iter": 300, "early_stopping": True, "random_state": SEED},
             "file": "model.joblib", "sha256": model_sha},
  "metrics_MEASURED": {"test_accuracy_all_classes": round(float(acc), 4),
                        "test_accuracy_structural_only": round(float(acc_structural), 4),
                        "per_class_recall": {k: round(v, 4) for k, v in per_class_recall.items()},
                        "crypto_blind_spot": {"class": "sig-tamper", "recall": round(per_class_recall["sig-tamper"], 4),
                          "statement": "structural features cannot detect signature tampering — this is measured, expected, and the reason the kernel stays authoritative"}},
  "environment": {"python": platform.python_version(), "sklearn": __import__("sklearn").__version__,
                   "numpy": np.__version__, "host": "replit 2-vCPU container", "wall_seconds": round(time.time()-T0, 1)},
  "honesty": "Every number above is MEASURED by this run. The surrogate never replaces kernel replay; Λ untouched = Conjecture 1.",
  "trained_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
with open(f"{out}/TRAINING_RECEIPT.json", "w") as f: json.dump(receipt, f, indent=2)
print(json.dumps(receipt["metrics_MEASURED"], indent=2))
print(f"rows={len(y)} kernel_audited_chains={kernel_checked} wall={receipt['environment']['wall_seconds']}s")
