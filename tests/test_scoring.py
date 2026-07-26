"""Unit tests for exact financial, evidence, pair, and calibration metrics."""

from __future__ import annotations

from dataclasses import replace

import pytest

from finmirror.adapters.baselines import OracleAdapter
from finmirror.models import CalculationOperand
from finmirror.scoring import (
    citation_scores,
    execute_formula,
    expected_calibration_error,
    normalize_number,
    prediction_changed,
    score_case,
    score_pair,
)


def _case(cases, *, scenario: str = "revenue_growth", language: str = "en", transform: str):
    return next(
        case
        for case in cases
        if case.scenario_id == scenario
        and case.language == language
        and case.relationship.transform == transform
    )


def _oracle_pair(cases, transform: str):
    reference = _case(cases, transform="reference")
    transformed = _case(cases, transform=transform)
    oracle = OracleAdapter(cases)
    reference_prediction = oracle.generate(reference.prompt_case())
    transformed_prediction = oracle.generate(transformed.prompt_case())
    reference_result = score_case(reference, reference_prediction)
    transformed_result = score_case(transformed, transformed_prediction)
    pair = score_pair(
        reference,
        transformed,
        reference_prediction,
        transformed_prediction,
        reference_result,
        transformed_result,
    )
    return reference, transformed, reference_prediction, transformed_prediction, pair


@pytest.mark.parametrize(
    ("value", "answer", "expected"),
    [
        (12, "", 12.0),
        ("1,234.50", "", 1234.5),
        (None, "(42.25)", -42.25),
        (None, "-7.5%", -7.5),
        (None, "about 3.20x", 3.2),
        (float("nan"), "", None),
        (None, "no numeric answer", None),
    ],
)
def test_normalize_number(value, answer, expected) -> None:
    assert normalize_number(value, answer) == expected


def test_citation_scores_use_sets_and_handle_abstention() -> None:
    assert citation_scores(["a", "a", "x"], ["a", "b"]) == (0.5, 0.5, 0.5)
    assert citation_scores([], []) == (1.0, 1.0, 1.0)
    assert citation_scores(["hallucinated"], []) == (0.0, 1.0, 0.0)
    assert citation_scores([], ["required"]) == (0.0, 0.0, 0.0)


@pytest.mark.parametrize(
    ("formula_id", "names", "values", "expected"),
    [
        ("revenue_growth", ("prior", "current"), (480.0, 540.0), 12.5),
        ("gross_margin", ("revenue", "cost"), (800.0, 520.0), 35.0),
        ("debt_to_equity", ("debt", "equity"), (300.0, 500.0), 0.6),
        ("cash_runway", ("cash", "monthly_burn"), (120.0, 10.0), 12.0),
        ("covenant_headroom", ("maximum", "actual"), (4.0, 3.2), 0.8),
        ("free_cash_flow", ("operating_cash", "capex"), (190.0, 70.0), 120.0),
    ],
)
def test_allowlisted_financial_formula_programs(
    formula_id,
    names,
    values,
    expected,
) -> None:
    operands = [
        CalculationOperand(name=name, value=value, unit="u", evidence=f"doc#{index}")
        for index, (name, value) in enumerate(zip(names, values, strict=True), start=1)
    ]
    assert execute_formula(formula_id, operands) == pytest.approx(expected)


def test_formula_executor_fails_closed() -> None:
    valid = [
        CalculationOperand("debt", 300.0, "USD", "doc#E1"),
        CalculationOperand("equity", 500.0, "USD", "doc#E2"),
    ]
    assert execute_formula("__import__('os').system('echo unsafe')", valid) is None
    assert execute_formula("debt_to_equity", valid[:1]) is None
    assert (
        execute_formula(
            "debt_to_equity",
            [
                valid[0],
                CalculationOperand("equity", 0.0, "USD", "doc#E2"),
            ],
        )
        is None
    )
    assert execute_formula("debt_to_equity", [valid[0], valid[0]]) is None


def test_oracle_answer_and_abstention_cases_score_exactly(cases) -> None:
    oracle = OracleAdapter(cases)
    reference = _case(cases, transform="reference")
    answerable = score_case(reference, oracle.generate(reference.prompt_case()))
    assert answerable.correct
    assert answerable.answer_score == 1.0
    assert answerable.unit_score == 1.0
    assert answerable.citation_f1 == 1.0
    assert answerable.retrieval_recall == 1.0
    assert answerable.brier == pytest.approx(0.0001)

    ablation = _case(cases, transform="evidence_ablation")
    abstained = score_case(ablation, oracle.generate(ablation.prompt_case()))
    assert abstained.correct
    assert abstained.abstention_score == 1.0
    assert abstained.citation_f1 == 1.0
    assert abstained.retrieval_recall is None
    assert abstained.brier is None


