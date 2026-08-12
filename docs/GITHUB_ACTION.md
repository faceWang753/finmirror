# GitHub Actions reliability gate

FinMirror can run as a pull-request check for systems that already emit the
[prediction contract](METHODOLOGY.md#submission-contract). The action installs the exact
repository revision referenced by the workflow, scores every case, saves standalone JSON
and HTML reports, and writes the core reliability vector to the GitHub job summary.

```yaml
name: Financial AI reliability

on:
  pull_request:

permissions:
  contents: read

jobs:
  finmirror:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Produce FinMirror predictions
        run: python scripts/run_finmirror_cases.py --out predictions.jsonl
      - name: Enforce paired-world reliability
        uses: faceWang753/finmirror@v0.2.0
        with:
          predictions: predictions.jsonl
          system: my-finance-agent
          system_version: ${{ github.sha }}
      - uses: actions/upload-artifact@v6
        if: always()
        with:
          name: finmirror-report
          path: finmirror-results/
```

The scoring step exits with status `2` when the strict gate is blocked, so the pull
request check fails while `report.json`, `report.html`, and `summary.md` remain available
for diagnosis. Invalid inputs and integrity failures exit with status `1`.

The action exposes `gate`, `audit_score`, and `pair_reliability` outputs. Treat them as
synthetic regression signals, not deployment approval. Pin a release tag or full commit
SHA; do not silently follow `main` in a production workflow.
