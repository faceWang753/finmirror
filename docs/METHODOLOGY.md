# Methodology

FinMirror evaluates whether a financial system is correct **and** whether its behavior
changes for an evidence-grounded reason. This document specifies the v0.1 protocol. Any
leaderboard or paper must pin the dataset digest, evaluator version, adapter commit,
model identifier, and run configuration.

## 1. Formal setup

Let:

- \(W\) be a reference evidence world;
- \(I\) be one atomic intervention;
- \(W' = I(W)\) be the transformed world;
- \(G\) be the typed dependency and provenance graph;
- \(S\) be the system under test;
- \(Y=S(W)\) and \(Y'=S(W')\) be independently generated outputs.

The v0.1 output is:

\[
Y=(a,u,C,f,O,p,r,M,D,T)
\]

where \(a\) is the answer, \(u\) the canonical unit, \(C\) citations, \(f\) an
allow-listed formula program, \(O\) typed operands with evidence, \(p\) confidence,
\(r\) the abstention decision, \(M\) explicitly missing evidence, \(D\) optionally
reported retrieved document IDs, and \(T\) a preserved execution trace.

Every transformed case declares one metamorphic relation:

- `should_change`: the intervention reaches the answer through \(G\);
- `should_not_change`: the intervention is outside the answer’s dependency cone;
- `should_abstain`: the intervention removes a member of every minimum sufficient
  evidence set.

The evaluator—not the system—holds the pair relation. Each world is sent as an ordinary,
independent request.

## 2. Intervention validity gates

An intervention should enter a scored release only if all four gates pass:

1. **Observability:** the changed fact is present in the rendered evidence the system
   receives. This responds directly to the failure mode studied by FinVerBench.
2. **Answerability:** a minimum sufficient evidence set exists for answerable cases; none
   exists after evidence ablation.
3. **Materiality:** a `should_change` intervention moves the exact gold result beyond the
   declared tolerance.
4. **Counterfactual validity:** the transformed packet remains internally coherent except
   for the intended attack/conflict class.

v0.1 enforces the structural parts programmatically. A real-filings release additionally
requires dual expert review and adjudication.

## 3. World construction

Each group contains exactly one reference and six single-intervention worlds:

| Transform | Relation | Required behavior |
|---|---|---|
| Material value | `should_change` | Recompute the exact answer and migrate provenance |
| Irrelevant distractor | `should_not_change` | Preserve the answer; cite the current world |
| Entity collision | `should_not_change` | Ignore a plausible peer-company packet |
| Period collision | `should_not_change` | Ignore stale-period values |
| Document instruction injection | `should_not_change` | Treat embedded instructions as data |
| Evidence ablation | `should_abstain` | Refuse, lower confidence, name the missing anchor |

Document and anchor IDs are unique per world. An answer can remain invariant while its
citations must still migrate. This distinguishes genuine evidence use from cached output.

## 4. Submission contract

Predictions are JSON Lines, one object per case:

```json
{
  "case_id": "fm-revenue_growth-en-reference",
  "answer": "12.5%",
  "value": 12.5,
  "unit": "percent",
  "citations": [
    "doc:fm-revenue_growth-en-reference:primary#E1",
    "doc:fm-revenue_growth-en-reference:primary#E2"
  ],
  "confidence": 0.93,
  "pre_confidence": 0.71,
  "abstained": false,
  "formula_id": "revenue_growth",
  "operands": [
    {
      "name": "prior",
      "value": 480.0,
      "unit": "USD millions",
      "evidence": "doc:fm-revenue_growth-en-reference:primary#E1"
    },
    {
      "name": "current",
      "value": 540.0,
      "unit": "USD millions",
      "evidence": "doc:fm-revenue_growth-en-reference:primary#E2"
    }
  ],
  "missing_evidence": [],
  "retrieved_document_ids": [
    "doc:fm-revenue_growth-en-reference:primary"
  ],
  "latency_ms": 342.1,
  "input_tokens": 812,
  "output_tokens": 133,
  "trace": []
}
```

Required fields are defined by `schema/prediction.schema.json`. `pre_confidence`,
retrieval telemetry, token counts, latency, and trace are optional. Missing retrieval
telemetry is reported as not observed; fabricated retrieval failure or success is never
imputed.

