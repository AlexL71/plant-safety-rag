/* SafetyAgent admin console: answers review, notice approval, test console, documents, settings. */
"use strict";

const $ = (id) => document.getElementById(id);
const viewer = new DA.Viewer();
const popover = new DA.Popover((p) => viewer.open({ chunk_id: p.chunk_id }));
const VERDICT_LABEL = { correct: "Correct", partial: "Partly correct", incorrect: "Incorrect" };
const VERDICT_CHIP = { correct: "ok", partial: "warn", incorrect: "bad" };
// Test-split results (eval/results/test_v1), shown next to each setup
const SETUP_RESULTS = {
  A: "Recall@5 18/34 · cross-language 0/16 · instant",
  B: "Recall@5 32/34 · cross-language 14/16 · ~0.5 s",
  C: "Recall@5 23/34 · false refusals 10/34 · ~5 s",
  D: "Recall@5 30/34 · false refusals 4/34 · ~16 s",
  E: "Recall@5 34/34 · false refusals 1/34 · ~23 s",
  F: "Recall@5 34/34 + 24/24 (set 2) · false refusals 1/34 + 0/24 · ~15–30 s (recommended)",
};
const content = $("content");

/* ---------------------------------------------------------------- auth */
async function boot() {
  try {
    const me = await DA.api("/api/admin/me");
    showApp(me.username);
  } catch (_) {
    $("loginView").hidden = false;
    $("u").focus();
  }
}

$("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("loginErr").textContent = "";
  try {
    const me = await DA.api("/api/admin/login", { method: "POST", body: { username: $("u").value, password: $("p").value } });
    $("p").value = "";
    $("loginView").hidden = true;
    showApp(me.username);
  } catch (err) {
    $("loginErr").textContent = err.message;
  }
});

$("logout").onclick = async () => { await DA.api("/api/admin/logout", { method: "POST" }); location.reload(); };

function showApp(name) {
  $("loginView").hidden = true;
  $("appView").hidden = false;
  $("who").textContent = name;
  $("avatar").textContent = (name || "?").slice(0, 1);
  document.querySelectorAll(".tab").forEach((t) => { t.onclick = () => go(t.dataset.tab); });
  go(location.hash.slice(1) || "overview");
}

function go(tab) {
  if (!TABS[tab]) tab = "overview";
  location.hash = tab;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tab));
  content.innerHTML = `<div class="muted small" style="display:flex;gap:10px;align-items:center"><div class="spinner"></div>Loading…</div>`;
  TABS[tab]().catch((err) => {
    if (err.status === 401) location.reload();
    content.innerHTML = `<div class="card" style="padding:20px">${DA.esc(err.message)}</div>`;
  });
}

/* ---------------------------------------------------------------- shared: answer detail */
function evidenceHtml(ev) {
  return `<div class="ev ${ev.cited ? "cited" : ""}">
    <div class="head"><span class="cite" style="cursor:default">${ev.n}</span><span class="t">${DA.esc(ev.title)}</span>
      <span class="chip muted">${DA.esc(ev.clause_id)}</span><span class="muted">${DA.pages(ev)} · ${ev.lang === "ko" ? "KO" : "EN"}</span>
      <span class="chip ${ev.cited ? "" : "muted"}">${ev.cited ? "cited" : "not cited"}</span>
      <span class="muted score">score ${Number(ev.score).toFixed(3)}</span></div>
    <div class="txt">${DA.esc(ev.text)}</div>
    <div class="acts"><button class="btn btn-ghost btn-sm" data-open="${DA.esc(ev.chunk_id)}" type="button">Open in document</button>
      <button class="btn btn-ghost btn-sm" data-more type="button">Show full text</button></div></div>`;
}

function checkLine(name, c) {
  if (!c || !c.elements) return "";
  const why = Object.entries(c).filter(([k]) => !["elements", "kept", "dropped"].includes(k)).map(([k, v]) => `${k} ${v}`).join(", ");
  return `<span class="chip ${c.dropped ? "warn" : "ok"}">${name}: ${c.kept}/${c.elements} kept${c.dropped ? ` · dropped ${c.dropped} (${DA.esc(why)})` : ""}</span>`;
}

