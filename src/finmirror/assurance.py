"""Deterministic one-field mutation assurance for the public evaluator contract."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Literal

from finmirror.adapters.base import run_adapter
from finmirror.adapters.baselines import EvidenceProgramBaseline
from finmirror.dataset import dataset_digest
from finmirror.models import BenchmarkCase, CaseResult, PairResult, Prediction
from finmirror.scoring import score_case, score_pair, semantic_prediction_key

ASSURANCE_SCHEMA_VERSION = "1.0"
_PAIR_COMPONENTS = (
    "answer_pass",
    "evidence_pass",
    "formula_pass",
    "confidence_pass",
    "retrieval_pass",
)
_CASE_COMPONENTS = (
    "correct",
    "answer_score",
    "unit_score",
    "citation_precision",
    "citation_recall",
    "citation_f1",
    "retrieval_recall",
    "formula_score",
    "operand_score",
    "clarification_score",
    "abstention_score",
    "contract_score",
    "brier",
)
Direction = Literal["decrease", "increase", "true_to_false"]


@dataclass(frozen=True)
class _Mutation:
    mutation_id: str
    field_path: str
    target_case: BenchmarkCase
    apply: Callable[[Prediction], Prediction]
    expected_case_failures: tuple[str, ...]
    expected_case_changes: dict[str, Direction]
    expected_pair_failures: tuple[str, ...]
    expect_cross_language_failure: bool = False


def _find_case(
    cases: list[BenchmarkCase],
    *,
    scenario: str,
    language: str,
    transform: str,
) -> BenchmarkCase:
    matches = [
        case
        for case in cases
        if case.scenario_id == scenario
        and case.language == language
        and case.relationship.transform == transform
    ]
    if len(matches) != 1:
        raise ValueError(
            "Evaluator assurance requires exactly one "
            f"{scenario}/{language}/{transform} case; found {len(matches)}"
        )
    return matches[0]


def _replace_first_operand(
    prediction: Prediction,
    *,
    name: str | None = None,
    value: float | None = None,
    unit: str | None = None,
    evidence: str | None = None,
) -> Prediction:
    if not prediction.operands:
        raise ValueError(f"{prediction.case_id}: mutation target has no operands")
    original = prediction.operands[0]
    operand = replace(
        original,
        name=original.name if name is None else name,
        value=original.value if value is None else value,
        unit=original.unit if unit is None else unit,
        evidence=original.evidence if evidence is None else evidence,
    )
    return replace(prediction, operands=(operand, *prediction.operands[1:]))


def _numeric_value(prediction: Prediction) -> float:
    if not isinstance(prediction.value, (int, float)):
        raise ValueError(f"{prediction.case_id}: mutation target must have a numeric value")
    return float(prediction.value)


def _mutation_definitions(
    cases: list[BenchmarkCase],
    baseline: dict[str, Prediction],
) -> tuple[_Mutation, ...]:
    material = _find_case(
        cases,
        scenario="revenue_growth",
        language="en",
        transform="material_value",
    )
    reference = _find_case(
        cases,
        scenario="revenue_growth",
        language="en",
        transform="reference",
    )
    invariant = _find_case(
        cases,
        scenario="revenue_growth",
        language="en",
        transform="distractor",
    )
    ablation = _find_case(
        cases,
        scenario="revenue_growth",
        language="en",
        transform="evidence_ablation",
    )
    multilingual = _find_case(
        cases,
        scenario="revenue_growth",
        language="zh",
        transform="material_value",
    )
    wrong_world_citations = baseline[reference.case_id].citations
    multilingual_delta = multilingual.expected.tolerance / 2

    return (
        _Mutation(
            "answer_value",
            "value",
            material,
            lambda item: replace(item, value=_numeric_value(item) + 1.0),
            ("invalid_formula_replay", "wrong_answer"),
            {
                "answer_score": "decrease",
                "formula_score": "decrease",
                "correct": "true_to_false",
                "brier": "increase",
            },
            ("answer_pass", "formula_pass"),
            expect_cross_language_failure=True,
        ),
        _Mutation(
            "answer_unit",
            "unit",
            material,
            lambda item: replace(item, unit="basis_points"),
            ("wrong_unit",),
            {
                "unit_score": "decrease",
                "correct": "true_to_false",
                "brier": "increase",
            },
            ("answer_pass",),
            expect_cross_language_failure=True,
        ),
        _Mutation(
            "citation_removed",
            "citations",
            material,
            lambda item: replace(item, citations=item.citations[:-1]),
            ("insufficient_evidence",),
            {"citation_recall": "decrease", "citation_f1": "decrease"},
            ("evidence_pass",),
        ),
        _Mutation(
            "citation_added",
            "citations",
            material,
            lambda item: replace(
                item,
                citations=(*item.citations, "doc:assurance-unrelated#E9"),
            ),
            ("insufficient_evidence",),
            {"citation_precision": "decrease", "citation_f1": "decrease"},
            ("evidence_pass",),
        ),
        _Mutation(
            "citation_wrong_world",
            "citations",
            material,
            lambda item: replace(item, citations=wrong_world_citations),
            ("insufficient_evidence",),
            {
                "citation_precision": "decrease",
                "citation_recall": "decrease",
                "citation_f1": "decrease",
            },
            ("evidence_pass",),
        ),
        _Mutation(
            "formula_id",
            "formula_id",
            material,
            lambda item: replace(item, formula_id="gross_margin"),
            ("invalid_formula_replay",),
            {"formula_score": "decrease"},
            ("formula_pass",),
        ),
        _Mutation(
            "operand_value",
            "operands[0].value",
            material,
            lambda item: _replace_first_operand(
                item,
                value=item.operands[0].value + 1.0,
            ),
            ("incorrect_operand_provenance", "invalid_formula_replay"),
            {"formula_score": "decrease", "operand_score": "decrease"},
            ("formula_pass",),
        ),
        _Mutation(
            "operand_semantic_name",
            "operands[0].name",
            material,
            lambda item: _replace_first_operand(item, name="wrong_type"),
            ("incorrect_operand_provenance", "invalid_formula_replay"),
            {"formula_score": "decrease", "operand_score": "decrease"},
            ("formula_pass",),
        ),
        _Mutation(
            "operand_unit",
            "operands[0].unit",
            material,
            lambda item: _replace_first_operand(item, unit="ratio"),
            ("incorrect_operand_provenance", "invalid_formula_replay"),
            {"formula_score": "decrease", "operand_score": "decrease"},
            ("formula_pass",),
        ),
        _Mutation(
            "operand_evidence",
            "operands[0].evidence",
            material,
            lambda item: _replace_first_operand(
                item,
                evidence="doc:assurance-unrelated#E9",
            ),
            ("incorrect_operand_provenance", "invalid_formula_replay"),
            {"formula_score": "decrease", "operand_score": "decrease"},
            ("formula_pass",),
        ),
        _Mutation(
            "confidence_invariant_drift",
            "confidence",
            invariant,
            lambda item: replace(item, confidence=0.70),
            (),
            {"brier": "increase"},
            ("confidence_pass",),
        ),
        _Mutation(
            "abstention_flag",
            "abstained",
            ablation,
            lambda item: replace(item, abstained=False),
            ("failed_to_abstain",),
            {
                "answer_score": "decrease",
                "unit_score": "decrease",
                "abstention_score": "decrease",
                "correct": "true_to_false",
            },
            ("answer_pass",),
            expect_cross_language_failure=True,
        ),
        _Mutation(
            "missing_evidence",
            "missing_evidence",
            ablation,
            lambda item: replace(item, missing_evidence=()),
            ("missing_requirement_not_identified",),
            {"clarification_score": "decrease"},
            ("formula_pass",),
        ),
        _Mutation(
            "reported_retrieval_ids",
            "retrieved_document_ids",
            material,
            lambda item: replace(item, retrieved_document_ids=("doc:assurance-miss",)),
            ("missed_required_document",),
            {"retrieval_recall": "decrease"},
            ("retrieval_pass",),
        ),
        _Mutation(
            "cross_language_semantic_value",
            "value",
            multilingual,
            lambda item: replace(item, value=_numeric_value(item) + multilingual_delta),
            (),
            {},
            (),
            expect_cross_language_failure=True,
        ),
    )


def _case_value(result: CaseResult, name: str) -> float | bool | None:
    value = getattr(result, name)
    if value is not None and not isinstance(value, (bool, int, float)):
        raise TypeError(f"Unsupported assurance metric {name}: {type(value).__name__}")
    return value


def _changed_field_paths(before: Prediction, after: Prediction) -> tuple[str, ...]:
    """Return changed contract leaf fields without exposing payload contents."""

    before_data = before.to_dict()
    after_data = after.to_dict()
    changed: list[str] = []
    for name in before_data:
        if name != "operands":
            if before_data[name] != after_data[name]:
                changed.append(name)
            continue
        before_operands = before.operands
        after_operands = after.operands
        if len(before_operands) != len(after_operands):
            changed.append("operands")
            continue
        for index, (left, right) in enumerate(
            zip(before_operands, after_operands, strict=True)
        ):
            for field_name in ("name", "value", "unit", "evidence"):
                if getattr(left, field_name) != getattr(right, field_name):
                    changed.append(f"operands[{index}].{field_name}")
    return tuple(changed)


def _change_matches(
    before: float | bool | None, after: float | bool | None, direction: Direction
) -> bool:
    if direction == "true_to_false":
        return before is True and after is False
    if before is None or after is None:
        return False
    if direction == "decrease":
        return float(after) < float(before)
    return float(after) > float(before)


def _pair_failure_components(result: PairResult) -> tuple[str, ...]:
    return tuple(name for name in _PAIR_COMPONENTS if getattr(result, name) is False)


def _score_target_pair(
    cases_by_id: dict[str, BenchmarkCase],
    predictions: dict[str, Prediction],
    target: BenchmarkCase,
) -> PairResult:
    reference_id = target.relationship.reference_case_id
    if reference_id is None:
        raise ValueError(f"{target.case_id}: assurance target must be a transformed case")
    reference_case = cases_by_id[reference_id]
    reference_prediction = predictions[reference_id]
    target_prediction = predictions[target.case_id]
    return score_pair(
        reference_case,
        target,
        reference_prediction,
        target_prediction,
        score_case(reference_case, reference_prediction),
        score_case(target, target_prediction),
    )


def _parallel_consistency(
    cases: list[BenchmarkCase],
    predictions: dict[str, Prediction],
    target: BenchmarkCase,
) -> float:
    members = [case for case in cases if case.parallel_id == target.parallel_id]
    results = [score_case(case, predictions[case.case_id]) for case in members]
    keys = {semantic_prediction_key(case, predictions[case.case_id]) for case in members}
    return 1.0 if all(result.correct for result in results) and len(keys) == 1 else 0.0


def _mutation_result(
    mutation: _Mutation,
    *,
    cases: list[BenchmarkCase],
    cases_by_id: dict[str, BenchmarkCase],
    baseline: dict[str, Prediction],
) -> dict[str, Any]:
    mutated = dict(baseline)
    target_id = mutation.target_case.case_id
    mutated[target_id] = mutation.apply(baseline[target_id])

    before_case = score_case(mutation.target_case, baseline[target_id])
    after_case = score_case(mutation.target_case, mutated[target_id])
    observed_case_failures = tuple(sorted(after_case.failure_labels))
    expected_case_failures = tuple(sorted(mutation.expected_case_failures))

    case_changes: dict[str, dict[str, Any]] = {}
    case_change_checks: list[bool] = []
    for metric, direction in mutation.expected_case_changes.items():
        before = _case_value(before_case, metric)
        after = _case_value(after_case, metric)
        matched = _change_matches(before, after, direction)
        case_change_checks.append(matched)
        case_changes[metric] = {
            "before": before,
            "after": after,
            "expected_direction": direction,
            "matched": matched,
        }
    observed_case_metric_changes = tuple(
        name
        for name in _CASE_COMPONENTS
        if _case_value(before_case, name) != _case_value(after_case, name)
    )
    expected_case_metric_changes = tuple(
        name for name in _CASE_COMPONENTS if name in mutation.expected_case_changes
    )

    before_pair = _score_target_pair(cases_by_id, baseline, mutation.target_case)
    after_pair = _score_target_pair(cases_by_id, mutated, mutation.target_case)
    observed_pair_failures = _pair_failure_components(after_pair)

    before_parallel = _parallel_consistency(cases, baseline, mutation.target_case)
    after_parallel = _parallel_consistency(cases, mutated, mutation.target_case)
    cross_language_detected = before_parallel == 1.0 and after_parallel == 0.0
    expected_cross_language = mutation.expect_cross_language_failure

    checks = {
        "one_declared_field_changed": _changed_field_paths(
            baseline[target_id], mutated[target_id]
        )
        == (mutation.field_path,),
        "case_failures_exact": observed_case_failures == expected_case_failures,
        "case_metric_changes_match": all(case_change_checks),
        "unrelated_case_metrics_unchanged": (
            observed_case_metric_changes == expected_case_metric_changes
        ),
        "pair_failures_exact": observed_pair_failures == mutation.expected_pair_failures,
        "pair_gate_before_passed": before_pair.passed,
        "pair_gate_after_expected": after_pair.passed
        == (not bool(mutation.expected_pair_failures)),
        "cross_language_expected": cross_language_detected == expected_cross_language,
    }
    return {
        "mutation_id": mutation.mutation_id,
        "target_case_id": target_id,
        "field_path": mutation.field_path,
        "expected_case_failures": list(expected_case_failures),
        "observed_case_failures": list(observed_case_failures),
        "case_metric_changes": case_changes,
        "observed_case_metric_changes": list(observed_case_metric_changes),
        "expected_pair_failures": list(mutation.expected_pair_failures),
        "observed_pair_failures": list(observed_pair_failures),
        "pair_gate_before": before_pair.passed,
        "pair_gate_after": after_pair.passed,
        "cross_language_before": before_parallel,
        "cross_language_after": after_parallel,
        "checks": checks,
        "passed": all(checks.values()),
    }


def run_evaluator_assurance(cases: list[BenchmarkCase]) -> dict[str, Any]:
    """Run the fixed v0.1 one-field mutation matrix with no network or LLM judge."""

    cases_by_id = {case.case_id: case for case in cases}
    predictions = run_adapter(EvidenceProgramBaseline(), cases)
    baseline = {prediction.case_id: prediction for prediction in predictions}
    if set(baseline) != set(cases_by_id):
        raise ValueError(
            "Evidence-program baseline did not emit exactly one prediction per case"
        )

    baseline_failures = {
        case.case_id: list(score_case(case, baseline[case.case_id]).failure_labels)
        for case in cases
        if score_case(case, baseline[case.case_id]).failure_labels
    }
    if baseline_failures:
        raise ValueError(f"Evidence-program baseline is not clean: {baseline_failures}")

    mutations = [
        _mutation_result(
            mutation,
            cases=cases,
            cases_by_id=cases_by_id,
            baseline=baseline,
        )
        for mutation in _mutation_definitions(cases, baseline)
    ]
    passed_count = sum(bool(item["passed"]) for item in mutations)
    return {
        "assurance_schema_version": ASSURANCE_SCHEMA_VERSION,
        "dataset_sha256": dataset_digest(cases),
        "baseline": {
            "name": EvidenceProgramBaseline.name,
            "version": EvidenceProgramBaseline.version,
            "uses_gold": False,
        },
        "method": "one-field-at-a-time deterministic mutation assurance",
        "mutation_count": len(mutations),
        "passed_count": passed_count,
        "passed": passed_count == len(mutations),
        "mutations": mutations,
        "claim_boundary": (
            "Passing provides inspectable regression evidence for declared mutations; "
            "it is not formal verification or proof that the evaluator is correct."
        ),
    }
