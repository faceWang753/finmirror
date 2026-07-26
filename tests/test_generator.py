"""Tests for the authored paired-world generator."""

from __future__ import annotations

from collections import Counter, defaultdict

from finmirror.dataset import dataset_digest, validate_cases
from finmirror.generator import LOCALE_TEXT, SCENARIOS, VARIANTS, build_cases


def test_v01_shape_and_balance(cases) -> None:
    assert len(cases) == 126
    assert len({case.pair_group_id for case in cases}) == 18
    assert len([case for case in cases if case.relationship.reference_case_id]) == 108
    assert {case.language for case in cases} == {"en", "fr", "zh"}
    assert {case.scenario_id for case in cases} == {
        "revenue_growth",
        "gross_margin",
        "debt_to_equity",
        "cash_runway",
        "covenant_headroom",
        "free_cash_flow",
    }
    assert len(SCENARIOS) == 6
    assert tuple(LOCALE_TEXT) == ("en", "fr", "zh")

    transform_counts = Counter(case.relationship.transform for case in cases)
    assert transform_counts == Counter(
        {
            "reference": 18,
            "material_value": 18,
            "distractor": 18,
            "entity_collision": 18,
            "period_collision": 18,
            "injection": 18,
            "evidence_ablation": 18,
        }
    )


def test_every_group_is_a_complete_seven_world_contract(cases) -> None:
    groups = defaultdict(list)
    for case in cases:
        groups[case.pair_group_id].append(case)

    expected_transforms = {
        "reference",
        "material_value",
        "distractor",
        "entity_collision",
        "period_collision",
        "injection",
        "evidence_ablation",
    }
    for members in groups.values():
        assert len(members) == len(VARIANTS)
        assert {member.relationship.transform for member in members} == expected_transforms
        references = [
            member for member in members if member.relationship.expectation == "reference"
        ]
        assert len(references) == 1
        reference = references[0]
        for member in members:
            if member is not reference:
                assert member.relationship.reference_case_id == reference.case_id


def test_interventions_preserve_or_change_only_the_declared_contract(cases) -> None:
    by_id = {case.case_id: case for case in cases}
    for case in cases:
        expectation = case.relationship.expectation
        if expectation == "reference":
            continue
        reference = by_id[case.relationship.reference_case_id]
        if expectation == "should_change":
            assert case.expected.value != reference.expected.value
            assert case.expected.required_evidence != reference.expected.required_evidence
        elif expectation == "should_not_change":
            assert case.expected.value == reference.expected.value
            assert case.expected.unit == reference.expected.unit
        else:
            assert expectation == "should_abstain"
            assert case.expected.abstain
            assert case.expected.value is None
            assert case.expected.required_evidence == ()


def test_entity_collision_puts_decoy_first_but_gold_points_to_target(cases) -> None:
    collisions = [case for case in cases if case.relationship.transform == "entity_collision"]
    assert len(collisions) == 18
    for case in collisions:
        assert len(case.documents) == 2
        assert case.documents[0].metadata["decoy"] is True
        target_id = case.documents[1].id
        assert all(
            anchor.startswith(f"{target_id}#") for anchor in case.expected.required_evidence
        )


def test_period_injection_and_ablation_are_visible_in_evidence(cases) -> None:
    by_transform = defaultdict(list)
    for case in cases:
        by_transform[case.relationship.transform].append(case)

    assert all("[P1]" in case.documents[0].content for case in by_transform["period_collision"])
    assert all("[P2]" in case.documents[0].content for case in by_transform["period_collision"])
    assert all("[X1]" in case.documents[0].content for case in by_transform["injection"])
    assert all("999" in case.documents[0].content for case in by_transform["injection"])
    assert all(
        "[E2]" not in case.documents[0].content for case in by_transform["evidence_ablation"]
    )
    assert all(
        case.expected.missing_evidence and case.expected.missing_evidence[0].endswith("#E2")
        for case in by_transform["evidence_ablation"]
    )


def test_answerable_worlds_have_replayable_operand_provenance(cases) -> None:
    answerable = [case for case in cases if not case.expected.abstain]
    assert len(answerable) == 108
    for case in answerable:
        assert case.expected.formula_id == case.scenario_id
        assert len(case.expected.operands) == 2
        assert {operand.evidence for operand in case.expected.operands} == set(
            case.expected.required_evidence
        )
        assert case.expected.missing_evidence == ()


def test_parallel_worlds_cover_all_three_languages(cases) -> None:
    parallel = defaultdict(list)
    for case in cases:
        parallel[case.parallel_id].append(case)
    assert len(parallel) == len(SCENARIOS) * len(VARIANTS)
    assert all(
        {item.language for item in members} == {"en", "fr", "zh"}
        for members in parallel.values()
    )


def test_build_is_deterministic_and_valid() -> None:
    first = build_cases()
    second = build_cases()
    validate_cases(first)
    validate_cases(second)
    assert dataset_digest(first) == dataset_digest(second)
    assert [case.to_dict() for case in first] == [case.to_dict() for case in second]


def test_prompt_view_does_not_expose_gold_contract(cases) -> None:
    prompt = cases[0].prompt_case()
    assert not hasattr(prompt, "expected")
    assert not hasattr(prompt, "relationship")
    assert prompt.case_id == cases[0].case_id
    assert prompt.documents == cases[0].documents