function renderDetail(el, m, { review = null } = {}) {
  const timings = m.timings ? Object.entries(m.timings).map(([k, v]) => `${k} ${v}s`).join(", ") : "";
  const route = m.route || {};
  const agent = `<div class="sub" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">
      <span class="chip accent">Mode ${DA.esc(m.mode || "auto")} → ${DA.esc(m.intent || "answer")}</span>
      ${route.reason ? `<span class="chip muted">planner: ${DA.esc(route.reason)}</span>` : ""}
      ${route.visual && route.visual !== "none" ? `<span class="chip muted">visual: ${DA.esc(route.visual)}</span>` : ""}
      ${route.country ? `<span class="chip muted">documents: ${DA.esc(route.country)}</span>` : ""}
      ${route.query_ko || route.query_en ? `<span class="chip muted" style="white-space:normal">searched as: “${DA.esc(route.query_ko || "")}” / “${DA.esc(route.query_en || "")}”</span>` : ""}
      ${checkLine("visual check", m.visual_check)}${checkLine("plan check", m.plan_check)}${checkLine("notice check", m.notice_check)}
      ${m.visual_reason ? `<span class="chip muted">no visual: ${DA.esc(m.visual_reason)}</span>` : ""}</div>`;
  el.innerHTML = `
    <div><div class="section-label">Question</div><div class="qbox">${DA.esc(m.question)}</div>
      <div class="sub">${m.standalone ? `Read as: “${DA.esc(m.standalone)}” · ` : ""}${m.translated ? `Also searched as: “${DA.esc(m.translated)}” · ` : ""}
        Setup ${DA.esc(m.setup || "?")} · ${m.total_s ? `${m.total_s} s total` : ""}${timings ? ` (${timings}, LLM ${m.llm_s}s${m.llm_cached ? " cached" : ""})` : ""}</div>${agent}</div>
    <div><div class="section-label">Answer ${m.refused ? `<span class="chip muted">Refused: ${DA.esc(m.reason)}</span>` : ""}</div>
      <div class="answer card" style="padding:16px 18px;box-shadow:none">${m.kind === "plan" && m.plan ? DA.renderPlan(m.plan, m.passages || {})
        : DA.renderAnswer(m.text, m.refused ? {} : m.passages || {})}${m.visual ? DA.renderVisual(m.visual, m.passages || {}) : ""}
        ${m.kind === "notice" && m.notice_id ? `<div style="margin-top:8px"><a href="#notices" onclick="go('notices')">Notice drafted: review it in Notices</a></div>` : ""}</div></div>
    ${review ? `<div class="review"><div class="section-label">Your review</div>
      <div class="verdicts">${Object.entries(VERDICT_LABEL).map(([k, l]) =>
        `<button class="verdict ${k} ${review.verdict === k ? "on" : ""}" data-v="${k}" type="button">${l}</button>`).join("")}</div>
      <textarea class="input" id="note" rows="2" placeholder="Note (what is wrong or missing?)">${DA.esc(review.note || "")}</textarea>
      <div style="display:flex;gap:10px;align-items:center"><button class="btn btn-primary btn-sm" id="saveReview" type="button">Save review</button>
        <span class="small muted" id="reviewMsg">${review.verdict ? `Reviewed by ${DA.esc(review.reviewer)}` : "Not reviewed yet"}</span></div></div>` : ""}
    <div><div class="section-label">Passages given to the model (${(m.evidence || []).length})</div>
      <div style="display:grid;gap:10px;margin-top:8px">${(m.evidence || []).map(evidenceHtml).join("") || `<div class="muted small">None</div>`}</div></div>`;
  popover.attach(el, m.refused ? {} : m.passages || {});
  el.querySelectorAll("[data-open]").forEach((b) => { b.onclick = () => viewer.open({ chunk_id: b.dataset.open }); });
  el.querySelectorAll("[data-more]").forEach((b) => {
    b.onclick = () => { const ev = b.closest(".ev"); ev.classList.toggle("open"); b.textContent = ev.classList.contains("open") ? "Show less" : "Show full text"; };
  });
}

