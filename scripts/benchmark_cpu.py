#!/usr/bin/env python3
"""Bounded, owner-run CPU microbenchmark of reviewed invariant source.

No Hub loader, network, weights, GPU, live data or signature authority. The
baseline is the reviewed Git commit supplied explicitly, not an external library.
Only unsigned synthetic rows with integer-valued facts are benchmarked.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import types


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "torch-ext/szl_invariants/__init__.py"
REVIEWED_BASE = "6b3b2160b7a301d7eb3a01ab7f62ac7445d4053a"
REVIEWED_BASE_SHA256 = "865b34d7196a657f2b9f7cdb3aca615332592d01ebcf0cd9ffd68ad9a4c5abbf"
CORE_FIELDS = (
    "endpoint", "mode", "requestedProvider", "servedProvider", "model",
    "servedNode", "demo", "ok", "latencyMs", "error",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def reference_hash(previous: str, row: dict) -> str:
    facts = {key: row.get(key) for key in CORE_FIELDS}
    content = digest(encode(facts))
    return digest(f"{previous}|{content}".encode("utf-8"))


def make_rows(size: int) -> list[dict]:
    previous = "genesis"
    rows = []
    for index in range(1, size + 1):
        row = dict(id=index, endpoint="/synthetic/run", mode="fixture",
                   requestedProvider="fixture", servedProvider="synthetic",
                   model="synthetic-α", servedNode="cpu-fixture", demo=False,
                   ok=True, latencyMs=index % 19, error=None, loopSteps=1,
                   receiptId=None, receiptJson=None, signature=None, keyId=None,
                   goalSha256=None, outputSha256=None, prevHash=previous)
        row["rowHash"] = reference_hash(previous, row)
        previous = row["rowHash"]
        rows.append(row)
    return rows


def load_reviewed(data: bytes, label: str) -> types.ModuleType:
    module = types.ModuleType(label)
    exec(compile(data, label, "exec"), module.__dict__)
    return module


def evaluate(module: types.ModuleType, rows: list[dict]) -> dict:
    return module.run_invariants(rows, samples=[], pubkey=None)


def chain_status(report: dict) -> str:
    return next(item["status"] for item in report["invariants"] if item["id"] == "receipt-chain-continuity")


def quantiles(samples: list[int], rows: int) -> dict:
    ordered = sorted(samples)
    return {"samples_ns": samples, "min_ns": min(samples),
            "median_ns": statistics.median(samples),
            "p95_ns": ordered[math.ceil(0.95 * len(ordered)) - 1],
            "max_ns": max(samples),
            "median_ns_per_row": statistics.median(samples) / rows}


def run(*, repeats: int, warmup: int, cpu_name: str) -> dict:
    baseline_bytes = subprocess.check_output(["git", "show", f"{REVIEWED_BASE}:{SOURCE}"], cwd=ROOT)
    if digest(baseline_bytes) != REVIEWED_BASE_SHA256:
        raise RuntimeError("reviewed baseline source digest mismatch")
    candidate_bytes = (ROOT / SOURCE).read_bytes()
    baseline = load_reviewed(baseline_bytes, "reviewed_baseline")
    candidate = load_reviewed(candidate_bytes, "reviewed_candidate")
    records = []
    for size in (1, 32, 256, 1024):
        rows = make_rows(size)
        for case in ("clean", "tampered"):
            fixture = [dict(row) for row in rows]
            if case == "tampered":
                fixture[-1]["latencyMs"] += 1
            expected = "HOLDS" if case == "clean" else "VIOLATED"
            before = encode(fixture)
            base_report = evaluate(baseline, fixture)
            candidate_report = evaluate(candidate, fixture)
            if candidate_report != base_report or chain_status(candidate_report) != expected:
                raise AssertionError("candidate/reference fixture correctness failed")
            if candidate_report["latentVerification"]["status"] != "UNAVAILABLE":
                raise AssertionError("missing signature authority must remain unavailable")
            for _ in range(warmup):
                evaluate(baseline, fixture)
                evaluate(candidate, fixture)
            samples = {"baseline": [], "candidate": []}
            modules = {"baseline": baseline, "candidate": candidate}
            for trial in range(repeats):
                order = ("baseline", "candidate") if trial % 2 == 0 else ("candidate", "baseline")
                for name in order:
                    started = time.perf_counter_ns()
                    observed = evaluate(modules[name], fixture)
                    elapsed = time.perf_counter_ns() - started
                    if observed != candidate_report:
                        raise AssertionError("non-deterministic result during measured run")
                    samples[name].append(elapsed)
            if encode(fixture) != before:
                raise AssertionError("kernel mutated benchmark input")
            records.append({"rows": size, "case": case, "chain_status": expected,
                            "fixture_sha256": digest(before), "output_sha256": digest(encode(candidate_report)),
                            "output_summary": candidate_report["summary"],
                            "timings": {name: quantiles(values, size) for name, values in samples.items()}})
    return {
        "schema": "szl.invariants-cpu-microbenchmark/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "MEASURED_LOCAL_CPU_SYNTHETIC_ONLY",
        "source_repository": "szl-holdings/szl-invariants", "baseline_git_sha": REVIEWED_BASE,
        "baseline_source_sha256": digest(baseline_bytes), "candidate_source_sha256": digest(candidate_bytes),
        "candidate_source_lf_sha256": digest(candidate_bytes.replace(b"\r\n", b"\n")),
        "benchmark_script_sha256": digest(Path(__file__).read_bytes()),
        "candidate_git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "worktree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip()),
        "environment": {"python": sys.version, "implementation": platform.python_implementation(),
                        "os": platform.platform(), "machine": platform.machine(),
                        "cpu_name_operator_observed": cpu_name, "logical_cpus": os.cpu_count(),
                        "timer": vars(time.get_clock_info("perf_counter")), "device": "CPU"},
        "method": {"warmup_per_implementation_per_case": warmup, "samples_per_implementation_per_case": repeats,
                   "ordering": "alternating baseline/candidate", "gc": "default enabled",
                   "threads": "one Python call stream; process affinity and host load uncontrolled",
                   "input_scope": "unsigned synthetic integer facts; eight invariants replayed; crypto unavailable",
                   "baseline_scope": "same reviewed kernel before receipt-object type guard; not a competing library"},
        "cases": records,
        "limitations": ["Microbenchmark only: no general speedup, production throughput or energy claim.",
                        "No GPU/CUDA execution or evaluation of published Hub bytes.",
                        "No signature fallback qualification, cross-language numeric canonicalization or live ledger validation.",
                        "No trained weights exist in this software kernel; no training was performed."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cpu-name", required=True)
    parser.add_argument("--repeats", type=int, default=31)
    parser.add_argument("--warmup", type=int, default=5)
    args = parser.parse_args()
    if not 5 <= args.repeats <= 101 or not 1 <= args.warmup <= 20:
        parser.error("bounded repeats must be 5..101 and warmup 1..20")
    receipt = run(repeats=args.repeats, warmup=args.warmup, cpu_name=args.cpu_name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "sha256": digest(args.output.read_bytes()),
                      "cases": len(receipt["cases"]), "status": receipt["status"]}))


if __name__ == "__main__":
    main()
