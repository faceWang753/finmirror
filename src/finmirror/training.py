"""Export deterministic reward vectors and pairwise preference data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finmirror.dataset import canonical_json
from finmirror.models import BenchmarkCase, Prediction
from finmirror.scoring import score_case


def _prompt(case: BenchmarkCase) -> str:
    documents = "\n\n".join(
        f"DOCUMENT {item.id} — {item.title}\n{item.content}" for item in case.documents
    )
    return (
        "Answer from the evidence packet. Cite every required operand and abstain "
        "when evidence is insufficient.\n\n"
        f"QUESTION ({case.language}):\n{case.question}\n\n"
        f"EVIDENCE:\n{documents}"
    )


def _reward_vector(case: BenchmarkCase, prediction: Prediction) -> dict[str, float]:
    result = score_case(case, prediction)
    calibration = 1.0 if result.brier is None else max(0.0, 1.0 - result.brier)
    return {
        "answer": result.answer_score,
        "unit": result.unit_score,
        "evidence": result.citation_f1,
        "formula": result.formula_score,
        "operands": result.operand_score,
        "clarification": result.clarification_score,
        "abstention": result.abstention_score,
        "contract": result.contract_score,
        "calibration": calibration,
    }


def _utility(reward: dict[str, float]) -> float:
    """Training-only utility; critical answer/evidence errors do not compensate."""

    hard_gate = reward["answer"] * reward["unit"] * reward["abstention"]
    if reward["answer"] and reward["formula"] == 0:
        hard_gate = 0.0
    if hard_gate == 0:
        return 0.10 * reward["contract"] + 0.05 * reward["calibration"]
    return (
        0.30 * reward["answer"]
        + 0.10 * reward["unit"]
        + 0.15 * reward["evidence"]
        + 0.15 * reward["formula"]
        + 0.10 * reward["operands"]
        + 0.05 * reward["clarification"]
        + 0.10 * reward["abstention"]
        + 0.025 * reward["contract"]
        + 0.025 * reward["calibration"]
    )


def export_preferences(
    cases: list[BenchmarkCase],
    left: list[Prediction],
    right: list[Prediction],
    output: str | Path,
) -> dict[str, int]:
    """Create DPO-style chosen/rejected records from deterministic verifier rewards."""

    left_map = {item.case_id: item for item in left}
    right_map = {item.case_id: item for item in right}
    expected_ids = {case.case_id for case in cases}
    if set(left_map) != expected_ids or set(right_map) != expected_ids:
        raise ValueError("Both prediction files must contain exactly one row per case")

    records: list[dict[str, Any]] = []
    ties = 0
    for case in sorted(cases, key=lambda item: item.case_id):
        candidates = (left_map[case.case_id], right_map[case.case_id])
        rewards = tuple(_reward_vector(case, item) for item in candidates)
        utilities = tuple(_utility(item) for item in rewards)
        if abs(utilities[0] - utilities[1]) < 1e-9:
            ties += 1
            continue
        chosen_index = 0 if utilities[0] > utilities[1] else 1
        rejected_index = 1 - chosen_index
        records.append(
            {
                "case_id": case.case_id,
                "prompt": _prompt(case),
                "chosen": candidates[chosen_index].to_dict(),
                "rejected": candidates[rejected_index].to_dict(),
                "chosen_reward": rewards[chosen_index],
                "rejected_reward": rewards[rejected_index],
                "chosen_utility": utilities[chosen_index],
                "rejected_utility": utilities[rejected_index],
                "provenance": {
                    "generator": "finmirror deterministic verifier",
                    "benchmark_version": "0.1.0",
                    "human_reviewed": False,
                },
            }
        )
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(canonical_json(item) for item in records) + ("\n" if records else ""),
        encoding="utf-8",
        newline="\n",
    )
    return {"exported": len(records), "ties_skipped": ties}


def load_predictions(path: str | Path) -> list[Prediction]:
    predictions: list[Prediction] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if not isinstance(data, dict):
                    raise ValueError("row is not an object")
                predictions.append(Prediction.from_dict(data))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid prediction on line {line_number}: {exc}") from exc
    return predictions


def save_predictions(predictions: list[Prediction], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(canonical_json(item.to_dict()) for item in predictions) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output
