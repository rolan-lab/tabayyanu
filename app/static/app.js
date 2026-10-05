// Frontend for Tabayyanu. Plain JS, no build step.
// All user and source text is inserted with textContent, never innerHTML.

let S = {};          // UI strings for the current language (strings_ar.json / strings_en.json)
let maxChars = 5000;
let LANG = "ar";

function savedLang() {
  try { return localStorage.getItem("tabayyanu.lang") === "en" ? "en" : "ar"; } catch { return "ar"; }
}

async function setLang(lang) {
  LANG = lang;
  try { localStorage.setItem("tabayyanu.lang", lang); } catch { /* not saved in private mode */ }
  S = await (await fetch(`/static/strings_${lang}.json`)).json();
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.title = lang === "ar" ? "تبيّنوا — التحقق من الآيات والأحاديث" : "Tabayyanu — verify verses and hadith";
  applyStrings();
  const btn = $("#lang-btn");
  btn.textContent = S.lang_switch;
  btn.setAttribute("aria-label", S.lang_switch_label);
  btn.lang = lang === "ar" ? "en" : "ar";
  $("#results").textContent = "";
  setStatus("");
  document.dispatchEvent(new Event("langchange"));
}

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

function diffWord(cls, op, text) {
  // The change type is also given in words (title and aria-label), not only by color.
  const span = el("span", "w " + cls, text);
  span.title = S.legend[op];
  span.setAttribute("aria-label", `${S.legend[op]}: ${text}`);
  return span;
}

function renderDiff(diff, container) {
  for (const d of diff) {
    if (d.op === "equal") { container.append(d.quote, " "); continue; }
    if (d.op === "replace") {
      container.append(diffWord("replace-q", "replace", d.quote), " ");
      container.append(diffWord("replace-s", "replace", d.source), " ");
    } else if (d.op === "insert") {
      container.append(diffWord("insert", "insert", d.quote), " ");
    } else if (d.op === "delete") {
      container.append(diffWord("delete", "delete", d.source), " ");
    } else if (d.op === "spelling") {
      container.append(diffWord("spelling", "spelling", d.quote), " ");
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
  renderMeaning(item, node);
  $(".report-form", node).addEventListener("submit", e => sendReport(e, item));
  return node;
}

// Approved meaning and translation (database text, never generated). The reader's
// language comes first; the other language is folded below.
function renderMeaning(item, node) {
  const m = item.meaning;
  if (!m || (!m.explanation_ar && !m.translation_en)) return;
  const box = $(".box-meaning", node);
  const body = $(".meaning-body", box);
  box.hidden = false;
  const blocks = [];
  if (m.explanation_ar) {
    const sec = el("section", "meaning-part");
    sec.lang = "ar"; sec.dir = "rtl";
    sec.append(el("h4", "", item.source.type === "quran" ? S.meaning_tafsir : S.meaning_hadith_explanation));
    if (m.explanation_ar.items) {
      for (const a of m.explanation_ar.items) {
        const p = el("p", "tafsir");
        a.segments.forEach(seg => p.append(seg.aya ? el("span", "aya-seg", seg.text) : seg.text));
        sec.append(p);
      }
    } else {
      sec.append(el("p", "", m.explanation_ar.text));
    }
    sec.append(sourceLine(m.explanation_ar));
    blocks.push(["ar", sec]);
  }
  const t = m.translation_en;
  const en = el("section", "meaning-part");
  en.lang = "en"; en.dir = "ltr";
  if (t) {
    en.append(el("h4", "", item.source.type === "quran" ? S.meaning_translation_en : S.meaning_hadith_translation));
    if (t.items) {
      for (const a of t.items) {
        en.append(el("p", "", t.items.length > 1 ? `(${a.ayah}) ${a.text}` : a.text));
        if (a.footnotes) {
          const d = el("details", "footnotes");
          d.append(el("summary", "", S.meaning_footnotes), el("p", "small", a.footnotes));
          en.append(d);
        }
      }
    } else {
      if (t.title) en.append(el("p", "strong", t.title));
      en.append(el("p", "", t.text));
      if (t.explanation) {
        const d = el("details", "footnotes");
        d.append(el("summary", "", S.meaning_hadith_explanation), el("p", "", t.explanation));
        en.append(d);
      }
    }
    en.append(sourceLine(t));
  } else if (item.source.type === "hadith") {
    en.append(el("p", "muted small", S.meaning_en_missing));
  }
  if (en.childNodes.length) blocks.push(["en", en]);
  // Reader's language first; the other one collapsed.
  blocks.sort((a, b) => (a[0] === LANG ? -1 : 1) - (b[0] === LANG ? -1 : 1));
  blocks.forEach(([lang, sec], i) => {
    if (i === 0) { body.append(sec); return; }
    const d = el("details", "meaning-more");
    d.append(el("summary", "", sec.querySelector("h4")?.textContent || ""), sec);
    body.append(d);
  });
}

function sourceLine(part) {
  const p = el("p", "source-meta muted");
  p.append(part.source + " — ");
  if (part.url) {
    const a = el("a", "", S.label_source_link);
    a.href = part.url; a.target = "_blank"; a.rel = "noopener";
    p.append(a);
  }
  return p;
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
      body: JSON.stringify({ text, lang: LANG }),
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
  await setLang(savedLang());
  $("#lang-btn").addEventListener("click", () => setLang(LANG === "ar" ? "en" : "ar").then(showMotto));
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
    window.META = meta;
    showMotto();
  } catch (err) { /* motto is decorative; the tool still works */ }
}

function showMotto() {
  const meta = window.META;
  if (!meta) return;
  $("#motto-text").textContent = meta.motto.text;  // the verse itself stays in Arabic
  const name = LANG === "en" ? meta.motto.surah_name_en : meta.motto.surah_name;
  $("#motto-ref").textContent = fmt(S.quran_ref_one, { surah: name, from: meta.motto.ayah });
  $("#motto").hidden = false;
}

// Used by lessons: send a text to the verifier on the home page.
function runCheck(text) {
  location.hash = "#verify";
  $("#input").value = text;
  $("#input").dispatchEvent(new Event("input"));
  verify();
}

window.appReady = init();
