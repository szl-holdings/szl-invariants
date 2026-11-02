"""A provenance join must identify one explicit non-demo ledger run."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "torch-ext/szl_invariants/__init__.py"
SPEC = importlib.util.spec_from_file_location("flywheel_join_kernel", SOURCE)
assert SPEC is not None and SPEC.loader is not None
kernel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kernel)


def lineage(rows, samples=None):
    report = kernel.run_invariants(
        rows,
        samples=samples if samples is not None else [{"sampleId": 17, "receiptId": "r-own"}],
    )
    return next(item for item in report["invariants"] if item["id"] == "flywheel-lineage")


OWN_METAL = {"id": 1, "ok": True, "demo": False, "servedNode": "node-a", "receiptId": "r-own"}


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("other_demo", [False, True])
def test_duplicate_receipts_do_not_choose_a_convenient_run(reverse, other_demo):
    rows = [dict(OWN_METAL), {**OWN_METAL, "id": 2, "demo": other_demo}]
    if reverse:
        rows.reverse()
    result = lineage(rows)
    assert result["status"] == "VIOLATED"
    assert result["checked"] == 1
    assert result["violations"] == 1
    assert result["worstRowId"] == 17


def test_prejoined_claim_cannot_resolve_an_ambiguous_receipt():
    rows = [dict(OWN_METAL), {**OWN_METAL, "id": 2}]
    samples = [{"sampleId": 17, "receiptId": "r-own", "runFound": True,
                "runDemo": False, "runServedNode": "node-a"}]
    assert lineage(rows, samples)["status"] == "VIOLATED"


@pytest.mark.parametrize("demo", [None, 0, 1, "false", "true", [], {}])
def test_non_boolean_demo_is_not_evidence_of_a_non_demo_run(demo):
    result = lineage([{**OWN_METAL, "demo": demo}])
    assert result["status"] == "VIOLATED"
    assert result["violations"] == 1


def test_missing_demo_is_not_evidence_of_a_non_demo_run():
    row = dict(OWN_METAL)
    del row["demo"]
    assert lineage([row])["status"] == "VIOLATED"


def test_unique_non_demo_join_holds_and_unrelated_duplicates_do_not_poison_it():
    rows = [dict(OWN_METAL), {**OWN_METAL, "id": 2, "receiptId": "other"},
            {**OWN_METAL, "id": 3, "receiptId": "other"}]
    result = lineage(rows)
    assert result["status"] == "HOLDS"
    assert result["checked"] == 1
    assert result["violations"] == 0


def test_unlinkable_samples_remain_explicitly_excluded():
    result = lineage([dict(OWN_METAL)], [{"sampleId": 17}])
    assert result["status"] == "NO_DATA"
    assert result["checked"] == 0
