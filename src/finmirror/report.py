"""Self-contained, offline HTML reports with no tracking or CDN dependencies."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _pct(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{100 * float(value):.1f}%"


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def _clean_html(document: str) -> str:
    """Normalize generated artifacts to LF with no trailing whitespace."""

    return "\n".join(line.rstrip() for line in document.splitlines()) + "\n"


def render_report(report: dict[str, Any], output: str | Path) -> Path:
    """Render one evaluation report as a polished standalone artifact."""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics = dict(report["metrics"])
    system = dict(report["system"])
    dataset = dict(report["dataset"])
    gate = bool(metrics["hard_gate_pass"])
    score = float(metrics["audit_score"])
    grade = (
        "A"
        if score >= 90
        else "B"
        if score >= 80
        else "C"
        if score >= 70
        else "D"
        if score >= 60
        else "F"
    )
    metric_cards = [
        ("Case accuracy", metrics["case_accuracy"], "Answers + canonical units"),
        (
            "Case verification",
            metrics["case_verification"],
            "Answer + evidence + replay",
        ),
        ("Pair reliability", metrics["pair_reliability"], "Changed for the right reason"),
        ("Answer behavior", metrics["pair_answer_behavior"], "Exact paired answer contract"),
        ("Citation migration", metrics["citation_migration"], "Evidence followed each world"),
        ("Formula replay", metrics["formula_replay"], "Allow-listed program executed"),
        (
            "Operand provenance",
            metrics["operand_provenance"],
            "Inputs linked to exact evidence",
        ),
        (
            "Confidence behavior",
            metrics["confidence_behavior"],
            "Uncertainty followed evidence",
        ),
        ("Material sensitivity", metrics["material_sensitivity"], "Reacted to material facts"),
        (
            "Distractor invariance",
            metrics["distractor_invariance"],
            "Ignored irrelevant changes",
        ),
        ("Evidence ablation", metrics["evidence_ablation"], "Abstained when proof vanished"),
        (
            "Missing evidence",
            metrics["missing_evidence_identification"],
            "Named the exact absent operand",
        ),
        ("Citation F1", metrics["citation_f1"], "Minimum sufficient evidence"),
        (
            "Cross-language",
            metrics["cross_language_consistency"],
            "English · French · Chinese",
        ),
        (
            "Calibration",
            metrics["calibration_score"],
            f"Brier {float(metrics['brier_score']):.3f}",
        ),
    ]
    cards_html = "\n".join(
        f"""
        <article class="metric-card">
          <div class="metric-label">{html.escape(label)}</div>
          <div class="metric-value">{_pct(value)}</div>
          <div class="metric-bar"><span style="width:{100 * float(value):.2f}%"></span></div>
          <p>{html.escape(note)}</p>
        </article>
        """
        for label, value, note in metric_cards
    )
    transform_rows = "\n".join(
        f"""
        <div class="transform-row">
          <span>{html.escape(name.replace("_", " "))}</span>
          <div class="track"><i style="width:{100 * float(values["pass_rate"]):.2f}%"></i></div>
          <strong>{_pct(values["pass_rate"])}</strong>
          <small>{int(values["count"])} pairs</small>
        </div>
        """
        for name, values in report["by_transform"].items()
    )
    failure_rows = (
        "\n".join(
            f"<li><span>{html.escape(name.replace('_', ' '))}</span><strong>{count}</strong></li>"
            for name, count in report["failure_counts"].items()
        )
        or "<li><span>No deterministic failures</span><strong>0</strong></li>"
    )

    title = f"FinMirror · {system['name']}"
    status_text = "Release gate passed" if gate else "Release gate blocked"
    status_class = "pass" if gate else "blocked"
    report_json = _safe_json(report)

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --ink:#f4f1e8; --muted:#a9b2ae; --paper:#0b1110; --panel:#111a18;
      --line:#26322f; --mint:#8ce7c1; --mint2:#39b98a; --coral:#ff8068;
      --amber:#f4c76b; --blue:#83b8ff;
    }}
    * {{ box-sizing:border-box }}
    html {{ scroll-behavior:smooth }}
    body {{
      margin:0; color:var(--ink); background:
        radial-gradient(circle at 88% 2%, rgba(57,185,138,.18), transparent 27rem),
        radial-gradient(circle at 0 45%, rgba(131,184,255,.10), transparent 24rem),
        var(--paper);
      font:15px/1.55 Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
      font-variant-numeric:tabular-nums;
    }}
    a {{ color:inherit }}
    .shell {{ width:min(1180px, calc(100% - 36px)); margin:auto }}
    header {{
      min-height:92px; display:flex; align-items:center; justify-content:space-between;
      border-bottom:1px solid var(--line);
    }}
    .brand {{ display:flex; gap:12px; align-items:center; font-weight:800; letter-spacing:.02em }}
    .mark {{
      width:34px; height:34px; border:1px solid var(--mint2); border-radius:50%;
      display:grid; place-items:center; position:relative;
    }}
    .mark:before,.mark:after {{ content:""; position:absolute; background:var(--mint) }}
    .mark:before {{ width:18px; height:1px }}
    .mark:after {{ height:18px; width:1px }}
    .eyebrow {{ color:var(--mint); text-transform:uppercase; letter-spacing:.16em; font-size:11px }}
    .stamp {{ color:var(--muted); font-size:12px }}
    .hero {{
      display:grid; grid-template-columns:minmax(0,1.45fr) minmax(270px,.55fr);
      gap:60px; padding:72px 0 58px; align-items:center;
    }}
    h1 {{ font-size:clamp(42px,7vw,82px); line-height:.96; letter-spacing:-.055em; margin:12px 0 24px }}
    .lede {{ max-width:720px; color:#c8cfcc; font-size:18px }}
    .pills {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:28px }}
    .pill {{ border:1px solid var(--line); border-radius:999px; padding:7px 11px; color:var(--muted); font-size:12px }}
    .score-card {{
      border:1px solid var(--line); background:linear-gradient(145deg, rgba(255,255,255,.04), rgba(255,255,255,.01));
      border-radius:24px; padding:28px; box-shadow:0 35px 90px rgba(0,0,0,.28);
    }}
    .score-top {{ display:flex; align-items:end; justify-content:space-between }}
    .score {{ font-size:76px; line-height:.85; letter-spacing:-.07em }}
    .grade {{ color:var(--mint); font-size:34px; font-weight:800 }}
    .score-caption {{ color:var(--muted); margin-top:14px }}
    .gate {{ margin-top:24px; border-radius:12px; padding:12px 14px; font-weight:700 }}
    .gate.pass {{ color:var(--mint); background:rgba(57,185,138,.12); border:1px solid rgba(57,185,138,.35) }}
    .gate.blocked {{ color:#ff9a86; background:rgba(255,128,104,.10); border:1px solid rgba(255,128,104,.30) }}
    section {{ padding:46px 0; border-top:1px solid var(--line) }}
    .section-head {{ display:flex; justify-content:space-between; gap:24px; align-items:end; margin-bottom:26px }}
    h2 {{ font-size:clamp(28px,4vw,46px); letter-spacing:-.04em; margin:6px 0 0 }}
    .section-head p {{ color:var(--muted); max-width:480px; margin:0 }}
    .metrics {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px }}
    .metric-card {{ border:1px solid var(--line); border-radius:16px; padding:20px; background:rgba(17,26,24,.74) }}
    .metric-label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em }}
    .metric-value {{ font-size:34px; font-weight:760; margin:9px 0 10px }}
    .metric-card p {{ color:var(--muted); font-size:12px; margin:11px 0 0 }}
    .metric-bar,.track {{ height:4px; border-radius:9px; background:#24302d; overflow:hidden }}
    .metric-bar span,.track i {{ display:block; height:100%; background:linear-gradient(90deg,var(--mint2),var(--mint)) }}
    .diagnostics {{ display:grid; grid-template-columns:1.5fr .5fr; gap:18px }}
    .panel {{ border:1px solid var(--line); background:rgba(17,26,24,.74); border-radius:18px; padding:24px }}
    .panel h3 {{ margin:0 0 20px; font-size:16px }}
    .transform-row {{
      display:grid; grid-template-columns:160px 1fr 60px 56px; align-items:center;
      gap:13px; padding:10px 0; border-top:1px solid rgba(38,50,47,.65);
    }}
    .transform-row:first-of-type {{ border:0 }}
    .transform-row span {{ text-transform:capitalize }}
    .transform-row strong {{ text-align:right }}
    .transform-row small {{ color:var(--muted); text-align:right }}
    .failures {{ list-style:none; padding:0; margin:0 }}
    .failures li {{ display:flex; justify-content:space-between; padding:9px 0; border-top:1px solid rgba(38,50,47,.65); text-transform:capitalize }}
    .failures li:first-child {{ border:0 }}
    .failures strong {{ color:var(--coral) }}
    .controls {{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:18px }}
    select,input {{
      color:var(--ink); background:#101816; border:1px solid var(--line); border-radius:10px;
      padding:10px 12px; font:inherit;
    }}
    input {{ min-width:260px }}
    .table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:15px }}
    table {{ width:100%; border-collapse:collapse; min-width:920px; background:rgba(17,26,24,.72) }}
    th,td {{ text-align:left; padding:13px 15px; border-bottom:1px solid var(--line); vertical-align:top }}
    th {{ color:var(--muted); text-transform:uppercase; letter-spacing:.08em; font-size:10px; position:sticky; top:0; background:#111a18 }}
    td {{ font-size:13px }}
    .ok {{ color:var(--mint) }} .bad {{ color:#ff9a86 }}
    .case-id {{ color:var(--muted); font-family:ui-monospace,SFMono-Regular,Consolas,monospace; font-size:11px }}
    .question {{ max-width:360px }}
    .answer {{ white-space:nowrap }}
    .empty {{ padding:28px; color:var(--muted); text-align:center; display:none }}
    .method-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px }}
    .method {{ padding:20px; border-left:2px solid var(--mint2); background:rgba(17,26,24,.55) }}
    .method b {{ display:block; margin-bottom:8px }} .method p {{ margin:0; color:var(--muted) }}
    footer {{ color:var(--muted); display:flex; justify-content:space-between; gap:24px; padding:36px 0 54px; border-top:1px solid var(--line); font-size:12px }}
    @media (max-width:900px) {{
      .hero,.diagnostics {{ grid-template-columns:1fr }}
      .metrics {{ grid-template-columns:repeat(2,1fr) }}
      .method-grid {{ grid-template-columns:1fr }}
    }}
    @media (max-width:560px) {{
      .shell {{ width:min(100% - 24px,1180px) }}
      header {{ min-height:72px }} .stamp {{ display:none }}
      .hero {{ padding-top:48px; gap:32px }}
      .metrics {{ grid-template-columns:1fr }}
      .section-head {{ display:block }}
      .transform-row {{ grid-template-columns:125px 1fr 52px }}
      .transform-row small {{ display:none }}
      footer {{ display:block }}
    }}
  </style>
</head>
<body>
  <header class="shell">
    <div class="brand"><span class="mark" aria-hidden="true"></span> FinMirror</div>
    <div class="stamp">Behavioral reliability card · schema {html.escape(str(report["report_schema_version"]))}</div>
  </header>
  <main class="shell">
    <div class="hero">
      <div>
        <div class="eyebrow">Paired counterfactual evaluation</div>
        <h1>{html.escape(str(system["name"]))}</h1>
        <p class="lede">Change one financial fact. Did the system change its answer for the
        right reason—or stay confident in a memorized story? FinMirror scores answers,
        evidence, abstention, calibration, and cross-language behavior together.</p>
        <div class="pills">
          <span class="pill">{int(dataset["case_count"])} cases</span>
          <span class="pill">{int(dataset["pair_count"])} paired interventions</span>
          <span class="pill">{html.escape(" · ".join(dataset["languages"]))}</span>
          <span class="pill">{html.escape(str(len(dataset["scenarios"])))} finance workflows</span>
        </div>
      </div>
      <aside class="score-card">
        <div class="score-top"><div class="score">{score:.1f}</div><div class="grade">{grade}</div></div>
        <div class="score-caption">FinMirror Audit Score / 100</div>
        <div class="gate {status_class}">{html.escape(status_text)}</div>
      </aside>
    </div>

    <section>
      <div class="section-head">
        <div><div class="eyebrow">Reliability vector</div><h2>One score cannot hide a failure.</h2></div>
        <p>Every axis is deterministic in v0.1. The release gate blocks systems that are
        fluent but financially wrong, weakly cited, or unable to abstain.</p>
      </div>
      <div class="metrics">{cards_html}</div>
    </section>

    <section>
      <div class="section-head">
        <div><div class="eyebrow">Behavioral diagnosis</div><h2>What broke under intervention?</h2></div>
        <p>Material changes demand sensitivity. Distractors, peer entities, stale periods,
        and document-borne instructions demand specificity.</p>
      </div>
      <div class="diagnostics">
        <div class="panel"><h3>Pass rate by transform</h3>{transform_rows}</div>
        <div class="panel"><h3>Failure taxonomy</h3><ul class="failures">{failure_rows}</ul></div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div><div class="eyebrow">Failure explorer</div><h2>Inspect every decision.</h2></div>
        <p>Filter by language, transform, or verdict. Evidence identifiers are stable,
        explicit, and machine-verifiable.</p>
      </div>
      <div class="controls">
        <select id="verdict"><option value="">All verdicts</option><option value="fail">Failures</option><option value="pass">Passes</option></select>
        <select id="language"><option value="">All languages</option></select>
        <select id="transform"><option value="">All transforms</option></select>
        <input id="search" type="search" placeholder="Search case, question, answer…" aria-label="Search cases">
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Verification</th><th>Case</th><th>Question</th><th>Expected</th><th>Predicted</th><th>Confidence</th><th>Citation F1</th><th>Formula</th></tr></thead>
          <tbody id="rows"></tbody>
        </table>
        <div class="empty" id="empty">No cases match these filters.</div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div><div class="eyebrow">Evaluation contract</div><h2>Correct—and correct for the right reason.</h2></div>
      </div>
      <div class="method-grid">
        <div class="method"><b>Material sensitivity</b><p>A controlled change to a required operand must produce the exact new answer.</p></div>
        <div class="method"><b>Specificity / invariance</b><p>Peer entities, old periods, distractors, and injected instructions must not move the answer.</p></div>
        <div class="method"><b>Tuple verification</b><p>Answer, citations, confidence, abstention, and reported retrieval must move together.</p></div>
      </div>
    </section>
  </main>
  <footer class="shell">
    <span>Generated locally by FinMirror · no telemetry · no external assets</span>
    <span>Audit Score is not a regulatory certification or investment recommendation.</span>
  </footer>
  <script id="report-data" type="application/json">{report_json}</script>
  <script>
    const report = JSON.parse(document.getElementById('report-data').textContent);
    const cases = report.cases;
    const $ = id => document.getElementById(id);
    const esc = value => String(value).replace(/[&<>"']/g, char => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}}[char]));
    const unique = key => [...new Set(cases.map(item => item[key]))].sort();
    for (const language of unique('language')) $('language').insertAdjacentHTML('beforeend', `<option>${{esc(language)}}</option>`);
    for (const transform of unique('transform')) $('transform').insertAdjacentHTML('beforeend', `<option value="${{esc(transform)}}">${{esc(transform.replaceAll('_',' '))}}</option>`);
    function render() {{
      const verdict = $('verdict').value, language = $('language').value;
      const transform = $('transform').value, search = $('search').value.trim().toLowerCase();
      const filtered = cases.filter(item =>
        (!verdict || (verdict === 'pass') === item.verified) &&
        (!language || item.language === language) &&
        (!transform || item.transform === transform) &&
        (!search || JSON.stringify(item).toLowerCase().includes(search))
      );
      $('rows').innerHTML = filtered.map(item => `<tr>
        <td class="${{item.verified?'ok':'bad'}}"><strong>${{item.verified?'PASS':'FAIL'}}</strong></td>
        <td><div class="case-id">${{esc(item.case_id)}}</div><div>${{esc(item.language)}} · ${{esc(item.transform.replaceAll('_',' '))}}</div></td>
        <td class="question">${{esc(item.question)}}</td>
        <td class="answer">${{esc(item.expected_display)}}</td>
        <td class="answer">${{esc(item.predicted_display)}}</td>
        <td>${{(100*item.confidence).toFixed(1)}}%</td>
        <td>${{(100*item.citation_f1).toFixed(1)}}%</td>
        <td>${{(100*item.formula_score).toFixed(1)}}%</td>
      </tr>`).join('');
      $('empty').style.display = filtered.length ? 'none' : 'block';
    }}
    ['verdict','language','transform'].forEach(id => $(id).addEventListener('change', render));
    $('search').addEventListener('input', render);
    render();
  </script>
</body>
</html>
"""
    output_path.write_text(_clean_html(document), encoding="utf-8", newline="\n")
    return output_path


