"""Deterministic passage-ranking assurance for evidence-grounded RAG systems."""

from __future__ import annotations

import html
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from finmirror.models import BenchmarkCase

_ANCHOR = re.compile(r"^\[([A-Z][0-9]+)\]\s*(.+)$")
_TOKEN = re.compile(r"[^\W_]+", flags=re.UNICODE)
_NEGATIVE_ANCHOR_PREFIXES = ("D", "P", "X")


@dataclass(frozen=True)
class RetrievalCandidate:
    """One independently rankable evidence passage with hidden audit utility."""

    candidate_id: str
    title: str
    text: str
    role: str
    utility: int

    def public_dict(self) -> dict[str, str]:
        return {
            "candidate_id": self.candidate_id,
            "title": self.title,
            "text": self.text,
        }


@dataclass(frozen=True)
class RetrievalCase:
    """A query and candidate pool derived from one FinMirror evidence world."""

    case_id: str
    pair_group_id: str
    language: str
    query: str
    transform: str
    expectation: str
    reference_case_id: str | None
    candidates: tuple[RetrievalCandidate, ...]
    required_candidate_ids: tuple[str, ...]
    answerable: bool

    def public_dict(self) -> dict[str, Any]:
        """Return the ranker-visible packet, excluding utility and pair gold."""

        return {
            "case_id": self.case_id,
            "language": self.language,
            "query": self.query,
            "candidates": [candidate.public_dict() for candidate in self.candidates],
        }


