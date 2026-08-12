# Qwen2.5 1.5B Q4_K_M English baseline

This directory preserves a real local-model run of the English FinMirror v0.1 slice: 42 cases, 36 paired comparisons, six finance scenarios, and seven transforms per scenario. The run used strict structured output through FinMirror's OpenAI-compatible adapter. It did **not** use gold labels at inference time.

The result is deliberately reported as a negative baseline: the model achieved an 8.5985/100 Audit Score, 11.90% case accuracy, 0% verified cases, and 0% pair reliability, so the hard gate was blocked. Contract validity was 100%, which shows only that the responses parsed against the required schema; it does not establish evidence grounding or reliability.

## Exact model and runtime

- Model repository: `Qwen/Qwen2.5-1.5B-Instruct-GGUF`
- Repository commit: `91cad51170dc346986eccefdc2dd33a9da36ead9`
- GGUF quantization: `Q4_K_M`
- GGUF SHA-256: `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`
- Runtime: `llama.cpp` release `b10375`, revision `ba360efe1`
- FinMirror: version `0.2.0`, commit `9875837ab6db77a29b7a9e32c7397aee8eaa0d2a`
- English-slice dataset SHA-256: `39924edf59c9c4e67912fd1ec14ba22d4af782c847b4d679e73e1f5283931f32`
- Evaluator-file SHA-256: `fd67d38860c2c6caaf80fa81c503d55630e567e40f435b579cba01cfbc56aff0`

`model-receipt.json` records the complete machine-readable receipt and artifact hashes.

## Reproduce

From a clean FinMirror checkout at the commit above, create an environment and install the OpenAI-compatible adapter:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[openai]"
```

Download the model from the fixed repository commit, verify its SHA-256, then start the fixed `llama.cpp` server on loopback:

```powershell
.\llama-server.exe `
  -m .\qwen2.5-1.5b-instruct-q4_k_m.gguf `
  --host 127.0.0.1 --port 8080 `
  -c 8192 -t 8 -tb 8 -np 4
```

Run each scenario independently. This is operationally equivalent to one 42-case run and makes recovery from a local structured-decoding timeout explicit:

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
    --model "Qwen/Qwen2.5-1.5B-Instruct-GGUF@91cad51170dc346986eccefdc2dd33a9da36ead9:q4_k_m" `
    --request-timeout 900 `
    --languages en `
    --scenarios $scenario `
    --out "runs/qwen2.5-1.5b-q4_k_m-en-$($scenario.Replace('_','-'))"
}
```

Aggregate the 42 predictions without changing any field, verify that the `case_id` values are unique and match the 42 English cases, then score against that exact slice:

```powershell
.\.venv\Scripts\finmirror.exe score `
  --dataset runs/qwen2.5-1.5b-q4_k_m-en-full/dataset `
  --predictions runs/qwen2.5-1.5b-q4_k_m-en-full/predictions.jsonl `
  --system openai-compatible `
  --system-version "Qwen/Qwen2.5-1.5B-Instruct-GGUF@91cad51170dc346986eccefdc2dd33a9da36ead9:q4_k_m" `
  --out runs/qwen2.5-1.5b-q4_k_m-en-full
```

The `finmirror score` command returns exit code `2` because this baseline correctly fails the reliability gate.

## Interpretation boundary

This is a deliberately small, CPU-runnable open-weight baseline on synthetic evidence worlds. It is useful for reproducing evaluator behavior and locating failures; it must not be generalized to production, regulatory, or investment performance. No latency claim is made because the archived predictions report zeroed latency telemetry.
