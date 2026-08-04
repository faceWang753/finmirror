"""Portable Markdown and machine outputs for CI evaluation gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _percent(value: Any) -> str:
    return f"{100 * float(value):.1f}%"


def _markdown_text(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_ci_summary(report: dict[str, Any]) -> str:
    """Render a compact, reviewable Markdown summary from one FinMirror report."""

    metrics = dict(report["metrics"])
    system = dict(report["system"])
    dataset = dict(report["dataset"])
    passed = bool(metrics["hard_gate_pass"])
    gate = "PASS" if passed else "BLOCKED"
    failure_counts = dict(report.get("failure_counts", {}))
    top_failures = sorted(
        failure_counts.items(),
        key=lambda item: (-int(item[1]), str(item[0])),
    )[:5]
    failure_lines = (
        "\n".join(f"- `{_markdown_text(name)}`: {int(count)}" for name, count in top_failures)
        if top_failures
        else "- No deterministic failures recorded."
    )

    return f"""## FinMirror gate: {gate}

**{_markdown_text(system["name"])}** scored **{float(metrics["audit_score"]):.1f}/100** on
{int(dataset["case_count"])} cases and {int(dataset["pair_count"])} paired interventions.

| Reliability contract | Result |
|---|---:|
| Case accuracy | {_percent(metrics["case_accuracy"])} |
| Strict pair reliability | {_percent(metrics["pair_reliability"])} |
| Citation migration | {_percent(metrics["citation_migration"])} |
| Operand provenance | {_percent(metrics["operand_provenance"])} |
| Confidence behavior | {_percent(metrics["confidence_behavior"])} |
| Evidence ablation | {_percent(metrics["evidence_ablation"])} |

### Most frequent failures

{failure_lines}

<sub>FinMirror v0.1 uses synthetic paired worlds. This gate is a deterministic regression
check, not a production-safety, regulatory, or investment claim.</sub>
"""


def write_ci_artifacts(
    report: dict[str, Any],
    *,
    summary_path: str | Path,
    outputs_path: str | Path | None = None,
) -> None:
    """Write a Markdown summary and optional GitHub-compatible step outputs."""

    summary = Path(summary_path)
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(render_ci_summary(report), encoding="utf-8", newline="\n")

    if outputs_path is None:
        return
    metrics = dict(report["metrics"])
    outputs = Path(outputs_path)
    outputs.parent.mkdir(parents=True, exist_ok=True)
    with outputs.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"gate={'PASS' if metrics['hard_gate_pass'] else 'BLOCKED'}\n")
        handle.write(f"audit_score={float(metrics['audit_score']):.1f}\n")
        handle.write(f"pair_reliability={float(metrics['pair_reliability']):.6f}\n")


def load_report(path: str | Path) -> dict[str, Any]:
    """Load one JSON report and reject a non-object root."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("FinMirror report root must be a JSON object")
    return value
