"""Standalone report rendering and injection-safety tests."""

from __future__ import annotations

import re

from finmirror.report import render_comparison, render_report


def test_report_is_a_self_contained_offline_artifact(tmp_path, oracle_report) -> None:
    output = render_report(oracle_report, tmp_path / "nested" / "report.html")
    document = output.read_text(encoding="utf-8")
    assert output.exists()
    assert "<!doctype html>" in document.lower()
    assert "harness-oracle" in document
    assert "126 cases" in document
    assert "108 paired interventions" in document
    assert 'id="report-data"' in document
    assert 'id="rows"' in document
    assert re.search(r"<script[^>]+\bsrc\s*=", document, re.IGNORECASE) is None
    assert re.search(r"<link[^>]+\bhref\s*=", document, re.IGNORECASE) is None
    assert (
        re.search(
            r"(?:src|href)\s*=\s*[\"'](?:https?:)?//",
            document,
            re.IGNORECASE,
        )
        is None
    )


def test_report_escapes_html_and_script_termination(tmp_path, oracle_report) -> None:
    hostile = dict(oracle_report)
    hostile["system"] = {
        "name": "</script><script src='https://attacker.invalid/x.js'>",
        "version": "test",
    }
    output = render_report(hostile, tmp_path / "hostile.html")
    document = output.read_text(encoding="utf-8")
    assert "</script><script src=" not in document
    assert "&lt;/script&gt;&lt;script" in document
    assert "<\\/script>" in document


def test_comparison_orders_by_audit_score_and_has_no_external_assets(
    tmp_path,
    oracle_report,
    memorized_report,
) -> None:
    output = render_comparison(
        [memorized_report, oracle_report],
        tmp_path / "comparison.html",
    )
    document = output.read_text(encoding="utf-8")
    assert document.index("harness-oracle") < document.index("memorized-evidence-blind")
    assert "PASS" in document
    assert "BLOCKED" in document
    assert "http://" not in document
    assert "https://" not in document
