"""Tests for prediction I/O and deterministic preference export."""

from __future__ import annotations

import json

import pytest

from finmirror.training import (
    export_preferences,
    load_predictions,
    save_predictions,
)


def test_prediction_jsonl_round_trip(tmp_path, oracle_predictions) -> None:
    output = save_predictions(oracle_predictions, tmp_path / "oracle.jsonl")
    loaded = load_predictions(output)
    assert [item.to_dict() for item in loaded] == [
        item.to_dict() for item in oracle_predictions
    ]
    assert output.read_text(encoding="utf-8").endswith("\n")


def test_oracle_is_preferred_to_memorized_baseline(
    tmp_path,
    cases,
    oracle_predictions,
    memorized_predictions,
) -> None:
    output = tmp_path / "preferences.jsonl"
    summary = export_preferences(
        cases,
        oracle_predictions,
        memorized_predictions,
        output,
    )
    assert summary == {"exported": 126, "ties_skipped": 0}
    rows = [
        json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line
    ]
    assert len(rows) == 126
    assert all(row["chosen_utility"] > row["rejected_utility"] for row in rows)
    assert all(row["chosen"]["metadata"]["uses_gold"] is True for row in rows)
    assert all(
        row["provenance"]["generator"] == "finmirror deterministic verifier" for row in rows
    )
    assert all("DOCUMENT " in row["prompt"] and "QUESTION (" in row["prompt"] for row in rows)


def test_identical_candidates_are_skipped_as_ties(
    tmp_path,
    cases,
    oracle_predictions,
) -> None:
    output = tmp_path / "ties.jsonl"
    summary = export_preferences(cases, oracle_predictions, oracle_predictions, output)
    assert summary == {"exported": 0, "ties_skipped": 126}
    assert output.read_text(encoding="utf-8") == ""


def test_preference_export_requires_exact_case_coverage(
    tmp_path,
    cases,
    oracle_predictions,
    memorized_predictions,
) -> None:
    with pytest.raises(ValueError, match="exactly one row per case"):
        export_preferences(
            cases,
            oracle_predictions[:-1],
            memorized_predictions,
            tmp_path / "invalid.jsonl",
        )


def test_invalid_prediction_row_reports_line_number(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"case_id":"incomplete"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        load_predictions(path)
