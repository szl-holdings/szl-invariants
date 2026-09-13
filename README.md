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

## Load only a verified publication

A merged GitHub fix is not proof of a Hugging Face release. The canonical
[Forge publication workflow](https://github.com/szl-holdings/szl-forge/blob/main/.github/workflows/publish-szl-invariants.yml)
must authorize the exact protected source and publisher revisions, serialize
publication, and verify the immutable provider bytes. Retain its authorization
and publication reports before choosing a runtime revision.

Set `SZL_INVARIANTS_HF_REVISION` to the **immutable Hugging Face commit from the
verified publication**, not a branch name, version label, or the GitHub source
commit. Use the client version qualified with that release. Do not substitute
`main` when a receipt or revision is unavailable; stop instead.

```python
import os
import re

hf_revision = os.environ.get("SZL_INVARIANTS_HF_REVISION", "")
if re.fullmatch(r"[0-9a-f]{40}", hf_revision) is None:
    raise ValueError("A verified immutable Hugging Face revision is required")

from kernels import get_kernel

kernel = get_kernel(
    "SZLHOLDINGS/szl-invariants",
    revision=hf_revision,
    trust_remote_code=True,
)
```

The format check above does **not** verify provenance, hashes, authorization, or
runtime compatibility. Those come from the release evidence. Enabling
`trust_remote_code` permits execution of the selected repository's Python; use
it only after reviewing that exact revision and its evidence. This example
neither unquarantines `model.joblib` nor establishes acceleration or model quality.

For source-only development, use a separately reviewed, immutable GitHub source
revision and run its tests in an isolated environment. Keep that evidence distinct
from Hub publication and installed-runtime verification.

Doctrine v11. Λ = Conjecture 1 (advisory, never a theorem). Apache-2.0. Owner: Stephen Lutar / SZL Holdings.
