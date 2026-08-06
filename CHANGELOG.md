# Changelog

All notable changes are documented here.

## [Unreleased]

### Added

- a hash-pinned Statistics Canada GDP calibration group with one source-derived
  reference, six visibly disclosed atomic interventions, reproducible curation code,
  exact licence/capture receipts, and no model results;
- a strict expert-review status schema and CLI gate that blocks benchmark claims until
  two independent annotations, blinded adjudication, agreement thresholds, and the
  exact dataset digest are recorded.
- a bounded expert-review packet and structured volunteer form with independence,
  conflict-disclosure, privacy, adjudication, and opt-in acknowledgement rules.
- a zero-backend blind review app that keeps drafts in browser storage, excludes gold and
  model outputs, and downloads schema-versioned JSONL bound to the exact pilot digest;
- a `validate-review` CLI and review-submission schema that reject incomplete, unblinded,
  inconsistent, unknown-field, or wrong-digest expert submissions.

### Planned

- expert-reviewed real-source pilot;
- sealed isomorphic intervention track;
- visual and agent-trajectory evaluation.

## [0.1.1] — 2026-08-04

### Added

- a reusable GitHub Actions gate that scores prediction-contract JSONL, fails blocked
  paired-world evaluations, publishes a bounded Markdown job summary, preserves
  standalone reports, and exposes gate, audit-score, and pair-reliability outputs;

- fail-closed v0.2 source-receipt schema, exact-byte hashing, drift checks, candidate
  ledger, and calibration/provenance protocol; these artifacts are infrastructure only
  and do not claim expert validation or release approval;
- a hash-bound evidence-lineage manifest and `evidence-status` gate that distinguishes
  synthetic data, provider captures, deterministic source-derived renders, and
  evaluator-authored counterfactuals; the committed state is machine-verified as
  `synthetic_only` and cannot claim a real-source pilot;
- automatic GitHub Pages deployment for the zero-key interactive demo;
- a CC BY 4.0 Hugging Face dataset release with the v0.1 manifest and JSON Schemas;
- a reproducible discovery submission to Awesome LLM Eval, currently under review;
- an independent integration-review ledger and pinned FinSight-AI reproducibility
  preflight, linked to an upstream evidence-snapshot contribution;
- five high-relevance 2026 papers on professional, trajectory, deep-research, and
  numerically aware evaluation, bringing the targeted literature scan to 47 papers;
- complete project URLs and citable author metadata for software indexes.

### Changed

- recorded Awesome Agent Evals' "not yet" review: the synthetic v0.1 release will be
  resubmitted only after an expert-validated real-source pilot exists, with authorship
  disclosed explicitly;
- updated the FinSight-AI preflight after maintainer review: nullable evidence fields
  are presence-marked, null and empty values are distinct, retrieval score is excluded
  from the current generation-context fingerprint, and the full local backend suite
  passes 18 tests with 3 infrastructure-dependent skips;
- recorded that FinSight-AI merged the evidence-snapshot contribution in upstream PR #14
  as commit `d2b9b60`, while preserving the distinction between merged infrastructure and
  an executed reliability audit.

## [0.1.0] — 2026-07-26

### Added

- 126-case deterministic synthetic benchmark with 108 paired interventions;
- English, French, and Chinese controlled worlds;
- material, distractor, entity, period, injection, and ablation relations;
- typed answers, evidence, formula programs, operands, confidence, and abstention;
- deterministic evaluator, hard gates, calibration and cross-language metrics;
- Cohere Command A+ / Rerank 4 adapter;
- oracle, non-gold evidence program, and evidence-blind negative control;
- JSONL scoring, preference export, annotation agreement, and HTML reports;
- integrity manifests, JSON Schemas, tests, research review, and release documentation.
