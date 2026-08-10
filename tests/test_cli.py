"""CLI contract tests using real generated datasets and artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from finmirror.cli import main
from finmirror.generator import generate_benchmark
from finmirror.training import save_predictions


def test_generate_then_validate(tmp_path, capsys) -> None:
    dataset = tmp_path / "benchmark"
    assert main(["generate", "--out", str(dataset)]) == 0
    generated = capsys.readouterr()
    assert "Generated 126 cases" in generated.out
    assert (dataset / "cases.jsonl").exists()
    assert (dataset / "manifest.json").exists()

    assert main(["validate", str(dataset)]) == 0
    validated = capsys.readouterr()
    assert "VALID" in validated.out
    assert "126 cases" in validated.out
    assert "18 groups" in validated.out


def test_zero_key_demo_writes_both_reports_and_comparison(tmp_path, capsys) -> None:
    dataset = tmp_path / "benchmark"
    output = tmp_path / "demo"
    assert main(["demo", "--dataset", str(dataset), "--out", str(output)]) == 0
    captured = capsys.readouterr()
    assert "Demo complete" in captured.out

    expected_files = (
        output / "index.html",
        output / "oracle" / "predictions.jsonl",
        output / "oracle" / "report.json",
        output / "oracle" / "report.html",
        output / "evidence-program" / "predictions.jsonl",
        output / "evidence-program" / "report.json",
        output / "evidence-program" / "report.html",
        output / "memorized" / "predictions.jsonl",
        output / "memorized" / "report.json",
        output / "memorized" / "report.html",
    )
    assert all(path.exists() for path in expected_files)
    comparison = (output / "index.html").read_text(encoding="utf-8")
    assert 'href="evidence-program/report.html"' in comparison
    assert 'href="memorized/report.html"' in comparison
    oracle = json.loads((output / "oracle" / "report.json").read_text(encoding="utf-8"))
    memorized = json.loads((output / "memorized" / "report.json").read_text(encoding="utf-8"))
    evidence = json.loads(
        (output / "evidence-program" / "report.json").read_text(encoding="utf-8")
    )
    assert oracle["metrics"]["hard_gate_pass"] is True
    assert oracle["dataset"]["pair_count"] == 108
    assert evidence["metrics"]["hard_gate_pass"] is True
    assert evidence["run_metadata"]["adapter_uses_gold"] is False
    assert memorized["metrics"]["hard_gate_pass"] is False
    assert memorized["by_transform"]["entity_collision"]["pass_rate"] == 0.0
    assert evidence["created_at"] == "2026-07-26T00:00:00+00:00"
    assert evidence["metrics"]["mean_latency_ms"] == 0.0

    first_snapshot = {path: path.read_bytes() for path in expected_files}
    assert main(["demo", "--dataset", str(dataset), "--out", str(output)]) == 0
    assert {path: path.read_bytes() for path in expected_files} == first_snapshot


def test_filtered_oracle_run_keeps_complete_pair_group(tmp_path, capsys) -> None:
    dataset = tmp_path / "benchmark"
    output = tmp_path / "run"
    generate_benchmark(dataset)
    status = main(
        [
            "run",
            "--dataset",
            str(dataset),
            "--adapter",
            "oracle",
            "--languages",
            "en",
            "--scenarios",
            "revenue_growth",
            "--out",
            str(output),
        ]
    )
    assert status == 0
    assert "gate PASS" in capsys.readouterr().out
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["dataset"]["case_count"] == 7
    assert report["dataset"]["pair_count"] == 6


def test_memorized_run_returns_blocked_exit_status(tmp_path, capsys) -> None:
    dataset = tmp_path / "benchmark"
    output = tmp_path / "run"
    generate_benchmark(dataset)
    status = main(
        [
            "run",
            "--dataset",
            str(dataset),
            "--adapter",
            "memorized",
            "--languages",
            "en",
            "--scenarios",
            "revenue_growth",
            "--out",
            str(output),
        ]
    )
    assert status == 2
    assert "gate BLOCKED" in capsys.readouterr().out


def test_score_and_rerender_existing_oracle_submission(
    tmp_path,
    capsys,
    cases,
    oracle_predictions,
) -> None:
    dataset = tmp_path / "benchmark"
    generate_benchmark(dataset)
    predictions = save_predictions(oracle_predictions, tmp_path / "oracle.jsonl")
    output = tmp_path / "scored"
    assert (
        main(
            [
                "score",
                "--dataset",
                str(dataset),
                "--predictions",
                str(predictions),
                "--system",
                "submission",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    assert "gate PASS" in capsys.readouterr().out

    rerendered = tmp_path / "rerendered.html"
    assert (
        main(
            [
                "report",
                str(output / "report.json"),
                "--out",
                str(rerendered),
            ]
        )
        == 0
    )
    assert rerendered.exists()
    assert "Wrote" in capsys.readouterr().out

    summary = tmp_path / "finmirror-summary.md"
    github_output = tmp_path / "github-output.txt"
    assert (
        main(
            [
                "ci-summary",
                "--report",
                str(output / "report.json"),
                "--summary-out",
                str(summary),
                "--github-output",
                str(github_output),
            ]
        )
        == 0
    )
    assert "FinMirror gate: PASS" in summary.read_text(encoding="utf-8")
    assert "gate=PASS" in github_output.read_text(encoding="utf-8")
    assert "Wrote CI summary" in capsys.readouterr().out


def test_cli_reports_invalid_filter_without_traceback(tmp_path, capsys) -> None:
    dataset = tmp_path / "benchmark"
    generate_benchmark(dataset)
    status = main(
        [
            "run",
            "--dataset",
            str(dataset),
            "--adapter",
            "oracle",
            "--languages",
            "de",
        ]
    )
    captured = capsys.readouterr()
    assert status == 1
    assert "Filters selected zero cases" in captured.err
    assert "Traceback" not in captured.err


def test_evidence_status_reports_release_ready_source_material(capsys) -> None:
    project_root = Path(__file__).resolve().parents[1]
    status = main(
        [
            "evidence-status",
            "--ledger",
            str(project_root / "sources" / "v0.2" / "ledger.jsonl"),
            "--manifest",
            str(project_root / "sources" / "v0.2" / "evidence-manifest.json"),
            "--root",
            str(project_root),
        ]
    )
    captured = capsys.readouterr()
    assert status == 0
    assert "RELEASE_READY_SOURCE_MATERIAL" in captured.out
    assert '"synthetic": 1' in captured.out
    assert '"source_derived": 2' in captured.out


def test_evidence_status_accepts_hash_bound_real_source_material(capsys) -> None:
    project_root = Path(__file__).resolve().parents[1]
    status = main(
        [
            "evidence-status",
            "--ledger",
            str(project_root / "sources" / "v0.2" / "ledger.jsonl"),
            "--manifest",
            str(project_root / "sources" / "v0.2" / "evidence-manifest.json"),
            "--root",
            str(project_root),
            "--require-real-source",
        ]
    )
    captured = capsys.readouterr()
    assert status == 0
    assert "RELEASE_READY_SOURCE_MATERIAL" in captured.out
    assert captured.err == ""


def test_review_status_reports_and_blocks_pending_external_review(capsys) -> None:
    project_root = Path(__file__).resolve().parents[1]
    status_path = (
        project_root
        / "sources"
        / "v0.2"
        / "calibration"
        / "statcan-gdp-2025q2-q3"
        / "review-status.json"
    )
    status = main(["review-status", "--status", str(status_path)])
    captured = capsys.readouterr()
    assert status == 0
    assert "PENDING_EXTERNAL_REVIEW" in captured.out
    assert "7 cases" in captured.out

    blocked = main(
        [
            "review-status",
            "--status",
            str(status_path),
            "--require-expert-validated",
        ]
    )
    captured = capsys.readouterr()
    assert blocked == 1
    assert "expert-validation claim blocked" in captured.err
    assert "Traceback" not in captured.err


def test_validate_review_cli_accepts_a_complete_digest_bound_export(tmp_path, capsys) -> None:
    project_root = Path(__file__).resolve().parents[1]
    status_path = (
        project_root
        / "sources"
        / "v0.2"
        / "calibration"
        / "statcan-gdp-2025q2-q3"
        / "review-status.json"
    )
    review_status = json.loads(status_path.read_text(encoding="utf-8"))
    rows = []
    for case_id in review_status["case_ids"]:
        rows.append(
            {
                "schema_version": "1.0",
                "pilot_id": review_status["pilot_id"],
                "dataset_sha256": review_status["dataset_sha256"],
                "reviewer_id": "reviewer-alpha",
                "role": "independent_annotator",
                "blinded": True,
                "conflict_disclosure": "none known",
                "submitted_at": "2026-08-06T12:34:56.789Z",
                "case_id": case_id,
                "answerable": "uncertain",
                "relation": "uncertain",
                "material": "uncertain",
                "evidence_complete": "uncertain",
                "formula_correct": "uncertain",
                "evidence_anchors": [],
                "computed_value": "",
                "notes": "test fixture",
            }
        )
    submission = tmp_path / "review.jsonl"
    submission.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    result = main(
        [
            "validate-review",
            "--submission",
            str(submission),
            "--status",
            str(status_path),
        ]
    )
    captured = capsys.readouterr()
    assert result == 0
    assert "VALID BLIND REVIEW" in captured.out
    assert "7 cases" in captured.out
