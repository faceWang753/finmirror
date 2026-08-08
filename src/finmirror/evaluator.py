"""Evaluation orchestration and aggregate behavioral diagnostics."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from finmirror.dataset import dataset_digest
from finmirror.models import BenchmarkCase, CaseResult, PairResult, Prediction
from finmirror.scoring import (
    expected_calibration_error,
    prediction_changed,
    score_case,
    score_pair,
    semantic_prediction_key,
)
from finmirror.uncertainty import clustered_bootstrap


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _behavior_change_metrics(
    cases_by_id: dict[str, BenchmarkCase],
    predictions: dict[str, Prediction],
) -> dict[str, float]:
    true_positive = false_positive = false_negative = 0
    for case in cases_by_id.values():
        if case.relationship.expectation == "reference":
            continue
        reference_id = case.relationship.reference_case_id
        if reference_id is None:
            continue
        reference_case = cases_by_id[reference_id]
        predicted_change = prediction_changed(
            reference_case,
            case,
            predictions[reference_id],
            predictions[case.case_id],
        )
        expected_change = case.relationship.expectation in {
            "should_change",
            "should_abstain",
        }
        if predicted_change and expected_change:
            true_positive += 1
        elif predicted_change and not expected_change:
            false_positive += 1
        elif not predicted_change and expected_change:
            false_negative += 1
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0.0
    )
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {
        "change_precision": precision,
        "change_recall": recall,
        "change_f1": f1,
    }


def evaluate(
    cases: list[BenchmarkCase],
    predictions: list[Prediction],
    *,
    system_name: str,
    system_version: str = "",
    run_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one prediction per case and return a JSON-serializable report."""

    cases_by_id = {case.case_id: case for case in cases}
    prediction_map: dict[str, Prediction] = {}
    for prediction in predictions:
        if prediction.case_id in prediction_map:
            raise ValueError(f"Duplicate prediction: {prediction.case_id}")
        prediction_map[prediction.case_id] = prediction
    missing = sorted(set(cases_by_id) - set(prediction_map))
    unknown = sorted(set(prediction_map) - set(cases_by_id))
    if missing:
        raise ValueError(f"Missing predictions for {len(missing)} cases: {missing[:5]}")
    if unknown:
        raise ValueError(f"Unknown prediction case IDs: {unknown[:5]}")

    case_results: dict[str, CaseResult] = {
        case_id: score_case(case, prediction_map[case_id])
        for case_id, case in cases_by_id.items()
    }
    pair_results: list[PairResult] = []
    for case in sorted(cases, key=lambda item: item.case_id):
        reference_id = case.relationship.reference_case_id
        if case.relationship.expectation == "reference" or reference_id is None:
            continue
        pair_results.append(
            score_pair(
                cases_by_id[reference_id],
                case,
                prediction_map[reference_id],
                prediction_map[case.case_id],
                case_results[reference_id],
                case_results[case.case_id],
            )
        )

    answerable_results = [
        case_results[case.case_id] for case in cases if not case.expected.abstain
    ]
    abstention_results = [case_results[case.case_id] for case in cases if case.expected.abstain]
    confidence_rows = [
        (prediction_map[case.case_id].confidence, int(case_results[case.case_id].correct))
        for case in cases
        if not case.expected.abstain
    ]
    confidences = [row[0] for row in confidence_rows]
    labels = [row[1] for row in confidence_rows]
    brier_values = [
        result.brier for result in case_results.values() if result.brier is not None
    ]
    brier = _mean([float(value) for value in brier_values])
    ece = expected_calibration_error(confidences, labels)

    pair_by_expectation: dict[str, list[PairResult]] = defaultdict(list)
    pair_by_transform: dict[str, list[PairResult]] = defaultdict(list)
    for result in pair_results:
        pair_by_expectation[result.expectation].append(result)
        pair_by_transform[result.transform].append(result)

    parallel: dict[str, list[BenchmarkCase]] = defaultdict(list)
    for case in cases:
        parallel[case.parallel_id].append(case)
    cross_language_scores: list[float] = []
    for members in parallel.values():
        if len({item.language for item in members}) < 2:
            continue
        keys = {
            semantic_prediction_key(member, prediction_map[member.case_id])
            for member in members
        }
        all_correct = all(case_results[member.case_id].correct for member in members)
        cross_language_scores.append(1.0 if all_correct and len(keys) == 1 else 0.0)

    accuracy = _mean([float(result.correct) for result in case_results.values()])
    pair_score = _mean([result.score for result in pair_results])
    pair_answer_behavior = _mean([float(result.answer_pass) for result in pair_results])
    citation_migration = _mean([float(result.evidence_pass) for result in pair_results])
    formula_behavior = _mean([float(result.formula_pass) for result in pair_results])
    confidence_behavior = _mean([float(result.confidence_pass) for result in pair_results])
    reported_retrieval = [
        float(result.retrieval_pass)
        for result in pair_results
        if result.retrieval_pass is not None
    ]
    retrieval_behavior = _mean(reported_retrieval) if reported_retrieval else None
    citation_f1 = _mean([result.citation_f1 for result in answerable_results])
    formula_replay = _mean([result.formula_score for result in answerable_results])
    operand_provenance = _mean([result.operand_score for result in answerable_results])
    clarification = _mean([result.clarification_score for result in abstention_results])
    abstention = _mean([result.abstention_score for result in abstention_results])
    unit_accuracy = _mean([result.unit_score for result in answerable_results])
    contract = _mean([result.contract_score for result in case_results.values()])
    cross_language = _mean(cross_language_scores)
    calibration_score = max(0.0, 1.0 - brier)
    verified_cases = {
        case_id: (
            case_result.correct
            and case_result.citation_f1 == 1.0
            and case_result.formula_score == 1.0
            and case_result.clarification_score == 1.0
            and (case_result.retrieval_recall is None or case_result.retrieval_recall == 1.0)
        )
        for case_id, case_result in case_results.items()
    }
    case_verification = _mean([float(value) for value in verified_cases.values()])

    audit_score = 100 * (
        0.30 * accuracy
        + 0.25 * pair_score
        + 0.15 * citation_f1
        + 0.10 * abstention
        + 0.10 * calibration_score
        + 0.10 * cross_language
    )
    hard_gate_pass = (
        accuracy >= 0.80
        and pair_score >= 0.75
        and case_verification >= 0.80
        and citation_f1 >= 0.80
        and abstention >= 0.80
        and citation_migration >= 0.80
        and formula_replay >= 0.80
        and operand_provenance >= 0.80
        and clarification >= 0.80
        and confidence_behavior >= 0.80
        and (retrieval_behavior is None or retrieval_behavior >= 0.80)
        and contract == 1.0
    )

    failure_counts: Counter[str] = Counter()
    for case_result in case_results.values():
        failure_counts.update(case_result.failure_labels)

    pre_confidences = [
        prediction.pre_confidence
        for prediction in prediction_map.values()
        if prediction.pre_confidence is not None
    ]
    post_confidences = [prediction.confidence for prediction in prediction_map.values()]

    metrics: dict[str, Any] = {
        "audit_score": round(audit_score, 4),
        "hard_gate_pass": hard_gate_pass,
        "case_accuracy": accuracy,
        "case_verification": case_verification,
        "unit_accuracy": unit_accuracy,
        "citation_f1": citation_f1,
        "formula_replay": formula_replay,
        "operand_provenance": operand_provenance,
        "missing_evidence_identification": clarification,
        "abstention_accuracy": abstention,
        "pair_reliability": pair_score,
        "pair_answer_behavior": pair_answer_behavior,
        "citation_migration": citation_migration,
        "formula_behavior": formula_behavior,
        "confidence_behavior": confidence_behavior,
        "retrieval_behavior": retrieval_behavior,
        "retrieval_telemetry_coverage": (
            len(reported_retrieval) / len(pair_results) if pair_results else 0.0
        ),
        "material_sensitivity": _mean(
            [item.score for item in pair_by_expectation["should_change"]]
        ),
        "distractor_invariance": _mean(
            [item.score for item in pair_by_expectation["should_not_change"]]
        ),
        "evidence_ablation": _mean(
            [item.score for item in pair_by_expectation["should_abstain"]]
        ),
        "cross_language_consistency": cross_language,
        "brier_score": brier,
        "expected_calibration_error": ece,
        "calibration_score": calibration_score,
        "contract_validity": contract,
        "mean_latency_ms": _mean(
            [prediction.latency_ms for prediction in prediction_map.values()]
        ),
        "total_input_tokens": sum(
            prediction.input_tokens for prediction in prediction_map.values()
        ),
        "total_output_tokens": sum(
            prediction.output_tokens for prediction in prediction_map.values()
        ),
        "pre_confidence_coverage": len(pre_confidences) / len(prediction_map),
        "mean_pre_confidence": (
            _mean([float(item) for item in pre_confidences]) if pre_confidences else None
        ),
        "mean_post_confidence": _mean(post_confidences),
        "mean_confidence_delta": (
            _mean(post_confidences) - _mean([float(item) for item in pre_confidences])
            if len(pre_confidences) == len(post_confidences)
            else None
        ),
        **_behavior_change_metrics(cases_by_id, prediction_map),
    }

    grouped_metrics: dict[str, dict[str, list[float]]] = {
        name: defaultdict(list)
        for name in (
            "case_accuracy",
            "case_verification",
            "citation_f1",
            "formula_replay",
            "abstention_accuracy",
            "pair_reliability",
        )
    }
    for case in cases:
        case_result = case_results[case.case_id]
        group_id = case.pair_group_id
        grouped_metrics["case_accuracy"][group_id].append(float(case_result.correct))
        grouped_metrics["case_verification"][group_id].append(
            float(verified_cases[case.case_id])
        )
        if case.expected.abstain:
            grouped_metrics["abstention_accuracy"][group_id].append(
                case_result.abstention_score
            )
        else:
            grouped_metrics["citation_f1"][group_id].append(case_result.citation_f1)
            grouped_metrics["formula_replay"][group_id].append(case_result.formula_score)
    for pair_result in pair_results:
        group_id = cases_by_id[pair_result.transformed_case_id].pair_group_id
        grouped_metrics["pair_reliability"][group_id].append(pair_result.score)
    uncertainty = clustered_bootstrap(grouped_metrics)

    return {
        "report_schema_version": "1.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "system": {"name": system_name, "version": system_version},
        "dataset": {
            "sha256": dataset_digest(cases),
            "case_count": len(cases),
            "pair_count": len(pair_results),
            "languages": sorted({case.language for case in cases}),
            "scenarios": sorted({case.scenario_id for case in cases}),
        },
        "metrics": metrics,
        "uncertainty": uncertainty,
        "by_transform": {
            name: {
                "count": len(rows),
                "pass_rate": _mean([row.score for row in rows]),
            }
            for name, rows in sorted(pair_by_transform.items())
        },
        "failure_counts": dict(sorted(failure_counts.items())),
        "cases": [
            {
                **case_results[case.case_id].to_dict(),
                "verified": verified_cases[case.case_id],
                "scenario_id": case.scenario_id,
                "language": case.language,
                "transform": case.relationship.transform,
                "question": case.question,
                "confidence": prediction_map[case.case_id].confidence,
                "pre_confidence": prediction_map[case.case_id].pre_confidence,
                "citations": list(prediction_map[case.case_id].citations),
                "formula_id": prediction_map[case.case_id].formula_id,
                "formula_score": case_results[case.case_id].formula_score,
                "operand_score": case_results[case.case_id].operand_score,
                "missing_evidence": list(prediction_map[case.case_id].missing_evidence),
                "expected_evidence": list(case.expected.required_evidence),
            }
            for case in sorted(cases, key=lambda item: item.case_id)
        ],
        "pairs": [item.to_dict() for item in pair_results],
        "run_metadata": run_metadata or {},
        "notes": [
            "Audit Score is a transparent project index, not a regulatory certification.",
            "Hard gates prevent strong fluency or calibration from hiding basic financial failures.",
            "Synthetic v0.1 results must not be generalized to real-world investment performance.",
        ],
    }
