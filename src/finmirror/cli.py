"""Command-line entry point for generation, evaluation, and reporting."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from finmirror.adapters.base import Adapter, run_adapter
from finmirror.adapters.baselines import (
    EvidenceProgramBaseline,
    MemorizedBaseline,
    OracleAdapter,
)
from finmirror.annotations import annotation_agreement
from finmirror.assurance import run_evaluator_assurance
from finmirror.ci import load_report, write_ci_artifacts
from finmirror.dataset import dataset_digest, load_cases
from finmirror.eee import EEEModelSpec, export_eee
from finmirror.equivalence import render_equivalence_report, run_equivalence_assurance
from finmirror.evaluator import evaluate
from finmirror.generator import generate_benchmark
from finmirror.judge_audit import (
    audit_judge_payload,
    build_judge_demo,
    dump_demo_inputs,
    render_judge_comparison,
)
from finmirror.lineage import (
    evidence_claim_tier,
    load_evidence_manifest,
    require_real_source_material,
    validate_lineage,
    verify_repository_artifacts,
)
from finmirror.report import render_comparison, render_report
from finmirror.retrieval_audit import (
    InputOrderRanker,
    LexicalOverlapRanker,
    RetrievalOracleRanker,
    audit_retrieval_rankings,
    build_retrieval_cases,
    dump_retrieval_packet,
    load_retrieval_predictions,
    render_retrieval_comparison,
    run_retrieval_ranker,
    save_retrieval_predictions,
)
from finmirror.review import load_expert_review_status, require_expert_validated
from finmirror.review_submission import load_review_submission
from finmirror.sources import ledger_digest, load_ledger
from finmirror.trace_audit import audit_trace_run, render_trace_comparison
from finmirror.training import (
    export_preferences,
    load_predictions,
    save_predictions,
)

_DEMO_ARTIFACT_CREATED_AT = "2026-07-26T00:00:00+00:00"


def _write_json(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _filter_cases(cases: list[Any], languages: str | None, scenarios: str | None) -> list[Any]:
    language_set = set(languages.split(",")) if languages else None
    scenario_set = set(scenarios.split(",")) if scenarios else None
    filtered = [
        case
        for case in cases
        if (language_set is None or case.language in language_set)
        and (scenario_set is None or case.scenario_id in scenario_set)
    ]
    if not filtered:
        raise ValueError("Filters selected zero cases")
    # Each retained group must remain complete, so pairwise metrics stay valid.
    retained_groups = {case.pair_group_id for case in filtered}
    return [case for case in filtered if case.pair_group_id in retained_groups]


def _select_adapter(args: argparse.Namespace, cases: list[Any]) -> Adapter:
    if args.adapter == "memorized":
        return MemorizedBaseline()
    if args.adapter == "oracle":
        return OracleAdapter(cases)
    if args.adapter == "evidence":
        return EvidenceProgramBaseline()
    if args.adapter == "cohere":
        from finmirror.adapters.cohere import CohereAdapter

        return CohereAdapter(
            model=args.model or "command-a-plus-05-2026",
            rerank_model=args.rerank_model,
            top_n=args.top_n,
            measure_pre_confidence=args.measure_pre_confidence,
        )
    if args.adapter == "openai":
        from finmirror.adapters.openai_compatible import OpenAICompatibleAdapter

        return OpenAICompatibleAdapter(
            model=args.model,
            base_url=args.base_url,
            timeout=args.request_timeout,
            max_retries=args.max_retries,
            measure_pre_confidence=args.measure_pre_confidence,
        )
    raise ValueError(f"Unknown adapter: {args.adapter}")


def _run_and_write(
    adapter: Adapter,
    cases: list[Any],
    output_dir: Path,
) -> dict[str, Any]:
    predictions = [
        replace(prediction, latency_ms=0.0) for prediction in run_adapter(adapter, cases)
    ]
    report = evaluate(
        cases,
        predictions,
        system_name=adapter.name,
        system_version=adapter.version,
        run_metadata={
            "adapter_uses_gold": adapter.uses_gold,
            "offline": adapter.offline,
        },
    )
    report["created_at"] = _DEMO_ARTIFACT_CREATED_AT
    output_dir.mkdir(parents=True, exist_ok=True)
    save_predictions(predictions, output_dir / "predictions.jsonl")
    _write_json(report, output_dir / "report.json")
    render_report(report, output_dir / "report.html")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="finmirror",
        description="Paired counterfactual evaluation for financial AI agents.",
    )
    parser.add_argument("--version", action="version", version="finmirror 0.2.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate the synthetic v0.1 benchmark")
    generate.add_argument("--out", default="benchmark/v0.1")

    validate = subparsers.add_parser("validate", help="Validate schema and dataset integrity")
    validate.add_argument("dataset", nargs="?", default="benchmark/v0.1")

    assurance = subparsers.add_parser(
        "assure-evaluator",
        help="Run deterministic one-field mutation assurance for the evaluator",
    )
    assurance.add_argument("--dataset", default="benchmark/v0.1")
    assurance.add_argument("--out", default="artifacts/evaluator-assurance.json")

    equivalence = subparsers.add_parser(
        "assure-equivalence",
        help="Verify invariance under declared semantic-equivalence relations",
    )
    equivalence.add_argument("--dataset", default="benchmark/v0.1")
    equivalence.add_argument("--out", default="artifacts/demo/equivalence")

    demo = subparsers.add_parser("demo", help="Run the zero-key oracle and evidence-blind demo")
    demo.add_argument("--dataset", default="benchmark/v0.1")
    demo.add_argument("--out", default="artifacts/demo")

    trace_demo = subparsers.add_parser(
        "trace-demo",
        help="Show why identical correct answers still need replayable evidence paths",
    )
    trace_demo.add_argument("--dataset", default="benchmark/v0.1")
    trace_demo.add_argument("--out", default="artifacts/demo/trace")

    trace_audit = subparsers.add_parser(
        "trace-audit",
        help="Replay content-addressed evidence receipts in a prediction JSONL file",
    )
    trace_audit.add_argument("--dataset", default="benchmark/v0.1")
    trace_audit.add_argument("--predictions", required=True)
    trace_audit.add_argument("--system", required=True)
    trace_audit.add_argument("--out", default="runs/trace-audit")

    judge_demo = subparsers.add_parser(
        "judge-demo",
        help="Audit checklist quality and permissive-verifier reward inflation",
    )
    judge_demo.add_argument("--out", default="artifacts/demo/judge")

    judge_audit = subparsers.add_parser(
        "judge-audit",
        help="Audit an external checklist-verifier JSON artifact",
    )
    judge_audit.add_argument("--input", required=True)
    judge_audit.add_argument("--out", default="runs/judge-audit")

    retrieval_demo = subparsers.add_parser(
        "retrieval-demo",
        help="Audit evidence coverage and harmful-passage exposure before generation",
    )
    retrieval_demo.add_argument("--dataset", default="benchmark/v0.1")
    retrieval_demo.add_argument("--top-k", type=int, default=2)
    retrieval_demo.add_argument("--out", default="artifacts/demo/retrieval")

    retrieval_audit = subparsers.add_parser(
        "retrieval-audit",
        help="Audit complete rankings returned for a public retrieval packet",
    )
    retrieval_audit.add_argument("--dataset", default="benchmark/v0.1")
    retrieval_audit.add_argument("--predictions", required=True)
    retrieval_audit.add_argument("--system", required=True)
    retrieval_audit.add_argument("--system-version", default="")
    retrieval_audit.add_argument("--top-k", type=int, default=2)
    retrieval_audit.add_argument("--out", default="runs/retrieval-audit")

    run = subparsers.add_parser("run", help="Run and score an adapter")
    run.add_argument("--dataset", default="benchmark/v0.1")
    run.add_argument(
        "--adapter",
        choices=["evidence", "memorized", "oracle", "cohere", "openai"],
        required=True,
    )
    run.add_argument("--model")
    run.add_argument("--rerank-model", default=None)
    run.add_argument("--top-n", type=int, default=5)
    run.add_argument(
        "--base-url",
        help="OpenAI-compatible base URL; defaults to OPENAI_BASE_URL",
    )
    run.add_argument("--request-timeout", type=float, default=120.0)
    run.add_argument("--max-retries", type=int, default=2)
    run.add_argument("--measure-pre-confidence", action="store_true")
    run.add_argument("--languages", help="Comma-separated language codes")
    run.add_argument("--scenarios", help="Comma-separated scenario IDs")
    run.add_argument("--out", default="runs/latest")

    score = subparsers.add_parser("score", help="Score an existing JSONL submission")
    score.add_argument("--dataset", default="benchmark/v0.1")
    score.add_argument("--predictions", required=True)
    score.add_argument("--system", required=True)
    score.add_argument("--system-version", default="")
    score.add_argument("--out", default="runs/scored")

    report = subparsers.add_parser("report", help="Re-render an HTML report")
    report.add_argument("report_json")
    report.add_argument("--out", default="report.html")

    ci_summary = subparsers.add_parser(
        "ci-summary",
        help="Write a Markdown CI summary and optional GitHub step outputs",
    )
    ci_summary.add_argument("--report", required=True, help="FinMirror report.json path")
    ci_summary.add_argument("--summary-out", required=True, help="Markdown summary path")
    ci_summary.add_argument(
        "--github-output",
        help="Optional path supplied by GitHub Actions through GITHUB_OUTPUT",
    )

    preferences = subparsers.add_parser(
        "export-preferences",
        help="Build deterministic chosen/rejected training pairs",
    )
    preferences.add_argument("--dataset", default="benchmark/v0.1")
    preferences.add_argument("--left", required=True)
    preferences.add_argument("--right", required=True)
    preferences.add_argument("--out", default="artifacts/preferences.jsonl")

    agreement = subparsers.add_parser(
        "agreement",
        help="Compute categorical annotation agreement and Cohen's kappa",
    )
    agreement.add_argument("--left", required=True)
    agreement.add_argument("--right", required=True)
    agreement.add_argument(
        "--fields",
        default="answerable,error_type,material",
        help="Comma-separated categorical fields",
    )
    agreement.add_argument("--out")

    evidence_status = subparsers.add_parser(
        "evidence-status",
        help="Verify evidence lineage and report the strongest justified source claim",
    )
    evidence_status.add_argument(
        "--ledger",
        default="sources/v0.2/ledger.jsonl",
        help="Source receipt ledger in JSONL format",
    )
    evidence_status.add_argument(
        "--manifest",
        default="sources/v0.2/evidence-manifest.json",
        help="Hash-bound evidence lineage manifest",
    )
    evidence_status.add_argument(
        "--root",
        default=".",
        help="Repository root used to verify committed artifact bytes",
    )
    evidence_status.add_argument(
        "--require-real-source",
        action="store_true",
        help="Fail unless release-ready provider material reaches rendered evidence",
    )

    review_status = subparsers.add_parser(
        "review-status",
        help="Report whether a real-source pilot has earned expert-validated gold status",
    )
    review_status.add_argument(
        "--status",
        default=("sources/v0.2/calibration/statcan-gdp-2025q2-q3/review-status.json"),
        help="Machine-readable expert review status record",
    )
    review_status.add_argument(
        "--dataset-sha256",
        help="Optional dataset digest that the review status must bind",
    )
    review_status.add_argument(
        "--require-expert-validated",
        action="store_true",
        help="Fail unless independent annotation and adjudication gates pass",
    )

    validate_review = subparsers.add_parser(
        "validate-review",
        help="Validate a blinded review submission against the exact pending pilot",
    )
    validate_review.add_argument("--submission", required=True, help="Reviewer JSONL export")
    validate_review.add_argument(
        "--status",
        default=("sources/v0.2/calibration/statcan-gdp-2025q2-q3/review-status.json"),
        help="Machine-readable expert review status record",
    )

    eee = subparsers.add_parser(
        "export-eee",
        help="Export a scored run using the Every Eval Ever 0.3.0 contract",
    )
    eee.add_argument("--dataset", default="benchmark/v0.1")
    eee.add_argument("--report", required=True, help="FinMirror report.json path")
    eee.add_argument("--predictions", required=True, help="Matching predictions JSONL")
    eee.add_argument("--model-id", required=True, help="Canonical developer/model identity")
    eee.add_argument("--model-name", required=True, help="Model display name from the run")
    eee.add_argument("--developer", required=True, help="Model developer; must match ID prefix")
    eee.add_argument(
        "--evaluator-relationship",
        required=True,
        choices=["first_party", "third_party", "collaborative", "other"],
    )
    eee.add_argument(
        "--deployment-type",
        required=True,
        choices=["self_deployed", "externally_managed", "unknown"],
    )
    eee.add_argument(
        "--model-availability",
        required=True,
        choices=["open_weights", "closed_weights", "unknown"],
    )
    eee.add_argument("--inference-platform", default="")
    eee.add_argument("--inference-engine", default="")
    eee.add_argument("--inference-engine-version", default="")
    eee.add_argument(
        "--source-url",
        default="https://huggingface.co/datasets/mingyang233/FinMirror",
    )
    eee.add_argument("--source-revision", default="")
    eee.add_argument("--file-uuid", help="Optional UUIDv4 for reproducible conversion tests")
    eee.add_argument("--retrieved-timestamp", help="Optional epoch/ISO retrieval time")
    eee.add_argument("--out", default="artifacts/eee")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            cases = generate_benchmark(args.out)
            print(
                f"Generated {len(cases)} cases in {args.out} "
                f"(sha256 {dataset_digest(cases)[:12]}…)"
            )
            return 0

        if args.command == "validate":
            cases = load_cases(args.dataset)
            print(
                f"VALID · {len(cases)} cases · "
                f"{len({item.pair_group_id for item in cases})} groups · "
                f"sha256 {dataset_digest(cases)}"
            )
            return 0

        if args.command == "assure-evaluator":
            assurance_report = run_evaluator_assurance(load_cases(args.dataset))
            _write_json(assurance_report, Path(args.out))
            print(
                f"{'PASS' if assurance_report['passed'] else 'BLOCKED'} · "
                f"{assurance_report['passed_count']}/{assurance_report['mutation_count']} "
                f"one-field mutations detected · wrote {Path(args.out).resolve()}"
            )
            return 0 if assurance_report["passed"] else 2

        if args.command == "assure-equivalence":
            equivalence_report = run_equivalence_assurance(load_cases(args.dataset))
            output = Path(args.out)
            _write_json(equivalence_report, output / "report.json")
            render_equivalence_report(equivalence_report, output / "index.html")
            print(
                f"{'PASS' if equivalence_report['passed'] else 'BLOCKED'} · "
                f"{equivalence_report['passed_count']}/{equivalence_report['relation_count']} "
                f"equivalence relations preserved · "
                f"{equivalence_report['semantic_assertion_count']} assertions · "
                f"open {(output / 'index.html').resolve()}"
            )
            return 0 if equivalence_report["passed"] else 2

        if args.command == "demo":
            dataset_path = Path(args.dataset)
            if not (dataset_path / "cases.jsonl").exists() and not dataset_path.is_file():
                generate_benchmark(dataset_path)
            cases = load_cases(dataset_path)
            output = Path(args.out)
            reports = [
                _run_and_write(OracleAdapter(cases), cases, output / "oracle"),
                _run_and_write(EvidenceProgramBaseline(), cases, output / "evidence-program"),
                _run_and_write(MemorizedBaseline(), cases, output / "memorized"),
            ]
            render_comparison(
                reports,
                output / "index.html",
                links={
                    "harness-oracle": "oracle/report.html",
                    "evidence-program": "evidence-program/report.html",
                    "memorized-evidence-blind": "memorized/report.html",
                },
            )
            print(f"Demo complete · open {(output / 'index.html').resolve()}")
            return 0

        if args.command == "trace-demo":
            dataset_path = Path(args.dataset)
            if not (dataset_path / "cases.jsonl").exists() and not dataset_path.is_file():
                generate_benchmark(dataset_path)
            cases = load_cases(dataset_path)
            verified_predictions = [
                replace(item, latency_ms=0.0)
                for item in run_adapter(EvidenceProgramBaseline(), cases)
            ]
            unverified_predictions = [replace(item, trace=()) for item in verified_predictions]
            output = Path(args.out)
            trace_reports = (
                audit_trace_run(
                    cases,
                    verified_predictions,
                    system_name="evidence-program-with-receipts",
                ),
                audit_trace_run(
                    cases,
                    unverified_predictions,
                    system_name="identical-output-without-receipts",
                ),
            )
            for name, predictions, report_value in (
                ("verified", verified_predictions, trace_reports[0]),
                ("unverified", unverified_predictions, trace_reports[1]),
            ):
                directory = output / name
                save_predictions(predictions, directory / "predictions.jsonl")
                _write_json(report_value, directory / "trace-report.json")
            render_trace_comparison(trace_reports, output / "index.html")
            print(
                "Trace demo complete · identical answer accuracy, "
                f"{100 * trace_reports[0]['metrics']['trace_pass_rate']:.1f}% vs "
                f"{100 * trace_reports[1]['metrics']['trace_pass_rate']:.1f}% verified paths · "
                f"open {(output / 'index.html').resolve()}"
            )
            return 0

        if args.command == "trace-audit":
            report_value = audit_trace_run(
                load_cases(args.dataset),
                load_predictions(args.predictions),
                system_name=args.system,
            )
            output = Path(args.out)
            _write_json(report_value, output / "trace-report.json")
            render_trace_comparison((report_value,), output / "trace-report.html")
            print(
                f"{args.system}: "
                f"{100 * report_value['metrics']['trace_pass_rate']:.1f}% verified paths · "
                f"gate {'PASS' if report_value['metrics']['hard_gate_pass'] else 'BLOCKED'}"
            )
            return 0 if report_value["metrics"]["hard_gate_pass"] else 2

        if args.command == "judge-demo":
            output = Path(args.out)
            judge_reports = build_judge_demo()
            for report_value in judge_reports:
                _write_json(
                    report_value,
                    output / report_value["system_name"] / "report.json",
                )
            dump_demo_inputs(output / "inputs")
            render_judge_comparison(judge_reports, output / "index.html")
            passed = sum(
                bool(report_value["metrics"]["hard_gate_pass"])
                for report_value in judge_reports
            )
            print(
                f"Judge assurance complete · {passed}/{len(judge_reports)} controls pass · "
                f"open {(output / 'index.html').resolve()}"
            )
            return 0

        if args.command == "judge-audit":
            payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
            report_value = audit_judge_payload(payload)
            output = Path(args.out)
            _write_json(report_value, output / "report.json")
            render_judge_comparison((report_value,), output / "report.html")
            gate = bool(report_value["metrics"]["hard_gate_pass"])
            print(
                f"{report_value['system_name']}: {'PASS' if gate else 'BLOCKED'} · "
                f"{report_value['metrics']['metamorphic_pass_rate']:.0%} paired relations · "
                f"{report_value['metrics']['false_pass_rate']:.0%} false passes"
            )
            return 0 if gate else 2

        if args.command == "retrieval-demo":
            retrieval_cases = build_retrieval_cases(load_cases(args.dataset))
            output = Path(args.out)
            dump_retrieval_packet(retrieval_cases, output / "packet.jsonl")
            retrieval_reports = []
            for ranker in (
                RetrievalOracleRanker(),
                LexicalOverlapRanker(),
                InputOrderRanker(),
            ):
                retrieval_predictions = run_retrieval_ranker(ranker, retrieval_cases)
                report_value = audit_retrieval_rankings(
                    retrieval_cases,
                    retrieval_predictions,
                    system_name=ranker.name,
                    system_version=ranker.version,
                    top_k=args.top_k,
                    uses_gold=ranker.uses_gold,
                )
                directory = output / ranker.name
                save_retrieval_predictions(
                    retrieval_predictions, directory / "predictions.jsonl"
                )
                _write_json(report_value, directory / "report.json")
                retrieval_reports.append(report_value)
            render_retrieval_comparison(retrieval_reports, output / "index.html")
            print(
                f"Retrieval assurance complete · {len(retrieval_cases)} cases · "
                f"open {(output / 'index.html').resolve()}"
            )
            return 0

        if args.command == "retrieval-audit":
            retrieval_cases = build_retrieval_cases(load_cases(args.dataset))
            report_value = audit_retrieval_rankings(
                retrieval_cases,
                load_retrieval_predictions(args.predictions),
                system_name=args.system,
                system_version=args.system_version,
                top_k=args.top_k,
            )
            output = Path(args.out)
            _write_json(report_value, output / "report.json")
            render_retrieval_comparison([report_value], output / "report.html")
            gate = bool(report_value["metrics"]["hard_gate_pass"])
            print(
                f"{args.system}: {'PASS' if gate else 'BLOCKED'} · "
                f"{report_value['metrics']['clean_completion_rate']:.0%} clean completion · "
                f"{report_value['metrics']['paired_reliability']:.0%} paired reliability"
            )
            return 0 if gate else 2

        if args.command == "run":
            cases = load_cases(args.dataset)
            cases = _filter_cases(cases, args.languages, args.scenarios)
            adapter = _select_adapter(args, cases)
            report_value = _run_and_write(adapter, cases, Path(args.out))
            print(
                f"{adapter.name}: {report_value['metrics']['audit_score']:.1f}/100 · "
                f"gate {'PASS' if report_value['metrics']['hard_gate_pass'] else 'BLOCKED'}"
            )
            return 0 if report_value["metrics"]["hard_gate_pass"] else 2

        if args.command == "score":
            cases = load_cases(args.dataset)
            predictions = load_predictions(args.predictions)
            report_value = evaluate(
                cases,
                predictions,
                system_name=args.system,
                system_version=args.system_version,
                run_metadata={"source": str(Path(args.predictions).resolve())},
            )
            output = Path(args.out)
            output.mkdir(parents=True, exist_ok=True)
            _write_json(report_value, output / "report.json")
            render_report(report_value, output / "report.html")
            print(
                f"{args.system}: {report_value['metrics']['audit_score']:.1f}/100 · "
                f"gate {'PASS' if report_value['metrics']['hard_gate_pass'] else 'BLOCKED'}"
            )
            return 0 if report_value["metrics"]["hard_gate_pass"] else 2

        if args.command == "report":
            report_value = json.loads(Path(args.report_json).read_text(encoding="utf-8"))
            render_report(report_value, args.out)
            print(f"Wrote {Path(args.out).resolve()}")
            return 0

        if args.command == "ci-summary":
            report_value = load_report(args.report)
            write_ci_artifacts(
                report_value,
                summary_path=args.summary_out,
                outputs_path=args.github_output,
            )
            print(f"Wrote CI summary {Path(args.summary_out).resolve()}")
            return 0

        if args.command == "export-preferences":
            cases = load_cases(args.dataset)
            summary = export_preferences(
                cases,
                load_predictions(args.left),
                load_predictions(args.right),
                args.out,
            )
            print(
                f"Exported {summary['exported']} preference pairs; "
                f"skipped {summary['ties_skipped']} ties"
            )
            return 0

        if args.command == "agreement":
            result = annotation_agreement(
                args.left,
                args.right,
                [item.strip() for item in args.fields.split(",") if item.strip()],
            )
            rendered = json.dumps(result, ensure_ascii=False, indent=2)
            if args.out:
                Path(args.out).write_text(rendered + "\n", encoding="utf-8", newline="\n")
            print(rendered)
            return 0

        if args.command == "evidence-status":
            receipts = load_ledger(args.ledger)
            manifest = load_evidence_manifest(args.manifest)
            validate_lineage(manifest, receipts)
            verify_repository_artifacts(manifest, args.root)
            tier = evidence_claim_tier(manifest, receipts)
            if args.require_real_source:
                require_real_source_material(manifest, receipts)
            counts = {
                kind: sum(artifact.kind == kind for artifact in manifest.artifacts)
                for kind in (
                    "synthetic",
                    "provider_capture",
                    "source_derived",
                    "evaluator_counterfactual",
                )
            }
            print(
                f"{tier.upper()} · {len(manifest.artifacts)} artifacts · "
                f"{json.dumps(counts, sort_keys=True)} · "
                f"ledger sha256 {ledger_digest(receipts)}"
            )
            return 0

        if args.command == "review-status":
            status = load_expert_review_status(args.status)
            blockers = status.validation_blockers()
            if args.require_expert_validated:
                require_expert_validated(
                    status,
                    dataset_sha256=args.dataset_sha256,
                )
            print(
                f"{status.review_state.upper()} · {len(status.case_ids)} cases · "
                f"gold {status.gold_status} · {len(blockers)} blockers · "
                f"dataset sha256 {status.dataset_sha256}"
            )
            return 0

        if args.command == "validate-review":
            status = load_expert_review_status(args.status)
            rows = load_review_submission(
                args.submission,
                expected_case_ids=status.case_ids,
                pilot_id=status.pilot_id,
                dataset_sha256=status.dataset_sha256,
            )
            first = rows[0]
            print(
                f"VALID BLIND REVIEW · {len(rows)} cases · "
                f"reviewer {first['reviewer_id']} · role {first['role']} · "
                f"dataset sha256 {status.dataset_sha256}"
            )
            return 0

        if args.command == "export-eee":
            report_value = json.loads(Path(args.report).read_text(encoding="utf-8"))
            if not isinstance(report_value, dict):
                raise ValueError("report JSON must contain an object")
            exported = export_eee(
                report=report_value,
                cases=load_cases(args.dataset),
                predictions=load_predictions(args.predictions),
                model=EEEModelSpec(
                    model_id=args.model_id,
                    name=args.model_name,
                    developer=args.developer,
                    evaluator_relationship=args.evaluator_relationship,
                    deployment_type=args.deployment_type,
                    model_availability=args.model_availability,
                    inference_platform=args.inference_platform,
                    inference_engine=args.inference_engine,
                    inference_engine_version=args.inference_engine_version,
                ),
                output_root=args.out,
                source_url=args.source_url,
                source_revision=args.source_revision,
                file_uuid=args.file_uuid,
                retrieved_timestamp=args.retrieved_timestamp,
            )
            print(
                f"EEE 0.3.0 VALID · {exported.sample_count} sample-metric rows · "
                f"wrote {exported.aggregate_path.resolve()}"
            )
            return 0
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    parser.error("Unhandled command")


if __name__ == "__main__":
    raise SystemExit(main())
