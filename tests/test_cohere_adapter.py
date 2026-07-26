"""Contract tests for the optional Cohere v2 adapter without network calls."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from finmirror.adapters.cohere import CohereAdapter


class FakeClient:
    def __init__(
        self,
        payloads: list[dict[str, Any]],
        *,
        rerank_indices: list[int] | None = None,
    ) -> None:
        self.payloads = list(payloads)
        self.rerank_indices = rerank_indices or []
        self.chat_calls: list[dict[str, Any]] = []
        self.rerank_calls: list[dict[str, Any]] = []

    def chat(self, **kwargs: Any) -> Any:
        self.chat_calls.append(kwargs)
        payload = self.payloads.pop(0)
        return SimpleNamespace(
            id="fake-response",
            message=SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))]),
            usage=SimpleNamespace(tokens=SimpleNamespace(input_tokens=123, output_tokens=45)),
        )

    def rerank(self, **kwargs: Any) -> Any:
        self.rerank_calls.append(kwargs)
        return SimpleNamespace(
            results=[SimpleNamespace(index=index) for index in self.rerank_indices]
        )


def _answer_payload(case) -> dict[str, Any]:
    return {
        "answer": case.expected.display,
        "value": str(case.expected.value),
        "unit": case.expected.unit,
        "citations": list(case.expected.required_evidence),
        "confidence": 0.92,
        "abstained": False,
        "formula_id": case.expected.formula_id,
        "operands": [item.to_dict() for item in case.expected.operands],
        "missing_evidence": [],
    }


def test_missing_api_key_fails_closed(monkeypatch) -> None:
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="COHERE_API_KEY"):
        CohereAdapter()


def test_structured_generation_uses_current_v2_types(monkeypatch, cases) -> None:
    monkeypatch.setenv("COHERE_API_KEY", "test-key")
    case = next(item for item in cases if item.case_id == "fm-revenue_growth-en-reference")
    adapter = CohereAdapter()
    client = FakeClient([_answer_payload(case)])
    adapter._client = client

    prediction = adapter.generate(case.prompt_case())

    assert prediction.case_id == case.case_id
    assert prediction.value == pytest.approx(case.expected.value)
    assert prediction.formula_id == "revenue_growth"
    assert prediction.operands == case.expected.operands
    assert prediction.input_tokens == 123
    assert prediction.output_tokens == 45
    assert prediction.metadata["response_id"] == "fake-response"
    call = client.chat_calls[0]
    assert call["messages"][0].role == "user"
    assert "DOCUMENT_ID#ANCHOR" in call["messages"][0].content
    assert call["response_format"].type == "json_object"
    assert call["response_format"].json_schema["required"]


def test_pre_confidence_is_a_separate_call(monkeypatch, cases) -> None:
    monkeypatch.setenv("COHERE_API_KEY", "test-key")
    case = cases[0]
    adapter = CohereAdapter(measure_pre_confidence=True)
    client = FakeClient(
        [
            {"success_probability": 1.7},
            _answer_payload(case),
        ]
    )
    adapter._client = client

    prediction = adapter.generate(case.prompt_case())

    assert prediction.pre_confidence == 1.0
    assert len(client.chat_calls) == 2
    assert "if given a relevant evidence packet" in client.chat_calls[0]["messages"][0].content


def test_optional_reranker_reports_selected_target(monkeypatch, cases) -> None:
    monkeypatch.setenv("COHERE_API_KEY", "test-key")
    case = next(
        item for item in cases if item.case_id == "fm-revenue_growth-en-entity_collision"
    )
    assert case.documents[0].metadata["decoy"] is True
    adapter = CohereAdapter(rerank_model="rerank-v4.0-pro", top_n=1)
    client = FakeClient([_answer_payload(case)], rerank_indices=[1])
    adapter._client = client

    prediction = adapter.generate(case.prompt_case())

    assert prediction.retrieved_document_ids == (case.documents[1].id,)
    assert len(client.rerank_calls) == 1
    assert client.rerank_calls[0]["top_n"] == 1


def test_no_text_response_is_rejected() -> None:
    response = SimpleNamespace(message=SimpleNamespace(content=[]))
    with pytest.raises(RuntimeError, match="no message content"):
        CohereAdapter._response_text(response)
    response.message.content = [SimpleNamespace(thinking="hidden")]
    with pytest.raises(RuntimeError, match="no text content"):
        CohereAdapter._response_text(response)
