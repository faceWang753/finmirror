"""Small, auditable helpers for human annotation quality checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: str | Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
            if not isinstance(row, dict) or "case_id" not in row:
                raise ValueError(f"Annotation line {line_number} needs a case_id")
            case_id = str(row["case_id"])
            if case_id in rows:
                raise ValueError(f"Duplicate annotation: {case_id}")
            rows[case_id] = row
    return rows


def cohen_kappa(left: list[str], right: list[str]) -> float:
    """Cohen's kappa for two categorical annotation vectors."""

    if len(left) != len(right) or not left:
        raise ValueError("Kappa requires two non-empty vectors of equal length")
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / len(left)
    labels = set(left) | set(right)
    expected = sum(
        (left.count(label) / len(left)) * (right.count(label) / len(right)) for label in labels
    )
    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)


def annotation_agreement(
    left_path: str | Path,
    right_path: str | Path,
    fields: list[str],
) -> dict[str, Any]:
    left = _load(left_path)
    right = _load(right_path)
    if set(left) != set(right):
        missing_left = sorted(set(right) - set(left))
        missing_right = sorted(set(left) - set(right))
        raise ValueError(
            f"Annotation IDs differ; missing_left={missing_left[:5]}, "
            f"missing_right={missing_right[:5]}"
        )
    case_ids = sorted(left)
    result: dict[str, Any] = {"case_count": len(case_ids), "fields": {}}
    for field in fields:
        left_values = [str(left[case_id].get(field, "<MISSING>")) for case_id in case_ids]
        right_values = [str(right[case_id].get(field, "<MISSING>")) for case_id in case_ids]
        agreement = sum(a == b for a, b in zip(left_values, right_values, strict=True)) / len(
            case_ids
        )
        result["fields"][field] = {
            "raw_agreement": agreement,
            "cohen_kappa": cohen_kappa(left_values, right_values),
            "labels": sorted(set(left_values) | set(right_values)),
        }
    return result
