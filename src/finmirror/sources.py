"""Fail-closed provenance receipts for future real-source benchmark slices.

This module deliberately performs no network access. It validates source metadata,
binds captured artifacts to their exact bytes, and detects drift when a caller supplies
bytes obtained through a separately reviewed retrieval process.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qsl, urlparse

Redistribution = Literal["redistribute", "fetch_only", "undetermined"]
ThirdPartyStatus = Literal["clear", "excluded", "unresolved", "not_reviewed"]
RecordState = Literal["candidate", "captured", "blocked"]

SCHEMA_VERSION = "1.0"
REDISTRIBUTION_VALUES = frozenset({"redistribute", "fetch_only", "undetermined"})
THIRD_PARTY_VALUES = frozenset({"clear", "excluded", "unresolved", "not_reviewed"})
RECORD_STATE_VALUES = frozenset({"candidate", "captured", "blocked"})
REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "receipt_id",
        "provider",
        "resource_id",
        "source_url",
        "terms_url",
        "license_id",
        "license_name",
        "attribution",
        "languages",
        "media_type",
        "redistribution",
        "third_party_status",
        "record_state",
        "retrieved_at",
        "as_of",
        "content_sha256",
        "content_bytes",
        "terms_checked_at",
        "terms_snapshot_sha256",
        "notes",
    }
)

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SENSITIVE_QUERY_KEYS = frozenset(
    {"access_token", "api_key", "apikey", "key", "password", "secret", "token"}
)


class SourceReceiptError(ValueError):
    """A source receipt or ledger failed validation."""


class SourceDriftError(SourceReceiptError):
    """Supplied source bytes differ from a captured receipt."""


def content_sha256(content: bytes) -> str:
    """Return the SHA-256 digest of exact source bytes.

    Text is intentionally not accepted: callers must choose and preserve the encoding
    and line endings used by the captured artifact.
    """

    if not isinstance(content, bytes):
        raise TypeError("content_sha256 requires bytes")
    return hashlib.sha256(content).hexdigest()


def _non_empty_string(data: Mapping[str, Any], field: str) -> str:
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise SourceReceiptError(f"{field} must be a non-empty string")
    return value.strip()


def _nullable_string(data: Mapping[str, Any], field: str) -> str | None:
    value = data[field]
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SourceReceiptError(f"{field} must be null or a non-empty string")
    return value.strip()


def _validate_https_url(value: str, field: str) -> None:
    if any(char.isspace() for char in value):
        raise SourceReceiptError(f"{field} must not contain whitespace")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise SourceReceiptError(f"{field} must be an absolute HTTPS URL")
    if parsed.username or parsed.password:
        raise SourceReceiptError(f"{field} must not contain credentials")
    if parsed.fragment:
        raise SourceReceiptError(f"{field} must not contain a fragment")
    query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if query_keys & _SENSITIVE_QUERY_KEYS:
        raise SourceReceiptError(f"{field} must not contain credential-like query parameters")


def _validate_date(value: str, field: str) -> None:
    if not _DATE.fullmatch(value):
        raise SourceReceiptError(f"{field} must use YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise SourceReceiptError(f"{field} must use YYYY-MM-DD") from exc


def _validate_datetime(value: str, field: str) -> None:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SourceReceiptError(f"{field} must be an ISO 8601 timestamp") from exc
    if parsed.utcoffset() is None:
        raise SourceReceiptError(f"{field} must include a timezone offset")


@dataclass(frozen=True)
class SourceReceipt:
    """A strict provenance record for one candidate or captured source artifact."""

    schema_version: str
    receipt_id: str
    provider: str
    resource_id: str
    source_url: str
    terms_url: str
    license_id: str
    license_name: str
    attribution: str
    languages: tuple[str, ...]
    media_type: str
    redistribution: Redistribution
    third_party_status: ThirdPartyStatus
    record_state: RecordState
    retrieved_at: str | None
    as_of: str | None
    content_sha256: str | None
    content_bytes: int | None
    terms_checked_at: str
    terms_snapshot_sha256: str | None
    notes: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SourceReceipt:
        keys = set(data)
        missing = REQUIRED_FIELDS - keys
        extra = keys - REQUIRED_FIELDS
        if missing:
            raise SourceReceiptError(f"source receipt is missing fields: {sorted(missing)}")
        if extra:
            raise SourceReceiptError(f"source receipt has unknown fields: {sorted(extra)}")

        raw_languages = data["languages"]
        if not isinstance(raw_languages, list) or not raw_languages:
            raise SourceReceiptError("languages must be a non-empty JSON array")
        if not all(isinstance(item, str) for item in raw_languages):
            raise SourceReceiptError("languages must contain only strings")

        raw_content_bytes = data["content_bytes"]
        if raw_content_bytes is not None and (
            isinstance(raw_content_bytes, bool)
            or not isinstance(raw_content_bytes, int)
            or raw_content_bytes < 0
        ):
            raise SourceReceiptError("content_bytes must be null or a non-negative integer")

        receipt = cls(
            schema_version=_non_empty_string(data, "schema_version"),
            receipt_id=_non_empty_string(data, "receipt_id"),
            provider=_non_empty_string(data, "provider"),
            resource_id=_non_empty_string(data, "resource_id"),
            source_url=_non_empty_string(data, "source_url"),
            terms_url=_non_empty_string(data, "terms_url"),
            license_id=_non_empty_string(data, "license_id"),
            license_name=_non_empty_string(data, "license_name"),
            attribution=_non_empty_string(data, "attribution"),
            languages=tuple(str(item) for item in raw_languages),
            media_type=_non_empty_string(data, "media_type"),
            redistribution=_non_empty_string(data, "redistribution"),  # type: ignore[arg-type]
            third_party_status=_non_empty_string(data, "third_party_status"),  # type: ignore[arg-type]
            record_state=_non_empty_string(data, "record_state"),  # type: ignore[arg-type]
            retrieved_at=_nullable_string(data, "retrieved_at"),
            as_of=_nullable_string(data, "as_of"),
            content_sha256=_nullable_string(data, "content_sha256"),
            content_bytes=raw_content_bytes,
            terms_checked_at=_non_empty_string(data, "terms_checked_at"),
            terms_snapshot_sha256=_nullable_string(data, "terms_snapshot_sha256"),
            notes=_non_empty_string(data, "notes"),
        )
        receipt.validate()
        return receipt

    def validate(self) -> None:
        """Validate structure and internal consistency without granting release status."""

        if self.schema_version != SCHEMA_VERSION:
            raise SourceReceiptError(
                f"unsupported source receipt schema_version: {self.schema_version}"
            )
        if not _IDENTIFIER.fullmatch(self.receipt_id):
            raise SourceReceiptError("receipt_id must be a stable lowercase identifier")
        _validate_https_url(self.source_url, "source_url")
        _validate_https_url(self.terms_url, "terms_url")
        if self.redistribution not in REDISTRIBUTION_VALUES:
            raise SourceReceiptError(f"unsupported redistribution: {self.redistribution}")
        if self.third_party_status not in THIRD_PARTY_VALUES:
            raise SourceReceiptError(
                f"unsupported third_party_status: {self.third_party_status}"
            )
        if self.record_state not in RECORD_STATE_VALUES:
            raise SourceReceiptError(f"unsupported record_state: {self.record_state}")
        if len(set(self.languages)) != len(self.languages):
            raise SourceReceiptError("languages must be unique")
        for language in self.languages:
            if not _LANGUAGE.fullmatch(language):
                raise SourceReceiptError(f"invalid language tag: {language}")
        if "/" not in self.media_type or any(char.isspace() for char in self.media_type):
            raise SourceReceiptError("media_type must be a compact type/subtype value")
        _validate_date(self.terms_checked_at, "terms_checked_at")
        if self.as_of is not None:
            _validate_date(self.as_of, "as_of")
        if self.retrieved_at is not None:
            _validate_datetime(self.retrieved_at, "retrieved_at")
        if self.content_sha256 is not None and not _SHA256.fullmatch(self.content_sha256):
            raise SourceReceiptError(
                "content_sha256 must be 64 lowercase hexadecimal characters"
            )
        if self.terms_snapshot_sha256 is not None and not _SHA256.fullmatch(
            self.terms_snapshot_sha256
        ):
            raise SourceReceiptError(
                "terms_snapshot_sha256 must be 64 lowercase hexadecimal characters"
            )
        if (self.content_sha256 is None) != (self.content_bytes is None):
            raise SourceReceiptError(
                "content_sha256 and content_bytes must be recorded together"
            )
        if self.record_state == "candidate" and any(
            value is not None
            for value in (self.retrieved_at, self.content_sha256, self.content_bytes)
        ):
            raise SourceReceiptError("candidate receipts must not claim captured content")
        if self.record_state == "captured" and any(
            value is None
            for value in (self.retrieved_at, self.content_sha256, self.content_bytes)
        ):
            raise SourceReceiptError("captured receipts require time, digest, and byte count")
        if self.record_state == "captured" and self.content_bytes == 0:
            raise SourceReceiptError("captured receipts must bind non-empty content")

    def release_blockers(self) -> tuple[str, ...]:
        """Return every reason this receipt cannot enter a scored public release."""

        self.validate()
        blockers: list[str] = []
        if self.record_state != "captured":
            blockers.append("record_state is not captured")
        if self.content_sha256 is None or self.content_bytes is None:
            blockers.append("source content is not hash-bound")
        if self.retrieved_at is None:
            blockers.append("retrieval time is missing")
        if self.as_of is None:
            blockers.append("as_of date is missing")
        if self.terms_snapshot_sha256 is None:
            blockers.append("terms snapshot is not hash-bound")
        if self.redistribution == "undetermined":
            blockers.append("redistribution decision is undetermined")
        if self.third_party_status not in {"clear", "excluded"}:
            blockers.append("third-party rights review is incomplete")
        return tuple(blockers)

    @property
    def release_ready(self) -> bool:
        return not self.release_blockers()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "provider": self.provider,
            "resource_id": self.resource_id,
            "source_url": self.source_url,
            "terms_url": self.terms_url,
            "license_id": self.license_id,
            "license_name": self.license_name,
            "attribution": self.attribution,
            "languages": list(self.languages),
            "media_type": self.media_type,
            "redistribution": self.redistribution,
            "third_party_status": self.third_party_status,
            "record_state": self.record_state,
            "retrieved_at": self.retrieved_at,
            "as_of": self.as_of,
            "content_sha256": self.content_sha256,
            "content_bytes": self.content_bytes,
            "terms_checked_at": self.terms_checked_at,
            "terms_snapshot_sha256": self.terms_snapshot_sha256,
            "notes": self.notes,
        }


def capture_receipt(
    receipt: SourceReceipt,
    content: bytes,
    *,
    retrieved_at: str,
) -> SourceReceipt:
    """Bind a candidate receipt to exact bytes without changing legal fields."""

    receipt.validate()
    if receipt.record_state != "candidate":
        raise SourceReceiptError("only a candidate receipt can be captured")
    if not content:
        raise SourceReceiptError("captured source content must not be empty")
    _validate_datetime(retrieved_at, "retrieved_at")
    captured = replace(
        receipt,
        record_state="captured",
        retrieved_at=retrieved_at,
        content_sha256=content_sha256(content),
        content_bytes=len(content),
    )
    captured.validate()
    return captured


def verify_content(receipt: SourceReceipt, content: bytes) -> None:
    """Raise when exact bytes do not match a captured receipt."""

    receipt.validate()
    if receipt.content_sha256 is None or receipt.content_bytes is None:
        raise SourceReceiptError(f"receipt {receipt.receipt_id} has no captured content")
    actual_size = len(content)
    actual_digest = content_sha256(content)
    if actual_size != receipt.content_bytes or actual_digest != receipt.content_sha256:
        raise SourceDriftError(
            f"source drift for {receipt.receipt_id}: expected "
            f"{receipt.content_bytes} bytes/{receipt.content_sha256}, got "
            f"{actual_size} bytes/{actual_digest}"
        )


def validate_ledger(
    receipts: Iterable[SourceReceipt],
    *,
    require_release_ready: bool = False,
) -> list[SourceReceipt]:
    """Validate a complete ledger, including duplicate and release gates."""

    materialized = list(receipts)
    if not materialized:
        raise SourceReceiptError("source ledger must contain at least one receipt")
    seen: set[str] = set()
    release_failures: list[str] = []
    for receipt in materialized:
        receipt.validate()
        if receipt.receipt_id in seen:
            raise SourceReceiptError(f"duplicate source receipt: {receipt.receipt_id}")
        seen.add(receipt.receipt_id)
        if require_release_ready:
            release_failures.extend(
                f"{receipt.receipt_id}: {blocker}" for blocker in receipt.release_blockers()
            )
    if release_failures:
        raise SourceReceiptError(
            "source ledger is not release-ready: " + "; ".join(release_failures)
        )
    return materialized


def load_ledger(
    path: str | Path,
    *,
    require_release_ready: bool = False,
) -> list[SourceReceipt]:
    """Load a JSONL ledger and fail with the exact source line on malformed data."""

    ledger_path = Path(path)
    receipts: list[SourceReceipt] = []
    with ledger_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SourceReceiptError(
                    f"invalid JSON in {ledger_path} line {line_number}: {exc}"
                ) from exc
            if not isinstance(raw, dict):
                raise SourceReceiptError(
                    f"source receipt in {ledger_path} line {line_number} must be an object"
                )
            try:
                receipts.append(SourceReceipt.from_dict(raw))
            except SourceReceiptError as exc:
                raise SourceReceiptError(
                    f"invalid receipt in {ledger_path} line {line_number}: {exc}"
                ) from exc
    return validate_ledger(receipts, require_release_ready=require_release_ready)


def ledger_digest(receipts: Iterable[SourceReceipt]) -> str:
    """Hash a canonical, order-independent JSON representation of a ledger."""

    materialized = validate_ledger(receipts)
    payload = [
        receipt.to_dict() for receipt in sorted(materialized, key=lambda item: item.receipt_id)
    ]
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return content_sha256(canonical)
