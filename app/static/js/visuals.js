/* SafetyAgent visuals: draws the checked visual specs (steps, checklist, compare, limits, intervals).
   Everything is built from escaped text; citation numbers become .cite buttons that the caller wires to the
   pop-over (DA.Popover.attach). Needs common.js and i18n.js. */
"use strict";

DA.cites = function (nums, passages) {
  return (nums || []).filter((n) => passages && passages[n])
    .map((n) => `<button type="button" class="cite" data-n="${n}" aria-label="${DA.t("cite.aria", { n })}">${n}</button>`)
    .join("");
};

const VIS_ICON = {
  steps: '<path d="M4 6h10M4 12h10M4 18h10"/><path d="M18 5l2 2-2 2M18 11l2 2-2 2"/>',
  checklist: '<path d="M9 11l3 3 8-8"/><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"/>',
  compare: '<path d="M12 3v18"/><path d="M4 7h5M4 12h5M4 17h5M15 7h5M15 12h5M15 17h5"/>',
  limits: '<path d="M3 12h18"/><path d="M8 8v8M16 8v8"/><path d="M3 9v6M21 9v6"/>',
  intervals: '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
};

function visHead(spec) {
  return `<div class="vis-head"><span class="vis-ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
      stroke-linecap="round" stroke-linejoin="round">${VIS_ICON[spec.type] || ""}</svg></span>
    <div><div class="vis-title">${DA.esc(spec.title)}</div><div class="vis-kind">${DA.t(`vis.${spec.type}`)}</div></div>
    <span class="chip ok vis-checked" title="${DA.esc(DA.t("vis.checkedTitle"))}">✓ ${DA.t("vis.checked")}</span></div>`;
}

function renderSteps(spec, P) {
  return `<ol class="vis-steps">${spec.items.map((x, i) => `<li><span class="num">${i + 1}</span><div>
      <div class="lbl">${DA.esc(x.label)} ${DA.cites(x.cite, P)}</div>
      ${x.detail ? `<div class="det">${DA.esc(x.detail)}</div>` : ""}</div></li>`).join("")}</ol>`;
}

function renderChecklist(spec, P) {
  return `<ul class="vis-check">${spec.items.map((x) => `<li><label><input type="checkbox"><span class="box"></span>
      <span><span class="lbl">${DA.esc(x.label)}</span> ${DA.cites(x.cite, P)}
      ${x.detail ? `<span class="det">${DA.esc(x.detail)}</span>` : ""}</span></label></li>`).join("")}</ul>`;
}

function renderCompare(spec, P) {
  const cell = (text, cites) => {
    const t = String(text || "").trim();
    return t && t !== "-" && t !== "—" ? `${DA.esc(t)} ${DA.cites(cites, P)}` : `<span class="muted">${DA.t("vis.notCovered")}</span>`;
  };
  return `<div class="vis-compare-wrap"><table class="vis-compare"><thead><tr><th></th>
      <th><span class="flag">KR</span> ${DA.esc(spec.left_label)}</th><th><span class="flag us">US</span> ${DA.esc(spec.right_label)}</th></tr></thead>
    <tbody>${spec.rows.map((r) => `<tr><th scope="row">${DA.esc(r.aspect)}</th><td>${cell(r.left, r.cite_left)}</td>
      <td>${cell(r.right, r.cite_right)}</td></tr>`).join("")}</tbody></table></div>`;
}

const fmtNum = (v) => (Number.isFinite(v) ? String(+v.toFixed(3)) : "");

/* One horizontal scale per limit: the allowed zone in green, the rest shaded red. */
function renderLimits(spec, P) {
  return `<div class="vis-limits">${spec.limits.map((x) => {
    const lo = Number(x.low), hi = Number(x.high);
    const ref = x.bound === "above" ? lo : hi;                       // the value the scale is built around
    const max = (Number.isFinite(ref) && ref > 0 ? ref : 1) * (x.bound === "above" ? 1.6 : 1.35);
    const pct = (v) => Math.max(0, Math.min(100, (v / max) * 100));
    let okFrom = 0, okTo = 100, text = "";
    if (x.bound === "range") { okFrom = pct(lo); okTo = pct(hi); text = `${fmtNum(lo)} – ${fmtNum(hi)} ${x.unit}`; }
    else if (x.bound === "below") { okTo = pct(hi); text = `< ${fmtNum(hi)} ${x.unit}`; }
    else { okFrom = pct(lo); text = `≥ ${fmtNum(lo)} ${x.unit}`; }
    const ticks = [x.bound !== "below" ? lo : null, x.bound !== "above" ? hi : null].filter((v) => v !== null && Number.isFinite(v));
    return `<div class="lim"><div class="lim-head"><span class="lbl">${DA.esc(x.name)}</span>
        <span class="val">${DA.esc(text)}</span> ${DA.cites(x.cite, P)}</div>
      <div class="lim-bar" role="img" aria-label="${DA.esc(`${x.name}: ${text}`)}">
        <div class="zone ok" style="left:${okFrom}%;width:${Math.max(1, okTo - okFrom)}%"></div>
        ${ticks.map((v) => `<span class="tick" style="left:${pct(v)}%"><i></i><b>${fmtNum(v)}</b></span>`).join("")}
      </div>${x.note ? `<div class="det">${DA.esc(x.note)}</div>` : ""}</div>`;
  }).join("")}<div class="lim-legend"><span class="sw ok"></span>${DA.t("vis.allowed")}<span class="sw bad"></span>${DA.t("vis.notAllowed")}</div></div>`;
}

const UNIT_MIN = { minutes: 1, hours: 60, days: 1440, weeks: 10080, months: 43800, years: 525600 };

/* Time periods on a log scale (30 minutes and 3 years on one chart), shortest first. */
function renderIntervals(spec, P) {
  const rows = spec.intervals.map((x) => ({ ...x, min: (Number(x.value) || 0) * (UNIT_MIN[x.unit] || 1) }))
    .sort((a, b) => a.min - b.min);
  const lmax = Math.log10(Math.max(...rows.map((r) => r.min), 2) * 1.5);
  return `<div class="vis-intervals">${rows.map((x) => {
    const w = Math.max(6, (Math.log10(Math.max(x.min, 1) + 1) / lmax) * 100);
    const unit = DA.t(`unit.${x.unit}${Number(x.value) === 1 ? ".one" : ""}`, { n: fmtNum(Number(x.value)) });
    return `<div class="iv"><div class="iv-lbl">${DA.esc(x.label)} ${DA.cites(x.cite, P)}</div>
      <div class="iv-bar"><div class="fill" style="width:${w}%"></div><span class="iv-val">${DA.t(`kind.${x.kind}`, { v: unit })}</span></div></div>`;
  }).join("")}<div class="det">${DA.t("vis.logScale")}</div></div>`;
}

DA.renderVisual = function (spec, passages) {
  if (!spec || !spec.type) return "";
  const body = { steps: renderSteps, checklist: renderChecklist, compare: renderCompare, limits: renderLimits,
                 intervals: renderIntervals }[spec.type];
  return body ? `<div class="vis vis-${spec.type}">${visHead(spec)}${body(spec, passages)}</div>` : "";
};
