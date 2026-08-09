# Every Eval Ever 0.3.0 interoperability

FinMirror exports a completed scored run into the aggregate and instance-level
contracts used by [MLCommons Every Eval Ever](https://github.com/mlcommons/every_eval_ever).
The implementation is pinned to upstream commit
`252f79668110c5d4b9a7b0fda4450bb4f1ec048b`; exact copies of both schemas live in
`src/finmirror/schemas/eee_v0_3_0/` so CI validates the claimed contract offline.

This is an interoperability feature, not an assertion that a model result has been
accepted by MLCommons or reviewed by the EvalEval registry.

## What is exported

The aggregate JSON contains seven declared results:

| Result ID | Scope | Range |
|---|---|---:|
| `finmirror.audit-score` | hard-gated diagnostic composite | 0–100 |
| `finmirror.case-accuracy` | case | 0–1 |
| `finmirror.case-verification` | case | 0–1 |
| `finmirror.citation-f1` | case | 0–1 |
| `finmirror.formula-replay` | case | 0–1 |
| `finmirror.abstention-accuracy` | case | 0–1 |
| `finmirror.pair-reliability` | paired world | 0–1 |

The audit score has no artificial per-sample decomposition. Each of the five case
metrics emits one record per case, and pair reliability emits one record per transformed
pair. A full v0.1 export therefore contains 738 sample-metric rows: `126 × 5 + 108`.
This deliberate duplication follows the EEE rule that a sample contributing to multiple
metrics has a distinct record for every `evaluation_result_id`.

For single-case rows, `input.raw` is only the user question and `input.formatted` is the
actual FinMirror evidence prompt. The gold display value appears only in
`input.reference`; model output appears only in `output.raw`. Pair rows preserve both
independently executed prompts and outputs without showing either paired world to the
system under test.

## Hard publication gates

`finmirror export-eee` fails before creating files when any of these conditions holds:

- the FinMirror report, benchmark digest, predictions, cases, or pairs disagree;
- the run declares `adapter_uses_gold`/`uses_gold`, or is the harness oracle;
- the model ID is not `developer/model`, or its prefix disagrees with `developer`;
- both an inference platform and a local inference engine are claimed;
- a score is missing, non-numeric, non-finite, or outside its declared range;
- the UUID is not RFC 4122 version 4, a datastore path is unsafe, or a destination exists.

All sample records and the aggregate are prepared in memory first. The JSONL SHA-256 is
then embedded in `detailed_evaluation_results`; publication uses exclusive creation and
removes only files/directories created by the failed call.

## Command

First score a real run and retain the matching prediction file. Then use facts from the
actual run rather than inferring provider or deployment metadata:

```bash
finmirror export-eee \
  --dataset benchmark/v0.1 \
  --report runs/my-agent/report.json \
  --predictions runs/my-agent/predictions.jsonl \
  --model-id "<registry-verified-developer/model>" \
  --model-name "<name recorded by the run>" \
  --developer "<registry-verified-developer>" \
  --evaluator-relationship third_party \
  --deployment-type externally_managed \
  --model-availability closed_weights \
  --inference-platform "<actual provider>" \
  --source-url "https://huggingface.co/datasets/mingyang233/FinMirror" \
  --source-revision "<exact dataset revision>" \
  --out artifacts/eee
```

For a self-deployed open-weight model, omit `--inference-platform`, provide the actual
`--inference-engine` and version, and use `self_deployed` / `open_weights` only when both
facts are true. Unknown facts should be declared `unknown`, not guessed.

Output follows the datastore path exactly:

```text
artifacts/eee/data/finmirror-v0.1/<developer>/<model>/<uuid>.json
artifacts/eee/data/finmirror-v0.1/<developer>/<model>/<uuid>_samples.jsonl
```

`--file-uuid` and `--retrieved-timestamp` exist for deterministic conversion tests. A
normal export generates a fresh UUIDv4 and current retrieval timestamp; the stable
`evaluation_id` is derived from the collection, raw model ID, and report evaluation time.

## Before an upstream submission

The exporter records `canonical_id_status=unverified` because it does not silently call a
hosted registry or rewrite identity. Before proposing datastore records:

1. resolve or request the exact canonical model ID in EvalEval;
2. verify provider, deployment, availability, source URL, and immutable revision;
3. re-run upstream schema and semantic validation against the target repository commit;
4. disclose that FinMirror v0.1 is synthetic and has no expert-validated real-source gold;
5. submit adapter code, registry additions, and data in the sequence requested upstream.

The current high-value contribution is the conversion adapter and its adversarial tests.
A model-result submission should wait for a real, reproducible run with reviewed identity
metadata; the deterministic evidence program is a harness fixture, not an LLM result.
