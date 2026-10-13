/* SafetyAgent notice sheets: one renderer for the editor (/notices) and the print/share view (/notice/<id>).
   Templates: poster (A4), leaflet (A5), card (square image for messengers), tbm (A4 tool box meeting sheet).
   Text inside the sheet uses the notice's own language; an optional second language is printed under each line.
   Citations print as small [n] marks that point to the sources list; QR codes open the cited clause. */
"use strict";

const NOTICE_L = {
  ko: {
    keyRules: "꼭 지킬 안전수칙", dos: "이렇게 하세요", donts: "이렇게 하지 마세요", numbers: "꼭 기억할 기준",
    sources: "근거 조항", ppe: "필요한 보호구", permits: "필요한 허가·절차", tbm: "TBM 전달 내용",
    hazards: "위험요인과 안전대책", before: "작업 전 확인", signoff: "참석자 확인 서명", name: "이름", sign: "서명",
    date: "일자", place: "작업 장소", task: "작업 내용", supervisor: "관리감독자", draft: "초안 · 승인 전 게시 금지",
    approved: "승인", scan: "스캔하면 근거 조항 원문이 열립니다", scanNotice: "스캔하면 이 게시물이 열립니다",
    footer: "SafetyAgent가 인용된 조항만으로 작성 · 사람이 검토하고 승인", mt: "기계 번역 · 사용 전 검토",
  },
  en: {
    keyRules: "Key safety rules", dos: "Do", donts: "Don't", numbers: "Numbers to remember", sources: "Sources",
    ppe: "Protective equipment", permits: "Permits and procedures", tbm: "TBM briefing", hazards: "Hazards and controls",
    before: "Before you start", signoff: "Attendance sign-off", name: "Name", sign: "Signature", date: "Date",
    place: "Location", task: "Task", supervisor: "Supervisor", draft: "DRAFT · not approved for posting",
    approved: "Approved", scan: "Scan to open the cited clause", scanNotice: "Scan to open this notice",
    footer: "Written by SafetyAgent from the cited clauses only · reviewed and approved by a person",
    mt: "Machine translation · review before use",
  },
};

