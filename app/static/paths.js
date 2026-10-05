// Learning paths (path -> module -> lesson), hash-routed on the same page.
// Content comes from /api/paths; Quran and hadith text in lessons comes from the database.
// Progress is stored only in this browser (localStorage), wrapped in try/catch.

const PROGRESS_KEY = "tabayyanu.progress.v1";
let PATHS = [];
let AUDIENCE = "all";  // filter: all | muslims | non_muslims

function loadProgress() {
  try { return JSON.parse(localStorage.getItem(PROGRESS_KEY)) || {}; } catch { return {}; }
}

function saveProgress(progress) {
  try { localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress)); } catch { /* private mode: progress is not kept */ }
}

const lessonKey = (p, m, l) => `${p.id}/${m.id}/${l.id}`;

function allLessons(path) {
  return path.modules.flatMap(m => m.lessons.map(l => ({ module: m, lesson: l })));
}

function pathProgress(path, progress) {
  const lessons = allLessons(path);
  const done = lessons.filter(({ module, lesson }) => progress[lessonKey(path, module, lesson)]).length;
  return { done, total: lessons.length };
}

function progressBar(done, total) {
  const bar = el("div", "progress");
  bar.setAttribute("role", "progressbar");
  bar.setAttribute("aria-valuemin", "0");
  bar.setAttribute("aria-valuemax", String(total));
  bar.setAttribute("aria-valuenow", String(done));
  bar.setAttribute("aria-label", fmt(S.path_progress, { done, total }));
  const fill = el("span");
  fill.style.width = total ? `${(100 * done) / total}%` : "0";
  bar.append(fill);
  return bar;
}

function audienceFilter() {
  // "both" paths show under every filter.
  const bar = el("div", "audience-filter");
  bar.setAttribute("role", "group");
  bar.setAttribute("aria-label", S.audience_label);
  for (const key of ["all", "muslims", "non_muslims"]) {
    const b = el("button", "chip-btn", S.audience[key]);
    b.type = "button";
    b.setAttribute("aria-pressed", String(AUDIENCE === key));
    b.addEventListener("click", () => { AUDIENCE = key; renderGrid(); });
    bar.append(b);
  }
  return bar;
}

function renderGrid() {
  const grid = $("#paths-grid");
  grid.textContent = "";
  const filterSlot = $("#paths-filter");
  if (filterSlot) filterSlot.replaceWith(Object.assign(audienceFilter(), { id: "paths-filter" }));
  else grid.before(Object.assign(audienceFilter(), { id: "paths-filter" }));
  const shown = PATHS.filter(p => AUDIENCE === "all" || (p.audience || "both") === "both" || p.audience === AUDIENCE);
  if (!shown.length) {
    grid.append(el("div", "card path-card placeholder", S.paths_empty));
    return;
  }
  const progress = loadProgress();
  for (const path of shown) {
    const card = el("a", "card path-card");
    card.href = `#/path/${encodeURIComponent(path.id)}`;
    card.append(el("h3", "", path.title));
    if (path.level) card.append(el("span", "chip", path.level));
    card.append(el("span", "chip", S.audience[path.audience || "both"]));
    if (path.description) card.append(el("p", "muted", path.description));
    const { done, total } = pathProgress(path, progress);
    card.append(el("span", "small muted", fmt(S.path_progress, { done, total })), progressBar(done, total));
    grid.append(card);
  }
}

function crumbs(...links) {
  const nav = el("nav", "crumbs");
  nav.setAttribute("aria-label", "مسار التنقل");
  links.forEach(([text, href], i) => {
    if (i) nav.append(el("span", "muted", "‹"));
    const a = el("a", "", text);
    a.href = href;
    nav.append(a);
  });
  return nav;
}

