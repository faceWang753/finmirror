"""Dataset serialization, integrity, and fail-closed validation tests."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from finmirror.dataset import (
    canonical_json,
    dataset_digest,
    load_cases,
    save_cases,
    validate_cases,
    write_manifest,
)
from finmirror.generator import generate_benchmark


def test_round_trip_manifest_and_digest(tmp_path, cases) -> None:
    dataset_dir = tmp_path / "benchmark"
    save_cases(reversed(cases), dataset_dir)
    manifest_path = write_manifest(
        cases,
        dataset_dir,
        name="test",
        version="0",
        description="test fixture",
    )

    loaded = load_cases(dataset_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(loaded) == 126
    assert manifest["case_count"] == 126
    assert manifest["pair_group_count"] == 18
    assert manifest["dataset_sha256"] == dataset_digest(cases)
    assert dataset_digest(loaded) == dataset_digest(cases)
    assert len(manifest["dataset_sha256"]) == 64


def test_save_is_canonical_and_order_independent(tmp_path, cases) -> None:
    first = save_cases(cases, tmp_path / "first")
    second = save_cases(reversed(cases), tmp_path / "second")
    assert first.read_bytes() == second.read_bytes()
    assert first.read_text(encoding="utf-8").endswith("\n")


def test_case_tampering_is_rejected_by_manifest(tmp_path) -> None:
    dataset_dir = tmp_path / "benchmark"
    generate_benchmark(dataset_dir)
    cases_path = dataset_dir / "cases.jsonl"
    rows = [
        json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line
    ]
    rows[0]["question"] += " tampered"
    cases_path.write_text(
        "\n".join(canonical_json(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Dataset integrity check failed"):
        load_cases(dataset_dir)
    assert load_cases(dataset_dir, verify_manifest=False)[0].question.endswith("tampered")


def test_manifest_count_tampering_is_rejected(tmp_path) -> None:
    dataset_dir = tmp_path / "benchmark"
    generate_benchmark(dataset_dir)
    manifest_path = dataset_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["case_count"] = 125
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="case_count"):
        load_cases(dataset_dir)


def test_duplicate_case_ids_are_rejected(cases) -> None:
    with pytest.raises(ValueError, match="Duplicate case IDs"):
        validate_cases([*cases, cases[0]])


def test_missing_required_anchor_is_rejected(cases) -> None:
    reference = next(case for case in cases if case.relationship.expectation == "reference")
    invalid = replace(
        reference,
        expected=replace(reference.expected, required_evidence=("missing-doc#E9",)),
    )
    altered = [invalid if case.case_id == reference.case_id else case for case in cases]
    with pytest.raises(ValueError, match="required evidence is absent"):
        validate_cases(altered)


def test_unknown_pair_reference_is_rejected(cases) -> None:
    transformed = next(case for case in cases if case.relationship.expectation != "reference")
    invalid = replace(
        transformed,
        relationship=replace(
            transformed.relationship,
            reference_case_id="fm-does-not-exist",
        ),
    )
    altered = [invalid if case.case_id == transformed.case_id else case for case in cases]
    with pytest.raises(ValueError, match="unknown reference"):
        validate_cases(altered)


def test_invalid_json_reports_the_source_line(tmp_path) -> None:
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text('{"case_id": "ok"}\n{not-json}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"cases\.jsonl:1"):
        load_cases(cases_path, verify_manifest=False)


def test_canonical_json_is_stable_and_unicode_preserving() -> None:
    left = {"z": 1, "中文": "证据", "nested": {"b": 2, "a": 1}}
    right = {"nested": {"a": 1, "b": 2}, "中文": "证据", "z": 1}
    assert canonical_json(left) == canonical_json(right)
    assert "证据" in canonical_json(left)
