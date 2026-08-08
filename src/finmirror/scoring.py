"""Deterministic financial, evidence, calibration, and pairwise metrics."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable

from finmirror.models import (
    BenchmarkCase,
    CalculationOperand,
    CaseResult,
    PairResult,
    Prediction,
)

_NUMBER_PATTERN = re.compile(
    r"(?<![\w])(?P<paren>\()?\s*(?P<sign>[-+])?\s*"
    r"(?P<number>\d[\d,\s]*(?:\.\d+)?)\s*(?P<suffix>%|x|m|million|months?)?"
    r"\s*(?(paren)\))",
    re.IGNORECASE,
)


def normalize_number(value: float | str | None, answer: str = "") -> float | None:
    """Normalize an explicit numeric value, falling back to the answer text."""

    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    candidates = [str(value)] if value is not None else []
    if answer:
        candidates.append(answer)
    for candidate in candidates:
        match = _NUMBER_PATTERN.search(candidate)
        if not match:
            continue
        token = match.group("number").replace(",", "").replace(" ", "")
        try:
            number = float(token)
        except ValueError:
            continue
        if match.group("paren") or match.group("sign") == "-":
            number = -number
        return number if math.isfinite(number) else None
    return None


def normalize_text(value: float | str | None, answer: str = "") -> str:
    raw = answer if value is None else str(value)
    return " ".join(raw.casefold().split())


def semantic_prediction_key(
    case: BenchmarkCase,
    prediction: Prediction,
) -> tuple[str, str]:
    """Canonical semantic output used by cross-language consistency checks."""

    if prediction.abstained:
        return ("abstain", "")
    if case.expected.answer_type == "number":
        value = normalize_number(prediction.value, prediction.answer)
        if value is not None:
            return ("number", f"{round(value, 8)}:{prediction.unit.casefold()}")
    return ("text", normalize_text(prediction.value, prediction.answer))


def citation_scores(
    predicted: Iterable[str], expected: Iterable[str]
) -> tuple[float, float, float]:
    predicted_set = set(predicted)
    expected_set = set(expected)
    if not expected_set:
        perfect = 1.0 if not predicted_set else 0.0
        return perfect, 1.0, perfect
    if not predicted_set:
        return 0.0, 0.0, 0.0
    overlap = len(predicted_set & expected_set)
    precision = overlap / len(predicted_set)
    recall = overlap / len(expected_set)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def execute_formula(formula_id: str, operands: Iterable[CalculationOperand]) -> float | None:
    """Execute one allow-listed, typed finance program.

    Arbitrary model-generated code is never evaluated. Unknown programs, missing
    names, duplicate names, non-finite values, and division by zero fail closed.
    """

    materialized = list(operands)
    values = {item.name: item.value for item in materialized}
    if len(values) != len(materialized):
        return None
    try:
        if formula_id == "revenue_growth":
            result = (values["current"] - values["prior"]) / values["prior"] * 100
        elif formula_id == "gross_margin":
            result = (values["revenue"] - values["cost"]) / values["revenue"] * 100
        elif formula_id == "debt_to_equity":
            result = values["debt"] / values["equity"]
        elif formula_id == "cash_runway":
            result = values["cash"] / values["monthly_burn"]
        elif formula_id == "covenant_headroom":
            result = values["maximum"] - values["actual"]
        elif formula_id == "free_cash_flow":
            result = values["operating_cash"] - values["capex"]
        else:
            return None
    except (KeyError, ZeroDivisionError):
        return None
    return result if math.isfinite(result) else None


def _formula_scores(case: BenchmarkCase, prediction: Prediction) -> tuple[float, float]:
    expected = case.expected
    if expected.abstain:
        empty = not prediction.formula_id and not prediction.operands
        return (1.0 if empty else 0.0, 1.0 if not prediction.operands else 0.0)
    expected_by_name = {item.name: item for item in expected.operands}
    predicted_by_name = {item.name: item for item in prediction.operands}
    if not expected_by_name:
        return (0.0, 0.0)

    component_matches = 0
    component_count = 3 * len(expected_by_name)
    for name, gold in expected_by_name.items():
        candidate = predicted_by_name.get(name)
        if candidate is None:
            continue
        component_matches += int(
            math.isclose(candidate.value, gold.value, abs_tol=1e-8, rel_tol=0.0)
        )
        component_matches += int(candidate.unit.casefold() == gold.unit.casefold())
        component_matches += int(candidate.evidence == gold.evidence)
    operand_score = component_matches / component_count
    if set(predicted_by_name) != set(expected_by_name):
        operand_score *= len(expected_by_name) / max(
            len(expected_by_name), len(predicted_by_name)
        )

    replayed = execute_formula(prediction.formula_id, prediction.operands)
    predicted_number = normalize_number(prediction.value, prediction.answer)
    expected_number = float(expected.value) if expected.value is not None else None
    replay_ok = (
        replayed is not None
        and predicted_number is not None
        and expected_number is not None
        and math.isclose(
            replayed,
            expected_number,
            abs_tol=expected.tolerance,
            rel_tol=0.0,
        )
        and math.isclose(
            replayed,
            predicted_number,
            abs_tol=expected.tolerance,
            rel_tol=0.0,
        )
    )
    formula_ok = (
        prediction.formula_id == expected.formula_id and operand_score == 1.0 and replay_ok
    )
    return (1.0 if formula_ok else 0.0, operand_score)


def score_case(case: BenchmarkCase, prediction: Prediction) -> CaseResult:
    """Score a single output without an LLM judge."""

    failures: list[str] = []
    contract_ok = (
        prediction.case_id == case.case_id
        and 0.0 <= prediction.confidence <= 1.0
        and (prediction.pre_confidence is None or 0.0 <= prediction.pre_confidence <= 1.0)
    )
    if not contract_ok:
        failures.append("invalid_contract")

    if case.expected.abstain:
        correct = prediction.abstained
        answer_score = 1.0 if correct else 0.0
        unit_score = 1.0 if correct else 0.0
        abstention_score = 1.0 if correct else 0.0
        if not correct:
            failures.append("failed_to_abstain")
        precision, recall, citation_f1 = citation_scores(prediction.citations, ())
        retrieval_recall = None
        formula_score, operand_score = _formula_scores(case, prediction)
        clarification_score = (
            1.0
            if set(prediction.missing_evidence) == set(case.expected.missing_evidence)
            else 0.0
        )
        if formula_score < 1.0:
            failures.append("calculated_without_sufficient_evidence")
        if clarification_score < 1.0:
            failures.append("missing_requirement_not_identified")
        brier = None
    elif prediction.abstained:
        correct = False
        answer_score = 0.0
        unit_score = 0.0
        abstention_score = 0.0
        failures.append("over_refusal")
        precision, recall, citation_f1 = citation_scores(
            prediction.citations, case.expected.required_evidence
        )
        retrieval_recall = _retrieval_recall(case, prediction)
        formula_score, operand_score = _formula_scores(case, prediction)
        clarification_score = 1.0 if not prediction.missing_evidence else 0.0
        brier = prediction.confidence**2
    else:
        abstention_score = 1.0
        if case.expected.answer_type == "number":
            predicted_number = normalize_number(prediction.value, prediction.answer)
            expected_number = (
                float(case.expected.value) if case.expected.value is not None else None
            )
            if predicted_number is None or expected_number is None:
                answer_score = 0.0
            else:
                answer_score = (
                    1.0
                    if math.isclose(
                        predicted_number,
                        expected_number,
                        abs_tol=case.expected.tolerance,
                        rel_tol=0.0,
                    )
                    else 0.0
                )
        else:
            answer_score = (
                1.0
                if normalize_text(prediction.value, prediction.answer)
                == normalize_text(case.expected.value, case.expected.display)
                else 0.0
            )
        unit_score = 1.0 if prediction.unit.casefold() == case.expected.unit.casefold() else 0.0
        if answer_score == 0:
            failures.append("wrong_answer")
        if unit_score == 0:
            failures.append("wrong_unit")
        precision, recall, citation_f1 = citation_scores(
            prediction.citations, case.expected.required_evidence
        )
        if citation_f1 < 1.0:
            failures.append("insufficient_evidence")
        retrieval_recall = _retrieval_recall(case, prediction)
        formula_score, operand_score = _formula_scores(case, prediction)
        clarification_score = 1.0 if not prediction.missing_evidence else 0.0
        if formula_score < 1.0:
            failures.append("invalid_formula_replay")
        if operand_score < 1.0:
            failures.append("incorrect_operand_provenance")
        if clarification_score < 1.0:
            failures.append("spurious_missing_requirement")
        if retrieval_recall is not None and retrieval_recall < 1.0:
            failures.append("missed_required_document")
        correct = bool(answer_score and unit_score)
        brier = (prediction.confidence - float(correct)) ** 2

    predicted_display = "ABSTAIN" if prediction.abstained else prediction.answer
    return CaseResult(
        case_id=case.case_id,
        correct=correct and contract_ok,
        answer_score=answer_score,
        unit_score=unit_score,
        citation_precision=precision,
        citation_recall=recall,
        citation_f1=citation_f1,
        retrieval_recall=retrieval_recall,
        formula_score=formula_score,
        operand_score=operand_score,
        clarification_score=clarification_score,
        abstention_score=abstention_score,
        contract_score=1.0 if contract_ok else 0.0,
        brier=brier,
        failure_labels=tuple(failures),
        expected_display="ABSTAIN" if case.expected.abstain else case.expected.display,
        predicted_display=predicted_display,
    )


def _retrieval_recall(case: BenchmarkCase, prediction: Prediction) -> float | None:
    """Score optional retrieval telemetry against gold evidence documents.

    Empty telemetry means "not reported", rather than a fabricated retrieval
    failure. Adapters that report retrieval IDs are held to the stricter gate.
    """

    if not prediction.retrieved_document_ids or not case.expected.required_evidence:
        return None
    expected_documents = {
        evidence.rsplit("#", maxsplit=1)[0] for evidence in case.expected.required_evidence
    }
    retrieved = set(prediction.retrieved_document_ids)
    return len(expected_documents & retrieved) / len(expected_documents)


def prediction_changed(
    reference_case: BenchmarkCase,
    transformed_case: BenchmarkCase,
    reference: Prediction,
    transformed: Prediction,
) -> bool:
    """Whether an agent's semantic answer changed across a pair."""

    if reference.abstained != transformed.abstained:
        return True
    if reference.abstained and transformed.abstained:
        return False
    if reference_case.expected.answer_type == "number":
        left = normalize_number(reference.value, reference.answer)
        right = normalize_number(transformed.value, transformed.answer)
        if left is None or right is None:
            return normalize_text(reference.value, reference.answer) != normalize_text(
                transformed.value, transformed.answer
            )
        tolerance = max(
            reference_case.expected.tolerance,
            transformed_case.expected.tolerance,
        )
        return not math.isclose(left, right, abs_tol=tolerance, rel_tol=0.0)
    return normalize_text(reference.value, reference.answer) != normalize_text(
        transformed.value, transformed.answer
    )


