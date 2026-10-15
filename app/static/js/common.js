/* SafetyAgent shared front-end: API helpers, safe answer rendering, citation pop-overs, document viewer. */
"use strict";

const DA = {};

/* ---------------------------------------------------------------- API */
DA.api = async function (path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (_) { /* empty body */ }
  if (!res.ok) {
    const err = new Error((data && data.detail) || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
};

/* POST that answers with Server-Sent Events: calls onEvent({type, ...}) for each event. */
DA.stream = async function (path, body, onEvent) {
  const res = await fetch(path, {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try { detail = (await res.json()).detail || detail; } catch (_) { /* not JSON */ }
    const err = new Error(detail); err.status = res.status; throw err;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (line) onEvent(JSON.parse(line.slice(6)));
    }
  }
};

/* ---------------------------------------------------------------- text helpers */
DA.esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

DA.pages = (p) => p.page_start === p.page_end ? `p. ${p.page_start}` : `pp. ${p.page_start}–${p.page_end}`;

DA.timeAgo = function (ts) {
  const s = Date.now() / 1000 - ts;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return new Date(ts * 1000).toLocaleDateString();
};

/* Inline formatting on escaped text: **bold**, `code`, and [n] / [1, 2] citations. */
function inline(text, passages) {
  let h = DA.esc(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
  return h.replace(/\[(\d+(?:\s*,\s*\d+)*)\]/g, (_, nums) => nums.split(/\s*,\s*/).map((n) =>
    passages && passages[n]
      ? `<button type="button" class="cite" data-n="${n}" aria-label="${DA.t("cite.aria", { n })}">${n}</button>`
      : `<sup class="muted">${n}</sup>`).join(""));
}

/* Small, safe Markdown renderer for answers (escapes everything first; no raw HTML from the model). */
DA.renderAnswer = function (text, passages) {
  const lines = String(text || "").replace(/\r/g, "").split("\n");
  let html = "", list = null, para = [];
  const flushPara = () => { if (para.length) { html += `<p>${inline(para.join(" "), passages)}</p>`; para = []; } };
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
  for (const raw of lines) {
    const line = raw.trim();
    const ul = line.match(/^[-*•]\s+(.*)$/);
    const ol = line.match(/^(\d+)[.)]\s+(.*)$/);
    if (!line) { flushPara(); closeList(); continue; }
    if (ul || ol) {
      flushPara();
      const kind = ul ? "ul" : "ol";
      if (list !== kind) {
        closeList();
        // keep the model's numbering when a numbered list is split by bullets ("1. … - … 2. …")
        const start = ol && Number(ol[1]) > 1 ? ` start="${Number(ol[1])}"` : "";
        html += `<${kind}${start}>`;
        list = kind;
      }
      html += `<li>${inline(ul ? ul[1] : ol[2], passages)}</li>`;
      continue;
    }
    closeList();
    para.push(line);
  }
  flushPara(); closeList();
  return html;
};

/* ---------------------------------------------------------------- citation pop-over */
DA.Popover = class {
  constructor(onOpen) {
    this.onOpen = onOpen;           // called with (passage) when the user wants the full document
    this.el = document.createElement("div");
    this.el.className = "popover";
    this.el.hidden = true;
    document.body.appendChild(this.el);
    this.hideTimer = null;
    this.el.addEventListener("mouseenter", () => clearTimeout(this.hideTimer));
    this.el.addEventListener("mouseleave", () => this.hideSoon());
    document.addEventListener("scroll", () => this.hide(), true);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") this.hide(); });
  }
  /* Wire every .cite inside `root` to the passages map {n: passage}. */
  attach(root, passages) {
    root.querySelectorAll(".cite").forEach((btn) => {
      const p = passages[btn.dataset.n];
      if (!p) return;
      btn.addEventListener("mouseenter", () => this.show(btn, p));
      btn.addEventListener("focus", () => this.show(btn, p));
      btn.addEventListener("mouseleave", () => this.hideSoon());
      btn.addEventListener("click", (e) => { e.preventDefault(); this.hide(); this.onOpen(p); });
    });
  }
  show(anchor, p) {
    clearTimeout(this.hideTimer);
    this.el.innerHTML = `
      <div class="pop-title">${DA.esc(p.title)}</div>
      <div class="pop-meta">${DA.esc(p.clause_id)} · ${DA.pages(p)} · ${DA.t(`lang.${p.lang === "ko" ? "ko" : "en"}`)}</div>
      <div class="pop-text">${DA.esc(p.text)}</div>
      <div class="pop-foot"><span class="small muted">${DA.t("pop.source", { n: p.n })}</span>
        <button class="btn btn-ghost btn-sm" type="button">${DA.t("pop.open")}</button></div>`;
    this.el.querySelector("button").onclick = () => { this.hide(); this.onOpen(p); };
    this.el.hidden = false;
    const r = anchor.getBoundingClientRect(), w = this.el.offsetWidth, h = this.el.offsetHeight;
    let left = Math.min(Math.max(12, r.left - 24), window.innerWidth - w - 12);
    let top = r.bottom + 8;
    if (top + h > window.innerHeight - 12) top = Math.max(12, r.top - h - 8);
    Object.assign(this.el.style, { left: `${left}px`, top: `${top}px` });
  }
  hideSoon() { clearTimeout(this.hideTimer); this.hideTimer = setTimeout(() => this.hide(), 180); }
  hide() { this.el.hidden = true; }
};

/* ---------------------------------------------------------------- document viewer */
/* Merge consecutive line boxes of a passage into blocks: same page, vertical gap under ~2 line heights
   (so paragraphs of one clause become one outline), and overlapping x-ranges (so two columns stay apart). */
function groupBoxes(boxes) {
  const blocks = [];
  let lineH = 12;
  for (const [page, x0, y0, x1, y1] of boxes) {
    const last = blocks[blocks.length - 1];
    if (last && last.page === page && y0 - last.y1 < Math.max(14, 2.2 * lineH) && x0 < last.x1 && x1 > last.x0) {
      last.x0 = Math.min(last.x0, x0); last.y0 = Math.min(last.y0, y0);
      last.x1 = Math.max(last.x1, x1); last.y1 = Math.max(last.y1, y1);
    } else {
      blocks.push({ page, x0, y0, x1, y1 });
    }
    lineH = Math.max(6, y1 - y0);
  }
  return blocks;
}

DA.Viewer = class {
  constructor() {
    this.backdrop = document.createElement("div");
    this.backdrop.className = "viewer-backdrop";
    this.el = document.createElement("aside");
    this.el.className = "viewer";
    this.el.setAttribute("aria-label", DA.t("viewer.aria"));
    this.el.innerHTML = `
      <div class="viewer-head">
        <div><div class="v-title"></div><div class="v-meta"></div></div>
        <button class="v-close" type="button" aria-label="${DA.t("viewer.close")}">×</button>
      </div>
      <div class="viewer-tools"></div>
      <div class="viewer-body"></div>`;
    document.body.append(this.backdrop, this.el);
    this.el.querySelector(".v-close").onclick = () => this.close();
    this.backdrop.onclick = () => this.close();
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") this.close(); });
    this.token = 0;
  }
  close() { this.el.classList.remove("open"); this.backdrop.classList.remove("open"); }

  /* Open a document; with a passage, outline it and scroll to it. */
  async open({ doc_id, chunk_id = null, page = 1 }) {
    const token = ++this.token;
    this.el.classList.add("open"); this.backdrop.classList.add("open");
    const body = this.el.querySelector(".viewer-body");
    body.innerHTML = `<div class="muted small" style="display:flex;gap:10px;align-items:center"><div class="spinner"></div>${DA.t("viewer.opening")}</div>`;
    let passage = null;
    if (chunk_id) passage = await DA.api(`/api/passages/${encodeURIComponent(chunk_id)}`);
    const docId = passage ? passage.doc_id : doc_id;
    const doc = await DA.api(`/api/docs/${encodeURIComponent(docId)}`);
    if (token !== this.token) return;

    this.el.querySelector(".v-title").textContent = doc.title;
    this.el.querySelector(".v-meta").textContent = passage
      ? `${passage.clause_id} · ${DA.pages(passage)} · ${DA.t("viewer.pages", { n: doc.pages.length })}`
      : `${DA.t("viewer.pages", { n: doc.pages.length })} · ${DA.t(`lang.${doc.lang === "ko" ? "ko" : "en"}`)}`;
    this.el.querySelector(".viewer-tools").innerHTML = passage
      ? `<span class="chip accent">${DA.t("viewer.outlined")}</span>`
      : `<span class="chip muted">${DA.t("viewer.whole")}</span>`;

    const blocks = passage ? groupBoxes(passage.boxes || []) : [];
    const pagesWithHl = new Set(blocks.map((b) => b.page));
    body.innerHTML = "";
    doc.pages.forEach(([w, h], i) => {
      const n = i + 1;
      const div = document.createElement("div");
      div.className = "page";
      div.id = `vp-${n}`;
      div.style.aspectRatio = `${w} / ${h}`;
      div.innerHTML = `<img alt="${DA.t("viewer.pageAlt", { n })}" loading="${pagesWithHl.has(n) || Math.abs(n - page) < 2 ? "eager" : "lazy"}"
                         src="/api/docs/${encodeURIComponent(docId)}/pages/${n}.png"><span class="pno">${n}</span>`;
      for (const b of blocks.filter((b) => b.page === n)) {
        const pad = 3, hl = document.createElement("div");
        hl.className = "hl flash";
        Object.assign(hl.style, {
          left: `${((b.x0 - pad) / w) * 100}%`, top: `${((b.y0 - pad) / h) * 100}%`,
          width: `${((b.x1 - b.x0 + 2 * pad) / w) * 100}%`, height: `${((b.y1 - b.y0 + 2 * pad) / h) * 100}%`,
        });
        div.appendChild(hl);
      }
      body.appendChild(div);
    });
    const target = blocks.length ? blocks[0] : null;
    setTimeout(() => {  // after layout (a timer also runs in background tabs, unlike requestAnimationFrame)
      const pageEl = body.querySelector(`#vp-${target ? target.page : page}`);
      if (!pageEl) return;
      const offset = target ? (target.y0 / doc.pages[target.page - 1][1]) * pageEl.offsetHeight - 80 : 0;
      body.scrollTop = pageEl.offsetTop - body.offsetTop + Math.max(0, offset);
    }, 60);
  }
};
