# TradingAgents reproducibility preflight

| Field | Value |
|---|---|
| Project | [`TauricResearch/TradingAgents`](https://github.com/TauricResearch/TradingAgents) |
| Upstream revision | `01477f9afb7a47b849ed4c9259d3a9a4738d9fda` (`v0.3.1`) |
| Review date | 2026-07-27 |
| Reviewer | Mingyang (Ethan) Wang |
| FinMirror stage | Integration preflight; **not an executed reliability audit** |
| Upstream contribution | [`TauricResearch/TradingAgents#1179`](https://github.com/TauricResearch/TradingAgents/pull/1179) |

## Conclusion

The pinned TradingAgents release already makes several unusually explicit
reproducibility choices: it resolves instrument identity, provides a deterministic
market-data verification snapshot for exact numeric claims, records a requested trade
date, and writes the agent reports to disk. Its own documentation also states that LLM
sampling and live news/social inputs remain non-deterministic.

The remaining preflight gap is not a missing disclaimer. The saved report tree does not
include a machine-readable receipt that binds a result to its effective configuration,
requested as-of date, selected analyst set, model identifiers, configured data-vendor
chains, prior-memory context, and final output. That makes two report directories harder
to compare without reconstructing runtime state.

PR #1179 proposes a focused remedy: save a sanitized `run_manifest.json` beside both
CLI and package-API reports. The manifest contains stable SHA-256 identities for the
effective safe configuration, instrument and memory context, and final decision. It
deliberately records **configured** vendor chains rather than claiming to know which
fallback served an individual tool call.

This is a reproducibility finding, not a claim about forecast quality, investment
performance, security, production safety, or the reliability of TradingAgents as a
whole.

## Evidence inspected

At the pinned revision:

- `build_verified_market_snapshot` constructs a dated OHLCV/indicator snapshot and tells
  the market analyst to use it as the source of truth for exact numeric claims.
- `TradingAgentsGraph` carries `trade_date`, resolved `instrument_context`, prior
  `past_context`, and `final_trade_decision` through the run state.
- `DEFAULT_CONFIG` identifies category-level and tool-level vendor chains.
- `write_report_tree` persists section reports and a consolidated report, but no
  structured run identity.
- The reproducibility documentation explicitly separates fixed market identity/data
  verification from moving live news/social inputs and non-deterministic LLM sampling.

Source links:

- [`market_data_validator.py`](https://github.com/TauricResearch/TradingAgents/blob/01477f9afb7a47b849ed4c9259d3a9a4738d9fda/tradingagents/dataflows/market_data_validator.py)
- [`trading_graph.py`](https://github.com/TauricResearch/TradingAgents/blob/01477f9afb7a47b849ed4c9259d3a9a4738d9fda/tradingagents/graph/trading_graph.py)
- [`default_config.py`](https://github.com/TauricResearch/TradingAgents/blob/01477f9afb7a47b849ed4c9259d3a9a4738d9fda/tradingagents/default_config.py)
- [`reporting.py`](https://github.com/TauricResearch/TradingAgents/blob/01477f9afb7a47b849ed4c9259d3a9a4738d9fda/tradingagents/reporting.py)
- [Pinned reproducibility note](https://github.com/TauricResearch/TradingAgents/blob/01477f9afb7a47b849ed4c9259d3a9a4738d9fda/README.md#reproducibility)

## Capability map

| FinMirror surface | Pinned support | Preflight treatment |
|---|---|---|
| Final answer capture | Yes, through `final_trade_decision` | Mappable |
| Intermediate report capture | Yes | Mappable, but not a normalized citation contract |
| Requested historical date | Yes | Recordable; does not freeze every live source |
| Verified market snapshot | Yes | Strong primitive for exact market-data claims |
| Exact served-vendor and input receipts | Not exposed | Blocks exact replay across fallback and live-source calls |
| Arbitrary frozen corpus injection | Not exposed through the public run API | Blocks a fair FinMirror paired-world execution |
| Final probability confidence | Not exposed as a calibrated probability | `not_exposed`; calibration is not applicable |
| Deterministic no-key execution | Not a model-equivalent path | No hosted-model score can be inferred without a configured provider |

## Why no FinMirror score is published

A paired reliability audit requires the same agent configuration to run independently
against two frozen evidence worlds. At this revision, the market snapshot is a useful
grounding primitive, but the complete tool-input boundary still includes live news,
social feeds, vendor fallbacks, and model calls. The public API does not expose a
test-scoped fixture seam that can replace those inputs with FinMirror's paired worlds.

Running the system twice against live sources would confound the authored intervention
with temporal and fallback drift. Scoring only the final rating without the exact
evidence path would also overstate what was measured. This preflight therefore publishes
the integration boundary and a concrete upstream improvement, but **no model score**.

## Patch verification

Patch commit:
[`475c8d11db5f0b10e7c3ab3dc18aae5881503fb8`](https://github.com/faceWang753/TradingAgents/commit/475c8d11db5f0b10e7c3ab3dc18aae5881503fb8)

```bash
git clone https://github.com/TauricResearch/TradingAgents
cd TradingAgents
git fetch https://github.com/faceWang753/TradingAgents \
  reproducible-run-manifest
git checkout FETCH_HEAD
python -m pip install -e ".[dev]"
python -m pytest -m unit -q
python -m ruff check \
  cli/main.py \
  tests/test_reporting.py \
  tradingagents/graph/trading_graph.py \
  tradingagents/reporting.py \
  tradingagents/run_manifest.py
```

Observed verification:

- full unit selection: 360 passed, 1 optional-provider skip, 202 deselected, with
  69 subtests passing;
- focused reporting selection: 5 passed;
- Ruff lint on every touched Python file: passed;
- `git diff --check`: passed.

The new tests cover manifest persistence, deterministic output, exclusion of runtime
paths, configured vendor identity, and removal of backend credentials, query strings,
and fragments.

## Requested maintainer correction

The PR asks one narrow technical question:

> Is configured vendor-chain identity the right first manifest boundary here, or should
> this wait until per-tool served-vendor and input receipts can also be captured?

Maintainer feedback should be recorded before this preflight is promoted into a joint or
endorsed case study. No affiliation, endorsement, or collaboration is implied.
