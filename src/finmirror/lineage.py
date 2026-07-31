"""Hash-bound evidence lineage for synthetic and real-source pilot artifacts.

Source receipts bind provider bytes and rights review. This module binds the next
layer: every evaluator-visible artifact is classified as synthetic, a byte-exact
provider capture, a deterministic source-derived render, or an evaluator-authored
counterfactual. The graph is deliberately strict so a derived artifact cannot be
mistaken for an authentic provider publication.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from finmirror.sources import (
    SourceReceipt,
    content_sha256,
    ledger_digest,
    validate_ledger,
)

ArtifactKind = Literal[
    "synthetic",
    "provider_capture",
    "source_derived",
    "evaluator_counterfactual",
]
ArtifactStorage = Literal["repository", "fetch_only"]
EvidenceClaimTier = Literal[
    "synthetic_only",
    "candidate_source_material",
    "captured_source_only",
    "release_ready_source_material",
]

SCHEMA_VERSION = "1.0"
ARTIFACT_KINDS = frozenset(
    {"synthetic", "provider_capture", "source_derived", "evaluator_counterfactual"}
)
ARTIFACT_STORAGE_VALUES = frozenset({"repository", "fetch_only"})
ARTIFACT_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "kind",
        "content_sha256",
        "content_bytes",
        "media_type",
        "storage",
        "path",
        "receipt_id",
        "parent_artifact_id",
        "process_id",
        "process_sha256",
        "transform",
        "disclosure",
    }
)
MANIFEST_REQUIRED_FIELDS = frozenset(
    {"schema_version", "manifest_id", "ledger_sha256", "artifacts"}
)

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EvidenceLineageError(ValueError):
    """An evidence manifest, artifact, or lineage claim failed validation."""


def _strict_fields(
    data: Mapping[str, Any],
    required: frozenset[str],
    label: str,
) -> None:
    keys = set(data)
    missing = required - keys
    extra = keys - required
    if missing:
        raise EvidenceLineageError(f"{label} is missing fields: {sorted(missing)}")
    if extra:
        raise EvidenceLineageError(f"{label} has unknown fields: {sorted(extra)}")


def _non_empty_string(data: Mapping[str, Any], field: str) -> str:
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise EvidenceLineageError(f"{field} must be a non-empty string")
    return value.strip()


def _nullable_string(data: Mapping[str, Any], field: str) -> str | None:
    value = data[field]
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise EvidenceLineageError(f"{field} must be null or a non-empty string")
    return value.strip()


def _validate_digest(value: str, field: str) -> None:
    if not _SHA256.fullmatch(value):
        raise EvidenceLineageError(f"{field} must be 64 lowercase hexadecimal characters")


def _validate_repository_path(value: str) -> None:
    if "\\" in value:
        raise EvidenceLineageError("path must use POSIX separators")
    parsed = PurePosixPath(value)
    if (
        parsed.is_absolute()
        or not parsed.parts
        or any(part in {"", ".", ".."} for part in parsed.parts)
    ):
        raise EvidenceLineageError("path must be a safe repository-relative POSIX path")


@dataclass(frozen=True)
class EvidenceArtifact:
    """One byte-bound artifact and its relationship to provider evidence."""

    schema_version: str
    artifact_id: str
    kind: ArtifactKind
    content_sha256: str
    content_bytes: int
    media_type: str
    storage: ArtifactStorage
    path: str | None
    receipt_id: str | None
    parent_artifact_id: str | None
    process_id: str | None
    process_sha256: str | None
    transform: str | None
    disclosure: str | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvidenceArtifact:
        _strict_fields(data, ARTIFACT_REQUIRED_FIELDS, "evidence artifact")
        raw_bytes = data["content_bytes"]
        if isinstance(raw_bytes, bool) or not isinstance(raw_bytes, int):
            raise EvidenceLineageError("content_bytes must be a positive integer")
        artifact = cls(
            schema_version=_non_empty_string(data, "schema_version"),
            artifact_id=_non_empty_string(data, "artifact_id"),
            kind=_non_empty_string(data, "kind"),  # type: ignore[arg-type]
            content_sha256=_non_empty_string(data, "content_sha256"),
            content_bytes=raw_bytes,
            media_type=_non_empty_string(data, "media_type"),
            storage=_non_empty_string(data, "storage"),  # type: ignore[arg-type]
            path=_nullable_string(data, "path"),
            receipt_id=_nullable_string(data, "receipt_id"),
            parent_artifact_id=_nullable_string(data, "parent_artifact_id"),
            process_id=_nullable_string(data, "process_id"),
            process_sha256=_nullable_string(data, "process_sha256"),
            transform=_nullable_string(data, "transform"),
            disclosure=_nullable_string(data, "disclosure"),
        )
        artifact.validate()
        return artifact

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise EvidenceLineageError(
                f"unsupported evidence artifact schema_version: {self.schema_version}"
            )
        if not _IDENTIFIER.fullmatch(self.artifact_id):
            raise EvidenceLineageError("artifact_id must be a stable lowercase identifier")
        if self.kind not in ARTIFACT_KINDS:
            raise EvidenceLineageError(f"unsupported artifact kind: {self.kind}")
        if self.storage not in ARTIFACT_STORAGE_VALUES:
            raise EvidenceLineageError(f"unsupported artifact storage: {self.storage}")
        _validate_digest(self.content_sha256, "content_sha256")
        if self.content_bytes <= 0:
            raise EvidenceLineageError("content_bytes must be a positive integer")
        if "/" not in self.media_type or any(char.isspace() for char in self.media_type):
            raise EvidenceLineageError("media_type must be a compact type/subtype value")
        if self.process_sha256 is not None:
            _validate_digest(self.process_sha256, "process_sha256")
        if (self.process_id is None) != (self.process_sha256 is None):
            raise EvidenceLineageError(
                "process_id and process_sha256 must be recorded together"
            )
        if self.storage == "repository":
            if self.path is None:
                raise EvidenceLineageError("repository artifacts require path")
            _validate_repository_path(self.path)
        elif self.path is not None:
            raise EvidenceLineageError("fetch_only artifacts must not declare path")

        lineage = (
            self.receipt_id,
            self.parent_artifact_id,
            self.process_id,
            self.process_sha256,
            self.transform,
            self.disclosure,
        )
        if self.kind == "synthetic":
            if any(value is not None for value in lineage):
                raise EvidenceLineageError("synthetic artifacts must not claim source lineage")
        elif self.kind == "provider_capture":
            if self.receipt_id is None:
                raise EvidenceLineageError("provider captures require receipt_id")
            if any(value is not None for value in lineage[1:]):
                raise EvidenceLineageError("provider captures must bind only a source receipt")
        elif self.kind == "source_derived":
            if any(
                value is None
                for value in (
                    self.receipt_id,
                    self.parent_artifact_id,
                    self.process_id,
                    self.process_sha256,
                    self.disclosure,
                )
            ):
                raise EvidenceLineageError(
                    "source-derived artifacts require receipt, parent, process, and disclosure"
                )
            if self.transform is not None:
                raise EvidenceLineageError(
                    "source-derived artifacts must not declare a counterfactual transform"
                )
        else:
            if any(
                value is None
                for value in (
                    self.receipt_id,
                    self.parent_artifact_id,
                    self.process_id,
                    self.process_sha256,
                    self.transform,
                    self.disclosure,
                )
            ):
                raise EvidenceLineageError(
                    "evaluator counterfactuals require receipt, parent, process, transform, and disclosure"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "kind": self.kind,
            "content_sha256": self.content_sha256,
            "content_bytes": self.content_bytes,
            "media_type": self.media_type,
            "storage": self.storage,
            "path": self.path,
            "receipt_id": self.receipt_id,
            "parent_artifact_id": self.parent_artifact_id,
            "process_id": self.process_id,
            "process_sha256": self.process_sha256,
            "transform": self.transform,
            "disclosure": self.disclosure,
        }


@dataclass(frozen=True)
class EvidenceManifest:
    """A ledger-bound collection of evidence artifacts."""

    schema_version: str
    manifest_id: str
    ledger_sha256: str
    artifacts: tuple[EvidenceArtifact, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvidenceManifest:
        _strict_fields(data, MANIFEST_REQUIRED_FIELDS, "evidence manifest")
        raw_artifacts = data["artifacts"]
        if not isinstance(raw_artifacts, list) or not raw_artifacts:
            raise EvidenceLineageError("artifacts must be a non-empty JSON array")
        if not all(isinstance(item, dict) for item in raw_artifacts):
            raise EvidenceLineageError("artifacts must contain only JSON objects")
        manifest = cls(
            schema_version=_non_empty_string(data, "schema_version"),
            manifest_id=_non_empty_string(data, "manifest_id"),
            ledger_sha256=_non_empty_string(data, "ledger_sha256"),
            artifacts=tuple(EvidenceArtifact.from_dict(item) for item in raw_artifacts),
        )
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise EvidenceLineageError(
                f"unsupported evidence manifest schema_version: {self.schema_version}"
            )
        if not _IDENTIFIER.fullmatch(self.manifest_id):
            raise EvidenceLineageError("manifest_id must be a stable lowercase identifier")
        _validate_digest(self.ledger_sha256, "ledger_sha256")
        if not self.artifacts:
            raise EvidenceLineageError("evidence manifest must contain at least one artifact")
        seen: set[str] = set()
        for artifact in self.artifacts:
            artifact.validate()
            if artifact.artifact_id in seen:
                raise EvidenceLineageError(
                    f"duplicate evidence artifact: {artifact.artifact_id}"
                )
            seen.add(artifact.artifact_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "ledger_sha256": self.ledger_sha256,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }


def load_evidence_manifest(path: str | Path) -> EvidenceManifest:
    """Load one strict evidence manifest from JSON."""

    manifest_path = Path(path)
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceLineageError(f"invalid JSON in {manifest_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise EvidenceLineageError(f"evidence manifest in {manifest_path} must be an object")
    return EvidenceManifest.from_dict(raw)


def validate_lineage(
    manifest: EvidenceManifest,
    receipts: Iterable[SourceReceipt],
    *,
    require_release_ready: bool = False,
) -> tuple[EvidenceArtifact, ...]:
    """Validate the artifact graph against an exact source ledger."""

    manifest.validate()
    materialized_receipts = validate_ledger(receipts)
    actual_ledger_digest = ledger_digest(materialized_receipts)
    if manifest.ledger_sha256 != actual_ledger_digest:
        raise EvidenceLineageError(
            "evidence manifest ledger_sha256 does not match the supplied ledger"
        )
    receipt_by_id = {receipt.receipt_id: receipt for receipt in materialized_receipts}
    artifact_by_id = {artifact.artifact_id: artifact for artifact in manifest.artifacts}
    referenced_receipts: dict[str, SourceReceipt] = {}

    for artifact in manifest.artifacts:
        if artifact.receipt_id is None:
            continue
        receipt = receipt_by_id.get(artifact.receipt_id)
        if receipt is None:
            raise EvidenceLineageError(
                f"artifact {artifact.artifact_id} references unknown receipt "
                f"{artifact.receipt_id}"
            )
        referenced_receipts[receipt.receipt_id] = receipt
        if artifact.storage == "repository" and receipt.redistribution != "redistribute":
            raise EvidenceLineageError(
                f"source-linked artifact {artifact.artifact_id} cannot be stored in the "
                "repository without a redistribute decision"
            )
        if artifact.kind == "provider_capture":
            if receipt.record_state != "captured":
                raise EvidenceLineageError(
                    f"provider capture {artifact.artifact_id} requires a captured receipt"
                )
            if (
                artifact.content_sha256 != receipt.content_sha256
                or artifact.content_bytes != receipt.content_bytes
            ):
                raise EvidenceLineageError(
                    f"provider capture {artifact.artifact_id} does not match receipt bytes"
                )
            continue

        parent_id = artifact.parent_artifact_id
        if parent_id is None:
            raise EvidenceLineageError(
                f"artifact {artifact.artifact_id} is missing its lineage parent"
            )
        parent = artifact_by_id.get(parent_id)
        if parent is None:
            raise EvidenceLineageError(
                f"artifact {artifact.artifact_id} references unknown parent {parent_id}"
            )
        if parent.receipt_id != artifact.receipt_id:
            raise EvidenceLineageError(
                f"artifact {artifact.artifact_id} and parent {parent_id} use different receipts"
            )
        if artifact.kind == "source_derived" and parent.kind != "provider_capture":
            raise EvidenceLineageError(
                f"source-derived artifact {artifact.artifact_id} must descend from a provider capture"
            )
        if artifact.kind == "evaluator_counterfactual" and parent.kind != "source_derived":
            raise EvidenceLineageError(
                f"evaluator counterfactual {artifact.artifact_id} must descend from a source-derived artifact"
            )

    if require_release_ready:
        failures = [
            f"{receipt_id}: {blocker}"
            for receipt_id, receipt in sorted(referenced_receipts.items())
            for blocker in receipt.release_blockers()
        ]
        if failures:
            raise EvidenceLineageError(
                "evidence lineage is not release-ready: " + "; ".join(failures)
            )
    return manifest.artifacts


def evidence_claim_tier(
    manifest: EvidenceManifest,
    receipts: Iterable[SourceReceipt],
) -> EvidenceClaimTier:
    """Return the strongest source-material claim justified by this manifest.

    This tier never asserts expert validation, representativeness, model reliability,
    or deployment readiness. Those require independent review artifacts and gates.
    """

    materialized_receipts = validate_ledger(receipts)
    validate_lineage(manifest, materialized_receipts)
    source_artifacts = [
        artifact for artifact in manifest.artifacts if artifact.kind != "synthetic"
    ]
    if not source_artifacts:
        return "synthetic_only"
    receipt_by_id = {receipt.receipt_id: receipt for receipt in materialized_receipts}
    used_receipts = {
        artifact.receipt_id for artifact in source_artifacts if artifact.receipt_id is not None
    }
    if any(not receipt_by_id[receipt_id].release_ready for receipt_id in used_receipts):
        return "candidate_source_material"
    if not any(artifact.kind == "source_derived" for artifact in source_artifacts):
        return "captured_source_only"
    return "release_ready_source_material"


def require_real_source_material(
    manifest: EvidenceManifest,
    receipts: Iterable[SourceReceipt],
) -> None:
    """Fail unless release-ready provider material reaches evaluator-visible evidence."""

    materialized_receipts = validate_ledger(receipts)
    tier = evidence_claim_tier(manifest, materialized_receipts)
    if tier != "release_ready_source_material":
        raise EvidenceLineageError("real-source claim blocked: evidence tier is " + tier)
    validate_lineage(manifest, materialized_receipts, require_release_ready=True)


def verify_repository_artifacts(
    manifest: EvidenceManifest,
    root: str | Path,
) -> None:
    """Verify byte identity for every artifact committed by repository-relative path."""

    manifest.validate()
    root_path = Path(root).resolve(strict=True)
    if not root_path.is_dir():
        raise EvidenceLineageError("artifact root must be a directory")
    for artifact in manifest.artifacts:
        if artifact.storage != "repository":
            continue
        if artifact.path is None:
            raise EvidenceLineageError(
                f"repository artifact {artifact.artifact_id} has no path"
            )
        candidate = (root_path / Path(*PurePosixPath(artifact.path).parts)).resolve(strict=True)
        try:
            candidate.relative_to(root_path)
        except ValueError as exc:
            raise EvidenceLineageError(
                f"artifact {artifact.artifact_id} resolves outside the repository root"
            ) from exc
        content = candidate.read_bytes()
        actual_digest = content_sha256(content)
        if len(content) != artifact.content_bytes or actual_digest != artifact.content_sha256:
            raise EvidenceLineageError(
                f"artifact drift for {artifact.artifact_id}: expected "
                f"{artifact.content_bytes} bytes/{artifact.content_sha256}, got "
                f"{len(content)} bytes/{actual_digest}"
            )
