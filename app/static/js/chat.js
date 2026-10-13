/* DocAgent user chat. */
"use strict";

const EXAMPLES = [
  ["Korean regulation", "안전밸브는 어떤 설비에 설치해야 하나요?"],
  ["Korean → US standard", "공정위험성평가는 몇 년마다 다시 해야 하나요?"],
  ["English → Korean guide", "How long must completed work permits be kept?"],
  ["US PSM", "What must a pre-startup safety review confirm before highly hazardous chemicals are introduced?"],
];
const FINISH_PAUSE_MS = 900;  // how long the all-green checklist stays visible before the answer
const STAGES = {
  condense: "Understanding your follow-up",
  translate: "Translating the question (KO ↔ EN)",
  search: "Searching the documents",
  rerank: "Re-reading the best passages",
  answer: "Writing the answer with citations",
};

const $ = (id) => document.getElementById(id);
const viewer = new DA.Viewer();
const popover = new DA.Popover((p) => viewer.open({ chunk_id: p.chunk_id }));
let current = null;     // current chat id (null = new, not created yet)
let busy = false;
let maxChats = 50;

/* ---------------------------------------------------------------- sidebar */
async function loadChats() {
  const data = await DA.api("/api/chats");
  maxChats = data.max;
  const list = $("chatList");
  list.innerHTML = data.chats.length ? "" : `<div class="small muted" style="padding:8px 12px">No chats yet.</div>`;
  for (const c of data.chats) {
    const item = document.createElement("div");
    item.className = "chat-item" + (c.id === current ? " active" : "");
    item.innerHTML = `<span class="t" title="${DA.esc(c.title)}">${DA.esc(c.title)}</span>
                      <button class="del" type="button" aria-label="Delete chat">✕</button>`;
    item.onclick = () => openChat(c.id);
    item.querySelector(".del").onclick = async (e) => {
      e.stopPropagation();
      if (!confirm("Delete this chat?")) return;
      await DA.api(`/api/chats/${c.id}`, { method: "DELETE" });
      if (c.id === current) newChat();
      loadChats();
    };
    list.appendChild(item);
  }
  $("chatCount").textContent = `${data.chats.length} / ${maxChats} chats`;
  $("chatMeter").style.width = `${Math.min(100, (100 * data.chats.length) / maxChats)}%`;
}

function newChat() {
  current = null;
  $("thread").innerHTML = "";
  $("emptyState").hidden = false;
  $("chatTitle").textContent = "New chat";
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

  /* finished = true: every step shows a green check (shown briefly before the answer appears). */
  function renderSteps(finished = false) {
    const order = Object.keys(STAGES).filter((s) => seen.includes(s) || ["search", "rerank", "answer"].includes(s));
    const active = finished ? null : seen.length ? seen[seen.length - 1] : order[0];  // first step runs before any event
    const secs = ((Date.now() - t0) / 1000).toFixed(0);
    bubble.innerHTML = `<div class="steps ${finished ? "finished" : ""}">${order.map((s) => {
      const state = finished || (seen.includes(s) && s !== active) ? "done" : s === active ? "now" : "todo";
      const icon = state === "now" ? `<div class="spinner"></div>` : state === "done" ? `<span class="ck">✓</span>` : `<span class="dot"></span>`;
      return `<div class="step ${state}">${icon}<span>${STAGES[s]}</span></div>`;
    }).join("")}</div><div class="meta-line">${finished
      ? `<span class="chip ok">✓ Done in ${secs} s</span>`
      : `<span>${secs} s</span><span>· searching ~1,155 clauses in 10 documents</span>`}</div>`;
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
        await new Promise((r) => setTimeout(r, FINISH_PAUSE_MS));
      }
      bubble.classList.add("reveal");
      const passages = m.passages || {};
      const lang = m.lang === "ko" ? "Korean" : "English";
      if (m.refused) {
        bubble.classList.add("refused");
        bubble.innerHTML = `<div class="refused-head"><span class="chip muted">Not found</span></div>
          <div class="answer">${DA.renderAnswer(m.text, {})}</div>
          <div class="meta-line">The documents searched don't answer this. Try rephrasing, or ask about a related clause.</div>`;
      } else {
        bubble.innerHTML = `<div class="answer">${DA.renderAnswer(m.text, passages)}</div>
          <div class="meta-line"><span class="chip">${Object.keys(passages).length} source${Object.keys(passages).length === 1 ? "" : "s"}</span>
          <span>Answered in ${lang}${m.total_s ? ` · ${Math.round(m.total_s)} s` : ""}</span>
          ${m.standalone ? `<span title="Your follow-up was read as this question">· read as: “${DA.esc(m.standalone)}”</span>` : ""}</div>`;
        popover.attach(bubble, passages);
      }
    },
    error(msg) {
      clearInterval(timer);
      bubble.classList.add("refused");
      bubble.innerHTML = `<div class="refused-head"><span class="chip bad">Error</span></div><div>${DA.esc(msg)}</div>`;
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
    if (!current) {
      const chat = await DA.api("/api/chats", { method: "POST" });
      current = chat.id;
    }
    addUser(question);
    $("chatTitle").textContent = $("chatTitle").textContent === "New chat" ? question.slice(0, 70) : $("chatTitle").textContent;
    setTimeout(loadChats, 400);  // show the new chat in the sidebar while the answer is prepared
    const bot = addBot();
    bot.start();
    scrollDown();
    let shown = null;  // finishes after the checklist pause and the answer render
    try {
      await DA.stream(`/api/chats/${current}/ask`, { question }, (ev) => {
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

$("examples").innerHTML = EXAMPLES.map(([tag, q]) => `<button class="ex" type="button"><small>${DA.esc(tag)}</small>${DA.esc(q)}</button>`).join("");
$("examples").querySelectorAll(".ex").forEach((b, i) => { b.onclick = () => ask(EXAMPLES[i][1]); });

async function pollStatus() {
  try {
    const s = await DA.api("/api/status");
    $("status").innerHTML = s.ready
      ? `<span class="chip ok">● Ready · ${s.documents} documents</span>`
      : s.error ? `<span class="chip bad">Engine error</span>` : `<span class="chip warn"><span class="spinner"></span>Starting up…</span>`;
    if (!s.ready && !s.error) setTimeout(pollStatus, 2000);
  } catch (_) { setTimeout(pollStatus, 4000); }
}
pollStatus();
loadChats();
// Deep links: /chat?q=<question> asks it in a new chat; /chat?source=<chunk_id> opens that passage
const params = new URLSearchParams(location.search);
if (params.get("source")) viewer.open({ chunk_id: params.get("source") });
if (params.get("q")) {
  history.replaceState(null, "", "/chat");  // don't ask again on reload
  ask(params.get("q").slice(0, 1000));
}