/* ---------------------------------------------------------------- tabs */
const TABS = {
  async overview() {
    const o = await DA.api("/api/admin/overview");
    const s = o.stats, rv = s.reviews || {};
    const reviewed = (rv.correct || 0) + (rv.partial || 0) + (rv.incorrect || 0);
    content.innerHTML = `
      <div class="h"><h2>Overview</h2><span class="chip ${o.status.ready ? "ok" : "warn"}">${o.status.ready ? "Engine ready" : "Engine loading"}</span>
        <span class="chip">Users get setup ${o.user_setup}</span></div>
      <div class="tiles">
        <div class="card tile"><div class="n">${s.questions}</div><div class="l">questions asked</div></div>
        <div class="card tile"><div class="n">${s.answers ? Math.round((100 * s.refused) / s.answers) : 0}%</div><div class="l">answered "not found" (${s.refused}/${s.answers})</div></div>
        <div class="card tile"><div class="n">${s.users}</div><div class="l">browsers · ${s.chats} chats</div></div>
        <div class="card tile"><div class="n">${reviewed}</div><div class="l">answers reviewed · ${rv.correct || 0} correct · ${rv.partial || 0} partly · ${rv.incorrect || 0} incorrect</div></div>
      </div>
      <div class="card" style="padding:20px;margin-top:18px">
        <div class="section-label">Corpus</div>
        <div style="margin-top:6px">${o.status.documents} documents · ${o.status.chunks.toLocaleString()} clauses indexed</div>
        <div class="small muted" style="margin-top:6px">Review answers in the <a href="#answers" onclick="go('answers')">Answers</a> tab; change the users' search setup in <a href="#settings" onclick="go('settings')">Settings</a>.</div>
      </div>`;
  },

  async answers() {
    content.innerHTML = `
      <div class="h"><h2>Answers</h2><span class="sub">Check user answers against the original documents</span>
        <select class="input" id="filter" style="width:200px;margin-left:auto">
          <option value="">All answers</option><option value="unreviewed">Not reviewed</option>
          <option value="correct">Correct</option><option value="partial">Partly correct</option><option value="incorrect">Incorrect</option></select></div>
      <div class="split"><div class="card list" id="alist"></div><div class="card detail" id="adetail"><div class="muted">Select an answer.</div></div></div>`;
    const load = async () => {
      const f = $("filter").value;
      const data = await DA.api(`/api/admin/answers?limit=100${f ? `&verdict=${f}` : ""}`);
      const list = $("alist");
      list.innerHTML = data.answers.length ? "" : `<div class="muted small" style="padding:12px">No answers yet.</div>`;
      for (const a of data.answers) {
        const row = document.createElement("div");
        row.className = "row";
        row.innerHTML = `<div class="q">${DA.esc(a.question || "(no question)")}</div>
          <div class="m">${a.verdict ? `<span class="chip ${VERDICT_CHIP[a.verdict]}">${VERDICT_LABEL[a.verdict]}</span>` : `<span class="chip muted">Not reviewed</span>`}
          ${a.refused ? `<span class="chip muted">Not found</span>` : ""}<span>Setup ${DA.esc(a.setup || "?")}</span><span>· ${DA.timeAgo(a.created)}</span></div>`;
        row.onclick = () => { list.querySelectorAll(".row").forEach((r) => r.classList.remove("active")); row.classList.add("active"); openAnswer(a.id, load); };
        list.appendChild(row);
      }
    };
    $("filter").onchange = load;
    await load();
  },

  async console() {
    const s = await DA.api("/api/admin/settings");
    content.innerHTML = `
      <div class="h"><h2>Test console</h2><span class="sub">Ask with any search setup and see everything the model was given. Not saved.</span></div>
      <form class="console" id="cform">
        <textarea class="input" id="cq" rows="2" placeholder="Question in Korean or English" required></textarea>
        <div style="display:grid;gap:8px"><select class="input" id="csetup">${Object.entries(s.setups).map(([k, d]) => `<option value="${k}" ${k === "E" ? "selected" : ""}>${k} · ${DA.esc(d)}</option>`).join("")}</select>
          <select class="input" id="cmode">${["auto", "answer", "task_plan", "notice"].map((x) => `<option value="${x}">mode: ${x}</option>`).join("")}</select></div>
        <button class="btn btn-primary" type="submit">Ask</button>
      </form>
      <div class="card detail" id="cout" style="margin-top:18px"><div class="muted">The answer, passages and timings appear here.</div></div>`;
    $("cform").addEventListener("submit", async (e) => {
      e.preventDefault();
      const out = $("cout"), question = $("cq").value.trim(), setup = $("csetup").value, mode = $("cmode").value;
      out.innerHTML = `<div class="steps" style="display:flex;gap:10px;align-items:center"><div class="spinner"></div><span id="cstage">Starting…</span></div>`;
      try {
        await DA.stream("/api/admin/ask", { question, setup, mode }, (ev) => {
          if (ev.type === "stage") $("cstage").textContent = `Stage: ${ev.stage}…`;
          else if (ev.type === "done") renderDetail(out, { ...ev.message, question });
          else if (ev.type === "error") out.innerHTML = `<span class="chip bad">Error</span> ${DA.esc(ev.detail)}`;
        });
      } catch (err) { out.innerHTML = `<span class="chip bad">Error</span> ${DA.esc(err.message)}`; }
    });
  },

  async notices() {
    content.innerHTML = `
      <div class="h"><h2>Notices</h2><span class="sub">Check drafted safety notices against their sources, then approve them for printing and sharing</span>
        <select class="input" id="nfilter" style="width:200px;margin-left:auto">
          <option value="">All notices</option><option value="draft">Waiting for approval</option><option value="approved">Approved</option></select></div>
      <div class="split"><div class="card list" id="nlist"></div><div class="card detail" id="ndetail"><div class="muted">Select a notice.</div></div></div>`;
    const load = async () => {
      const f = $("nfilter").value;
      const data = await DA.api(`/api/admin/notices${f ? `?status=${f}` : ""}`);
      const list = $("nlist");
      list.innerHTML = data.notices.length ? "" : `<div class="muted small" style="padding:12px">No notices yet.</div>`;
      for (const n of data.notices) {
        const row = document.createElement("div");
        row.className = "row";
        row.innerHTML = `<div class="q">${DA.esc(n.title)}</div><div class="m">${n.status === "approved" ? `<span class="chip ok">Approved v${n.approved_version ?? n.version}</span>`
          : `<span class="chip warn">Draft v${n.version}</span>`}<span>${DA.esc(n.template)}</span><span>· ${n.lang.toUpperCase()}</span><span>· ${DA.timeAgo(n.updated)}</span></div>`;
        row.onclick = () => { list.querySelectorAll(".row").forEach((r) => r.classList.remove("active")); row.classList.add("active"); openNotice(n.id, load); };
        list.appendChild(row);
      }
    };
    $("nfilter").onchange = load;
    await load();
  },

  async docs() {
    const data = await DA.api("/api/admin/docs");
    content.innerHTML = `
      <div class="h"><h2>Documents</h2><span class="sub">${data.docs.length} documents in the index</span></div>
      <div class="card"><table><thead><tr><th>Document</th><th>Lang</th><th>Pages</th><th>Clauses</th><th></th></tr></thead><tbody>
      ${data.docs.map((d) => `<tr><td><div style="font-weight:600">${DA.esc(d.title)}</div><div class="small muted">${DA.esc(d.doc_id)}</div></td>
        <td><span class="chip ${d.lang === "ko" ? "" : "accent"}">${d.lang.toUpperCase()}</span></td><td>${d.n_pages}</td><td>${d.chunks ?? "–"}</td>
        <td style="white-space:nowrap;text-align:right"><button class="btn btn-ghost btn-sm" data-view="${DA.esc(d.doc_id)}" type="button">View pages</button>
          <a class="btn btn-ghost btn-sm" href="/api/admin/docs/${encodeURIComponent(d.doc_id)}/file" target="_blank" rel="noopener">Open PDF ↗</a>
          ${d.source_url ? `<a class="btn btn-ghost btn-sm" href="${DA.esc(d.source_url)}" target="_blank" rel="noopener noreferrer">Source ↗</a>` : ""}</td></tr>`).join("")}
      </tbody></table></div>`;
    content.querySelectorAll("[data-view]").forEach((b) => { b.onclick = () => viewer.open({ doc_id: b.dataset.view }); });
  },

  async settings() {
    const s = await DA.api("/api/admin/settings");
    let sel = s.user_setup;
    content.innerHTML = `
      <div class="h"><h2>Settings</h2></div>
      <div class="card" style="padding:22px;display:grid;gap:14px">
        <div><div style="font-weight:700">Search setup for users</div>
          <div class="small muted">Which method answers users' questions. Measured on the 40 held-out test questions.</div></div>
        <div class="setup-opts" id="opts">${Object.entries(s.setups).map(([k, d]) => `
          <label class="opt ${k === sel ? "sel" : ""}" data-k="${k}"><input type="radio" name="setup" value="${k}" ${k === sel ? "checked" : ""}>
            <div><div class="nm">${k} · ${DA.esc(d)}</div><div class="ds">${SETUP_RESULTS[k] || ""}</div></div>
            ${k === "F" ? `<span class="chip ok">Best measured</span>` : "<span></span>"}</label>`).join("")}</div>
        <div style="display:flex;gap:12px;align-items:center"><button class="btn btn-primary btn-sm" id="saveSetup" type="button">Save</button><span class="small muted" id="setMsg"></span></div>
      </div>
      <div class="card" style="padding:22px;margin-top:18px">
        <div style="font-weight:700">Limits</div>
        <div class="small muted" style="margin-top:6px">${s.limits.max_chats_per_user} chats per browser (oldest removed automatically) ·
          ${s.limits.max_turns_per_chat} questions per chat · ${s.limits.max_question_chars} characters per question.
          Change them in <code>configs/config.yaml</code> (section <code>web</code>) and restart.</div>
      </div>`;
    content.querySelectorAll(".opt").forEach((o) => {
      o.onclick = () => { sel = o.dataset.k; content.querySelectorAll(".opt").forEach((x) => x.classList.toggle("sel", x === o)); };
    });
    $("saveSetup").onclick = async () => {
      await DA.api("/api/admin/settings", { method: "PUT", body: { user_setup: sel } });
      $("setMsg").textContent = `Saved. Users now get setup ${sel}.`;
    };
  },
};

