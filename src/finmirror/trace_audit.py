"""Deterministic replay checks for evidence-using agent trajectories.

The audit deliberately verifies observable claims, not hidden model reasoning. A
content-addressed read receipt proves that a trajectory is consistent with the exact
document bytes in the evaluated world; it does not prove that a model did not receive
the same information through another channel.
"""

from __future__ import annotations

import hashlib
import html
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from finmirror.dataset import canonical_json, dataset_digest
from finmirror.models import BenchmarkCase, Document, Prediction
from finmirror.scoring import score_case


def document_observation_sha256(document: Document) -> str:
    """Bind a read observation to the complete public document contract."""

    payload = {
        "content": document.content,
        "id": document.id,
        "media_type": document.media_type,
        "metadata": document.metadata,
        "source_url": document.source_url,
        "title": document.title,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def verified_read_event(document: Document) -> dict[str, object]:
    """Return the canonical, replayable trace event for one document read."""

    return {
        "step": "read_document",
        "document_id": document.id,
        "observation_sha256": document_observation_sha256(document),
    }


@dataclass(frozen=True)
class TraceAuditResult:
    """Fail-closed path checks for one normalized prediction."""

    case_id: str
    passed: bool
    score: float
    answer_correct: bool
    receipt_valid: bool
    retrieval_claim_valid: bool
    citation_path_valid: bool
    operand_path_valid: bool
    decision_path_valid: bool
    verified_document_ids: tuple[str, ...]
    failure_labels: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["verified_document_ids"] = list(self.verified_document_ids)
        value["failure_labels"] = list(self.failure_labels)
        return value


def _document_id(evidence: str) -> str:
    return evidence.split("#", 1)[0]


def _string_list(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return None
    return tuple(value)


def audit_prediction_trace(
    case: BenchmarkCase,
    prediction: Prediction,
) -> TraceAuditResult:
    """Replay one trace against its exact evidence world.

    Unknown or malformed events fail closed. The five component checks are kept
    separate so a client can distinguish bad receipts from unsupported citations or
    an incomplete decision program.
    """

    if prediction.case_id != case.case_id:
        raise ValueError(
            f"Prediction {prediction.case_id!r} does not match case {case.case_id!r}"
        )

    documents = {item.id: item for item in case.documents}
    failures: set[str] = set()
    verified_reads: list[str] = []
    extraction_evidence: tuple[str, ...] | None = None
    executed_formula: str | None = None
    abstention_evidence: tuple[str, ...] | None = None

    for event in prediction.trace:
        step = event.get("step")
        if step == "read_document":
            document_id = event.get("document_id")
            receipt = event.get("observation_sha256")
            if not isinstance(document_id, str) or not isinstance(receipt, str):
                failures.add("malformed_read_event")
                continue
            document = documents.get(document_id)
            if document is None:
                failures.add("unknown_document_read")
                continue
            if receipt != document_observation_sha256(document):
                failures.add("observation_digest_mismatch")
                continue
            if document_id not in verified_reads:
                verified_reads.append(document_id)
        elif step == "extract_operands":
            evidence = _string_list(event.get("evidence"))
            if evidence is None:
                failures.add("malformed_extraction_event")
            else:
                extraction_evidence = evidence
        elif step == "execute_formula":
            formula_id = event.get("formula_id")
            if not isinstance(formula_id, str) or not formula_id:
                failures.add("malformed_formula_event")
            else:
                executed_formula = formula_id
        elif step == "abstain":
            evidence = _string_list(event.get("missing_evidence"))
            if evidence is None:
                failures.add("malformed_abstention_event")
            else:
                abstention_evidence = evidence
        else:
            failures.add("unsupported_trace_event")

    verified = set(verified_reads)
    if not verified:
        failures.add("no_verified_document_read")

    reported = set(prediction.retrieved_document_ids)
    retrieval_claim_valid = reported == verified
    if not retrieval_claim_valid:
        failures.add("retrieval_claim_mismatch")

    citation_documents = {_document_id(item) for item in prediction.citations}
    citation_path_valid = citation_documents.issubset(verified)
    if not citation_path_valid:
        failures.add("citation_without_verified_read")

    operand_evidence = tuple(item.evidence for item in prediction.operands)
    operand_documents = {_document_id(item) for item in operand_evidence}
    operand_path_valid = operand_documents.issubset(verified)
    if not operand_path_valid:
        failures.add("operand_without_verified_read")

    required_documents = {
        _document_id(item)
        for item in (
            case.expected.missing_evidence
            if case.expected.abstain
            else case.expected.required_evidence
        )
    }
    if not required_documents.issubset(verified):
        failures.add("required_document_not_read")

    decision_path_valid = True
    if prediction.abstained:
        if abstention_evidence is None:
            failures.add("missing_abstention_event")
            decision_path_valid = False
        elif set(abstention_evidence) != set(prediction.missing_evidence):
            failures.add("abstention_provenance_mismatch")
            decision_path_valid = False
    else:
        if extraction_evidence is None:
            failures.add("missing_extraction_event")
            decision_path_valid = False
        elif set(extraction_evidence) != set(operand_evidence):
            failures.add("extraction_provenance_mismatch")
            decision_path_valid = False
        if executed_formula is None:
            failures.add("missing_formula_execution_event")
            decision_path_valid = False
        elif executed_formula != prediction.formula_id:
            failures.add("formula_execution_mismatch")
            decision_path_valid = False

    receipt_failures = {
        "malformed_read_event",
        "no_verified_document_read",
        "observation_digest_mismatch",
        "unknown_document_read",
        "unsupported_trace_event",
    }
    receipt_valid = not failures.intersection(receipt_failures)
    components = (
        receipt_valid,
        retrieval_claim_valid,
        citation_path_valid,
        operand_path_valid,
        decision_path_valid,
    )
    answer_correct = score_case(case, prediction).correct
    labels = tuple(sorted(failures))
    return TraceAuditResult(
        case_id=case.case_id,
        passed=not labels,
        score=100.0 * sum(components) / len(components),
        answer_correct=answer_correct,
        receipt_valid=receipt_valid,
        retrieval_claim_valid=retrieval_claim_valid,
        citation_path_valid=citation_path_valid,
        operand_path_valid=operand_path_valid,
        decision_path_valid=decision_path_valid,
        verified_document_ids=tuple(verified_reads),
        failure_labels=labels,
    )


def audit_trace_run(
    cases: Iterable[BenchmarkCase],
    predictions: Iterable[Prediction],
    *,
    system_name: str,
) -> dict[str, Any]:
    """Audit exact case coverage and return a deterministic run artifact."""

    case_list = sorted(cases, key=lambda item: item.case_id)
    prediction_list = list(predictions)
    prediction_map = {item.case_id: item for item in prediction_list}
    if len(prediction_map) != len(prediction_list):
        raise ValueError("Trace audit received duplicate prediction case IDs")
    expected_ids = {item.case_id for item in case_list}
    if set(prediction_map) != expected_ids:
        missing = sorted(expected_ids - set(prediction_map))
        unknown = sorted(set(prediction_map) - expected_ids)
        raise ValueError(
            "Trace audit requires exactly one prediction per case "
            f"(missing={missing[:5]}, unknown={unknown[:5]})"
        )

    results = [audit_prediction_trace(case, prediction_map[case.case_id]) for case in case_list]
    failure_counts = Counter(label for result in results for label in result.failure_labels)
    passed = sum(result.passed for result in results)
    answer_correct = sum(result.answer_correct for result in results)
    correct_but_unverified = sum(
        result.answer_correct and not result.passed for result in results
    )
    return {
        "schema_version": "1.0",
        "audit_kind": "replayable_evidence_trace",
        "system_name": system_name,
        "claim_boundary": (
            "Verifies observable trace consistency against the supplied evidence world; "
            "does not reveal or prove hidden model reasoning."
        ),
        "dataset": {
            "case_count": len(case_list),
            "sha256": dataset_digest(case_list),
        },
        "metrics": {
            "answer_accuracy": answer_correct / len(results),
            "trace_pass_rate": passed / len(results),
            "mean_trace_score": sum(item.score for item in results) / len(results),
            "answer_correct_but_unverified_count": correct_but_unverified,
            "hard_gate_pass": passed == len(results),
        },
        "failure_counts": dict(sorted(failure_counts.items())),
        "results": [item.to_dict() for item in results],
    }


def render_trace_comparison(reports: Iterable[dict[str, Any]], output: str | Path) -> Path:
    """Render a dependency-free comparison artifact for sharing or client delivery."""

    values = list(reports)
    if not values:
        raise ValueError("At least one trace report is required")
    rows = []
    for report in values:
        metrics = report["metrics"]
        gate = "PASS" if metrics["hard_gate_pass"] else "BLOCKED"
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(str(report['system_name']))}</strong></td>"
            f"<td>{100 * float(metrics['answer_accuracy']):.1f}%</td>"
            f"<td>{100 * float(metrics['trace_pass_rate']):.1f}%</td>"
            f"<td>{int(metrics['answer_correct_but_unverified_count'])}</td>"
            f'<td><span class="gate {gate.lower()}">{gate}</span></td>'
            "</tr>"
        )
    embedded = (
        json.dumps(values, ensure_ascii=False, sort_keys=True)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>FinMirror Agent Trace Audit</title><style>
:root{{--ink:#102235;--muted:#5d6b79;--line:#d8e0e8;--cyan:#08a6a6;--navy:#071b2f;--paper:#f5f8fa}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1050px;margin:auto;padding:64px 24px}}.eyebrow{{color:var(--cyan);font-weight:800;letter-spacing:.12em;text-transform:uppercase}}
h1{{font-size:clamp(2.4rem,6vw,5rem);line-height:1.02;margin:.2em 0}}.lede{{font-size:1.25rem;max-width:760px;color:var(--muted)}}
.card{{background:white;border:1px solid var(--line);border-radius:18px;padding:24px;margin-top:32px;box-shadow:0 12px 40px #0a223611}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:16px;text-align:left;border-bottom:1px solid var(--line)}}th{{color:var(--muted);font-size:.8rem;text-transform:uppercase}}
.gate{{font-size:.75rem;font-weight:900;padding:6px 9px;border-radius:99px}}.pass{{background:#d9f6ec;color:#075d45}}.blocked{{background:#ffe1df;color:#94251f}}
.callout{{background:var(--navy);color:white;border-radius:18px;padding:24px;margin-top:24px}}code{{background:#e8eef2;padding:.15em .35em;border-radius:5px}}
small{{color:var(--muted)}}@media(max-width:700px){{.card{{overflow:auto}}th,td{{white-space:nowrap}}}}
</style></head><body><main>
<div class="eyebrow">FinMirror Agent Lab · deterministic replay</div>
<h1>Did the agent read what it cited?</h1>
<p class="lede">Final-answer accuracy cannot establish a valid evidence path. FinMirror replays content-addressed document-read receipts, then checks retrieval claims, citations, operands, and the terminal calculation or abstention.</p>
<section class="card"><table><thead><tr><th>System</th><th>Answer accuracy</th><th>Verified trace</th><th>Correct but unverified</th><th>Gate</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>
<section class="callout"><strong>Interpretation boundary.</strong> This audit verifies that an observable trajectory is consistent with the exact evidence world. It does not claim access to hidden chain-of-thought and does not prove that the model lacked another information channel.</section>
<p><small>Self-contained artifact · no telemetry · embedded machine-readable evidence</small></p>
<script type="application/json" id="finmirror-trace-reports">{embedded}</script>
</main></body></html>"""
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8", newline="\n")
    return destination
