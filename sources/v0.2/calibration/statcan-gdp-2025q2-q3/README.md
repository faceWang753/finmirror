# Statistics Canada GDP calibration group

This directory is a **review-pending calibration artifact**, not a scored benchmark
release. It closes the technical source-lineage loop requested in external review while
keeping expert-validation claims fail-closed.

## Contents

- `source.json` — five rows deterministically extracted from the exact captured bytes;
- `reference.jsonl` — one source-derived reference world;
- `counterfactuals.jsonl` — six visibly disclosed evaluator-authored transformations;
- `review-status.json` — machine-readable proof that independent review is incomplete.

The seven cases form one complete paired group covering material value change,
irrelevant evidence, entity collision, period collision, prompt injection, and evidence
ablation. The provisional reference answer is 0.5% growth from 2025 Q2 to Q3, calculated
from 2,495,975 and 2,507,754 CAD millions. It is not expert gold.

## Reproduce

Obtain the official full-table ZIP through Statistics Canada's documented Web Data
Service, then run:

```bash
python scripts/curate_statcan_gdp_pilot.py \
  --capture 36100104-eng.zip \
  --out sources/v0.2/calibration/statcan-gdp-2025q2-q3
```

The script accepts only the reviewed 961,751-byte capture with SHA-256
`9a5e3ffe478f1ccb69724147c246818e98786adfafee6818605a298c48626dcd`.

Source acknowledgment:

> Adapted from Statistics Canada, Table 36-10-0104-01, reference date 2026-05-29.
> This does not constitute an endorsement by Statistics Canada of this product.

## Review boundary

Before any model run or benchmark submission, two independent finance-capable
annotators and one blinded adjudicator must review every case under
`docs/ANNOTATION_GUIDE.md`. The release gate requires raw agreement of at least 0.90,
Cohen's kappa of at least 0.80, and adjudication of every disagreement. Until then,
`finmirror review-status --require-expert-validated` must fail.
