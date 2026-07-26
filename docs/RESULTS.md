# Reproducible Offline Results

Generated with the committed synthetic v0.1 dataset and zero external API calls.

```bash
finmirror generate
finmirror demo
```

Dataset SHA-256:

```text
3db16674c7fb5d0f9a45c41389045d001ca8ed8f2d0d55368baec8673de23009
```

## Results

| Metric | Harness oracle | Evidence program | Evidence-blind memorizer |
|---|---:|---:|---:|
| Audit score | 100.0 | 100.0 | 49.5 |
| Hard gate | Pass | Pass | Blocked |
| Case accuracy | 100.0% | 100.0% | 71.4% |
| Full case verification | 100.0% | 100.0% | 0.0% |
| Strict pair reliability | 100.0% | 100.0% | 0.0% |
| Citation F1 | 100.0% | 100.0% | 83.3% |
| Formula replay | 100.0% | 100.0% | 0.0% |
| Operand provenance | 100.0% | 100.0% | 0.0% |
| Missing-evidence identification | 100.0% | 100.0% | 0.0% |
| Material sensitivity | 100.0% | 100.0% | 0.0% |
| Distractor invariance, strict tuple | 100.0% | 100.0% | 0.0% |
| Evidence ablation | 100.0% | 100.0% | 0.0% |

Scores shown to one decimal are rounded. The raw oracle and evidence-program audit
indices are 99.999 and 99.996 because their non-degenerate confidence values produce a
small Brier penalty.

The report also contains deterministic 95% pair-group bootstrap intervals (2,000
replicates). Every authored group has the same control pattern, so the memorizer's case
accuracy interval collapses to 71.4% and its strict pair-reliability interval to 0.0%.
This is descriptive consistency across synthetic templates, not population uncertainty.

## Interpretation

- The oracle validates evaluator plumbing and is not a model result.
- The evidence program receives only the public prompt view and validates that a
  non-gold system can satisfy the complete contract.
- The memorizer gets most pointwise cases right because four invariant worlds preserve
  the reference value. It fails every **strict** pair because it supplies no verifiable
  formula or operands; it also fails material changes, ablations, and peer evidence.
- Strict distractor-invariance includes current-world evidence migration and calculation
  provenance. Answer-only invariance for the memorizer is reported separately as
  `pair_answer_behavior`.

## What these results do not show

They do not compare language models, validate real filings, demonstrate investment
performance, or establish production safety. Hosted Cohere results require a user API
key and must be reported with model version, date, decoding, retries, costs, and the
unaltered result files.
