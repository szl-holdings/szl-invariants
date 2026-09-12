# Changelog

## 2026-09-12

- Complete the six-destination publication contract with the CPU variant's
  existing, hash-bound package metadata. This matches Forge's closed target set;
  no kernel bytes, artifact hashes, trained-weight claims or publisher gates change.
- Test publication completeness against the installable package's Python files
  and declared package data, including missing, duplicated and misrouted targets.

## 2026-08-28

- Honesty README. Package source already on main. No kernel math changed.
- Quarantine joblib/pickle: forge no longer dumps `model.joblib`; eval refuses the file; Hub deletion is a dispatched PR with exact parent commit.