def render_comparison(
    reports: list[dict[str, Any]],
    output: str | Path,
    *,
    links: dict[str, str] | None = None,
) -> Path:
    """Render a compact comparison table for demo and release artifacts."""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for report in sorted(
        reports, key=lambda item: float(item["metrics"]["audit_score"]), reverse=True
    ):
        system = report["system"]["name"]
        metrics = report["metrics"]
        gate = "PASS" if metrics["hard_gate_pass"] else "BLOCKED"
        label = html.escape(str(system))
        href = (links or {}).get(str(system))
        system_cell = (
            f'<a href="{html.escape(href, quote=True)}"><strong>{label}</strong></a>'
            if href
            else f"<strong>{label}</strong>"
        )
        rows.append(
            "<tr>"
            f"<td>{system_cell}</td>"
            f"<td>{float(metrics['audit_score']):.1f}</td>"
            f"<td>{_pct(metrics['case_accuracy'])}</td>"
            f"<td>{_pct(metrics['pair_reliability'])}</td>"
            f"<td>{_pct(metrics['material_sensitivity'])}</td>"
            f"<td>{_pct(metrics['distractor_invariance'])}</td>"
            f"<td>{_pct(metrics['evidence_ablation'])}</td>"
            f'<td class="{"pass" if gate == "PASS" else "blocked"}">{gate}</td>'
            "</tr>"
        )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FinMirror · System comparison</title>