function renderPath(path, view) {
  const progress = loadProgress();
  view.append(crumbs([S.paths_home, "#"], [S.paths_title, "#paths"]));
  view.append(el("h1", "", path.title));
  if (path.description) view.append(el("p", "muted", path.description));
  const { done, total } = pathProgress(path, progress);
  view.append(el("p", "small muted", fmt(S.path_progress, { done, total })), progressBar(done, total));
  for (const module of path.modules) {
    const sec = el("section", "module card");
    sec.append(el("h2", "", module.title));
    const list = el("ol", "lesson-list");
    for (const lesson of module.lessons) {
      const a = el("a");
      a.href = `#/lesson/${encodeURIComponent(path.id)}/${encodeURIComponent(module.id)}/${encodeURIComponent(lesson.id)}`;
      a.append(el("span", "", lesson.title));
      if (progress[lessonKey(path, module, lesson)]) a.append(el("span", "done", "✓"));
      const li = el("li");
      li.append(a);
      list.append(li);
    }
    sec.append(list);
    view.append(sec);
  }
}

// Approved English translation of a verse or hadith (QuranEnc / HadeethEnc), open in English
// mode and folded in Arabic mode. The Arabic text above it never changes.
function englishPart(tr, label) {
  const frag = document.createDocumentFragment();
  if (!tr) return frag;
  const d = el("details", "lesson-en");
  d.open = LANG === "en";
  d.lang = "en"; d.dir = "ltr";
  d.append(el("summary", "", label));
  if (tr.items) tr.items.forEach(a => d.append(el("p", "", tr.items.length > 1 ? `(${a.ayah}) ${a.text}` : a.text)));
  else d.append(el("p", "", tr.text));
  d.append(sourceLine(tr));
  frag.append(d);
  return frag;
}

function renderBlock(block) {
  const wrap = el("div", "block");
  if (block.type === "text") {
    wrap.append(el("p", "lesson-text", block.body));
  } else if (block.type === "heading") {
    wrap.append(el("h3", "lesson-heading", block.body));
  } else if (block.type === "cited") {
    // The author's own quotation: shown as written, clearly labelled, with a check button.
    const box = el("section", "box box-cited");
    box.append(el("p", "cited-text", block.body));
    if (block.attribution) box.append(el("p", "source-meta muted", block.attribution));
    box.append(el("p", "small muted", block.indexed === false ? S.cited_not_indexed : S.cited_quote));
    const b = el("button", "btn btn-ghost", S.check_this);
    b.type = "button";
    b.addEventListener("click", () => runCheck(block.body));
    box.append(b);
    wrap.append(box);
  } else if (block.type === "quran") {
    const box = el("section", "box box-source");
    box.append(el("div", "block-label", S.block_quran_label));
    box.append(el("blockquote", "quran", block.text || ""));
    const name = LANG === "en" ? block.surah_name_en : block.surah_name;
    const ref = block.ayah_from === block.ayah_to
      ? fmt(S.quran_ref_one, { surah: name, from: block.ayah_from })
      : fmt(S.quran_ref_range, { surah: name, from: block.ayah_from, to: block.ayah_to });
    box.append(el("p", "source-meta muted", `${ref} — ${S.quran_source_name}`));
    box.append(englishPart(block.translation_en, S.meaning_translation_en));
    wrap.append(box);
  } else if (block.type === "hadith") {
    const box = el("section", "box box-source");
    box.append(el("div", "block-label", S.block_hadith_label));
    box.append(el("p", "hadith-text", block.text || ""));
    const meta = [block.attribution, block.grade ? `${S.label_grade}: ${block.grade} (${block.grade_source})` : ""]
      .filter(Boolean).join(" • ");
    box.append(el("p", "source-meta muted", meta));
    box.append(englishPart(block.translation_en, S.meaning_hadith_translation));
    wrap.append(box);
  } else if (block.type === "question") {
    const q = el("fieldset", "question card");
    q.append(el("legend", "", block.prompt));
    const opts = el("div", "options");
    const feedback = el("p", "feedback");
    feedback.setAttribute("aria-live", "polite");
    block.options.forEach((option, i) => {
      const b = el("button", "btn btn-ghost", option);
      b.type = "button";
      b.addEventListener("click", () => {
        feedback.textContent = i === block.answer ? S.question_correct : S.question_wrong;
        feedback.className = "feedback " + (i === block.answer ? "ok" : "muted");
      });
      opts.append(b);
    });
    q.append(opts, feedback);
    wrap.append(q);
  } else if (block.type === "check") {
    const card = el("div", "card");
    card.append(el("p", "", block.body));
    const b = el("button", "btn btn-gold", S.check_this);
    b.type = "button";
    b.addEventListener("click", () => runCheck(block.body));
    card.append(b);
    wrap.append(card);
  }
  return wrap;
}

