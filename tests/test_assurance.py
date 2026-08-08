"""One-field evaluator mutation assurance and artifact contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finmirror.assurance import run_evaluator_assurance
from finmirror.cli import main
from finmirror.generator import generate_benchmark


@pytest.fixture(scope="module")
def assurance_report(cases):
    return run_evaluator_assurance(cases)


EXPECTED_MUTATIONS = {
    "answer_value": (
        ["invalid_formula_replay", "wrong_answer"],
        ["answer_pass", "formula_pass"],
    ),
    "answer_unit": (["wrong_unit"], ["answer_pass"]),
    "citation_removed": (["insufficient_evidence"], ["evidence_pass"]),
    "citation_added": (["insufficient_evidence"], ["evidence_pass"]),
    "citation_wrong_world": (["insufficient_evidence"], ["evidence_pass"]),
    "formula_id": (["invalid_formula_replay"], ["formula_pass"]),
    "operand_value": (
        ["incorrect_operand_provenance", "invalid_formula_replay"],
        ["formula_pass"],
    ),
    "operand_semantic_name": (
        ["incorrect_operand_provenance", "invalid_formula_replay"],
        ["formula_pass"],
    ),
    "operand_unit": (
        ["incorrect_operand_provenance", "invalid_formula_replay"],
        ["formula_pass"],
    ),
    "operand_evidence": (
        ["incorrect_operand_provenance", "invalid_formula_replay"],
        ["formula_pass"],
    ),
    "confidence_invariant_drift": ([], ["confidence_pass"]),
    "abstention_flag": (["failed_to_abstain"], ["answer_pass"]),
    "missing_evidence": (["missing_requirement_not_identified"], ["formula_pass"]),
    "reported_retrieval_ids": (["missed_required_document"], ["retrieval_pass"]),
    "cross_language_semantic_value": ([], []),
}


def test_assurance_matrix_passes_without_gold_or_network(assurance_report) -> None:
    assert assurance_report["passed"] is True
    assert assurance_report["mutation_count"] == 15
    assert assurance_report["passed_count"] == 15
    assert assurance_report["baseline"] == {
        "name": "evidence-program",
        "version": "0.1",
        "uses_gold": False,
    }
    assert {row["mutation_id"] for row in assurance_report["mutations"]} == set(
        EXPECTED_MUTATIONS
    )


@pytest.mark.parametrize(
    ("mutation_id", "expected_case_failures", "expected_pair_failures"),
    [
        (mutation_id, case_failures, pair_failures)
        for mutation_id, (case_failures, pair_failures) in EXPECTED_MUTATIONS.items()
    ],
)
def test_each_mutation_has_exact_local_failure_attribution(
    assurance_report,
    mutation_id,
    expected_case_failures,
    expected_pair_failures,
) -> None:
    rows = {row["mutation_id"]: row for row in assurance_report["mutations"]}
    row = rows[mutation_id]
    assert row["observed_case_failures"] == expected_case_failures
    assert row["observed_pair_failures"] == expected_pair_failures
    assert row["pair_gate_before"] is True
    assert row["pair_gate_after"] is (not bool(expected_pair_failures))
    assert all(row["checks"].values())
    assert row["passed"] is True


def test_within_tolerance_language_mutation_is_isolated(assurance_report) -> None:
    row = next(
        item
        for item in assurance_report["mutations"]
        if item["mutation_id"] == "cross_language_semantic_value"
    )
    assert row["case_metric_changes"] == {}
    assert row["observed_case_failures"] == []
    assert row["observed_pair_failures"] == []
    assert row["pair_gate_after"] is True
    assert row["cross_language_before"] == 1.0
    assert row["cross_language_after"] == 0.0


def test_assurance_report_is_byte_reproducible(cases) -> None:
    assert run_evaluator_assurance(cases) == run_evaluator_assurance(cases)


def test_assurance_cli_writes_machine_readable_artifact(tmp_path, capsys) -> None:
    dataset = tmp_path / "benchmark"
    output = tmp_path / "assurance.json"
    generate_benchmark(dataset)
    status = main(
        [
            "assure-evaluator",
            "--dataset",
            str(dataset),
            "--out",
            str(output),
        ]
    )
    captured = capsys.readouterr()
    assert status == 0
    assert "PASS · 15/15 one-field mutations detected" in captured.out
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["mutation_count"] == 15


def test_assurance_schema_matches_runtime_artifact(assurance_report) -> None:
    project_root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (project_root / "schema" / "evaluator-assurance.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(schema["required"]) == set(assurance_report)
    assert schema["additionalProperties"] is False
    mutation_schema = schema["$defs"]["mutation"]
    assert set(mutation_schema["required"]) == set(assurance_report["mutations"][0])
    assert mutation_schema["additionalProperties"] is False