<style>
:root{{--ink:#f4f1e8;--muted:#9da9a5;--bg:#0b1110;--line:#283531;--mint:#8ce7c1;--coral:#ff917c}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 85% 0,rgba(57,185,138,.17),transparent 30rem),var(--bg);color:var(--ink);font:15px/1.55 Inter,system-ui,sans-serif;font-variant-numeric:tabular-nums}}
main{{width:min(1120px,calc(100% - 32px));margin:auto;padding:72px 0}} .brand{{color:var(--mint);text-transform:uppercase;letter-spacing:.16em;font-size:11px}}
h1{{font-size:clamp(42px,7vw,76px);line-height:.98;letter-spacing:-.05em;margin:12px 0 20px}} p{{color:var(--muted);max-width:720px;font-size:17px}}
.modules{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:32px}} .module{{border:1px solid var(--line);border-radius:16px;padding:18px;background:rgba(255,255,255,.025)}} .module strong{{display:block;margin-bottom:5px}} .module span{{color:var(--muted);font-size:13px}} .table{{margin-top:48px;overflow:auto;border:1px solid var(--line);border-radius:18px;background:rgba(255,255,255,.025)}} table{{width:100%;min-width:900px;border-collapse:collapse}} th,td{{padding:17px 18px;border-bottom:1px solid var(--line);text-align:left}} th{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.09em}} td:nth-child(2){{font-size:24px;font-weight:800}} a{{color:var(--ink);text-decoration-color:var(--mint);text-underline-offset:4px}} .pass{{color:var(--mint);font-weight:800}} .blocked{{color:var(--coral);font-weight:800}} .note{{margin-top:24px;font-size:12px}} @media(max-width:760px){{.modules{{grid-template-columns:1fr}}}}
</style></head><body><main>
<div class="brand">FinMirror · paired counterfactual evaluation</div>
<h1>Does the agent change<br>for the right reason?</h1>
<p>A zero-key offline comparison. The gold-reading oracle validates the harness; the
non-gold evidence program validates the public contract; and the evidence-blind baseline
demonstrates why ordinary accuracy misses groundedness failures.</p>
<nav class="modules" aria-label="FinMirror assurance modules">
  <a class="module" href="judge/"><strong>Judge assurance</strong><span>Falsify checklist collapse and permissive learned verifiers.</span></a>
  <a class="module" href="trace/"><strong>Agent trace audit</strong><span>Replay observable evidence paths without hidden chain-of-thought.</span></a>
  <a class="module" href="review/"><strong>Blind expert review</strong><span>Inspect provisional finance gold without seeing model outputs.</span></a>
</nav>
<div class="table"><table><thead><tr><th>System</th><th>Audit score</th><th>Case accuracy</th><th>Pair reliability</th><th>Sensitivity</th><th>Invariance</th><th>Ablation</th><th>Gate</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p class="note">Oracle results are harness checks, not model results. Synthetic v0.1 is a
developer preview and not a regulatory certification or investment recommendation.</p>
</main></body></html>"""
    output_path.write_text(_clean_html(document), encoding="utf-8", newline="\n")
    return output_path
