# Research Roadmap

FinMirror v0.1 is a protocol and software release. The goal of the roadmap is to decide,
with evidence, whether the idea deserves a benchmark paper and sustained open-source
program. Dates should be set only after maintainers and reviewers are available.

## Research questions

1. How often does pointwise financial accuracy hide behavior that fails paired causal or
   provenance constraints?
2. Which interventions expose failures not predicted by ordinary citation and
   groundedness scores?
3. Does pairwise confidence delta better identify evidence failures than standalone
   verbalized confidence?
4. Can deterministic finance programs and operand provenance reduce dependence on LLM
   judges without making coverage trivial?
5. Do paired verifier rewards improve grounded behavior, or merely teach public
   transformations?

## Phase 0 — Protocol proof (shipped in v0.1)

Deliverables:

- typed case and prediction contracts;
- deterministic generator, integrity manifest, verifier, CLI, and local reports;
- six calculation programs and six intervention families;
- English, French, and Chinese controlled variants;
- oracle, non-gold evidence program, evidence-blind negative control;
- Cohere adapter, reward export, annotation agreement utilities;
- tests and explicit limitations.

Stop/go:

- **Go** if all deterministic checks pass and a negative control exposes a material gap
  between case accuracy and strict pair reliability.
- **Stop** if the pair protocol can be passed without reading current-world evidence.

## Phase 1 — Expert pilot

Target: 50–100 complete reference groups across two source families.

Candidate sources:

- Statistics Canada English/French material under its open licence;
- Eurostat data with record-level reuse verification;
- EDINET or CVM shards separated by their applicable licences;
- SEC fetch manifests rather than assumed redistribution of issuer-authored filings.

Required work:

- license ledger with SPDX identifier, source URL, terms URL, retrieval time, and hash;
- dual finance annotation plus adjudication;
- native-language review;
- observable rendering check;
- real rounding, units, fiscal periods, GAAP/non-GAAP, and restatement cases;
- at least five model/system families and three stochastic runs.

Stop/go:

- ≥0.80 κ on relation and answerability;
- ≥0.90 deterministic replay coverage for numeric tasks;
- pair metrics reveal statistically meaningful failures beyond pointwise metrics;
- no unresolved redistribution or privacy issue.

If those conditions fail, publish the negative result and keep FinMirror as a testing
library rather than claiming a benchmark contribution.

## Phase 2 — FilingProof engine

Build a separate data/reference-system layer:

- source fetcher with content-addressed snapshots;
- XBRL fact and taxonomy relationship extraction;
- typed entity–metric–period–unit graph;
- restatement and amendment timeline;
- formula program compiler;
- stable page/region/anchor IDs;
- side-by-side world and provenance visualization.

The engine must be replaceable: FinMirror remains provider-neutral and source-neutral.

## Phase 3 — Real agent track

Add:

- multi-document and long-context tasks;
- search, fetch, XBRL, calculator, and spreadsheet tools;
- trace replay and allowed-tool-state transitions;
- failure injection: timeouts, stale cache, permission denial, duplicate results;
- `as_of` leakage checks;
- explicit tool/cost/latency budgets;
- prompt injection and source-authority attacks.

Primary metric candidate: **Pairwise Licensed Change F1**, decomposed into answer
sensitivity, irrelevant specificity, evidence migration, formula/operand replay,
confidence/abstention, and trace compliance.

## Phase 4 — Contamination-limited benchmark

- public frozen development track;
- rotating sealed test groups;
- post-cutoff or newly amended source material;
- model-knowledge filtering;
- unpublished isomorphic transformations;
- signed evaluation containers;
- group-clustered bootstrap confidence intervals;
- public incident and correction log.

Use “contamination-limited,” never “contamination-free.”

## Phase 5 — Training research

Study deterministic reward vectors with strict separation between train and benchmark:

- supervised structured-output training;
- DPO on chosen/rejected evidence behavior;
- RLVR with pairwise hard gates;
- held-out formula isomorphisms and intervention families;
- reward-hacking audit inspired by isomorphic perturbation testing;
- calibration objectives inspired by CALIBER;
- soft checklist rewards inspired by Soft-SVeRL, bounded by deterministic gates.

Negative or null findings are publishable if the protocol is pre-registered.

## Evaluation matrix

Every serious result should stratify:

| Axis | Minimum strata |
|---|---|
| System | long-context, retrieval, reranked RAG, tool agent, deterministic reference |
| Source | filing, statistical release, annual report, structured facts |
| Relation | material, irrelevant, ablation, conflict |
| Language | source language × question language × answer language |
| Modality | text, table, visual page |
| Time | current, stale, amended/restated, strict `as_of` |
| Budget | latency and tool-call tiers |
| Risk | analyst, audit, compliance stakeholder |

## Paper package

A submission is not ready without:

- public protocol and development split;
- sealed or access-controlled test procedure;
- finance-expert annotation study;
- competitive baselines and ablations;
- scorer meta-evaluation;
- error taxonomy with blinded examples;
- complete cost and latency accounting;
- license/provenance appendix;
- limitations and stakeholder impact analysis;
- artifact reproducibility badge checklist.

