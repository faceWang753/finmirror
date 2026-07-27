# Independent integration reviews

This directory separates integration preflights from executed FinMirror audits.

- A **preflight** pins source code, maps capabilities, identifies the seams required for
  frozen inputs and output capture, and verifies a focused upstream improvement. It
  contains no model score.
- An **executed audit** additionally publishes the adapter, frozen fixtures, system
  configuration, repeated-run baseline, raw predictions, evaluator output, and a
  limitations statement.

No preflight should be cited as evidence that a project is reliable or unreliable.
Unsupported capabilities are marked not applicable rather than scored as failures.

| Project | Pinned revision | Stage | Public contribution |
|---|---|---|---|
| [FinSight-AI](finsight-ai/preflight-54ca3ac.md) | `54ca3ac2ba5178a0c17daa4a773cb9462f274206` | Preflight complete; paired execution blocked on a frozen-corpus seam | [PR #14](https://github.com/juanjuandog/FinSight-AI/pull/14) |
| [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) | `00d509b06f4e4de473d78ceb24cb840f9b0be735` | Integration work in progress | Pending verification |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | `01477f9afb7a47b849ed4c9259d3a9a4738d9fda` | Integration work in progress | Pending verification |
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | `a4a7fe6ace8f04b99188c9f6587e12ea86299bc1` | Planned | None |

The standing scope statement is:

> Independent, non-security-certifying reliability work on `<repo>@<sha>` under a
> declared FinMirror version, configuration, fixture set, and seed. Results characterize
> that pinned configuration and transformation suite—not the project in general,
> investment quality, or production safety.

