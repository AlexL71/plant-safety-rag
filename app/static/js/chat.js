/* DocAgent user chat. */
"use strict";

/* [label key in i18n.js, question]; the questions stay as written: they show the cross-language search */
const EXAMPLES = [
  ["ex.1", "안전밸브는 어떤 설비에 설치해야 하나요?"],
  ["ex.2", "공정위험성평가는 몇 년마다 다시 해야 하나요?"],
  ["ex.3", "How long must completed work permits be kept?"],
  ["ex.4", "What must a pre-startup safety review confirm before highly hazardous chemicals are introduced?"],
];
const FINISH_PAUSE_MS = 900;  // how long the all-green checklist stays visible before the answer
const FADE_MS = 180;          // checklist fade-out before the answer appears
const LANGS = ["auto", "ko", "en"];  // answer language: auto = same language as the question
const STAGES = ["condense", "translate", "search", "rerank", "answer"];  // labels: "stage.<name>" in i18n.js

const $ = (id) => document.getElementById(id);
const viewer = new DA.Viewer();
const popover = new DA.Popover((p) => viewer.open({ chunk_id: p.chunk_id }));
let current = null;     // current chat id (null = new, not created yet)
let busy = false;
let maxChats = 50;
let answerLang = "auto";
try { if (LANGS.includes(localStorage.getItem("da_lang"))) answerLang = localStorage.getItem("da_lang"); } catch (_) {}

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

/* Assistant message: starts as a progress list, then becomes the answer. */
function addBot() {
  const wrap = document.createElement("div");
  wrap.className = "msg-bot";
  wrap.innerHTML = `<img class="av" src="/brand/docagent_icon.svg" alt="DocAgent"><div class="bubble"></div>`;
  $("thread").appendChild(wrap);
  const bubble = wrap.querySelector(".bubble");
  const seen = [];
  const t0 = Date.now();
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
    const order = STAGES.filter((s) => seen.includes(s) || ["search", "rerank", "answer"].includes(s));
    const active = finished ? null : seen.length ? seen[seen.length - 1] : order[0];  // first step runs before any event
    order.forEach((s, i) => {
      let row = list.querySelector(`[data-stage="${s}"]`);
      if (!row) {  // optional steps (follow-up, translation) appear when the server reports them
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
    const secs = ((Date.now() - t0) / 1000).toFixed(0);
    if (finished) {
      list.classList.add("finished");
      bubble.querySelector(".meta-line").innerHTML = `<span class="chip ok">${DA.t("steps.done", { s: secs })}</span>`;
    } else {
      setText(bubble.querySelector(".elapsed"), DA.t("steps.secs", { s: secs }));
      setText(bubble.querySelector(".note"), DA.t("steps.scope"));
    }
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
      bubble.classList.add("reveal");
      const passages = m.passages || {};
      const lang = DA.t(m.lang === "ko" ? "lang.ko" : "lang.en");
      const nSrc = Object.keys(passages).length;
      if (m.refused) {
        bubble.classList.add("refused");
        bubble.innerHTML = `<div class="refused-head"><span class="chip muted">${DA.t("ref.head")}</span></div>
          <div class="answer">${DA.renderAnswer(m.text, {})}</div>
          <div class="meta-line">${DA.t("ref.note")}</div>`;
      } else {
        bubble.innerHTML = `<div class="answer">${DA.renderAnswer(m.text, passages)}</div>
          <div class="meta-line"><span class="chip">${DA.t(nSrc === 1 ? "ans.source1" : "ans.sourceN", { n: nSrc })}</span>
          <span>${DA.t("ans.in", { lang })}${m.total_s ? ` · ${DA.t("steps.secs", { s: Math.round(m.total_s) })}` : ""}</span>
          ${m.standalone ? `<span title="${DA.esc(DA.t("ans.readAsTitle"))}">${DA.t("ans.readAs", { q: DA.esc(m.standalone) })}</span>` : ""}</div>`;
        popover.attach(bubble, passages);
      }
    },
    error(msg) {
      clearInterval(timer);
      bubble.classList.add("refused");
      bubble.innerHTML = `<div class="refused-head"><span class="chip bad">${DA.t("err.head")}</span></div><div>${DA.esc(msg)}</div>`;
    },
  };
}

/* ---------------------------------------------------------------- asking */
async function ask(question) {
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
    const bot = addBot();
    bot.start();
    scrollDown();
    let shown = null;  // finishes after the checklist pause and the answer render
    try {
      await DA.stream(`/api/chats/${current}/ask`, { question, lang: answerLang }, (ev) => {
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

/* Answer language picker (remembered in this browser). */
function setLang(lang) {
  answerLang = lang;
  try { localStorage.setItem("da_lang", lang); } catch (_) {}
  document.querySelectorAll("#langSeg button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
}
document.querySelectorAll("#langSeg button").forEach((b) => { b.onclick = () => setLang(b.dataset.lang); });
setLang(answerLang);

function renderExamples() {
  $("examples").innerHTML = EXAMPLES.map(([key, q]) => `<button class="ex" type="button"><small>${DA.esc(DA.t(key))}</small>${DA.esc(q)}</button>`).join("");
  $("examples").querySelectorAll(".ex").forEach((b, i) => { b.onclick = () => ask(EXAMPLES[i][1]); });
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
  if (!current) $("chatTitle").textContent = DA.t("chat.new");
  else if (!busy) openChat(current);
});

renderExamples();
pollStatus();
loadChats();
if (!current) $("chatTitle").textContent = DA.t("chat.new");
// Deep links: /chat?q=<question> asks it in a new chat; /chat?source=<chunk_id> opens that passage
const params = new URLSearchParams(location.search);
if (params.get("source")) viewer.open({ chunk_id: params.get("source") });
if (params.get("q")) {
  history.replaceState(null, "", "/chat");  // don't ask again on reload
  ask(params.get("q").slice(0, 1000));
}
