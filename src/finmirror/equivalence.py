"""Positive metamorphic assurance for the deterministic evaluator.

The negative mutation suite asks whether harmful one-field changes are detected. This
module asks the dual question: do declared, representation-only changes preserve every
scored verdict? Both directions are needed before an evaluator can be used as a release
gate.
"""

from __future__ import annotations

import html
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from finmirror.adapters.base import run_adapter
from finmirror.adapters.baselines import EvidenceProgramBaseline
from finmirror.dataset import dataset_digest
from finmirror.models import BenchmarkCase, CaseResult, PairResult, Prediction
from finmirror.scoring import score_case, score_pair, semantic_prediction_key

EQUIVALENCE_SCHEMA_VERSION = "1.0"
_PREDICTION_FIELDS = tuple(Prediction.__dataclass_fields__)


@dataclass(frozen=True)
class _Relation:
    relation_id: str
    description: str
    declared_fields: tuple[str, ...]
    eligible: Callable[[BenchmarkCase, Prediction], bool]
    apply: Callable[[Prediction], Prediction]


def _is_numeric_answer(case: BenchmarkCase, prediction: Prediction) -> bool:
    return (
        not prediction.abstained
        and case.expected.answer_type == "number"
        and isinstance(prediction.value, (int, float))
        and not isinstance(prediction.value, bool)
    )


def _numeric_string(prediction: Prediction) -> Prediction:
    if not isinstance(prediction.value, (int, float)) or isinstance(prediction.value, bool):
        raise ValueError(f"{prediction.case_id}: numeric-string relation requires a number")
    return replace(prediction, value=f"{float(prediction.value):,.8f}")


def _telemetry_variation(prediction: Prediction) -> Prediction:
    return replace(
        prediction,
        latency_ms=prediction.latency_ms + 123.0,
        input_tokens=prediction.input_tokens + 7,
        output_tokens=prediction.output_tokens + 11,
        metadata={
            **prediction.metadata,
            "equivalence_audit": "deliberately irrelevant telemetry",
        },
    )


def _relations() -> tuple[_Relation, ...]:
    return (
        _Relation(
            "citation_permutation",
            "Citation order changes while the cited evidence set stays fixed.",
            ("citations",),
            lambda _case, item: len(item.citations) > 1,
            lambda item: replace(item, citations=tuple(reversed(item.citations))),
        ),
        _Relation(
            "citation_idempotence",
            "Repeating an existing citation does not create new evidence.",
            ("citations",),
            lambda _case, item: bool(item.citations),
            lambda item: replace(item, citations=(*item.citations, item.citations[0])),
        ),
        _Relation(
            "operand_permutation",
            "Named calculation operands are reordered without changing their bindings.",
            ("operands",),
            lambda _case, item: len(item.operands) > 1,
            lambda item: replace(item, operands=tuple(reversed(item.operands))),
        ),
        _Relation(
            "answer_surrounding_whitespace",
            "Whitespace around the human-readable answer display is non-semantic.",
            ("answer",),
            lambda _case, item: not item.abstained and bool(item.answer),
            lambda item: replace(item, answer=f"  {item.answer}  "),
        ),
        _Relation(
            "numeric_string_encoding",
            "A numeric contract value is rendered as a comma-aware decimal string.",
            ("value",),
            _is_numeric_answer,
            _numeric_string,
        ),
        _Relation(
            "answer_unit_case",
            "Canonical unit tokens are compared case-insensitively.",
            ("unit",),
            lambda _case, item: item.unit != item.unit.upper(),
            lambda item: replace(item, unit=item.unit.upper()),
        ),
        _Relation(
            "operand_unit_case",
            "Operand unit labels change letter case without changing quantities.",
            ("operands",),
            lambda _case, item: (
                bool(item.operands)
                and any(operand.unit != operand.unit.upper() for operand in item.operands)
            ),
            lambda item: replace(
                item,
                operands=tuple(
                    replace(operand, unit=operand.unit.upper()) for operand in item.operands
                ),
            ),
        ),
        _Relation(
            "retrieval_idempotence",
            "Repeating a reported retrieval identifier does not retrieve a new document.",
            ("retrieved_document_ids",),
            lambda _case, item: bool(item.retrieved_document_ids),
            lambda item: replace(
                item,
                retrieved_document_ids=(
                    *item.retrieved_document_ids,
                    item.retrieved_document_ids[0],
                ),
            ),
        ),
        _Relation(
            "missing_requirement_idempotence",
            "Repeating the same missing requirement leaves the clarification set fixed.",
            ("missing_evidence",),
            lambda _case, item: bool(item.missing_evidence),
            lambda item: replace(
                item,
                missing_evidence=(*item.missing_evidence, item.missing_evidence[0]),
            ),
        ),
        _Relation(
            "irrelevant_telemetry",
            "Latency, token counts, and metadata vary without affecting quality scores.",
            ("latency_ms", "input_tokens", "output_tokens", "metadata"),
            lambda _case, _item: True,
            _telemetry_variation,
        ),
    )


