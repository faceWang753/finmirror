"""Validation for blinded expert-review submissions bound to one pilot digest."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
REVIEW_ROLES = frozenset({"independent_annotator", "adjudicator"})
TERNARY = frozenset({"yes", "no", "uncertain"})
RELATIONS = frozenset(
    {"reference", "should_change", "should_not_change", "should_abstain", "uncertain"}
)
REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "pilot_id",
        "dataset_sha256",
        "reviewer_id",
        "role",
        "blinded",
        "conflict_disclosure",
        "submitted_at",
        "case_id",
        "answerable",
        "relation",
        "material",
        "evidence_complete",
        "formula_correct",
        "evidence_anchors",
        "computed_value",
        "notes",
    }
)

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")


class ReviewSubmissionError(ValueError):
    """A submitted review cannot be admitted to the independent review record."""


def _string(row: Mapping[str, Any], field: str, *, allow_empty: bool = False) -> str:
    value = row[field]
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        qualifier = "a string" if allow_empty else "a non-empty string"
        raise ReviewSubmissionError(f"{field} must be {qualifier}")
    return value


def _enum(row: Mapping[str, Any], field: str, choices: frozenset[str]) -> str:
    value = _string(row, field)
    if value not in choices:
        raise ReviewSubmissionError(f"{field} must be one of {sorted(choices)}")
    return value


def _validate_row(row: Mapping[str, Any], *, line_number: int) -> dict[str, Any]:
    missing = REQUIRED_FIELDS - set(row)
    extra = set(row) - REQUIRED_FIELDS
    if missing:
        raise ReviewSubmissionError(
            f"review line {line_number} is missing fields: {sorted(missing)}"
        )
    if extra:
        raise ReviewSubmissionError(
            f"review line {line_number} has unknown fields: {sorted(extra)}"
        )
    if row["schema_version"] != SCHEMA_VERSION:
        raise ReviewSubmissionError(f"unsupported schema_version: {row['schema_version']}")
    for field in ("pilot_id", "reviewer_id", "case_id"):
        value = _string(row, field)
        if not _IDENTIFIER.fullmatch(value):
            raise ReviewSubmissionError(f"{field} is not a stable identifier")
    digest = _string(row, "dataset_sha256")
    if not _SHA256.fullmatch(digest):
        raise ReviewSubmissionError("dataset_sha256 must be lowercase hexadecimal SHA-256")
    role = _enum(row, "role", REVIEW_ROLES)
    if not isinstance(row["blinded"], bool):
        raise ReviewSubmissionError("blinded must be a boolean")
    if role == "independent_annotator" and not row["blinded"]:
        raise ReviewSubmissionError("independent annotations must be completed blind")
    _string(row, "conflict_disclosure")
    submitted_at = _string(row, "submitted_at")
    if not _UTC_TIMESTAMP.fullmatch(submitted_at):
        raise ReviewSubmissionError("submitted_at must be an ISO-8601 UTC timestamp")
    _enum(row, "answerable", TERNARY)
    _enum(row, "relation", RELATIONS)
    _enum(row, "material", TERNARY)
    _enum(row, "evidence_complete", TERNARY)
    _enum(row, "formula_correct", TERNARY)
    anchors = row["evidence_anchors"]
    if not isinstance(anchors, list) or not all(
        isinstance(item, str) and item.strip() for item in anchors
    ):
        raise ReviewSubmissionError("evidence_anchors must be an array of non-empty strings")
    if len(anchors) != len(set(anchors)):
        raise ReviewSubmissionError("evidence_anchors must be unique")
    _string(row, "computed_value", allow_empty=True)
    _string(row, "notes", allow_empty=True)
    return dict(row)


def validate_review_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_case_ids: Iterable[str],
    pilot_id: str,
    dataset_sha256: str,
) -> list[dict[str, Any]]:
    """Validate a complete, internally consistent review submission."""

    validated = [_validate_row(row, line_number=index) for index, row in enumerate(rows, 1)]
    if not validated:
        raise ReviewSubmissionError("review submission is empty")
    case_ids = [str(row["case_id"]) for row in validated]
    if len(case_ids) != len(set(case_ids)):
        raise ReviewSubmissionError("review submission contains duplicate case_id values")
    expected = set(expected_case_ids)
    actual = set(case_ids)
    if actual != expected:
        raise ReviewSubmissionError(
            "review case IDs differ from the pilot; "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    invariants = {
        field: {row[field] for row in validated}
        for field in (
            "schema_version",
            "pilot_id",
            "dataset_sha256",
            "reviewer_id",
            "role",
            "blinded",
            "conflict_disclosure",
            "submitted_at",
        )
    }
    inconsistent = sorted(field for field, values in invariants.items() if len(values) != 1)
    if inconsistent:
        raise ReviewSubmissionError(f"submission metadata changes between rows: {inconsistent}")
    if invariants["pilot_id"] != {pilot_id}:
        raise ReviewSubmissionError("submission is bound to a different pilot_id")
    if invariants["dataset_sha256"] != {dataset_sha256}:
        raise ReviewSubmissionError("submission is bound to a different dataset digest")
    return sorted(validated, key=lambda row: str(row["case_id"]))


def load_review_submission(
    path: str | Path,
    *,
    expected_case_ids: Iterable[str],
    pilot_id: str,
    dataset_sha256: str,
) -> list[dict[str, Any]]:
    """Load JSONL and validate it against the exact pending pilot."""

    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReviewSubmissionError(
                    f"invalid JSON on review line {line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise ReviewSubmissionError(f"review line {line_number} must be an object")
            rows.append(value)
    return validate_review_rows(
        rows,
        expected_case_ids=expected_case_ids,
        pilot_id=pilot_id,
        dataset_sha256=dataset_sha256,
    )
