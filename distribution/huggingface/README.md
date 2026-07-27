---
license: cc-by-4.0
language:
  - en
  - fr
  - zh
task_categories:
  - question-answering
pretty_name: FinMirror Synthetic Paired Worlds v0.1
size_categories:
  - n<1K
tags:
  - benchmark
  - finance
  - financial-ai
  - rag
  - ai-agents
  - evaluation
  - counterfactual
  - calibration
  - provenance
  - multilingual
configs:
  - config_name: default
    data_files:
      - split: test
        path: test.jsonl
---

# FinMirror Synthetic Paired Worlds v0.1

**Change one financial fact. Did the agent change for the right reason?**

FinMirror is a deterministic paired-world benchmark for financial RAG systems and
agents. A system receives each evidence world independently. The evaluator later checks
whether its answer, citations, formula operands, confidence, and abstention changed only
when the evidence and dependency graph permit.

- **126 cases**
- **108 transformed pairs**
- **18 complete reference groups**
- **6 finance workflows**
- **English, French, and Chinese**
- **CC BY 4.0 synthetic data**
- **No personal data, real companies, or investment advice**

[Interactive zero-key demo](https://facewang753.github.io/finmirror/) ·
[Code and evaluator](https://github.com/faceWang753/finmirror) ·
[Methodology](https://github.com/faceWang753/finmirror/blob/main/docs/METHODOLOGY.md) ·
[Data card](https://github.com/faceWang753/finmirror/blob/main/docs/DATA_CARD.md)

## Why paired evaluation?

Pointwise accuracy can reward the wrong mechanism. In the bundled deterministic demo,
an evidence-blind memorizer reaches **71.4% case accuracy** but **0% strict pair
reliability**. It fails to update after material evidence changes, migrate citations to
the current world, replay formulas from grounded operands, and abstain after evidence
removal.

Those values are harness checks on a deliberately flawed offline baseline. They are not
claims about any hosted model.

## Dataset structure

Every group has one reference world and six atomic transformations:

| Transformation | Required behavior |
|---|---|
| Material value change | Recompute and migrate provenance |
| Irrelevant distractor | Preserve the answer |
| Peer-entity collision | Ignore plausible wrong-entity evidence |
| Stale-period collision | Ignore wrong-period evidence |
| Document prompt injection | Treat embedded instructions as data |
| Evidence ablation | Abstain and identify the missing evidence |

The JSONL retains the complete authored benchmark contract. Do not pass hidden gold,
pair relations, or expected evidence to the system under test. Use the FinMirror loader,
which converts every record into a stripped `PromptCase`.

```bash
git clone https://github.com/faceWang753/finmirror
cd finmirror
python -m pip install -e ".[dev]"
finmirror validate benchmark/v0.1
finmirror demo
```

To score another system, emit the documented prediction contract and run:

```bash
finmirror score \
  --predictions path/to/predictions.jsonl \
  --system "my-finance-agent" \
  --out runs/my-agent
```

## Primary metric

`strict_pair_reliability` is the primary metric. A pair passes only when all applicable
answer, citation migration, formula replay, operand provenance, confidence, abstention,
and reported retrieval checks pass.

The aggregate audit score is secondary. Serious comparisons should publish the complete
metric vector, raw predictions, evaluator version, dataset digest, model identifier,
decoding configuration, latency, cost, and at least three independent stochastic runs.

## Integrity

The FinMirror canonical dataset digest (computed from sorted, parsed case objects rather
than raw file bytes) is:

```text
3db16674c7fb5d0f9a45c41389045d001ca8ed8f2d0d55368baec8673de23009
```

See `manifest.json` for the bound case count, transforms, languages, and schema version.

## Limitations

v0.1 is small, templated, text-only, synthetic, and public. It does not establish
real-world model safety, financial intelligence, or production readiness. French and
Chinese variants share controlled semantic templates and have not been certified by
professional translators. Public cases must not be used to train a model later evaluated
on the same track.

The next research milestone is an expert-validated pilot over licence-audited public
financial sources with blinded adjudication and a predeclared stop/go criterion.

## Citation

```bibtex
@software{wang_2026_finmirror,
  author = {Mingyang (Ethan) Wang},
  title = {FinMirror: Paired-World Reliability Evaluation for Financial RAG and Agents},
  year = {2026},
  version = {0.1.0},
  url = {https://github.com/faceWang753/finmirror}
}
```