def _case_signature(result: CaseResult) -> dict[str, Any]:
    """Return the public scoring verdict, excluding display-only answer rendering."""

    value = result.to_dict()
    value.pop("predicted_display")
    return value


def _pair_results(
    cases: list[BenchmarkCase], predictions: dict[str, Prediction]
) -> dict[str, PairResult]:
    cases_by_id = {case.case_id: case for case in cases}
    results: dict[str, PairResult] = {}
    for target in cases:
        reference_id = target.relationship.reference_case_id
        if reference_id is None:
            continue
        reference = cases_by_id[reference_id]
        reference_prediction = predictions[reference_id]
        target_prediction = predictions[target.case_id]
        results[target.case_id] = score_pair(
            reference,
            target,
            reference_prediction,
            target_prediction,
            score_case(reference, reference_prediction),
            score_case(target, target_prediction),
        )
    return results


def _parallel_results(
    cases: list[BenchmarkCase], predictions: dict[str, Prediction]
) -> dict[str, bool]:
    groups: dict[str, list[BenchmarkCase]] = defaultdict(list)
    for case in cases:
        groups[case.parallel_id].append(case)
    results: dict[str, bool] = {}
    for parallel_id, members in groups.items():
        case_results = [score_case(case, predictions[case.case_id]) for case in members]
        keys = {semantic_prediction_key(case, predictions[case.case_id]) for case in members}
        results[parallel_id] = all(item.correct for item in case_results) and len(keys) == 1
    return results


def _changed_fields(before: Prediction, after: Prediction) -> tuple[str, ...]:
    before_data = before.to_dict()
    after_data = after.to_dict()
    return tuple(name for name in _PREDICTION_FIELDS if before_data[name] != after_data[name])


def _relation_result(
    relation: _Relation,
    *,
    cases: list[BenchmarkCase],
    baseline: dict[str, Prediction],
    baseline_cases: dict[str, dict[str, Any]],
    baseline_pairs: dict[str, PairResult],
    baseline_parallel: dict[str, bool],
) -> dict[str, Any]:
    cases_by_id = {case.case_id: case for case in cases}
    eligible_ids = tuple(
        sorted(
            case.case_id for case in cases if relation.eligible(case, baseline[case.case_id])
        )
    )
    if not eligible_ids:
        raise ValueError(f"Equivalence relation {relation.relation_id!r} has no eligible cases")

    eligible_set = set(eligible_ids)
    transformed = {
        case_id: relation.apply(prediction) if case_id in eligible_set else prediction
        for case_id, prediction in baseline.items()
    }
    changed_ids = tuple(
        case_id
        for case_id in eligible_ids
        if baseline[case_id].to_dict() != transformed[case_id].to_dict()
    )
    changed_set = set(changed_ids)

    observed_fields = {
        case_id: _changed_fields(baseline[case_id], transformed[case_id])
        for case_id in changed_ids
    }
    case_preserved_count = sum(
        _case_signature(score_case(cases_by_id[case_id], transformed[case_id]))
        == baseline_cases[case_id]
        for case_id in changed_ids
    )
    semantic_preserved_count = sum(
        semantic_prediction_key(cases_by_id[case_id], transformed[case_id])
        == semantic_prediction_key(cases_by_id[case_id], baseline[case_id])
        for case_id in changed_ids
    )

    affected_pair_ids = tuple(
        sorted(
            target.case_id
            for target in cases
            if target.relationship.reference_case_id is not None
            and (
                target.case_id in changed_set
                or target.relationship.reference_case_id in changed_set
            )
        )
    )
    transformed_pairs = _pair_results(cases, transformed)
    pair_preserved_count = sum(
        transformed_pairs[case_id].to_dict() == baseline_pairs[case_id].to_dict()
        for case_id in affected_pair_ids
    )

    affected_parallel_ids = tuple(
        sorted({cases_by_id[case_id].parallel_id for case_id in changed_ids})
    )
    transformed_parallel = _parallel_results(cases, transformed)
    parallel_preserved_count = sum(
        transformed_parallel[parallel_id] == baseline_parallel[parallel_id]
        for parallel_id in affected_parallel_ids
    )

    raw_rejection_count = sum(
        baseline[case_id].to_dict() != transformed[case_id].to_dict()
        for case_id in eligible_ids
    )
    declared = set(relation.declared_fields)
    checks = {
        "eligible_cases_changed": len(changed_ids) == len(eligible_ids),
        "only_declared_fields_changed": all(
            set(fields) == declared for fields in observed_fields.values()
        ),
        "case_scores_preserved": case_preserved_count == len(changed_ids),
        "semantic_keys_preserved": semantic_preserved_count == len(changed_ids),
        "pair_results_preserved": pair_preserved_count == len(affected_pair_ids),
        "parallel_results_preserved": parallel_preserved_count == len(affected_parallel_ids),
        "raw_equality_control_rejected": raw_rejection_count == len(eligible_ids),
    }
    assertion_count = 2 * len(changed_ids) + len(affected_pair_ids) + len(affected_parallel_ids)
    return {
        "relation_id": relation.relation_id,
        "description": relation.description,
        "declared_fields": list(relation.declared_fields),
        "eligible_case_count": len(eligible_ids),
        "changed_case_count": len(changed_ids),
        "affected_pair_count": len(affected_pair_ids),
        "affected_parallel_group_count": len(affected_parallel_ids),
        "semantic_assertion_count": assertion_count,
        "case_score_preserved_count": case_preserved_count,
        "semantic_key_preserved_count": semantic_preserved_count,
        "pair_result_preserved_count": pair_preserved_count,
        "parallel_result_preserved_count": parallel_preserved_count,
        "raw_equality_rejection_count": raw_rejection_count,
        "checks": checks,
        "passed": all(checks.values()),
    }


