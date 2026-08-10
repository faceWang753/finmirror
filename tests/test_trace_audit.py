"""Replayable agent-trace contract and CLI tests."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from finmirror.adapters.baselines import EvidenceProgramBaseline
from finmirror.cli import main
from finmirror.models import BenchmarkCase, Document, Prediction
from finmirror.trace_audit import (
    audit_prediction_trace,
    audit_trace_run,
    document_observation_sha256,
    render_trace_comparison,
)


def test_document_receipt_is_deterministic_and_binds_every_public_field() -> None:
    document = Document(
        id="doc-1",
        title="Quarterly filing",
        content="[E1] Revenue was 10.",
        source_url="https://example.test/filing",
        metadata={"period": "2026-Q1"},
    )
    assert document_observation_sha256(document) == document_observation_sha256(document)
    variants = (
        replace(document, id="doc-2"),
        replace(document, title="Annual filing"),
        replace(document, content="[E1] Revenue was 11."),
        replace(document, source_url="https://example.test/other"),
        replace(document, media_type="text/html"),
        replace(document, metadata={"period": "2026-Q2"}),
    )
    assert all(
        document_observation_sha256(item) != document_observation_sha256(document)
        for item in variants
    )


def test_evidence_program_has_fully_replayable_paths(
    cases: list[BenchmarkCase],
    evidence_program_predictions: list[Prediction],
) -> None:
    report = audit_trace_run(
        cases,
        evidence_program_predictions,
        system_name="evidence-program-with-receipts",
    )
    assert report["metrics"] == {
        "answer_accuracy": 1.0,
        "trace_pass_rate": 1.0,
        "mean_trace_score": 100.0,
        "answer_correct_but_unverified_count": 0,
        "hard_gate_pass": True,
    }
    assert report["failure_counts"] == {}
    assert all(item["passed"] for item in report["results"])


def test_identical_correct_outputs_fail_without_receipts(
    cases: list[BenchmarkCase],
    evidence_program_predictions: list[Prediction],
) -> None:
    unverified = [replace(item, trace=()) for item in evidence_program_predictions]
    report = audit_trace_run(cases, unverified, system_name="identical-output")
    assert report["metrics"]["answer_accuracy"] == 1.0
    assert report["metrics"]["trace_pass_rate"] == 0.0
    assert report["metrics"]["answer_correct_but_unverified_count"] == len(cases)
    assert report["metrics"]["hard_gate_pass"] is False
    assert report["failure_counts"]["no_verified_document_read"] == len(cases)


def test_digest_tampering_fails_closed(cases: list[BenchmarkCase]) -> None:
    case = cases[0]
    prediction = EvidenceProgramBaseline().generate(case.prompt_case())
    event = dict(prediction.trace[0])
    event["observation_sha256"] = "0" * 64
    tampered = replace(prediction, trace=(event, *prediction.trace[1:]))
    result = audit_prediction_trace(case, tampered)
    assert result.passed is False
    assert "observation_digest_mismatch" in result.failure_labels
    assert "no_verified_document_read" in result.failure_labels


def test_trace_audit_requires_exact_case_coverage(
    cases: list[BenchmarkCase],
    evidence_program_predictions: list[Prediction],
) -> None:
    try:
        audit_trace_run(cases, evidence_program_predictions[:-1], system_name="partial")
    except ValueError as exc:
        assert "exactly one prediction per case" in str(exc)
    else:
        raise AssertionError("partial trace run should fail closed")


def test_trace_demo_cli_writes_reproducible_comparison(
    tmp_path: Path,
    capsys: Any,
) -> None:
    dataset = tmp_path / "benchmark"
    output = tmp_path / "trace-demo"
    assert main(["trace-demo", "--dataset", str(dataset), "--out", str(output)]) == 0
    assert "100.0% vs 0.0% verified paths" in capsys.readouterr().out
    verified = json.loads(
        (output / "verified" / "trace-report.json").read_text(encoding="utf-8")
    )
    unverified = json.loads(
        (output / "unverified" / "trace-report.json").read_text(encoding="utf-8")
    )
    assert verified["metrics"]["hard_gate_pass"] is True
    assert unverified["metrics"]["hard_gate_pass"] is False
    page = (output / "index.html").read_text(encoding="utf-8")
    assert "Did the agent read what it cited?" in page
    assert "identical-output-without-receipts" in page

    snapshot_paths = (
        output / "index.html",
        output / "verified" / "predictions.jsonl",
        output / "verified" / "trace-report.json",
        output / "unverified" / "predictions.jsonl",
        output / "unverified" / "trace-report.json",
    )
    first_snapshot = {path: path.read_bytes() for path in snapshot_paths}

    assert main(["trace-demo", "--dataset", str(dataset), "--out", str(output)]) == 0
    assert {path: path.read_bytes() for path in snapshot_paths} == first_snapshot


def test_trace_report_escapes_system_names(
    tmp_path: Path,
    cases: list[BenchmarkCase],
    evidence_program_predictions: list[Prediction],
) -> None:
    report = audit_trace_run(
        cases,
        evidence_program_predictions,
        system_name='agent</script><script>alert("x")</script>',
    )
    output = render_trace_comparison((report,), tmp_path / "trace.html")
    page = output.read_text(encoding="utf-8")
    assert '<script>alert("x")</script>' not in page
    assert "agent&lt;/script&gt;" in page
    match = re.search(
        r'<script type="application/json" id="finmirror-trace-reports">(.*)</script>',
        page,
    )
    assert match is not None
    embedded = json.loads(match.group(1))
    assert embedded[0]["system_name"] == report["system_name"]


def test_trace_report_matches_committed_schema(
    cases: list[BenchmarkCase],
    evidence_program_predictions: list[Prediction],
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (project_root / "schema" / "trace-audit-report.schema.json").read_text(encoding="utf-8")
    )
    report = audit_trace_run(
        cases,
        evidence_program_predictions,
        system_name="schema-test",
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)
