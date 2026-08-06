"""Build data for a zero-backend, model-output-blind expert review interface."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from finmirror.models import BenchmarkCase
from finmirror.review import ExpertReviewStatus


def blind_review_payload(
    cases: Iterable[BenchmarkCase], status: ExpertReviewStatus
) -> dict[str, Any]:
    """Return only fields reviewers may inspect before independent labels are frozen."""

    case_list = list(cases)
    actual_ids = {case.case_id for case in case_list}
    if actual_ids != set(status.case_ids):
        raise ValueError("review app cases do not match the status record")
    sanitized = []
    for case in case_list:
        sanitized.append(
            {
                "case_id": case.case_id,
                "question": case.question,
                "documents": [
                    {
                        "id": document.id,
                        "title": document.title,
                        "content": document.content,
                        "source_url": document.source_url,
                    }
                    for document in case.documents
                ],
            }
        )
    return {
        "schema_version": "1.0",
        "pilot_id": status.pilot_id,
        "dataset_sha256": status.dataset_sha256,
        "case_count": len(sanitized),
        "cases": sanitized,
    }


def write_review_data(
    cases: Iterable[BenchmarkCase], status: ExpertReviewStatus, output_path: str | Path
) -> None:
    """Write deterministic JavaScript data consumed by the static review app."""

    payload = blind_review_payload(cases, status)
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        f"window.FINMIRROR_REVIEW_DATA={rendered};\n",
        encoding="utf-8",
        newline="\n",
    )
