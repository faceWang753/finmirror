"""Tests for fail-closed expert review status records."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from finmirror.review import (
    ExpertReviewError,
    ExpertReviewStatus,
    load_expert_review_status,
    require_expert_validated,
)


def _pending() -> ExpertReviewStatus:
    return ExpertReviewStatus(
        schema_version="1.0",
        pilot_id="statcan-gdp-pilot",
        case_ids=("case-a", "case-b"),
        dataset_sha256="a" * 64,
        review_state="pending_external_review",
        gold_status="provisional_machine_derived",
        independent_annotators_required=2,
        independent_annotators_completed=0,
        adjudicators_required=1,
        adjudicators_completed=0,
        raw_agreement=None,
        cohen_kappa=None,
        disagreements_total=None,
        disagreements_adjudicated=None,
        model_outputs_hidden=True,
        notes="No external review has been completed.",
    )


def test_pending_review_is_valid_metadata_but_blocks_expert_claim() -> None:
    status = _pending()
    status.validate()
    with pytest.raises(ExpertReviewError, match="expert-validation claim blocked"):
        require_expert_validated(status)
    assert "independent annotation is incomplete" in status.validation_blockers()


def test_complete_review_passes_all_release_gates() -> None:
    status = replace(
        _pending(),
        review_state="expert_validated",
        gold_status="adjudicated_expert_gold",
        independent_annotators_completed=2,
        adjudicators_completed=1,
        raw_agreement=0.95,
        cohen_kappa=0.84,
        disagreements_total=2,
        disagreements_adjudicated=2,
    )
    require_expert_validated(status, dataset_sha256="a" * 64)
    assert status.validation_blockers() == ()


def test_review_digest_must_match_the_cases_being_released() -> None:
    status = replace(
        _pending(),
        review_state="expert_validated",
        gold_status="adjudicated_expert_gold",
        independent_annotators_completed=2,
        adjudicators_completed=1,
        raw_agreement=1.0,
        cohen_kappa=1.0,
        disagreements_total=0,
        disagreements_adjudicated=0,
    )
    with pytest.raises(ExpertReviewError, match="does not bind the supplied dataset"):
        require_expert_validated(status, dataset_sha256="b" * 64)


def test_review_status_rejects_duplicate_case_ids() -> None:
    raw = {
        "schema_version": "1.0",
        "pilot_id": "statcan-gdp-pilot",
        "case_ids": ["case-a", "case-a"],
        "dataset_sha256": "a" * 64,
        "review_state": "pending_external_review",
        "gold_status": "provisional_machine_derived",
        "independent_annotators_required": 2,
        "independent_annotators_completed": 0,
        "adjudicators_required": 1,
        "adjudicators_completed": 0,
        "raw_agreement": None,
        "cohen_kappa": None,
        "disagreements_total": None,
        "disagreements_adjudicated": None,
        "model_outputs_hidden": True,
        "notes": "Pending.",
    }
    with pytest.raises(ExpertReviewError, match="case_ids must be unique"):
        ExpertReviewStatus.from_dict(raw)


def _raw_pending() -> dict[str, object]:
    status = _pending()
    return {
        "schema_version": status.schema_version,
        "pilot_id": status.pilot_id,
        "case_ids": list(status.case_ids),
        "dataset_sha256": status.dataset_sha256,
        "review_state": status.review_state,
        "gold_status": status.gold_status,
        "independent_annotators_required": status.independent_annotators_required,
        "independent_annotators_completed": status.independent_annotators_completed,
        "adjudicators_required": status.adjudicators_required,
        "adjudicators_completed": status.adjudicators_completed,
        "raw_agreement": status.raw_agreement,
        "cohen_kappa": status.cohen_kappa,
        "disagreements_total": status.disagreements_total,
        "disagreements_adjudicated": status.disagreements_adjudicated,
        "model_outputs_hidden": status.model_outputs_hidden,
        "notes": status.notes,
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("independent_annotators_completed", True, "non-negative integer"),
        ("adjudicators_completed", -1, "non-negative integer"),
        ("raw_agreement", "high", "null or a number"),
        ("cohen_kappa", 1.1, "between 0 and 1"),
        ("disagreements_total", True, "null or a non-negative integer"),
    ],
)
def test_review_status_rejects_invalid_field_shapes(
    field: str,
    value: object,
    message: str,
) -> None:
    raw = _raw_pending()
    raw[field] = value
    with pytest.raises(ExpertReviewError, match=message):
        ExpertReviewStatus.from_dict(raw)


def test_review_status_rejects_missing_and_unknown_fields() -> None:
    missing = _raw_pending()
    missing.pop("notes")
    with pytest.raises(ExpertReviewError, match="missing fields"):
        ExpertReviewStatus.from_dict(missing)

    extra = _raw_pending()
    extra["endorsement"] = True
    with pytest.raises(ExpertReviewError, match="unknown fields"):
        ExpertReviewStatus.from_dict(extra)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": "2.0"}, "unsupported review schema_version"),
        ({"pilot_id": "Not Valid"}, "stable lowercase identifier"),
        ({"dataset_sha256": "ABC"}, "64 lowercase"),
        ({"review_state": "approved"}, "unsupported review_state"),
        ({"gold_status": "expertish"}, "unsupported gold_status"),
        ({"model_outputs_hidden": "yes"}, "must be a boolean"),
        ({"notes": ""}, "notes must be non-empty"),
        ({"independent_annotators_required": 1}, "at least two"),
        ({"adjudicators_required": 0}, "at least one"),
        (
            {"disagreements_total": 1, "disagreements_adjudicated": None},
            "must both be null",
        ),
        (
            {"disagreements_total": 1, "disagreements_adjudicated": 2},
            "cannot exceed",
        ),
    ],
)
def test_review_status_validates_claim_contract(
    changes: dict[str, object],
    message: str,
) -> None:
    status = replace(_pending(), **changes)
    with pytest.raises(ExpertReviewError, match=message):
        status.validate()


def test_load_review_status_rejects_invalid_json_and_non_objects(tmp_path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{not json}", encoding="utf-8")
    with pytest.raises(ExpertReviewError, match="invalid JSON"):
        load_expert_review_status(invalid)

    array = tmp_path / "array.json"
    array.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ExpertReviewError, match="must be an object"):
        load_expert_review_status(array)
