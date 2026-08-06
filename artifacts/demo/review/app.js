(() => {
  "use strict";

  const data = window.FINMIRROR_REVIEW_DATA;
  if (!data || !Array.isArray(data.cases) || data.cases.length === 0) {
    document.body.textContent = "Review data failed to load.";
    return;
  }

  const byId = (id) => document.getElementById(id);
  const fieldIds = {
    answerable: "answerable",
    relation: "relation",
    material: "material",
    evidence_complete: "evidence-complete",
    formula_correct: "formula-correct",
    computed_value: "computed-value",
    evidence_anchors: "evidence-anchors",
    notes: "notes"
  };
  const requiredJudgments = ["answerable", "relation", "material", "evidence_complete", "formula_correct"];
  const storageKey = `finmirror-review:${data.dataset_sha256}`;
  const emptyDraft = () => ({ reviewer_id: "", conflicts: "", blind: false, labels: {} });
  let current = 0;
  let draft = loadDraft();

  function loadDraft() {
    try {
      const parsed = JSON.parse(localStorage.getItem(storageKey) || "null");
      return parsed && typeof parsed === "object" ? parsed : emptyDraft();
    } catch (_) {
      return emptyDraft();
    }
  }

  function persist() {
    localStorage.setItem(storageKey, JSON.stringify(draft));
  }

  function escapeText(value) {
    return document.createTextNode(String(value));
  }

  function renderDocuments(documents) {
    const container = byId("documents");
    container.replaceChildren();
    documents.forEach((itemDocument, index) => {
      const details = document.createElement("details");
      details.className = "document";
      details.open = index === 0;
      const summary = document.createElement("summary");
      summary.append(escapeText(itemDocument.title || itemDocument.id));
      const pre = document.createElement("pre");
      pre.append(escapeText(itemDocument.content));
      details.append(summary, pre);
      if (itemDocument.source_url) {
        const link = document.createElement("a");
        link.href = itemDocument.source_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.append(escapeText("Open declared source ↗"));
        details.append(link);
      }
      container.append(details);
    });
  }

  function currentLabel() {
    const caseId = data.cases[current].case_id;
    if (!draft.labels[caseId]) {
      draft.labels[caseId] = {
        answerable: "",
        relation: "",
        material: "",
        evidence_complete: "",
        formula_correct: "",
        computed_value: "",
        evidence_anchors: "",
        notes: ""
      };
    }
    return draft.labels[caseId];
  }

  function isComplete(label) {
    return requiredJudgments.every((field) => Boolean(label && label[field]));
  }

  function completionCount() {
    return data.cases.filter((item) => isComplete(draft.labels[item.case_id])).length;
  }

  function saveVisible() {
    draft.reviewer_id = byId("reviewer-id").value.trim();
    draft.conflicts = byId("conflicts").value.trim();
    draft.blind = byId("blind-confirmation").checked;
    const label = currentLabel();
    Object.entries(fieldIds).forEach(([field, id]) => { label[field] = byId(id).value.trim(); });
    persist();
    updateProgress();
  }

  function renderCase() {
    const item = data.cases[current];
    const label = currentLabel();
    byId("case-number").textContent = `WORLD ${String(current + 1).padStart(2, "0")}`;
    byId("case-id").textContent = item.case_id;
    byId("question").textContent = item.question;
    renderDocuments(item.documents);
    Object.entries(fieldIds).forEach(([field, id]) => { byId(id).value = label[field] || ""; });
    byId("previous").disabled = current === 0;
    byId("next").textContent = current === data.cases.length - 1 ? "Save case" : "Save & next";
    updateProgress();
    byId("case-card").setAttribute("tabindex", "-1");
    byId("case-card").focus({ preventScroll: true });
  }

  function updateProgress() {
    const complete = completionCount();
    byId("progress-label").textContent = `Case ${current + 1} of ${data.cases.length}`;
    byId("completion-label").textContent = `${complete} complete`;
    byId("progress-bar").style.width = `${(complete / data.cases.length) * 100}%`;
  }

  function validateExport() {
    saveVisible();
    const errors = [];
    if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$/.test(draft.reviewer_id)) {
      errors.push("enter a valid reviewer ID");
    }
    if (!draft.conflicts) errors.push("complete the conflict disclosure");
    if (!draft.blind) errors.push("confirm the blinding statement");
    const incomplete = data.cases.filter((item) => !isComplete(draft.labels[item.case_id]));
    if (incomplete.length) errors.push(`complete ${incomplete.length} remaining case(s)`);
    const message = byId("validation-message");
    message.classList.toggle("error", errors.length > 0);
    message.textContent = errors.length ? `Cannot export: ${errors.join("; ")}.` : "Ready: all seven cases are complete and dataset-bound.";
    return errors.length === 0;
  }

  function exportRows() {
    if (!validateExport()) return;
    const submittedAt = new Date().toISOString();
    const rows = data.cases.map((item) => {
      const label = draft.labels[item.case_id];
      return {
        schema_version: "1.0",
        pilot_id: data.pilot_id,
        dataset_sha256: data.dataset_sha256,
        reviewer_id: draft.reviewer_id,
        role: "independent_annotator",
        blinded: true,
        conflict_disclosure: draft.conflicts,
        submitted_at: submittedAt,
        case_id: item.case_id,
        answerable: label.answerable,
        relation: label.relation,
        material: label.material,
        evidence_complete: label.evidence_complete,
        formula_correct: label.formula_correct,
        evidence_anchors: label.evidence_anchors.split(",").map((value) => value.trim()).filter(Boolean),
        computed_value: label.computed_value,
        notes: label.notes
      };
    });
    const blob = new Blob([`${rows.map((row) => JSON.stringify(row)).join("\n")}\n`], { type: "application/x-ndjson" });
    const link = document.createElement("a");
    const downloadUrl = URL.createObjectURL(blob);
    link.href = downloadUrl;
    link.download = `finmirror-review-${draft.reviewer_id}-${data.dataset_sha256.slice(0, 12)}.jsonl`;
    link.hidden = true;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
  }

  byId("reviewer-id").value = draft.reviewer_id || "";
  byId("conflicts").value = draft.conflicts || "";
  byId("blind-confirmation").checked = Boolean(draft.blind);
  byId("case-count").textContent = String(data.case_count);
  byId("dataset-digest").textContent = data.dataset_sha256;
  Object.values(fieldIds).forEach((id) => byId(id).addEventListener("change", saveVisible));
  ["reviewer-id", "conflicts", "blind-confirmation"].forEach((id) => byId(id).addEventListener("change", saveVisible));
  byId("previous").addEventListener("click", () => { saveVisible(); current -= 1; renderCase(); });
  byId("next").addEventListener("click", () => { saveVisible(); if (current < data.cases.length - 1) current += 1; renderCase(); });
  byId("download").addEventListener("click", exportRows);
  byId("clear").addEventListener("click", () => {
    if (!window.confirm("Clear every locally saved review judgment for this dataset?")) return;
    localStorage.removeItem(storageKey);
    draft = emptyDraft();
    current = 0;
    byId("reviewer-id").value = "";
    byId("conflicts").value = "";
    byId("blind-confirmation").checked = false;
    byId("validation-message").textContent = "Local draft cleared.";
    renderCase();
  });

  renderCase();
})();
