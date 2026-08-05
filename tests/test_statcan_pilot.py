"""Offline integrity tests for the review-pending Statistics Canada pilot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from finmirror.dataset import dataset_digest, validate_cases
from finmirror.models import BenchmarkCase
from finmirror.review import load_expert_review_status
from finmirror.sources import load_ledger

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = PROJECT_ROOT / "sources" / "v0.2" / "calibration" / "statcan-gdp-2025q2-q3"


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_committed_pilot_is_one_complete_review_pending_group() -> None:
    raw_cases = _load_jsonl(PILOT_ROOT / "reference.jsonl") + _load_jsonl(
        PILOT_ROOT / "counterfactuals.jsonl"
    )
    cases = [BenchmarkCase.from_dict(item) for item in raw_cases]
    validate_cases(cases)
    assert len(cases) == 7
    assert len({item.pair_group_id for item in cases}) == 1
    assert {item.relationship.transform for item in cases} == {
        "reference",
        "material_value",
        "distractor",
        "entity_collision",
        "period_collision",
        "injection",
        "evidence_ablation",
    }
    assert all("pending-expert-review" in item.tags for item in cases)

    status = load_expert_review_status(PILOT_ROOT / "review-status.json")
    assert dataset_digest(cases) == status.dataset_sha256
    assert set(status.case_ids) == {item.case_id for item in cases}
    assert status.review_state == "pending_external_review"
    assert status.validation_blockers()


def test_source_extract_matches_the_captured_receipt_and_process_hash() -> None:
    source = json.loads((PILOT_ROOT / "source.json").read_text(encoding="utf-8"))
    receipts = load_ledger(PROJECT_ROOT / "sources" / "v0.2" / "ledger.jsonl")
    statcan = next(item for item in receipts if item.provider == "Statistics Canada")
    assert source["capture_sha256"] == statcan.content_sha256
    assert source["capture_bytes"] == statcan.content_bytes
    assert source["receipt_id"] == statcan.receipt_id
    assert len(source["observations"]) == 5

    manifest = json.loads(
        (PROJECT_ROOT / "sources" / "v0.2" / "evidence-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    process_digest = hashlib.sha256(
        (PROJECT_ROOT / "scripts" / "curate_statcan_gdp_pilot.py").read_bytes()
    ).hexdigest()
    process_bound = [
        item
        for item in manifest["artifacts"]
        if item.get("process_id") == "curate-statcan-gdp-pilot-v1"
    ]
    assert len(process_bound) == 3
    assert {item["process_sha256"] for item in process_bound} == {process_digest}


def test_curator_rejects_unreviewed_capture_bytes(tmp_path: Path) -> None:
    from scripts.curate_statcan_gdp_pilot import build

    bad_capture = tmp_path / "unreviewed.zip"
    bad_capture.write_bytes(b"not the reviewed provider capture")
    with pytest.raises(ValueError, match="do not match the reviewed"):
        build(bad_capture, tmp_path / "out")
