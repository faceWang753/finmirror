"""Benchmark I/O, integrity hashing, and fail-closed validation."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from finmirror.models import BenchmarkCase

SCHEMA_VERSION = "1.0"


def canonical_json(value: Any) -> str:
    """Serialize a value deterministically for hashing and reproducibility."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def dataset_digest(cases: Iterable[BenchmarkCase]) -> str:
    """Return the SHA-256 digest of cases sorted by case ID."""

    payload = "\n".join(
        canonical_json(case.to_dict()) for case in sorted(cases, key=lambda item: item.case_id)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_cases_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_dir() or not candidate.suffix:
        candidate = candidate / "cases.jsonl"
    return candidate


def load_cases(path: str | Path, *, verify_manifest: bool = True) -> list[BenchmarkCase]:
    """Load and validate a JSONL benchmark."""

    cases_path = resolve_cases_path(path)
    if not cases_path.exists():
        raise FileNotFoundError(f"Dataset not found: {cases_path}")

    cases: list[BenchmarkCase] = []
    with cases_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on {cases_path}:{line_number}: {exc}") from exc
            if not isinstance(raw, dict):
                raise ValueError(f"Expected object on {cases_path}:{line_number}")
            try:
                cases.append(BenchmarkCase.from_dict(raw))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid case on {cases_path}:{line_number}: {exc}") from exc

    validate_cases(cases)
    manifest_path = cases_path.parent / "manifest.json"
    if verify_manifest and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = str(manifest.get("dataset_sha256", ""))
        actual = dataset_digest(cases)
        if not expected:
            raise ValueError(f"Manifest has no dataset_sha256: {manifest_path}")
        if expected != actual:
            raise ValueError(
                "Dataset integrity check failed: "
                f"manifest={expected}, computed={actual}. Refusing to continue."
            )
        if int(manifest.get("case_count", -1)) != len(cases):
            raise ValueError("Manifest case_count does not match cases.jsonl")
    return cases


def save_cases(cases: Iterable[BenchmarkCase], path: str | Path) -> Path:
    """Write deterministic JSONL."""

    output = resolve_cases_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    materialized = sorted(cases, key=lambda item: item.case_id)
    text = "\n".join(canonical_json(case.to_dict()) for case in materialized) + "\n"
    output.write_text(text, encoding="utf-8", newline="\n")
    return output


def write_manifest(
    cases: list[BenchmarkCase],
    directory: str | Path,
    *,
    name: str,
    version: str,
    description: str,
) -> Path:
    output = Path(directory) / "manifest.json"
    languages = sorted({case.language for case in cases})
    transforms = Counter(case.relationship.transform for case in cases)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "version": version,
        "description": description,
        "case_count": len(cases),
        "pair_group_count": len({case.pair_group_id for case in cases}),
        "scenario_count": len({case.scenario_id for case in cases}),
        "languages": languages,
        "transforms": dict(sorted(transforms.items())),
        "dataset_sha256": dataset_digest(cases),
        "data_license": "CC-BY-4.0",
        "synthetic": True,
        "contains_investment_advice": False,
    }
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output


def validate_cases(cases: list[BenchmarkCase]) -> None:
    """Validate structural and counterfactual invariants."""

    if not cases:
        raise ValueError("Dataset contains no cases")
    ids = [case.case_id for case in cases]
    duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate case IDs: {duplicates[:5]}")
    by_id = {case.case_id: case for case in cases}
    groups: dict[str, list[BenchmarkCase]] = defaultdict(list)

    for case in cases:
        groups[case.pair_group_id].append(case)
        if not case.question.strip():
            raise ValueError(f"{case.case_id}: empty question")
        if not 0.0 <= case.expected.materiality <= 1.0:
            raise ValueError(f"{case.case_id}: materiality must be between 0 and 1")
        if case.expected.tolerance < 0:
            raise ValueError(f"{case.case_id}: negative tolerance")
        document_ids = [document.id for document in case.documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError(f"{case.case_id}: duplicate document IDs")
        available_evidence = {
            f"{document.id}#{anchor}"
            for document in case.documents
            for anchor in _extract_anchors(document.content)
        }
        if not case.expected.abstain:
            missing_evidence = set(case.expected.required_evidence) - available_evidence
            if missing_evidence:
                raise ValueError(
                    f"{case.case_id}: required evidence is absent: {sorted(missing_evidence)}"
                )
            operand_evidence = {operand.evidence for operand in case.expected.operands}
            if operand_evidence != set(case.expected.required_evidence):
                raise ValueError(
                    f"{case.case_id}: operand provenance must equal required evidence"
                )
            if not case.expected.formula_id or not case.expected.operands:
                raise ValueError(
                    f"{case.case_id}: answerable numeric case needs a formula program"
                )
            if case.expected.missing_evidence:
                raise ValueError(
                    f"{case.case_id}: answerable case cannot declare missing evidence"
                )
        else:
            if case.expected.formula_id or case.expected.operands:
                raise ValueError(
                    f"{case.case_id}: unanswerable case cannot contain a formula program"
                )
            if not case.expected.missing_evidence:
                raise ValueError(
                    f"{case.case_id}: unanswerable case must identify missing evidence"
                )
        relation = case.relationship
        if relation.expectation == "reference":
            if relation.reference_case_id is not None:
                raise ValueError(f"{case.case_id}: reference case cannot point to a parent")
        else:
            if not relation.reference_case_id:
                raise ValueError(f"{case.case_id}: transformed case has no reference")
            if relation.reference_case_id not in by_id:
                raise ValueError(
                    f"{case.case_id}: unknown reference {relation.reference_case_id}"
                )

    for group_id, members in groups.items():
        references = [item for item in members if item.relationship.expectation == "reference"]
        if len(references) != 1:
            raise ValueError(
                f"{group_id}: expected exactly one reference case, found {len(references)}"
            )
        reference = references[0]
        for member in members:
            relation = member.relationship
            if relation.expectation != "reference":
                if relation.reference_case_id != reference.case_id:
                    raise ValueError(
                        f"{member.case_id}: reference must be {reference.case_id} within group"
                    )
                if (
                    relation.expectation == "should_change"
                    and member.expected.value == reference.expected.value
                ):
                    raise ValueError(
                        f"{member.case_id}: should_change has unchanged gold value"
                    )
                if (
                    relation.expectation == "should_not_change"
                    and member.expected.value != reference.expected.value
                ):
                    raise ValueError(f"{member.case_id}: should_not_change altered gold value")
                if relation.expectation == "should_abstain" and not member.expected.abstain:
                    raise ValueError(
                        f"{member.case_id}: should_abstain is not marked unanswerable"
                    )


def _extract_anchors(content: str) -> set[str]:
    anchors: set[str] = set()
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("[") and "]" in stripped:
            anchors.add(stripped[1 : stripped.index("]")])
    return anchors
