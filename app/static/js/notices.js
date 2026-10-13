/* SafetyAgent notice editor: list, draft from a topic, edit in place, second language, print / image / share. */
"use strict";

const $ = (id) => document.getElementById(id);
const viewer = new DA.Viewer();
const SHEET_W = { poster: 794, tbm: 794, leaflet: 559, card: 720 };
const HTML2IMG = "https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/dist/html-to-image.js";
let notices = [], cur = null, dirty = false, status = null;

/* ---------------------------------------------------------------- list */
async function loadList() {
  const data = await DA.api("/api/notices");
  notices = data.notices;
  $("list").innerHTML = notices.length ? notices.map((n) => `<div class="item${cur && n.id === cur.id ? " active" : ""}" data-id="${n.id}">
      <span class="t">${DA.esc(n.title)}</span><span class="m">${statusChip(n.status)}<span>${DA.t(`tpl.${n.template}`)}</span>
      <span>· v${n.version}</span><span>· ${DA.timeAgo(n.updated)}</span></span></div>`).join("")
    : `<div class="small muted" style="padding:8px 12px">${DA.t("notices.none")}</div>`;
  $("list").querySelectorAll(".item").forEach((el) => { el.onclick = () => openNotice(el.dataset.id); });
}

const statusChip = (s) => s === "approved" ? `<span class="chip ok">✓ ${DA.t("notices.approved")}</span>`
  : `<span class="chip warn">${DA.t("notices.draft")}</span>`;

/* ---------------------------------------------------------------- one notice */
async function openNotice(id) {
  if (dirty && !confirm(DA.t("notices.discard"))) return;
  cur = await DA.api(`/api/notices/${encodeURIComponent(id)}`);
  dirty = false;
  history.replaceState(null, "", `/notices?id=${encodeURIComponent(id)}`);
  render();
  loadList();
}

function render() {
  const n = cur;
  $("emptyMain").hidden = !!n;
  $("toolbar").hidden = !n;
  $("checks").hidden = !n;
  if (!n) { $("stageBox").innerHTML = ""; return; }
  $("tTitle").textContent = n.title;
  $("tStatus").innerHTML = statusChip(n.status);
  $("tTpl").innerHTML = (n.templates || []).map((t) => `<option value="${t}"${t === n.template ? " selected" : ""}>${DA.t(`tpl.${t}`)}</option>`).join("");
  $("tLang2").innerHTML = `<option value="none">${DA.t("notices.noSecond")}</option>` + Object.entries(n.langs || {})
    .filter(([k]) => k !== n.lang).map(([k, v]) => `<option value="${k}"${n.translation && n.translation.lang === k ? " selected" : ""}>+ ${DA.esc(v)}</option>`).join("");
  $("bSave").disabled = !dirty;
  [$("tTpl"), $("tLang2"), $("bDel")].forEach((el) => { el.disabled = !n.can_edit; });
  $("stageBox").innerHTML = DA.Notice.render(n, { editable: n.can_edit });
  $("stageBox").querySelectorAll("[data-path]").forEach((el) => el.addEventListener("input", () => { dirty = true; $("bSave").disabled = false; }));
  fit();
  renderChecks();
}

/* Scale the sheet to the preview width (print uses the real size). */
function fit() {
  const box = $("stageBox"), sheet = box.querySelector(".sheet");
  if (!sheet) return;
  const w = SHEET_W[cur.template] || 794, avail = $("preview").clientWidth - 40;
  const s = Math.min(1, avail / w);
  box.style.width = `${w}px`;
  box.style.transform = `scale(${s})`;
  box.style.height = `${sheet.offsetHeight}px`;
  box.style.marginBottom = `${-(1 - s) * sheet.offsetHeight}px`;
  box.style.marginLeft = `${Math.max(0, (avail - w * s) / 2)}px`;
}
window.addEventListener("resize", () => cur && fit());

function renderChecks() {
  const n = cur, warns = n.warnings || [], lc = n.line_checks || [];
  const bad = lc.filter((c) => !c.ok);
  const P = Object.values(n.passages || {});
  $("checks").innerHTML = `
    <div><h3>${DA.t("notices.cNumbers")}</h3><div class="box">${warns.length
      ? `<div class="warnline">⚠ ${DA.t("notices.cWarn", { n: warns.length })}</div><div class="small muted">${DA.t("notices.cWarnNote")}</div>`
      : `<div class="okline">✓ ${DA.t("notices.cOk")}</div><div class="small muted">${DA.t("notices.cOkNote")}</div>`}</div></div>
    ${n.translation ? `<div><h3>${DA.t("notices.cTr")}</h3><div class="box">${bad.length
      ? `<div class="warnline">⚠ ${DA.t("notices.cTrBad", { n: bad.length, t: lc.length })}</div>`
      : `<div class="okline">✓ ${DA.t("notices.cTrOk", { t: lc.length })}</div>`}
      <div class="small muted">${DA.t("notices.cTrNote")}</div>
      <details><summary class="small">${DA.t("notices.cBack")}</summary><div class="small" style="display:grid;gap:4px;margin-top:6px">
        ${lc.map((c) => `<div${c.ok ? "" : ' style="color:var(--bad)"'}>${c.ok ? "✓" : "⚠"} ${DA.esc(c.back)}</div>`).join("")}</div></details></div></div>` : ""}
    <div><h3>${DA.t("notices.cSources")}</h3><div class="box">${P.map((p) => `<div class="src" data-chunk="${p.chunk_id}">[${p.n}] ${DA.esc(p.title)}<br>
      <span class="muted small">${DA.esc(p.clause_id)} · ${DA.pages(p)}</span></div>`).join("") || `<span class="muted">-</span>`}</div></div>
    <div><h3>${DA.t("notices.cApproval")}</h3><div class="box">${n.status === "approved"
      ? `<div class="okline">✓ ${DA.t("notices.approvedBy", { u: DA.esc(n.approved_by), v: n.approved_version })}</div>`
      : `<div class="warnline">${DA.t("notices.needsApproval")}</div><div class="small muted">${DA.t("notices.needsApprovalNote")}</div>`}</div></div>
    <div><h3>${DA.t("notices.cShare")}</h3><div class="box sharebox">${n.status === "approved"
      ? `<img src="/api/qr/notice/${encodeURIComponent(n.id)}.svg" alt=""><input class="input" readonly value="${DA.esc(n.share_url)}">
         <button class="btn btn-ghost btn-sm" id="bCopy" type="button">${DA.t("notices.copy")}</button>`
      : `<span class="small muted">${DA.t("notices.shareAfter")}</span>`}</div></div>`;
  $("checks").querySelectorAll(".src").forEach((el) => { el.onclick = () => viewer.open({ chunk_id: el.dataset.chunk }); });
  const copy = $("bCopy");
  if (copy) copy.onclick = async () => { try { await navigator.clipboard.writeText(n.share_url); copy.textContent = DA.t("notices.copied"); } catch (_) {} };
}

