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
