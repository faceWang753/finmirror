"""Deterministic meta-evaluation for checklist-based learned verifiers.

The audit separates two failure surfaces that aggregate scores often conflate:
checklist decomposition quality and the calibration of the judgments attached to
those checklist items. It requires no model calls and can therefore be used as a
replayable release gate for learned-judge outputs.
"""

from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

JUDGE_AUDIT_SCHEMA_VERSION = "1.0"
RelationKind = Literal["reference", "atomic_omission", "irrelevant_context", "reorder"]
DemoMode = Literal["calibrated", "permissive", "collapsed"]


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    satisfied: bool


@dataclass(frozen=True)
class ChecklistItem:
    item_id: str
    covers: tuple[str, ...]
    probability: float


@dataclass(frozen=True)
class JudgeScenario:
    scenario_id: str
    relation: RelationKind
    reference_scenario_id: str | None
    requirements: tuple[Requirement, ...]
    checklist: tuple[ChecklistItem, ...]


def _expect_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _expect_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return value


def _parse_requirement(value: Any, scenario_id: str) -> Requirement:
    if not isinstance(value, dict):
        raise ValueError(f"{scenario_id}: every requirement must be an object")
    if set(value) != {"requirement_id", "satisfied"}:
        raise ValueError(
            f"{scenario_id}: requirement fields must be requirement_id and satisfied"
        )
    requirement_id = _expect_string(value["requirement_id"], f"{scenario_id}.requirement_id")
    if not isinstance(value["satisfied"], bool):
        raise ValueError(f"{scenario_id}.{requirement_id}.satisfied must be boolean")
    return Requirement(requirement_id, value["satisfied"])


def _parse_checklist_item(value: Any, scenario_id: str) -> ChecklistItem:
    if not isinstance(value, dict):
        raise ValueError(f"{scenario_id}: every checklist item must be an object")
    if set(value) != {"item_id", "covers", "probability"}:
        raise ValueError(
            f"{scenario_id}: checklist fields must be item_id, covers, and probability"
        )
    item_id = _expect_string(value["item_id"], f"{scenario_id}.item_id")
    covers = tuple(
        _expect_string(item, f"{scenario_id}.{item_id}.covers")
        for item in _expect_list(value["covers"], f"{scenario_id}.{item_id}.covers")
    )
    if not covers:
        raise ValueError(f"{scenario_id}.{item_id}.covers cannot be empty")
    probability = value["probability"]
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        raise ValueError(f"{scenario_id}.{item_id}.probability must be numeric")
    probability = float(probability)
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError(f"{scenario_id}.{item_id}.probability must be between 0 and 1")
    return ChecklistItem(item_id, covers, probability)


def _parse_scenario(value: Any) -> JudgeScenario:
    if not isinstance(value, dict):
        raise ValueError("every scenario must be an object")
    expected = {
        "scenario_id",
        "relation",
        "reference_scenario_id",
        "requirements",
        "checklist",
    }
    if set(value) != expected:
        raise ValueError(f"scenario fields must be {sorted(expected)}")
    scenario_id = _expect_string(value["scenario_id"], "scenario_id")
    relation = value["relation"]
    allowed_relations = {"reference", "atomic_omission", "irrelevant_context", "reorder"}
    if relation not in allowed_relations:
        raise ValueError(f"{scenario_id}: unknown relation {relation!r}")
    reference = value["reference_scenario_id"]
    if reference is not None:
        reference = _expect_string(reference, f"{scenario_id}.reference_scenario_id")
    if relation == "reference" and reference is not None:
        raise ValueError(f"{scenario_id}: a reference scenario cannot point to a reference")
    if relation != "reference" and reference is None:
        raise ValueError(f"{scenario_id}: transformed scenarios require a reference")
    requirements = tuple(
        _parse_requirement(item, scenario_id)
        for item in _expect_list(value["requirements"], f"{scenario_id}.requirements")
    )
    checklist = tuple(
        _parse_checklist_item(item, scenario_id)
        for item in _expect_list(value["checklist"], f"{scenario_id}.checklist")
    )
    if not requirements or not checklist:
        raise ValueError(f"{scenario_id}: requirements and checklist cannot be empty")
    return JudgeScenario(
        scenario_id=scenario_id,
        relation=relation,
        reference_scenario_id=reference,
        requirements=requirements,
        checklist=checklist,
    )


