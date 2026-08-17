from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import build_anonymous_supplement as supplement


def write_receipt(stage: Path, byte_count: int) -> None:
    baseline = stage / "artifacts" / "model-baselines" / "qwen-test"
    baseline.mkdir(parents=True)
    (baseline / "model-receipt.json").write_text(
        json.dumps({"model": {"bytes": byte_count}}), encoding="utf-8"
    )
    (baseline / "RUN.md").write_text(
        f"Exact model file size: `{byte_count}` bytes.\n", encoding="utf-8"
    )


def test_scan_allows_exact_declared_model_byte_token(tmp_path: Path) -> None:
    write_receipt(tmp_path, 2_497_280_256)

    result = supplement.scan(tmp_path)

    assert result["phone_or_sin_hits"] == 0


def test_scan_rejects_another_ten_digit_number(tmp_path: Path) -> None:
    write_receipt(tmp_path, 2_497_280_256)
    baseline = tmp_path / "artifacts" / "model-baselines" / "qwen-test"
    (baseline / "notes.md").write_text("Unexpected token: 3658836277\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match=r"phone/SIN-like PII:.*notes\.md"):
        supplement.scan(tmp_path)


def test_scan_does_not_exempt_declared_bytes_outside_baseline(tmp_path: Path) -> None:
    write_receipt(tmp_path, 2_497_280_256)
    (tmp_path / "README.md").write_text(
        "The same token outside its receipt bundle: 2497280256\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match=r"phone/SIN-like PII: README\.md"):
        supplement.scan(tmp_path)
