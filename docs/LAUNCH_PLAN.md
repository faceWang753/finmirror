# Ethical Open-Source Launch Plan

Stars are an outcome, not a controllable deliverable. The launch should earn attention by
making a sharp claim reproducible, useful, and easy to inspect.

## Positioning

One sentence:

> FinMirror changes one financial fact and tests whether an AI agent changes for the
> right reason—not merely whether it gets one answer right.

Do not lead with “finance chatbot,” “LLM benchmark,” or unsupported “first” claims. Lead
with the surprising reproducible gap: **71.4% pointwise accuracy, 0% strict pair
reliability** for an evidence-blind system.

## Pre-launch gate

- all tests, lint, types, build, install, and demo pass from a clean environment;
- replace or add repository URLs only after the real GitHub slug is known;
- create a 1280×640 social preview from `assets/finmirror-social-card.svg`;
- capture the comparison card and one failure-explorer screenshot;
- verify every external paper and documentation link;
- confirm license files and dataset digest;
- open three beginner-friendly issues and one research RFC;
- obtain two external reviewers: one evaluation researcher, one finance practitioner;
- never publish an API key or paid-model raw prompt containing confidential data.

## Launch package

1. GitHub repository and signed `v0.1.0` release.
2. A 90-second screen recording:
   - pointwise score;
   - flip one operand;
   - show unchanged memorized output;
   - show missing evidence and confidence gate;
   - open the interactive report.
3. A concise technical post with methodology and limitations.
4. A public roadmap issue inviting real-source and adapter collaborators.
5. An optional arXiv technical report only after expert pilot results exist.

## Seven-day sequence

### Day 0 — Quiet review

Send a private release candidate to 5–8 relevant researchers/engineers. Ask:

- Is the claim precise?
- Is a pair invalid or gameable?
- Which metric would you remove?
- What would make you use this in CI?

Fix substantive issues and credit reviewers with permission.

### Day 1 — GitHub release

Publish one strong demo GIF/video and the results table. Cross-post a short, technically
specific thread to LinkedIn and X. Tag authors only when directly discussing their work;
do not mass-tag Cohere employees.

### Day 2 — Research explanation

Publish “Why 71% financial accuracy can mean 0% evidence reliability,” including a
complete failure trace and exact reproduction commands.

### Day 3 — Practitioner use case

Show how an analyst, auditor, or model-evaluation engineer would add one regression pair.

### Day 4 — Community adapter

Ship or highlight one external/provider adapter through a reviewed pull request.

### Day 5 — Open research question

Ask for feedback on Pairwise Licensed Change F1, with the formula and known failure modes.

### Day 7 — Transparent retrospective

Report traffic, clones, issues, reproduction successes, broken assumptions, and next
milestone. Do not manufacture urgency or engagement.

## Channel-specific copy

### GitHub description

```text
Change one financial fact. Test whether an AI agent changes for the right reason.
Deterministic paired evaluation for answers, citations, calculations, confidence,
abstention, and retrieval.
```

### LinkedIn

```text
A financial AI can score 71.4% on ordinary accuracy while failing every strict paired
evidence test.

I built FinMirror to ask a harder question: when one fact changes, do the answer,
citations, calculation inputs, and confidence change together—and when irrelevant
evidence changes, do they stay stable?

v0.1 is open, deterministic, multilingual, and honest about its limits: 126 synthetic
cases prove the protocol, not production safety. Reproduction takes three commands.

[repository link]
```

### Hacker News title

```text
Show HN: FinMirror – paired counterfactual tests for financial AI agents
```

The submission body should include the 71.4%/0% result, zero-key demo, and synthetic-data
limitation in the first paragraph.

## Growth metrics that matter

Track:

- clean-environment reproductions;
- external adapters and case contributions;
- unique contributors and reviewer quality;
- issues that identify real protocol flaws;
- citations or use in evaluation pipelines;
- benchmark groups with verified licences;
- stars and followers only as secondary reach indicators.

Never buy stars, automate unsolicited messages, conceal synthetic results, or imply Cohere
endorsement. A credible correction earns more long-term trust than a viral overclaim.

