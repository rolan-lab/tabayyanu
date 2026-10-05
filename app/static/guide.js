// Learning-path guide: a small panel at the bottom corner. It only points to lessons
// (POST /api/guide); every text it shows is either fixed wording or the team's lesson text.
// Questions are not stored, on the server or in the browser.

(function () {
  const fab = el("button", "guide-fab");
  fab.type = "button";
  fab.setAttribute("aria-haspopup", "dialog");
  fab.setAttribute("aria-expanded", "false");
  fab.append(el("span", "guide-fab-icon", "✦"), el("span", "guide-fab-label"));

  const panel = el("section", "guide-panel");
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-modal", "false");
  panel.setAttribute("aria-labelledby", "guide-title");
  panel.hidden = true;
  panel.innerHTML = `
    <header class="guide-head">
      <h2 id="guide-title"></h2>
      <div class="guide-head-actions">
        <button type="button" class="guide-close guide-min" aria-label="">–</button>
        <button type="button" class="guide-close guide-x" aria-label="">✕</button>
      </div>
    </header>
    <div class="guide-log" aria-live="polite"></div>
    <form class="guide-form">
      <label class="visually-hidden" for="guide-input"></label>
      <input id="guide-input" type="text" maxlength="500" autocomplete="off">
      <button type="submit" class="btn btn-gold"></button>
    </form>`;  // static markup only; all dynamic text below uses textContent

  const log = $(".guide-log", panel);
  const input = $("#guide-input", panel);

  function applyGuideStrings() {
    $(".guide-fab-label", fab).textContent = S.guide_button;
    fab.setAttribute("aria-label", S.guide_title);
    $("#guide-title", panel).textContent = S.guide_title;
    $(".guide-x", panel).setAttribute("aria-label", S.guide_close);
    $(".guide-min", panel).setAttribute("aria-label", S.guide_minimize);
    $("label", panel).textContent = S.guide_title;
    input.placeholder = S.guide_placeholder;
    $(".guide-form .btn", panel).textContent = S.guide_send;
    log.textContent = "";
    log.append(el("p", "guide-msg guide-bot", S.guide_intro));
  }

  function open(show) {
    panel.hidden = !show;
    fab.setAttribute("aria-expanded", String(show));
    panel.classList.toggle("enter", show);
    if (show) input.focus(); else fab.focus();
  }

  function addReply(data) {
    const box = el("div", "guide-msg guide-bot");
    box.append(el("p", "", data.message));
    if (data.verify_hint) {
      const a = el("a", "guide-verify", data.verify_hint);
      a.href = "#verify";
      a.addEventListener("click", () => { $("#input").value = data.question; open(false); });
      box.append(a);
    }
    for (const l of data.lessons) {
      const card = el("a", "guide-lesson");
      card.href = l.href;
      card.append(el("span", "guide-lesson-title", l.lesson), el("span", "guide-lesson-path small muted", `${l.path} › ${l.module}`));
      const ex = el("span", "guide-lesson-excerpt small", l.excerpt);
      ex.lang = "ar"; ex.dir = "rtl";
      card.append(ex);
      card.addEventListener("click", () => { if (window.matchMedia("(max-width: 640px)").matches) open(false); });
      box.append(card);
    }
    log.append(box);
    box.classList.add("enter");
    log.scrollTop = log.scrollHeight;
  }

  async function ask(e) {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;
    log.append(el("p", "guide-msg guide-user", question));
    input.value = "";
    const waiting = el("p", "guide-msg guide-bot muted", S.guide_searching);
    log.append(waiting);
    log.scrollTop = log.scrollHeight;
    try {
      const res = await fetch("/api/guide", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, lang: LANG }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      data.question = question;
      waiting.remove();
      addReply(data);
    } catch (err) {
      waiting.textContent = S.guide_error;
    }
  }

  fab.addEventListener("click", () => open(panel.hidden));
  // Minimize keeps the conversation; close clears it.
  $(".guide-min", panel).addEventListener("click", () => open(false));
  $(".guide-x", panel).addEventListener("click", () => { open(false); applyGuideStrings(); });
  document.addEventListener("click", e => {  // clicking outside the panel minimizes it
    if (!panel.hidden && !panel.contains(e.target) && !fab.contains(e.target)) open(false);
  });
  panel.addEventListener("keydown", e => { if (e.key === "Escape") open(false); });
  $(".guide-form", panel).addEventListener("submit", ask);
  document.addEventListener("langchange", applyGuideStrings);

  window.appReady.then(() => {
    applyGuideStrings();
    document.body.append(panel, fab);
  });
})();