DA.Notice = {
  /* n = notice from the API; opts.editable = contenteditable text + warning badges (editor only) */
  render(n, opts = {}) {
    const L = NOTICE_L[n.lang] || NOTICE_L.en;
    const m = n.main || {}, tr = n.translation || null;
    const ed = !!opts.editable;
    const warn = {};
    for (const w of n.warnings || []) warn[`${w.list}.${w.index}`] = w;
    const trCheck = {};
    for (const c of n.line_checks || []) trCheck[c.field] = c;
    const mark = (cites) => (cites || []).length ? `<sup class="nref">[${cites.join(",")}]</sup>` : "";
    const editAttr = (path) => ed ? ` contenteditable="true" spellcheck="false" data-path="${path}"` : "";
    const badge = (key) => {
      const w = warn[key];
      return ed && w ? `<span class="nwarn" title="${DA.esc(DA.t("notice.warnTitle", { n: (w.numbers || []).join(", ") || "-" }))}">⚠</span>` : "";
    };
    const trLine = (field, text) => {
      if (!tr || !text) return "";
      const c = trCheck[field];
      const bad = c && !c.ok;
      return `<div class="tr${bad ? " bad" : ""}" lang="${DA.esc(tr.lang)}"${c && ed ? ` title="${DA.esc(DA.t("notice.back", { t: c.back }))}"` : ""}>${DA.esc(text)}${bad && ed ? " ⚠" : ""}</div>`;
    };
    const lines = (key, cls, icon) => (m[key] || []).map((x, i) => `<li class="${cls}">${icon ? `<span class="ic">${icon}</span>` : ""}<div>
        <span${editAttr(`${key}.${i}.text`)}>${DA.esc(x.text)}</span>${mark(x.cite)}${badge(`${key}.${i}`)}
        ${trLine(`${key}.${i}`, tr && tr[key] && tr[key][i] ? tr[key][i].text : "")}</div></li>`).join("");
    const numbers = (m.key_numbers || []).map((x, i) => `<div class="nnum"><div class="v"${editAttr(`key_numbers.${i}.value`)}>${DA.esc(x.value)}</div>
        <div class="l"><span${editAttr(`key_numbers.${i}.label`)}>${DA.esc(x.label)}</span>${mark(x.cite)}${badge(`key_numbers.${i}`)}</div>
        ${trLine(`key_numbers.${i}`, tr && tr.key_numbers && tr.key_numbers[i] ? `${tr.key_numbers[i].label} ${tr.key_numbers[i].value}` : "")}</div>`).join("");

    const P = Object.values(n.passages || {});
    const sources = P.map((p) => `<li><b>[${p.n}]</b> ${DA.esc(p.title)}, ${DA.esc(p.clause_id)}, ${DA.pages(p)}</li>`).join("");
    const qrs = P.slice(0, n.template === "card" ? 0 : 2).map((p) => `<figure class="nqr"><img src="/api/qr/source/${encodeURIComponent(p.chunk_id)}.svg" alt="">
        <figcaption>[${p.n}] ${DA.esc(p.clause_id)}</figcaption></figure>`).join("");
    const approved = n.status === "approved";
    const stamp = approved
      ? `<div class="nstamp ok">✓ ${L.approved} · ${DA.esc(n.approved_by || "")} · ${new Date(n.approved_at * 1000).toLocaleDateString()} · v${n.approved_version}</div>`
      : `<div class="nstamp draft">${L.draft}</div>`;
    const head = `<div class="nstripe"></div><header class="nhead"><img src="/brand/safetyagent_icon.svg" alt=""><span class="nbrand">SafetyAgent</span>${stamp}</header>`;
    const title = `<h1 class="ntitle"${editAttr("title")}>${DA.esc(m.title || n.title)}</h1>${trLine("title", tr && tr.title)}`;
    const subtitle = m.subtitle || ed ? `<p class="nsub"${editAttr("subtitle")}>${DA.esc(m.subtitle || "")}</p>${trLine("subtitle", tr && tr.subtitle)}` : "";
    const foot = `<footer class="nfoot"><div class="nsrc"><div class="nh">${L.sources}</div><ol>${sources}</ol>
        ${tr ? `<div class="nmt">${DA.esc(L.mt)} (${DA.esc((n.langs || {})[tr.lang] || tr.lang)})</div>` : ""}
        <div class="nnote">${L.footer}</div></div><div class="nqrs">${qrs}${qrs ? `<div class="nqrcap">${L.scan}</div>` : ""}</div></footer>`;
    const draftMark = approved ? "" : `<div class="nwatermark" aria-hidden="true">DRAFT</div>`;

    if (n.template === "tbm") {
      const blanks = [L.date, L.place, L.task, L.supervisor].map((x) => `<div class="blank"><span>${x}</span><i></i></div>`).join("");
      const rows = Array.from({ length: 8 }, (_, i) => `<tr><td>${i + 1}</td><td></td><td></td></tr>`).join("");
      return `<article class="sheet sheet-tbm" lang="${DA.esc(n.lang)}">${draftMark}${head}${title}<div class="blanks">${blanks}</div>
        ${m.key_rules && m.key_rules.length ? `<section><h2>${L.hazards}</h2><ul class="nlist">${lines("key_rules", "rule")}</ul></section>` : ""}
        <div class="ncols">
          ${m.dos && m.dos.length ? `<section><h2>${L.before}</h2><ul class="nlist">${lines("dos", "do", "☐")}</ul></section>` : ""}
          ${m.ppe && m.ppe.length ? `<section><h2>${L.ppe}</h2><ul class="nlist">${lines("ppe", "do", "☐")}</ul></section>` : ""}
        </div>
        ${m.permits && m.permits.length ? `<section><h2>${L.permits}</h2><ul class="nlist">${lines("permits", "do", "☐")}</ul></section>` : ""}
        ${m.tbm_script && m.tbm_script.length ? `<section class="script"><h2>${L.tbm}</h2><ol class="nlist">${lines("tbm_script", "say")}</ol></section>` : ""}
        <section><h2>${L.signoff}</h2><table class="nsign"><thead><tr><th>#</th><th>${L.name}</th><th>${L.sign}</th></tr></thead><tbody>${rows}</tbody></table></section>
        ${foot}</article>`;
    }
    if (n.template === "card") {
      const top = (m.key_rules || []).slice(0, 3);
      return `<article class="sheet sheet-card" lang="${DA.esc(n.lang)}">${draftMark}${head}${title}
        <ol class="nrules">${top.map((x, i) => `<li><span class="nb">${i + 1}</span><div><span${editAttr(`key_rules.${i}.text`)}>${DA.esc(x.text)}</span>${mark(x.cite)}${badge(`key_rules.${i}`)}
          ${trLine(`key_rules.${i}`, tr && tr.key_rules && tr.key_rules[i] ? tr.key_rules[i].text : "")}</div></li>`).join("")}</ol>
        <footer class="ncardfoot"><img class="nqr-lg" src="/api/qr/notice/${encodeURIComponent(n.id)}.svg" alt=""><div><b>${L.scanNotice}</b>
          <div class="nsrc-mini">${P.map((p) => `[${p.n}] ${DA.esc(p.clause_id)}`).join(" · ")}</div></div></footer></article>`;
    }
    const rules = (m.key_rules || []).map((x, i) => `<li><span class="nb">${i + 1}</span><div><span${editAttr(`key_rules.${i}.text`)}>${DA.esc(x.text)}</span>${mark(x.cite)}${badge(`key_rules.${i}`)}
        ${trLine(`key_rules.${i}`, tr && tr.key_rules && tr.key_rules[i] ? tr.key_rules[i].text : "")}</div></li>`).join("");
    return `<article class="sheet sheet-${n.template === "leaflet" ? "leaflet" : "poster"}" lang="${DA.esc(n.lang)}">${draftMark}${head}${title}${subtitle}
      <section><h2>${L.keyRules}</h2><ol class="nrules">${rules}</ol></section>
      ${(m.dos || []).length || (m.donts || []).length ? `<div class="ncols">
        ${(m.dos || []).length ? `<section class="ndo"><h2>✔ ${L.dos}</h2><ul class="nlist">${lines("dos", "do")}</ul></section>` : ""}
        ${(m.donts || []).length ? `<section class="ndont"><h2>✖ ${L.donts}</h2><ul class="nlist">${lines("donts", "dont")}</ul></section>` : ""}
      </div>` : ""}
      ${numbers ? `<section><h2>${L.numbers}</h2><div class="nnums">${numbers}</div></section>` : ""}
      ${foot}</article>`;
  },

  /* Read the edited text back into a copy of `main` (editor). */
  collect(root, main) {
    const out = JSON.parse(JSON.stringify(main));
    root.querySelectorAll("[data-path]").forEach((el) => {
      const path = el.dataset.path.split(".");
      const text = el.textContent.replace(/\s+/g, " ").trim();
      if (path.length === 1) { out[path[0]] = text; return; }
      const [key, idx, field] = path;
      if (out[key] && out[key][+idx]) out[key][+idx][field] = text;
    });
    return out;
  },
};
