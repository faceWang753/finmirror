# Qwen3 4B Q4_K_M English baseline

This directory preserves a real local-model run of the English FinMirror v0.1 slice:
42 cases, 36 paired comparisons, six finance scenarios, and seven transforms per
scenario. The run used FinMirror's strict JSON Schema through its OpenAI-compatible
adapter. It did **not** use gold labels at inference time.

The result is a diagnostic negative baseline. Qwen3 4B achieved a 36.4977/100 Audit
Score and 73.81% case accuracy, but 0% complete case verification and 0% strict pair
reliability, so the hard gate was blocked. All 42 responses satisfied the prediction
schema. This contrast is the point of the run: answer accuracy and parseability did not
establish current-world evidence reliability.

## Exact model and runtime

- Model repository: `Qwen/Qwen3-4B-GGUF`
- Repository commit: `34778e26c8fa5e8bc0daa2389a9f958cffb1aedd`
- Repository filename: `Qwen3-4B-Q4_K_M.gguf`
- GGUF quantization: `Q4_K_M`
- GGUF bytes: `2497280256`
- GGUF SHA-256: `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`
- Runtime: `llama.cpp` release `b10375`, revision `ba360efe1`
- Server: loopback-only, one slot, 8,192-token context, eight generation threads,
  eight batch threads, Jinja chat template, non-thinking template setting
- Inference: temperature `0`, strict JSON Schema, no pre-answer confidence pass
- FinMirror: version `0.2.0`, evaluator/adapter state from commit
  `9875837ab6db77a29b7a9e32c7397aee8eaa0d2a`
- Canonical English-slice dataset SHA-256:
  `39924edf59c9c4e67912fd1ec14ba22d4af782c847b4d679e73e1f5283931f32`
- English-slice `cases.jsonl` file SHA-256:
  `5223d982d99a63844c43b5ee0d82d66f93de042f10d7c7cbc37fb914b7ed3ed4`
- Evaluator-file SHA-256:
  `fd67d38860c2c6caaf80fa81c503d55630e567e40f435b579cba01cfbc56aff0`

`model-receipt.json` records the machine-readable receipt and artifact hashes.

## Reproduce

From a clean FinMirror checkout at the commit above, create an environment and install
the OpenAI-compatible adapter:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[openai]"
```

Download the model from the fixed repository commit, verify its SHA-256, then start the
fixed `llama.cpp` server on loopback:

```powershell
.\llama-server.exe `
  -m .\Qwen3-4B-Q4_K_M.gguf `
  --host 127.0.0.1 --port 8080 `
  -c 8192 -t 8 -tb 8 -np 1 `
  --jinja --no-webui `
  --alias "Qwen/Qwen3-4B-GGUF@34778e26c8fa5e8bc0daa2389a9f958cffb1aedd:Q4_K_M"
```

Run each scenario independently. This makes recovery from a local structured-decoding
timeout explicit without changing the 42-case evaluation:

```powershell
$scenarios = @(
  "cash_runway", "covenant_headroom", "debt_to_equity",
  "free_cash_flow", "gross_margin", "revenue_growth"
)

foreach ($scenario in $scenarios) {
  $env:OPENAI_API_KEY = "local"
  .\.venv\Scripts\finmirror.exe run `
    --adapter openai `
    --base-url http://127.0.0.1:8080/v1 `
    --model "Qwen/Qwen3-4B-GGUF@34778e26c8fa5e8bc0daa2389a9f958cffb1aedd:Q4_K_M" `
    --request-timeout 900 `
    --languages en `
    --scenarios $scenario `
    --out "runs/qwen3-4b-q4_k_m-en-$($scenario.Replace('_','-'))"
}
```

Mechanically concatenate the six prediction files without changing any JSON field.
Before scoring, require exactly 42 unique `case_id` values and exact set equality with
the frozen English slice. Score the aggregate with the canonical evaluator:

```powershell
.\.venv\Scripts\finmirror.exe score `
  --dataset runs/qwen3-4b-q4_k_m-en-full/dataset `
  --predictions runs/qwen3-4b-q4_k_m-en-full/predictions.jsonl `
  --system openai-compatible `
  --system-version "Qwen/Qwen3-4B-GGUF@34778e26c8fa5e8bc0daa2389a9f958cffb1aedd:Q4_K_M" `
  --out runs/qwen3-4b-q4_k_m-en-full
```

The `finmirror score` command returns exit code `2` because this baseline correctly
fails the reliability gate.

## Interpretation boundary

This is one deterministic decoding run of one quantized, local open-weight model on a
small synthetic English benchmark slice. It is useful for reproducing evaluator
behavior and locating failure modes; it is not a ranking of Qwen models and must not be
generalized to production, regulatory, multilingual, or investment performance. No
latency claim is made because the archived predictions intentionally zero latency
telemetry for deterministic artifacts.
