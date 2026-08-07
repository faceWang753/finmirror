"""Adapter interface and leak-resistant execution loop."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import replace

from finmirror.models import BenchmarkCase, Prediction, PromptCase


class Adapter(ABC):
    """One provider or agent implementation under evaluation."""

    name: str
    version: str = ""
    uses_gold: bool = False
    offline: bool = True

    @abstractmethod
    def generate(self, case: PromptCase) -> Prediction:
        """Produce a normalized prediction without access to gold data."""


def run_adapter(adapter: Adapter, cases: list[BenchmarkCase]) -> list[Prediction]:
    """Run an adapter sequentially with wall-clock timing."""

    predictions: list[Prediction] = []
    for case in cases:
        started = time.perf_counter()
        prediction = adapter.generate(case.prompt_case())
        elapsed_ms = (time.perf_counter() - started) * 1000
        if prediction.case_id != case.case_id:
            raise ValueError(
                f"Adapter returned {prediction.case_id!r} for case {case.case_id!r}"
            )
        if prediction.latency_ms <= 0:
            prediction = replace(prediction, latency_ms=elapsed_ms)
        predictions.append(prediction)
    return predictions
