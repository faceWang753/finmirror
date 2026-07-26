# Annotation Guide

This guide applies to future human-reviewed FinMirror cases. Synthetic v0.1 is generated
from deterministic templates but uses the same concepts.

## Roles

Each case is labeled independently by two annotators with finance-domain competence. A
third adjudicator resolves disagreements. No annotator may see a model prediction during
gold labeling.

## Required judgments

1. **Entity:** exact legal or reporting entity.
2. **Period:** fiscal period and `as_of` availability.
3. **Metric:** definition, accounting basis, and GAAP/non-GAAP status.
4. **Unit:** scale, currency, and denominator.
5. **Answerability:** whether a minimum sufficient evidence set exists.
6. **Evidence:** all minimal sufficient sets, not merely one convenient citation.
7. **Formula:** allow-listed program or reviewed typed program.
8. **Operands:** exact value, unit, period, entity, and evidence anchor.
9. **Intervention relation:** `should_change`, `should_not_change`, or `should_abstain`.
10. **Materiality:** whether the output movement exceeds declared tolerance.
11. **Harm class:** plausible consequence if wrong.

## Atomic intervention test

Reject or split a pair if more than one causal variable changed. Formatting-only changes
are permitted only in a dedicated robustness stratum. Every substantive difference must
be listed in `changed_fields`.

## Evidence rules

- Prefer first-party, authoritative evidence.
- Use stable semantic region IDs plus page/box coordinates where available.
- Capture enough context to establish entity, period, metric, and unit.
- For calculations, cite every operand.
- Record contradictions rather than silently selecting a value.
- A source published after `as_of` is invalid even if factually correct later.

## Answerability

Mark answerable only if at least one minimum sufficient evidence set supports a unique
result. Mark unanswerable if an operand, entity, period, unit, or governing definition is
missing or irreconcilably conflicting. Record the exact missing requirement.

## Review workflow

1. Annotator A labels the reference world.
2. Annotator B independently labels it.
3. Differences are measured with field-level agreement and Cohen’s κ.
4. Adjudicator creates the accepted reference.
5. An intervention author creates one transformed world.
6. Both annotators verify observability, answerability, materiality, and counterfactual
   validity without seeing system output.
7. Adjudicator approves or rejects the pair.

## Quality targets

- 100% programmatic schema and replay validity;
- ≥0.90 raw agreement for answerability and relation;
- ≥0.80 Cohen’s κ for categorical error type and materiality;
- 100% adjudication of disagreements;
- spot re-audit after rendering and before release.

Targets are release criteria, not evidence that the annotations are free from error.

