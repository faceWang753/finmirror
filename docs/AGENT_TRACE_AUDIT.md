# Replayable agent-trace audit

## Question

An agent can return the right number while its observable evidence path is absent,
stale, or inconsistent with its citations. FinMirror v0.2 therefore asks a narrower
question than “did the model reason correctly?”:

> Is the submitted trajectory replay-consistent with the exact documents in this
> evidence world, and does the final decision use only that verified path?

The audit is deterministic and judge-free. It complements the paired-world evaluator;
it does not replace it.

## Zero-key falsification demo

```bash
finmirror trace-demo
```

The command creates two systems with **byte-identical final predictions** over all 126
cases. The first retains content-addressed read receipts. The second removes only the
trace. Both have 100% answer accuracy; their verified-path pass rates are 100% and 0%.
Open `artifacts/demo/trace/index.html` to inspect the self-contained comparison, or use
the [live copy](https://facewang753.github.io/finmirror/trace/).

This is a contract test, not a hosted-model result. The unverified variant is an
intentional negative control.

## Canonical read receipt

An adapter records a document read at the moment the evidence is exposed to the agent:

```json
{
  "step": "read_document",
  "document_id": "acme-2026q1",
  "observation_sha256": "<64 lowercase hexadecimal characters>"
}
```

The digest binds the complete public `Document` value: ID, title, content, source URL,
media type, and canonicalized metadata. The verifier recomputes it from the selected
paired world. Copying a receipt from a reference world into a perturbed world therefore
fails whenever a bound field changed.

The remainder of a successful numeric trace declares the evidence anchors extracted
and the allow-listed program executed:

```json
[
  {"step": "read_document", "document_id": "acme-2026q1", "observation_sha256": "..."},
  {"step": "extract_operands", "evidence": ["acme-2026q1#E1", "acme-2026q1#E2"]},
  {"step": "execute_formula", "formula_id": "revenue_growth"}
]
```

An abstention ends with `{"step":"abstain","missing_evidence":[...]}`. Unknown and
malformed events fail closed.

## Five independent checks

For each prediction, the audit reports:

1. `receipt_valid` — every trace event is supported and each read digest replays;
2. `retrieval_claim_valid` — claimed retrieved IDs equal the verified reads;
3. `citation_path_valid` — every cited document was read with a valid receipt;
4. `operand_path_valid` — every calculation operand comes from a verified document;
5. `decision_path_valid` — extraction and formula execution, or abstention provenance,
   match the submitted prediction.

The hard gate is conjunctive. The component score is diagnostic only; it cannot
compensate for a failed component. The report also separates `answer_accuracy` from
`trace_pass_rate` and counts answers that are correct but not path-verifiable.

## Audit an external run

```bash
finmirror trace-audit \
  --dataset benchmark/v0.1 \
  --predictions runs/my-agent/predictions.jsonl \
  --system "my-agent@commit" \
  --out runs/my-agent-trace
```

Outputs are a machine-readable `trace-report.json` conforming to
[`schema/trace-audit-report.schema.json`](../schema/trace-audit-report.schema.json) and
a standalone `trace-report.html` with no remote assets or telemetry. The command exits
with status 2 when any trajectory is blocked.

## Claim boundary and threat model

The receipt is content-addressed, not a secret signature. The audit proves that the
*observable submitted trace* is consistent with the supplied world. It does **not**:

- expose or validate private chain-of-thought;
- prove that a model lacked another information channel;
- prove that a tool was invoked inside a tamper-resistant sandbox;
- establish causal attribution from document to answer;
- certify regulatory, financial, or production safety.

For higher-assurance deployments, the harness—not the model—should mint receipts at the
tool boundary, isolate evidence access, record append-only events, and bind tool state,
permissions, time, and code revision. A future signed environment can add those controls
without changing this report contract.

## Relation to paired-world evaluation

Trace replay catches unsupported *paths within one world*. Paired interventions test
whether outputs and paths change across worlds only when the typed evidence relation
permits. A production gate should require both: trace consistency is not causal
sensitivity, and causal sensitivity is not proof of a valid execution record.
