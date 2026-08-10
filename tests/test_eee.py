"""Contract tests for the Every Eval Ever 0.3.0 exporter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from finmirror.cli import main
from finmirror.eee import EEEModelSpec, export_eee
from finmirror.generator import generate_benchmark
from finmirror.training import save_predictions

FILE_UUID = "f3a1c0de-4b2e-4c1a-9f6d-1b7e5a2c8d40"


def _model() -> EEEModelSpec:
    return EEEModelSpec(
        model_id="finmirror/evidence-program",
        name="evidence-program",
        developer="finmirror",
        evaluator_relationship="first_party",
        deployment_type="self_deployed",
        model_availability="unknown",
        inference_engine="finmirror",
        inference_engine_version="0.1",
    )


def _schema(name: str) -> dict[str, object]:
    path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "finmirror"
        / "schemas"
        / "eee_v0_3_0"
        / name
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_export_is_schema_valid_and_hash_bound(
    tmp_path,
    cases,
    evidence_program_predictions,
    evidence_program_report,
) -> None:
    exported = export_eee(
        report=evidence_program_report,
        cases=cases,
        predictions=evidence_program_predictions,
        model=_model(),
        output_root=tmp_path,
        source_revision="3db16674",
        file_uuid=FILE_UUID,
        retrieved_timestamp="1750000001",
    )
    aggregate = json.loads(exported.aggregate_path.read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in exported.samples_path.read_text(encoding="utf-8").splitlines()
    ]

    Draft202012Validator(_schema("eval.schema.json")).validate(aggregate)
    row_validator = Draft202012Validator(_schema("instance_level_eval.schema.json"))
    for row in rows:
        row_validator.validate(row)

    assert exported.sample_count == 738
    assert aggregate["schema_version"] == "0.3.0"
    assert aggregate["evaluation_id"] == exported.evaluation_id
    assert aggregate["model_info"]["additional_details"]["canonical_id_status"] == (
        "unverified"
    )
    assert aggregate["source_metadata"]["source_type"] == "evaluation_run"
    assert aggregate["detailed_evaluation_results"]["file_path"] == (
        f"data/finmirror-v0.1/finmirror/evidence-program/{FILE_UUID}_samples.jsonl"
    )
    assert (
        aggregate["detailed_evaluation_results"]["checksum"]
        == hashlib.sha256(exported.samples_path.read_bytes()).hexdigest()
    )
    assert {row["evaluation_id"] for row in rows} == {exported.evaluation_id}
    assert {row["model_id"] for row in rows} == {"finmirror/evidence-program"}
    assert all(row["input"]["raw"] not in row["output"]["raw"] for row in rows)
    assert all(
        set(row["answer_attribution"][0])
        == {
            "turn_idx",
            "source",
            "extracted_value",
            "extraction_method",
            "is_terminal",
        }
        for row in rows
    )


def test_export_refuses_gold_aware_oracle(
    tmp_path,
    cases,
    oracle_predictions,
    oracle_report,
) -> None:
    with pytest.raises(ValueError, match="gold-aware"):
        export_eee(
            report={**oracle_report, "run_metadata": {"adapter_uses_gold": True}},
            cases=cases,
            predictions=oracle_predictions,
            model=_model(),
            output_root=tmp_path,
            file_uuid=FILE_UUID,
            retrieved_timestamp="1750000001",
        )
    assert not list(tmp_path.rglob("*"))


def test_export_refuses_dataset_and_prediction_mismatch(
    tmp_path,
    cases,
    evidence_program_predictions,
    evidence_program_report,
) -> None:
    with pytest.raises(ValueError, match="exactly one row"):
        export_eee(
            report=evidence_program_report,
            cases=cases,
            predictions=evidence_program_predictions[:-1],
            model=_model(),
            output_root=tmp_path,
            file_uuid=FILE_UUID,
            retrieved_timestamp="1750000001",
        )


def test_export_never_overwrites_existing_artifacts(
    tmp_path,
    cases,
    evidence_program_predictions,
    evidence_program_report,
) -> None:
    kwargs = {
        "report": evidence_program_report,
        "cases": cases,
        "predictions": evidence_program_predictions,
        "model": _model(),
        "output_root": tmp_path,
        "file_uuid": FILE_UUID,
        "retrieved_timestamp": "1750000001",
    }
    first = export_eee(**kwargs)
    before = first.aggregate_path.read_bytes()
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        export_eee(**kwargs)
    assert first.aggregate_path.read_bytes() == before


def test_model_identity_and_inference_provenance_are_strict() -> None:
    with pytest.raises(ValueError, match="prefix"):
        EEEModelSpec(
            model_id="cohere/command-a",
            name="command-a",
            developer="other",
            evaluator_relationship="third_party",
            deployment_type="externally_managed",
            model_availability="closed_weights",
        ).validate()
    with pytest.raises(ValueError, match="not both"):
        EEEModelSpec(
            model_id="cohere/command-a",
            name="command-a",
            developer="cohere",
            evaluator_relationship="third_party",
            deployment_type="externally_managed",
            model_availability="closed_weights",
            inference_platform="Cohere API",
            inference_engine="vLLM",
        ).validate()


def test_export_eee_cli_publishes_and_reports_overwrite_error(
    tmp_path,
    capsys,
    evidence_program_predictions,
    evidence_program_report,
) -> None:
    dataset = tmp_path / "benchmark"
    generate_benchmark(dataset)
    predictions = save_predictions(evidence_program_predictions, tmp_path / "predictions.jsonl")
    report = tmp_path / "report.json"
    report.write_text(json.dumps(evidence_program_report), encoding="utf-8")
    output = tmp_path / "eee"
    args = [
        "export-eee",
        "--dataset",
        str(dataset),
        "--report",
        str(report),
        "--predictions",
        str(predictions),
        "--model-id",
        "finmirror/evidence-program",
        "--model-name",
        "evidence-program",
        "--developer",
        "finmirror",
        "--evaluator-relationship",
        "first_party",
        "--deployment-type",
        "self_deployed",
        "--model-availability",
        "unknown",
        "--inference-engine",
        "finmirror",
        "--inference-engine-version",
        "0.1",
        "--file-uuid",
        FILE_UUID,
        "--retrieved-timestamp",
        "1750000001",
        "--out",
        str(output),
    ]
    assert main(args) == 0
    captured = capsys.readouterr()
    assert "EEE 0.3.0 VALID" in captured.out
    assert "738 sample-metric rows" in captured.out

    assert main(args) == 1
    captured = capsys.readouterr()
    assert "refusing to overwrite" in captured.err
    assert "Traceback" not in captured.err
