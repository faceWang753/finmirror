"""Offline contract tests for the Cohere retrieval-audit adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from finmirror.adapters.cohere_retrieval import CohereRetrievalRanker
from finmirror.retrieval_audit import build_retrieval_cases


class FakeRerankClient:
    def __init__(self, results: list[tuple[int, float]]) -> None:
        self.results = results
        self.calls: list[dict[str, Any]] = []

    def rerank(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            results=[
                SimpleNamespace(index=index, relevance_score=score)
                for index, score in self.results
            ]
        )


def _ranker(monkeypatch, results: list[tuple[int, float]]) -> CohereRetrievalRanker:
    monkeypatch.setenv("COHERE_API_KEY", "test-key")
    ranker = CohereRetrievalRanker()
    ranker._client = FakeRerankClient(results)
    return ranker


def test_cohere_rerank_returns_complete_auditable_order(monkeypatch, cases) -> None:
    case = build_retrieval_cases(cases)[0]
    order = list(reversed(range(len(case.candidates))))
    ranker = _ranker(
        monkeypatch,
        [(index, float(len(order) - rank)) for rank, index in enumerate(order)],
    )

    prediction = ranker.rank(case)

    assert prediction.ranked_candidate_ids == tuple(
        case.candidates[index].candidate_id for index in order
    )
    assert prediction.scores == tuple(float(len(order) - rank) for rank in range(len(order)))
    call = ranker._client.calls[0]
    assert call["model"] == "rerank-v4.0-pro"
    assert call["top_n"] == len(case.candidates)
    assert set(call["documents"][0]) == {"title", "text"}
    assert "utility" not in call["documents"][0]


def test_cohere_rerank_rejects_partial_or_duplicate_results(monkeypatch, cases) -> None:
    case = build_retrieval_cases(cases)[0]
    ranker = _ranker(monkeypatch, [(0, 0.9)])
    with pytest.raises(RuntimeError, match="required rankings"):
        ranker.rank(case)

    duplicate = [
        (0, float(len(case.candidates) - index)) for index in range(len(case.candidates))
    ]
    ranker._client = FakeRerankClient(duplicate)
    with pytest.raises(RuntimeError, match="duplicate"):
        ranker.rank(case)


def test_cohere_retrieval_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="COHERE_API_KEY"):
        CohereRetrievalRanker()
