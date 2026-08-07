"""Contract tests for OpenAI-compatible endpoints with no network access."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

import finmirror.adapters.openai_compatible as compatible_module
from finmirror.adapters.openai_compatible import OpenAICompatibleAdapter
from finmirror.cli import build_parser


class FakeCompletions:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        content = response if isinstance(response, str) else json.dumps(response)
        return SimpleNamespace(
            id="chatcmpl-test",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=321, completion_tokens=87),
        )


class FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def _answer_payload(case: Any) -> dict[str, Any]:
    return {
        "answer": case.expected.display,
        "value": str(case.expected.value),
        "unit": case.expected.unit,
        "citations": list(case.expected.required_evidence),
        "confidence": 0.91,
        "abstained": False,
        "formula_id": case.expected.formula_id,
        "operands": [item.to_dict() for item in case.expected.operands],
        "missing_evidence": [],
    }


def _abstention_payload(case: Any) -> dict[str, Any]:
    return {
        "answer": "Insufficient evidence",
        "value": "",
        "unit": case.expected.unit,
        "citations": [],
        "confidence": 0.12,
        "abstained": True,
        "formula_id": "",
        "operands": [],
        "missing_evidence": list(case.expected.missing_evidence),
    }


def test_successful_response_preserves_contract_and_safe_trace(cases) -> None:
    case = next(item for item in cases if item.case_id == "fm-revenue_growth-en-reference")
    client = FakeClient([_answer_payload(case)])
    adapter = OpenAICompatibleAdapter(
        model="local-test-model",
        base_url="http://127.0.0.1:8000/v1",
        client=client,
    )

    prediction = adapter.generate(case.prompt_case())

    assert adapter.offline is True
    assert prediction.value == pytest.approx(case.expected.value)
    assert prediction.citations == case.expected.required_evidence
    assert prediction.operands == case.expected.operands
    assert prediction.input_tokens == 321
    assert prediction.output_tokens == 87
    assert prediction.metadata == {
        "provider": "openai-compatible",
        "model": "local-test-model",
        "response_id": "chatcmpl-test",
        "finish_reason": "stop",
        "endpoint_kind": "local",
    }
    assert prediction.trace == (
        {
            "event": "model_response",
            **prediction.metadata,
        },
    )
    call = client.completions.calls[0]
    assert call["temperature"] == 0
    assert call["response_format"]["type"] == "json_schema"
    schema = call["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["additionalProperties"] is False
    assert "DOCUMENT_ID#ANCHOR" in call["messages"][0]["content"]


def test_abstention_and_pre_confidence_are_normalized(cases) -> None:
    case = next(item for item in cases if item.expected.abstain)
    client = FakeClient(
        [
            {"success_probability": 1.4},
            _abstention_payload(case),
        ]
    )
    adapter = OpenAICompatibleAdapter(
        model="test-model",
        measure_pre_confidence=True,
        client=client,
    )

    prediction = adapter.generate(case.prompt_case())

    assert prediction.pre_confidence == 1.0
    assert prediction.abstained is True
    assert prediction.value == ""
    assert prediction.formula_id == ""
    assert prediction.operands == ()
    assert prediction.missing_evidence == case.expected.missing_evidence
    assert len(client.completions.calls) == 2


def test_malformed_json_fails_without_echoing_model_output(cases) -> None:
    secret_output = "not-json PRIVATE-EVIDENCE-CONTENT"
    adapter = OpenAICompatibleAdapter(
        model="test-model",
        client=FakeClient([secret_output]),
    )

    with pytest.raises(RuntimeError, match="invalid JSON") as raised:
        adapter.generate(cases[0].prompt_case())

    assert "PRIVATE-EVIDENCE-CONTENT" not in str(raised.value)


def test_timeout_is_wrapped_without_leaking_provider_message(cases) -> None:
    adapter = OpenAICompatibleAdapter(
        model="test-model",
        client=FakeClient([TimeoutError("Bearer secret-key and confidential evidence")]),
    )

    with pytest.raises(RuntimeError, match=r"request failed \(TimeoutError\)") as raised:
        adapter.generate(cases[0].prompt_case())

    assert "secret-key" not in str(raised.value)
    assert "confidential evidence" not in str(raised.value)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"model": None}, "--model or OPENAI_MODEL"),
        ({"model": "x", "timeout": 0}, "timeout must be positive"),
        ({"model": "x", "max_retries": -1}, "retries cannot be negative"),
    ],
)
def test_configuration_fails_closed(monkeypatch, kwargs, match) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    with pytest.raises((RuntimeError, ValueError), match=match):
        OpenAICompatibleAdapter(client=FakeClient([]), **kwargs)


def test_loopback_endpoint_can_initialize_without_an_api_key(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeOpenAIModule:
        @staticmethod
        def OpenAI(**kwargs: Any) -> FakeClient:
            captured.update(kwargs)
            return FakeClient([])

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        compatible_module.importlib,
        "import_module",
        lambda _name: FakeOpenAIModule,
    )

    adapter = OpenAICompatibleAdapter(
        model="local-model",
        base_url="http://localhost:8000/v1",
    )

    assert adapter.offline is True
    assert captured["base_url"] == "http://localhost:8000/v1"
    assert captured["api_key"] == "local-endpoint-no-key"


def test_cli_exposes_compatible_endpoint_controls() -> None:
    args = build_parser().parse_args(
        [
            "run",
            "--adapter",
            "openai",
            "--model",
            "served-model",
            "--base-url",
            "http://localhost:8000/v1",
            "--request-timeout",
            "45",
            "--max-retries",
            "1",
            "--measure-pre-confidence",
        ]
    )

    assert args.adapter == "openai"
    assert args.model == "served-model"
    assert args.base_url == "http://localhost:8000/v1"
    assert args.request_timeout == 45.0
    assert args.max_retries == 1
    assert args.measure_pre_confidence is True