def run_equivalence_assurance(cases: list[BenchmarkCase]) -> dict[str, Any]:
    """Run the fixed positive-equivalence matrix without a network or LLM judge."""

    cases_by_id = {case.case_id: case for case in cases}
    predictions = run_adapter(EvidenceProgramBaseline(), cases)
    baseline = {prediction.case_id: prediction for prediction in predictions}
    if set(baseline) != set(cases_by_id):
        raise ValueError(
            "Evidence-program baseline did not emit exactly one prediction per case"
        )

    baseline_results = {
        case.case_id: score_case(case, baseline[case.case_id]) for case in cases
    }
    baseline_failures = {
        case_id: list(result.failure_labels)
        for case_id, result in baseline_results.items()
        if result.failure_labels
    }
    if baseline_failures:
        raise ValueError(f"Evidence-program baseline is not clean: {baseline_failures}")

    baseline_pairs = _pair_results(cases, baseline)
    blocked_pairs = sorted(
        case_id for case_id, result in baseline_pairs.items() if not result.passed
    )
    if blocked_pairs:
        raise ValueError(f"Evidence-program baseline has blocked pairs: {blocked_pairs}")

    baseline_cases = {
        case_id: _case_signature(result) for case_id, result in baseline_results.items()
    }
    baseline_parallel = _parallel_results(cases, baseline)
    if not all(baseline_parallel.values()):
        blocked = sorted(key for key, value in baseline_parallel.items() if not value)
        raise ValueError(
            f"Evidence-program baseline has inconsistent parallel groups: {blocked}"
        )

    relations = [
        _relation_result(
            relation,
            cases=cases,
            baseline=baseline,
            baseline_cases=baseline_cases,
            baseline_pairs=baseline_pairs,
            baseline_parallel=baseline_parallel,
        )
        for relation in _relations()
    ]
    passed_count = sum(bool(item["passed"]) for item in relations)
    rejected_relations = sum(
        bool(item["checks"]["raw_equality_control_rejected"]) for item in relations
    )
    return {
        "equivalence_schema_version": EQUIVALENCE_SCHEMA_VERSION,
        "dataset_sha256": dataset_digest(cases),
        "baseline": {
            "name": EvidenceProgramBaseline.name,
            "version": EvidenceProgramBaseline.version,
            "uses_gold": False,
        },
        "method": "positive metamorphic assurance over declared semantic equivalence classes",
        "relation_count": len(relations),
        "semantic_assertion_count": sum(
            int(item["semantic_assertion_count"]) for item in relations
        ),
        "passed_count": passed_count,
        "passed": passed_count == len(relations),
        "negative_control": {
            "name": "raw-contract-equality",
            "deliberately_brittle": True,
            "rejected_relation_count": rejected_relations,
            "rejection_rate": rejected_relations / len(relations),
            "purpose": (
                "Prove each transformation is non-trivial and that byte/sequence equality "
                "would falsely reject legitimate representations."
            ),
        },
        "relations": relations,
        "claim_boundary": (
            "Passing shows invariance only for the declared contract-level relations over "
            "this digest-bound dataset. It is not proof of all financial equivalences, "
            "formal verification, or production validity."
        ),
    }


