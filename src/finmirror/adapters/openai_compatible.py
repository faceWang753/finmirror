"""OpenAI-compatible chat-completions adapter for hosted and local endpoints."""

from __future__ import annotations

import importlib
import os
import time
from typing import Any
from urllib.parse import urlparse

from finmirror.adapters.base import Adapter
from finmirror.adapters.structured import (
    FINANCIAL_OUTPUT_SCHEMA,
    PRE_CONFIDENCE_SCHEMA,
    build_financial_prompt,
    build_pre_confidence_prompt,
    parse_probability,
    prediction_from_json,
)
from finmirror.models import Prediction, PromptCase


def _is_loopback_url(value: str | None) -> bool:
    if not value:
        return False
    hostname = urlparse(value).hostname
    return hostname in {"localhost", "127.0.0.1", "::1"}


def _response_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": schema,
        },
    }


class OpenAICompatibleAdapter(Adapter):
    """Run the FinMirror contract through a chat-completions compatible endpoint."""

    name = "openai-compatible"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 2,
        measure_pre_confidence: bool = False,
        client: Any | None = None,
    ) -> None:
        selected_model = model or os.getenv("OPENAI_MODEL")
        if not selected_model:
            raise RuntimeError("Set --model or OPENAI_MODEL for the OpenAI-compatible adapter")
        if timeout <= 0:
            raise ValueError("request timeout must be positive")
        if max_retries < 0:
            raise ValueError("max retries cannot be negative")

        configured_base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.offline = _is_loopback_url(configured_base_url)
        if client is None:
            try:
                openai = importlib.import_module("openai")
            except ImportError as exc:
                raise RuntimeError(
                    "OpenAI-compatible support is optional. Install it with: "
                    "pip install 'finmirror[openai]'"
                ) from exc
            key = api_key or os.getenv("OPENAI_API_KEY")
            if not key and self.offline:
                key = "local-endpoint-no-key"
            if not key:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            client_options: dict[str, Any] = {
                "api_key": key,
                "timeout": timeout,
                "max_retries": max_retries,
            }
            if configured_base_url:
                client_options["base_url"] = configured_base_url
            self._client: Any = openai.OpenAI(**client_options)
        else:
            self._client = client

        self.model = selected_model
        self.version = selected_model
        self.measure_pre_confidence = measure_pre_confidence
        self._endpoint_kind = "local" if self.offline else "hosted-or-remote"

    @staticmethod
    def _response_text(response: Any) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            raise RuntimeError("OpenAI-compatible endpoint returned no choices")
        content = getattr(getattr(choices[0], "message", None), "content", None)
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenAI-compatible endpoint returned no text content")
        return content

    def _chat(self, prompt: str, *, response_name: str, schema: dict[str, Any]) -> Any:
        try:
            return self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format=_response_format(response_name, schema),
                temperature=0,
            )
        except Exception as exc:
            # Some SDKs include request bodies, credentials, or evidence in errors.
            # Preserve the exception type for diagnosis without echoing its message.
            raise RuntimeError(
                f"OpenAI-compatible request failed ({type(exc).__name__})"
            ) from exc

    def _pre_confidence(self, case: PromptCase) -> float | None:
        if not self.measure_pre_confidence:
            return None
        response = self._chat(
            build_pre_confidence_prompt(case),
            response_name="finmirror_pre_confidence",
            schema=PRE_CONFIDENCE_SCHEMA,
        )
        return parse_probability(
            self._response_text(response),
            context="OpenAI-compatible pre-confidence",
        )

    def generate(self, case: PromptCase) -> Prediction:
        started = time.perf_counter()
        pre_confidence = self._pre_confidence(case)
        response = self._chat(
            build_financial_prompt(case, case.documents),
            response_name="finmirror_prediction",
            schema=FINANCIAL_OUTPUT_SCHEMA,
        )
        raw = self._response_text(response)
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        choice = response.choices[0]
        response_id = str(getattr(response, "id", ""))
        finish_reason = str(getattr(choice, "finish_reason", ""))
        trace = (
            {
                "event": "model_response",
                "provider": "openai-compatible",
                "model": self.model,
                "response_id": response_id,
                "finish_reason": finish_reason,
                "endpoint_kind": self._endpoint_kind,
            },
        )
        return prediction_from_json(
            raw,
            case=case,
            pre_confidence=pre_confidence,
            retrieved_document_ids=tuple(item.id for item in case.documents),
            latency_ms=(time.perf_counter() - started) * 1000,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata={
                "provider": "openai-compatible",
                "model": self.model,
                "response_id": response_id,
                "finish_reason": finish_reason,
                "endpoint_kind": self._endpoint_kind,
            },
            trace=trace,
            context="OpenAI-compatible endpoint",
        )
