"""Checklist decomposition and learned-verifier meta-evaluation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from finmirror.cli import main
from finmirror.judge_audit import (
    audit_judge_payload,
    build_judge_demo,
    dump_demo_inputs,
    render_judge_comparison,
)


def test_positive_and_negative_controls_isolate_failure_surfaces() -> None:
    calibrated, permissive, collapsed = build_judge_demo()
    assert calibrated["metrics"]["hard_gate_pass"] is True
    assert calibrated["metrics"]["atomic_checklist_rate"] == 1.0
    assert calibrated["metrics"]["false_pass_rate"] == 0.0
    assert calibrated["metrics"]["metamorphic_pass_rate"] == 1.0

    assert permissive["metrics"]["atomic_checklist_rate"] == 1.0
    assert permissive["metrics"]["false_pass_rate"] == 1.0
    assert permissive["metrics"]["hard_gate_pass"] is False

    assert collapsed["metrics"]["exact_coverage_rate"] == 1.0
    assert collapsed["metrics"]["atomic_checklist_rate"] == 0.0
    assert collapsed["metrics"]["hard_gate_pass"] is False


def test_atomic_omission_requires_local_probability_and_reward_change() -> None:
    calibrated = build_judge_demo()[0]
    omission = next(
        item for item in calibrated["pairs"] if item["relation"] == "atomic_omission"
    )
    assert omission["changed_requirements"] == ["grounded_citation"]
    assert omission["probability_deltas"]["grounded_citation"] == pytest.approx(-0.94)
    assert omission["reward_delta"] == pytest.approx(-0.235)
    assert all(omission["checks"].values())
    assert omission["passed"] is True


def test_invariant_relations_are_order_and_context_stable() -> None:
    calibrated = build_judge_demo()[0]
    invariant_pairs = [
        item
        for item in calibrated["pairs"]
        if item["relation"] in {"irrelevant_context", "reorder"}
    ]
    assert len(invariant_pairs) == 2
    assert all(item["reward_delta"] == 0.0 for item in invariant_pairs)
    assert all(item["passed"] for item in invariant_pairs)


def test_report_is_byte_reproducible() -> None:
    assert build_judge_demo() == build_judge_demo()


def test_committed_schemas_validate_demo_inputs_and_reports() -> None:
    project_root = Path(__file__).resolve().parents[1]
    input_schema = json.loads(
        (project_root / "schema" / "judge-audit-input.schema.json").read_text(encoding="utf-8")
    )
    report_schema = json.loads(
        (project_root / "schema" / "judge-audit-report.schema.json").read_text(encoding="utf-8")
    )
    demo_input = json.loads(
        (
            project_root
            / "artifacts"
            / "demo"
            / "judge"
            / "inputs"
            / "atomic-calibrated-verifier-input.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(input_schema).validate(demo_input)
    for report in build_judge_demo():
        Draft202012Validator(report_schema).validate(report)


def test_duplicate_checklist_item_ids_fail_the_structure_gate(tmp_path) -> None:
    payload_path = dump_demo_inputs(tmp_path)[0]
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    checklist = payload["scenarios"][0]["checklist"]
    checklist[1]["item_id"] = checklist[0]["item_id"]

    report = audit_judge_payload(payload)

    assert report["scenarios"][0]["checks"]["unique_checklist_items"] is False
    assert report["hard_gate_checks"]["all_checklists_exact_atomic_nonoverlapping"] is False
    assert report["metrics"]["hard_gate_pass"] is False


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda value: value.update(schema_version="2.0"), "schema_version"),
        (lambda value: value["scenarios"].clear(), "cannot be empty"),
        (
            lambda value: value["scenarios"].append(value["scenarios"][0]),
            "must be unique",
        ),
    ],
)
def test_strict_input_contract_rejects_ambiguous_payloads(mutation, match) -> None:
    payload = {
        "schema_version": "1.0",
        "system_name": "candidate",
        "scenarios": [
            {
                "scenario_id": "reference",
                "relation": "reference",
                "reference_scenario_id": None,
                "requirements": [{"requirement_id": "a", "satisfied": True}],
                "checklist": [{"item_id": "a", "covers": ["a"], "probability": 0.9}],
            },
            {
                "scenario_id": "invariant",
                "relation": "irrelevant_context",
                "reference_scenario_id": "reference",
                "requirements": [{"requirement_id": "a", "satisfied": True}],
                "checklist": [{"item_id": "a", "covers": ["a"], "probability": 0.9}],
            },
        ],
    }
    mutation(payload)
    with pytest.raises(ValueError, match=match):
        audit_judge_payload(payload)


def test_html_report_is_standalone_and_escapes_names(tmp_path) -> None:
    reports = list(build_judge_demo())
    reports[0] = {**reports[0], "system_name": "<script>alert(1)</script>"}
    output = render_judge_comparison(tuple(reports), tmp_path / "index.html")
    document = output.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in document
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in document
    assert "https://" not in document
    assert "finmirror judge-demo" in document


def test_judge_demo_cli_writes_replayable_artifacts(tmp_path, capsys) -> None:
    status = main(["judge-demo", "--out", str(tmp_path)])
    captured = capsys.readouterr()
    assert status == 0
    assert "1/3 controls pass" in captured.out
    assert (tmp_path / "index.html").exists()
    report = json.loads(
        (tmp_path / "atomic-calibrated-verifier" / "report.json").read_text(encoding="utf-8")
    )
    assert report["metrics"]["hard_gate_pass"] is True


def test_judge_audit_cli_returns_blocked_status_for_bad_verifier(tmp_path, capsys) -> None:
    payload_path = tmp_path / "input.json"
    payload_path.write_text((tmp_path / "seed").as_posix(), encoding="utf-8")
    # Reuse the exact committed demo input rather than duplicating the contract here.
    main(["judge-demo", "--out", str(tmp_path / "demo")])
    payload_path = tmp_path / "demo" / "inputs" / "atomic-permissive-verifier-input.json"
    status = main(
        ["judge-audit", "--input", str(payload_path), "--out", str(tmp_path / "audit")]
    )
    captured = capsys.readouterr()
    assert status == 2
    assert "BLOCKED" in captured.out
    assert (tmp_path / "audit" / "report.json").exists()