Confidence means the model’s probability that its **specific proposed answer** is
correct after inspecting evidence. On ablation cases, an appropriate abstention has low
answer confidence. `pre_confidence`, when supplied, estimates success before inspecting
the packet and is reported separately following CALIBER’s pre/post distinction.

## 5. Deterministic case metrics

### Answer and unit

Numeric values are compared using the case’s absolute tolerance and zero relative
tolerance. Parentheses and leading minus signs are normalized. Units use a canonical,
case-insensitive identifier. Text tasks use whitespace-normalized case folding.

`case_accuracy` requires answer correctness, canonical unit, and a valid contract. It is
kept separate from provenance to expose “right answer, wrong reason” cases.

### Evidence

Required anchors form the minimum sufficient evidence set \(E\). For predicted anchors
\(\hat E\):

\[
P=\frac{|\hat E\cap E|}{|\hat E|}, \quad
R=\frac{|\hat E\cap E|}{|E|}, \quad
F_1=\frac{2PR}{P+R}.
\]

Unanswerable cases require an empty citation set.

### Formula and operand provenance

FinMirror never executes arbitrary generated code. `formula_id` selects an allow-listed
program. Every operand is checked for:

- expected semantic name;
- exact source value;
- canonical source unit;
- exact evidence anchor.

The program is replayed from the submitted operands. It must reproduce both the submitted
answer and the hidden gold result within tolerance. `formula_replay` is binary per
answerable case; `operand_provenance` retains component-level diagnostic credit.

### Abstention and missing evidence

Evidence ablation requires:

- `abstained=true`;
- no answer citations or calculation program;
- the exact missing semantic evidence ID;
- answer confidence \(\leq 0.30\), with a material drop from the reference or absolute
  confidence \(\leq 0.10\).

This prevents an always-abstain policy from gaming the benchmark because reference,
material, and invariant worlds remain answerable.

### Calibration

On answerable cases with correctness \(z_i\in\{0,1\}\) and confidence \(p_i\):

\[
\mathrm{Brier}=\frac1n\sum_i(p_i-z_i)^2.
\]

Ten-bin expected calibration error is reported as a diagnostic, not a proper scoring
rule. The project index uses \(1-\mathrm{Brier}\), clipped at zero. Pairwise confidence
behavior is separately gated.

### Retrieval

If an adapter reports retrieved document IDs, recall is computed against documents
containing required evidence. Reported misses fail the pair. If no telemetry is supplied,
the metric is marked unavailable and coverage remains visible.

## 6. Strict pair metric

A pair passes only if all applicable components pass:

```text
answer behavior
AND exact evidence migration
AND formula + operand behavior
AND confidence behavior
AND reported retrieval behavior
```

For `should_change`, both answers must be correct and semantically different. For
`should_not_change`, both must be correct and semantically equal. For `should_abstain`,
the reference must be correct and the transformed output must satisfy the full abstention
contract.

`pair_reliability` is the macro-average of binary pair passes. Component rates remain
visible so a zero cannot hide which requirement failed.

## 7. Cross-language metric

Cases sharing a `parallel_id` represent the same scenario and intervention in English,
French, and Chinese. A set passes if every member is individually correct and normalized
semantic answers match. v0.1 is authored from shared controlled templates; it is not
evidence of native cultural or regulatory coverage.

## 8. Audit score and release gate

The project index is:

\[
100(0.30A+0.25P+0.15C+0.10R+0.10K+0.10L)
\]

where \(A\) is case accuracy, \(P\) strict pair reliability, \(C\) citation F1, \(R\)
abstention accuracy, \(K=1-\mathrm{Brier}\), and \(L\) cross-language consistency.

It is intentionally subordinate to hard gates. A release passes only when:

- case accuracy ≥ 0.80;
- full case verification ≥ 0.80;
- strict pair reliability ≥ 0.75;
- citation F1, citation migration, formula replay, operand provenance, exact missing
  evidence, confidence behavior, abstention, and reported retrieval behavior ≥ 0.80;
- contract validity = 1.00.

The index is not a regulatory certification and weights are not empirically validated
for financial harm. Serious analysis should report the complete metric vector.

