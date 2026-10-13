# Changelog

## 0.1.1 (release candidate)

- Prepare a maintenance release carrying the canonical GitHub Source, issue,
  and changelog URLs and supported Python classifiers already on main. The
  immutable PyPI 0.1.0 distributions do not contain those project URLs.
- Keep the distribution, Python module, and both package-metadata variants at
  the same version; refresh their declared publication hashes. Invariant logic,
  signature requirements, six Hub destinations, and advisory claims are unchanged.
- Publication remains pending. After protected source admission, reconcile the
  exact source through Forge's governed model/kernel mirror and publish the
  tag-bound PyPI release through Trusted Publishing; retain both readbacks.

## 2026-10-13

- Add the canonical kernel publisher: `.github/workflows/hf-kernel-publish.yml`,
  `scripts/szl_kernel_publish.py` and `.github/hf-kernels.json`. It builds
  `build/torch-cpu` and `build/torch-universal` from `torch-ext/szl_invariants` at one
  reviewed commit, publishes them fast-forward to the kernel repo's `main` and `v1`,
  verifies `get_kernel(..., version=1)` and the `main` branch anonymously against the
  GitHub bytes, and then turns the model repo into a pointer card (no `build/`).
  The kernel card source is `hf/kernel-card.md`; it loads with `version=1`, never
  `revision="main"`. The Hub `OPERATIONAL.json` and `BENCH.laptop-blackwell.json`
  plates are pruned. A weekly job re-verifies what `get_kernel` serves.
- Remove the committed `build/torch-universal` copy and the Forge six-destination
  contract (`publishing/invariants-source-binding.json`, its test). The Hub build is
  now generated from `torch-ext/` only; the parity test checks the generated variants,
  and the installed-wheel smoke compares against `torch-ext/` directly.
- The kernel docstring quickstart uses `version=1`. No invariant logic changed.

## 2026-09-29

- Retire the one-shot Hub joblib quarantine writer (`hub-joblib-quarantine.yml`,
  `scripts/hub_quarantine_joblib.py`). The live Hub model and kernel repos hold no
  `model.joblib`, and the workflow was an unlocked Hub writer with an
  `HF_TOKEN || HF_ORG_TOKEN` fallback. The source-side refusal of joblib, pickle and
  dill loaders is unchanged. `tests/test_hub_single_writer.py` now fails if any file
  here gains a Hub write path outside a committed mirror.

## 2026-09-12

- Complete the six-destination publication contract with the CPU variant's
  existing, hash-bound package metadata. This matches Forge's closed target set;
  no kernel bytes, artifact hashes, trained-weight claims or publisher gates change.
- Test publication completeness against the installable package's Python files
  and declared package data, including missing, duplicated and misrouted targets.
- Preserve Python 3.9 support with a conditional development-only TOML backport,
  a Python-compatible build-backend pin, and minimum-version CI coverage.

## 2026-08-28

- Honesty README. Package source already on main. No kernel math changed.
- Quarantine joblib/pickle: forge no longer dumps `model.joblib`; eval refuses the file; Hub deletion is a dispatched PR with exact parent commit.
