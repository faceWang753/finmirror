"""Tests for v0.2 source provenance receipts and release gates."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from finmirror.sources import (
    REQUIRED_FIELDS,
    SourceDriftError,
    SourceReceipt,
    SourceReceiptError,
    capture_receipt,
    content_sha256,
    ledger_digest,
    load_ledger,
    validate_ledger,
    verify_content,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _candidate_data() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "receipt_id": "provider-series-001",
        "provider": "Official Provider",
        "resource_id": "SERIES-001",
        "source_url": "https://data.example.org/series/001?end=2026-07-15",
        "terms_url": "https://data.example.org/terms",
        "license_id": "LicenseRef-Provider-Terms",
        "license_name": "Provider reuse terms",
        "attribution": "Source: Official Provider. Changes are identified.",
        "languages": ["en", "fr"],
        "media_type": "application/json",
        "redistribution": "undetermined",
        "third_party_status": "not_reviewed",
        "record_state": "candidate",
        "retrieved_at": None,
        "as_of": "2026-07-15",
        "content_sha256": None,
        "content_bytes": None,
        "terms_checked_at": "2026-07-31",
        "terms_snapshot_sha256": None,
        "notes": "Candidate only; not approved for release.",
    }


def _candidate() -> SourceReceipt:
    return SourceReceipt.from_dict(_candidate_data())


def test_committed_schema_and_runtime_require_the_same_fields() -> None:
    schema = json.loads(
        (PROJECT_ROOT / "schema" / "source-receipt.schema.json").read_text(encoding="utf-8")
    )
    assert set(schema["required"]) == REQUIRED_FIELDS
    assert schema["additionalProperties"] is False
    assert len(schema["allOf"]) == 3


def test_content_hash_is_byte_exact_and_rejects_text() -> None:
    assert content_sha256("é\r\n".encode()) != content_sha256("é\n".encode())
    assert len(content_sha256(b"source bytes")) == 64
    with pytest.raises(TypeError, match="requires bytes"):
        content_sha256("source bytes")  # type: ignore[arg-type]


def test_candidate_round_trip_preserves_null_capture_fields() -> None:
    receipt = _candidate()
    assert receipt.to_dict() == _candidate_data()
    assert not receipt.release_ready
    assert "record_state is not captured" in receipt.release_blockers()
    assert "source content is not hash-bound" in receipt.release_blockers()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "2.0", "unsupported"),
        ("receipt_id", "Bad ID", "stable lowercase"),
        ("source_url", "http://data.example.org/x", "HTTPS"),
        ("source_url", "https://user:secret@data.example.org/x", "credentials"),
        ("source_url", "https://data.example.org/x#frag", "fragment"),
        ("source_url", "https://data.example.org/a b", "whitespace"),
        ("source_url", "https://data.example.org/x?api_key=secret", "credential-like"),
        ("redistribution", "probably", "unsupported redistribution"),
        ("third_party_status", "maybe", "unsupported third_party_status"),
        ("record_state", "downloaded", "unsupported record_state"),
        ("media_type", "json", "type/subtype"),
        ("terms_checked_at", "31-07-2026", "YYYY-MM-DD"),
        ("terms_checked_at", "20260731", "YYYY-MM-DD"),
        ("as_of", "2026/07/15", "YYYY-MM-DD"),
        ("content_bytes", True, "non-negative integer"),
    ],
)
def test_receipt_rejects_invalid_fields(field: str, value: object, message: str) -> None:
    data = _candidate_data()
    data[field] = value
    with pytest.raises(SourceReceiptError, match=message):
        SourceReceipt.from_dict(data)


def test_receipt_rejects_missing_unknown_and_duplicate_languages() -> None:
    missing = _candidate_data()
    del missing["provider"]
    with pytest.raises(SourceReceiptError, match="missing fields"):
        SourceReceipt.from_dict(missing)

    extra = _candidate_data()
    extra["approval_guess"] = True
    with pytest.raises(SourceReceiptError, match="unknown fields"):
        SourceReceipt.from_dict(extra)

    duplicate_languages = _candidate_data()
    duplicate_languages["languages"] = ["en", "en"]
    with pytest.raises(SourceReceiptError, match="must be unique"):
        SourceReceipt.from_dict(duplicate_languages)


def test_capture_binds_exact_bytes_and_detects_drift() -> None:
    content = b'{"observations":[1,2,3]}'
    captured = capture_receipt(
        _candidate(),
        content,
        retrieved_at="2026-07-31T15:00:00Z",
    )
    assert captured.record_state == "captured"
    assert captured.content_sha256 == content_sha256(content)
    assert captured.content_bytes == len(content)
    verify_content(captured, content)

    with pytest.raises(SourceDriftError, match="source drift"):
        verify_content(captured, b'{"observations":[1,2,4]}')
    with pytest.raises(SourceDriftError, match="source drift"):
        verify_content(captured, content + b"\n")


def test_capture_rejects_empty_bytes_and_naive_timestamp() -> None:
    with pytest.raises(SourceReceiptError, match="must not be empty"):
        capture_receipt(_candidate(), b"", retrieved_at="2026-07-31T15:00:00Z")
    with pytest.raises(SourceReceiptError, match="timezone"):
        capture_receipt(
            _candidate(),
            b"content",
            retrieved_at="2026-07-31T15:00:00",
        )

    already_captured = capture_receipt(
        _candidate(),
        b"content",
        retrieved_at="2026-07-31T15:00:00Z",
    )
    with pytest.raises(SourceReceiptError, match="only a candidate"):
        capture_receipt(
            already_captured,
            b"new content",
            retrieved_at="2026-08-01T15:00:00Z",
        )


def test_uncaptured_receipt_cannot_verify_content() -> None:
    with pytest.raises(SourceReceiptError, match="has no captured content"):
        verify_content(_candidate(), b"content")


def test_candidate_cannot_claim_partial_or_complete_capture() -> None:
    partial = _candidate_data()
    partial["content_sha256"] = "0" * 64
    with pytest.raises(SourceReceiptError, match="recorded together"):
        SourceReceipt.from_dict(partial)

    claimed = _candidate_data()
    claimed.update(
        {
            "retrieved_at": "2026-07-31T15:00:00Z",
            "content_sha256": "0" * 64,
            "content_bytes": 10,
        }
    )
    with pytest.raises(SourceReceiptError, match="must not claim"):
        SourceReceipt.from_dict(claimed)

    empty_capture = _candidate_data()
    empty_capture.update(
        {
            "record_state": "captured",
            "retrieved_at": "2026-07-31T15:00:00Z",
            "content_sha256": content_sha256(b""),
            "content_bytes": 0,
        }
    )
    with pytest.raises(SourceReceiptError, match="non-empty content"):
        SourceReceipt.from_dict(empty_capture)


def test_release_gate_requires_legal_and_terms_review_after_capture() -> None:
    captured = capture_receipt(
        _candidate(),
        b"fixed source response",
        retrieved_at="2026-07-31T15:00:00+00:00",
    )
    with pytest.raises(SourceReceiptError, match="redistribution decision"):
        validate_ledger([captured], require_release_ready=True)

    ready = replace(
        captured,
        redistribution="redistribute",
        third_party_status="clear",
        terms_snapshot_sha256="a" * 64,
    )
    assert ready.release_ready
    assert validate_ledger([ready], require_release_ready=True) == [ready]


def test_ledger_rejects_empty_and_duplicate_receipts() -> None:
    with pytest.raises(SourceReceiptError, match="at least one"):
        validate_ledger([])
    with pytest.raises(SourceReceiptError, match="duplicate"):
        validate_ledger([_candidate(), _candidate()])


def test_ledger_digest_is_order_independent_and_sensitive() -> None:
    first = _candidate()
    second_data = deepcopy(_candidate_data())
    second_data["receipt_id"] = "provider-series-002"
    second_data["resource_id"] = "SERIES-002"
    second = SourceReceipt.from_dict(second_data)
    assert ledger_digest([first, second]) == ledger_digest([second, first])

    changed = replace(second, as_of="2026-07-14")
    assert ledger_digest([first, second]) != ledger_digest([first, changed])


def test_load_ledger_reports_line_and_object_errors(tmp_path: Path) -> None:
    invalid_json = tmp_path / "invalid.jsonl"
    invalid_json.write_text(
        json.dumps(_candidate_data()) + "\n{not-json}\n",
        encoding="utf-8",
    )
    with pytest.raises(SourceReceiptError, match="line 2"):
        load_ledger(invalid_json)

    non_object = tmp_path / "array.jsonl"
    non_object.write_text("[]\n", encoding="utf-8")
    with pytest.raises(SourceReceiptError, match="must be an object"):
        load_ledger(non_object)


def test_committed_v02_ledger_separates_captured_and_candidate_sources() -> None:
    receipts = load_ledger(PROJECT_ROOT / "sources" / "v0.2" / "ledger.jsonl")
    assert {receipt.provider for receipt in receipts} == {
        "Bank of Canada",
        "Statistics Canada",
    }
    assert {receipt.resource_id for receipt in receipts} == {"36-10-0104-01", "V39079"}
    by_provider = {receipt.provider: receipt for receipt in receipts}
    assert by_provider["Statistics Canada"].record_state == "captured"
    assert by_provider["Statistics Canada"].release_ready is True
    assert by_provider["Bank of Canada"].record_state == "candidate"
    assert by_provider["Bank of Canada"].release_ready is False
    with pytest.raises(SourceReceiptError, match="not release-ready"):
        load_ledger(
            PROJECT_ROOT / "sources" / "v0.2" / "ledger.jsonl",
            require_release_ready=True,
        )
