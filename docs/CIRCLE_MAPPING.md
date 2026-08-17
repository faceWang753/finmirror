# From CIRCLE constructs to FinMirror change contracts

**Public technical mapping · 17 August 2026**

## The narrow connection

[CIRCLE](https://arxiv.org/html/2602.24055v4) is a six-stage, construct-centred lifecycle for translating stakeholder priorities into contextualized evidence, interpretation, and continuous monitoring. FinMirror is much narrower: it is an automated test harness for asking whether a financial QA system changes its answer, evidence, calculation, confidence, and abstention behavior when one controlled evidence fact changes.

The defensible connection is therefore **component-level, not equivalence**:

> **Mapping inference (not a CIRCLE claim):** a FinMirror expected-change contract can instantiate one automated observable inside a CIRCLE evaluation design, provided stakeholders and domain experts first establish that evidence-responsiveness is a relevant construct in the intended setting.

FinMirror does **not** implement the CIRCLE lifecycle, establish real-world impact, or replace stakeholder elicitation, field testing, human-subjects safeguards, expert review, or longitudinal monitoring.

## Lifecycle mapping

| CIRCLE stage and construct role | FinMirror artifact | Observable produced | Claim boundary |
|---|---|---|---|
| **1 · Contextualize — Context specification.** Elicit what stakeholders need evidence about; produce a context brief. | Case metadata such as `stakeholder` and `harm_if_wrong`; the v0.2 research question and explicit non-claims. | A declared financial use context and harm hypothesis. | **Partial design placeholder only.** FinMirror has not elicited or validated these priorities with affected stakeholders. |
| **2 · Identify — Evaluation design and planning.** Operationalize a construct into scenarios, protocols, and metrics. | Typed relations (`should_change`, `should_not_change`, `should_abstain`); intervention gates for observability, answerability, materiality, and counterfactual validity; six atomic transforms. | A machine-readable expectation for what must change and what must remain invariant across a pair. | **Closest fit.** The contracts are authored test specifications, not evidence that the construct is valid in a deployment context. |
| **3 · Represent — Evaluation execution.** Run the planned evaluation and preserve the resulting evidence. | Independently rendered reference/transformed worlds; adapters; prediction JSONL; pinned dataset, model, run, and provenance metadata; v0.2 source receipts and evidence manifest. | Two independently generated system outputs under one declared evidence intervention. | Current scored data are synthetic and automated. There are no participant trials or claims of population coverage. The v0.2 real-source gold remains provisional. |
| **4 · Compare — Analysis.** Link observed behavior back to the construct using rubrics and metrics. | Strict pair evaluator; answer, citation migration, formula replay, operand provenance, confidence, abstention, retrieval, and cross-language diagnostics; mutation/equivalence assurance. | Whether the joint output changed only along the declared dependency path, plus the exact failing component. | This measures contract compliance on specified cases, not downstream financial quality, user behavior, or causal impact. Aggregate weights and thresholds are not empirically validated for financial harm. |
| **5 · Learn — Insights and reporting.** Re-contextualize findings for stakeholder action. | Decomposed reports, hard release gates, data card, limitations, and an explicit negative-result path in the v0.2 protocol. | A bounded go/no-go result and inspectable failure record. | FinMirror can report a test failure; it cannot by itself determine whether to deploy, govern, or decommission a system. Stakeholder interpretation is still required. |
| **6 · Extend — Continuous monitoring.** Revisit constructs and detect changes as deployment conditions evolve. | Pinned digests and versions; source/terms drift checks; planned refreshed test sets, correction log, and re-freezing procedure. | Reproducible differences across evidence, evaluator, and model versions. | This is **evaluation-asset monitoring**, not monitoring of people, workflows, organizational outcomes, or real deployments. Longitudinal CIRCLE evidence is not yet present. |

## One minimal worked example

**Proposed construct:** *evidence-responsive financial calculation* — when an evidence fact material to a calculation changes, the system should recompute from the current evidence; when an irrelevant fact changes, the financial conclusion should remain stable.

This construct name and its placement in CIRCLE are **our mapping inference**, not language or validation supplied by the CIRCLE paper.

FinMirror's synthetic revenue-growth pair asks: “What was Aurelia Robotics' FY2025 revenue growth versus FY2024?”

| World | Evidence | Expected joint behavior |
|---|---|---|
| Reference | FY2024 revenue = 480; FY2025 revenue = 540 (USD millions) | Return **12.5%**; cite both current-world anchors; replay `(540−480)/480×100`. |
| One material intervention | FY2025 revenue changes from 540 to 576; everything else relevant is held fixed | Return **20.0%**; migrate the FY2025 citation and operand to the transformed world; preserve unit and formula; adjust confidence only consistently with the contract. |

The observable is not merely “the answer changed.” The pair passes only if the answer, current-world evidence, operands, and replayed calculation change together as licensed. A memorized **12.5%** on both worlds is pointwise-correct on the reference but fails the material pair. Conversely, changing the answer after only an irrelevant distractor is added also fails.

**Permitted inference:** the test supplies automated evidence about one narrowly operationalized behavior.

**Prohibited inference:** the test does not show that a system is reliable in finance, benefits analysts, reduces real errors, is safe to deploy, or satisfies CIRCLE's real-world validation objective.

---

# Technical note

## 1. Source-grounded interpretation of CIRCLE

CIRCLE expands evaluation beyond isolated model outputs by organizing evaluation as **Contextualize, Identify, Represent, Compare, Learn, and Extend**. Each stage produces a work product that informs the next stage, and the lifecycle is intended to tie metrics to named constructs, observable behavior, and stakeholder-relevant outcomes. See the official v4 paper's [framework overview](https://arxiv.org/html/2602.24055v4#S2), [stage descriptions](https://arxiv.org/html/2602.24055v4#S2.SS1), and [Appendix framework table](https://arxiv.org/html/2602.24055v4#S5).

The paper's examples move from an elicited concern such as over-reliance, through construct operationalization and contextualized scenarios, to mixed-methods analysis and longitudinal monitoring. It explicitly places automated benchmarks at the primary-effects end of a wider methods continuum; participant studies, field testing, and longitudinal evidence are needed to observe richer secondary and tertiary effects ([Stage 2](https://arxiv.org/html/2602.24055v4#S2.SS1.SSS2), [Stage 3](https://arxiv.org/html/2602.24055v4#S2.SS1.SSS3), [Stage 6](https://arxiv.org/html/2602.24055v4#S2.SS1.SSS6)).

Accordingly, the table above does **not** assert that CIRCLE endorses FinMirror, that FinMirror implements CIRCLE, or that a paired-world benchmark constitutes real-world validation. It is a proposed interface: CIRCLE supplies the contextual and construct-validity questions; FinMirror supplies one executable measurement primitive that may be useful after those questions are answered.

## 2. The proposed construct-to-observable chain

The following chain is a synthesis grounded in the two projects, not a quotation from either source:

1. **Stakeholder concern:** a financial system may ignore material evidence changes, react to irrelevant evidence, or preserve an answer while its supporting provenance becomes stale.
2. **Proposed construct:** evidence-responsive financial calculation.
3. **Test scenario:** hold the task and context fixed; apply one observable, atomic intervention to the evidence world.
4. **Behavioral indicator:** the submitted joint output changes exactly where the typed dependency relation licenses change.
5. **Operational metric:** strict pair pass/fail, decomposed into answer behavior, evidence migration, formula/operand behavior, confidence behavior, and reported retrieval behavior.
6. **Narrow interpretation:** evidence about contract compliance for the tested case family.
7. **Required external validation:** stakeholder review of the construct; finance-expert review of facts, materiality, equivalence, and harms; realistic execution conditions; and, where deployment claims are contemplated, contextualized human and longitudinal evidence.

FinMirror formalizes worlds as `W` and `W′ = I(W)` and holds the pair relation in the evaluator rather than revealing it to the system. Its [methodology](METHODOLOGY.md) defines three relations:

- `should_change` when the intervention reaches the answer through the typed dependency/provenance graph;
- `should_not_change` when it lies outside the answer's dependency cone; and
- `should_abstain` when the intervention removes a member of every minimum sufficient evidence set.

This is the technical basis for calling the artifact an **expected-change contract**. “Expected-change contract,” “evidence-responsive financial calculation,” and the CIRCLE-to-FinMirror interface are FinMirror-side or analytical terminology; they are **not terms introduced or validated by CIRCLE**.

## 3. Artifact-to-observable details

### Context and construct record

- **Artifacts:** `stakeholder`, `harm_if_wrong`, task type, language, entity/period metadata, v0.2 research question, annotation guide.
- **Observable:** what the authors claim the case is intended to represent.
- **Validity gap:** authored metadata is not stakeholder elicitation. It cannot establish ecological, construct, criterion, or consequential validity.

### Operationalized change contract

- **Artifacts:** `reference_case_id`, `changed_fields`, transformation type, expected relation, minimum sufficient evidence, gold answer/unit, allow-listed formula, typed operands, tolerance, and materiality declaration.
- **Observable:** an exact predicted change set for the output tuple.
- **Validity gates:** FinMirror requires the intervention to be observable, answerable as declared, material where change is required, and internally coherent apart from the intended attack/conflict class.
- **Validity gap:** v0.1 cases are templated and synthetic; the gates are structurally enforced but are not independently finance-expert validated.

### Execution evidence

- **Artifacts:** current-world documents, independent model calls, predictions, optional retrieval/latency/token/trace telemetry, model identifier, adapter commit, run configuration, and dataset digest.
- **Observable:** the system's output under each world and the metadata needed to reproduce the run.
- **Validity gap:** missing telemetry is marked unavailable rather than imputed. Automated execution does not approximate all real workflows or participant behavior.

### Analysis evidence

- **Artifacts:** case results, strict pair results, component failure labels, group-clustered bootstrap intervals, evaluator-mutation assurance, and positive-equivalence assurance.
- **Observable:** whether harmful mutations are detected, declared representation-only changes remain invariant, and a tested model follows the pair contract.
- **Validity gap:** passing the assurance suite demonstrates regression behavior only for declared mutation/equivalence classes. It does not prove evaluator correctness or financial equivalence coverage.

### Real-source pilot boundary

FinMirror's [v0.2 protocol](V0.2_PROTOCOL.md) proposes a 12-group calibration slice with rights-reviewed captures, source and terms hashes, independent finance-capable annotation, blinded adjudication, and a stop/go release gate. At the document's current status, one English Statistics Canada group exercises the source-to-counterfactual pipeline, but its machine-derived gold is provisional; the unresolved Bank of Canada candidate cannot enter a scored release. Synthetic v0.1 remains the only scored dataset.

This means v0.2 is evidence of **provenance and evaluation infrastructure**, not evidence of semantic correctness, expert agreement, representativeness, licensing permission for unresolved artifacts, or model reliability.

## 4. What a genuine CIRCLE-informed pilot would still require

Before presenting FinMirror results as evidence inside a deployment decision, a team would need to add work outside the current harness:

1. **Contextualize:** interview affected analysts, reviewers, risk owners, and downstream decision-makers; document when stale provenance or evidence-insensitive answers cause material problems.
2. **Identify:** validate the construct definition and choose scenarios, thresholds, populations, comparison conditions, and qualitative evidence with those stakeholders.
3. **Represent:** run realistic workflows with appropriate consent, governance, sampling, training, and protocol-deviation records; retain an automated FinMirror track only as one comparable component.
4. **Compare:** triangulate pair metrics with expert review, interaction records, error recovery, and workflow outcomes; report distributions and disagreements rather than a single index.
5. **Learn:** co-interpret results with stakeholders and state which deployment decisions the evidence can and cannot support.
6. **Extend:** monitor the construct and real outcomes as tasks, sources, users, policies, and system versions change, subject to data minimization and purpose limitation.

## 5. Claim ledger

| Statement | Status | Basis |
|---|---|---|
| CIRCLE is a six-stage lifecycle connecting stakeholder priorities, constructs, contextualized evidence, insights, and monitoring. | **Paper-supported** | CIRCLE abstract, §2, §2.1, and Appendix Table 2. |
| FinMirror independently tests reference and transformed evidence worlds under `should_change`, `should_not_change`, or `should_abstain`. | **Implementation-supported** | FinMirror methodology and case schema. |
| A FinMirror change contract can serve as one automated observable in a CIRCLE-informed evaluation. | **Mapping inference** | Conceptual compatibility between CIRCLE's construct-to-observable design and FinMirror's pair contract; not evaluated by CIRCLE's authors. |
| Strict pair reliability measures real-world financial reliability. | **Not supported** | It measures only declared contract compliance on the benchmark. |
| FinMirror completes CIRCLE's execution, insight, or monitoring stages. | **Not supported** | No human field study, stakeholder interpretation, deployment monitoring, or longitudinal outcome evidence. |
| The v0.2 provenance pipeline makes a case semantically correct or legally redistributable. | **Not supported** | The v0.2 protocol explicitly separates byte/provenance evidence from semantic, expert, and rights conclusions. |
| Passing FinMirror is evidence that a system is safe, beneficial, production-ready, or endorsed by CIRCLE/Cohere/the authors. | **Not supported** | Explicitly outside both this mapping and FinMirror's declared claim boundary. |

## Primary sources

- Schwartz et al., **“CIRCLE: A Framework for Evaluating AI from a Real-World Lens,” arXiv:2602.24055v4**, revised 25 March 2026: [abstract record](https://arxiv.org/abs/2602.24055v4), [official HTML](https://arxiv.org/html/2602.24055v4), [official PDF](https://arxiv.org/pdf/2602.24055v4).
- FinMirror, **Methodology**: [repository source](METHODOLOGY.md) and [public GitHub version](https://github.com/facewang753/finmirror/blob/main/docs/METHODOLOGY.md).
- FinMirror, **v0.2 Calibration-Slice Protocol**: [repository source](V0.2_PROTOCOL.md) and [public GitHub version](https://github.com/facewang753/finmirror/blob/main/docs/V0.2_PROTOCOL.md).
- FinMirror, **v0.1 case record used in the example**: [repository JSONL](../benchmark/v0.1/cases.jsonl) and [public GitHub version](https://github.com/facewang753/finmirror/blob/main/benchmark/v0.1/cases.jsonl).

## Self-check

- Used CIRCLE v4, not an earlier revision.
- Separated paper-supported statements, implementation-supported statements, and mapping inferences.
- Did not imply endorsement, collaboration, real-world validation, expert validation, regulatory certification, or production readiness.
- Kept the worked example synthetic and labeled it as such.
- Treated FinMirror as a possible measurement component, not a substitute for the CIRCLE lifecycle.
- Preserved FinMirror's v0.2 non-claims and stopped short of semantic, legal, population, or downstream-impact conclusions.
