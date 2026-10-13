/* SafetyAgent user chat: the agent answers, explains with visuals, compares Korea vs US, plans a job, drafts notices. */
"use strict";

/* [label key in i18n.js, request, mode]; the requests stay as written: they show the agent's tools and the
   cross-language search */
const EXAMPLES = [
  ["ex.1", "밀폐공간 작업 시 적정공기 기준은 무엇인가요?", "auto"],
  ["ex.2", "Show the safe air limits for confined-space work as a chart", "auto"],
  ["ex.3", "Compare Korea and the US: from what height is fall protection required?", "auto"],
  ["ex.4", "내일 탱크 내부에서 용접 작업을 합니다. 무엇을 준비하고 점검해야 하나요?", "auto"],
  ["ex.5", "Make a poster about forklift safety for our warehouse", "auto"],
  ["ex.6", "How long must a fire watch continue after welding?", "auto"],
];
const FINISH_PAUSE_MS = 900;  // how long the all-green checklist stays visible before the answer
const FADE_MS = 180;          // checklist fade-out before the answer appears
const LANGS = ["auto", "ko", "en"];  // answer language: auto = same language as the question
// every stage the server can report, in display order; labels: "stage.<name>" in i18n.js
const STAGES = ["route", "condense", "plan", "translate", "search", "rerank", "answer", "visual", "notice", "check"];
const DEFAULT_STAGES = {   // shown (waiting) from the start, per mode; others appear when reported
  auto: ["route", "search", "rerank", "answer"],
  answer: ["search", "rerank", "answer"],
  visual: ["search", "rerank", "answer", "visual"],
  compare: ["search", "rerank", "answer", "visual"],
  task_plan: ["plan", "search", "answer", "check"],
  notice: ["search", "rerank", "notice"],
};
const INTENT_ICON = { answer: "💬", visual: "📊", compare: "⚖️", task_plan: "🧰", notice: "📄", chitchat: "👋" };

const $ = (id) => document.getElementById(id);
const viewer = new DA.Viewer();
const popover = new DA.Popover((p) => viewer.open({ chunk_id: p.chunk_id }));
let current = null;     // current chat id (null = new, not created yet)
let busy = false;
let maxChats = 50;
let answerLang = "auto";
let mode = "auto";
try { if (LANGS.includes(localStorage.getItem("da_lang"))) answerLang = localStorage.getItem("da_lang"); } catch (_) {}
try { if (DEFAULT_STAGES[localStorage.getItem("sa_mode")]) mode = localStorage.getItem("sa_mode"); } catch (_) {}

/* ---------------------------------------------------------------- sidebar */
async function loadChats() {
  const data = await DA.api("/api/chats");
  maxChats = data.max;
  const list = $("chatList");
  list.innerHTML = data.chats.length ? "" : `<div class="small muted" style="padding:8px 12px">${DA.t("chat.none")}</div>`;
  for (const c of data.chats) {
    const item = document.createElement("div");
    item.className = "chat-item" + (c.id === current ? " active" : "");
    item.innerHTML = `<span class="t" title="${DA.esc(c.title)}">${DA.esc(c.title)}</span>
                      <button class="del" type="button" aria-label="${DA.t("chat.deleteAria")}">✕</button>`;
    item.onclick = () => openChat(c.id);
    item.querySelector(".del").onclick = async (e) => {
      e.stopPropagation();
      if (!confirm(DA.t("chat.deleteConfirm"))) return;
      await DA.api(`/api/chats/${c.id}`, { method: "DELETE" });
      if (c.id === current) newChat();
      loadChats();
    };
    list.appendChild(item);
  }
  $("chatCount").textContent = DA.t("chat.count", { n: data.chats.length, max: maxChats });
  $("chatMeter").style.width = `${Math.min(100, (100 * data.chats.length) / maxChats)}%`;
}

function newChat() {
  current = null;
  $("thread").innerHTML = "";
  $("emptyState").hidden = false;
  $("chatTitle").textContent = DA.t("chat.new");
  document.querySelectorAll(".chat-item.active").forEach((el) => el.classList.remove("active"));
  $("input").focus();
}

async function openChat(id) {
  if (busy) return;
  const data = await DA.api(`/api/chats/${id}`);
  current = id;
  $("emptyState").hidden = true;
  $("thread").innerHTML = "";
  $("chatTitle").textContent = data.chat.title;
  for (const m of data.messages) {
    if (m.role === "user") addUser(m.text);
    else if (m.error) addBot().error(m.text);
    else addBot().done(m);
  }
  loadChats();
  scrollDown();
}

