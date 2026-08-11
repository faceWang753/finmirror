"""Positive semantic-equivalence assurance and artifact contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from finmirror.cli import main
from finmirror.equivalence import run_equivalence_assurance
from finmirror.generator import generate_benchmark

EXPECTED_COUNTS = {
    "citation_permutation": 108,
    "citation_idempotence": 108,
    "operand_permutation": 108,
    "answer_surrounding_whitespace": 108,
    "numeric_string_encoding": 108,
    "answer_unit_case": 126,
    "operand_unit_case": 108,
    "retrieval_idempotence": 126,
    "missing_requirement_idempotence": 18,
    "irrelevant_telemetry": 126,
}


@pytest.fixture(scope="module")
def equivalence_report(cases):
    return run_equivalence_assurance(cases)


def test_equivalence_matrix_passes_with_nontrivial_control(equivalence_report) -> None:
    assert equivalence_report["passed"] is True
    assert equivalence_report["relation_count"] == 10
    assert equivalence_report["passed_count"] == 10
    assert equivalence_report["semantic_assertion_count"] == 3426
    assert equivalence_report["baseline"] == {
        "name": "evidence-program",
        "version": "0.1",
        "uses_gold": False,
    }
    assert equivalence_report["negative_control"] == {
        "name": "raw-contract-equality",
        "deliberately_brittle": True,
        "rejected_relation_count": 10,
        "rejection_rate": 1.0,
        "purpose": (
            "Prove each transformation is non-trivial and that byte/sequence equality "
            "would falsely reject legitimate representations."
        ),
    }


@pytest.mark.parametrize("relation_id", sorted(EXPECTED_COUNTS))
def test_each_relation_preserves_all_declared_verdicts(equivalence_report, relation_id) -> None:
    row = next(
        item for item in equivalence_report["relations"] if item["relation_id"] == relation_id
    )
    assert row["eligible_case_count"] == EXPECTED_COUNTS[relation_id]
    assert row["changed_case_count"] == row["eligible_case_count"]
    assert row["case_score_preserved_count"] == row["eligible_case_count"]
    assert row["semantic_key_preserved_count"] == row["eligible_case_count"]
    assert row["pair_result_preserved_count"] == row["affected_pair_count"]
    assert row["parallel_result_preserved_count"] == row["affected_parallel_group_count"]
    assert row["raw_equality_rejection_count"] == row["eligible_case_count"]
    assert all(row["checks"].values())
    assert row["passed"] is True


def test_equivalence_report_is_byte_reproducible(cases) -> None:
    assert run_equivalence_assurance(cases) == run_equivalence_assurance(cases)


def test_equivalence_cli_writes_public_artifacts(tmp_path, capsys) -> None:
    dataset = tmp_path / "benchmark"
    output = tmp_path / "equivalence"
    generate_benchmark(dataset)
    status = main(
        [
            "assure-equivalence",
            "--dataset",
            str(dataset),
            "--out",
            str(output),
        ]
    )
    captured = capsys.readouterr()
    assert status == 0
    assert "PASS · 10/10 equivalence relations preserved · 3426 assertions" in captured.out
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    page = (output / "index.html").read_text(encoding="utf-8")
    assert report["passed"] is True
    assert "Equivalent inputs" in page
    assert "Deliberately brittle control" in page


def test_equivalence_schema_matches_runtime_artifact(equivalence_report) -> None:
    project_root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (project_root / "schema" / "equivalence-assurance.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(schema["required"]) == set(equivalence_report)
    assert schema["additionalProperties"] is False
    relation_schema = schema["$defs"]["relation"]
    assert set(relation_schema["required"]) == set(equivalence_report["relations"][0])
    assert relation_schema["additionalProperties"] is False
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(equivalence_report)
