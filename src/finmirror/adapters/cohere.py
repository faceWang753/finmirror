"""First-class Cohere Command A+ / Rerank 4 adapter."""

from __future__ import annotations

import os
import time
from typing import Any

from finmirror.adapters.base import Adapter
from finmirror.adapters.structured import (
    FINANCIAL_OUTPUT_SCHEMA,
    PRE_CONFIDENCE_SCHEMA,
    build_financial_prompt,
    build_pre_confidence_prompt,
    parse_probability,
    prediction_from_json,
)
from finmirror.models import Document, Prediction, PromptCase


class CohereAdapter(Adapter):
    """Evaluate Cohere directly, without an orchestration-framework dependency."""

    name = "cohere"
    offline = False

    def __init__(
        self,
        *,
        model: str = "command-a-plus-05-2026",
        api_key: str | None = None,
        rerank_model: str | None = None,
        top_n: int = 5,
        measure_pre_confidence: bool = False,
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
        self._cohere: Any = cohere
        self._client: Any = cohere.ClientV2(api_key=key)
        self.model = model
        self.version = model
        self.rerank_model = rerank_model
        self.top_n = top_n
        self.measure_pre_confidence = measure_pre_confidence

    @staticmethod
    def _response_text(response: Any) -> str:
        content = response.message.content
        if not content:
            raise RuntimeError("Cohere returned no message content")
        for item in content:
            text = getattr(item, "text", None)
            if isinstance(text, str):
                return text
        raise RuntimeError("Cohere returned no text content")

    def _pre_confidence(self, case: PromptCase) -> float | None:
        if not self.measure_pre_confidence:
            return None
        response = self._client.chat(
            model=self.model,
            messages=[
                self._cohere.UserChatMessageV2(content=build_pre_confidence_prompt(case))
            ],
            response_format=self._cohere.JsonObjectResponseFormatV2(
                json_schema=PRE_CONFIDENCE_SCHEMA
            ),
            temperature=0,
        )
        return parse_probability(
            self._response_text(response),
            context="Cohere pre-confidence",
        )

    def _select_documents(self, case: PromptCase) -> tuple[Document, ...]:
        if not self.rerank_model or len(case.documents) <= self.top_n:
            return case.documents
        response = self._client.rerank(
            model=self.rerank_model,
            query=case.question,
            documents=[item.content for item in case.documents],
            top_n=min(self.top_n, len(case.documents)),
        )
        return tuple(case.documents[item.index] for item in response.results)

    def generate(self, case: PromptCase) -> Prediction:
        started = time.perf_counter()
        pre_confidence = self._pre_confidence(case)
        selected = self._select_documents(case)
        response = self._client.chat(
            model=self.model,
            messages=[
                self._cohere.UserChatMessageV2(content=build_financial_prompt(case, selected))
            ],
            response_format=self._cohere.JsonObjectResponseFormatV2(
                json_schema=FINANCIAL_OUTPUT_SCHEMA
            ),
            temperature=0,
        )
        raw = self._response_text(response)
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "tokens", None)
        input_tokens = int(getattr(tokens, "input_tokens", 0) or 0)
        output_tokens = int(getattr(tokens, "output_tokens", 0) or 0)
        response_id = str(getattr(response, "id", ""))
        return prediction_from_json(
            raw,
            case=case,
            pre_confidence=pre_confidence,
            retrieved_document_ids=tuple(item.id for item in selected),
            latency_ms=(time.perf_counter() - started) * 1000,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata={
                "provider": "cohere",
                "model": self.model,
                "rerank_model": self.rerank_model,
                "response_id": response_id,
            },
            trace=(
                {
                    "event": "model_response",
                    "provider": "cohere",
                    "model": self.model,
                    "response_id": response_id,
                },
            ),
            context="Cohere",
        )
