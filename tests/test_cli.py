"""CLI contract tests using real generated datasets and artifacts."""

from __future__ import annotations

import json

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
