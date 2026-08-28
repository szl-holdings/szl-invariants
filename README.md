# szl-invariants

Software kernel for SZL runtime invariants. **Not a model. No weights.**

Python lives under `torch-ext/szl_invariants/` (`__init__.py` is the package). Hub mirror: [`kernels/SZLHOLDINGS/szl-invariants`](https://huggingface.co/kernels/SZLHOLDINGS/szl-invariants). Card: [`SZLHOLDINGS/szl-invariants`](https://huggingface.co/SZLHOLDINGS/szl-invariants).

## What this is NOT

- Not trained weights, not a LoRA
- No MEASURED CUDA benches in this repo
- Passing `selfcheck` (if present) is not an eval leaderboard

## Load

```python
from kernels import get_kernel
get_kernel("SZLHOLDINGS/szl-invariants", revision="main", trust_remote_code=True)
```

Doctrine v11. Λ = Conjecture 1 (advisory, never a theorem). Apache-2.0. Owner: Stephen Lutar / SZL Holdings.
