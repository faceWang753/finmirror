# FinMirror Literature Review

**Evidence cut-off:** 10 August 2026

**Scope:** a targeted, project-oriented scan of 53 primary research papers. It is **not** a systematic review, a complete census of financial NLP, or evidence of priority by itself.

## 1. Review question and publication-status policy

This review asks a narrow question: **what prior work most strongly constrains the design, evaluation, and defensible novelty claims of a benchmark for evidence-sensitive financial question answering?**

The tiers below measure **relevance to FinMirror**, not scientific quality:

- **S — claim-defining:** directly constrains FinMirror's contribution boundary or supplies a method that its core evaluation contract must address.
- **A — design-defining:** strongly informs financial tasks, retrieval, reasoning, abstention, tooling, deployment, or benchmark construction.
- **B — validation-defining:** informs evaluator reliability, live evaluation, multilingual validity, confidence, or real-world evaluation.

Publication status is stated conservatively:

- **Peer-reviewed / proceedings** means a paper appears in the linked conference or journal proceedings.
- **Accepted** means the linked primary record explicitly reports acceptance, but proceedings publication was not independently established here.
- **Preprint** means arXiv only as of the cut-off. A preprint is never described below as peer-reviewed.

Dates are the proceedings date where available and otherwise the first arXiv submission date. Findings are summarized from the linked primary records; numerical claims should be checked again before use in a paper abstract or press material.

## 2. Working thesis

Prior work already covers financial counterfactual perturbations, financial-document error detection, safe abstention, evidence-aware RAG, executable financial reasoning, fine-grained citation, confidence calibration, multilingual finance, and agent/tool evaluation. FinMirror therefore should not present any one of those ingredients as new.

The defensible target is narrower: a deterministic evaluation harness in which a source world and a minimally changed evidence world define an **expected-change contract** over a joint output tuple:

`answer + citations + executable formula + operand provenance + abstention/clarification + confidence`

This turns a perturbation into more than a changed-answer test. It asks whether every output that should migrate does migrate, whether outputs that should remain invariant do remain invariant, and whether the entire answer can be replayed against the supplied evidence.

## 3. Evidence map

### S tier — claim-defining work

