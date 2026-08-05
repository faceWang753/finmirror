# Source Provenance Ledger

FinMirror v0.2 introduces strict source receipts for future real-source work. The ledger
is an auditable control surface: it binds an artifact to exact bytes and records the
rights review needed for release. It is not a downloader, a legal opinion, or a claim
that a candidate is benchmark-ready.

## Files

- `schema/source-receipt.schema.json` — interoperable JSON Schema;
- `src/finmirror/sources.py` — dependency-free runtime validation, hashing, and drift
  checks;
- `sources/v0.2/ledger.jsonl` — current candidate records;
- `schema/evidence-manifest.schema.json` — strict artifact-lineage schema;
- `src/finmirror/lineage.py` — byte verification, lineage-graph validation, and
  fail-closed evidence claim tiers;
- `sources/v0.2/evidence-manifest.json` — current hash-bound claim boundary;
- `docs/V0.2_PROTOCOL.md` — curation and release protocol.

## Receipt fields

| Field | Meaning |
|---|---|
| `receipt_id` | Stable FinMirror identifier; unique in one ledger |
| `provider`, `resource_id` | First-party provider and its stable resource identifier |
| `source_url` | Exact bounded artifact or query URL; HTTPS with no credentials or fragment |
| `terms_url` | Terms reviewed for this artifact |
| `license_id`, `license_name` | Licence reference; `LicenseRef-*` is used when no SPDX ID applies |
| `attribution` | Proposed source acknowledgment and non-endorsement wording |
| `languages`, `media_type` | Source-language and byte-format declarations |
| `record_state` | `candidate`, `captured`, or `blocked` |
| `retrieved_at`, `as_of` | Retrieval time and information cutoff |
| `content_sha256`, `content_bytes` | Identity of exact source bytes |
| `terms_checked_at`, `terms_snapshot_sha256` | Date and identity of reviewed terms |
| `redistribution` | `redistribute`, `fetch_only`, or release-blocking `undetermined` |
| `third_party_status` | `clear`, `excluded`, `unresolved`, or `not_reviewed` |
| `notes` | Scope, exclusions, and unresolved risks |

Runtime validation rejects unknown fields rather than silently accepting misspellings.
Structural validation is intentionally separate from release eligibility: a candidate
record can be valid metadata while still being prohibited from a scored release.

## Exact-byte capture

The library never normalizes source data before hashing. Encoding, compression, JSON
whitespace, and line endings are part of the captured identity.

```python
from dataclasses import replace
from pathlib import Path

from finmirror.sources import capture_receipt, load_ledger, verify_content

receipt = load_ledger("sources/v0.2/ledger.jsonl")[0]
raw = Path("reviewed-download.bin").read_bytes()
captured = capture_receipt(
    receipt,
    raw,
    retrieved_at="2026-07-31T15:00:00Z",
)
verify_content(captured, raw)

# Legal review remains independent of byte capture.
reviewed = replace(
    captured,
    redistribution="fetch_only",
    third_party_status="excluded",
    terms_snapshot_sha256="<64-lowercase-hex-digest>",
)
```

The example does not write the updated receipt automatically. A reviewer must inspect
and commit the complete diff, including legal fields, attribution, and exclusions.

## Fail-closed release check

```python
from finmirror.sources import ledger_digest, load_ledger

receipts = load_ledger(
    "sources/v0.2/ledger.jsonl",
    require_release_ready=True,
)
print(ledger_digest(receipts))
```

The committed ledger is expected to fail this check today because both rows are
candidate records without captured bytes or completed rights review. This is deliberate.

## Evidence lineage and claim tiers

A source receipt is necessary but insufficient: it says which provider bytes were
captured, not what evidence the evaluator actually saw. The evidence manifest closes
that gap with four non-interchangeable artifact kinds:

| Kind | Meaning | Required parentage |
|---|---|---|
| `synthetic` | Fully authored benchmark material | No source receipt or parent |
| `provider_capture` | Byte-exact content bound to a captured receipt | Source receipt; hash and size must match |
| `source_derived` | Deterministic extract or render | Provider capture plus process hash and disclosure |
| `evaluator_counterfactual` | Evaluator-authored transformed evidence | Source-derived parent plus transform, process hash, and disclosure |

Repository paths are relative and byte-verified. `fetch_only` artifacts have no
repository path. A provider capture cannot be stored in the repository unless its
receipt has an explicit `redistribute` decision. Counterfactuals must descend from a
source-derived artifact, so an edited value cannot be confused with an authentic
government publication.

```bash
finmirror evidence-status
```

The committed manifest binds `benchmark/v0.1/cases.jsonl` and reports
`SYNTHETIC_ONLY`. Candidate URLs in the ledger do not raise that tier. The possible
machine-derived tiers are:

1. `synthetic_only`;
2. `candidate_source_material`;
3. `captured_source_only`;
4. `release_ready_source_material`.

Only the fourth tier can satisfy `--require-real-source`, and only when a release-ready
receipt reaches evaluator-visible derived evidence. No tier asserts expert validation,
representativeness, safety, or production readiness.

## Drift semantics

`verify_content` compares both byte count and SHA-256. A mismatch raises
`SourceDriftError`; it does not overwrite the receipt or bless the new bytes. A changed
source requires a new reviewed receipt or an explicit versioned correction.

A matching digest establishes only byte identity. It does not prove that:

- the provider is authoritative for the intended claim;
- the data are accurate, complete, or current;
- redistribution rights exist;
- third-party material is absent; or
- extraction and rendering preserved the financially relevant meaning.

Those properties require the independent gates in the v0.2 protocol.

## Current source states

The ledger identifies two official source families:

- Statistics Canada Table 36-10-0104-01 is captured as an exact English full-table ZIP,
  covered by the Statistics Canada Open Licence, and connected to a reproducible
  one-group calibration artifact;
- Bank of Canada series V39079 remains a candidate with unresolved record-level rights
  and no captured content.

The Statistics Canada lineage can pass the real-source material gate, but the separate
expert-review gate remains blocked. The Bank of Canada candidate explicitly excludes
exchange-rate data and other third-party series from its scope and cannot enter a
release until its terms and third-party review are complete.
