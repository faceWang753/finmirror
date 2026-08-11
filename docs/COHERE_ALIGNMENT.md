# FinMirror × Cohere: Research and Role Alignment

**Evidence snapshot:** 26 July 2026  
**Purpose:** identify substantive alignment between FinMirror and Cohere's current model, evaluation research, and public role descriptions—without implying endorsement, inside knowledge, or production readiness.

## 1. Executive assessment

FinMirror is most credible as a **model-evaluation and research-engineering artifact**: a small, inspectable harness that turns evidence sensitivity into a versioned contract and produces failure traces rather than a single benchmark score. That maps directly to Cohere's public emphasis on enterprise retrieval, multilingual systems, agentic workflows, calibrated confidence, scalable evaluation, and post-training signals.

The fit is strongest when presented honestly:

- the current suite is a deterministic, synthetic diagnostic environment;
- the Cohere adapter demonstrates API-level integration, not Cohere endorsement or superior model performance;
- decomposed preference records are an open-weight research artifact, not a Cohere fine-tuning pipeline;
- real financial workflows, expert validation, field studies, and competitive baselines remain roadmap items.

## 2. Alignment with current Cohere work

| Cohere model or research program | Public evidence | Concrete FinMirror alignment | Boundary to state explicitly |
|---|---|---|---|
| **Command A+** | Cohere announced [Command A+](https://cohere.com/blog/command-a-plus) on 20 May 2026 as `command-a-plus-05-2026`, an Apache-2.0 sparse-MoE model aimed at reasoning, agentic, retrieval-augmented, multilingual, and multimodal enterprise workloads. The announcement reports 218B total / 25B active parameters, 128K input context, up to 64K generation, 48 languages, tool use, and text/image input. | The adapter defaults to `command-a-plus-05-2026`, requests structured JSON, treats document instructions as untrusted evidence, supports optional Cohere Rerank, and evaluates parallel English/French/Chinese cases. This makes Command A+ a natural *candidate under test*. | Architecture, performance, and hardware figures are Cohere-reported. v0.1 includes an adapter, not a published Command A+ result, independent replication, multimodal test, or production deployment. |
| **CALIBER** | [CALIBER](https://arxiv.org/abs/2606.24281) and Cohere's [research summary](https://cohere.com/research/papers/caliber-calibrating-confidence-before-and-after-reasoning-in-language-models-2026-06-24) distinguish confidence before reasoning from confidence after reasoning and train each against the appropriate information state. | FinMirror's response contract can collect optional pre-answer confidence and required post-answer confidence; the evaluator includes Brier score and ECE and slices behavior by evidence condition. Paired ablations can ask whether confidence falls when decisive evidence disappears. | v0.1 evaluates self-reported confidence. It does not reproduce CALIBER training, prove calibrated confidence, or inherit the paper's reported gains. Reliability plots, repeated model runs, target definitions, and larger held-out sets are still needed. |
| **Soft-SVeRL** | [Soft-SVeRL](https://arxiv.org/abs/2605.28561) and Cohere's [research summary](https://cohere.com/research/papers/soft-sverl-self-verified-reinforcement-learning-with-soft-rewards-2026-05-27) use checklist-like soft rewards and analyze instability caused by self-verification and reward inflation. | FinMirror exports a decomposed deterministic reward vector for answer, unit, evidence, formula, operands, clarification, abstention, contract adherence, and calibration. Those dimensions can support controlled open-weight preference or reward-model experiments and make reward failures inspectable. | The exporter is not Soft-SVeRL, no RL training has been run, and deterministic checks can still be gamed. Records are explicitly marked `human_reviewed: false`; adversarial verifier tests and human labels are roadmap work. |
| **CIRCLE** | [CIRCLE](https://arxiv.org/abs/2602.24055) and Cohere's [research page](https://cohere.com/research/papers/circle-a-framework-for-evaluating-ai-from-a-real-world-lens-2026-03-03) frame evaluation as a six-stage, stakeholder- and deployment-aware lifecycle. | FinMirror supplies one early-layer instrument: controlled model/system behavior tests with reproducible failure traces. Its explicit limitations make it possible to embed the harness in a broader evaluation plan. | v0.1 is not real-world evaluation. It has no stakeholder study, customer workflow, field pilot, longitudinal monitoring, harm analysis, or deployment feedback. Those activities should be designed using a CIRCLE-style lifecycle rather than retroactively claimed. |
| **Global MMLU and multilingual evaluation** | Cohere's [Global MMLU](https://cohere.com/research/globalmmlu) work emphasizes broad language coverage, human verification, and cultural sensitivity. | FinMirror makes every scenario runnable in English, French, and Chinese and reports cross-language consistency, creating useful instrumentation for multilingual regression testing. | The cases are parallel synthetic renderings, not native expert-authored finance tasks. Three languages and answer consistency do not establish cultural validity, equal difficulty, or multilingual generalization. |

## 3. Why the project is relevant to Cohere roles

Public job descriptions are point-in-time signals and may change or close. The mapping below uses the pages available on 26 July 2026 and should not be represented as a guarantee about hiring criteria.

| Role signal | What the public description emphasizes | Evidence FinMirror can show | Evidence still missing |
|---|---|---|---|
| [Senior Research Engineer, Model Evaluation](https://jobs.ashbyhq.com/cohere/cb5d588c-5637-423a-968b-bf637ee2caf9/) | Next-generation benchmarks, datasets, environments, evaluation methods, scalable analysis tooling, judge training, and evaluation efficiency | A versioned environment generator; machine-readable expected-change contracts; deterministic component metrics; hard gates; multilingual variants; analyzable failure records; preference-data export; 15-class harmful-mutation assurance; 10-class positive-equivalence assurance with a brittle control | Real-model leaderboard with uncertainty, expert validation, learned-judge experiments, expert-defined financial equivalence classes, scaling and efficiency measurements |
| [Senior Research Scientist, Model Evaluation](https://jobs.ashbyhq.com/cohere/830c613b-d4bf-4673-ab33-46ccc12cc415) | Research contributions in evaluation methodology and widely useful benchmarks | A precise research hypothesis about causal evidence use and a falsifiable multi-output contract grounded in prior work | Peer-reviewed study, broader systematic review, statistical validation, independent adoption, and evidence that the method generalizes beyond authored finance templates |
| [Research Engineer](https://jobs.ashbyhq.com/cohere/1a5925d0-41bd-4549-9b78-f427a2dda922) and [post-training](https://jobs.ashbyhq.com/cohere/554a9380-ab50-4338-88a9-c6b8ab19d92e) signals | Reliable research infrastructure, experiments, data, evaluation, and post-training workflows | Reproducible generation/evaluation code; typed outputs; inspectable reward components; DPO-style open-weight export; deliberate weak controls | Actual SFT/DPO/RL experiments, ablations, scaling studies, dataset governance, training stability, and human preference data |
| [Agent Harness & Modelling](https://jobs.ashbyhq.com/cohere/1d1b300d-254b-48c4-958f-99c6b907f295) and the current [agentic platform/workflow listing](https://jobs.ashbyhq.com/cohere/1fa01a03-9253-4f62-8f10-0fe368b38cb9/) | Agent harnesses, tool use, enterprise workflows, reliability, and evaluation of action sequences | Structured response contracts; untrusted-instruction handling; paired evidence worlds; content-addressed document-read receipts; fail-closed citation, operand, retrieval, formula, and abstention path replay | Harness-minted signed receipts, executable stateful tools, isolated permissions, recovery behavior, cost/latency, and real enterprise workflow tests |
| [Data Analysis / Evaluation](https://jobs.ashbyhq.com/cohere/61703710-4379-42fd-a508-946f2a5fb6bc) | Evaluation data, analysis, error discovery, and decision-relevant reporting | Component-level metrics, paired comparisons, calibration metrics, language slices, and failure export | Confidence intervals, power analysis, human disagreement, dashboarding on actual model runs, and decision thresholds derived from user risk |
| [North for Finance](https://jobs.ashbyhq.com/cohere/f722247c-291b-44ee-af67-5159b8d5d9b9) | Enterprise finance use cases and domain-specific customer value | A finance-specific failure taxonomy covering evidence, calculation, provenance, abstention, confidence, entity/period collision, and injection | Customer discovery, real document permissions, integration with finance systems, regulatory review, and measured business impact |

The most compelling portfolio signal is therefore not “I built another finance chatbot.” It is: **I found a narrow reliability failure, formalized it as an executable contract, built tests that distinguish memorization from evidence use, mapped the claim against current literature, and documented what evidence would falsify or extend it.**

## 4. Cohere API and licensing reality

### Inference path

The v0.1 adapter uses Cohere's current inference interface through `ClientV2`, with `command-a-plus-05-2026` as the default candidate model. It asks for structured output, supports optional reranking, and keeps evidence instructions untrusted. The active API should be checked against the current [structured outputs documentation](https://docs.cohere.com/v2/docs/structured-outputs) and [tool-use documentation](https://docs.cohere.com/v2/docs/tool-use-overview) before every tagged release.

Command A+ is also announced under Apache 2.0, so a reproducible self-hosted baseline may be possible where hardware and license review permit. That path should be documented separately from hosted API results.

### Fine-tuning path: retired, not merely deprecated

Cohere's [deprecations page](https://docs.cohere.com/docs/deprecations) states that, effective **15 September 2025**, fine-tuning capabilities were retired from the Cohere dashboard and API. Consequently:

- FinMirror must not advertise “one-click Cohere fine-tuning,” a Cohere DPO endpoint, or a Cohere-managed preference-training workflow.
- The current training artifact is correctly limited to a **vendor-neutral, DPO-style export for open-weight experimentation**.
- The Cohere integration is for inference and evaluation (and, where selected, Rerank), not fine-tuning.
- Any future Cohere training claim requires a newly documented, currently supported Cohere product; it cannot be inferred from historical API examples.

This constraint strengthens the project's credibility if stated prominently: the repository follows the current product surface instead of preserving a dead integration for marketing effect.

## 5. Implemented now versus roadmap

| Capability | v0.1 implemented | Roadmap needed for a strong Cohere-facing research artifact |
|---|---|---|
| Paired environment | 18 deterministic groups and seven variants per group; 126 cases and 108 transformed pairs; digest-bound harmful-mutation and positive-equivalence assurance | Larger compositional generator, hidden refreshed worlds, expert-defined scale/currency/formula equivalences, contamination policy |
| Finance reasoning | Six synthetic calculation scenarios with formula and operand replay | Real filings, tables, spreadsheets, wider formula AST, accounting/tax/risk workflows, licensing record |
| Change contract | Expected answer behavior, citation migration, formula/operand provenance, abstention or clarification, and confidence | Typed intermediate state transitions, equivalent-form handling, tool/agent trajectory contracts |
| Perturbations | Material edits, distractors, entity and period collisions, instruction injection, evidence ablation | Layout/OCR changes, cross-document contradictions, tool-schema drift, stale sources, adversarial isomorphs |
| Languages | English, French, and Chinese parallel cases with consistency checks | Native expert authoring, cultural/market coverage, human parity judgments, language-specific calibration |
| Metrics | Deterministic correctness, behavior, citation, replay, provenance, confidence, optional retrieval, abstention, clarification, hard gates | Bootstrap intervals, reliability diagrams, human agreement, external evaluator validation, statistical power |
| Cohere model access | Command A+ inference adapter; structured JSON; optional Rerank; optional pre-confidence | Published API and/or self-hosted Command A+ runs, repeated trials, cost/latency, prompt and decoding disclosure |
| Training data | Vendor-neutral DPO-style pairs and decomposed rewards; `human_reviewed: false` | Human-reviewed preference set, open-weight training runs, Soft-SVeRL-inspired experiments, reward-gaming audits |
| Agents and tools | No full agent environment; injection-aware evidence contract and optional retrieval instrumentation only | Executable finance tools, tool permissions, multi-step state, trajectory capture, recovery and handoff evaluation |
| Real-world evaluation | No production or stakeholder claim | CIRCLE-style stakeholder mapping, field pilots, longitudinal monitoring, incident taxonomy, red-team and governance review |

## 6. A rigorous Command A+ experiment

A credible first model study should be deliberately small and reproducible.

### Registered hypotheses

1. A model that genuinely uses evidence will change its answer, supporting citations, operands, and confidence in the direction specified by a material paired-world contract.
2. Irrelevant and injection transformations should preserve the valid answer and evidence program.
3. Evidence ablation should increase abstention or targeted clarification and reduce confidence.
4. Pair-aware metrics will reveal failures that standalone answer accuracy conceals.

### Conditions

- Command A+ with the repository's fixed structured-output prompt;
- at least two strong comparison models, including one open-weight model where redistribution permits;
- deterministic harness responders only as positive/negative controls, clearly excluded from model ranking;
- repeated stochastic runs with fixed, disclosed seeds where the provider supports them;
- direct context and retrieval-plus-Rerank conditions kept separate;
- pre-registered decoding parameters, prompt version, API/model version, date, cost, and latency.

### Reporting

Report the complete metric vector and per-variant slices, not one composite score. Include paired bootstrap confidence intervals, Brier score, ECE, reliability diagrams, refusal/clarification confusion matrices, and qualitative traces for every hard-gate failure. Publish negative results and prompt failures. Do not tune on the held-out reporting set.

## 7. Interview and portfolio narrative

A concise, defensible narrative:

> Financial QA systems can keep the right-looking answer while ignoring changed evidence, or change the answer without migrating its citations, operands, uncertainty, and refusal behavior. I built FinMirror to make those dependencies executable. Each source world has controlled variants and a declared contract specifying what should change and what should stay invariant. The harness replays calculations, checks operand provenance and citation migration, scores confidence and missing-evidence behavior, and emits decomposed preference records. I then tested the evaluator in both directions—harmful changes must fail, valid representations must remain invariant—bounded the claim against 56 current papers, and made the gaps part of the experimental roadmap.

Useful live demonstrations:

1. Show the memorized responder passing a reference case and failing a material pair.
2. Show a distractor or injection case where the answer must remain invariant.
3. Show evidence ablation requiring abstention or a specific clarification.
4. Open the failure record and replay the formula from cited operands.
5. Run a real Command A+ case only when credentials are present; label the output with the model ID, date, prompt hash, and retrieval condition.

This presentation demonstrates research judgment because it includes the negative control, the failure mode, the executable evaluator, and the claim boundary—not only a polished demo.

## 8. What FinMirror does not prove

The current repository does not prove:

- that Command A+ or any other model is superior on financial work;
- that its synthetic cases predict accuracy, safety, or return on investment in a customer deployment;
- that confidence emitted by a model is calibrated;
- that French or Chinese behavior is native-quality or culturally valid;
- that deterministic reward components cannot be gamed;
- that the preference export improves an open-weight model;
- that a single-system answer contract captures agentic workflow risk;
- that the dataset is contamination-free, statistically representative, or expert-verified; or
- that Cohere has reviewed, endorsed, or requested the project.

These are not cosmetic disclaimers. They define the next experiments.

## 9. High-impact next deliverables

1. **Reproducible model card:** real Command A+ plus comparison-model runs, exact configuration, paired confidence intervals, cost, latency, and public failure traces.
2. **Extend evaluator assurance:** harmful-mutation and positive-equivalence reports now ship; add finance-expert scale/currency/formula equivalence classes, scorer–expert disagreement analysis, and a documented metric-change process.
3. **Native multilingual pack:** independently authored English, French, and Chinese cases with market-specific concepts and bilingual expert adjudication.
4. **Open-weight training study:** human-reviewed subset, DPO or soft-reward experiment, reward-gaming probes, ablations, and a held-out paired-world evaluation.
5. **Agentic finance environment:** versioned tools, permissions, stale-data and injection scenarios, full trajectories, recovery evaluation, and risk-weighted failure gates.
6. **CIRCLE-style field protocol:** stakeholder goals, deployment context, harm hypotheses, monitoring measures, incident review, and retirement criteria before any customer pilot.

If these deliverables produce negative results, they still strengthen the work: a benchmark becomes useful when it reveals where its own assumptions and the tested systems fail.
