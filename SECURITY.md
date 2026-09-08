# Security

Report vulnerabilities to stephen@szlholdings.com.

## Signature verification

Ed25519 verification requires the optional audited `cryptography` package
(`python -m pip install 'cryptography>=46,<50'`, or this project's `crypto`
extra). The unsigned ledger checks remain usable with only the standard
library. No custom cryptographic verifier is used.

When the capability is absent or cannot import, `verify_ed25519` returns
`False`; the report's signature invariant and verification coverage are
`UNAVAILABLE`, with no checked signatures and no claimed verification ratio.
This is not a tamper verdict and never becomes `HOLDS`.

The previous pure-Python fallback was removed after an RFC 8032 public
test-vector check demonstrated acceptance of a noncanonical signature
scalar. Regression tests cover the audited backend's valid vector,
tamper/noncanonical rejection, strict base64 and SPKI parsing, and missing
capability behavior. These tests are not a full cryptographic audit.
See [RFC 8032 verification requirements](https://www.rfc-editor.org/rfc/rfc8032#section-5.1.7).

Receipt payloads must parse to JSON objects. Loop-step counts must be finite
numbers, not booleans, satisfying the existing lower bound of one; no upper
bound or integer-only rule is newly inferred from fields that are not stored.

## Serialization

`model.joblib` / pickle / dill are not approved load paths. The kernel source under `torch-ext/` is. If a Hub revision still lists `model.joblib`, treat it as QUARANTINED residue pending a Hub PR with exact `parent_commit`.
