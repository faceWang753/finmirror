"""Typed, dependency-free data contracts used across FinMirror."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

AnswerType = Literal["number", "text"]
Expectation = Literal[
    "reference",
    "should_change",
    "should_not_change",
    "should_abstain",
]


def _missing(data: dict[str, Any], required: set[str]) -> set[str]:
    return required.difference(data)


@dataclass(frozen=True)
class Document:
    """One evidence document supplied to an agent."""

    id: str
    title: str
    content: str
    source_url: str = ""
    media_type: str = "text/plain"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        missing = _missing(data, {"id", "title", "content"})
        if missing:
            raise ValueError(f"Document is missing fields: {sorted(missing)}")
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            content=str(data["content"]),
            source_url=str(data.get("source_url", "")),
            media_type=str(data.get("media_type", "text/plain")),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CalculationOperand:
    """One typed input to a deterministic financial calculation program."""

    name: str
    value: float
    unit: str
    evidence: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalculationOperand:
        missing = _missing(data, {"name", "value", "unit", "evidence"})
        if missing:
            raise ValueError(f"Calculation operand is missing fields: {sorted(missing)}")
        return cls(
            name=str(data["name"]),
            value=float(data["value"]),
            unit=str(data["unit"]),
            evidence=str(data["evidence"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExpectedAnswer:
    """Gold answer and minimum sufficient evidence."""

    answer_type: AnswerType
    value: float | str | None
    unit: str
    display: str
    tolerance: float
    required_evidence: tuple[str, ...]
    abstain: bool = False
    formula: str = ""
    formula_id: str = ""
    operands: tuple[CalculationOperand, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    materiality: float = 1.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpectedAnswer:
        missing = _missing(
            data,
            {
                "answer_type",
                "value",
                "unit",
                "display",
                "tolerance",
                "required_evidence",
            },
        )
        if missing:
            raise ValueError(f"Expected answer is missing fields: {sorted(missing)}")
        answer_type = str(data["answer_type"])
        if answer_type not in {"number", "text"}:
            raise ValueError(f"Unsupported answer_type: {answer_type}")
        raw_value = data["value"]
        value: float | str | None
        if raw_value is None:
            value = None
        elif answer_type == "number":
            value = float(raw_value)
        else:
            value = str(raw_value)
        return cls(
            answer_type=answer_type,  # type: ignore[arg-type]
            value=value,
            unit=str(data["unit"]),
            display=str(data["display"]),
            tolerance=float(data["tolerance"]),
            required_evidence=tuple(str(item) for item in data["required_evidence"]),
            abstain=bool(data.get("abstain", False)),
            formula=str(data.get("formula", "")),
            formula_id=str(data.get("formula_id", "")),
            operands=tuple(
                CalculationOperand.from_dict(dict(item)) for item in data.get("operands", [])
            ),
            missing_evidence=tuple(str(item) for item in data.get("missing_evidence", [])),
            materiality=float(data.get("materiality", 1.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["required_evidence"] = list(self.required_evidence)
        data["operands"] = [item.to_dict() for item in self.operands]
        data["missing_evidence"] = list(self.missing_evidence)
        return data


@dataclass(frozen=True)
class Relationship:
    """How this case should behave relative to its reference case."""

    reference_case_id: str | None
    transform: str
    expectation: Expectation
    changed_fields: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Relationship:
        missing = _missing(data, {"transform", "expectation"})
        if missing:
            raise ValueError(f"Relationship is missing fields: {sorted(missing)}")
        expectation = str(data["expectation"])
        allowed = {
            "reference",
            "should_change",
            "should_not_change",
            "should_abstain",
        }
        if expectation not in allowed:
            raise ValueError(f"Unsupported expectation: {expectation}")
        reference = data.get("reference_case_id")
        return cls(
            reference_case_id=None if reference is None else str(reference),
            transform=str(data["transform"]),
            expectation=expectation,  # type: ignore[arg-type]
            changed_fields=tuple(str(item) for item in data.get("changed_fields", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["changed_fields"] = list(self.changed_fields)
        return data


@dataclass(frozen=True)
class BenchmarkCase:
    """A complete benchmark case, including hidden gold data."""

    case_id: str
    scenario_id: str
    pair_group_id: str
    parallel_id: str
    language: str
    question: str
    task_type: str
    documents: tuple[Document, ...]
    expected: ExpectedAnswer
    relationship: Relationship
    tags: tuple[str, ...] = ()
    stakeholder: str = "financial_analyst"
    harm_if_wrong: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkCase:
        required = {
            "case_id",
            "scenario_id",
            "pair_group_id",
            "parallel_id",
            "language",
            "question",
            "task_type",
            "documents",
            "expected",
            "relationship",
        }
        missing = _missing(data, required)
        if missing:
            raise ValueError(f"Case is missing fields: {sorted(missing)}")
        return cls(
            case_id=str(data["case_id"]),
            scenario_id=str(data["scenario_id"]),
            pair_group_id=str(data["pair_group_id"]),
            parallel_id=str(data["parallel_id"]),
            language=str(data["language"]),
            question=str(data["question"]),
            task_type=str(data["task_type"]),
            documents=tuple(Document.from_dict(item) for item in data["documents"]),
            expected=ExpectedAnswer.from_dict(dict(data["expected"])),
            relationship=Relationship.from_dict(dict(data["relationship"])),
            tags=tuple(str(item) for item in data.get("tags", [])),
            stakeholder=str(data.get("stakeholder", "financial_analyst")),
            harm_if_wrong=str(data.get("harm_if_wrong", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "scenario_id": self.scenario_id,
            "pair_group_id": self.pair_group_id,
            "parallel_id": self.parallel_id,
            "language": self.language,
            "question": self.question,
            "task_type": self.task_type,
            "documents": [item.to_dict() for item in self.documents],
            "expected": self.expected.to_dict(),
            "relationship": self.relationship.to_dict(),
            "tags": list(self.tags),
            "stakeholder": self.stakeholder,
            "harm_if_wrong": self.harm_if_wrong,
        }

    def prompt_case(self) -> PromptCase:
        """Strip gold data before an adapter sees the case."""

        return PromptCase(
            case_id=self.case_id,
            scenario_id=self.scenario_id,
            language=self.language,
            question=self.question,
            task_type=self.task_type,
            expected_unit=self.expected.unit,
            documents=self.documents,
            tags=self.tags,
        )


@dataclass(frozen=True)
class PromptCase:
    """The non-leaky view supplied to an evaluated system."""

    case_id: str
    scenario_id: str
    language: str
    question: str
    task_type: str
    expected_unit: str
    documents: tuple[Document, ...]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Prediction:
    """A system response normalized into FinMirror's submission contract."""

    case_id: str
    answer: str
    value: float | str | None
    unit: str
    citations: tuple[str, ...]
    confidence: float
    abstained: bool
    formula_id: str = ""
    operands: tuple[CalculationOperand, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    pre_confidence: float | None = None
    retrieved_document_ids: tuple[str, ...] = ()
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    trace: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Prediction:
        missing = _missing(
            data,
            {
                "case_id",
                "answer",
                "value",
                "unit",
                "citations",
                "confidence",
                "abstained",
            },
        )
        if missing:
            raise ValueError(f"Prediction is missing fields: {sorted(missing)}")
        raw_value = data["value"]
        value: float | str | None
        if raw_value is None:
            value = None
        elif isinstance(raw_value, (int, float)):
            value = float(raw_value)
        else:
            value = str(raw_value)
        pre = data.get("pre_confidence")
        return cls(
            case_id=str(data["case_id"]),
            answer=str(data["answer"]),
            value=value,
            unit=str(data["unit"]),
            citations=tuple(str(item) for item in data["citations"]),
            confidence=float(data["confidence"]),
            abstained=bool(data["abstained"]),
            formula_id=str(data.get("formula_id", "")),
            operands=tuple(
                CalculationOperand.from_dict(dict(item)) for item in data.get("operands", [])
            ),
            missing_evidence=tuple(str(item) for item in data.get("missing_evidence", [])),
            pre_confidence=None if pre is None else float(pre),
            retrieved_document_ids=tuple(
                str(item) for item in data.get("retrieved_document_ids", [])
            ),
            latency_ms=float(data.get("latency_ms", 0.0)),
            input_tokens=int(data.get("input_tokens", 0)),
            output_tokens=int(data.get("output_tokens", 0)),
            trace=tuple(dict(item) for item in data.get("trace", [])),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["citations"] = list(self.citations)
        data["operands"] = [item.to_dict() for item in self.operands]
        data["missing_evidence"] = list(self.missing_evidence)
        data["retrieved_document_ids"] = list(self.retrieved_document_ids)
        data["trace"] = list(self.trace)
        return data


@dataclass(frozen=True)
class CaseResult:
    """Deterministic scores for one case."""

    case_id: str
    correct: bool
    answer_score: float
    unit_score: float
    citation_precision: float
    citation_recall: float
    citation_f1: float
    retrieval_recall: float | None
    formula_score: float
    operand_score: float
    clarification_score: float
    abstention_score: float
    contract_score: float
    brier: float | None
    failure_labels: tuple[str, ...]
    expected_display: str
    predicted_display: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["failure_labels"] = list(self.failure_labels)
        return data


@dataclass(frozen=True)
class PairResult:
    """Behavioral score for a transformed case versus its reference.

    ``passed`` is deliberately conjunctive: an answer-only success cannot hide
    stale evidence, unjustified confidence, or a reported retrieval miss.
    """

    reference_case_id: str
    transformed_case_id: str
    transform: str
    expectation: Expectation
    passed: bool
    score: float
    answer_pass: bool
    evidence_pass: bool
    formula_pass: bool
    confidence_pass: bool
    retrieval_pass: bool | None
    answer_changed: bool
    citation_migrated: bool
    confidence_delta: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
