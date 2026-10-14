"""SafetyAgent: one entry point that decides what to do with a request and uses the right tools.

Tools (all grounded in the same evidence passages, all checked before anything is shown):
    search_rules   hybrid search + reranker (retrieve.Retriever.search), setup E by default
    answer         cited text answer or "not found" (generate.answer)
    make_visual    structured visual: steps / checklist / compare / limits / intervals (visuals.make_visual)
    plan_task      multi-step: task -> hazards -> one search per hazard -> cited checklist + TBM script
    draft_notice   poster / leaflet content (notices.draft_notice); stored and edited in the web app

Routing: in "auto" mode one short model call (structured JSON, low thinking) picks the intent; the user can also
choose a mode explicitly. The agent is deliberately a small, fixed state machine (at most ~4 steps per request,
every step reported to the progress UI) rather than an open-ended loop: easier to explain, test and measure.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Callable

from plant_rag.checks import check_elements, merge_stats
from plant_rag.generate import (LANG_NAME, NOT_FOUND, answer, call_llm_record, condense_question, detect_lang,
                                light_cfg, make_search_query, parse_json)
from plant_rag.notices import draft_notice
from plant_rag.visuals import VISUAL_TYPES, evidence_block, make_visual

if TYPE_CHECKING:
    from plant_rag.retrieve import Hit, Retriever

log = logging.getLogger(__name__)

INTENTS = ("answer", "visual", "compare", "task_plan", "notice", "chitchat")
MODES = ("auto", *INTENTS[:-1])  # what the user can pick in the chat

# ------------------------------------------------------------------ router

ROUTER_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": list(INTENTS)},
        "visual_type": {"type": "string", "enum": [*VISUAL_TYPES, "auto"]},
        "reason": {"type": "string"},
    },
    "required": ["intent", "visual_type", "reason"],
}

ROUTER_SYSTEM = """You route requests for SafetyAgent, a workplace-safety assistant that answers from Korean and US
safety regulations and guides (KOSHA guides, Korean OSH Act and rules, OSHA standards). Choose ONE intent:
- answer: a question about a safety rule, requirement, definition, number or procedure.
- visual: the user asks to show or explain something as a chart, diagram, flow, table, checklist or visual.
- compare: the user wants Korea and the US (KOSHA / Korean law vs OSHA), or two standards, compared.
- task_plan: the user describes a job they (or a crew) will do and wants to know what to prepare or check:
  permits, hazards, controls, PPE, a pre-work checklist or a TBM (tool box meeting) briefing.
