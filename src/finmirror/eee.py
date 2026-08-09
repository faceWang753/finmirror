"""Strict Every Eval Ever 0.3.0 export for FinMirror evaluation runs."""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from finmirror import __version__
from finmirror.adapters.structured import build_financial_prompt
from finmirror.dataset import dataset_digest
from finmirror.models import BenchmarkCase, Prediction

EEE_SCHEMA_VERSION = "0.3.0"
EEE_COLLECTION = "finmirror-v0.1"
EEE_UPSTREAM_COMMIT = "252f79668110c5d4b9a7b0fda4450bb4f1ec048b"
FINMIRROR_DATASET_URL = "https://huggingface.co/datasets/mingyang233/FinMirror"
FINMIRROR_REPOSITORY_URL = "https://github.com/faceWang753/finmirror"

EvaluatorRelationship = Literal["first_party", "third_party", "collaborative", "other"]
DeploymentType = Literal["self_deployed", "externally_managed", "unknown"]
ModelAvailability = Literal["open_weights", "closed_weights", "unknown"]

_PATH_INVALID = re.compile(r'[<>:"\\|?*\x00-\x1f]')
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


@dataclass(frozen=True)
class EEEModelSpec:
    """Model identity and provenance required by the EEE datastore."""

    model_id: str
    name: str
    developer: str
    evaluator_relationship: EvaluatorRelationship
    deployment_type: DeploymentType
    model_availability: ModelAvailability
    inference_platform: str = ""
    inference_engine: str = ""
    inference_engine_version: str = ""

    def validate(self) -> None:
        _required_identity(self.model_id, "model_id")
        _required_identity(self.name, "model name")
        _required_identity(self.developer, "model developer")
        if "/" not in self.model_id:
            raise ValueError("model_id must use the canonical developer/model form")
        if self.model_id.split("/", 1)[0] != self.developer:
            raise ValueError("model_id prefix must exactly match model developer")
        if self.evaluator_relationship not in {
            "first_party",
            "third_party",
            "collaborative",
            "other",
        }:
            raise ValueError("invalid evaluator_relationship")
        if self.deployment_type not in {
            "self_deployed",
            "externally_managed",
            "unknown",
        }:
            raise ValueError("invalid deployment_type")
        if self.model_availability not in {
            "open_weights",
            "closed_weights",
            "unknown",
        }:
            raise ValueError("invalid model_availability")
        if self.inference_platform and self.inference_engine:
            raise ValueError(
                "report inference_platform or inference_engine, not both; do not guess"
            )
        if self.inference_engine_version and not self.inference_engine:
            raise ValueError("inference_engine_version requires inference_engine")


@dataclass(frozen=True)
class EEEExport:
    """Paths and stable identifiers produced by one successful export."""

    aggregate_path: Path
    samples_path: Path
    evaluation_id: str
    sample_count: int


@dataclass(frozen=True)
class _Metric:
    key: str
    result_id: str
    name: str
    description: str
    unit: str
    minimum: float
    maximum: float
    sample_kind: Literal["none", "case", "pair"]
    sample_field: str = ""


_METRICS = (
    _Metric(
        "audit_score",
        "finmirror.audit-score",
        "FinMirror audit score",
        "Hard-gated composite reliability score; a diagnostic summary, not accuracy.",
        "points",
        0.0,
        100.0,
        "none",
    ),
    _Metric(
        "case_accuracy",
        "finmirror.case-accuracy",
        "FinMirror case accuracy",
        "Proportion of cases with a correct answer or correct abstention.",
        "proportion",
        0.0,
        1.0,
        "case",
        "correct",
    ),
    _Metric(
        "case_verification",
        "finmirror.case-verification",
        "FinMirror case verification",
        "Proportion of cases passing answer, evidence, formula, and contract verification.",
        "proportion",
        0.0,
        1.0,
        "case",
        "verified",
    ),
    _Metric(
        "citation_f1",
        "finmirror.citation-f1",
        "FinMirror citation F1",
        "F1 over exact evidence anchors required for the answer.",
        "proportion",
        0.0,
        1.0,
        "case",
        "citation_f1",
    ),
    _Metric(
        "formula_replay",
        "finmirror.formula-replay",
        "FinMirror formula replay",
        "Proportion of cases whose declared formula deterministically replays.",
        "proportion",
        0.0,
        1.0,
        "case",
        "formula_score",
    ),
    _Metric(
        "abstention_accuracy",
        "finmirror.abstention-accuracy",
        "FinMirror abstention accuracy",
        "Correct answer-versus-abstain behavior under evidence sufficiency changes.",
        "proportion",
        0.0,
        1.0,
        "case",
        "abstention_score",
    ),
    _Metric(
        "pair_reliability",
        "finmirror.pair-reliability",
        "FinMirror paired reliability",
        "Reliability across paired counterfactual evidence interventions.",
        "proportion",
        0.0,
        1.0,
        "pair",
        "score",
    ),
)


