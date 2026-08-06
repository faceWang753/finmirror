# Contributing

FinMirror welcomes small, auditable contributions. Precision matters more than volume.

## Development

```bash
python -m venv .venv
# Activate the environment, then:
python -m pip install -e ".[dev]"
finmirror generate
python -m pytest
ruff check .
ruff format --check .
mypy
python -m build
```

Do not commit API keys, private filings, paid data, model outputs containing confidential
information, or copied content without verified redistribution rights.

## Good first contributions

- an adapter that implements the normalized prediction contract;
- a regression test for an evaluator edge case;
- an allow-listed financial program plus adversarial tests;
- a documentation correction with primary evidence;
- an atomic paired-world proposal using authored synthetic data.

## Adding a benchmark group

A contribution must contain exactly one reference and balanced transformed worlds. In the
pull request, document:

- intended finance workflow and stakeholder;
- exact dependency graph;
- minimum sufficient evidence;
- formula and operand provenance;
- intervention and expected relation;
- observability, answerability, materiality, and validity checks;
- source and licence for every non-authored element;
- native-language reviewer when applicable.

Avoid compound interventions. Do not change the entity, period, metric, and value in one
pair.

## Pull-request requirements

- tests cover success, failure, and tamper paths;
- no hidden network calls or telemetry;
- all generated files are reproducible;
- public APIs remain typed and documented;
- claims distinguish preprints from peer-reviewed work;
- results identify oracle/gold access and synthetic scope;
- changelog entry for user-visible behavior.

Maintainers may reject technically correct contributions that weaken interpretability,
licensing, or benchmark validity.

## Research contributions

Open an issue before large dataset work. Include a short protocol, proposed sources and
licences, annotation expertise, evaluation plan, and stop/go criterion. Training data and
sealed benchmark data must remain disjoint.

## Expert review contributions

The Statistics Canada calibration group is seeking two independent finance-capable
annotators and one blinded adjudicator. Read `docs/EXPERT_REVIEW_PACKET.md` before
volunteering through the expert review issue form. The account-free review app at
`https://facewang753.github.io/finmirror/review/` stores drafts only in the browser and
exports JSONL that must pass `finmirror validate-review`. Reviewers must keep model
outputs and other reviewers' labels hidden, disclose conflicts or prior gold exposure,
and record uncertainty rather than forcing agreement. Public acknowledgement is opt-in;
review participation never implies endorsement.

## Reporting problems

Use a public issue for ordinary bugs or benchmark errors. Follow `SECURITY.md` for
vulnerabilities or accidental data exposure. Corrections are documented; benchmark
errors are never silently rewritten.