- notice: the user asks to make, create or draft a poster, flyer, notice, sign or leaflet to print, post or share.
- chitchat: greetings, thanks, questions about the assistant itself, or requests unrelated to workplace safety.
For visual, also pick visual_type: steps (procedure), checklist, limits (numeric thresholds), intervals (time
periods), compare, or auto. Otherwise use auto. reason: a few English words."""


def route_request(question: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """One cached, light model call. Falls back to "answer" if the output is unusable."""
    rec = call_llm_record(f"Request: {question}", light_cfg(cfg, 512), ROUTER_SYSTEM, json_schema=ROUTER_SCHEMA)
    try:
        out = parse_json(rec["text"])
        if out.get("intent") not in INTENTS:
            raise ValueError(out)
        return {"intent": out["intent"], "visual_type": out.get("visual_type", "auto"),
                "reason": out.get("reason", ""), "llm_s": rec.get("seconds", 0.0), "cached": rec["cached"]}
    except (ValueError, KeyError) as exc:
        log.warning("Router fallback to answer: %s", exc)
        return {"intent": "answer", "visual_type": "auto", "reason": "router_fallback", "llm_s": 0.0, "cached": False}


# ------------------------------------------------------------------ task plan

DECOMPOSE_SCHEMA = {
    "type": "object",
    "properties": {
        "task_summary": {"type": "string"},
        "hazards": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "query": {"type": "string"}}, "required": ["name", "query"]}},
    },
    "required": ["task_summary", "hazards"],
}

DECOMPOSE_SYSTEM = """A worker describes a job. List the main workplace-safety hazard topics of this job that safety
rules would cover (for example hot work / fire, confined space / oxygen and gas, work at height / falls,
lockout of energy, forklifts and vehicles, heat, personal protective equipment, work permits).
Return 1 to {max_hazards} hazards, most important first. For each: a short name in {lang_name} and one search query
in {lang_name} that would find the rule text (e.g. "밀폐공간 작업 전 산소 및 유해가스 농도 측정").
task_summary: the job in one short line, in {lang_name}."""

_CITE = {"type": "array", "items": {"type": "integer"}}
_ITEM = {"type": "object", "properties": {"text": {"type": "string"}, "cite": _CITE}, "required": ["text", "cite"]}
PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "permits": {"type": "array", "items": _ITEM},
        "hazards": {"type": "array", "items": {"type": "object", "properties": {
            "hazard": {"type": "string"}, "controls": {"type": "array", "items": _ITEM}},
            "required": ["hazard", "controls"]}},
        "before_start": {"type": "array", "items": _ITEM},
        "ppe": {"type": "array", "items": _ITEM},
        "tbm_script": {"type": "array", "items": _ITEM},
        "not_covered": {"type": "string"},
    },
    "required": ["title", "hazards"],
}

PLAN_SYSTEM = """You prepare a pre-work safety plan for a job from evidence passages (Korean and US rules).
Use ONLY the numbered passages. Never add rules, numbers or advice that are not in them.
Write in {lang_name}, short imperative lines for a site supervisor.
- permits: work permits or written procedures the passages require for this job (may be empty).
- hazards: one entry per hazard, each with 1 to 4 controls.
- before_start: checks to do before work begins (measurements, inspections, briefings).
- ppe: protective equipment the passages require.
- tbm_script: 3 to 6 short sentences a supervisor can read out at the tool box meeting (TBM).
- not_covered: one line naming important parts of the job the passages do not cover (or empty).
Every line cites the passage number(s) that support it. Keep numbers and units exactly as in the passages.
Prefer rules that apply where the job is done; mark the source country only if it matters ("(US OSHA)")."""

PLAN_LISTS = ("permits", "before_start", "ppe", "tbm_script")


def plan_task(task: str, retriever: Retriever, cfg: dict[str, Any], lang: str, setup: str,
              stage: Callable[[str], None]) -> dict[str, Any]:
    acfg = cfg.get("agent", {})
    max_h = int(acfg.get("plan_max_hazards", 3))
    t0 = time.perf_counter()
    stage("plan")
    rec = call_llm_record(f"Job: {task}", light_cfg(cfg, 1024),
                          DECOMPOSE_SYSTEM.format(max_hazards=max_h, lang_name=LANG_NAME[lang]),
                          json_schema=DECOMPOSE_SCHEMA)
    try:
        dec = parse_json(rec["text"])
        hazards = [h for h in dec.get("hazards", []) if h.get("query")][:max_h]
    except ValueError:
        dec, hazards = {"task_summary": task}, []
    if not hazards:
        hazards = [{"name": task, "query": task}]

    hits: list[Hit] = []
    per_hazard = int(acfg.get("plan_hits_per_hazard", 3))
    searched = []
    for h in hazards:
        stage("search")
        found = retriever.search(h["query"], setup=setup, k=per_hazard,
                                 rerank_candidates=int(acfg.get("plan_rerank_candidates", 6)))
        keep = [x for x in found if x.rerank_score is None or x.rerank_score >= float(acfg.get("plan_min_rerank", 0.05))]
        searched.append({"hazard": h["name"], "query": h["query"], "found": len(keep)})
        for x in keep:
            if all(x.chunk["chunk_id"] != y.chunk["chunk_id"] for y in hits):
                hits.append(x)
    hits = hits[: int(acfg.get("plan_max_evidence", 9))]
    if not hits:
        return {"plan": None, "hits": [], "hazards_searched": searched, "reason": "no_evidence",
                "summary": dec.get("task_summary", task), "seconds": time.perf_counter() - t0}

    stage("answer")
    sub = {**cfg, "llm": {**cfg["llm"], "max_output_tokens": int(acfg.get("plan_max_output_tokens", 6144))}}
    prompt = f"Job: {task}\n\nEvidence passages:\n\n{evidence_block(hits)}"
    rec = call_llm_record(prompt, sub, PLAN_SYSTEM.format(lang_name=LANG_NAME[lang]), json_schema=PLAN_SCHEMA)
    try:
        raw = parse_json(rec["text"])
    except ValueError:
        return {"plan": None, "hits": hits, "hazards_searched": searched, "reason": "invalid_json",
                "summary": dec.get("task_summary", task), "seconds": time.perf_counter() - t0}

    stage("check")
    passages = {n: h.chunk for n, h in enumerate(hits, 1)}
    results, plan = [], {"title": raw.get("title") or dec.get("task_summary", task),
                         "not_covered": raw.get("not_covered", "")}
    for key in PLAN_LISTS:
        r = check_elements(raw.get(key) or [], ("text",), passages)
        plan[key] = r.kept
        results.append(r)
    plan["hazards"] = []
    for hz in raw.get("hazards") or []:
        r = check_elements(hz.get("controls") or [], ("text",), passages)
        results.append(r)
        if r.kept:
            plan["hazards"].append({"hazard": hz.get("hazard", ""), "controls": r.kept})
    n_kept = sum(len(plan[k]) for k in PLAN_LISTS) + sum(len(h["controls"]) for h in plan["hazards"])
    return {"plan": plan if n_kept else None, "hits": hits, "hazards_searched": searched,
            "reason": "" if n_kept else "no_checked_items", "check": merge_stats(*results),
            "summary": dec.get("task_summary", task), "seconds": time.perf_counter() - t0}


def plan_as_text(plan: dict) -> str:
    """Plain-text version of a plan (stored as the message text; used for follow-up questions)."""
    lines = [plan["title"]]
    for h in plan.get("hazards", []):
        lines.append(f"- {h['hazard']}: " + "; ".join(c["text"] for c in h["controls"]))
    for key in ("permits", "before_start", "ppe"):
        lines += [f"- {x['text']}" for x in plan.get(key, [])]
    return "\n".join(lines)


# ------------------------------------------------------------------ helpers

def balance_languages(hits: list[Hit], per_lang: int) -> list[Hit]:
    """For comparisons: the best `per_lang` Korean and English passages, interleaved by score."""
    ko = [h for h in hits if h.chunk["lang"] == "ko"][:per_lang]
    en = [h for h in hits if h.chunk["lang"] == "en"][:per_lang]
    return sorted(ko + en, key=lambda h: -(h.rerank_score if h.rerank_score is not None else h.score))


CHITCHAT = {
    "en": ("I'm SafetyAgent. I answer workplace-safety questions from Korean and US safety rules and guides, "
           "with the exact clause for every statement. I can also explain rules as a visual, compare Korea and "
           "the US, plan the safety checks for a job, and draft a notice you can print. Try: "
           "\"What oxygen level is safe in a confined space?\""),
    "ko": ("저는 SafetyAgent입니다. 한국과 미국의 산업안전 규정·가이드를 근거로 질문에 답하고, 모든 내용에 근거 조항을 "
           "표시합니다. 규정을 시각 자료로 설명하거나, 한국과 미국 기준을 비교하거나, 작업 전 안전 점검 계획을 세우고, "
           "인쇄용 안전 게시물 초안도 만들 수 있습니다. 예: \"밀폐공간 작업 시 적정 산소농도는?\""),
}


# ------------------------------------------------------------------ main entry

def run(question: str, history: list[tuple[str, str]], retriever: Retriever, cfg: dict[str, Any], setup: str,
        mode: str = "auto", lang: str | None = None,
        on_stage: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Handle one chat request. Returns JSON-ready data; the web app stores it as the message payload."""
    stage = on_stage or (lambda s: None)
    lang = lang if lang in LANG_NAME else detect_lang(question)
    t0 = time.perf_counter()
    route: dict[str, Any] = {"intent": mode, "visual_type": "auto", "reason": "user_choice", "llm_s": 0.0}
    if mode == "auto":
        stage("route")
        route = route_request(question, cfg)
    intent = route["intent"] if route["intent"] in INTENTS else "answer"
    out: dict[str, Any] = {"kind": "answer", "intent": intent, "route": route, "lang": lang, "setup": setup,
                           "question": question}

    if intent == "chitchat":
        out |= {"kind": "chat", "text": CHITCHAT[lang], "refused": False, "cited": [], "evidence_hits": []}
        out["total_s"] = round(time.perf_counter() - t0, 2)
        return out

    standalone = question
    if history:
        stage("condense")
        standalone = condense_question(question, history[-int(cfg.get("web", {}).get("history_turns", 3)):], cfg)
    out["standalone"] = standalone if standalone != question else None

    if intent == "task_plan":
        res = plan_task(standalone, retriever, cfg, lang, setup, stage)
        hits = res["hits"]
        out |= {"kind": "plan", "plan": res["plan"], "plan_check": res.get("check", {}),
                "hazards_searched": res["hazards_searched"], "evidence_hits": hits,
                "refused": res["plan"] is None, "reason": res["reason"],
                "cited": sorted({c for x in _plan_items(res["plan"]) for c in x["cite"]}) if res["plan"] else []}
        out["text"] = plan_as_text(res["plan"]) if res["plan"] else NOT_FOUND[lang]
        out["total_s"] = round(time.perf_counter() - t0, 2)
        return out

    k = int(cfg["retrieval"]["final_k"])
    query = standalone
    if intent in ("notice", "visual", "compare"):  # "make / show ..." requests: search for the rule, not the request
        stage("query")
        query = make_search_query(standalone, cfg)
        out["search_query"] = query
    if intent == "compare":
        per_lang = int(cfg.get("agent", {}).get("compare_per_language", 3))
        hits = balance_languages(retriever.search(query, setup=setup, k=2 * k, on_stage=stage), per_lang)
    else:
        hits = retriever.search(query, setup=setup, k=k, on_stage=stage)
    out["timings"] = dict(retriever.timings)
    out["translated"] = getattr(retriever, "last_translation", None) if cfg["retrieval"]["setups"][setup].get("translate") else None

    if intent == "notice":
        stage("notice")
        res = draft_notice(standalone, hits, cfg, lang)
        out |= {"kind": "notice", "notice_content": res["content"], "notice_check": res["check"],
                "evidence_hits": hits, "refused": res["content"] is None, "reason": res["reason"],
                "cited": sorted({c for key in ("key_rules", "dos", "donts", "key_numbers")
                                 for x in (res["content"] or {}).get(key, []) for c in x["cite"]})}
        out["text"] = res["content"]["title"] if res["content"] else NOT_FOUND[lang]
        out["total_s"] = round(time.perf_counter() - t0, 2)
        return out

    stage("answer")
    ans = answer(standalone, hits, cfg, setup, lang=lang)
    out |= {"text": ans.text, "refused": ans.refused, "reason": ans.refusal_reason, "cited": ans.cited,
            "evidence_hits": hits, "llm_s": round(ans.llm_seconds, 2), "llm_cached": ans.llm_cached}
    if intent in ("visual", "compare") and not ans.refused:
        stage("visual")
        preferred = "compare" if intent == "compare" else route.get("visual_type")
        vis = make_visual(standalone, hits, cfg, lang, preferred, answer_text=ans.text)
        out |= {"visual": vis["visual"], "visual_check": vis["check"], "visual_reason": vis["reason"]}
        if vis["visual"]:  # the visual's citations count as cited passages too
            out["cited"] = sorted(set(ans.cited) | _visual_cites(vis["visual"]))
    out["total_s"] = round(time.perf_counter() - t0, 2)
    return out


def _plan_items(plan: dict | None) -> list[dict]:
    if not plan:
        return []
    items = [x for k in PLAN_LISTS for x in plan.get(k, [])]
    return items + [c for h in plan.get("hazards", []) for c in h["controls"]]


def _visual_cites(v: dict) -> set[int]:
    cites: set[int] = set()
    for key in ("items", "limits", "intervals"):
        for x in v.get(key) or []:
            cites.update(x.get("cite") or [])
    for row in v.get("rows") or []:
        cites.update(row.get("cite_left") or [])
        cites.update(row.get("cite_right") or [])
    return cites