def render_equivalence_report(report: dict[str, Any], output: str | Path) -> Path:
    """Render a self-contained public assurance card."""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    passed = bool(report["passed"])
    status = "PASS" if passed else "BLOCKED"
    relation_rows = []
    for relation in report["relations"]:
        relation_status = "PASS" if relation["passed"] else "BLOCKED"
        relation_rows.append(
            "<tr>"
            f"<td><strong>{html.escape(str(relation['relation_id']))}</strong>"
            f"<small>{html.escape(str(relation['description']))}</small></td>"
            f"<td>{int(relation['eligible_case_count'])}</td>"
            f"<td>{int(relation['affected_pair_count'])}</td>"
            f"<td>{int(relation['semantic_assertion_count'])}</td>"
            f'<td class="{relation_status.lower()}">{relation_status}</td>'
            "</tr>"
        )
    negative = report["negative_control"]
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FinMirror · Equivalence assurance</title>
<style>
:root{{--ink:#f4f1e8;--muted:#a8b3af;--bg:#09100e;--panel:#101a17;--line:#2a3934;--mint:#8ce7c1;--coral:#ff917c;--gold:#f6d477}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 85% 0,rgba(63,194,145,.18),transparent 34rem),var(--bg);color:var(--ink);font:15px/1.55 Inter,system-ui,sans-serif;font-variant-numeric:tabular-nums}}
main{{width:min(1120px,calc(100% - 32px));margin:auto;padding:64px 0}} a{{color:var(--mint)}} .brand{{color:var(--mint);text-transform:uppercase;letter-spacing:.16em;font-size:11px}} h1{{font-size:clamp(42px,7vw,74px);line-height:.98;letter-spacing:-.05em;margin:12px 0 18px}} .lede{{max-width:770px;color:var(--muted);font-size:17px}}
.scorecard{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:36px 0}} .metric{{padding:19px;border:1px solid var(--line);border-radius:16px;background:var(--panel)}} .metric b{{display:block;font-size:28px}} .metric span{{color:var(--muted);font-size:12px}} .metric.status b{{color:{"var(--mint)" if passed else "var(--coral)"}}}
.thesis{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:24px 0 38px}} .card{{border:1px solid var(--line);border-radius:18px;padding:20px;background:rgba(255,255,255,.025)}} .card h2{{font-size:18px;margin:0 0 8px}} .card p{{color:var(--muted);margin:0}} .negative h2{{color:var(--gold)}}
.table{{overflow:auto;border:1px solid var(--line);border-radius:18px;background:var(--panel)}} table{{width:100%;min-width:760px;border-collapse:collapse}} th,td{{padding:15px 17px;border-bottom:1px solid var(--line);text-align:left}} th{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.09em}} td small{{display:block;color:var(--muted);max-width:570px;margin-top:3px}} .pass{{color:var(--mint);font-weight:800}} .blocked{{color:var(--coral);font-weight:800}} .boundary{{margin-top:24px;color:var(--muted);font-size:12px;max-width:850px}} @media(max-width:760px){{.scorecard{{grid-template-columns:1fr 1fr}}.thesis{{grid-template-columns:1fr}}}}
</style></head><body><main>
<div class="brand">FinMirror · evaluator assurance</div>
<h1>Equivalent inputs.<br>Identical verdicts.</h1>
<p class="lede">A digest-bound, zero-network positive metamorphic audit. Ten declared representation changes must preserve case scores, semantic keys, paired-world gates, and cross-language consistency.</p>
<section class="scorecard">
  <div class="metric status"><b>{status}</b><span>release gate</span></div>
  <div class="metric"><b>{int(report["passed_count"])}/{int(report["relation_count"])}</b><span>relations preserved</span></div>
  <div class="metric"><b>{int(report["semantic_assertion_count"]):,}</b><span>semantic assertions</span></div>
  <div class="metric"><b>{100 * float(negative["rejection_rate"]):.0f}%</b><span>brittle control rejected</span></div>
</section>
<section class="thesis">
  <div class="card"><h2>The dual assurance rule</h2><p>Harmful mutations must lower the right metric; harmless representations must not change any verdict. FinMirror now gates both directions.</p></div>
  <div class="card negative"><h2>Deliberately brittle control</h2><p>Raw contract equality rejected {int(negative["rejected_relation_count"])}/{int(report["relation_count"])} valid relations. This confirms the audit is not passing unchanged fixtures.</p></div>
</section>
<div class="table"><table><thead><tr><th>Declared relation</th><th>Cases</th><th>Pairs</th><th>Assertions</th><th>Gate</th></tr></thead><tbody>{"".join(relation_rows)}</tbody></table></div>
<p class="boundary">{html.escape(str(report["claim_boundary"]))} <a href="report.json">Inspect the machine-readable report</a>.</p>
</main></body></html>"""
    output_path.write_text(document, encoding="utf-8", newline="\n")
    return output_path
