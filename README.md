# szl-invariants
<!-- szl:header v1 -->
<!-- badges: add this repo's CI / release / status badges here -->
[![org: szl-holdings](https://img.shields.io/badge/org-szl--holdings-black)](https://github.com/szl-holdings)
[![doctrine](https://img.shields.io/badge/doctrine-control%20before%20action%20%C2%B7%20evidence%20after-blue)](https://a-11-oy.com)

**Control before action. Evidence after.**

Part of the [szl-holdings](https://github.com/szl-holdings) estate ·
Product: [a-11-oy.com](https://a-11-oy.com) ·
Proof: [a11oy.net](https://a11oy.net)
<!-- /szl:header -->

Software kernel for SZL runtime invariants. **Not a model. No weights.**

Python lives under `torch-ext/szl_invariants/` (`__init__.py` is the package). Hub mirror: [`kernels/SZLHOLDINGS/szl-invariants`](https://huggingface.co/kernels/SZLHOLDINGS/szl-invariants). Card: [`SZLHOLDINGS/szl-invariants`](https://huggingface.co/SZLHOLDINGS/szl-invariants).

## What this is NOT

- Not trained weights, not a LoRA
- No MEASURED CUDA benches in this repo
- Passing `selfcheck` (if present) is not an eval leaderboard
- Hub `model.joblib` is **QUARANTINED** executable serialization. Do not `joblib.load` it. GitHub source is the approved path.

## Load

```python
from kernels import get_kernel
get_kernel("SZLHOLDINGS/szl-invariants", revision="main", trust_remote_code=True)
```

Doctrine v11. Λ = Conjecture 1 (advisory, never a theorem). Apache-2.0. Owner: Stephen Lutar / SZL Holdings.