def test_wrong_unit_retrieval_and_contract_are_labeled(cases) -> None:
    case = _case(cases, transform="reference")
    prediction = OracleAdapter(cases).generate(case.prompt_case())
    flawed = replace(
        prediction,
        unit="wrong-unit",
        confidence=1.2,
        retrieved_document_ids=("unrelated-document",),
    )
    result = score_case(case, flawed)
    assert not result.correct
    assert result.answer_score == 1.0
    assert result.unit_score == 0.0
    assert result.retrieval_recall == 0.0
    assert set(result.failure_labels) == {
        "invalid_contract",
        "wrong_unit",
        "missed_required_document",
    }


@pytest.mark.parametrize(
    "transform",
    [
        "material_value",
        "distractor",
        "entity_collision",
        "period_collision",
        "injection",
        "evidence_ablation",
    ],
)
def test_oracle_passes_every_pair_contract(cases, transform) -> None:
    _, _, _, _, pair = _oracle_pair(cases, transform)
    assert pair.passed
    assert pair.answer_pass
    assert pair.evidence_pass
    assert pair.formula_pass
    assert pair.confidence_pass
    assert pair.retrieval_pass is not False
    assert pair.score == 1.0


def test_material_answer_changes_but_distractor_answer_does_not(cases) -> None:
    reference, material, left, right, _ = _oracle_pair(cases, "material_value")
    assert prediction_changed(reference, material, left, right)

    reference, distractor, left, right, _ = _oracle_pair(cases, "distractor")
    assert not prediction_changed(reference, distractor, left, right)


def test_stale_material_citation_fails_pair_despite_correct_answer(cases) -> None:
    reference, transformed, left, right, _ = _oracle_pair(cases, "material_value")
    stale = replace(right, citations=left.citations)
    pair = score_pair(
        reference,
        transformed,
        left,
        stale,
        score_case(reference, left),
        score_case(transformed, stale),
    )
    assert pair.answer_pass
    assert not pair.evidence_pass
    assert pair.formula_pass
    assert not pair.citation_migrated
    assert not pair.passed
    assert "evidence migration" in pair.reason


def test_invariant_confidence_drift_fails_pair(cases) -> None:
    reference, transformed, left, right, _ = _oracle_pair(cases, "distractor")
    drifted = replace(right, confidence=0.50)
    pair = score_pair(
        reference,
        transformed,
        left,
        drifted,
        score_case(reference, left),
        score_case(transformed, drifted),
    )
    assert pair.answer_pass
    assert pair.evidence_pass
    assert pair.formula_pass
    assert not pair.confidence_pass
    assert pair.confidence_delta == pytest.approx(-0.49)
    assert not pair.passed


def test_high_confidence_abstention_fails_pair(cases) -> None:
    reference, transformed, left, right, _ = _oracle_pair(cases, "evidence_ablation")
    overconfident = replace(right, confidence=0.80)
    pair = score_pair(
        reference,
        transformed,
        left,
        overconfident,
        score_case(reference, left),
        score_case(transformed, overconfident),
    )
    assert pair.answer_pass
    assert pair.evidence_pass
    assert pair.formula_pass
    assert not pair.confidence_pass
    assert not pair.passed


def test_reported_retrieval_miss_is_a_hard_pair_failure(cases) -> None:
    reference, transformed, left, right, _ = _oracle_pair(cases, "material_value")
    missed = replace(right, retrieved_document_ids=("wrong-document",))
    pair = score_pair(
        reference,
        transformed,
        left,
        missed,
        score_case(reference, left),
        score_case(transformed, missed),
    )
    assert pair.answer_pass
    assert pair.evidence_pass
    assert pair.formula_pass
    assert pair.retrieval_pass is False
    assert not pair.passed


def test_expected_calibration_error_extremes() -> None:
    assert expected_calibration_error([], []) is None
    assert expected_calibration_error([0.0, 1.0], [0, 1]) == 0.0
    assert expected_calibration_error([1.0, 0.0], [0, 1]) == 1.0
