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

## Current candidates

The initial ledger identifies two official candidate families:

- Statistics Canada Table 36-10-0104-01, quarterly expenditure-based GDP;
- Bank of Canada series V39079, target for the overnight rate, with a fixed date range.

Neither row is approved for release. The Bank of Canada candidate explicitly excludes
exchange-rate data and other third-party series from its scope. Record-level terms and
third-party review must be completed before either source is used.