def score_pair(
    reference_case: BenchmarkCase,
    transformed_case: BenchmarkCase,
    reference_prediction: Prediction,
    transformed_prediction: Prediction,
    reference_result: CaseResult,
    transformed_result: CaseResult,
) -> PairResult:
    expectation = transformed_case.relationship.expectation
    changed = prediction_changed(
        reference_case,
        transformed_case,
        reference_prediction,
        transformed_prediction,
    )
    reference_evidence_ok = reference_result.citation_f1 == 1.0
    if expectation == "should_abstain":
        transformed_evidence_ok = (
            transformed_result.citation_f1 == 1.0 and not transformed_prediction.citations
        )
    else:
        transformed_evidence_ok = transformed_result.citation_f1 == 1.0
    evidence_pass = reference_evidence_ok and transformed_evidence_ok
    citation_migrated = evidence_pass and (
        expectation == "should_abstain"
        or set(reference_prediction.citations).isdisjoint(transformed_prediction.citations)
    )
    evidence_pass = evidence_pass and citation_migrated
    formula_pass = (
        reference_result.formula_score == 1.0
        and transformed_result.formula_score == 1.0
        and (expectation != "should_abstain" or transformed_result.clarification_score == 1.0)
    )

    retrieval_values = [
        value
        for value in (
            reference_result.retrieval_recall,
            transformed_result.retrieval_recall,
        )
        if value is not None
    ]
    retrieval_pass = (
        None if not retrieval_values else all(value == 1.0 for value in retrieval_values)
    )
    confidence_delta = transformed_prediction.confidence - reference_prediction.confidence

    if expectation == "should_change":
        answer_pass = reference_result.correct and transformed_result.correct and changed
        confidence_pass = (
            reference_prediction.confidence >= 0.5 and transformed_prediction.confidence >= 0.5
        )
    elif expectation == "should_not_change":
        answer_pass = reference_result.correct and transformed_result.correct and not changed
        confidence_pass = abs(confidence_delta) <= 0.15
    elif expectation == "should_abstain":
        answer_pass = (
            reference_result.correct
            and transformed_result.correct
            and transformed_prediction.abstained
        )
        confidence_pass = transformed_prediction.confidence <= 0.30 and (
            confidence_delta <= -0.20 or transformed_prediction.confidence <= 0.10
        )
    else:
        raise ValueError("Reference cases cannot be scored as transformed pairs")

    passed = (
        answer_pass
        and evidence_pass
        and formula_pass
        and confidence_pass
        and retrieval_pass is not False
    )
    failures = []
    if not answer_pass:
        failures.append("answer behavior")
    if not evidence_pass:
        failures.append("evidence migration")
    if not formula_pass:
        failures.append("formula/operand behavior")
    if not confidence_pass:
        failures.append("confidence behavior")
    if retrieval_pass is False:
        failures.append("reported retrieval")
    reason = (
        "answer, evidence, confidence, and reported retrieval followed the intervention"
        if passed
        else "failed " + ", ".join(failures)
    )
    return PairResult(
        reference_case_id=reference_case.case_id,
        transformed_case_id=transformed_case.case_id,
        transform=transformed_case.relationship.transform,
        expectation=expectation,
        passed=passed,
        score=1.0 if passed else 0.0,
        answer_pass=answer_pass,
        evidence_pass=evidence_pass,
        formula_pass=formula_pass,
        confidence_pass=confidence_pass,
        retrieval_pass=retrieval_pass,
        answer_changed=changed,
        citation_migrated=citation_migrated,
        confidence_delta=confidence_delta,
        reason=reason,
    )


def expected_calibration_error(
    confidences: list[float], labels: list[int], bins: int = 10
) -> float | None:
    if not confidences:
        return None
    total = len(confidences)
    error = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        members = [
            position
            for position, confidence in enumerate(confidences)
            if lower <= confidence < upper or (index == bins - 1 and confidence == 1.0)
        ]
        if not members:
            continue
        mean_confidence = sum(confidences[position] for position in members) / len(members)
        accuracy = sum(labels[position] for position in members) / len(members)
        error += len(members) / total * abs(mean_confidence - accuracy)
    return error
