# Interview Brief

## 30-second pitch

I built FinMirror because pointwise accuracy cannot tell whether a financial AI used the
evidence or repeated a plausible answer. FinMirror runs the same system independently in
paired evidence worlds and verifies whether answers, citations, calculation operands,
confidence, and abstention change only when the financial dependency graph permits. The
v0.1 release is a fully tested synthetic protocol with a Cohere Command A+ adapter,
deterministic formula replay, multilingual cases, calibration metrics, and preference
export. I also mapped 42 recent papers to state exactly what is and is not novel.

## Five-minute technical narrative

1. **Problem:** finance errors are often entity-, period-, unit-, or provenance-specific.
   A correct number from the wrong world is still dangerous.
2. **Insight:** evaluation needs both sensitivity and specificity. Change a material
   operand and the system must change; change a distractor and it must not.
3. **Design:** the pair is hidden from the system. The evaluator owns a typed relation and
   exact evidence graph.
4. **Verifier:** no arbitrary code or LLM judge in v0.1—only allow-listed finance
   programs, operand provenance, exact citation sets, calibration, and hard gates.
5. **Negative control:** a memorizer reaches 71.4% case accuracy but 0% strict pair
   reliability.
6. **Cohere alignment:** model evaluation, multilingual systems, agentic RAG, calibrated
   reasoning, soft verifiable rewards, and real-world stakeholder framing.
7. **Scientific honesty:** synthetic v0.1 proves the protocol, not production validity.
   The roadmap has expert annotation, license audit, real filings, sealed transformations,
   and statistical intervals.

## Likely questions

### Isn’t this just metamorphic testing?

Metamorphic testing is the core evaluation technique, not the complete contribution.
FinMirror specializes it into typed financial/provenance relations and evaluates a
structured RAG output, including citation migration, executable calculation inputs,
confidence, and exact missing evidence. The literature review explicitly credits
logic-grounded and causal counterfactual work.

### What is actually novel?

The defensible hypothesis is full-output licensed change under hidden paired document
interventions. I do not claim the first financial counterfactual benchmark, first
entity/period perturbation, first multilingual finance benchmark, or first verifiable
financial reasoning system.

### Why synthetic data?

It gives complete causal control, reproducibility, and clean licensing for protocol
validation. It is also the biggest current limitation. A real-data release needs
record-level licence review and expert validation; public access to issuer filings is not
automatically permission to redistribute them.

### Why not use an LLM judge?

Exact numeric tasks permit stronger deterministic checks. LLM judges can later support
open-ended claim semantics, but only after finance-expert meta-evaluation and never as a
substitute for entity, period, unit, source, or formula constraints.

### Can a model game the six formula IDs?

Yes. Public v0.1 is gameable and not a leaderboard. A research release needs sealed
isomorphic formulas, held-out intervention families, rolling sources, and train/test
separation. The project treats this as a primary threat, not a footnote.

### Why an aggregate score?

It helps regression dashboards, but the vector and hard gates are primary. The index
cannot compensate for basic financial, evidence, formula, or abstention failures.

### Why Cohere?

Cohere publicly emphasizes enterprise agents, RAG, multilinguality, evaluation, CALIBER
pre/post confidence, Soft-SVeRL’s verifiable rewards, and CIRCLE’s real-world lifecycle.
FinMirror turns those themes into a concrete provider-neutral artifact while offering a
first-class Command A+ / Rerank 4 integration.

### What would you do with three more months?

Run a licensed bilingual expert pilot, build XBRL dependency graphs and stable evidence
anchors, compare long-context/RAG/agent baselines, add sealed transformations, and
meta-evaluate the scorer with finance experts. I would stop or narrow the paper claim if
paired metrics do not reveal failures beyond strong pointwise baselines.

## Evidence to show live

- `finmirror validate` and manifest digest;
- the comparison report;
- one material pair and one entity collision;
- the public `PromptCase` boundary;
- formula allow-list and replay;
- a failed pair’s component vector;
- tests that detect dataset tampering;
- literature “cannot claim” table;
- roadmap stop/go criteria.

## Resume bullets

- Built **FinMirror**, an Apache-2.0 paired counterfactual evaluation harness for
  financial RAG/agents across 126 reproducible English, French, and Chinese cases.
- Implemented deterministic scoring for numeric answers, minimum evidence, citation
  migration, allow-listed formula replay, operand provenance, calibration, abstention,
  retrieval telemetry, and preference-data export.
- Demonstrated that an evidence-blind baseline with 71.4% pointwise accuracy achieves 0%
  strict pair reliability; shipped interactive local reports and a Cohere Command A+ /
  Rerank 4 adapter.
- Conducted a 42-paper 2024–2026 literature audit to narrow novelty claims and designed an
  expert-reviewed, contamination-limited research roadmap.

Only use these bullets after publishing the repository and keeping the reproduced
artifacts intact.

