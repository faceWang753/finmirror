# Rerank assurance: sufficient evidence before harmful passages

FinMirror's answer evaluator starts after evidence has reached an agent. The retrieval
assurance lane isolates the preceding boundary: does a ranker surface the complete
minimum evidence set before a stale, wrong-entity, injected, or otherwise harmful
passage?

This matters because high topical relevance is not the same as downstream utility. The
2025 ACL paper [*The Distracting Effect*](https://aclanthology.org/2025.acl-long.892/)
studies irrelevant passages that actively degrade RAG answers, while the 2026 EACL paper
[*Redefining Retrieval Evaluation in the Era of
LLMs*](https://aclanthology.org/2026.eacl-long.391/) argues that classical rank metrics
omit negative passage utility. The 2026 ACL paper [*Are LLMs Reliable
Rankers?*](https://aclanthology.org/2026.acl-long.413/) separately demonstrates
naturalistic rank manipulation. FinMirror does not reproduce those experiments. It
turns the narrower failure surface into a deterministic regression contract.

## Packet construction

`build_retrieval_cases()` converts the existing 126 evidence worlds into anchor-level
candidate pools. The ranker sees only case ID, language, query, and candidate ID/title/
text. Hidden audit labels never enter the public packet.

Required evidence anchors receive positive utility. Wrong-entity documents and `D*`,
`P*`, or `X*` anchors are marked harmful. Other passages are neutral. The evaluator
rejects partial rankings, duplicate IDs, unknown IDs, non-finite scores, and scores that
contradict the reported order.

## Metrics and hard gate

- **Full evidence coverage:** every required anchor appears inside the evaluated prefix.
- **Sufficient evidence rank:** the position at which the final required anchor appears.
- **Harmful exposure@k:** the fraction of the prefix labelled as harmful.
- **Clean completion:** all required anchors arrive before any harmful passage.
- **Paired reliability:** clean completion holds in reference and transformed worlds.

The evaluated prefix is `max(top_k, required_anchor_count)`, bounded by pool size. The
public hard gate requires 100% clean completion and 100% paired reliability. A gold-aware
oracle is included only to test the harness and is structurally barred from passing the
public gate. An input-order control is designed to fail on entity-collision cases.

Evidence-ablation worlds are reported as unanswerable, but excluded from the ranker
gate: a reranker can reveal that required evidence is absent, while the downstream
system—not the ranker alone—must decide to abstain.

## Zero-key reproduction

```bash
python -m finmirror.cli retrieval-demo \
  --dataset benchmark/v0.1 \
  --out artifacts/demo/retrieval
```

The command writes a non-leaky `packet.jsonl`, complete ranking predictions, JSON
reports, and a static comparison page. To audit another ranker, return a complete
permutation for each case:

```json
{"case_id":"...","ranked_candidate_ids":["doc:...#E1","doc:...#E2"],"scores":[0.91,0.76]}
```

Then run:

```bash
python -m finmirror.cli retrieval-audit \
  --dataset benchmark/v0.1 \
  --predictions rankings.jsonl \
  --system "my-reranker" \
  --out runs/retrieval-audit
```

For Cohere Rerank, `finmirror.adapters.cohere_retrieval.CohereRetrievalRanker`
provides a thin production adapter. It sends only the public query, title, and
passage text to the provider; hidden utility and pair labels remain inside the
evaluator. The adapter always requests every candidate and fails closed on
partial, duplicate, or invalid result indices. Its contract is covered by
offline fake-client tests, so the repository test suite makes no paid API calls.

## Cohere boundary

Cohere publicly positions [Rerank 4](https://cohere.com/blog/rerank-4) for enterprise
search, RAG, and agent workflows, and its current Search role describes retrieval
datasets and evaluation pipelines. That makes this audit interoperable with a Cohere
Rerank adapter, but the repository does not claim Cohere review, endorsement, or model
performance. No real Rerank score should be published without the exact model ID, run
date, packet digest, parameters, complete ranking JSONL, and cost/latency disclosure.

## Limitations

- Synthetic anchor-level passages do not estimate production search quality.
- Utility labels are authored contracts, not human relevance judgments.
- The dataset is intentionally small and finance-specific.
- Passage splitting removes layout, OCR, chunking, and retriever-recall failure modes.
- A model comparison still needs repeated real runs and uncertainty analysis.
