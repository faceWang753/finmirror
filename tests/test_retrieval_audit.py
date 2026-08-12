from __future__ import annotations

import json
from dataclasses import replace

import pytest

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


def test_packet_is_anchor_level_and_hides_utility(cases, tmp_path) -> None:
    retrieval_cases = build_retrieval_cases(cases)
    collision = next(
        case for case in retrieval_cases if case.case_id == "fm-cash_runway-en-entity_collision"
    )
    assert len(collision.candidates) == 5
    assert sum(candidate.utility < 0 for candidate in collision.candidates) == 3
    assert len(collision.required_candidate_ids) == 2

    packet = tmp_path / "packet.jsonl"
    dump_retrieval_packet(retrieval_cases, packet)
    first = json.loads(packet.read_text(encoding="utf-8").splitlines()[0])
    assert "utility" not in json.dumps(first)
    assert "pair_group_id" not in first


def test_oracle_is_positive_control_but_cannot_pass_public_gate(cases) -> None:
    retrieval_cases = build_retrieval_cases(cases)
    ranker = RetrievalOracleRanker()
    report = audit_retrieval_rankings(
        retrieval_cases,
        run_retrieval_ranker(ranker, retrieval_cases),
        system_name=ranker.name,
        uses_gold=ranker.uses_gold,
    )
    assert report["metrics"]["clean_completion_rate"] == 1.0
    assert report["metrics"]["paired_reliability"] == 1.0
    assert report["metrics"]["hard_gate_pass"] is False


def test_input_order_control_exposes_entity_collision(cases) -> None:
    retrieval_cases = build_retrieval_cases(cases)
    ranker = InputOrderRanker()
    report = audit_retrieval_rankings(
        retrieval_cases,
        run_retrieval_ranker(ranker, retrieval_cases),
        system_name=ranker.name,
    )
    assert report["metrics"]["clean_completion_rate"] < 1.0
    assert report["metrics"]["paired_reliability"] < 1.0
    collision = next(
        row
        for row in report["case_results"]
        if row["case_id"] == "fm-cash_runway-en-entity_collision"
    )
    assert collision["harmful_before_sufficient"] == 2
    assert collision["clean_completion"] is False


def test_lexical_predictions_round_trip_and_render(cases, tmp_path) -> None:
    retrieval_cases = build_retrieval_cases(cases)
    ranker = LexicalOverlapRanker()
    predictions = run_retrieval_ranker(ranker, retrieval_cases)
    path = tmp_path / "predictions.jsonl"
    save_retrieval_predictions(predictions, path)
    loaded = load_retrieval_predictions(path)
    assert loaded == predictions
    report = audit_retrieval_rankings(
        retrieval_cases,
        loaded,
        system_name=ranker.name,
    )
    rendered = tmp_path / "index.html"
    render_retrieval_comparison([report], rendered)
    assert "Paired reliability" in rendered.read_text(encoding="utf-8")


def test_ranking_contract_rejects_omissions_duplicates_and_bad_scores(cases) -> None:
    retrieval_cases = build_retrieval_cases(cases[:1])
    valid = run_retrieval_ranker(InputOrderRanker(), retrieval_cases)[0]
    with pytest.raises(ValueError, match="complete permutation"):
        audit_retrieval_rankings(
            retrieval_cases,
            [replace(valid, ranked_candidate_ids=valid.ranked_candidate_ids[:-1])],
            system_name="broken",
        )
    duplicate = (valid.ranked_candidate_ids[0],) * len(valid.ranked_candidate_ids)
    with pytest.raises(ValueError, match="duplicate candidate"):
        audit_retrieval_rankings(
            retrieval_cases,
            [replace(valid, ranked_candidate_ids=duplicate)],
            system_name="broken",
        )
    bad_scores = (float("nan"), *valid.scores[1:])
    with pytest.raises(ValueError, match="non-finite"):
        audit_retrieval_rankings(
            retrieval_cases,
            [replace(valid, scores=bad_scores)],
            system_name="broken",
        )


def test_unanswerable_ablation_is_disclosed_not_misattributed(cases) -> None:
    retrieval_cases = build_retrieval_cases(cases)
    ranker = RetrievalOracleRanker()
    report = audit_retrieval_rankings(
        retrieval_cases,
        run_retrieval_ranker(ranker, retrieval_cases),
        system_name=ranker.name,
        uses_gold=True,
    )
    ablation_pairs = [
        row for row in report["pair_results"] if row["expectation"] == "should_abstain"
    ]
    assert ablation_pairs
    assert all(row["passed"] is None for row in ablation_pairs)
    assert all("reranker alone" in row["reason"] for row in ablation_pairs)