/* ---------------------------------------------------------------- actions */
async function save() {
  const main = DA.Notice.collect($("stageBox"), cur.main);
  cur = await DA.api(`/api/notices/${cur.id}`, { method: "PUT", body: { title: main.title || cur.title, template: cur.template, main } });
  dirty = false;
  render();
  loadList();
}

$("bSave").onclick = () => save().catch((e) => alert(e.message));
$("tTpl").onchange = async () => {
  if (dirty) await save();
  cur = await DA.api(`/api/notices/${cur.id}/template`, { method: "PUT", body: { template: $("tTpl").value } });
  render(); loadList();
};
$("tLang2").onchange = async () => {
  const sel = $("tLang2");
  if (dirty) await save();
  sel.disabled = true;
  $("tStatus").innerHTML = `<span class="chip"><span class="spinner"></span> ${DA.t("notices.translating")}</span>`;
  try {
    cur = await DA.api(`/api/notices/${cur.id}/translate`, { method: "POST", body: { lang2: sel.value } });
  } catch (e) { alert(e.message); }
  render(); loadList();
};
$("bPrint").onclick = () => window.print();
$("bDel").onclick = async () => {
  if (!confirm(DA.t("notices.deleteConfirm"))) return;
  await DA.api(`/api/notices/${cur.id}`, { method: "DELETE" });
  cur = null; dirty = false;
  history.replaceState(null, "", "/notices");
  render(); loadList();
};
$("bPng").onclick = async () => {
  const btn = $("bPng"), sheet = $("stageBox").querySelector(".sheet");
  btn.disabled = true;
  try {
    if (!window.htmlToImage) await new Promise((ok, bad) => {
      const s = document.createElement("script"); s.src = HTML2IMG; s.onload = ok; s.onerror = () => bad(new Error("image library failed to load"));
      document.head.appendChild(s);
    });
    const box = $("stageBox"), t = box.style.transform;
    box.style.transform = "none";
    const url = await window.htmlToImage.toPng(sheet, { pixelRatio: 2, backgroundColor: "#ffffff" });
    box.style.transform = t;
    const a = document.createElement("a");
    a.href = url; a.download = `${cur.title.replace(/[\\/:*?"<>|]+/g, "_")}.png`; a.click();
  } catch (e) { alert(e.message); }
  btn.disabled = false;
};

/* New notice from a topic: searches the documents, drafts, checks; progress streams in. */
$("newForm").onsubmit = async (e) => {
  e.preventDefault();
  const topic = $("topic").value.trim();
  if (!topic) return;
  const prog = $("newProgress"), btn = e.target.querySelector("button[type=submit]");
  prog.hidden = false; btn.disabled = true;
  const t0 = Date.now(), seen = [];
  const draw = () => { prog.innerHTML = `<div><span class="spinner"></span>${DA.t(`stage.${seen[seen.length - 1] || "search"}`)} · ${Math.round((Date.now() - t0) / 1000)} s</div>`; };
  draw();
  const tick = setInterval(draw, 1000);
  try {
    let id = null, err = null;
    await DA.stream("/api/notices", { topic, lang: $("newLang").value, template: $("newTpl").value }, (ev) => {
      if (ev.type === "stage") { seen.push(ev.stage); draw(); }
      else if (ev.type === "done") id = ev.notice.id;
      else if (ev.type === "error") err = ev.detail;
    });
    if (err) throw new Error(err);
    $("topic").value = "";
    await openNotice(id);
  } catch (e2) { alert(e2.message); }
  clearInterval(tick);
  prog.hidden = true; btn.disabled = false;
};

window.addEventListener("beforeunload", (e) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } });
document.addEventListener("da:lang", () => { loadList(); if (cur) render(); fillTemplates(); });

function fillTemplates() {
  $("newTpl").innerHTML = ["poster", "leaflet", "card", "tbm"].map((t) => `<option value="${t}">${DA.t(`tpl.${t}`)}</option>`).join("");
  $("newLang").value = DA.lang === "en" ? "en" : "ko";
}

fillTemplates();
loadList().then(() => {
  const id = new URLSearchParams(location.search).get("id");
  if (id) openNotice(id).catch(() => { history.replaceState(null, "", "/notices"); });
});