@dataclass(frozen=True)
class RetrievalPrediction:
    """A complete ranking and optional comparable relevance scores."""

    case_id: str
    ranked_candidate_ids: tuple[str, ...]
    scores: tuple[float, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> RetrievalPrediction:
        missing = {"case_id", "ranked_candidate_ids"}.difference(value)
        if missing:
            raise ValueError(f"retrieval prediction is missing fields: {sorted(missing)}")
        return cls(
            case_id=str(value["case_id"]),
            ranked_candidate_ids=tuple(str(item) for item in value["ranked_candidate_ids"]),
            scores=tuple(float(item) for item in value.get("scores", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "ranked_candidate_ids": list(self.ranked_candidate_ids),
            "scores": list(self.scores),
        }


@dataclass(frozen=True)
class RetrievalCaseResult:
    case_id: str
    answerable: bool
    required_count: int
    evaluated_k: int
    evidence_recall_at_k: float | None
    harmful_exposure_at_k: float
    sufficient_evidence_rank: int | None
    harmful_before_sufficient: int
    utility_dcg_at_k: float
    clean_completion: bool | None


@dataclass(frozen=True)
class RetrievalPairResult:
    reference_case_id: str
    transformed_case_id: str
    transform: str
    expectation: str
    passed: bool | None
    reason: str


class RetrievalRanker(Protocol):
    """Small provider-neutral boundary for ranking public retrieval packets."""

    name: str
    version: str
    uses_gold: bool

    def rank(self, case: RetrievalCase) -> RetrievalPrediction: ...


def _document_role(case: BenchmarkCase, document_index: int) -> str:
    document = case.documents[document_index]
    if bool(document.metadata.get("decoy")):
        return "decoy"
    if document_index == len(case.documents) - 1:
        return "primary"
    return f"document-{document_index}"


def build_retrieval_cases(cases: list[BenchmarkCase]) -> list[RetrievalCase]:
    """Split document anchor lines into a deterministic retrieval audit packet."""

    result: list[RetrievalCase] = []
    for case in cases:
        required = set(case.expected.required_evidence)
        candidates: list[RetrievalCandidate] = []
        for document_index, document in enumerate(case.documents):
            document_role = _document_role(case, document_index)
            for raw_line in document.content.splitlines():
                match = _ANCHOR.match(raw_line.strip())
                if match is None:
                    continue
                anchor, text = match.groups()
                candidate_id = f"{document.id}#{anchor}"
                harmful = bool(document.metadata.get("decoy")) or anchor.startswith(
                    _NEGATIVE_ANCHOR_PREFIXES
                )
                utility = 2 if candidate_id in required else (-1 if harmful else 0)
                candidates.append(
                    RetrievalCandidate(
                        candidate_id=candidate_id,
                        title=document.title,
                        text=text,
                        role=f"{document_role}#{anchor}",
                        utility=utility,
                    )
                )
        candidate_ids = {candidate.candidate_id for candidate in candidates}
        unresolved = required.difference(candidate_ids)
        if unresolved:
            raise ValueError(
                f"{case.case_id} required evidence has no candidate passage: {sorted(unresolved)}"
            )
        if not candidates:
            raise ValueError(f"{case.case_id} contains no anchored retrieval candidates")
        result.append(
            RetrievalCase(
                case_id=case.case_id,
                pair_group_id=case.pair_group_id,
                language=case.language,
                query=case.question,
                transform=case.relationship.transform,
                expectation=case.relationship.expectation,
                reference_case_id=case.relationship.reference_case_id,
                candidates=tuple(candidates),
                required_candidate_ids=tuple(case.expected.required_evidence),
                answerable=not case.expected.abstain,
            )
        )
    return result


def dump_retrieval_packet(cases: list[RetrievalCase], path: str | Path) -> None:
    """Write only ranker-visible fields; hidden utility never leaves the evaluator."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(json.dumps(case.public_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def save_retrieval_predictions(
    predictions: list[RetrievalPrediction], path: str | Path
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for prediction in predictions:
            handle.write(json.dumps(prediction.to_dict(), sort_keys=True) + "\n")


def load_retrieval_predictions(path: str | Path) -> list[RetrievalPrediction]:
    predictions: list[RetrievalPrediction] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number} must contain a JSON object")
            predictions.append(RetrievalPrediction.from_dict(value))
    return predictions


def run_retrieval_ranker(
    ranker: RetrievalRanker, cases: list[RetrievalCase]
) -> list[RetrievalPrediction]:
    return [ranker.rank(case) for case in cases]


class InputOrderRanker:
    """Deliberately brittle control that trusts candidate input order."""

    name = "input-order-control"
    version = "1"
    uses_gold = False

    def rank(self, case: RetrievalCase) -> RetrievalPrediction:
        count = len(case.candidates)
        return RetrievalPrediction(
            case_id=case.case_id,
            ranked_candidate_ids=tuple(item.candidate_id for item in case.candidates),
            scores=tuple(float(count - index) for index in range(count)),
        )


class LexicalOverlapRanker:
    """Zero-key, evidence-blind token-overlap baseline."""

    name = "lexical-overlap"
    version = "1"
    uses_gold = False

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {token.casefold() for token in _TOKEN.findall(value) if len(token) > 1}

    def rank(self, case: RetrievalCase) -> RetrievalPrediction:
        query_tokens = self._tokens(case.query)
        scored = []
        for input_index, candidate in enumerate(case.candidates):
            candidate_tokens = self._tokens(f"{candidate.title} {candidate.text}")
            union = query_tokens.union(candidate_tokens)
            score = len(query_tokens.intersection(candidate_tokens)) / max(1, len(union))
            scored.append((score, -input_index, candidate.candidate_id))
        scored.sort(reverse=True)
        return RetrievalPrediction(
            case_id=case.case_id,
            ranked_candidate_ids=tuple(item[2] for item in scored),
            scores=tuple(item[0] for item in scored),
        )


class RetrievalOracleRanker:
    """Gold-aware positive control; never a model result."""

    name = "retrieval-harness-oracle"
    version = "1"
    uses_gold = True

    def rank(self, case: RetrievalCase) -> RetrievalPrediction:
        ranked = sorted(
            enumerate(case.candidates),
            key=lambda item: (item[1].utility, -item[0]),
            reverse=True,
        )
        return RetrievalPrediction(
            case_id=case.case_id,
            ranked_candidate_ids=tuple(candidate.candidate_id for _, candidate in ranked),
            scores=tuple(float(candidate.utility) for _, candidate in ranked),
        )


def _validated_prediction_map(
    cases: list[RetrievalCase], predictions: list[RetrievalPrediction]
) -> dict[str, RetrievalPrediction]:
    case_ids = {case.case_id for case in cases}
    mapping: dict[str, RetrievalPrediction] = {}
    for prediction in predictions:
        if prediction.case_id not in case_ids:
            raise ValueError(f"prediction references unknown case: {prediction.case_id}")
        if prediction.case_id in mapping:
            raise ValueError(f"duplicate retrieval prediction: {prediction.case_id}")
        mapping[prediction.case_id] = prediction
    missing = case_ids.difference(mapping)
    if missing:
        raise ValueError(f"missing retrieval predictions: {sorted(missing)[:5]}")
    for case in cases:
        prediction = mapping[case.case_id]
        expected_ids = {candidate.candidate_id for candidate in case.candidates}
        ranked_ids = prediction.ranked_candidate_ids
        if len(set(ranked_ids)) != len(ranked_ids):
            raise ValueError(f"{case.case_id} ranking contains duplicate candidate IDs")
        if set(ranked_ids) != expected_ids:
            unknown = set(ranked_ids).difference(expected_ids)
            omitted = expected_ids.difference(ranked_ids)
            raise ValueError(
                f"{case.case_id} ranking must be a complete permutation; "
                f"unknown={sorted(unknown)}, omitted={sorted(omitted)}"
            )
        if prediction.scores and len(prediction.scores) != len(ranked_ids):
            raise ValueError(f"{case.case_id} score count does not match ranking length")
        if any(not math.isfinite(score) for score in prediction.scores):
            raise ValueError(f"{case.case_id} contains a non-finite ranking score")
        if any(
            left < right
            for left, right in zip(prediction.scores, prediction.scores[1:], strict=False)
        ):
            raise ValueError(f"{case.case_id} scores must be in non-increasing rank order")
    return mapping


def _score_retrieval_case(
    case: RetrievalCase, prediction: RetrievalPrediction, top_k: int
) -> RetrievalCaseResult:
    candidate_by_id = {candidate.candidate_id: candidate for candidate in case.candidates}
    required = set(case.required_candidate_ids)
    evaluated_k = min(len(case.candidates), max(top_k, len(required)))
    prefix = prediction.ranked_candidate_ids[:evaluated_k]
    required_ranks = [
        prediction.ranked_candidate_ids.index(candidate_id) + 1 for candidate_id in required
    ]
    sufficient_rank = max(required_ranks) if required_ranks else None
    harmful_ranks = [
        index + 1
        for index, candidate_id in enumerate(prediction.ranked_candidate_ids)
        if candidate_by_id[candidate_id].utility < 0
    ]
    harmful_before_sufficient = (
        sum(rank < sufficient_rank for rank in harmful_ranks) if sufficient_rank is not None else 0
    )
    recall = len(required.intersection(prefix)) / len(required) if required else None
    harmful_exposure = (
        sum(candidate_by_id[candidate_id].utility < 0 for candidate_id in prefix)
        / evaluated_k
    )
    utility_dcg = sum(
        candidate_by_id[candidate_id].utility / math.log2(rank + 1)
        for rank, candidate_id in enumerate(prefix, 1)
    )
    clean_completion = (
        None
        if not case.answerable
        else recall == 1.0 and harmful_before_sufficient == 0
    )
    return RetrievalCaseResult(
        case_id=case.case_id,
        answerable=case.answerable,
        required_count=len(required),
        evaluated_k=evaluated_k,
        evidence_recall_at_k=recall,
        harmful_exposure_at_k=harmful_exposure,
        sufficient_evidence_rank=sufficient_rank,
        harmful_before_sufficient=harmful_before_sufficient,
        utility_dcg_at_k=utility_dcg,
        clean_completion=clean_completion,
    )


def audit_retrieval_rankings(
    cases: list[RetrievalCase],
    predictions: list[RetrievalPrediction],
    *,
    system_name: str,
    system_version: str = "",
    top_k: int = 2,
    uses_gold: bool = False,
) -> dict[str, Any]:
    """Audit complete rankings without using an LLM judge."""

    if top_k < 1:
        raise ValueError("top_k must be positive")
    prediction_by_id = _validated_prediction_map(cases, predictions)
    case_by_id = {case.case_id: case for case in cases}
    case_results = [
        _score_retrieval_case(case, prediction_by_id[case.case_id], top_k) for case in cases
    ]
    result_by_id = {result.case_id: result for result in case_results}
    pair_results: list[RetrievalPairResult] = []
    for case in cases:
        if case.reference_case_id is None:
            continue
        if case.reference_case_id not in case_by_id:
            raise ValueError(f"{case.case_id} references missing case {case.reference_case_id}")
        reference_result = result_by_id[case.reference_case_id]
        transformed_result = result_by_id[case.case_id]
        if not case.answerable:
            pair_results.append(
                RetrievalPairResult(
                    reference_case_id=case.reference_case_id,
                    transformed_case_id=case.case_id,
                    transform=case.transform,
                    expectation=case.expectation,
                    passed=None,
                    reason=(
                        "candidate-set ablation is unanswerable; a reranker alone cannot "
                        "make the downstream abstention decision"
                    ),
                )
            )
            continue
        passed = bool(reference_result.clean_completion and transformed_result.clean_completion)
        pair_results.append(
            RetrievalPairResult(
                reference_case_id=case.reference_case_id,
                transformed_case_id=case.case_id,
                transform=case.transform,
                expectation=case.expectation,
                passed=passed,
                reason=(
                    "both worlds surface the complete evidence set before harmful passages"
                    if passed
                    else "at least one paired world exposes harmful content before sufficient evidence"
                ),
            )
        )

    answerable_results = [result for result in case_results if result.answerable]
    scored_pairs = [pair for pair in pair_results if pair.passed is not None]
    if not answerable_results or not scored_pairs:
        raise ValueError("retrieval audit requires answerable cases and scored pairs")
    full_coverage_rate = sum(
        result.evidence_recall_at_k == 1.0 for result in answerable_results
    ) / len(answerable_results)
    clean_completion_rate = sum(
        result.clean_completion is True for result in answerable_results
    ) / len(answerable_results)
    pair_reliability = sum(pair.passed is True for pair in scored_pairs) / len(scored_pairs)
    harmful_exposure = sum(
        result.harmful_exposure_at_k for result in answerable_results
    ) / len(answerable_results)
    hard_gate = clean_completion_rate == 1.0 and pair_reliability == 1.0 and not uses_gold
    return {
        "schema_version": "finmirror.retrieval-audit.v1",
        "system": {"name": system_name, "version": system_version, "uses_gold": uses_gold},
        "dataset": {
            "case_count": len(cases),
            "answerable_case_count": len(answerable_results),
            "unanswerable_case_count": len(cases) - len(answerable_results),
            "pair_count": len(scored_pairs),
            "languages": sorted({case.language for case in cases}),
            "top_k": top_k,
        },
        "metrics": {
            "full_evidence_coverage_rate": full_coverage_rate,
            "clean_completion_rate": clean_completion_rate,
            "paired_reliability": pair_reliability,
            "mean_harmful_exposure_at_k": harmful_exposure,
            "hard_gate_pass": hard_gate,
        },
        "case_results": [asdict(result) for result in case_results],
        "pair_results": [asdict(result) for result in pair_results],
        "limitations": [
            "The packet is synthetic and anchor-level; it does not estimate production search quality.",
            "Utility labels are deterministic audit contracts, not human relevance judgments.",
            "Unanswerable candidate sets are disclosed but downstream abstention is not scored here.",
            "The harness oracle uses hidden utility and is a control, never a model result.",
        ],
    }


def render_retrieval_comparison(reports: list[dict[str, Any]], path: str | Path) -> None:
    """Render a dependency-free comparison suitable for GitHub Pages."""

    rows = []
    for report in reports:
        metrics = report["metrics"]
        system = report["system"]
        gate = (
            "CONTROL"
            if system["uses_gold"]
            else ("PASS" if metrics["hard_gate_pass"] else "BLOCKED")
        )
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(str(system['name']))}</strong></td>"
            f"<td>{gate}</td>"
            f"<td>{100 * float(metrics['full_evidence_coverage_rate']):.1f}%</td>"
            f"<td>{100 * float(metrics['clean_completion_rate']):.1f}%</td>"
            f"<td>{100 * float(metrics['paired_reliability']):.1f}%</td>"
            f"<td>{100 * float(metrics['mean_harmful_exposure_at_k']):.1f}%</td>"
            "</tr>"
        )
    page = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>FinMirror retrieval assurance</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;margin:0;background:#f6f7fb;color:#172033}}
main{{max-width:1050px;margin:auto;padding:42px 24px}} .card{{background:white;border:1px solid #dce1ea;border-radius:14px;padding:24px;box-shadow:0 8px 24px #1720330d}}
h1{{margin-top:0}} table{{border-collapse:collapse;width:100%;margin:24px 0}} th,td{{text-align:left;border-bottom:1px solid #e3e7ef;padding:12px 9px}} th{{font-size:13px;color:#59657a}}
.note{{color:#59657a}} code{{background:#eef1f6;padding:2px 5px;border-radius:4px}}
</style><main><div class="card">
<h1>Can a ranker surface sufficient evidence before harmful distractors?</h1>
<p>Anchor-level passages come from FinMirror's paired evidence worlds. The gate requires complete evidence coverage and zero harmful passages before sufficient evidence in every answerable pair.</p>
<table><thead><tr><th>System</th><th>Gate</th><th>Evidence coverage</th><th>Clean completion</th><th>Paired reliability</th><th>Harmful exposure@k</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p class="note">The gold-aware oracle is only a harness control. Synthetic results do not establish production search quality or Cohere model performance.</p>
</div></main></html>"""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8", newline="\n")
