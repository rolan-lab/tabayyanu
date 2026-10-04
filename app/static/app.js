// Frontend for Tabayyanu. Plain JS, no build step.
// All user and source text is inserted with textContent, never innerHTML.

let S = {};          // Arabic UI strings (strings_ar.json)
let maxChars = 5000;

const $ = (sel, root = document) => root.querySelector(sel);

function fmt(template, values) {
  return template.replace(/\{(\w+)\}/g, (_, k) => (values[k] ?? ""));
}

function applyStrings(root = document) {
  root.querySelectorAll("[data-s]").forEach(el => { el.textContent = S[el.dataset.s] ?? ""; });
  root.querySelectorAll("[data-s-placeholder]").forEach(el => { el.placeholder = S[el.dataset.sPlaceholder] ?? ""; });
}

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setStatus(text, kind = "") {
  const box = $("#status");
  box.className = "status-line " + kind;
  box.textContent = "";
  if (kind === "loading") box.appendChild(el("span", "spinner"));
  box.appendChild(document.createTextNode(text));
}

function renderDiff(diff, container) {
  for (const d of diff) {
    if (d.op === "equal") { container.append(d.quote, " "); continue; }
    if (d.op === "replace") {
      container.append(el("span", "w replace-q", d.quote), " ");
      container.append(el("span", "w replace-s", d.source), " ");
    } else if (d.op === "insert") {
      container.append(el("span", "w insert", d.quote), " ");
    } else if (d.op === "delete") {
      container.append(el("span", "w delete", d.source), " ");
    } else if (d.op === "spelling") {
      container.append(el("span", "w spelling", d.quote), " ");
    }
  }
}

function renderLegend(diff, list) {
  const ops = new Set(diff.map(d => d.op).filter(op => op !== "equal"));
  const cls = { replace: "replace-q", insert: "insert", delete: "delete", spelling: "spelling" };
  for (const op of ops) {
    const li = el("li");
    li.append(el("span", "w " + cls[op], S.legend[op]));
    list.append(li);
  }
}

function renderMessage(item) {
  // Referral (levels C/D) and out-of-scope: fixed wording, never AI-generated.
  const node = $("#message-tpl").content.firstElementChild.cloneNode(true);
  const badge = $(".badge", node);
  badge.textContent = item.status_label;
  badge.classList.add(item.kind);
  $(".message-text", node).textContent = item.explanation;
  return node;
}

function renderItem(item) {
  if (item.kind !== "quote") return renderMessage(item);
  const node = $("#item-tpl").content.firstElementChild.cloneNode(true);
  applyStrings(node);
  const badge = $(".badge", node);
  badge.textContent = item.status_label;
  badge.classList.add(item.status);
  $(".quote", node).textContent = item.quote;
  $(".explanation", node).textContent = item.explanation;
  $(".origin", node).textContent = item.explanation_origin === "llm" ? S.box_ai_llm_badge : S.box_ai_template_badge;

  if (item.source) {
    $(".ref", node).textContent = item.source.ref;
    const sourceText = $(".source-text", node);
    sourceText.textContent = item.source.text;
    if (item.source.type !== "quran") sourceText.classList.replace("quran", "hadith-text");
    const meta = $(".source-meta", node);
    meta.append(item.source.name + " — ");
    const link = el("a", "", S.label_source_link);
    link.href = item.source.url; link.target = "_blank"; link.rel = "noopener";
    meta.append(link);
    if (item.source.attribution) meta.append(` • ${S.label_attribution}: ${item.source.attribution}`);
    if (item.source.grade) meta.append(` • ${S.label_grade}: ${item.source.grade} (${item.source.grade_source})`);
  } else {
    $(".box-source", node).hidden = true;
  }

  if (item.diff_notes && item.diff_notes.length) {
    $(".diff-wrap", node).hidden = false;
    renderDiff(item.diff, $(".diff", node));
    renderLegend(item.diff, $(".legend", node));
    const notes = $(".diff-notes", node);
    item.diff_notes.forEach(n => notes.append(el("li", "", n)));
  }
  $(".note", node).textContent = item.note || "";
  $(".report-form", node).addEventListener("submit", e => sendReport(e, item));
  return node;
}

// Error report: sent only when the user ticks the consent box (nothing is stored otherwise).
async function sendReport(event, item) {
  event.preventDefault();
  const form = event.target;
  const status = $(".report-status", form);
  if (!form.consent.checked) { status.textContent = S.report_need_consent; return; }
  try {
    const res = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consent: true, quote: item.quote || "", status: item.status,
                             ref: item.source ? item.source.ref : null, comment: form.comment.value }),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    status.textContent = S.report_thanks;
    form.querySelector("button").disabled = true;
  } catch (err) {
    status.textContent = S.report_failed;
  }
}

async function verify() {
  const text = $("#input").value;
  const results = $("#results");
  if (!text.trim()) { setStatus(S.empty_input, "error"); return; }
  if (text.length > maxChars) { setStatus(fmt(S.error_too_long, { n: maxChars }), "error"); return; }
  const btn = $("#verify-btn");
  btn.disabled = true;
  results.textContent = "";
  setStatus(S.loading, "loading");
  try {
    const res = await fetch("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    setStatus("");
    if (data.notice) setStatus(S[data.notice] || "", "error");
    data.items.forEach(item => results.append(renderItem(item)));
    if (data.items.length) results.firstElementChild.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    setStatus(S.error_generic, "error");
  } finally {
    btn.disabled = false;
  }
}

async function init() {
  S = await (await fetch("/static/strings_ar.json")).json();
  applyStrings();
  const input = $("#input");
  const counter = $("#counter");
  const updateCounter = () => { counter.textContent = `${input.value.length} / ${maxChars}`; };
  input.addEventListener("input", updateCounter);
  input.addEventListener("keydown", e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) verify(); });
  $("#verify-btn").addEventListener("click", verify);
  $("#clear-btn").addEventListener("click", () => { input.value = ""; $("#results").textContent = ""; setStatus(""); updateCounter(); input.focus(); });
  updateCounter();
  try {
    const meta = await (await fetch("/api/meta")).json();
    maxChars = meta.max_chars;
    updateCounter();
    $("#motto-text").textContent = meta.motto.text;
    $("#motto-ref").textContent = fmt(S.quran_ref_one, { surah: meta.motto.surah_name, from: meta.motto.ayah });
    $("#motto").hidden = false;
  } catch (err) { /* motto is decorative; the tool still works */ }
}

// Used by lessons: send a text to the verifier on the home page.
function runCheck(text) {
  location.hash = "#verify";
  $("#input").value = text;
  $("#input").dispatchEvent(new Event("input"));
  verify();
}

window.appReady = init();
