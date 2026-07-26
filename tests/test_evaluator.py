"""End-to-end aggregation tests for the two transparent offline baselines."""

from __future__ import annotations

from dataclasses import replace

import pytest

from finmirror.evaluator import evaluate


def test_oracle_validates_the_complete_harness(oracle_report) -> None:
    assert oracle_report["report_schema_version"] == "1.1"
    assert oracle_report["dataset"]["case_count"] == 126
    assert oracle_report["dataset"]["pair_count"] == 108
    assert oracle_report["dataset"]["languages"] == ["en", "fr", "zh"]
    metrics = oracle_report["metrics"]
    for key in (
        "case_accuracy",
        "unit_accuracy",
        "citation_f1",
        "formula_replay",
        "operand_provenance",
        "missing_evidence_identification",
        "abstention_accuracy",
        "pair_reliability",
        "pair_answer_behavior",
        "citation_migration",
        "formula_behavior",
        "confidence_behavior",
        "retrieval_behavior",
        "material_sensitivity",
        "distractor_invariance",
        "evidence_ablation",
        "cross_language_consistency",
        "contract_validity",
        "change_precision",
        "change_recall",
        "change_f1",
    ):
        assert metrics[key] == pytest.approx(1.0), key
    assert metrics["hard_gate_pass"] is True
    assert metrics["audit_score"] >= 99.99
    assert metrics["brier_score"] == pytest.approx(0.0001)
    assert oracle_report["failure_counts"] == {}
    assert len(oracle_report["cases"]) == 126
    assert len(oracle_report["pairs"]) == 108
    assert all(
        values == {"count": 18, "pass_rate": 1.0}
        for values in oracle_report["by_transform"].values()
    )


def test_non_gold_evidence_program_satisfies_full_contract(
    evidence_program_report,
) -> None:
    metrics = evidence_program_report["metrics"]
    assert evidence_program_report["run_metadata"]["uses_gold"] is False
    assert metrics["hard_gate_pass"] is True
    assert metrics["case_accuracy"] == 1.0
    assert metrics["pair_reliability"] == 1.0
    assert metrics["formula_replay"] == 1.0
    assert metrics["operand_provenance"] == 1.0
    assert metrics["missing_evidence_identification"] == 1.0
    assert metrics["audit_score"] >= 99.99
    assert evidence_program_report["failure_counts"] == {}


def test_memorized_baseline_exposes_hidden_failures(memorized_report) -> None:
    metrics = memorized_report["metrics"]
    assert metrics["hard_gate_pass"] is False
    assert metrics["case_accuracy"] == pytest.approx(5 / 7)
    assert metrics["pair_reliability"] == 0.0
    assert metrics["pair_answer_behavior"] == pytest.approx(2 / 3)
    assert metrics["formula_replay"] == 0.0
    assert metrics["operand_provenance"] == 0.0
    assert metrics["missing_evidence_identification"] == 0.0
    assert metrics["material_sensitivity"] == 0.0
    assert metrics["distractor_invariance"] == 0.0
    assert metrics["evidence_ablation"] == 0.0
    assert memorized_report["by_transform"]["entity_collision"]["pass_rate"] == 0.0
    assert memorized_report["failure_counts"] == {
        "failed_to_abstain": 18,
        "incorrect_operand_provenance": 108,
        "insufficient_evidence": 18,
        "invalid_formula_replay": 108,
        "missing_requirement_not_identified": 18,
        "wrong_answer": 18,
    }


def test_every_memorized_material_ablation_and_entity_pair_fails(
    memorized_report,
) -> None:
    exposed = {"material_value", "evidence_ablation", "entity_collision"}
    relevant = [pair for pair in memorized_report["pairs"] if pair["transform"] in exposed]
    assert len(relevant) == 54
    assert all(not pair["passed"] for pair in relevant)


def test_evaluate_rejects_duplicate_predictions(cases, oracle_predictions) -> None:
    with pytest.raises(ValueError, match="Duplicate prediction"):
        evaluate(
            cases,
            [*oracle_predictions, oracle_predictions[0]],
            system_name="duplicate",
        )


def test_evaluate_rejects_missing_predictions(cases, oracle_predictions) -> None:
    with pytest.raises(ValueError, match="Missing predictions"):
        evaluate(cases, oracle_predictions[:-1], system_name="missing")


def test_evaluate_rejects_unknown_predictions(cases, oracle_predictions) -> None:
    unknown = replace(oracle_predictions[0], case_id="unknown-case")
    with pytest.raises(ValueError, match="Unknown prediction"):
        evaluate(cases, [*oracle_predictions, unknown], system_name="unknown")


def test_run_metadata_is_preserved(cases, oracle_predictions) -> None:
    metadata = {"commit": "abc123", "offline": True}
    report = evaluate(
        cases,
        oracle_predictions,
        system_name="oracle",
        system_version="test",
        run_metadata=metadata,
    )
    assert report["run_metadata"] == metadata
