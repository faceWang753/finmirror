"""Tests for evidence lineage and fail-closed real-source claim tiers."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from finmirror.lineage import (
    ARTIFACT_REQUIRED_FIELDS,
    MANIFEST_REQUIRED_FIELDS,
    EvidenceArtifact,
    EvidenceLineageError,
    EvidenceManifest,
    evidence_claim_tier,
    load_evidence_manifest,
    require_real_source_material,
    validate_lineage,
    verify_repository_artifacts,
)
from finmirror.sources import (
    SourceReceipt,
    capture_receipt,
    content_sha256,
    ledger_digest,
    load_ledger,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _candidate() -> SourceReceipt:
    return SourceReceipt.from_dict(
        {
            "schema_version": "1.0",
            "receipt_id": "official-series-001",
            "provider": "Official Provider",
            "resource_id": "SERIES-001",
            "source_url": "https://data.example.org/series/001",
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
    )


def _captured(*, release_ready: bool) -> tuple[SourceReceipt, bytes]:
    raw = b'{"series":"SERIES-001","value":4.25}'
    captured = capture_receipt(
        _candidate(),
        raw,
        retrieved_at="2026-07-31T15:00:00Z",
    )
    if not release_ready:
        return captured, raw
    return (
        replace(
            captured,
            redistribution="fetch_only",
            third_party_status="excluded",
            terms_snapshot_sha256=content_sha256(b"reviewed provider terms"),
        ),
        raw,
    )


def _artifact(
    artifact_id: str,
    kind: str,
    content: bytes,
    *,
    receipt_id: str | None = None,
    parent_artifact_id: str | None = None,
    process_id: str | None = None,
    process_sha256: str | None = None,
    transform: str | None = None,
    disclosure: str | None = None,
    storage: str = "fetch_only",
    path: str | None = None,
) -> EvidenceArtifact:
    return EvidenceArtifact.from_dict(
        {
            "schema_version": "1.0",
            "artifact_id": artifact_id,
            "kind": kind,
            "content_sha256": content_sha256(content),
            "content_bytes": len(content),
            "media_type": "application/json",
            "storage": storage,
            "path": path,
            "receipt_id": receipt_id,
            "parent_artifact_id": parent_artifact_id,
            "process_id": process_id,
            "process_sha256": process_sha256,
            "transform": transform,
            "disclosure": disclosure,
        }
    )


def _manifest(receipt: SourceReceipt, *artifacts: EvidenceArtifact) -> EvidenceManifest:
    return EvidenceManifest(
        schema_version="1.0",
        manifest_id="pilot-lineage-001",
        ledger_sha256=ledger_digest([receipt]),
        artifacts=artifacts,
    )


def _real_source_chain(
    receipt: SourceReceipt,
    raw: bytes,
) -> tuple[EvidenceArtifact, EvidenceArtifact, EvidenceArtifact]:
    process_digest = content_sha256(b"renderer implementation v1")
    capture = _artifact(
        "provider-capture-001",
        "provider_capture",
        raw,
        receipt_id=receipt.receipt_id,
    )
    rendered = _artifact(
        "source-render-001",
        "source_derived",
        b'{"metric":"target rate","value":4.25}',
        receipt_id=receipt.receipt_id,
        parent_artifact_id=capture.artifact_id,
        process_id="json-field-renderer-v1",
        process_sha256=process_digest,
        disclosure="Deterministic extract from the captured provider response.",
    )
    counterfactual = _artifact(
        "counterfactual-001",
        "evaluator_counterfactual",
        b'{"metric":"target rate","value":4.50}',
        receipt_id=receipt.receipt_id,
        parent_artifact_id=rendered.artifact_id,
        process_id="atomic-value-transform-v1",
        process_sha256=content_sha256(b"counterfactual transformer v1"),
        transform="replace target rate 4.25 with 4.50",
        disclosure=(
            "Evaluator-authored counterfactual; this is not an authentic provider publication."
        ),
    )
    return capture, rendered, counterfactual


def test_committed_schema_and_runtime_require_the_same_fields() -> None:
    schema = json.loads(
        (PROJECT_ROOT / "schema" / "evidence-manifest.schema.json").read_text(encoding="utf-8")
    )
    assert set(schema["required"]) == MANIFEST_REQUIRED_FIELDS
    assert set(schema["$defs"]["artifact"]["required"]) == ARTIFACT_REQUIRED_FIELDS
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["artifact"]["additionalProperties"] is False
    assert len(schema["$defs"]["artifact"]["allOf"]) == 5


def test_committed_manifest_proves_release_ready_source_lineage() -> None:
    receipts = load_ledger(PROJECT_ROOT / "sources" / "v0.2" / "ledger.jsonl")
    manifest = load_evidence_manifest(
        PROJECT_ROOT / "sources" / "v0.2" / "evidence-manifest.json"
    )
    validate_lineage(manifest, receipts)
    verify_repository_artifacts(manifest, PROJECT_ROOT)
    assert evidence_claim_tier(manifest, receipts) == "release_ready_source_material"
    require_real_source_material(manifest, receipts)


def test_release_ready_source_chain_reaches_evaluator_visible_material() -> None:
    receipt, raw = _captured(release_ready=True)
    chain = _real_source_chain(receipt, raw)
    manifest = _manifest(receipt, *chain)
    validate_lineage(manifest, [receipt], require_release_ready=True)
    assert evidence_claim_tier(manifest, [receipt]) == "release_ready_source_material"
    require_real_source_material(manifest, [receipt])


def test_captured_but_unreviewed_source_remains_candidate_material() -> None:
    receipt, raw = _captured(release_ready=False)
    manifest = _manifest(receipt, *_real_source_chain(receipt, raw))
    assert evidence_claim_tier(manifest, [receipt]) == "candidate_source_material"
    with pytest.raises(EvidenceLineageError, match="candidate_source_material"):
        require_real_source_material(manifest, [receipt])
    with pytest.raises(EvidenceLineageError, match="redistribution decision"):
        validate_lineage(manifest, [receipt], require_release_ready=True)


def test_capture_without_render_cannot_claim_evaluator_visible_real_source() -> None:
    receipt, raw = _captured(release_ready=True)
    capture = _real_source_chain(receipt, raw)[0]
    manifest = _manifest(receipt, capture)
    assert evidence_claim_tier(manifest, [receipt]) == "captured_source_only"
    with pytest.raises(EvidenceLineageError, match="captured_source_only"):
        require_real_source_material(manifest, [receipt])


def test_fetch_only_source_material_cannot_be_committed_to_repository() -> None:
    receipt, raw = _captured(release_ready=True)
    capture = _artifact(
        "provider-capture-001",
        "provider_capture",
        raw,
        receipt_id=receipt.receipt_id,
        storage="repository",
        path="sources/provider-capture.json",
    )
    with pytest.raises(EvidenceLineageError, match="without a redistribute decision"):
        validate_lineage(_manifest(receipt, capture), [receipt])


def test_provider_capture_must_match_receipt_bytes() -> None:
    receipt, raw = _captured(release_ready=True)
    capture = _artifact(
        "provider-capture-001",
        "provider_capture",
        raw + b"drift",
        receipt_id=receipt.receipt_id,
    )
    with pytest.raises(EvidenceLineageError, match="does not match receipt bytes"):
        validate_lineage(_manifest(receipt, capture), [receipt])


def test_derived_artifacts_require_typed_parent_chain_and_same_receipt() -> None:
    receipt, raw = _captured(release_ready=True)
    capture, rendered, counterfactual = _real_source_chain(receipt, raw)
    wrong_parent = replace(rendered, parent_artifact_id="missing-capture")
    with pytest.raises(EvidenceLineageError, match="unknown parent"):
        validate_lineage(_manifest(receipt, capture, wrong_parent), [receipt])

    wrong_kind = replace(counterfactual, parent_artifact_id=capture.artifact_id)
    with pytest.raises(EvidenceLineageError, match="source-derived artifact"):
        validate_lineage(_manifest(receipt, capture, wrong_kind), [receipt])


def test_manifest_rejects_ledger_drift_and_duplicate_artifacts() -> None:
    receipt, raw = _captured(release_ready=True)
    capture = _real_source_chain(receipt, raw)[0]
    duplicate = _manifest(receipt, capture, capture)
    with pytest.raises(EvidenceLineageError, match="duplicate evidence artifact"):
        validate_lineage(duplicate, [receipt])

    stale = replace(_manifest(receipt, capture), ledger_sha256="0" * 64)
    with pytest.raises(EvidenceLineageError, match="does not match"):
        validate_lineage(stale, [receipt])


def test_repository_artifact_verification_detects_drift(tmp_path: Path) -> None:
    receipt, _ = _captured(release_ready=True)
    path = tmp_path / "artifact.json"
    path.write_bytes(b'{"kind":"synthetic"}')
    artifact = _artifact(
        "synthetic-artifact-001",
        "synthetic",
        path.read_bytes(),
        storage="repository",
        path="artifact.json",
    )
    manifest = _manifest(receipt, artifact)
    verify_repository_artifacts(manifest, tmp_path)
    path.write_bytes(b'{"kind":"changed"}')
    with pytest.raises(EvidenceLineageError, match="artifact drift"):
        verify_repository_artifacts(manifest, tmp_path)


@pytest.mark.parametrize("path", ["../secret.json", "/absolute.json", "dir\\file.json"])
def test_repository_paths_are_fail_closed(path: str) -> None:
    with pytest.raises(EvidenceLineageError, match="path"):
        _artifact(
            "synthetic-artifact-001",
            "synthetic",
            b"payload",
            storage="repository",
            path=path,
        )


def test_counterfactual_requires_explicit_disclosure() -> None:
    with pytest.raises(EvidenceLineageError, match="require receipt, parent, process"):
        _artifact(
            "counterfactual-001",
            "evaluator_counterfactual",
            b"payload",
            receipt_id="official-series-001",
            parent_artifact_id="source-render-001",
            process_id="transform-v1",
            process_sha256=content_sha256(b"transformer"),
            transform="change value",
            disclosure=None,
        )


def _synthetic_data() -> dict[str, object]:
    return _artifact(
        "synthetic-artifact-001",
        "synthetic",
        b"payload",
    ).to_dict()


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"artifact_id": ""}, "non-empty string"),
        ({"path": 7}, "null or a non-empty string"),
        ({"content_bytes": True}, "positive integer"),
        ({"schema_version": "2.0"}, "unsupported evidence artifact schema_version"),
        ({"artifact_id": "INVALID"}, "stable lowercase identifier"),
        ({"kind": "unknown"}, "unsupported artifact kind"),
        ({"storage": "cloud"}, "unsupported artifact storage"),
        ({"content_sha256": "0" * 63}, "64 lowercase hexadecimal"),
        ({"content_bytes": 0}, "positive integer"),
        ({"media_type": "json"}, "compact type/subtype"),
        ({"process_id": "process-v1"}, "recorded together"),
        ({"storage": "repository"}, "repository artifacts require path"),
        ({"path": "artifact.json"}, "fetch_only artifacts must not declare path"),
        ({"receipt_id": "official-series-001"}, "must not claim source lineage"),
        ({"kind": "provider_capture"}, "provider captures require receipt_id"),
        (
            {
                "kind": "provider_capture",
                "receipt_id": "official-series-001",
                "process_id": "process-v1",
                "process_sha256": "0" * 64,
            },
            "must bind only a source receipt",
        ),
        (
            {"kind": "source_derived", "receipt_id": "official-series-001"},
            "source-derived artifacts require",
        ),
        (
            {
                "kind": "source_derived",
                "receipt_id": "official-series-001",
                "parent_artifact_id": "provider-capture-001",
                "process_id": "renderer-v1",
                "process_sha256": "0" * 64,
                "transform": "change value",
                "disclosure": "Derived evidence.",
            },
            "must not declare a counterfactual transform",
        ),
    ],
)
def test_artifact_contract_rejects_ambiguous_or_malformed_fields(
    updates: dict[str, object],
    message: str,
) -> None:
    data = _synthetic_data()
    data.update(updates)
    with pytest.raises(EvidenceLineageError, match=message):
        EvidenceArtifact.from_dict(data)


def test_artifact_contract_rejects_missing_and_unknown_fields() -> None:
    missing = _synthetic_data()
    missing.pop("disclosure")
    with pytest.raises(EvidenceLineageError, match="missing fields"):
        EvidenceArtifact.from_dict(missing)
    extra = _synthetic_data()
    extra["claim"] = "real"
    with pytest.raises(EvidenceLineageError, match="unknown fields"):
        EvidenceArtifact.from_dict(extra)


def test_manifest_loader_and_contract_fail_closed(tmp_path: Path) -> None:
    artifact = _synthetic_data()
    valid = {
        "schema_version": "1.0",
        "manifest_id": "manifest-001",
        "ledger_sha256": "0" * 64,
        "artifacts": [artifact],
    }
    assert EvidenceManifest.from_dict(valid).to_dict() == valid

    for field, value, message in (
        ("schema_version", "2.0", "unsupported evidence manifest schema_version"),
        ("manifest_id", "INVALID", "stable lowercase identifier"),
        ("ledger_sha256", "0" * 63, "64 lowercase hexadecimal"),
        ("artifacts", [], "non-empty JSON array"),
        ("artifacts", ["artifact"], "only JSON objects"),
    ):
        invalid = dict(valid)
        invalid[field] = value
        with pytest.raises(EvidenceLineageError, match=message):
            EvidenceManifest.from_dict(invalid)

    empty = EvidenceManifest("1.0", "manifest-001", "0" * 64, ())
    with pytest.raises(EvidenceLineageError, match="at least one artifact"):
        empty.validate()

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(EvidenceLineageError, match="invalid JSON"):
        load_evidence_manifest(malformed)
    not_object = tmp_path / "list.json"
    not_object.write_text("[]", encoding="utf-8")
    with pytest.raises(EvidenceLineageError, match="must be an object"):
        load_evidence_manifest(not_object)


def test_lineage_rejects_unknown_receipt_and_uncaptured_provider_bytes() -> None:
    receipt, raw = _captured(release_ready=True)
    capture = _real_source_chain(receipt, raw)[0]
    unknown = replace(capture, receipt_id="unknown-receipt")
    with pytest.raises(EvidenceLineageError, match="unknown receipt"):
        validate_lineage(_manifest(receipt, unknown), [receipt])

    candidate = _candidate()
    claimed_capture = _artifact(
        "provider-capture-001",
        "provider_capture",
        raw,
        receipt_id=candidate.receipt_id,
    )
    with pytest.raises(EvidenceLineageError, match="requires a captured receipt"):
        validate_lineage(_manifest(candidate, claimed_capture), [candidate])


def test_source_derived_artifact_cannot_descend_from_counterfactual() -> None:
    receipt, raw = _captured(release_ready=True)
    capture, rendered, counterfactual = _real_source_chain(receipt, raw)
    invalid = replace(
        rendered,
        artifact_id="source-render-invalid",
        parent_artifact_id=counterfactual.artifact_id,
    )
    with pytest.raises(EvidenceLineageError, match="must descend from a provider capture"):
        validate_lineage(
            _manifest(receipt, capture, rendered, counterfactual, invalid),
            [receipt],
        )


def test_repository_verifier_rejects_file_as_root(tmp_path: Path) -> None:
    receipt, _ = _captured(release_ready=True)
    root_file = tmp_path / "not-a-directory"
    root_file.write_bytes(b"root")
    manifest = _manifest(
        receipt,
        _artifact("synthetic-artifact-001", "synthetic", b"payload"),
    )
    with pytest.raises(EvidenceLineageError, match="root must be a directory"):
        verify_repository_artifacts(manifest, root_file)