function renderLesson(path, module, lesson, view) {
  view.append(crumbs([S.paths_home, "#"], [path.title, `#/path/${encodeURIComponent(path.id)}`]));
  view.append(el("h1", "", lesson.title));
  if (LANG === "en") view.append(el("p", "note-en muted small", S.lesson_text_arabic_note));
  lesson.blocks.forEach(b => view.append(renderBlock(b)));

  const key = lessonKey(path, module, lesson);
  const nav = el("div", "lesson-nav");
  const done = el("button", "btn btn-gold", loadProgress()[key] ? S.lesson_completed : S.lesson_complete);
  done.type = "button";
  done.addEventListener("click", () => {
    const progress = loadProgress();
    progress[key] = true;
    saveProgress(progress);
    done.textContent = S.lesson_completed;
  });
  nav.append(done);
  const list = allLessons(path);
  const i = list.findIndex(x => x.lesson === lesson);
  for (const [j, label] of [[i - 1, S.lesson_prev], [i + 1, S.lesson_next]]) {
    if (j < 0 || j >= list.length) continue;
    const a = el("a", "btn btn-ghost", label);
    a.href = `#/lesson/${encodeURIComponent(path.id)}/${encodeURIComponent(list[j].module.id)}/${encodeURIComponent(list[j].lesson.id)}`;
    nav.append(a);
  }
  view.append(nav);
}

// Page changes fade and slide in: the browser's View Transitions API where available,
// otherwise a CSS entrance animation. Both are off when the user prefers reduced motion.
function route() {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (document.startViewTransition && !reduce && document.visibilityState === "visible") {
    const t = document.startViewTransition(renderRoute);
    // A transition can be skipped (e.g. the tab is hidden); the page is still rendered.
    t.ready.catch(() => {});
    t.finished.catch(() => {});
  } else {
    renderRoute();
  }
}

function animateIn(el) {
  el.classList.remove("enter");
  void el.offsetWidth;  // restart the animation
  el.classList.add("enter");
}

function renderRoute() {
  const view = $("#path-view");
  const parts = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  const isPathRoute = parts[0] === "path" || parts[0] === "lesson";
  $("#home").hidden = isPathRoute;
  view.hidden = !isPathRoute;
  animateIn(isPathRoute ? view : $("#home"));
  if (!isPathRoute) { renderGrid(); return; }
  view.textContent = "";
  const path = PATHS.find(p => p.id === parts[1]);
  const module = path && path.modules.find(m => m.id === parts[2]);
  const lesson = module && module.lessons.find(l => l.id === parts[3]);
  if (parts[0] === "path" && path) renderPath(path, view);
  else if (parts[0] === "lesson" && lesson) renderLesson(path, module, lesson, view);
  else view.append(el("p", "", S.not_found_page), crumbs([S.paths_home, "#"]));
  window.scrollTo({ top: 0, behavior: "instant" });
}

(async () => {
  await window.appReady;
  try {
    PATHS = (await (await fetch("/api/paths")).json()).paths;
  } catch { PATHS = []; }
  window.addEventListener("hashchange", route);
  document.addEventListener("langchange", route);
  route();
})();