/* ---------------------------------------------------------------- messages */
const setText = (el, text) => { if (el && el.textContent !== text) el.textContent = text; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function scrollDown() { const s = $("scroll"); s.scrollTop = s.scrollHeight; }

function addUser(text) {
  const div = document.createElement("div");
  div.className = "msg-user";
  div.textContent = text;
  $("thread").appendChild(div);
}

/* The parts of a finished assistant message, by kind (answer / plan / notice / chat / refused). */
function messageHtml(m) {
  const passages = m.passages || {};
  const nSrc = Object.keys(passages).length;
  const lang = DA.t(m.lang === "ko" ? "lang.ko" : "lang.en");
  const routed = m.intent && m.intent !== "answer"
    ? `<span class="chip accent" title="${DA.esc(DA.t("agent.routedTitle", { r: m.route_reason || "" }))}">${INTENT_ICON[m.intent] || ""} ${DA.t(`mode.${m.intent}`)}</span>` : "";
  const meta = `<div class="meta-line">${routed}<span class="chip">${DA.t(nSrc === 1 ? "ans.source1" : "ans.sourceN", { n: nSrc })}</span>
      <span>${DA.t("ans.in", { lang })}${m.total_s ? ` · ${DA.t("steps.secs", { s: Math.round(m.total_s) })}` : ""}</span>
      ${m.standalone ? `<span title="${DA.esc(DA.t("ans.readAsTitle"))}">${DA.t("ans.readAs", { q: DA.esc(m.standalone) })}</span>` : ""}</div>`;
  if (m.kind === "chat") {
    return { cls: "", html: `<div class="answer">${DA.renderAnswer(m.text, {})}</div>` };
  }
  if (m.refused) {
    return { cls: "refused", html: `<div class="refused-head"><span class="chip muted">${DA.t("ref.head")}</span>${routed}</div>
      <div class="answer">${DA.renderAnswer(m.text, {})}</div><div class="meta-line">${DA.t("ref.note")}</div>` };
  }
  if (m.kind === "plan" && m.plan) {
    return { cls: "wide", html: `${DA.renderPlan(m.plan, passages)}${meta}
      <div class="actions"><button class="btn btn-ghost btn-sm" data-act="print">🖨 ${DA.t("act.print")}</button>
      <button class="btn btn-ghost btn-sm" data-act="tbm">📄 ${DA.t("act.tbm")}</button></div>` };
  }
  if (m.kind === "notice") {
    return { cls: "", html: `<div class="notice-card"><div class="nc-ico">📄</div><div><div class="nc-kicker">${DA.t("notice.drafted")}</div>
        <div class="nc-title">${DA.esc(m.text)}</div><div class="small muted">${DA.t("notice.draftedNote")}</div></div>
        ${m.notice_id ? `<a class="btn btn-primary btn-sm" href="/notices?id=${encodeURIComponent(m.notice_id)}">${DA.t("notice.open")} →</a>` : ""}</div>${meta}` };
  }
  return { cls: m.visual ? "wide" : "", html: `<div class="answer">${DA.renderAnswer(m.text, passages)}</div>
      ${m.visual ? DA.renderVisual(m.visual, passages) : ""}${meta}
      <div class="actions">${m.visual ? "" : `<button class="btn btn-ghost btn-sm" data-act="visual">📊 ${DA.t("act.visual")}</button>`}
      <button class="btn btn-ghost btn-sm" data-act="notice">📄 ${DA.t("act.notice")}</button></div>` };
}

/* Assistant message: starts as a progress list, then becomes the answer. */
function addBot(msgMode = "auto") {
  const wrap = document.createElement("div");
  wrap.className = "msg-bot";
  wrap.innerHTML = `<img class="av" src="/brand/safetyagent_icon.svg" alt="SafetyAgent"><div class="bubble"></div>`;
  $("thread").appendChild(wrap);
  const bubble = wrap.querySelector(".bubble");
  const seen = [];
  const t0 = Date.now();
  const defaults = DEFAULT_STAGES[msgMode] || DEFAULT_STAGES.auto;
  let timer = null;

  /* The step list is built once and then only updated in place (class changes, new rows), so spinners keep
     turning and nothing flickers. finished = true: every step gets a green check before the answer appears. */
  function renderSteps(finished = false) {
    let list = bubble.querySelector(".steps");
    const firstRender = !list;
    if (firstRender) {
      bubble.innerHTML = `<div class="steps"></div><div class="meta-line"><span class="elapsed">0 s</span>
        <span class="note"></span></div>`;
      list = bubble.querySelector(".steps");
    }
    const order = STAGES.filter((s) => seen.includes(s) || (defaults.includes(s) && !finished) || (finished && seen.includes(s)));
    const active = finished ? null : seen.length ? seen[seen.length - 1] : order[0];  // first step runs before any event
    order.forEach((s, i) => {
      let row = list.querySelector(`[data-stage="${s}"]`);
      if (!row) {  // optional steps (follow-up, translation, plan, visual ...) appear when the server reports them
        row = document.createElement("div");
        row.className = "step todo" + (firstRender ? "" : " enter");
        row.dataset.stage = s;
        row.innerHTML = `<span class="ic"><span class="dot"></span><span class="spinner"></span><span class="ck">✓</span></span>
                         <span class="lbl"></span>`;
        list.insertBefore(row, list.children[i] || null);
      }
      const state = finished || (seen.includes(s) && s !== active) ? "done" : s === active ? "now" : "todo";
      if (!row.classList.contains(state)) { row.classList.remove("todo", "now", "done"); row.classList.add(state); }
      setText(row.querySelector(".lbl"), DA.t(`stage.${s}`));  // follows an interface-language switch
    });
    if (finished) list.querySelectorAll(".step").forEach((r) => { if (!order.includes(r.dataset.stage)) r.remove(); });
    const secs = ((Date.now() - t0) / 1000).toFixed(0);
    if (finished) {
      list.classList.add("finished");
      bubble.querySelector(".meta-line").innerHTML = `<span class="chip ok">${DA.t("steps.done", { s: secs })}</span>`;
    } else {
      setText(bubble.querySelector(".elapsed"), DA.t("steps.secs", { s: secs }));
      setText(bubble.querySelector(".note"), DA.t("steps.scope"));
    }
  }

  function show(m) {
    const { cls, html } = messageHtml(m);
    bubble.className = `bubble reveal ${cls}`;
    bubble.innerHTML = html;
    popover.attach(bubble, m.passages || {});
    wireActions(bubble, m);
  }

  return {
    start() { renderSteps(); timer = setInterval(renderSteps, 1000); },
    stage(s) { if (!seen.includes(s)) seen.push(s); renderSteps(); scrollDown(); },
    /* Live answers first show all steps checked for a moment; answers loaded from history appear at once. */
    async done(m) {
      if (timer) {
        clearInterval(timer);
        timer = null;
        renderSteps(true);
        scrollDown();
        await sleep(FINISH_PAUSE_MS);
        bubble.classList.add("leaving");  // fade the checklist out, then fade the answer in
        await sleep(FADE_MS);
        bubble.classList.remove("leaving");
      }
      show(m);
    },
    error(msg) {
      clearInterval(timer);
      bubble.className = "bubble refused";
      bubble.innerHTML = `<div class="refused-head"><span class="chip bad">${DA.t("err.head")}</span></div><div>${DA.esc(msg)}</div>`;
    },
    show,
  };
}

/* Buttons under an answer: make a visual from the same sources, or turn it into a notice / TBM sheet. */
function wireActions(bubble, m) {
  bubble.querySelectorAll("[data-act]").forEach((btn) => {
    btn.onclick = async () => {
      const act = btn.dataset.act;
      if (act === "print") { printPlan(bubble); return; }
      btn.disabled = true;
      const label = btn.innerHTML;
      btn.innerHTML = `<span class="spinner"></span> ${DA.t("act.working")}`;
      try {
        if (act === "visual") {
          const upd = await DA.api(`/api/messages/${m.id}/visual`, { method: "POST", body: { type: "auto" } });
          const { cls, html } = messageHtml(upd);
          bubble.className = `bubble reveal ${cls}`;
          bubble.innerHTML = html;
          popover.attach(bubble, upd.passages || {});
          wireActions(bubble, upd);
        } else {  // notice / tbm: draft from this message's evidence, then open the editor
          let id = null, err = null;
          await DA.stream("/api/notices", { message_id: m.id, lang: m.lang === "en" ? "en" : "ko",
                                           template: act === "tbm" ? "tbm" : "poster" }, (ev) => {
            if (ev.type === "done") id = ev.notice.id;
            else if (ev.type === "error") err = ev.detail;
          });
          if (err) throw new Error(err);
          location.href = `/notices?id=${encodeURIComponent(id)}`;
        }
      } catch (e) {
        btn.innerHTML = label;
        btn.disabled = false;
        alert(e.message);
      }
    };
  });
}

function printPlan(bubble) {
  const w = window.open("", "_blank");
  if (!w) return;
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>SafetyAgent</title>
    <link rel="stylesheet" href="/static/css/safetyagent.css"><style>body{background:#fff;padding:24px}.cite{border:none;background:none;color:#555;font-size:11px}
    .vis{border:none}</style></head><body>${bubble.querySelector(".vis").outerHTML}</body></html>`);
  w.document.close();
  setTimeout(() => w.print(), 300);
}

/* ---------------------------------------------------------------- asking */
async function ask(question, askMode = mode) {
  if (busy || !question.trim()) return;
  busy = true;
  $("send").disabled = true;
  $("emptyState").hidden = true;
  try {
    const isNewChat = !current;
    if (!current) {
      const chat = await DA.api("/api/chats", { method: "POST" });
      current = chat.id;
    }
    addUser(question);
    if (isNewChat) $("chatTitle").textContent = question.slice(0, 70);
    setTimeout(loadChats, 400);  // show the new chat in the sidebar while the answer is prepared
    const bot = addBot(askMode);
    bot.start();
    scrollDown();
    let shown = null;  // finishes after the checklist pause and the answer render
    try {
      await DA.stream(`/api/chats/${current}/ask`, { question, lang: answerLang, mode: askMode }, (ev) => {
        if (ev.type === "stage") bot.stage(ev.stage);
        else if (ev.type === "done") shown = bot.done(ev.message);
        else if (ev.type === "error") bot.error(ev.detail);
      });
    } catch (err) {
      bot.error(err.message);
    }
    if (shown) await shown;
    scrollDown();
    loadChats();
  } finally {
    busy = false;
    $("send").disabled = false;
    $("input").focus();
  }
}

/* ---------------------------------------------------------------- composer & start-up */
const input = $("input");
input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = `${Math.min(input.scrollHeight, 180)}px`; });
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("composer").requestSubmit(); }
});
$("composer").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  input.value = ""; input.style.height = "auto";
  ask(q);
});
$("newChat").onclick = newChat;

/* Answer language and agent mode pickers (remembered in this browser). */
function setLang(lang) {
  answerLang = lang;
  try { localStorage.setItem("da_lang", lang); } catch (_) {}
  document.querySelectorAll("#langSeg button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
}
document.querySelectorAll("#langSeg button").forEach((b) => { b.onclick = () => setLang(b.dataset.lang); });
setLang(answerLang);

function setMode(m) {
  mode = DEFAULT_STAGES[m] ? m : "auto";
  try { localStorage.setItem("sa_mode", mode); } catch (_) {}
  document.querySelectorAll("#modeSeg button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
  $("input").placeholder = DA.t(`ph.${mode}`);
}
document.querySelectorAll("#modeSeg button").forEach((b) => { b.onclick = () => setMode(b.dataset.mode); });

function renderExamples() {
  $("examples").innerHTML = EXAMPLES.map(([key, q]) => `<button class="ex" type="button"><small>${DA.esc(DA.t(key))}</small>${DA.esc(q)}</button>`).join("");
  $("examples").querySelectorAll(".ex").forEach((b, i) => { b.onclick = () => ask(EXAMPLES[i][1], EXAMPLES[i][2]); });
}

let lastStatus = null;
function renderStatus() {
  const s = lastStatus;
  if (!s) return;
  $("status").innerHTML = s.ready
    ? `<span class="chip ok">${DA.t("status.ready", { n: s.documents })}</span>`
    : s.error ? `<span class="chip bad">${DA.t("status.error")}</span>`
      : `<span class="chip warn"><span class="spinner"></span>${DA.t("status.starting")}</span>`;
}
async function pollStatus() {
  try {
    lastStatus = await DA.api("/api/status");
    renderStatus();
    if (!lastStatus.ready && !lastStatus.error) setTimeout(pollStatus, 2000);
  } catch (_) { setTimeout(pollStatus, 4000); }
}

/* Interface language switch: redraw everything built in JavaScript. An answer being prepared keeps going;
   its step labels follow on the next tick. */
document.addEventListener("da:lang", () => {
  renderExamples();
  renderStatus();
  loadChats();
  setMode(mode);
  if (!current) $("chatTitle").textContent = DA.t("chat.new");
  else if (!busy) openChat(current);
});

renderExamples();
setMode(mode);
pollStatus();
loadChats();
if (!current) $("chatTitle").textContent = DA.t("chat.new");
// Deep links: /chat?q=<question>[&mode=<mode>] asks it in a new chat; /chat?source=<chunk_id> opens that passage
const params = new URLSearchParams(location.search);
if (params.get("source")) viewer.open({ chunk_id: params.get("source") });
if (params.get("q")) {
  history.replaceState(null, "", "/chat");  // don't ask again on reload
  const m = params.get("mode");
  ask(params.get("q").slice(0, 1000), DEFAULT_STAGES[m] ? m : mode);
}
