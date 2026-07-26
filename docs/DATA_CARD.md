# Data Card: FinMirror Synthetic Paired Worlds v0.1

## Summary

FinMirror v0.1 is a deterministic synthetic benchmark for testing evidence-sensitive
behavior in financial AI systems.

| Property | Value |
|---|---|
| Version | 0.1.0 |
| Cases | 126 |
| Reference groups | 18 |
| Transformed pairs | 108 |
| Workflows | 6 |
| Languages | English (`en`), French (`fr`), Chinese (`zh`) |
| Data type | Authored synthetic text and annotations |
| Personal data | None |
| Real companies | None |
| Investment advice | None |
| Data license | CC BY 4.0 |
| Integrity | SHA-256 in `benchmark/v0.1/manifest.json` |

## Intended use

- regression testing for RAG systems and financial agents;
- testing answer sensitivity and distractor specificity;
- validating citation, calculation, operand, confidence, and abstention contracts;
- adapter development and evaluation-tool research;
- demonstrating paired/metamorphic evaluation.

## Out-of-scope use

- investment decisions or recommendations;
- regulatory, audit, accounting, or compliance certification;
- ranking general financial intelligence;
- claims about real filings, markets, cultures, or languages;
- training and evaluating on the same public cases;
- replacing expert review.

## Composition

Each of six fictional-company workflows has one group in each language. Every group has
one reference and six transformed cases:

```text
reference
material value change
irrelevant distractor
peer-entity collision
stale-period collision
document prompt injection
evidence ablation
```

Every answerable case contains two minimum required evidence anchors, an allow-listed
formula program, typed operand values, and exact operand provenance. Ablation removes the
second anchor and labels its semantic identifier as missing.

## Creation process

Cases are generated from manually authored templates in `src/finmirror/generator.py`.
Financial values were selected to yield unambiguous, human-checkable calculations. The
generator is deterministic and writes canonical, sorted JSONL plus a manifest digest.

The three languages share a controlled semantic template. French and Chinese text was
authored for evaluation clarity, not certified by professional translators. A real-world
release requires paid native financial reviewers.

## Validation

The loader fails closed on:

- duplicate IDs;
- absent reference cases or broken pair links;
- missing required evidence anchors;
- operand provenance that differs from required evidence;
- answerable numeric cases without formula programs;
- unanswerable cases without an explicit missing requirement;
- unchanged gold values in `should_change` worlds;
- changed gold values in `should_not_change` worlds;
- manifest digest or case-count mismatch.

Run:

```bash
finmirror validate benchmark/v0.1
```

## Known biases and limitations

- Template style is cleaner and shorter than real filings.
- Entity, period, and unit fields are explicit.
- There is no OCR, layout, table, image, footnote, or cross-document reasoning.
- Workflows overrepresent simple two-operand calculations.
- Language variants share the same Western corporate-finance concepts.
- Prompt injection is obvious and not representative of adaptive attacks.
- Fictional evidence removes licensing risk but reduces ecological validity.

Systems may overfit the six public formula IDs. A research leaderboard should maintain
sealed formula isomorphisms and rolling source material.

## Licensing and provenance

All benchmark text and labels are authored for this repository and contain no copied
issuer filings or commercial market data. They are released under CC BY 4.0; see
`DATA_LICENSE.md`. Code is separately Apache-2.0.

Public access to a filing does not automatically grant unrestricted redistribution of
issuer-authored content. Future real-source shards must carry record-level source,
license, retrieval time, hash, and terms URL, or distribute only fetch manifests after
legal review.

## Maintenance

Breaking schema changes require a new versioned directory. Corrections must update the
manifest digest and changelog. Benchmark cases accepted through contributions require
review for atomicity, observability, materiality, language quality, and license status.

