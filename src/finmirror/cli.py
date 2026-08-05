"""Command-line entry point for generation, evaluation, and reporting."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from finmirror.adapters.base import Adapter, run_adapter
from finmirror.adapters.baselines import (
    EvidenceProgramBaseline,
    MemorizedBaseline,
    OracleAdapter,
)
from finmirror.annotations import annotation_agreement
from finmirror.ci import load_report, write_ci_artifacts
from finmirror.dataset import dataset_digest, load_cases
from finmirror.evaluator import evaluate
from finmirror.generator import generate_benchmark
from finmirror.lineage import (
    evidence_claim_tier,
    load_evidence_manifest,
    require_real_source_material,
    validate_lineage,
    verify_repository_artifacts,
)
from finmirror.report import render_comparison, render_report
from finmirror.review import load_expert_review_status, require_expert_validated
from finmirror.sources import ledger_digest, load_ledger
from finmirror.training import (
    export_preferences,
    load_predictions,
    save_predictions,
)


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
            model=args.model,
            rerank_model=args.rerank_model,
            top_n=args.top_n,
            measure_pre_confidence=args.measure_pre_confidence,
        )
    raise ValueError(f"Unknown adapter: {args.adapter}")


def _run_and_write(
    adapter: Adapter,
    cases: list[Any],
    output_dir: Path,
) -> dict[str, Any]:
    predictions = run_adapter(adapter, cases)
    report = evaluate(
        cases,
        predictions,
        system_name=adapter.name,
        system_version=adapter.version,
        run_metadata={
            "adapter_uses_gold": adapter.uses_gold,
            "offline": adapter.name != "cohere",
        },
    )
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
    parser.add_argument("--version", action="version", version="finmirror 0.1.1")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate the synthetic v0.1 benchmark")
    generate.add_argument("--out", default="benchmark/v0.1")

    validate = subparsers.add_parser("validate", help="Validate schema and dataset integrity")
    validate.add_argument("dataset", nargs="?", default="benchmark/v0.1")

    demo = subparsers.add_parser("demo", help="Run the zero-key oracle and evidence-blind demo")
    demo.add_argument("--dataset", default="benchmark/v0.1")
    demo.add_argument("--out", default="artifacts/demo")

    run = subparsers.add_parser("run", help="Run and score an adapter")
    run.add_argument("--dataset", default="benchmark/v0.1")
    run.add_argument(
        "--adapter",
        choices=["evidence", "memorized", "oracle", "cohere"],
        required=True,
    )
    run.add_argument("--model", default="command-a-plus-05-2026")
    run.add_argument("--rerank-model", default=None)
    run.add_argument("--top-n", type=int, default=5)
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
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    parser.error("Unhandled command")


if __name__ == "__main__":
    raise SystemExit(main())
