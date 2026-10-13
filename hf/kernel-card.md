---
license: apache-2.0
library_name: kernels
tags:
  - kernel
  - szl-holdings
  - governance
  - invariants
  - provenance
  - receipts
  - ed25519
szl-governance:
  verdict: ADVISORY
  lambda: "Conjecture 1 (open): uniqueness unproven; untouched by these invariants; advisory only"
  honest_blocked: "a VIOLATED invariant stays VIOLATED: statuses are never coerced to a pass"
---

# {{KERNEL_NAME}}

The eight falsifiable runtime invariants of the a11oy backbone, as an offline governance kernel
that `get_kernel` can load. Pure-Python (noarch), published from GitHub
[{{GITHUB_REPOSITORY}}](https://github.com/{{GITHUB_REPOSITORY}}) by its `hf-kernel-publish`
workflow. GitHub is the source of truth; this repository is written only by that workflow.

> **Scope.** This is not a trained model and ships no weights. It recomputes, offline, the
> receipt/ledger self-consistency invariants the a11oy backbone checks live at `/api/invariants`,
> over a JSONL export you already hold. It does no network I/O and does not use tensors.
> Historical `model.joblib` surrogate artifacts are QUARANTINED and are not a load path.
> Λ is not touched here and stays Conjecture 1 (open).

## Load it

```python
# pip install "kernels>=0.17.2" torch
from kernels import get_kernel

inv = get_kernel("{{REPO_ID}}", version={{KERNEL_VERSION}}, trust_remote_code=True)

rows = inv.load_jsonl("runs_export.jsonl")          # your ledger export
samples = inv.load_jsonl("training_samples.jsonl")  # optional flywheel export
pubkey = "<SPKI base64 from /api/receipts/pubkey>"  # optional, enables Ed25519

report = inv.run_invariants(rows, samples=samples, pubkey=pubkey)
print(report["summary"])
for check in report["invariants"]:
    print(check["id"], check["status"], check["detail"])

print(inv.selfcheck())  # clean chain HOLDS, tampered chain VIOLATED, no key UNAVAILABLE
```

- `version={{KERNEL_VERSION}}` resolves the `v{{KERNEL_VERSION}}` branch, the stable API channel. It is
  republished from GitHub on every publication. The `kernels` library refuses a call that names
  neither a version nor a revision.
- `trust_remote_code` is required: SZLHOLDINGS is not a trusted kernel publisher on the Hub.
  The narrowest form is `trust_remote_code=["{{REPO_ID}}"]`.
- CPU hosts load `build/torch-cpu`; CUDA and other hosts load `build/torch-universal`.
  Both variants carry identical code, built from the same GitHub commit.

### Pin an exact build (production)

```python
from huggingface_hub import HfApi
from kernels import get_kernel

refs = HfApi().list_repo_refs("{{REPO_ID}}", repo_type="kernel")
pin = next(b.target_commit for b in refs.branches if b.name == "v{{KERNEL_VERSION}}")
inv = get_kernel("{{REPO_ID}}", revision=pin, trust_remote_code=["{{REPO_ID}}"])
```

Record `pin` (a commit of this kernel repository) in your lockfile.
`SZL_KERNEL_SOURCE.json` in this repository names the GitHub commit each build came from.
Commits of the model repository [{{MODEL_TWIN_URL}}]({{MODEL_TWIN_URL}}) are not kernel
revisions and do not resolve here.

## The eight invariants

Every check can genuinely fail. A check that cannot fail would be verification theater and is
excluded. Statuses `HOLDS`, `VIOLATED`, `KEY_ROTATED`, `NO_DATA` and `UNAVAILABLE` are all
first-class and never coerced. Counts are enumerated rows only, never a claimed total.

| # | id | Holds when |
|---|---|---|
| 1 | `receipt-chain-continuity` | `rowHash == sha256(prevHash \| contentHash)` and each `prevHash` links the next-older `rowHash` |
| 2 | `ledger-failure-shape` | `ok=false` rows carry no `servedProvider` / `latencyMs` |
| 3 | `served-run-has-model` | `ok ∧ ¬demo ⇒ model IS NOT NULL` |
| 4 | `signed-columns-atomic` | `(receiptId, signature, keyId, receiptJson)` are all present or all absent |
| 5 | `loop-steps-positive` | `ok ∧ ¬demo ⇒ loopSteps ≥ 1` (lower bound only) |
| 6 | `receipt-ed25519-verify` | signed rows verify under the supplied key; `KEY_ROTATED` is reported as such |
| 7 | `receipt-columns-consistent` | `parse(receiptJson)` agrees with the indexed columns |
| 8 | `flywheel-lineage` | every sample with a `receiptId` joins a run with `demo=false ∧ servedNode≠null` |

`pubkey=None` leaves invariant 6 `UNAVAILABLE` (not a pass, not a fail); `samples=None` leaves
invariant 8 `UNAVAILABLE`.

## Requirements

- Python 3.9 or later. The unsigned checks use the standard library only.
- Ed25519 verification needs the optional `cryptography` backend (`cryptography>=46,<51`).
  Without it, signature checks report `UNAVAILABLE`; they fail closed and are never coerced.
- Loading through `kernels` needs `kernels>=0.17.2` and torch. The kernel itself does not import torch.

## Verification

Before any publication the workflow builds both variants from Git objects at one GitHub commit,
loads them with `kernels==0.17.2` on CPU torch, and runs `selfcheck()`. After publishing it loads
this repository anonymously with `get_kernel(..., version={{KERNEL_VERSION}})`, and through
the `main` branch, in a fresh environment and checks that the served files are byte-identical to
the GitHub source. The receipts are kept as workflow artifacts in
[{{GITHUB_REPOSITORY}}](https://github.com/{{GITHUB_REPOSITORY}}/actions/workflows/hf-kernel-publish.yml).
The same package is on PyPI as `szl-invariants`.

## Provenance

Mirrors the a11oy backbone `/api/invariants` recompute (`artifacts/api-server/src/routes/invariants.ts`)
and the chain hashing in `runLedger.ts` and `receipts.ts`. Backed by the Lean 4 formalization
[szl-holdings/lutar-lean](https://github.com/szl-holdings/lutar-lean), DOI
[10.5281/zenodo.20434308](https://doi.org/10.5281/zenodo.20434308).

## License

Apache-2.0 (see `LICENSE` and `NOTICE`). Copyright 2026 SZL Holdings.
