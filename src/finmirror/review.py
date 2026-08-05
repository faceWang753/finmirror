"""Fail-closed status records for external expert review of real-source pilots."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ReviewState = Literal["pending_external_review", "expert_validated", "blocked"]
GoldStatus = Literal["provisional_machine_derived", "adjudicated_expert_gold"]

SCHEMA_VERSION = "1.0"
REVIEW_STATES = frozenset({"pending_external_review", "expert_validated", "blocked"})
GOLD_STATUSES = frozenset({"provisional_machine_derived", "adjudicated_expert_gold"})
REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "pilot_id",
        "case_ids",
        "dataset_sha256",
        "review_state",
        "gold_status",
        "independent_annotators_required",
        "independent_annotators_completed",
        "adjudicators_required",
        "adjudicators_completed",
        "raw_agreement",
        "cohen_kappa",
        "disagreements_total",
        "disagreements_adjudicated",
        "model_outputs_hidden",
        "notes",
    }
)

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ExpertReviewError(ValueError):
    """A review record is malformed or does not justify expert-validation claims."""


def _integer(data: Mapping[str, Any], field: str) -> int:
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExpertReviewError(f"{field} must be a non-negative integer")
    return value


def _nullable_rate(data: Mapping[str, Any], field: str) -> float | None:
    value = data[field]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExpertReviewError(f"{field} must be null or a number")
    rate = float(value)
    if not 0.0 <= rate <= 1.0:
        raise ExpertReviewError(f"{field} must be between 0 and 1")
    return rate


@dataclass(frozen=True)
class ExpertReviewStatus:
    """Machine-checkable boundary between provisional and expert-reviewed gold."""

    schema_version: str
    pilot_id: str
    case_ids: tuple[str, ...]
    dataset_sha256: str
    review_state: ReviewState
    gold_status: GoldStatus
    independent_annotators_required: int
    independent_annotators_completed: int
    adjudicators_required: int
    adjudicators_completed: int
    raw_agreement: float | None
    cohen_kappa: float | None
    disagreements_total: int | None
    disagreements_adjudicated: int | None
    model_outputs_hidden: bool
    notes: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ExpertReviewStatus:
        missing = REQUIRED_FIELDS - set(data)
        extra = set(data) - REQUIRED_FIELDS
        if missing:
            raise ExpertReviewError(f"review status is missing fields: {sorted(missing)}")
        if extra:
            raise ExpertReviewError(f"review status has unknown fields: {sorted(extra)}")
        case_ids = data["case_ids"]
        if not isinstance(case_ids, list) or not case_ids:
            raise ExpertReviewError("case_ids must be a non-empty JSON array")
        if not all(isinstance(item, str) and item.strip() for item in case_ids):
            raise ExpertReviewError("case_ids must contain non-empty strings")
        if len(case_ids) != len(set(case_ids)):
            raise ExpertReviewError("case_ids must be unique")
        disagreements_total_raw = data["disagreements_total"]
        disagreements_adjudicated_raw = data["disagreements_adjudicated"]
        for field, value in (
            ("disagreements_total", disagreements_total_raw),
            ("disagreements_adjudicated", disagreements_adjudicated_raw),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise ExpertReviewError(f"{field} must be null or a non-negative integer")
        status = cls(
            schema_version=str(data["schema_version"]),
            pilot_id=str(data["pilot_id"]),
            case_ids=tuple(str(item) for item in case_ids),
            dataset_sha256=str(data["dataset_sha256"]),
            review_state=str(data["review_state"]),  # type: ignore[arg-type]
            gold_status=str(data["gold_status"]),  # type: ignore[arg-type]
            independent_annotators_required=_integer(data, "independent_annotators_required"),
            independent_annotators_completed=_integer(data, "independent_annotators_completed"),
            adjudicators_required=_integer(data, "adjudicators_required"),
            adjudicators_completed=_integer(data, "adjudicators_completed"),
            raw_agreement=_nullable_rate(data, "raw_agreement"),
            cohen_kappa=_nullable_rate(data, "cohen_kappa"),
            disagreements_total=disagreements_total_raw,
            disagreements_adjudicated=disagreements_adjudicated_raw,
            model_outputs_hidden=data["model_outputs_hidden"],
            notes=str(data["notes"]),
        )
        status.validate()
        return status

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ExpertReviewError(f"unsupported review schema_version: {self.schema_version}")
        if not _IDENTIFIER.fullmatch(self.pilot_id):
            raise ExpertReviewError("pilot_id must be a stable lowercase identifier")
        if not _SHA256.fullmatch(self.dataset_sha256):
            raise ExpertReviewError(
                "dataset_sha256 must be 64 lowercase hexadecimal characters"
            )
        if self.review_state not in REVIEW_STATES:
            raise ExpertReviewError(f"unsupported review_state: {self.review_state}")
        if self.gold_status not in GOLD_STATUSES:
            raise ExpertReviewError(f"unsupported gold_status: {self.gold_status}")
        if not isinstance(self.model_outputs_hidden, bool):
            raise ExpertReviewError("model_outputs_hidden must be a boolean")
        if not self.notes.strip():
            raise ExpertReviewError("notes must be non-empty")
        if self.independent_annotators_required < 2:
            raise ExpertReviewError("at least two independent annotators are required")
        if self.adjudicators_required < 1:
            raise ExpertReviewError("at least one adjudicator is required")
        if (self.disagreements_total is None) != (self.disagreements_adjudicated is None):
            raise ExpertReviewError("disagreement totals must both be null or both be recorded")
        if (
            self.disagreements_total is not None
            and self.disagreements_adjudicated is not None
            and self.disagreements_adjudicated > self.disagreements_total
        ):
            raise ExpertReviewError(
                "disagreements_adjudicated cannot exceed disagreements_total"
            )

    def validation_blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if self.review_state != "expert_validated":
            blockers.append(f"review_state is {self.review_state}")
        if self.gold_status != "adjudicated_expert_gold":
            blockers.append(f"gold_status is {self.gold_status}")
        if self.independent_annotators_completed < self.independent_annotators_required:
            blockers.append("independent annotation is incomplete")
        if self.adjudicators_completed < self.adjudicators_required:
            blockers.append("adjudication is incomplete")
        if self.raw_agreement is None or self.raw_agreement < 0.90:
            blockers.append("raw agreement is missing or below 0.90")
        if self.cohen_kappa is None or self.cohen_kappa < 0.80:
            blockers.append("Cohen's kappa is missing or below 0.80")
        if self.disagreements_total is None or self.disagreements_adjudicated is None:
            blockers.append("disagreement adjudication counts are missing")
        elif self.disagreements_adjudicated != self.disagreements_total:
            blockers.append("not all disagreements were adjudicated")
        if not self.model_outputs_hidden:
            blockers.append("model outputs were not hidden during gold review")
        return tuple(blockers)


def load_expert_review_status(path: str | Path) -> ExpertReviewStatus:
    review_path = Path(path)
    try:
        raw = json.loads(review_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExpertReviewError(f"invalid JSON in {review_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ExpertReviewError(f"review status in {review_path} must be an object")
    return ExpertReviewStatus.from_dict(raw)


def require_expert_validated(
    status: ExpertReviewStatus,
    *,
    dataset_sha256: str | None = None,
) -> None:
    """Fail unless the status justifies an expert-validated gold claim."""

    status.validate()
    blockers = list(status.validation_blockers())
    if dataset_sha256 is not None and status.dataset_sha256 != dataset_sha256:
        blockers.append("review status does not bind the supplied dataset digest")
    if blockers:
        raise ExpertReviewError("expert-validation claim blocked: " + "; ".join(blockers))