| # | Work and original source | Date / venue / status | What it establishes | FinMirror implication |
|---:|---|---|---|---|
| 1 | [FinVerBench](https://arxiv.org/abs/2605.29586) | 28 May 2026; **arXiv preprint** | Evaluates financial-statement verification with controlled errors and exposes both missed errors and false positives on clean statements. | Treat clean-world specificity and calibration as first-class metrics. It forecloses a broad claim to be the first counterfactual or controlled-error finance benchmark. |
| 2 | [All That Glisters Is Not Gold: RFC-Bench](https://aclanthology.org/2026.acl-long.492/) | July 2026; **ACL 2026 Long Paper, peer-reviewed proceedings** | Uses original and perturbed financial-news pairs for reference-free factuality diagnosis. | Paired financial worlds are prior art. FinMirror must differentiate itself through its explicit multi-output change contract, deterministic replay, provenance, and invariance tests—not pairing alone. |
| 3 | [Achieving Multi-Hop Calculation and Safe Abstention in Financial QA: GBFR](https://aclanthology.org/2026.acl-long.1273/) | July 2026; **ACL 2026 Long Paper, peer-reviewed proceedings** | Creates answerable and unanswerable variants through entity, time, and metric changes, with multi-hop calculation and safe abstention. | Entity/period collisions and missing-information behavior require explicit tests. FinMirror must not claim the first finance benchmark for perturbed unanswerables or abstention. |
| 4 | [Are Large Language Models Reliable Reviewers? A Benchmark for Error Detection in Financial Documents (FinED-Bench)](https://aclanthology.org/2026.findings-acl.1481/) | July 2026; **Findings of ACL 2026, peer-reviewed proceedings** | Benchmarks error detection across more than 900 financial documents, nine scenarios, and graded complexity. | Add both clean negative controls and varied error mechanisms; avoid claiming the first benchmark for financial-document error detection. |
| 5 | [FaithEval](https://arxiv.org/abs/2410.03727) | First posted 30 September 2024; **ICLR 2025, peer-reviewed** | Separates ordinary QA from behavior under unanswerable, inconsistent, and counterfactual contexts. | Report results by evidence condition rather than collapsing them into answer accuracy. Counterfactual context evaluation is established prior art. |
| 6 | [CUB: Benchmarking Context Utilization](https://arxiv.org/abs/2505.16518) | First posted 22 May 2025; **accepted to ACL 2026 according to the arXiv record** | Tests behavior under gold, conflicting, and irrelevant context across multiple methods and language models. | Explicitly separate evidence use from memorized-answer behavior, and include conflict and irrelevance controls. Do not equate correct answers with correct context use. |
| 7 | [LongCite](https://aclanthology.org/2025.findings-acl.264/) | July 2025; **Findings of ACL 2025, peer-reviewed proceedings** | Studies fine-grained citations for long-context question answering. | Citation correctness and granularity need independent scoring; citation evaluation itself is not novel. FinMirror's claim must concern citation *migration under controlled evidence change*. |
| 8 | [Theoria](https://arxiv.org/abs/2607.01223) | 1 July 2026; **arXiv preprint** | Represents auditable reasoning as typed state transitions and evaluates completeness under changed or poisoned proofs. | Move beyond free-form rationales toward typed, replayable derivations and test whether all change-dependent states migrate. Formula replay in v0.1 is a limited instance, not a full typed proof system. |
| 9 | [LGMT: Logic-Guided Metamorphic Testing](https://arxiv.org/abs/2605.23965) | First posted 12 May 2026; **Knowledge-Based Systems 348 (2026), peer-reviewed journal article** | Applies logic-guided metamorphic relations to test invariant behavior without requiring a conventional oracle for every transformation. | Declare, generate, and score metamorphic relations explicitly: some transformations require change, while distractors and formatting changes require invariance. |
| 10 | [LIBERTy](https://arxiv.org/abs/2601.10700) | 15 January 2026; **arXiv preprint** | Uses structural-causal counterfactuals to test order-faithful behavior rather than surface sensitivity. | Treat paired worlds as interventions over evidence variables and document which outputs are causally expected to change. Current authored pairs do not yet constitute a learned or complete structural causal model. |
| 11 | [LLMs Gaming Verifiers](https://arxiv.org/abs/2604.15149) | 16 April 2026; **arXiv preprint** | Shows that systems trained against verifiers can exploit shortcuts; isomorphic perturbation testing helps reveal reward gaming. | Keep deterministic component scores inspectable, add isomorphic/adversarial variants, and never infer genuine reasoning solely from a high aggregate reward. |
| 12 | [CALIBER: Calibrating Confidence Before and After Reasoning in Language Models](https://arxiv.org/abs/2606.24281) ([Cohere research page](https://cohere.com/research/papers/caliber-calibrating-confidence-before-and-after-reasoning-in-language-models-2026-06-24)) | 23 June 2026; **arXiv preprint** | Trains confidence before and after reasoning against information-state-appropriate targets and reports materially improved calibration. | Record pre-answer and post-answer confidence separately; score Brier/ECE by evidence condition. FinMirror v0.1 evaluates reported confidence but does not implement CALIBER training. |
| 13 | [Soft-SVeRL: Self-Verified Reinforcement Learning with Soft Rewards](https://arxiv.org/abs/2605.28561) ([Cohere research page](https://cohere.com/research/papers/soft-sverl-self-verified-reinforcement-learning-with-soft-rewards-2026-05-27)) | 27 May 2026; **arXiv preprint** | Replaces brittle binary verification with checklist-style soft rewards while identifying instability when self-verification inflates reward. | Export decomposed, inspectable reward dimensions instead of one opaque label. FinMirror's deterministic reward vector is not Soft-SVeRL and does not demonstrate stable RL training. |

### A tier — design-defining work

| # | Work and original source | Date / venue / status | What it establishes | FinMirror implication |
|---:|---|---|---|---|
| 14 | [LiveBench](https://arxiv.org/abs/2406.19314) | First posted 27 June 2024; **ICLR 2025, peer-reviewed** | Uses frequently refreshed questions and objective scoring to reduce contamination and judge dependence. | Publish generators and scoring while holding back or refreshing evaluation instances. The fixed synthetic v0.1 suite is reproducible, but cannot be called contamination-free or “live.” |
| 15 | [FinBalance](https://arxiv.org/abs/2606.15949) | 14 June 2026; **arXiv preprint** | Uses deterministic ledgers, cited journal entries, balance-sheet replay, and distractors. | Deterministic financial replay is prior art. Differentiate through paired evidence worlds and the full output-change contract; later extend beyond six authored formulas. |
| 16 | [BigFinanceBench](https://arxiv.org/abs/2606.03829) | 2 June 2026; **arXiv preprint** | Introduces 928 expert-authored, workflow-grounded finance tasks with point-based rubrics and audit trails. | Add expert-authored workflows and rubric validation before making broad claims about professional usefulness. Synthetic templates are useful unit tests, not a substitute for domain validation. |
| 17 | [FORCE-Bench](https://arxiv.org/abs/2607.19409) | 11 July 2026; **arXiv preprint** | Evaluates enterprise finance agents on 251 expert queries and multiple rubric dimensions. | Evaluate end-to-end agents and workflow quality, not only answer generation. v0.1 remains a component-level harness. |
| 18 | [Finance Agent Benchmark](https://arxiv.org/abs/2508.00828) | First submitted 20 May 2025; **arXiv preprint** | Tests expert financial questions with search and EDGAR tools while accounting for tool behavior and cost. | Future baselines need reproducible tool traces, latency, and cost. FinMirror must not claim to be the first finance-agent benchmark. |
| 19 | [FinMRAGBench](https://aclanthology.org/2026.findings-acl.187/) | July 2026; **Findings of ACL 2026, peer-reviewed proceedings** | Covers expert financial QA across documents, pages, and modalities, including a ReAct-style agent. | Real filings, multi-page evidence, and multimodal retrieval are necessary external-validity extensions. v0.1's synthetic text evidence does not cover them. |
| 20 | [FinRAGBench-V](https://aclanthology.org/2025.emnlp-main.211/) | November 2025; **EMNLP 2025 Main Conference, peer-reviewed proceedings** | Evaluates bilingual financial RAG with visual evidence and citations. | Do not claim the first multilingual, visual, or citation-aware finance benchmark. Test visual grounding and bilingual retrieval in a later, separately licensed suite. |
| 21 | [MultiFinBen](https://aclanthology.org/2026.acl-long.770/) | July 2026; **ACL 2026 Long Paper, peer-reviewed proceedings** | Evaluates financial understanding across five languages and text, vision, and audio. | Three-language templating is not the first multilingual finance evaluation and does not establish native-language validity. Add native expert authoring and cultural/market coverage. |
| 22 | [SAHM](https://aclanthology.org/2026.acl-long.1593/) | July 2026; **ACL 2026 Long Paper, peer-reviewed proceedings** | Provides expert-verified Arabic financial and Shari'ah reasoning data across seven tasks. | Language coverage must include domain-specific institutions and norms, not translation alone. FinMirror's current English/French/Chinese cases should be described as parallel synthetic renderings. |
| 23 | [ARQA](https://aclanthology.org/2026.eacl-industry.63/) | March 2026; **EACL 2026 Industry Track, peer-reviewed proceedings** | Builds roughly 2,500 table-text questions over enterprise annual reports with deterministic recomputation and expert review. | Add table-text evidence, annual-report provenance, and expert review. Deterministic recomputation is established; paired migration remains the intended differentiator. |
| 24 | [LEDGER](https://arxiv.org/abs/2606.13100) | 11 June 2026; **arXiv preprint** | Uses thousands of annual reports and KPI tasks spanning page retrieval, lookup, extraction, and OCR annotations. | Stress-test retrieval and extraction over long, noisy filings. v0.1 cannot support claims about document-scale or OCR robustness. |
| 25 | [FinAuditing](https://arxiv.org/abs/2510.08886) | 10 October 2025; **arXiv preprint** | Uses XBRL structure for semantic, relational, and numerical multi-document auditing. | Add taxonomy-aware and cross-document consistency checks. Formula replay alone is narrower than financial auditing. |
| 26 | [Fin-RATE](https://arxiv.org/abs/2602.07294) | First posted 7 February 2026; **KDD 2026, peer-reviewed** | Tests cross-entity and longitudinal reasoning over SEC material and decomposes errors. | Expand paired worlds to entity and period histories, and preserve component-level error reporting. Authored collision cases are only an initial proxy. |
| 27 | [FinRAG-12B](https://aclanthology.org/2026.acl-industry.92/) | July 2026; **ACL 2026 Industry Track, peer-reviewed proceedings** | Trains for answers, citations, and refusals and reports deployment at more than 40 institutions. | Joint answer/citation/refusal training is prior art. FinMirror can export preference data, but v0.1 has neither production deployment nor evidence of training gains. |
| 28 | [Efficiency vs. Verifiability in Evidence-Aware RAG](https://aclanthology.org/2026.customnlp4u-1.19/) | July 2026; **CustomNLP4U at ACL 2026, peer-reviewed workshop proceedings** | Finds that prompt compression may preserve answer accuracy while degrading grounding substantially. | Measure citation/provenance under context compression and latency constraints; answer accuracy must never stand in for verifiability. |
| 29 | [Abstain-R1](https://arxiv.org/abs/2604.17073) | 18 April 2026; **arXiv preprint** | Applies verifiable reinforcement learning to abstention and missing-information clarification. | Score abstention and clarification separately and export them as distinct training signals. v0.1 does not establish the first such training method or any RL result. |
| 30 | [FinChain](https://aclanthology.org/2026.acl-long.662/) | July 2026; **ACL 2026 Long Paper, peer-reviewed proceedings** | Evaluates executable symbolic financial reasoning and provides component-level chain evaluation. | Executable financial reasoning is prior art. FinMirror's contribution must be the behavior of a replayable chain *across paired evidence changes*, not execution alone. |
| 31 | [Knowing What's Missing](https://aclanthology.org/2026.findings-eacl.217/) | March 2026; **Findings of EACL 2026, peer-reviewed proceedings** | Separates identifying missing information from verifying answer sufficiency. | Require systems to name missing operands or constraints, not merely refuse. Clarification quality needs a structured target and separate score. |
| 32 | [FinToolBench](https://arxiv.org/abs/2603.08262) | 9 March 2026; **arXiv preprint** | Evaluates financial tool use with hundreds of executable tools and queries, including timeliness, intent, and regulatory dimensions. | Add tool-schema changes, stale-data tests, and execution traces. v0.1's optional retrieval adapter is not a tool-use benchmark. |
| 33 | [Finch](https://aclanthology.org/2026.findings-acl.523/) | July 2026; **Findings of ACL 2026, peer-reviewed proceedings** | Evaluates spreadsheet-centric enterprise finance workflows. | Add workbook state, formulas, and multi-step artifacts; current scalar evidence programs do not represent spreadsheet workflows. |
| 34 | [From Tasks to Teams](https://aclanthology.org/2026.findings-acl.1934/) | July 2026; **Findings of ACL 2026, peer-reviewed proceedings** | Advocates risk-first, trajectory-level evaluation for multi-agent financial systems. | Evaluate failures and handoffs across agent trajectories before claiming workflow safety. FinMirror v0.1 scores single-system outputs only. |

### B tier — validation-defining work

| # | Work and original source | Date / venue / status | What it establishes | FinMirror implication |
|---:|---|---|---|---|
| 35 | [RAGChecker](https://proceedings.neurips.cc/paper_files/paper/2024/hash/27245589131d17368cccdfa990cbf16e-Abstract-Datasets_and_Benchmarks_Track.html) | December 2024; **NeurIPS 2024 Datasets & Benchmarks Track, peer-reviewed proceedings** | Decomposes RAG performance into claim-level retrieval and generation diagnostics. | Keep retrieval metrics separate from answer, citation, and provenance metrics; report a vector rather than one leaderboard number. |
| 36 | [MEMERAG](https://arxiv.org/abs/2502.17163) | First posted 24 February 2025; **ACL 2025 according to the arXiv record** | Uses multilingual, human-annotated data to meta-evaluate RAG evaluators. | Validate any future learned judge against multilingual human labels. v0.1's deterministic core deliberately avoids an LLM judge, but its rules still require test coverage and expert audit. |
| 37 | [LiveCLKTBench](https://arxiv.org/abs/2511.14774) | 3 November 2025; **arXiv preprint** | Studies time-sensitive, cross-lingual knowledge transfer in a refreshable benchmark. | Version datasets by knowledge date and language, and add recurring refreshes. Static synthetic facts test controlled behavior, not temporal freshness. |
| 38 | [LiveClin](https://arxiv.org/abs/2602.16747) | First posted 18 February 2026; **ICLR 2026, peer-reviewed** | Uses physician-verified, periodically updated clinical cases to support live evaluation. | This is a lifecycle analogue rather than finance evidence: pair open development data with refreshed expert-verified hidden cases and disclose update policy. |
| 39 | [Global MMLU](https://arxiv.org/abs/2412.03304) ([Cohere research page](https://cohere.com/research/globalmmlu)) | 4 December 2024; **arXiv preprint** | Expands multilingual evaluation to 42 languages with human verification and attention to cultural sensitivity. | Translation parity is insufficient. Add native review, locale-specific finance concepts, and per-language validity evidence before making multilingual generalization claims. |
| 40 | [CIRCLE: A Framework for Evaluating AI from a Real-World Lens](https://arxiv.org/abs/2602.24055) ([Cohere research page](https://cohere.com/research/papers/circle-a-framework-for-evaluating-ai-from-a-real-world-lens-2026-03-03)) | First posted 27 February 2026; **accepted to IntelliSys 2026 according to the primary records** | Proposes a six-stage lifecycle for stakeholder-grounded, real-world AI evaluation. | Position v0.1 as controlled model/system evaluation only. Stakeholder discovery, field pilots, longitudinal monitoring, and deployment feedback belong on the roadmap. |
| 41 | [Towards Dependable Retrieval-Augmented Generation Using Factual Confidence Prediction](https://arxiv.org/abs/2605.05244) | 4 May 2026; **arXiv preprint** | Combines factual-confidence prediction with conformal retriever selection; formal guarantees depend on assumptions such as exchangeability. | Add confidence-aware retrieval selection and test calibration under distribution shift. Do not inherit formal guarantees without reproducing their assumptions. |
| 42 | [ConfidenceBench](https://arxiv.org/abs/2607.20526) | 10 July 2026; **arXiv preprint** | Evaluates verbalized confidence with proper scoring rules and highlights divergence between accuracy and calibration. | Report Brier score and ECE alongside accuracy, with reliability plots and condition slices. A confidence field alone is not evidence of calibrated uncertainty. |

### 27 July update — additional high-relevance work

| # | Tier | Work and original source | Date / venue / status | What it establishes | FinMirror implication |
|---:|:---:|---|---|---|---|
| 43 | A | [FinanceComplexQA](https://arxiv.org/abs/2607.19238) | 21 July 2026; **arXiv preprint** | Evaluates agentic reasoning over complex, bilingual, industrial-style financial documents with open-ended deep-research tasks and an agent-as-judge protocol. | Add complex layouts and open-ended workflows, but meta-evaluate any agent judge against experts. FinMirror's deterministic core remains intentionally limited to closed-form verifiable tasks. |
| 44 | A | [PRBench](https://aclanthology.org/2026.acl-long.1958/) | July 2026; **ACL 2026 Long Paper, peer-reviewed proceedings** | Provides 1,100 expert-authored finance and law tasks with 19,356 expert-curated criteria, contributed by 182 qualified professionals. | External validity requires finance-expert task authoring and independently validated criteria. Synthetic protocol tests cannot substitute for professional workflow evidence. |
| 45 | B | [Plan-RewardBench](https://aclanthology.org/2026.acl-long.1062/) | July 2026; **ACL 2026 Long Paper, peer-reviewed proceedings** | Tests reward models on preferred versus minimally perturbed tool-using trajectories and finds degradation on long horizons. | Preserve replayable traces and create hard-negative trajectory pairs before using FinMirror reward vectors for agent training or claiming trajectory-level reliability. |
| 46 | B | [DREAM](https://aclanthology.org/2026.acl-long.448/) | July 2026; **ACL 2026 Long Paper, peer-reviewed proceedings** | Argues for evaluator capability parity and uses tool-calling evaluation to detect factual and temporal decay in deep-research outputs. | Deterministic evaluation is a strength only where the target is fully specified. Open-ended, time-sensitive tracks will need tool-capable evaluators plus independent meta-evaluation. |
| 47 | B | [NASH](https://aclanthology.org/2026.findings-acl.1119/) | July 2026; **Findings of ACL 2026, peer-reviewed proceedings** | Separates numerical verification from textual semantic similarity and improves sensitivity to number changes on financial evaluation data. | Keep exact numeric replay for closed-form tasks and evaluate numerically aware semantic scoring before accepting free-form equivalents in future open-ended tracks. |

### 8 August update — failure localization and evaluator assurance

| # | Tier | Work and original source | Date / venue / status | What it establishes | FinMirror implication |
|---:|:---:|---|---|---|---|
| 48 | B | [AgentRx](https://arxiv.org/abs/2602.02475) | 2 February 2026; **arXiv preprint** | Uses constraint-validation logs to localize critical failure steps in 115 annotated agent trajectories. | Emit exact, inspectable validation records and distinguish local failure attribution from end-task success. FinMirror's closed-form mutation runner does not reproduce its LLM-based trajectory diagnosis. |
| 49 | B | [AgenticRAGTracer](https://aclanthology.org/2026.findings-acl.66/) | July 2026; **Findings of ACL 2026, peer-reviewed proceedings** | Adds hop-level questions and step-by-step validation to diagnose collapsed or over-extended multi-hop retrieval chains. | Future agentic RAG tracks need typed intermediate retrieval states; v0.1 assurance should stay at the fully specified case/pair level. |
| 50 | B | [Toward Scalable Verifiable Reward: Proxy State-Based Evaluation for Multi-turn Tool-Calling LLM Agents](https://aclanthology.org/2026.acl-industry.87/) | July 2026; **ACL 2026 Industry Track, peer-reviewed proceedings** | Evaluates multi-turn tool agents against expected proxy states and behavior constraints, with reported human–LLM judge agreement above 90%. | Preserve expected state and behavior separately when FinMirror adds tools; learned state tracking will require independent human agreement evidence. |
| 51 | B | [Agentic CLEAR](https://aclanthology.org/2026.acl-demo.74/) | July 2026; **ACL 2026 System Demonstrations, peer-reviewed proceedings** | Provides multi-level, data-driven agent failure analysis and reports alignment with human-annotated errors. | Prefer decomposed failure attribution and meta-evaluate any learned diagnostic layer; deterministic checks remain appropriate only for fully specified targets. |
| 52 | B | [A Survey on Evaluation of LLM-based Agents](https://aclanthology.org/2026.findings-acl.1330/) | July 2026; **Findings of ACL 2026, peer-reviewed proceedings** | Synthesizes capability, application, generalist, benchmark-dimension, and developer-tool perspectives; identifies cost-efficiency, safety, robustness, and fine-grained scalable evaluation as gaps. | Keep cost, safety, robustness, and trajectory evaluation explicit roadmap axes rather than inferring them from answer accuracy. |

### 10 August update — contextual judge calibration

| # | Tier | Work and original source | Date / venue / status | What it establishes | FinMirror implication |
|---:|:---:|---|---|---|---|
| 53 | B | [Project Kaleidoscope: Contextual, Human-Aligned Evaluation for Real-World AI Applications](https://arxiv.org/abs/2607.14673) | 16 July 2026; **arXiv preprint** | Separates evaluation-set construction, human calibration labels, and automated judge scores; uses single-metric judge prompts and withholds aggregation when no judge clears a local human-alignment gate. | Keep oracle requirements separate from learned judgments, expose per-item disagreement, and withhold a release gate when local verifier evidence fails. FinMirror's deterministic judge assurance adds metamorphic checklist probes but does not replace human calibration. |

## 4. Synthesis

Six conclusions follow from the evidence map.

1. **Paired and perturbed financial evaluation already exists.** RFC-Bench, FinVerBench, GBFR, FinED-Bench, and FinBalance make a general “first counterfactual finance benchmark” claim untenable.
2. **Joint outputs matter, but their dependencies must be explicit.** LongCite, FinChain, CALIBER, Abstain-R1, and RAGChecker motivate separate scoring of citation, execution, uncertainty, abstention, retrieval, and answer quality. FinMirror's opportunity is to specify how those outputs should change together under an intervention.
3. **Determinism is valuable but not sufficient.** Replayable formulas and rule-based metrics improve reproducibility; LGMT and verifier-gaming work show that invariants, adversarially isomorphic cases, and evaluator audits are still necessary.
4. **Synthetic tests have high internal control and limited external validity.** Current financial benchmarks increasingly use filings, annual reports, spreadsheets, multimodal pages, tools, experts, and deployed workflows. FinMirror v0.1 should be described as a diagnostic unit-test suite, not a proxy for production finance.
5. **Multilingual and calibrated behavior require validation, not fields in a schema.** Parallel English, French, and Chinese templates plus confidence outputs are useful instrumentation. They do not establish native-language validity or calibration without human review, strong model baselines, confidence analyses, and distribution-shift tests.
6. **Evaluator capability must match task openness.** PRBench and FinanceComplexQA motivate expert rubrics for realistic professional work; DREAM and Plan-RewardBench show why open-ended reports and long tool trajectories cannot be validated by a static scalar judge alone. Project Kaleidoscope further separates human calibration evidence from automated aggregation. FinMirror should retain deterministic checks for fully specified relations and add expert-validated, tool-capable evaluation only for tracks that require it.

## 5. Novelty boundary

### Claims this project must not make

FinMirror should not be described as:

- the first financial counterfactual, perturbation, error-detection, or abstention benchmark;
- the first financial RAG, citation, executable-reasoning, auditing, agent, tool-use, multilingual, multimodal, or long-context benchmark;
- the first approach to calibrated confidence, verifier-aware reward design, or metamorphic LLM testing;
- state of the art, leakage-free, expert-verified, production-validated, or representative of real financial practice on the basis of v0.1;
- a successful fine-tuning or reinforcement-learning method merely because it exports preference records and reward components.

The deterministic oracle and evidence-program responders are **harness sanity checks**, not competitive model baselines. A memorized-answer responder is a deliberately weak negative control.

### Safest current contribution statement

> To our knowledge, as of 10 August 2026 and within this targeted 53-paper scan, FinMirror v0.1 is the first open, deterministic harness to score finance QA systems on paired evidence worlds with an explicit expected-change contract over the joint output tuple—answer, citations, executable formula and operand provenance, abstention or clarification, and confidence—while also testing invariance to irrelevant, entity, period, and injection perturbations in English, French, and Chinese.

Mandatory qualifications:

- v0.1 contains authored, synthetic, fictional evidence rather than real filings or customer workflows;
- the statement is **not** a claim to the first financial counterfactual dataset or benchmark;
- “first” is conditional on this targeted scan and must be revalidated through a broader systematic search before inclusion in a paper abstract, product launch, or press release.

For most public materials, prefer the lower-risk wording:

> In this targeted review, we did not identify another open harness that combines paired financial evidence worlds with a declared change contract spanning answers, citations, replayable formulas and operands, abstention or clarification, and confidence.

## 6. v0.1 implementation versus research roadmap

| Area | Implemented in v0.1 | Not yet implemented / required next |
|---|---|---|
| Evidence worlds | Deterministic paired synthetic cases; reference, material-change, distractor, entity-collision, period-collision, injection, and evidence-ablation variants | Real filings and tables with documented licensing; refreshed hidden cases; document-scale and multimodal evidence |
| Financial scope | Six authored financial calculation scenarios | Broader accounting, valuation, risk, controls, and workflow coverage; formula AST and compositional generation |
| Languages | Parallel English, French, and Chinese renderings | Native expert authoring, locale-specific finance concepts, translation audits, and per-language reliability |
| Outputs | Structured answer, citation, formula, operands, missing-evidence behavior, and confidence contract | Richer typed proof states, tool and agent trajectories, spreadsheet artifacts, visual citations |
| Evaluation | Deterministic answer correctness, answer-change behavior, citation migration, formula replay, operand provenance, abstention, clarification, Brier/ECE, cross-language checks, hard gates, group-clustered bootstrap intervals, 15-class one-field mutation assurance, and checklist-verifier metamorphic assurance | Human/expert agreement, positive equivalence-class assurance, model-generated judge validation, and statistical power analysis |
| Retrieval | Optional retrieval-behavior metrics and Cohere Rerank integration | Controlled retriever baselines, compression studies, confidence-aware selection, long-document retrieval |
| Training artifact | DPO-style open-weight preference export with decomposed deterministic reward vector; records marked not human-reviewed | Human preference collection, open-weight SFT/DPO/RL experiments, verifier-gaming stress tests, ablations, stability studies |
| Models | Deterministic sanity checks and a Cohere inference adapter | Reproducible runs across Command A+ and strong open/proprietary baselines, with cost, latency, variance, and prompt disclosure |
| Real-world validity | None claimed | Stakeholder mapping, field pilots, longitudinal monitoring, red teaming, and CIRCLE-style deployment evaluation |

## 7. Recommended research sequence

1. **Maintain the locked contract.** Version schemas and machine-readable metamorphic relations, run the committed one-field mutation assurance in CI, and add positive equivalence classes without silently changing public metrics.
2. **Run real model baselines.** Evaluate Command A+ and multiple current open and proprietary models with repeated runs, disclosed prompts, decoding settings, cost, latency, and confidence reliability diagrams.
3. **Validate the evaluator.** Commission blinded finance-expert review of a stratified sample; report inter-annotator agreement, deterministic-score disagreement, and failure taxonomy.
4. **Test causal specificity.** Add isomorphic variants, paraphrases, unit/scale changes, formula-equivalent forms, and balanced clean negatives to rule out template and verifier shortcuts.
5. **Earn multilingual claims.** Replace translation-only coverage with native authoring and expert review in each language, including market-specific terminology and disclosure conventions.
6. **Add real evidence carefully.** Build a separately versioned, license-audited set from public filings, tables, and spreadsheets; keep synthetic pairs as controlled unit tests.
7. **Move to workflows.** Capture retrieval, tool, spreadsheet, and multi-agent trajectories and evaluate both final outcomes and risk-bearing intermediate actions.
8. **Adopt a live lifecycle.** Maintain hidden refreshed sets, publish contamination and retirement policies, and evaluate field behavior with stakeholder-defined harms and monitoring plans.

## 8. Validity risks to disclose

- **Construct validity:** exact-match or formula replay can miss financially equivalent answers and reward a narrow schema.
- **Internal validity:** templated pairs may leak the intended transformation or make the change contract easier to infer than real evidence changes.
- **External validity:** synthetic scalar snippets do not approximate the noise, layout, ambiguity, incentives, or regulatory stakes of financial work.
- **Evaluator validity:** deterministic rules are inspectable, but rule bugs and underspecified equivalence classes can still mis-score systems.
- **Statistical validity:** 126 cases (18 groups and 108 transformed pairs) are appropriate for deterministic regression testing, not for precise population estimates without uncertainty analysis.
- **Multilingual validity:** parallel rendering does not demonstrate native fluency, cultural coverage, or equal difficulty.
- **Temporal validity:** a fixed suite can become contaminated and obsolete; results must name the dataset and code version.
- **Training contamination:** public generators improve transparency but make leaderboard-only claims fragile; hidden or frequently refreshed evaluation is needed.

## 9. Maintenance protocol

This review should be versioned with the benchmark. Before every public research claim:

1. repeat searches for financial counterfactual evaluation, evidence-change testing, executable finance QA, citation migration, calibrated abstention, metamorphic LLM testing, and financial agent evaluation;
2. verify every preprint's current venue status from proceedings or an official venue record;
3. append newly discovered work without silently changing the cut-off;
4. revise the novelty statement or remove “first” whenever a closer predecessor appears; and
5. archive the exact search date, query set, screening decisions, and reviewer names if the project later claims a systematic review.
