# CPU correctness and microbenchmark evidence

This is an owner-run local CPU measurement of the eight-invariant report on
unsigned, synthetic receipt-ledger rows. It is not model training, a GPU
benchmark, clinical evidence, a cross-language conformance proof, or a claim
that all invariant/security paths are qualified.

The accompanying patch rejects parsed receipt payloads that are not JSON
objects, counting each as `VIOLATED` instead of crashing the entire report.
Six new regression cases failed with `AttributeError` before this patch and
passed after it. Both canonical source copies and the declared publication
hashes are updated together. No existing assertion is weakened or skipped.

## Reproduce

From this repository using Python 3.12 and pytest:

```powershell
python -I -B -m pytest tests -q
python -I -B scripts/benchmark_cpu.py --output benchmarks/results/local-new.json --cpu-name "YOUR OBSERVED CPU NAME"
```

The output path must not exist. The script verifies the exact reviewed
baseline source digest before executing it and uses only local source.
It requires Git commit `6b3b2160b7a301d7eb3a01ab7f62ac7445d4053a` in local history.
It never loads pickle/joblib, contacts the Hub, requests a GPU, or imports
third-party kernel code. CPU names are operator-supplied after hardware
inspection; machine, OS, interpreter, clock and logical CPU count are
recorded by the script.

Inputs are generated independently with sorted stdlib JSON and SHA-256,
including Unicode strings and integer facts. All generated row hashes must
match the kernel and a changed last-row fact must report `VIOLATED`.
Each measured candidate report must exactly equal the pre-change report;
the fixture must remain unchanged. Cryptographic verification remains
`UNAVAILABLE` because no signing key or signatures are supplied.

## Observed run on 2026-09-07

Hardware: Intel Core Ultra 9 285H, 16 logical CPUs, Windows 11 build 26200.
Runtime: CPython 3.12.10 AMD64; QueryPerformanceCounter, reported resolution
100 ns. One Python call stream; default GC; CPU affinity and machine load
not controlled. Five warmups and 31 samples per implementation/case, with
alternating baseline/candidate timing order. Timing covers all eight
invariants over in-memory rows, not fixture generation, validation, disk
I/O, JSON output serialization or network.

| Rows | Fixture | Baseline median ms | Candidate median ms | Candidate p95 ms |
|---:|---|---:|---:|---:|
| 1 | clean | 0.0435 | 0.0436 | 0.0536 |
| 1 | tampered | 0.0438 | 0.0440 | 0.0532 |
| 32 | clean | 1.0746 | 1.0547 | 1.9158 |
| 32 | tampered | 0.8104 | 0.8103 | 1.4345 |
| 256 | clean | 10.4259 | 9.6110 | 17.5413 |
| 256 | tampered | 9.2320 | 9.4795 | 18.7149 |
| 1024 | clean | 42.3200 | 43.6056 | 83.0980 |
| 1024 | tampered | 27.9273 | 27.8356 | 70.6106 |

The broad sample spread shows substantial host noise. No statistically
established speedup or regression is claimed. The baseline is the same
kernel before the receipt-object guard, not a competing library.

`results/cpu-20260907.json` retains all 496 raw timing samples, exact input
and output hashes, environment and source identities. It intentionally
records a dirty working tree: the candidate source was tested before its
commit. Its SHA-256 is
`f9e18412d331aa05ca3d2bda22bed2047b40395ca737933470c894c4bd09f88a`.
The candidate source canonical LF hash is
`d90e40e5bda398769e3a13a71e752526410de40e675c0c21c5b624547aedbdad`;
the receipt also records the actual Windows working-copy byte hash.

## Scope limits

Passing this benchmark does not qualify the pure-Python signature fallback,
nonfinite numeric inputs, every malformed ledger type, JavaScript/Python
number serialization equivalence, or published Hub artifacts. Those paths
require separate conformance checks. This deterministic software kernel has
no trainable weights; training a surrogate would not verify its invariants.