def export_eee(
    *,
    report: dict[str, Any],
    cases: list[BenchmarkCase],
    predictions: list[Prediction],
    model: EEEModelSpec,
    output_root: str | Path,
    source_url: str = FINMIRROR_DATASET_URL,
    source_revision: str = "",
    file_uuid: str | None = None,
    retrieved_timestamp: str | None = None,
) -> EEEExport:
    """Build, validate, and failure-safely publish one EEE 0.3.0 export.

    The function is intentionally strict: it rejects gold-aware runs, mismatched
    datasets or predictions, non-finite scores, unsafe paths, and overwrites.
    """

    model.validate()
    _validate_report(report, cases, predictions)
    if not source_url.strip():
        raise ValueError("source_url is required; do not invent dataset provenance")

    selected_uuid = _require_uuid4(file_uuid or str(uuid.uuid4()))
    evaluation_timestamp = _epoch_timestamp(report["created_at"], "report.created_at")
    retrieved = _epoch_timestamp(
        retrieved_timestamp
        or str(int(datetime.now(tz=timezone.utc).timestamp())),
        "retrieved_timestamp",
    )
    model_token = model.model_id.replace("/", "_")
    evaluation_id = f"{EEE_COLLECTION}/{model_token}/{evaluation_timestamp}"

    collection, developer_component, model_component = _datastore_components(
        EEE_COLLECTION, model.model_id, model.developer
    )
    filename = f"{selected_uuid}.json"
    samples_filename = f"{selected_uuid}_samples.jsonl"
    repo_samples_path = PurePosixPath(
        "data", collection, developer_component, model_component, samples_filename
    ).as_posix()

    prediction_by_id = {item.case_id: item for item in predictions}
    case_by_id = {item.case_id: item for item in cases}
    report_case_by_id = {str(item["case_id"]): item for item in report["cases"]}
    sample_rows = _sample_rows(
        report,
        case_by_id,
        prediction_by_id,
        report_case_by_id,
        model.model_id,
        evaluation_id,
    )
    samples_bytes = (
        "\n".join(_compact_json(item) for item in sample_rows) + "\n"
    ).encode("utf-8")
    checksum = hashlib.sha256(samples_bytes).hexdigest()
    aggregate = _aggregate_record(
        report=report,
        model=model,
        source_url=source_url.strip(),
        source_revision=source_revision.strip(),
        evaluation_id=evaluation_id,
        evaluation_timestamp=evaluation_timestamp,
        retrieved_timestamp=retrieved,
        samples_path=repo_samples_path,
        samples_checksum=checksum,
        sample_count=len(sample_rows),
    )

    _validate_export_semantics(aggregate, sample_rows)
    aggregate_bytes = (
        json.dumps(
            aggregate,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")

    destination = (
        Path(output_root) / "data" / collection / developer_component / model_component
    )
    aggregate_path = destination / filename
    samples_path = destination / samples_filename
    _publish_atomically(
        ((samples_path, samples_bytes), (aggregate_path, aggregate_bytes))
    )
    return EEEExport(
        aggregate_path=aggregate_path,
        samples_path=samples_path,
        evaluation_id=evaluation_id,
        sample_count=len(sample_rows),
    )


def _aggregate_record(
    *,
    report: dict[str, Any],
    model: EEEModelSpec,
    source_url: str,
    source_revision: str,
    evaluation_id: str,
    evaluation_timestamp: str,
    retrieved_timestamp: str,
    samples_path: str,
    samples_checksum: str,
    sample_count: int,
) -> dict[str, Any]:
    dataset_sha = str(report["dataset"]["sha256"])
    model_info: dict[str, Any] = {
        "name": model.name,
        "id": model.model_id,
        "developer": model.developer,
        "additional_details": {
            "deployment_type": model.deployment_type,
            "model_availability": model.model_availability,
            "canonical_id_status": "unverified",
        },
    }
    if model.inference_platform:
        model_info["inference_platform"] = model.inference_platform
    if model.inference_engine:
        model_info["inference_engine"] = {
            "name": model.inference_engine,
            "version": model.inference_engine_version or "unknown",
        }

    source_additional = {
        "dataset_sha256": dataset_sha,
        "benchmark_version": "0.1",
        "synthetic": "true",
    }
    if source_revision:
        source_additional["source_revision"] = source_revision
    source_data = {
        "dataset_name": EEE_COLLECTION,
        "source_type": "url",
        "url": [source_url],
        "additional_details": source_additional,
    }
    evaluation_results = []
    metrics = report["metrics"]
    intervals = report.get("uncertainty", {}).get("intervals", {})
    uncertainty_meta = report.get("uncertainty", {})
    for metric in _METRICS:
        score = _finite_score(metrics[metric.key], f"metrics.{metric.key}")
        score_details: dict[str, Any] = {
            "score": score,
            "details": {
                "dataset_sha256": dataset_sha,
                "case_count": str(report["dataset"]["case_count"]),
                "pair_count": str(report["dataset"]["pair_count"]),
                "hard_gate_pass": str(bool(metrics["hard_gate_pass"])).lower(),
            },
        }
        interval = intervals.get(metric.key)
        if isinstance(interval, dict):
            score_details["uncertainty"] = {
                "confidence_interval": {
                    "lower": _finite_score(interval["lower"], f"{metric.key}.lower"),
                    "upper": _finite_score(interval["upper"], f"{metric.key}.upper"),
                    "confidence_level": _finite_score(
                        uncertainty_meta["confidence"], "uncertainty.confidence"
                    ),
                    "method": str(uncertainty_meta["method"]),
                },
                "num_samples": int(report["dataset"]["case_count"]),
                "num_bootstrap_samples": int(uncertainty_meta["replicates"]),
            }
        evaluation_results.append(
            {
                "evaluation_result_id": metric.result_id,
                "evaluation_name": "finmirror.v0.1",
                "source_data": source_data,
                "evaluation_timestamp": evaluation_timestamp,
                "metric_config": {
                    "evaluation_description": metric.description,
                    "metric_id": metric.result_id,
                    "metric_name": metric.name,
                    "metric_kind": "reliability",
                    "metric_unit": metric.unit,
                    "lower_is_better": False,
                    "score_type": "continuous",
                    "min_score": metric.minimum,
                    "max_score": metric.maximum,
                    "additional_details": {
                        "implementation": "deterministic",
                        "sample_kind": metric.sample_kind,
                    },
                },
                "score_details": score_details,
            }
        )

    return {
        "schema_version": EEE_SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "evaluation_timestamp": evaluation_timestamp,
        "retrieved_timestamp": retrieved_timestamp,
        "source_metadata": {
            "source_name": "FinMirror",
            "source_type": "evaluation_run",
            "source_organization_name": "FinMirror",
            "source_organization_url": FINMIRROR_REPOSITORY_URL,
            "evaluator_relationship": model.evaluator_relationship,
            "additional_details": {
                "report_schema_version": str(report["report_schema_version"]),
                "eee_schema_upstream_commit": EEE_UPSTREAM_COMMIT,
            },
        },
        "eval_library": {
            "name": "finmirror",
            "version": __version__,
            "additional_details": {
                "system_version": str(report["system"].get("version", "")),
            },
        },
        "model_info": model_info,
        "evaluation_results": evaluation_results,
        "detailed_evaluation_results": {
            "format": "jsonl",
            "file_path": samples_path,
            "hash_algorithm": "sha256",
            "checksum": samples_checksum,
            "total_rows": sample_count,
            "additional_details": {
                "record_policy": "one sample-metric record per row",
            },
        },
    }


def _sample_rows(
    report: dict[str, Any],
    cases: dict[str, BenchmarkCase],
    predictions: dict[str, Prediction],
    report_cases: dict[str, dict[str, Any]],
    model_id: str,
    evaluation_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric in _METRICS:
        if metric.sample_kind == "case":
            for case_id in sorted(cases):
                case = cases[case_id]
                prediction = predictions[case_id]
                case_result = report_cases[case_id]
                score = _finite_score(
                    case_result[metric.sample_field],
                    f"cases.{case_id}.{metric.sample_field}",
                )
                rows.append(
                    _case_sample(
                        case,
                        prediction,
                        metric,
                        score,
                        model_id,
                        evaluation_id,
                    )
                )
        elif metric.sample_kind == "pair":
            for pair in sorted(
                report["pairs"], key=lambda item: str(item["transformed_case_id"])
            ):
                rows.append(
                    _pair_sample(
                        pair,
                        cases,
                        predictions,
                        metric,
                        model_id,
                        evaluation_id,
                    )
                )
    return rows


def _case_sample(
    case: BenchmarkCase,
    prediction: Prediction,
    metric: _Metric,
    score: float,
    model_id: str,
    evaluation_id: str,
) -> dict[str, Any]:
    reference = [case.expected.display]
    raw_input = case.question
    output_value = prediction.answer or ("ABSTAIN" if prediction.abstained else "")
    row: dict[str, Any] = {
        "schema_version": EEE_SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "model_id": model_id,
        "evaluation_name": "finmirror.v0.1",
        "evaluation_result_id": metric.result_id,
        "sample_id": case.case_id,
        "sample_hash": _sample_hash(raw_input, reference),
        "interaction_type": "single_turn",
        "input": {
            "raw": raw_input,
            "formatted": build_financial_prompt(case.prompt_case(), case.documents),
            "reference": reference,
        },
        "output": {"raw": [output_value]},
        "answer_attribution": [
            {
                "turn_idx": 0,
                "source": "output.raw",
                "extracted_value": output_value,
                "extraction_method": "finmirror.prediction-contract.v1",
                "is_terminal": True,
            }
        ],
        "evaluation": {
            "score": score,
            "is_correct": math.isclose(score, 1.0),
            "num_turns": 1,
            "tool_calls_count": 0,
        },
        "performance": {"latency_ms": _finite_score(prediction.latency_ms, "latency_ms")},
        "metadata": {
            "language": case.language,
            "scenario_id": case.scenario_id,
            "transform": case.relationship.transform,
            "task_type": case.task_type,
            "abstained": str(prediction.abstained).lower(),
            "citations": _compact_json(list(prediction.citations)),
        },
    }
    if prediction.input_tokens or prediction.output_tokens:
        row["token_usage"] = {
            "input_tokens": prediction.input_tokens,
            "output_tokens": prediction.output_tokens,
            "total_tokens": prediction.input_tokens + prediction.output_tokens,
        }
    return row


def _pair_sample(
    pair: dict[str, Any],
    cases: dict[str, BenchmarkCase],
    predictions: dict[str, Prediction],
    metric: _Metric,
    model_id: str,
    evaluation_id: str,
) -> dict[str, Any]:
    reference_id = str(pair["reference_case_id"])
    transformed_id = str(pair["transformed_case_id"])
    reference_case = cases[reference_id]
    transformed_case = cases[transformed_id]
    reference_prediction = predictions[reference_id]
    transformed_prediction = predictions[transformed_id]
    raw_input = (
        f"REFERENCE QUESTION:\n{reference_case.question}\n\n"
        f"TRANSFORMED QUESTION:\n{transformed_case.question}"
    )
    reference = [str(pair["expectation"])]
    output_payload = {
        "reference_answer": reference_prediction.answer,
        "reference_abstained": reference_prediction.abstained,
        "transformed_answer": transformed_prediction.answer,
        "transformed_abstained": transformed_prediction.abstained,
    }
    observed_relation = (
        "abstained"
        if transformed_prediction.abstained
        else "changed"
        if bool(pair["answer_changed"])
        else "unchanged"
    )
    score = _finite_score(pair[metric.sample_field], f"pairs.{transformed_id}.score")
    return {
        "schema_version": EEE_SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "model_id": model_id,
        "evaluation_name": "finmirror.v0.1",
        "evaluation_result_id": metric.result_id,
        "sample_id": f"{reference_id}::{transformed_id}",
        "sample_hash": _sample_hash(raw_input, reference),
        "interaction_type": "single_turn",
        "input": {
            "raw": raw_input,
            "formatted": (
                "REFERENCE PROMPT:\n"
                + build_financial_prompt(reference_case.prompt_case(), reference_case.documents)
                + "\nTRANSFORMED PROMPT:\n"
                + build_financial_prompt(
                    transformed_case.prompt_case(), transformed_case.documents
                )
            ),
            "reference": reference,
        },
        "output": {"raw": [_compact_json(output_payload)]},
        "answer_attribution": [
            {
                "turn_idx": 0,
                "source": "output.raw",
                "extracted_value": observed_relation,
                "extraction_method": "finmirror.pair-behavior.v1",
                "is_terminal": True,
            }
        ],
        "evaluation": {
            "score": score,
            "is_correct": bool(pair["passed"]),
            "num_turns": 1,
            "tool_calls_count": 0,
        },
        "metadata": {
            "transform": str(pair["transform"]),
            "expectation": str(pair["expectation"]),
            "answer_pass": str(bool(pair["answer_pass"])).lower(),
            "evidence_pass": str(bool(pair["evidence_pass"])).lower(),
            "formula_pass": str(bool(pair["formula_pass"])).lower(),
            "confidence_pass": str(bool(pair["confidence_pass"])).lower(),
            "retrieval_pass": str(bool(pair["retrieval_pass"])).lower(),
        },
    }


def _validate_report(
    report: dict[str, Any],
    cases: list[BenchmarkCase],
    predictions: list[Prediction],
) -> None:
    if report.get("report_schema_version") != "1.1":
        raise ValueError("EEE export requires FinMirror report schema 1.1")
    if not cases:
        raise ValueError("cannot export an empty dataset")
    expected_ids = {item.case_id for item in cases}
    prediction_ids = [item.case_id for item in predictions]
    if len(prediction_ids) != len(set(prediction_ids)):
        raise ValueError("predictions contain duplicate case IDs")
    if set(prediction_ids) != expected_ids:
        raise ValueError("predictions must contain exactly one row per benchmark case")
    report_ids = [str(item.get("case_id", "")) for item in report.get("cases", [])]
    if len(report_ids) != len(set(report_ids)) or set(report_ids) != expected_ids:
        raise ValueError("report cases do not exactly match the benchmark")
    computed_digest = dataset_digest(cases)
    if str(report.get("dataset", {}).get("sha256", "")) != computed_digest:
        raise ValueError("report dataset digest does not match benchmark bytes")
    if int(report["dataset"]["case_count"]) != len(cases):
        raise ValueError("report case_count does not match benchmark")
    transformed_ids = {
        item.case_id
        for item in cases
        if item.relationship.expectation != "reference"
    }
    report_pair_ids = {
        str(item.get("transformed_case_id", "")) for item in report.get("pairs", [])
    }
    if report_pair_ids != transformed_ids:
        raise ValueError("report pairs do not exactly match transformed benchmark cases")
    metadata = report.get("run_metadata", {})
    if bool(metadata.get("adapter_uses_gold")) or bool(metadata.get("uses_gold")):
        raise ValueError("gold-aware runs cannot be exported as public model evaluations")
    if str(report.get("system", {}).get("name", "")).lower() == "harness-oracle":
        raise ValueError("the harness oracle is a test fixture, not a publishable model run")
    for metric in _METRICS:
        score = _finite_score(report.get("metrics", {}).get(metric.key), metric.key)
        if not metric.minimum <= score <= metric.maximum:
            raise ValueError(
                f"metrics.{metric.key} must be in [{metric.minimum}, {metric.maximum}]"
            )


def _validate_export_semantics(
    aggregate: dict[str, Any], rows: list[dict[str, Any]]
) -> None:
    result_ids = {
        str(item["evaluation_result_id"]) for item in aggregate["evaluation_results"]
    }
    if not rows:
        raise ValueError("EEE instance export must not be empty")
    for index, row in enumerate(rows, start=1):
        if row["evaluation_id"] != aggregate["evaluation_id"]:
            raise ValueError(f"sample row {index} evaluation_id does not match aggregate")
        if row["model_id"] != aggregate["model_info"]["id"]:
            raise ValueError(f"sample row {index} model_id does not match aggregate")
        if row["evaluation_result_id"] not in result_ids:
            raise ValueError(f"sample row {index} references an unknown result")
        expected_hash = _sample_hash(row["input"]["raw"], row["input"]["reference"])
        if row["sample_hash"] != expected_hash:
            raise ValueError(f"sample row {index} has an invalid sample_hash")
        if len(row["answer_attribution"]) != 1:
            raise ValueError(f"sample row {index} must have explicit answer attribution")
        json.dumps(row, allow_nan=False)
    json.dumps(aggregate, allow_nan=False)


def _publish_atomically(artifacts: tuple[tuple[Path, bytes], ...]) -> None:
    paths = [path for path, _ in artifacts]
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate EEE publication paths")
    for path in paths:
        if path.exists():
            raise FileExistsError(f"refusing to overwrite output file {path}")
    created: list[Path] = []
    created_directories: list[Path] = []
    try:
        for path, content in artifacts:
            missing: list[Path] = []
            parent = path.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for directory in reversed(missing):
                directory.mkdir()
                created_directories.append(directory)
            with path.open("xb") as handle:
                created.append(path)
                handle.write(content)
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        for directory in reversed(created_directories):
            with suppress(OSError):
                directory.rmdir()
        raise


def _datastore_components(
    collection: str, model_id: str, developer: str
) -> tuple[str, str, str]:
    collection_component = _flatten_component(collection, "collection")
    model_parts = model_id.strip().split("/")
    if any(not item for item in model_parts):
        raise ValueError(f"invalid model_id: {model_id!r}")
    if len(model_parts) >= 2:
        developer_component = _path_component(model_parts[0], "model developer")
        model_component = _flatten_component("/".join(model_parts[1:]), "model name")
    else:
        developer_component = _path_component(developer, "model developer")
        model_component = _path_component(model_parts[0], "model name")
    return collection_component, developer_component, model_component


def _flatten_component(value: str, field: str) -> str:
    parts = value.strip().split("/")
    if any(not item for item in parts):
        raise ValueError(f"invalid {field}: {value!r}")
    return "_".join(_path_component(item, field) for item in parts)


def _path_component(value: str, field: str) -> str:
    value = _required_identity(value, field).replace(":", "_")
    if (
        value in {".", ".."}
        or "/" in value
        or _PATH_INVALID.search(value)
        or value.endswith((".", " "))
        or value.split(".", 1)[0].upper() in _WINDOWS_RESERVED
        or value == "data"
    ):
        raise ValueError(f"{field} is not a safe datastore path component: {value!r}")
    return value


def _required_identity(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value.strip().lower() == "unknown":
        raise ValueError(f"{field} must be known")
    return value.strip()


def _require_uuid4(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid file UUID: {value!r}") from exc
    if parsed.version != 4 or parsed.variant != uuid.RFC_4122:
        raise ValueError(f"file UUID must be RFC 4122 UUIDv4: {value!r}")
    return str(parsed)


def _epoch_timestamp(value: str, field: str) -> str:
    text = str(value).strip()
    if text.isdigit():
        if int(text) < 0:
            raise ValueError(f"{field} must be non-negative")
        return str(int(text))
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 or epoch timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} ISO-8601 timestamp must include a timezone")
    return str(int(parsed.timestamp()))


def _finite_score(value: Any, field: str) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(score):
        raise ValueError(f"{field} must be finite")
    return score


def _sample_hash(raw: str, reference: list[str]) -> str:
    payload = json.dumps(
        {"raw": raw, "reference": reference},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _compact_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
