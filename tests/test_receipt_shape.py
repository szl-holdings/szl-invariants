"""Malformed but valid JSON receipts are violations, never report crashes."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "torch-ext/szl_invariants/__init__.py"
SPEC = importlib.util.spec_from_file_location("receipt_shape_kernel", SOURCE)
assert SPEC is not None and SPEC.loader is not None
kernel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kernel)


@pytest.mark.parametrize("receipt", ["null", "[]", '[{"receiptId":"r1"}]', "true", "7", '"text"'])
def test_non_object_receipt_is_violated_without_crashing_report(receipt: str) -> None:
    report = kernel.run_invariants([{"id": 23, "receiptJson": receipt}])
    result = next(item for item in report["invariants"] if item["id"] == "receipt-columns-consistent")
    assert result["status"] == "VIOLATED"
    assert result["checked"] == 1
    assert result["violations"] == 1
    assert result["worstRowId"] == 23
    assert len(report["invariants"]) == 8
    assert report["latentVerification"]["status"] == "UNAVAILABLE"


def test_valid_receipt_still_holds_and_malformed_receipt_still_violates() -> None:
    good = {"id": 23, "receiptId": "r1", "goalSha256": "goal", "keyId": "key"}
    good["receiptJson"] = kernel.canonical_json({k: v for k, v in good.items() if k != "id"})
    for row, expected in [(good, "HOLDS"), ({**good, "receiptJson": "{"}, "VIOLATED")]:
        report = kernel.run_invariants([row])
        result = next(item for item in report["invariants"] if item["id"] == "receipt-columns-consistent")
        assert result["status"] == expected
