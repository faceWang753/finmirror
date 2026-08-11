# Positive equivalence assurance

FinMirror's negative mutation matrix checks sensitivity: a harmful change must lower the
right score. This protocol checks the dual requirement, specificity: a declared
representation-only change must preserve every evaluator verdict. An evaluator that
passes only one direction can still be either under-strict or brittle.

## Reproduce

```bash
python -m pip install -e ".[dev]"
finmirror assure-equivalence \
  --dataset benchmark/v0.1 \
  --out artifacts/demo/equivalence
```

The command performs no network or model calls. It writes a digest-bound JSON report and
a standalone HTML assurance card. CI regenerates both files on Python 3.10, 3.11, and
3.12 and fails on any byte-level artifact drift.

## Declared relations

The v1 matrix contains ten contract-level equivalence classes:

| Relation | Why the score must stay fixed |
|---|---|
| Citation permutation | Evidence is a set; its serialized order has no meaning |
| Citation idempotence | Repeating an existing anchor adds no evidence |
| Operand permutation | Named formula operands retain the same bindings |
| Answer surrounding whitespace | Display padding is not financial content |
| Numeric string encoding | A number and its comma-aware decimal string denote the same value |
| Answer-unit letter case | Canonical unit comparison is case-insensitive |
| Operand-unit letter case | Quantity and provenance stay fixed when label case changes |
| Retrieval idempotence | Repeating a document ID does not retrieve another document |
| Missing-requirement idempotence | Repeating one missing requirement does not add a requirement |
| Irrelevant telemetry | Latency, token counts, and metadata do not determine answer quality |

For each relation, the runner applies the transformation to every eligible prediction,
then requires all of the following:

1. every eligible fixture actually changes and only declared top-level fields change;
2. every case scoring signature remains identical;
3. every canonical semantic prediction key remains identical;
4. every affected paired-world result remains identical, not merely passing;
5. every affected English/French/Chinese consistency result remains identical;
6. a deliberately brittle raw-contract equality control rejects the transformed values.

The committed v1 artifact evaluates 10 relations with 3,426 semantic assertions over
126 cases, 108 paired interventions, and 42 parallel-language groups. The raw-equality
control rejects all ten relations, proving that the suite is exercising changed inputs
rather than unchanged fixtures.

## Why this design follows current evidence

[LGMT](https://arxiv.org/abs/2605.23965) shows that static correctness can miss defects
exposed by semantically invariant transformations. [All Prompts Are Created
Equal?](https://aclanthology.org/2026.findings-acl.1929/) identifies an
accuracy–robustness gap across semantically equivalent judge prompts.
[MM-JudgeBias](https://aclanthology.org/2026.acl-long.1162/) separately measures
sensitivity to meaningful changes and stability under irrelevant ones, while
[J4R](https://aclanthology.org/2026.acl-long.67/) targets positional robustness in
reasoning judges. FinMirror does not reproduce those studies; it implements the narrow,
deterministic lesson that evaluator sensitivity and invariance must be tested separately.

## Claim boundary

The relation list is an allow-list, not a universal definition of financial equivalence.
Passing does not establish equivalence for scale conversions, formula rewrites, rounding
policies, currencies, periods, locale-specific formats, or open-ended prose. Those
relations need finance-expert specification and adversarial tests before they enter a
versioned metric contract. This suite is regression evidence, not formal verification,
expert validation, or production certification.