def load_judge_payload(value: Any) -> tuple[str, tuple[JudgeScenario, ...]]:
    """Parse a strict, closed input contract for a judge audit."""

    if not isinstance(value, dict):
        raise ValueError("judge audit input must be an object")
    if set(value) != {"schema_version", "system_name", "scenarios"}:
        raise ValueError("input fields must be schema_version, system_name, and scenarios")
    if value["schema_version"] != JUDGE_AUDIT_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {JUDGE_AUDIT_SCHEMA_VERSION!r}")
    system_name = _expect_string(value["system_name"], "system_name")
    scenarios = tuple(
        _parse_scenario(item) for item in _expect_list(value["scenarios"], "scenarios")
    )
    if not scenarios:
        raise ValueError("scenarios cannot be empty")
    ids = [item.scenario_id for item in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError("scenario_id values must be unique")
    known = set(ids)
    for scenario in scenarios:
        if (
            scenario.reference_scenario_id is not None
            and scenario.reference_scenario_id not in known
        ):
            raise ValueError(
                f"{scenario.scenario_id}: unknown reference {scenario.reference_scenario_id!r}"
            )
    return system_name, scenarios


def _truth(scenario: JudgeScenario) -> dict[str, bool]:
    return {item.requirement_id: item.satisfied for item in scenario.requirements}


def _scenario_result(scenario: JudgeScenario) -> dict[str, Any]:
    requirement_ids = [item.requirement_id for item in scenario.requirements]
    checklist_ids = [item.item_id for item in scenario.checklist]
    coverage = [requirement for item in scenario.checklist for requirement in item.covers]
    requirement_set = set(requirement_ids)
    coverage_set = set(coverage)
    truth = _truth(scenario)

    checks = {
        "unique_requirements": len(requirement_ids) == len(requirement_set),
        "unique_checklist_items": len(checklist_ids) == len(set(checklist_ids)),
        "known_coverage": coverage_set <= requirement_set,
        "exact_coverage": coverage_set == requirement_set,
        "overlap_free": len(coverage) == len(coverage_set),
        "atomic_checklist": all(len(item.covers) == 1 for item in scenario.checklist),
    }
    item_rows: list[dict[str, Any]] = []
    for item in scenario.checklist:
        known = all(requirement in truth for requirement in item.covers)
        item_truth = known and all(truth[requirement] for requirement in item.covers)
        predicted_pass = item.probability >= 0.5
        item_rows.append(
            {
                "item_id": item.item_id,
                "covers": list(item.covers),
                "truth": item_truth,
                "probability": item.probability,
                "predicted_pass": predicted_pass,
                "correct": predicted_pass == item_truth,
                "brier": round((item.probability - float(item_truth)) ** 2, 12),
            }
        )

    truth_completion = round(sum(truth.values()) / len(truth), 12) if truth else 0.0
    soft_reward = round(
        sum(item.probability for item in scenario.checklist) / len(scenario.checklist),
        12,
    )
    return {
        "scenario_id": scenario.scenario_id,
        "relation": scenario.relation,
        "reference_scenario_id": scenario.reference_scenario_id,
        "requirement_count": len(requirement_ids),
        "checklist_item_count": len(scenario.checklist),
        "truth_completion": truth_completion,
        "soft_reward": soft_reward,
        "reward_inflation": round(soft_reward - truth_completion, 12),
        "checks": checks,
        "items": item_rows,
        "structure_pass": all(checks.values()),
    }


def _atomic_probabilities(result: dict[str, Any]) -> dict[str, float] | None:
    if not result["checks"]["atomic_checklist"]:
        return None
    probabilities: dict[str, float] = {}
    for item in result["items"]:
        covers = item["covers"]
        if len(covers) != 1 or covers[0] in probabilities:
            return None
        probabilities[covers[0]] = float(item["probability"])
    return probabilities


def _pair_result(
    reference: JudgeScenario,
    transformed: JudgeScenario,
    reference_result: dict[str, Any],
    transformed_result: dict[str, Any],
) -> dict[str, Any]:
    reference_truth = _truth(reference)
    transformed_truth = _truth(transformed)
    same_ids = set(reference_truth) == set(transformed_truth)
    changed = sorted(
        item
        for item in set(reference_truth) | set(transformed_truth)
        if reference_truth.get(item) != transformed_truth.get(item)
    )
    reference_probabilities = _atomic_probabilities(reference_result)
    transformed_probabilities = _atomic_probabilities(transformed_result)
    comparable = (
        reference_probabilities is not None
        and transformed_probabilities is not None
        and set(reference_probabilities) == set(transformed_probabilities)
    )
    probability_deltas: dict[str, float] = {}
    if comparable:
        assert reference_probabilities is not None
        assert transformed_probabilities is not None
        probability_deltas = {
            item: round(
                transformed_probabilities[item] - reference_probabilities[item],
                12,
            )
            for item in sorted(reference_probabilities)
        }
    reward_delta = round(
        transformed_result["soft_reward"] - reference_result["soft_reward"],
        12,
    )

    checks: dict[str, bool] = {
        "same_requirement_set": same_ids,
        "atomic_probability_map": comparable,
    }
    if transformed.relation == "atomic_omission":
        affected = changed[0] if len(changed) == 1 else None
        checks.update(
            {
                "one_true_to_false": (
                    affected is not None
                    and reference_truth.get(affected) is True
                    and transformed_truth.get(affected) is False
                ),
                "affected_probability_decreases": (
                    affected is not None and probability_deltas.get(affected, 0.0) <= -0.25
                ),
                "unaffected_probabilities_stable": (
                    comparable
                    and affected is not None
                    and all(
                        abs(delta) <= 0.05
                        for item, delta in probability_deltas.items()
                        if item != affected
                    )
                ),
                "reward_decreases": reward_delta < -0.05,
            }
        )
    elif transformed.relation == "irrelevant_context":
        checks.update(
            {
                "truth_unchanged": not changed,
                "probabilities_stable": (
                    comparable
                    and all(abs(delta) <= 0.05 for delta in probability_deltas.values())
                ),
                "reward_stable": abs(reward_delta) <= 0.05,
            }
        )
    elif transformed.relation == "reorder":
        checks.update(
            {
                "truth_unchanged": not changed,
                "order_changed": (
                    [item.requirement_id for item in reference.requirements]
                    != [item.requirement_id for item in transformed.requirements]
                ),
                "probabilities_stable": (
                    comparable
                    and all(abs(delta) <= 0.05 for delta in probability_deltas.values())
                ),
                "reward_stable": abs(reward_delta) <= 0.05,
            }
        )
    else:
        raise ValueError(f"Unsupported transformed relation: {transformed.relation}")

    return {
        "reference_scenario_id": reference.scenario_id,
        "transformed_scenario_id": transformed.scenario_id,
        "relation": transformed.relation,
        "changed_requirements": changed,
        "probability_deltas": probability_deltas,
        "reward_delta": reward_delta,
        "checks": checks,
        "passed": all(checks.values()),
    }


def audit_judge_payload(value: Any) -> dict[str, Any]:
    """Audit checklist coverage, reward inflation, and paired judge behavior."""

    system_name, scenarios = load_judge_payload(value)
    by_id = {item.scenario_id: item for item in scenarios}
    scenario_results = [_scenario_result(item) for item in scenarios]
    result_by_id = {item["scenario_id"]: item for item in scenario_results}
    pair_results = [
        _pair_result(
            by_id[scenario.reference_scenario_id],
            scenario,
            result_by_id[scenario.reference_scenario_id],
            result_by_id[scenario.scenario_id],
        )
        for scenario in scenarios
        if scenario.reference_scenario_id is not None
    ]
    if not pair_results:
        raise ValueError("at least one transformed scenario is required")

    items = [item for result in scenario_results for item in result["items"]]
    false_items = [item for item in items if not item["truth"]]
    scenario_count = len(scenario_results)
    metrics = {
        "scenario_count": scenario_count,
        "pair_count": len(pair_results),
        "exact_coverage_rate": sum(
            result["checks"]["exact_coverage"] for result in scenario_results
        )
        / scenario_count,
        "overlap_free_rate": sum(
            result["checks"]["overlap_free"] for result in scenario_results
        )
        / scenario_count,
        "atomic_checklist_rate": sum(
            result["checks"]["atomic_checklist"] for result in scenario_results
        )
        / scenario_count,
        "item_accuracy": sum(item["correct"] for item in items) / len(items),
        "item_brier": sum(item["brier"] for item in items) / len(items),
        "false_pass_rate": (
            sum(item["predicted_pass"] for item in false_items) / len(false_items)
            if false_items
            else 0.0
        ),
        "mean_reward_inflation": sum(result["reward_inflation"] for result in scenario_results)
        / scenario_count,
        "max_reward_inflation": max(result["reward_inflation"] for result in scenario_results),
        "metamorphic_pass_rate": sum(result["passed"] for result in pair_results)
        / len(pair_results),
    }
    metrics = {
        key: round(value, 12) if isinstance(value, float) else value
        for key, value in metrics.items()
    }
    hard_gate_checks = {
        "all_checklists_exact_atomic_nonoverlapping": all(
            result["structure_pass"] for result in scenario_results
        ),
        "all_items_classified_correctly": metrics["item_accuracy"] == 1.0,
        "no_false_requirement_passes": metrics["false_pass_rate"] == 0.0,
        "item_brier_at_most_0_10": metrics["item_brier"] <= 0.10,
        "all_metamorphic_relations_pass": metrics["metamorphic_pass_rate"] == 1.0,
    }
    metrics["hard_gate_pass"] = all(hard_gate_checks.values())
    return {
        "judge_audit_schema_version": JUDGE_AUDIT_SCHEMA_VERSION,
        "system_name": system_name,
        "method": "deterministic checklist and metamorphic verifier audit",
        "metrics": metrics,
        "hard_gate_checks": hard_gate_checks,
        "scenarios": scenario_results,
        "pairs": pair_results,
        "claim_boundary": (
            "This audit detects declared checklist and judgment failures in supplied "
            "outputs. It does not prove semantic completeness, model safety, or causal "
            "faithfulness of hidden reasoning."
        ),
    }


def _demo_payload(system_name: str, mode: DemoMode) -> dict[str, Any]:
    requirement_order = (
        "correct_answer",
        "current_period",
        "grounded_citation",
        "access_scope",
    )

    def scenario(
        scenario_id: str,
        relation: RelationKind,
        truth: dict[str, bool],
        *,
        order: tuple[str, ...] = requirement_order,
    ) -> dict[str, Any]:
        requirements = [{"requirement_id": item, "satisfied": truth[item]} for item in order]
        if mode == "collapsed":
            checklist = [
                {
                    "item_id": "overall_quality",
                    "covers": list(order),
                    "probability": 0.96,
                }
            ]
        else:
            checklist = [
                {
                    "item_id": f"check_{item}",
                    "covers": [item],
                    "probability": (0.97 if truth[item] else 0.03)
                    if mode == "calibrated"
                    else 0.96,
                }
                for item in order
            ]
        return {
            "scenario_id": scenario_id,
            "relation": relation,
            "reference_scenario_id": None if relation == "reference" else "reference",
            "requirements": requirements,
            "checklist": checklist,
        }

    all_true = {item: True for item in requirement_order}
    omission = dict(all_true)
    omission["grounded_citation"] = False
    return {
        "schema_version": JUDGE_AUDIT_SCHEMA_VERSION,
        "system_name": system_name,
        "scenarios": [
            scenario("reference", "reference", all_true),
            scenario("citation-omitted", "atomic_omission", omission),
            scenario("irrelevant-context", "irrelevant_context", all_true),
            scenario(
                "requirements-reordered",
                "reorder",
                all_true,
                order=tuple(reversed(requirement_order)),
            ),
        ],
    }


def build_judge_demo() -> tuple[dict[str, Any], ...]:
    """Return one positive and two isolated negative controls."""

    controls: tuple[tuple[str, DemoMode], ...] = (
        ("atomic-calibrated-verifier", "calibrated"),
        ("atomic-permissive-verifier", "permissive"),
        ("collapsed-permissive-verifier", "collapsed"),
    )
    return tuple(audit_judge_payload(_demo_payload(name, mode)) for name, mode in controls)


def render_judge_comparison(reports: tuple[dict[str, Any], ...], path: str | Path) -> Path:
    """Render a standalone, no-network comparison for the audit reports."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cards = []
    for report in reports:
        metrics = report["metrics"]
        gate = "PASS" if metrics["hard_gate_pass"] else "BLOCKED"
        cards.append(
            "<article class='card'>"
            f"<div class='gate {gate.lower()}'>{gate}</div>"
            f"<h2>{html.escape(report['system_name'])}</h2>"
            "<dl>"
            f"<dt>Atomic checklist</dt><dd>{metrics['atomic_checklist_rate']:.0%}</dd>"
            f"<dt>Item accuracy</dt><dd>{metrics['item_accuracy']:.0%}</dd>"
            f"<dt>False-pass rate</dt><dd>{metrics['false_pass_rate']:.0%}</dd>"
            f"<dt>Item Brier</dt><dd>{metrics['item_brier']:.3f}</dd>"
            f"<dt>Paired relations</dt><dd>{metrics['metamorphic_pass_rate']:.0%}</dd>"
            f"<dt>Max reward inflation</dt><dd>{metrics['max_reward_inflation']:+.3f}</dd>"
            "</dl></article>"
        )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FinMirror Judge Audit</title>
<style>
:root{{--ink:#102d3f;--muted:#526573;--line:#d7e0e5;--paper:#f6f8f9;--teal:#007e7e;--red:#a33a3a}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 Arial,sans-serif}}
main{{max-width:1100px;margin:auto;padding:48px 24px 64px}}h1{{font-size:clamp(2rem,5vw,4rem);line-height:1.02;margin:.2em 0}}
.kicker{{color:var(--teal);font-weight:700;letter-spacing:.12em;text-transform:uppercase}}.lede{{max-width:780px;color:var(--muted);font-size:1.1rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px;margin:32px 0}}
.card{{background:white;border:1px solid var(--line);border-radius:14px;padding:22px;box-shadow:0 8px 25px #17324d10}}
.card h2{{font-size:1.1rem;overflow-wrap:anywhere}}.gate{{display:inline-block;padding:4px 9px;border-radius:999px;font-weight:700;font-size:.78rem}}
.pass{{background:#dff4ee;color:#086247}}.blocked{{background:#fbe5e5;color:var(--red)}}dl{{display:grid;grid-template-columns:1fr auto;gap:8px 16px}}
dt{{color:var(--muted)}}dd{{margin:0;font-variant-numeric:tabular-nums;font-weight:700}}.note{{border-left:4px solid var(--teal);padding:4px 0 4px 16px}}
code{{background:#e9eef1;padding:.15em .35em;border-radius:4px}}footer{{margin-top:38px;color:var(--muted);font-size:.9rem}}
</style></head><body><main>
<div class="kicker">FinMirror · deterministic meta-evaluation</div>
<h1>Did the judge reward the right requirement?</h1>
<p class="lede">A zero-model-call audit that separates checklist decomposition defects from permissive verifier judgments, then tests reward behavior under atomic omission, irrelevant context, and requirement reordering.</p>
<section class="grid">{"".join(cards)}</section>
<p class="note"><strong>Positive and negative controls:</strong> all three systems see the same oracle requirement states. Only the atomic calibrated verifier earns the release gate; permissive scores and collapsed checklists fail for different, inspectable reasons.</p>
<p>Reproduce with <code>finmirror judge-demo</code>. Supply external learned-judge outputs with <code>finmirror judge-audit --input audit.json</code>.</p>
<footer>{html.escape(reports[0]["claim_boundary"])}</footer>
</main></body></html>"""
    output.write_text(document, encoding="utf-8", newline="\n")
    return output


def dump_demo_inputs(path: str | Path) -> tuple[Path, ...]:
    """Write the exact synthetic inputs used by the three demo controls."""

    output = Path(path)
    output.mkdir(parents=True, exist_ok=True)
    written = []
    controls: tuple[tuple[str, DemoMode], ...] = (
        ("atomic-calibrated-verifier", "calibrated"),
        ("atomic-permissive-verifier", "permissive"),
        ("collapsed-permissive-verifier", "collapsed"),
    )
    for name, mode in controls:
        target = output / f"{name}-input.json"
        target.write_text(
            json.dumps(_demo_payload(name, mode), indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        written.append(target)
    return tuple(written)