async function openNotice(id, reloadList) {
  const el = $("ndetail");
  el.innerHTML = `<div class="muted small" style="display:flex;gap:10px;align-items:center"><div class="spinner"></div>Loading…</div>`;
  const n = await DA.api(`/api/admin/notices/${encodeURIComponent(id)}`);
  const lc = n.line_checks || [], bad = lc.filter((c) => !c.ok), warns = n.warnings || [];
  const P = Object.values(n.passages || {});
  el.innerHTML = `
    <div><div class="section-label">Notice</div><div class="qbox">${DA.esc(n.title)}</div>
      <div class="sub">${n.lang.toUpperCase()} · ${DA.esc(n.template)} · version ${n.version} · ${n.status === "approved" ? `approved by ${DA.esc(n.approved_by)} (v${n.approved_version})` : "not approved"}
        ${n.topic ? ` · topic: “${DA.esc(n.topic)}”` : ""}</div></div>
    <div class="review"><div class="section-label">Checks</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">${warns.length ? `<span class="chip warn">⚠ ${warns.length} line(s): number not in the cited source, or no valid source</span>`
        : `<span class="chip ok">✓ Every line cites a source and its numbers appear there</span>`}
        ${checkLine("draft check", n.check)}
        ${n.translation ? (bad.length ? `<span class="chip warn">⚠ translation: ${bad.length}/${lc.length} lines changed numbers</span>`
          : `<span class="chip ok">✓ translation (${DA.esc((n.langs || {})[n.translation.lang] || n.translation.lang)}): numbers kept in ${lc.length}/${lc.length} lines</span>`) : ""}</div>
      ${n.translation ? `<details><summary class="small">Back-translation (read this to check the meaning)</summary><div class="small" style="display:grid;gap:4px;margin-top:6px">
        ${lc.map((c) => `<div${c.ok ? "" : ' style="color:var(--bad)"'}>${c.ok ? "✓" : "⚠"} ${DA.esc(c.back)}</div>`).join("")}</div></details>` : ""}
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <button class="btn btn-primary btn-sm" id="approve" type="button" ${n.status === "approved" ? "disabled" : ""}>${n.status === "approved" ? "Approved" : "Approve for posting"}</button>
        <a class="btn btn-ghost btn-sm" href="/notice/${encodeURIComponent(n.id)}" target="_blank" rel="noopener">Open print view ↗</a>
        <button class="btn btn-ghost btn-sm" id="ndel" type="button">Delete</button><span class="small muted" id="nmsg"></span></div></div>
    <div><div class="section-label">Sources (${P.length})</div><div style="display:grid;gap:6px;margin-top:6px">${P.map((p) =>
      `<div class="small"><button class="btn btn-ghost btn-sm" data-open="${DA.esc(p.chunk_id)}" type="button">[${p.n}] Open</button> ${DA.esc(p.title)}, ${DA.esc(p.clause_id)}, ${DA.pages(p)}</div>`).join("")}</div></div>
    <div><div class="section-label">Preview</div><div style="overflow:auto;background:var(--bg);padding:14px;border-radius:12px">
      <div style="transform:scale(.62);transform-origin:top left;width:794px;margin-bottom:-38%">${DA.Notice.render(n, { editable: false })}</div></div></div>`;
  el.querySelectorAll("[data-open]").forEach((b) => { b.onclick = () => viewer.open({ chunk_id: b.dataset.open }); });
  $("approve").onclick = async () => {
    await DA.api(`/api/admin/notices/${encodeURIComponent(id)}/approve`, { method: "POST" });
    $("nmsg").textContent = "Approved. The share link and QR code now work for everyone.";
    reloadList(); openNotice(id, reloadList);
  };
  $("ndel").onclick = async () => {
    if (!confirm("Delete this notice?")) return;
    await DA.api(`/api/admin/notices/${encodeURIComponent(id)}`, { method: "DELETE" });
    el.innerHTML = `<div class="muted">Deleted.</div>`;
    reloadList();
  };
}

async function openAnswer(id, reloadList) {
  const el = $("adetail");
  el.innerHTML = `<div class="muted small" style="display:flex;gap:10px;align-items:center"><div class="spinner"></div>Loading…</div>`;
  const m = await DA.api(`/api/admin/answers/${id}`);
  renderDetail(el, m, { review: m.review });
  let verdict = m.review.verdict;
  el.querySelectorAll(".verdict").forEach((b) => {
    b.onclick = () => { verdict = b.dataset.v; el.querySelectorAll(".verdict").forEach((x) => x.classList.toggle("on", x === b)); };
  });
  $("saveReview").onclick = async () => {
    if (!verdict) { $("reviewMsg").textContent = "Choose a verdict first."; return; }
    await DA.api(`/api/admin/answers/${id}/review`, { method: "PUT", body: { verdict, note: $("note").value } });
    $("reviewMsg").textContent = "Saved.";
    reloadList();
  };
}

boot();
