# szl-invariants
[![PyPI](https://img.shields.io/pypi/v/szl-invariants)](https://pypi.org/project/szl-invariants/) [![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/szl-holdings/szl-invariants/badge)](https://scorecard.dev/viewer/?uri=github.com/szl-holdings/szl-invariants)

<!-- szl:header v1 -->
<!-- Native identity: szl-brand@4309f6fce89179331b0b3ed8c99494e76c5be256; Orbit v2 icon. -->
<p>
  <a href="https://github.com/szl-holdings">
    <img src="https://raw.githubusercontent.com/szl-holdings/szl-brand/4309f6fce89179331b0b3ed8c99494e76c5be256/kit/logos/orbit-v2/suite/szl-icon-32.svg" alt="SZL Holdings — Orbit v2" width="32" height="32" />
  </a>
</p>

**Control before action. Evidence after.**

[Product](https://a-11-oy.com) · [Proof](https://a11oy.net) · [GitHub organization](https://github.com/szl-holdings)
<!-- /szl:header -->

Software kernel for SZL runtime invariants. **Not a model. No weights.**

Python lives under `torch-ext/szl_invariants/` (`__init__.py` is the package). Hub kernel: [`kernels/SZLHOLDINGS/szl-invariants`](https://huggingface.co/kernels/SZLHOLDINGS/szl-invariants), published from this repository by [`hf-kernel-publish`](.github/workflows/hf-kernel-publish.yml) (card source: [`hf/kernel-card.md`](hf/kernel-card.md)). The model repo [`SZLHOLDINGS/szl-invariants`](https://huggingface.co/SZLHOLDINGS/szl-invariants) only points to the kernel repo; it holds no loadable build.

## What this is NOT

- Not trained weights, not a LoRA
- No MEASURED CUDA benches in this repo
- Passing `selfcheck` (if present) is not an eval leaderboard
- Hub `model.joblib` is **QUARANTINED** executable serialization. Do not `joblib.load` it. GitHub source is the approved path.

## Load only a verified publication

A merged GitHub fix is not proof of a Hugging Face release. This repository's
[`hf-kernel-publish`](.github/workflows/hf-kernel-publish.yml) workflow is the only
writer of the kernel repo. It builds `build/torch-cpu` and `build/torch-universal`
from `torch-ext/` at one reviewed commit, pushes them fast-forward to the kernel
repo's `main` and `v1` branches, and then loads them anonymously through
`get_kernel` in a fresh job to check the served bytes against GitHub. Its publish
and verify receipts (workflow artifacts) name the kernel-repo commits.

The stable channel is `get_kernel("SZLHOLDINGS/szl-invariants", version=1, trust_remote_code=True)`.
For production, pin an exact build: set `SZL_INVARIANTS_HF_REVISION` to the
**immutable kernel-repo commit of `v1` from a passing verify receipt**, not a
branch name, version label, or the GitHub source commit. Use `kernels>=0.17.2`.
Do not substitute `main` when a receipt or revision is unavailable; stop instead.

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
