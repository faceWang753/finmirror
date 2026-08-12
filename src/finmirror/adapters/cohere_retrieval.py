"""Cohere Rerank adapter for FinMirror's provider-neutral retrieval audit."""

from __future__ import annotations

import os
from typing import Any

from finmirror.retrieval_audit import RetrievalCase, RetrievalPrediction


class CohereRetrievalRanker:
    """Return a complete Cohere Rerank ordering without exposing audit gold."""

    name = "cohere-rerank"
    uses_gold = False

    def __init__(
        self,
        *,
        model: str = "rerank-v4.0-pro",
        api_key: str | None = None,
    ) -> None:
        try:
            import cohere
        except ImportError as exc:
            raise RuntimeError(
                "Cohere support is optional. Install it with: pip install 'finmirror[cohere]'"
            ) from exc
        key = api_key or os.getenv("COHERE_API_KEY")
        if not key:
            raise RuntimeError("COHERE_API_KEY is not configured")
        self._client: Any = cohere.ClientV2(api_key=key)
        self.model = model
        self.version = model

    def rank(self, case: RetrievalCase) -> RetrievalPrediction:
        """Rank every candidate so omissions cannot silently improve the audit."""

        documents = [
            {"title": candidate.title, "text": candidate.text} for candidate in case.candidates
        ]
        response = self._client.rerank(
            model=self.model,
            query=case.query,
            documents=documents,
            top_n=len(documents),
        )
        results = list(response.results)
        if len(results) != len(documents):
            raise RuntimeError(
                f"Cohere returned {len(results)} of {len(documents)} required rankings"
            )
        indices = [int(item.index) for item in results]
        if len(set(indices)) != len(indices) or any(
            index < 0 or index >= len(documents) for index in indices
        ):
            raise RuntimeError("Cohere returned invalid or duplicate document indices")
        return RetrievalPrediction(
            case_id=case.case_id,
            ranked_candidate_ids=tuple(
                case.candidates[index].candidate_id for index in indices
            ),
            scores=tuple(float(item.relevance_score) for item in results),
        )
