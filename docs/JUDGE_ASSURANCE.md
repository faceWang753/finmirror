# Judge assurance: checklist quality before aggregate reward

Learned verifiers can make evaluation and reinforcement learning scale beyond tasks with
a single executable answer. They also create two separable failure surfaces:

1. **Decomposition risk** — the checklist omits a requirement, covers it twice, or
   bundles several requirements into one judgment.
2. **Judgment risk** — the checklist is sound, but a permissive verifier assigns high
   probability to an unsatisfied item and inflates the aggregate reward.

`finmirror judge-audit` measures both surfaces without making a model call. It consumes
the verifier's item probabilities together with an evaluator-authored atomic requirement
state, and emits a replayable report with an explicit release gate.

This is a narrower engineering extension inspired by the failure modes documented in
[Soft-SVeRL](https://arxiv.org/abs/2605.28561). It is not an implementation or
reproduction of that training method, and the paper's authors are not affiliated with
FinMirror.

[Project Kaleidoscope](https://arxiv.org/abs/2607.14673) independently demonstrates a
complementary production pattern: calibrate single-metric judges against human labels
and withhold automated aggregation when none clears a local reliability gate. The
deterministic metamorphic checks here do not replace that human calibration layer.

## What the gate checks

For every scenario, the audit requires:

- exact coverage of the oracle requirement IDs;
- no duplicate checklist item IDs or overlapping coverage;
- one atomic requirement per checklist item;
- a finite satisfaction probability in `[0, 1]`;
- correct pass/fail classification at the declared `0.5` threshold;
- item-level Brier score no greater than `0.10` across the submitted run.

It then evaluates three metamorphic relations:

| Relation | Oracle change | Required judge behavior |
|---|---|---|
| `atomic_omission` | exactly one requirement changes from satisfied to unsatisfied | only the affected probability falls materially and aggregate reward decreases |
| `irrelevant_context` | no requirement state changes | probabilities and reward remain stable |
| `reorder` | only requirement order changes | per-requirement probabilities and reward remain stable |

The thresholds are declared regression gates, not universal statistical cutoffs. A real
deployment should set them using a held-out, independently annotated calibration set.

## Zero-key falsification demo

```bash
finmirror judge-demo
```

The demo evaluates the same four oracle scenarios with three deterministic controls:

- `atomic-calibrated-verifier` uses one item per requirement and lowers only the
  probability of the omitted citation requirement;
- `atomic-permissive-verifier` preserves the correct checklist but returns high
  probability for every item, isolating reward inflation;
- `collapsed-permissive-verifier` compresses all requirements into a single positive
  judgment, isolating decomposition loss as well as permissiveness.

Only the first control passes. The standalone HTML report and every machine-readable
input/output are written under `artifacts/demo/judge/` and published with the other
zero-key demos at `https://facewang753.github.io/finmirror/judge/`.

## External input contract

```json
{
  "schema_version": "1.0",
  "system_name": "my-checklist-verifier",
  "scenarios": [
    {
      "scenario_id": "reference",
      "relation": "reference",
      "reference_scenario_id": null,
      "requirements": [
        {"requirement_id": "grounded_citation", "satisfied": true}
      ],
      "checklist": [
        {
          "item_id": "citation-check",
          "covers": ["grounded_citation"],
          "probability": 0.97
        }
      ]
    }
  ]
}
```

At least one transformed scenario pointing to a reference is required. The parser is
closed-world: unknown fields, unknown relations, non-finite probabilities, missing
references, and duplicate scenario IDs fail before scoring.

```bash
finmirror judge-audit --input my-audit.json --out runs/my-judge
```

## Claim boundary and threat model

The audit checks declared atomic requirements and supplied verifier probabilities. It
does not establish that the oracle requirements are complete, that annotations are
correct, that a learned verifier is robust out of distribution, or that hidden model
reasoning is faithful. Checklist authors can game the contract by omitting a requirement
from both the oracle specification and the learned checklist; independent specification
review remains necessary.

The next research step is to add blinded human agreement over oracle decompositions,
held-out checklist paraphrases, and model-generated judgments from separately versioned
verifiers. Those results must remain distinct from the deterministic controls shipped
here.
