# FinMirror Synthetic Paired Worlds v0.1

- `cases.jsonl`: 126 canonically sorted cases.
- `manifest.json`: counts, licence, transforms, and SHA-256 integrity digest.
- Full data card: [`../../docs/DATA_CARD.md`](../../docs/DATA_CARD.md).
- Case schema: [`../../schema/case.schema.json`](../../schema/case.schema.json).

Regenerate and verify:

```bash
finmirror generate --out benchmark/v0.1
finmirror validate benchmark/v0.1
```

The authored synthetic benchmark is CC BY 4.0. It contains fictional companies and no
investment advice.

