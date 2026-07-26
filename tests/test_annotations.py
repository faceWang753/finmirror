"""Tests for auditable human-annotation agreement helpers."""

from __future__ import annotations

import json

import pytest

from finmirror.annotations import annotation_agreement, cohen_kappa


def _write_rows(path, rows) -> None:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_cohen_kappa_perfect_and_known_partial_agreement() -> None:
    assert cohen_kappa(["yes", "no"], ["yes", "no"]) == 1.0
    assert cohen_kappa(
        ["a", "a", "b", "b"],
        ["a", "b", "b", "b"],
    ) == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("left", "right"),
    [([], []), (["a"], []), (["a"], ["a", "b"])],
)
def test_cohen_kappa_rejects_empty_or_misaligned_vectors(left, right) -> None:
    with pytest.raises(ValueError, match="non-empty vectors of equal length"):
        cohen_kappa(left, right)


def test_annotation_agreement_multiple_fields(tmp_path) -> None:
    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    _write_rows(
        left,
        [
            {"case_id": "1", "answerable": "yes", "material": "yes"},
            {"case_id": "2", "answerable": "no", "material": "no"},
        ],
    )
    _write_rows(
        right,
        [
            {"case_id": "2", "answerable": "no", "material": "yes"},
            {"case_id": "1", "answerable": "yes", "material": "yes"},
        ],
    )
    result = annotation_agreement(left, right, ["answerable", "material"])
    assert result["case_count"] == 2
    assert result["fields"]["answerable"]["raw_agreement"] == 1.0
    assert result["fields"]["answerable"]["cohen_kappa"] == 1.0
    assert result["fields"]["material"]["raw_agreement"] == 0.5


def test_missing_annotation_values_are_explicit_categories(tmp_path) -> None:
    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    _write_rows(left, [{"case_id": "1"}])
    _write_rows(right, [{"case_id": "1"}])
    result = annotation_agreement(left, right, ["material"])
    assert result["fields"]["material"]["labels"] == ["<MISSING>"]
    assert result["fields"]["material"]["cohen_kappa"] == 1.0


def test_annotation_id_mismatch_is_rejected(tmp_path) -> None:
    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    _write_rows(left, [{"case_id": "left"}])
    _write_rows(right, [{"case_id": "right"}])
    with pytest.raises(ValueError, match="Annotation IDs differ"):
        annotation_agreement(left, right, ["answerable"])


def test_duplicate_and_invalid_annotation_rows_are_rejected(tmp_path) -> None:
    duplicate = tmp_path / "duplicate.jsonl"
    peer = tmp_path / "peer.jsonl"
    _write_rows(duplicate, [{"case_id": "1"}, {"case_id": "1"}])
    _write_rows(peer, [{"case_id": "1"}])
    with pytest.raises(ValueError, match="Duplicate annotation"):
        annotation_agreement(duplicate, peer, ["answerable"])

    invalid = tmp_path / "invalid.jsonl"
    invalid.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON on line 1"):
        annotation_agreement(invalid, peer, ["answerable"])
