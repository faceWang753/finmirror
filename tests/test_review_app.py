"""Privacy and blinding tests for the static expert-review interface."""

from __future__ import annotations

import json
from pathlib import Path

from finmirror.models import BenchmarkCase
from finmirror.review import load_expert_review_status
from finmirror.review_app import blind_review_payload, write_review_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = PROJECT_ROOT / "sources" / "v0.2" / "calibration" / "statcan-gdp-2025q2-q3"
APP_ROOT = PROJECT_ROOT / "artifacts" / "demo" / "review"


def _cases() -> list[BenchmarkCase]:
    rows = []
    for name in ("reference.jsonl", "counterfactuals.jsonl"):
        rows.extend(
            json.loads(line)
            for line in (PILOT_ROOT / name).read_text(encoding="utf-8").splitlines()
        )
    return [BenchmarkCase.from_dict(row) for row in rows]


def test_blind_payload_contains_no_gold_relationships_or_model_outputs() -> None:
    status = load_expert_review_status(PILOT_ROOT / "review-status.json")
    payload = blind_review_payload(_cases(), status)
    rendered = json.dumps(payload, sort_keys=True)
    assert payload["case_count"] == 7
    assert payload["dataset_sha256"] == status.dataset_sha256
    assert set(payload) == {
        "schema_version",
        "pilot_id",
        "dataset_sha256",
        "case_count",
        "cases",
    }
    assert '"expected"' not in rendered
    assert '"relationship"' not in rendered
    assert '"score"' not in rendered
    assert '"prediction"' not in rendered
    assert all(set(case) == {"case_id", "question", "documents"} for case in payload["cases"])


def test_committed_review_data_is_deterministic(tmp_path: Path) -> None:
    status = load_expert_review_status(PILOT_ROOT / "review-status.json")
    generated = tmp_path / "data.js"
    write_review_data(_cases(), status, generated)
    assert generated.read_bytes() == (APP_ROOT / "data.js").read_bytes()


def test_review_app_is_backend_free_and_locked_down() -> None:
    html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
    script = (APP_ROOT / "app.js").read_text(encoding="utf-8")
    assert "connect-src 'none'" in html
    assert "form-action 'none'" in html
    assert "analytics" in html
    assert "fetch(" not in script
    assert "XMLHttpRequest" not in script
    assert "sendBeacon" not in script
    assert "localStorage" in script
    assert "dataset_sha256" in script
