"""Offline baselines that make the benchmark runnable with zero API keys."""

from __future__ import annotations

import re
from typing import ClassVar

from finmirror.adapters.base import Adapter
from finmirror.models import (
    BenchmarkCase,
    CalculationOperand,
    Document,
    ExpectedAnswer,
    Prediction,
    PromptCase,
)
from finmirror.scoring import execute_formula
from finmirror.trace_audit import verified_read_event


def _display(value: float, unit: str) -> str:
    if unit == "percent":
        return f"{value:.1f}%"
    if unit == "ratio":
        return f"{value:.2f}x"
    if unit == "months":
        return f"{value:.1f} months"
    if unit == "usd_millions":
        return f"${value:.1f}m"
    return str(value)


class MemorizedBaseline(Adapter):
    """Intentionally evidence-blind baseline used to demonstrate hidden failures.

    It memorizes each scenario's reference answer. It therefore looks competent on
    unchanged cases, yet fails material perturbations and evidence ablations.
    """

    name = "memorized-evidence-blind"
    version = "0.1"

    _answers: ClassVar[dict[str, tuple[float, str]]] = {
        "revenue_growth": (12.5, "percent"),
        "gross_margin": (35.0, "percent"),
        "debt_to_equity": (0.6, "ratio"),
        "cash_runway": (12.0, "months"),
        "covenant_headroom": (0.8, "ratio"),
        "free_cash_flow": (120.0, "usd_millions"),
    }

    def generate(self, case: PromptCase) -> Prediction:
        value, unit = self._answers[case.scenario_id]
        primary = case.documents[0].id
        return Prediction(
            case_id=case.case_id,
            answer=_display(value, unit),
            value=value,
            unit=unit,
            citations=(f"{primary}#E1", f"{primary}#E2"),
            confidence=0.95,
            pre_confidence=0.91,
            abstained=False,
            retrieved_document_ids=tuple(item.id for item in case.documents),
            metadata={
                "warning": "Demonstration baseline; intentionally ignores evidence values."
            },
        )


class EvidenceProgramBaseline(Adapter):
    """Small non-LLM reference system that reads, cites, and replays evidence.

    This adapter never receives gold answers. It demonstrates the complete public
    contract with an auditable program specialized to the six synthetic workflows.
    """

    name = "evidence-program"
    version = "0.1"

    _operand_names: ClassVar[dict[str, tuple[str, str]]] = {
        "revenue_growth": ("prior", "current"),
        "gross_margin": ("revenue", "cost"),
        "debt_to_equity": ("debt", "equity"),
        "cash_runway": ("cash", "monthly_burn"),
        "covenant_headroom": ("maximum", "actual"),
        "free_cash_flow": ("operating_cash", "capex"),
    }
    _source_units: ClassVar[dict[str, str]] = {
        "covenant_headroom": "turns",
    }

    def _target_document(self, case: PromptCase) -> Document:
        for document in case.documents:
            entity = str(document.metadata.get("entity", ""))
            if entity and entity in case.question:
                return document
        return next(
            (
                document
                for document in case.documents
                if not document.metadata.get("decoy", False)
            ),
            case.documents[0],
        )

    def generate(self, case: PromptCase) -> Prediction:
        document = self._target_document(case)
        extracted: dict[str, float] = {}
        for line in document.content.splitlines():
            anchor_match = re.match(r"^\[(E[12])\]", line.strip())
            if not anchor_match:
                continue
            numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", line)
            if numbers:
                extracted[anchor_match.group(1)] = float(numbers[-1])

        retrieved = (document.id,)
        trace: list[dict[str, object]] = [verified_read_event(document)]
        if "E2" not in extracted:
            missing = f"{document.id}#E2"
            trace.append({"step": "abstain", "missing_evidence": [missing]})
            return Prediction(
                case_id=case.case_id,
                answer="",
                value=None,
                unit=case.expected_unit,
                citations=(),
                confidence=0.05,
                pre_confidence=0.70,
                abstained=True,
                missing_evidence=(missing,),
                retrieved_document_ids=retrieved,
                trace=tuple(trace),
                metadata={"uses_gold": False, "deterministic": True},
            )

        source_unit = self._source_units.get(case.scenario_id, "USD millions")
        operands = tuple(
            CalculationOperand(
                name=name,
                value=extracted[f"E{index}"],
                unit=source_unit,
                evidence=f"{document.id}#E{index}",
            )
            for index, name in enumerate(self._operand_names[case.scenario_id], start=1)
        )
        value = execute_formula(case.scenario_id, operands)
        if value is None:
            raise ValueError(f"Unable to execute formula for {case.case_id}")
        trace.extend(
            [
                {
                    "step": "extract_operands",
                    "evidence": [item.evidence for item in operands],
                },
                {"step": "execute_formula", "formula_id": case.scenario_id},
            ]
        )
        return Prediction(
            case_id=case.case_id,
            answer=_display(value, case.expected_unit),
            value=value,
            unit=case.expected_unit,
            citations=tuple(item.evidence for item in operands),
            confidence=0.98,
            pre_confidence=0.70,
            abstained=False,
            formula_id=case.scenario_id,
            operands=operands,
            retrieved_document_ids=retrieved,
            trace=tuple(trace),
            metadata={"uses_gold": False, "deterministic": True},
        )


class OracleAdapter(Adapter):
    """Gold-reading harness oracle. Never use this as a model baseline."""

    name = "harness-oracle"
    version = "0.1"
    uses_gold = True

    def __init__(self, cases: list[BenchmarkCase]) -> None:
        self._gold: dict[str, ExpectedAnswer] = {case.case_id: case.expected for case in cases}

    def generate(self, case: PromptCase) -> Prediction:
        expected = self._gold[case.case_id]
        if expected.abstain:
            return Prediction(
                case_id=case.case_id,
                answer="",
                value=None,
                unit=expected.unit,
                citations=(),
                confidence=0.02,
                pre_confidence=0.50,
                abstained=True,
                missing_evidence=expected.missing_evidence,
                retrieved_document_ids=tuple(item.id for item in case.documents),
                metadata={"uses_gold": True},
            )
        return Prediction(
            case_id=case.case_id,
            answer=expected.display,
            value=expected.value,
            unit=expected.unit,
            citations=expected.required_evidence,
            confidence=0.99,
            pre_confidence=0.75,
            abstained=False,
            formula_id=expected.formula_id,
            operands=expected.operands,
            retrieved_document_ids=tuple(item.id for item in case.documents),
            metadata={"uses_gold": True},
        )
