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
