# szl-invariants

Canonical GitHub source for **SZLHOLDINGS/szl-invariants**.

**GitHub is the source of truth.** The Hugging Face Hub kernel package is a **publish mirror** of this tree. Do not treat the Hub copy as canonical.

ATELIER owns Hub cards. This README is a source face for the Git repository. It is **not** a second model card.

## What this is

A **software kernel**: executable, falsifiable runtime self-consistency checks over a ledger/receipts export you hold. Pure Python, stdlib-only. **Not** trained weights. **Not** CUDA benches.

- Eight invariants: receipt-chain continuity, ledger failure shape, served-run-has-model, signed-columns-atomic, loop-steps-positive, ed25519 verify, receipt-columns-consistent, flywheel lineage.
- Statuses are first-class (`HOLDS` / `VIOLATED` / `KEY_ROTATED` / `NO_DATA` / `UNAVAILABLE`) and are never coerced to a pass.
- **Λ = Conjecture 1**, never a theorem. These checks do not prove or upgrade Λ.
- Doctrine v11.
- License: Apache-2.0.

## Load (via the Hub publish mirror)

```python
from kernels import get_kernel
inv = get_kernel("SZLHOLDINGS/szl-invariants", revision="main", trust_remote_code=True)
```

Hub package: https://huggingface.co/SZLHOLDINGS/szl-invariants

## Layout

- `build.toml` — kernel-builder manifest (`universal = true`)
- `build/torch-universal/szl_invariants/` — kernel module
- `tests/test_invariants.py` — honest falsifiability tests
- `LICENSE` — Apache-2.0
