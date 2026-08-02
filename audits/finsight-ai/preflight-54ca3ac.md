# FinSight-AI reproducibility preflight

| Field | Value |
|---|---|
| Project | [`juanjuandog/FinSight-AI`](https://github.com/juanjuandog/FinSight-AI) |
| Upstream revision | `54ca3ac2ba5178a0c17daa4a773cb9462f274206` |
| Review date | 2026-07-27; maintainer feedback incorporated 2026-07-31; upstream merge verified 2026-08-02 |
| Reviewer | Mingyang (Ethan) Wang |
| FinMirror stage | Integration preflight; **not an executed reliability audit** |
| Upstream contribution | [PR #14](https://github.com/juanjuandog/FinSight-AI/pull/14), merged as [`d2b9b60`](https://github.com/juanjuandog/FinSight-AI/commit/d2b9b6043135e6863eaf8b84457b2cdec71539e6) |

## Conclusion

FinSight-AI exposes a useful answer/evidence/trace contract, but the pinned revision does
not bind an answer to the exact ordered evidence sent to generation. A trace records only
`evidenceCount`; equal counts can conceal changes in document identity, content, score,
or rerank order. That prevents a third party from proving that two reproduced runs used
the same retrieved context.

The merged PR #14 adds a focused remedy: a stable SHA-256 `dataSnapshotHash` over the complete
ordered `EvidenceChunk` list, exposed in `RagTrace` and persisted through a nullable
database migration. After maintainer review, the boundary is the ordered content sent
to answer generation: document ID, title, document type, publication date, section, and
text. Retrieval score is deliberately excluded because the current generation prompt
does not consume it; a score-only change therefore does not alter the model context.

This is a reproducibility finding, not a claim about answer quality, investment quality,
security, or production safety.

## Evidence inspected

At the pinned revision:

- `AnalysisApplicationService.ask` retrieves, reranks, truncates, and sends at most five
  `EvidenceChunk` records to answer generation.
- `RagTrace` records `structuredQuery`, retrieval channels, `evidenceCount`, and latency,
  but not the identity of that context.
- `JdbcRagTraceRepository` persists the trace count and latency, but not an evidence
  digest.
- `RestAiServiceClient` can fall back independently during reranking or generation.
  Exact execution-path provenance is therefore a separate follow-up concern; it is not
  scored here and is deliberately outside the single-concern PR.

Source links:

- [`AnalysisApplicationService.java`](https://github.com/juanjuandog/FinSight-AI/blob/54ca3ac2ba5178a0c17daa4a773cb9462f274206/backend/src/main/java/com/finsight/application/AnalysisApplicationService.java)
- [`RagTrace.java`](https://github.com/juanjuandog/FinSight-AI/blob/54ca3ac2ba5178a0c17daa4a773cb9462f274206/backend/src/main/java/com/finsight/domain/model/RagTrace.java)
- [`JdbcRagTraceRepository.java`](https://github.com/juanjuandog/FinSight-AI/blob/54ca3ac2ba5178a0c17daa4a773cb9462f274206/backend/src/main/java/com/finsight/infrastructure/jdbc/JdbcRagTraceRepository.java)
- [`RestAiServiceClient.java`](https://github.com/juanjuandog/FinSight-AI/blob/54ca3ac2ba5178a0c17daa4a773cb9462f274206/backend/src/main/java/com/finsight/ai/RestAiServiceClient.java)

## Capability map

| FinMirror surface | Pinned support | Preflight treatment |
|---|---|---|
| Answer capture | Yes | Mappable |
| Retrieved evidence capture | Yes | Mappable |
| Retrieval trace | Partial | Count and channels exist; exact snapshot identity missing |
| Citation identifiers | Evidence document IDs exist | Mappable as evidence provenance, not yet scored as answer-level citations |
| Probability confidence | Not exposed | `not_exposed`; calibration is not applicable |
| Arbitrary frozen corpus injection | Not exposed through the public API | Blocks a fair paired-world execution |
| Deterministic no-key fallback | Yes | Suitable for harness integration, but must not be described as a hosted-LLM result |

## Why no FinMirror score is published

A paired audit requires the same system configuration to run independently against two
frozen evidence worlds. The public ingestion path at this revision does not provide an
arbitrary, test-scoped fixture corpus seam. Substituting live public-market data would
introduce temporal drift and would not reproduce the authored intervention contract.

Accordingly, this preflight reports the integration blocker and contributes the first
reproducibility primitive. It does **not** manufacture a score from partial or live data.
A full audit should begin only after a frozen-corpus seam exists.

## Patch verification

Reviewed fork patch commit:
[`41291521c041dd970d6670c509f9f709d837420f`](https://github.com/faceWang753/FinSight-AI/commit/41291521c041dd970d6670c509f9f709d837420f)

Upstream merge commit:
[`d2b9b6043135e6863eaf8b84457b2cdec71539e6`](https://github.com/juanjuandog/FinSight-AI/commit/d2b9b6043135e6863eaf8b84457b2cdec71539e6)

```bash
git clone https://github.com/juanjuandog/FinSight-AI
cd FinSight-AI
git checkout d2b9b6043135e6863eaf8b84457b2cdec71539e6
cd backend
mvn test
```

Observed verification environment:

- Apache Maven 3.9.16, binary SHA-512 verified against the Apache release checksum;
- Java 23.0.1 compiling with Maven `release 17`;
- Docker Desktop 29.6.1 available to Testcontainers;
- 18 tests discovered, 0 failures, 0 errors, 3 environment-dependent skips.

Six hasher tests verify digest stability, sensitivity to changed evidence content,
sensitivity to rerank order, a nullable publication date, a distinct encoding for null
versus empty text, and invariance to score-only changes. Each nullable value receives a
presence marker before its length-prefixed UTF-8 payload, so null cannot collide with an
empty string and no nullable field can crash hashing.

The contribution was subsequently merged upstream. The verification result above is the
recorded local Maven run; merge status is not presented as a substitute for that test evidence.

## Maintainer feedback and resolution

The maintainer agreed that the direction fits FinSight-AI's reproducibility goals and
requested three concrete corrections:

- encode nullable fields deterministically and keep null distinct from an empty string;
- add a regression test with `publishedAt = null`;
- define whether order and retrieval score are identity-bearing.

Commit `4129152` implements those corrections and documents the resolved boundary.
Order remains significant because it is sent to generation. Score is excluded for the
current path because it is not sent to generation.

The contribution is merged, but this remains an independent preflight rather than a joint
or endorsed case study. No affiliation, endorsement, or collaboration is implied.
