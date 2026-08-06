# Expert Review Packet: Statistics Canada Calibration Group

## Purpose

FinMirror needs independent evidence that its real-source cases are answerable, faithful
to the source, financially meaningful, and atomically transformed. This packet covers
one seven-case calibration group. It is intentionally small enough to reject or revise
before the project scales.

The current gold is machine-derived and provisional. Reviewers are validating the data
and evaluator contract, not endorsing FinMirror, Statistics Canada, a model, or an
investment conclusion.

## Roles and independence

- Two finance-capable annotators label the packet independently.
- A third reviewer adjudicates only after both independent submissions are frozen.
- Model predictions, scores, and other reviewers' labels remain hidden during initial
  annotation.
- Prior access to gold or conflicts must be disclosed. A conflicted reviewer may still
  provide methodology feedback but is excluded from agreement claims.

Reviewers should not submit identity documents, confidential employer information,
client data, or private credentials. Public acknowledgement is optional and requires
explicit permission.

## Materials

1. `sources/v0.2/calibration/statcan-gdp-2025q2-q3/source.json`
2. `sources/v0.2/calibration/statcan-gdp-2025q2-q3/reference.jsonl`
3. `sources/v0.2/calibration/statcan-gdp-2025q2-q3/counterfactuals.jsonl`
4. `sources/v0.2/calibration/statcan-gdp-2025q2-q3/review-status.json`
5. `docs/ANNOTATION_GUIDE.md`
6. `docs/PROVENANCE_LEDGER.md`

The provider capture is not committed. Its exact byte count and SHA-256 are public, and
the deterministic curator accepts only that reviewed capture.

## Required judgments

For each case, record:

- correct entity, reference periods, metric definition, price basis, seasonal basis,
  unit, and `as_of` date;
- answerability and every minimum sufficient evidence anchor;
- formula, operands, calculated value, tolerance, and display rounding;
- expected relation to the reference: `reference`, `should_change`,
  `should_not_change`, or `should_abstain`;
- whether the changed field is observable, atomic, and materially relevant;
- any licensing, attribution, ambiguity, or harm concern.

Do not copy the provisional answer without recomputing it from the cited operands.

## Submission format

The fastest route is the
[browser-only blind review app](https://facewang753.github.io/finmirror/review/). It has
no account, backend, analytics, or form submission; browser storage holds the draft and
the final action downloads JSONL. The app contains source evidence but omits provisional
gold, relationships, predictions, and scores.

Submit JSONL with one object per `case_id`. Each row binds the pilot, reviewer role,
blinding statement, conflict disclosure, timestamp, and exact dataset SHA-256. The
judgment fields include:

```json
{"case_id":"...","answerable":"yes","relation":"should_not_change","material":"no","evidence_complete":"yes","formula_correct":"yes","evidence_anchors":["...#E1","...#E2"],"computed_value":"0.47%","notes":""}
```

Use `uncertain` rather than guessing. The repository's `finmirror agreement` command
computes raw agreement and Cohen's kappa after both files are frozen.

Validate a downloaded file before sharing it:

```bash
finmirror validate-review --submission reviewer-alpha.jsonl
```

The validator rejects missing cases, duplicate IDs, changed metadata, unknown fields,
unblinded independent reviews, and submissions bound to another pilot digest.

## Release decision

The pilot remains blocked unless all conditions hold:

- two independent reviews and one adjudication are complete;
- raw agreement is at least 0.90 and Cohen's kappa is at least 0.80 for declared
  categorical fields;
- every disagreement is adjudicated;
- the review record binds the exact seven-case dataset digest;
- no unresolved source, licensing, attribution, or validity defect remains.

If the thresholds fail, the result is recorded and the pilot is revised or stopped. The
project will not relabel disagreement as consensus or run models first and tune gold to
their outputs.

## Volunteer

Use the [expert review issue form](https://github.com/faceWang753/finmirror/issues/new?template=expert_review.yml).
Opening the form expresses interest only; it does not publish credentials beyond what
the volunteer chooses to write.
