# Evaluator assurance

FinMirror's deterministic core can still be wrong. This protocol tests a narrower and
auditable question: when one declared prediction field is corrupted, does the evaluator
attribute the resulting defect to the exact case, pair, and language component that the
public scoring contract specifies?

## Reproduce

```bash
python -m pip install -e "[dev]"
finmirror assure-evaluator \
  --dataset benchmark/v0.1 \
  --out artifacts/evaluator-assurance.json
```

The command makes no network calls and uses no LLM judge. It starts from the
`evidence-program` baseline, which reads the public evidence packet without receiving
hidden gold. The committed report is byte-reproducible for the same code and dataset
digest.

## Assurance contract

For every mutation, the runner verifies all of the following:

1. exactly one declared contract leaf changed;
2. observed case failure labels equal the expected labels—extra labels fail the check;
3. changed case metrics equal the declared set and move in the expected direction;
4. unrelated case metrics remain unchanged;
5. observed failed pair components equal the expected components;
6. the clean local pair passes before mutation;
7. the mutated pair passes or fails exactly as declared;
8. the parallel-language effect matches the declaration.

The 15 mutation classes cover answer value and unit; removed, surplus, and wrong-world
citations; formula ID; operand value, semantic name, unit, and evidence anchor;
confidence drift on an invariant pair; abstention; missing-evidence identification;
reported retrieval; and a within-tolerance numeric change designed to isolate the
cross-language semantic check.

The last case matters: both the case verifier and strict pair remain valid, but the
English/French/Chinese semantic keys diverge. Conversely, answer, unit, or abstention
failures legitimately also break their parallel-language set. These coupled effects are
declared rather than treated as scorer noise.

## Why local gates are the oracle

The public release gate aggregates 126 cases and 108 pairs. One deliberately corrupted
prediction may be detected correctly without moving an aggregate rate below its release
threshold. The assurance runner therefore evaluates the affected `CaseResult`,
`PairResult`, and parallel-language set directly. It never treats an unchanged aggregate
pass/fail bit as evidence that a mutation escaped detection.

## Research alignment

The protocol follows a conservative lesson from current agent-evaluation work: final
task success alone is too coarse for failure attribution. AgentRx localizes critical
trajectory steps with constraint-validation logs; AgenticRAGTracer adds hop-aware
diagnosis; Agentic CLEAR evaluates at multiple levels; and the 2026 agent-evaluation
survey highlights fine-grained, scalable, cost-, safety-, and robustness-aware
evaluation as open needs. FinMirror applies only the deterministic, fully specified
part of that lesson to its current closed-form finance contract:

- [AgentRx](https://arxiv.org/abs/2602.02475)
- [AgenticRAGTracer](https://aclanthology.org/2026.findings-acl.66/)
- [Agentic CLEAR](https://aclanthology.org/2026.acl-demo.74/)
- [A Survey on Evaluation of LLM-based Agents](https://aclanthology.org/2026.findings-acl.1330/)

FinMirror does not infer hidden reasoning quality, localize arbitrary agent failures, or
claim coverage of open-ended trajectories from these mutation checks.

## Claim boundary and next validation layers

Passing means the declared one-field regression matrix is detected exactly. The dual
[positive equivalence suite](EQUIVALENCE_ASSURANCE.md) now checks ten representation-
invariance classes and rejects a deliberately brittle raw-equality control. Neither
suite means the evaluator is formally verified or production-valid. Remaining layers
include:

- finance-expert specification of scale, currency, rounding, locale, and equivalent-
  formula classes beyond the current contract-level allow-list;
- scorer property tests across generated edge cases;
- mutation coverage beyond the current public contract;
- blinded finance-expert review and scorer–expert disagreement analysis;
- stateful tool and trajectory evaluation only after a real replayable environment
  exists.