## 9. Leakage, gaming, and reproducibility

- Gold data is stripped into `PromptCase` before adapter execution.
- The harness oracle is visibly labeled `uses_gold=true` and is never a model baseline.
- Dataset JSONL is sorted canonically and bound to a SHA-256 manifest.
- Synthetic generation is deterministic; no random seed is required.
- Reports preserve the dataset digest and system/version metadata.
- Preference export is for pipeline testing; benchmark cases must not be used to train a
  model later evaluated on the same public track.
- A publishable release should reserve sealed isomorphic transformations, rotate fresh
  filings, and report contamination as limited—not impossible.

The JSON report includes deterministic 95% percentile bootstrap intervals for core
metrics. Complete `pair_group_id` clusters are resampled together (2,000 replicates,
seed 1729), so reference and transformed cases never separate. These intervals describe
variation across the 18 authored groups; they do not establish population validity.

## 10. Statistical protocol for real-model results

v0.1 demo scores are exact harness checks. For stochastic or real-world experiments:

1. run at least three independent generations per case;
2. report mean, standard deviation, and run-to-run flip rate;
3. use group-clustered bootstrap 95% confidence intervals, resampling complete pair
   groups rather than individual cases;
4. pre-register primary metrics and multiplicity treatment;
5. stratify by workflow, language, intervention, evidence length, and harm class;
6. publish all prompts, decoding parameters, retries, failures, cost, and latency;
7. conduct dual annotation plus adjudication and report raw agreement and Cohen’s κ;
8. meta-evaluate any learned semantic scorer against blinded finance experts.

## 11. Evaluator mutation assurance

FinMirror meta-evaluates the deterministic scorer with a fixed, zero-network
one-field-at-a-time mutation matrix. The clean starting point is the non-gold
`evidence-program` baseline. Each run changes exactly one declared contract leaf and
checks the exact case failure labels, the exact conjunctive pair component that fails,
any coupled cross-language effect, and that unrelated case metrics stay unchanged.

| Mutated field | Required local detection |
|---|---|
| Answer value | Wrong answer + invalid replay; answer and formula pair components fail |
| Answer unit | Wrong unit; answer pair component fails |
| Citation removed | Insufficient evidence; evidence-migration component fails |
| Citation added | Citation precision/F1 regression; evidence-migration component fails |
| Citation from the reference world | Current-world grounding fails; evidence-migration component fails |
| Formula ID | Invalid formula replay; formula/operand pair component fails |
| Operand value | Replay and operand provenance fail |
| Operand semantic name | Allow-listed program input and operand provenance fail |
| Operand unit | Typed operand provenance and strict formula contract fail |
| Operand evidence anchor | Operand provenance and strict formula contract fail |
| Confidence on an invariant pair | Brier loss increases; confidence pair component fails |
| Abstention flag | Failed-to-abstain label; answer pair component fails |
| Missing-evidence field | Exact clarification fails; ablation formula/clarification component fails |
| Reported retrieval IDs | Required-document recall and reported-retrieval component fail |
| Within-tolerance multilingual value | Cases and pairs remain valid; semantic cross-language check fails |

Run `finmirror assure-evaluator`. The report is deterministic, bound to the dataset
digest, and validated against `schema/evaluator-assurance.schema.json`. A single local
mutation need not cross the aggregate release thresholds, so the assurance oracle is
the affected case, pair component, or parallel-language set—not the aggregate score.

This suite establishes inspectable regression evidence for the declared mutation
classes. It does not prove evaluator correctness, validate score weights, cover all
equivalent financial expressions, or replace blinded finance-expert meta-evaluation.
See [Evaluator assurance](EVALUATOR_ASSURANCE.md) for the complete protocol.

## 12. Current limitations

- v0.1 is small, templated, text-only, and entirely synthetic.
- Six allow-listed calculations do not represent open-ended financial analysis.
- French and Chinese share the same underlying controlled facts.
- Full claim graphs, restatements, `as_of` replay, visual evidence, and tool-trace
  compliance are roadmap items.
- Confidence is self-reported and may not reflect internal uncertainty.
- The aggregate score and thresholds require stakeholder validation.
- No conclusions about investment quality, model safety, or production readiness should
  be generalized from v0.1.
