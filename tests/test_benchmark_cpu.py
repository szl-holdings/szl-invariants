"""The benchmark fixtures use an independent stdlib hash construction."""
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("benchmark_cpu", ROOT / "scripts/benchmark_cpu.py")
assert SPEC is not None and SPEC.loader is not None
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)


def test_independent_reference_matches_kernel_and_detects_tamper() -> None:
    kernel = bench.load_reviewed((ROOT / bench.SOURCE).read_bytes(), "benchmark_test_kernel")
    for count in (1, 32, 256, 1024):
        rows = bench.make_rows(count)
        for row in rows:
            assert kernel.recompute_row_hash(row["prevHash"], row) == row["rowHash"]
        assert bench.chain_status(bench.evaluate(kernel, rows)) == "HOLDS"
        rows[-1]["latencyMs"] += 1
        assert bench.chain_status(bench.evaluate(kernel, rows)) == "VIOLATED"


def test_timing_summary_retains_all_raw_samples() -> None:
    assert bench.quantiles([10, 50, 20, 40, 30], 2) == {
        "samples_ns": [10, 50, 20, 40, 30], "min_ns": 10, "median_ns": 30,
        "p95_ns": 50, "max_ns": 50, "median_ns_per_row": 15,
    }


def test_comparison_ignores_only_documented_loop_predicate_not_status() -> None:
    before = {"invariants": [{"id": "loop-steps-positive", "predicate": "old", "status": "HOLDS"}]}
    after = {"invariants": [{"id": "loop-steps-positive", "predicate": "new", "status": "HOLDS"}]}
    assert bench.comparable_report(before) == bench.comparable_report(after)
    assert before["invariants"][0]["predicate"] == "old"
    after["invariants"][0]["status"] = "VIOLATED"
    assert bench.comparable_report(before) != bench.comparable_report(after)
