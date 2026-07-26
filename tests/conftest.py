"""Shared, immutable-ish fixtures for FinMirror's deterministic test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from finmirror.adapters.base import run_adapter  # noqa: E402
from finmirror.adapters.baselines import (  # noqa: E402
    EvidenceProgramBaseline,
    MemorizedBaseline,
    OracleAdapter,
)
from finmirror.evaluator import evaluate  # noqa: E402
from finmirror.generator import build_cases  # noqa: E402


@pytest.fixture(scope="session")
def cases():
    """The complete deterministic v0.1 benchmark."""

    return build_cases()


@pytest.fixture(scope="session")
def oracle_predictions(cases):
    return run_adapter(OracleAdapter(cases), cases)


@pytest.fixture(scope="session")
def memorized_predictions(cases):
    return run_adapter(MemorizedBaseline(), cases)


@pytest.fixture(scope="session")
def evidence_program_predictions(cases):
    return run_adapter(EvidenceProgramBaseline(), cases)


@pytest.fixture(scope="session")
def oracle_report(cases, oracle_predictions):
    return evaluate(
        cases,
        oracle_predictions,
        system_name="harness-oracle",
        system_version="test",
        run_metadata={"fixture": True},
    )


@pytest.fixture(scope="session")
def memorized_report(cases, memorized_predictions):
    return evaluate(
        cases,
        memorized_predictions,
        system_name="memorized-evidence-blind",
        system_version="test",
        run_metadata={"fixture": True},
    )


@pytest.fixture(scope="session")
def evidence_program_report(cases, evidence_program_predictions):
    return evaluate(
        cases,
        evidence_program_predictions,
        system_name="evidence-program",
        system_version="test",
        run_metadata={"fixture": True, "uses_gold": False},
    )
