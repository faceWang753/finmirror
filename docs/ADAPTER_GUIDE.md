# Adapter Guide

An adapter receives `PromptCase`, which excludes expected answers, pair relations, and
gold evidence. It returns one normalized `Prediction`.

```python
from finmirror.adapters.base import Adapter
from finmirror.models import Prediction, PromptCase


class MyAdapter(Adapter):
    name = "my-agent"
    version = "2026-07-26"

    def generate(self, case: PromptCase) -> Prediction:
        result = call_my_system(
            question=case.question,
            documents=[document.to_dict() for document in case.documents],
        )
        return Prediction.from_dict({"case_id": case.case_id, **result})
```

Run through the leak-resistant harness:

```python
from finmirror.adapters.base import run_adapter
from finmirror.dataset import load_cases
from finmirror.evaluator import evaluate

cases = load_cases("benchmark/v0.1")
predictions = run_adapter(MyAdapter(), cases)
report = evaluate(cases, predictions, system_name="my-agent")
```

## Requirements

- Return the same `case_id`.
- Keep confidence in `[0, 1]`.
- Use the canonical answer unit supplied in `PromptCase.expected_unit`.
- Cite `DOCUMENT_ID#ANCHOR`, not a bare anchor.
- Cite every calculation operand.
- Use only allow-listed formula IDs.
- Submit typed operands even if the model produced only free-form reasoning.
- Leave formula and operands empty on abstention.
- Name exact missing semantic evidence on abstention.
- Report retrieval IDs only if they reflect what the system actually retrieved.
- Preserve trace events without chain-of-thought. Tool/action metadata is sufficient.

Never pass a `BenchmarkCase` into the system; it contains hidden gold.

## Formula IDs

| ID | Named operands | Program |
|---|---|---|
| `revenue_growth` | `prior`, `current` | `(current-prior)/prior*100` |
| `gross_margin` | `revenue`, `cost` | `(revenue-cost)/revenue*100` |
| `debt_to_equity` | `debt`, `equity` | `debt/equity` |
| `cash_runway` | `cash`, `monthly_burn` | `cash/monthly_burn` |
| `covenant_headroom` | `maximum`, `actual` | `maximum-actual` |
| `free_cash_flow` | `operating_cash`, `capex` | `operating_cash-capex` |

FinMirror executes these internally and never evaluates arbitrary generated code.

## Reproducible model cards

Record:

- provider and exact model ID;
- adapter commit and package versions;
- date/time and region;
- prompt/template version;
- temperature, seed if supported, max tokens;
- reranker/model and `top_n`;
- retry and timeout policy;
- total token usage, cost, and latency;
- dataset SHA-256;
- number of independent runs;
- raw prediction JSONL and report JSON.

