"""Tests for complete, digest-bound blinded review submissions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finmirror.review_submission import (
    ReviewSubmissionError,
    load_review_submission,
    validate_review_rows,
)

DIGEST = "a" * 64
CASE_IDS = ("case-one", "case-two")


def _row(case_id: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "pilot_id": "pilot-one",
        "dataset_sha256": DIGEST,
        "reviewer_id": "reviewer-alpha",
        "role": "independent_annotator",
        "blinded": True,
        "conflict_disclosure": "none known",
        "submitted_at": "2026-08-06T12:34:56.789Z",
        "case_id": case_id,
        "answerable": "yes",
        "relation": "should_not_change",
        "material": "no",
        "evidence_complete": "yes",
        "formula_correct": "yes",
        "evidence_anchors": [f"doc:{case_id}#E1", f"doc:{case_id}#E2"],
        "computed_value": "0.47%",
        "notes": "",
    }


def _validate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return validate_review_rows(
        rows,
        expected_case_ids=CASE_IDS,
        pilot_id="pilot-one",
        dataset_sha256=DIGEST,
    )


def test_complete_blinded_submission_is_accepted_and_sorted() -> None:
    rows = _validate([_row("case-two"), _row("case-one")])
    assert [row["case_id"] for row in rows] == ["case-one", "case-two"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("blinded", False, "completed blind"),
        ("dataset_sha256", "b" * 64, "different dataset digest"),
        ("pilot_id", "pilot-two", "different pilot_id"),
        ("answerable", "maybe", "answerable must be one of"),
        ("submitted_at", "yesterday", "ISO-8601 UTC"),
        ("evidence_anchors", ["E1", "E1"], "must be unique"),
    ],
)
def test_submission_rejects_invalid_or_unbound_fields(
    field: str, value: object, message: str
) -> None:
    rows = [_row("case-one"), _row("case-two")]
    for row in rows:
        row[field] = value
    with pytest.raises(ReviewSubmissionError, match=message):
        _validate(rows)


def test_submission_rejects_missing_extra_duplicate_and_inconsistent_rows() -> None:
    missing = [_row("case-one")]
    with pytest.raises(ReviewSubmissionError, match=r"missing=.*case-two"):
        _validate(missing)

    duplicate = [_row("case-one"), _row("case-one")]
    with pytest.raises(ReviewSubmissionError, match="duplicate case_id"):
        _validate(duplicate)

    extra_field = [_row("case-one"), _row("case-two")]
    extra_field[0]["score"] = 1
    with pytest.raises(ReviewSubmissionError, match="unknown fields"):
        _validate(extra_field)

    inconsistent = [_row("case-one"), _row("case-two")]
    inconsistent[1]["reviewer_id"] = "reviewer-beta"
    with pytest.raises(ReviewSubmissionError, match="metadata changes"):
        _validate(inconsistent)


def test_jsonl_loader_rejects_non_object_and_invalid_json(tmp_path: Path) -> None:
    non_object = tmp_path / "array.jsonl"
    non_object.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ReviewSubmissionError, match="must be an object"):
        load_review_submission(
            non_object,
            expected_case_ids=CASE_IDS,
            pilot_id="pilot-one",
            dataset_sha256=DIGEST,
        )

    invalid = tmp_path / "invalid.jsonl"
    invalid.write_text("{\n", encoding="utf-8")
    with pytest.raises(ReviewSubmissionError, match="invalid JSON"):
        load_review_submission(
            invalid,
            expected_case_ids=CASE_IDS,
            pilot_id="pilot-one",
            dataset_sha256=DIGEST,
        )


def test_jsonl_loader_accepts_the_browser_export_shape(tmp_path: Path) -> None:
    path = tmp_path / "review.jsonl"
    path.write_text(
        "\n".join(json.dumps(_row(case_id)) for case_id in CASE_IDS) + "\n",
        encoding="utf-8",
    )
    rows = load_review_submission(
        path,
        expected_case_ids=CASE_IDS,
        pilot_id="pilot-one",
        dataset_sha256=DIGEST,
    )
    assert len(rows) == 2
