"""CI summaries expose the strict gate without overstating the benchmark."""

from __future__ import annotations

from finmirror.adapters.base import run_adapter
from finmirror.adapters.baselines import MemorizedBaseline, OracleAdapter
from finmirror.ci import render_ci_summary, write_ci_artifacts
from finmirror.evaluator import evaluate


def test_blocked_summary_is_reviewable_and_bounded(cases) -> None:
    predictions = run_adapter(MemorizedBaseline(), cases)
    report = evaluate(cases, predictions, system_name="evidence|blind\nsystem")

    summary = render_ci_summary(report)

    assert "FinMirror gate: BLOCKED" in summary
    assert "evidence\\|blind system" in summary
    assert "Strict pair reliability | 0.0%" in summary
    assert "not a production-safety" in summary
    assert "`incorrect_operand_provenance`" in summary


def test_ci_artifacts_append_machine_outputs(tmp_path, cases) -> None:
    adapter = OracleAdapter(cases)
    predictions = run_adapter(adapter, cases)
    report = evaluate(cases, predictions, system_name="oracle")
    summary = tmp_path / "summary" / "finmirror.md"
    outputs = tmp_path / "github-output.txt"
    outputs.write_text("existing=value\n", encoding="utf-8")

    write_ci_artifacts(report, summary_path=summary, outputs_path=outputs)

    assert "FinMirror gate: PASS" in summary.read_text(encoding="utf-8")
    output_text = outputs.read_text(encoding="utf-8")
    assert output_text.startswith("existing=value\n")
    assert "gate=PASS\n" in output_text
    assert "audit_score=100.0\n" in output_text
    assert "pair_reliability=1.000000\n" in output_text
