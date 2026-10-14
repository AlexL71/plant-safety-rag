"""SafetyAgent: one entry point that understands a request, plans the search and uses the right tools.

Step 1, the planner (one light model call with structured output) reads the request and the last chat turns and
returns:
    tool       answer | task_plan | notice | chitchat
    visual     none | steps | checklist | limits | intervals | compare  (added under the answer when it helps)
    question   the request as a complete question (follow-ups resolved), in the user's language
    query_ko / query_en   search queries in the documents' own words (헬멧 -> 안전모, 복장 -> 보호구), both languages
    country    KR | US | both  (which documents to search)

Step 2, the tools (all grounded in the same evidence passages, all checked before anything is shown):
    search_rules   hybrid search + reranker; setup F searches the user's words AND the planner's queries, filtered
                   by country (retrieve.Retriever.search)
    answer         cited answer to the user's own question, or "not found" (generate.answer)
    make_visual    a chart / checklist / timeline / Korea-vs-US table when the planner says it helps
    plan_task      job -> hazards -> one search per hazard -> cited plan + TBM script
    draft_notice   poster / TBM sheet content (notices.draft_notice), edited and approved in the web app

The agent is a small, fixed state machine (planner + at most ~3 tool steps, every step shown in the progress list)
rather than an open-ended loop: easier to explain, test and measure.
"""
from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Any, Callable

from plant_rag.checks import check_elements, merge_stats
from plant_rag.generate import LANG_NAME, NOT_FOUND, answer, call_llm_record, detect_lang, light_cfg, parse_json
from plant_rag.notices import draft_notice
from plant_rag.visuals import VISUAL_TYPES, evidence_block, make_visual

if TYPE_CHECKING:
    from plant_rag.retrieve import Hit, Retriever

log = logging.getLogger(__name__)

TOOLS = ("answer", "task_plan", "notice", "chitchat")
COUNTRIES = ("KR", "US", "both")

# ------------------------------------------------------------------ planner

PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": list(TOOLS)},
        "visual": {"type": "string", "enum": [*VISUAL_TYPES, "none"]},
        "question": {"type": "string"},
        "question_translated": {"type": "string"},
        "query_ko": {"type": "string"},
        "query_en": {"type": "string"},
        "country": {"type": "string", "enum": list(COUNTRIES)},
        "reason": {"type": "string"},
    },
    "required": ["tool", "visual", "question", "question_translated", "query_ko", "query_en", "country", "reason"],
}

PLANNER_SYSTEM = """You are the planner of SafetyAgent, a workplace-safety assistant for workers on construction and
plant sites. It answers from Korean and US safety rules: the Korean OSH Act (산업안전보건법), the Safety and Health
Standards Rule (산업안전보건기준에 관한 규칙), the risk assessment guideline, KOSHA guides, and OSHA standards
(29 CFR 1910 / 1926). Read the conversation and the new message and return a JSON plan.

tool:
- answer: any question about a safety rule, requirement, number, procedure or comparison (the default).
- task_plan: the user describes a specific job they or a crew will do and wants to know what to prepare or check
  (permits, hazards, controls, PPE, pre-work checklist, TBM briefing).
- notice: the user asks to make a poster, flyer, notice, sign or leaflet to print, post or share.
- chitchat: greetings, thanks, questions about the assistant, or anything unrelated to workplace safety.

visual (only for tool "answer"; otherwise "none"). Most questions need none. Add one only when the answer has
several parts that are easier to see than to read:
- steps: a procedure of 3 or more ordered steps;  checklist: several things to confirm, provide or wear;
- limits: several numeric thresholds or a range (gas concentrations, several heights or distances);
- intervals: several time periods or frequencies (initial, every year, within 1 month);
- compare: the user compares Korea and the US (or two standards);
- none: a single number, a single fact, a yes/no answer, who / which, or a definition. When the user asks for a
  chart, table or visual, always pick the best-fitting type.

question: the new message as one complete question in the user's language. Resolve follow-ups from the
conversation ("그럼 미국은?" -> the full question about the US). Keep every name and number.

question_translated: the same complete question in the other language (Korean <-> English), as a natural question,
using the words the regulations use. Add nothing that the question does not say.

query_ko and query_en: one search query each, in Korean and in English, that would find the rule text. Use the
words the regulations use and fix misspellings (헬멧/핼멧 -> 안전모, hard hat -> head protection, 복장 -> 보호구 작업복,
안전벨트 at height -> 안전대 / personal fall arrest). Drop words about the output (make, show, poster, chart,
만들어 줘, 보여줘, 시각화). Keep regulation names and numbers the user wrote exactly (OSHA, 29 CFR 1910.146, 제32조,
2 m), but never add article, section or CFR numbers the user did not write: a wrong number finds the wrong rule.

country: KR if the user asks only about Korean rules, US if only about US / OSHA rules, otherwise both
(including comparisons and questions that name no country).

reason: a few English words."""


def plan_request(message: str, history: list[tuple[str, str]], cfg: dict[str, Any]) -> dict[str, Any]:
    """One cached, light model call. Falls back to a plain answer plan if the output is unusable."""
    turns = []
    for q, a in history[-int(cfg.get("web", {}).get("history_turns", 3)):]:
        a = re.sub(r"\s*\[\d+\]", "", a)[:500]  # citation marks mean nothing to the planner
        turns.append(f"User: {q}\nAssistant: {a}")
    convo = "\n\n".join(turns) if turns else "(none)"
    rec = call_llm_record(f"Conversation:\n{convo}\n\nNew message: {message}", light_cfg(cfg, 1024), PLANNER_SYSTEM,
                          json_schema=PLANNER_SCHEMA)
    try:
        p = parse_json(rec["text"])
        if p.get("tool") not in TOOLS:
            raise ValueError(p)
        plan = {
            "tool": p["tool"],
            "visual": p.get("visual") if p.get("visual") in VISUAL_TYPES and p["tool"] == "answer" else "none",
            "question": (p.get("question") or message).strip(),
            "question_translated": (p.get("question_translated") or "").strip(),
            "query_ko": (p.get("query_ko") or "").strip(),
            "query_en": (p.get("query_en") or "").strip(),
            "country": p.get("country") if p.get("country") in COUNTRIES else "both",
            "reason": p.get("reason", ""),
        }
    except (ValueError, KeyError) as exc:
        log.warning("Planner fallback: %s", exc)
        plan = {"tool": "answer", "visual": "none", "question": message, "question_translated": "", "query_ko": "", "query_en": "",
                "country": "both", "reason": "planner_fallback"}
    return plan | {"llm_s": rec.get("seconds", 0.0), "cached": rec["cached"]}


def plan_search(retriever: Retriever, plan: dict[str, Any], setup: str, k: int,
                on_stage: Callable[[str], None] | None = None, rerank_candidates: int | None = None) -> list[Hit]:
    """Search with the user's question plus the planner's queries, limited to the planner's country."""
    return retriever.search(plan["question"], setup=setup, k=k, on_stage=on_stage, rerank_candidates=rerank_candidates,
                            alt_queries={"ko": plan.get("query_ko", ""), "en": plan.get("query_en", ""),
                                         "question_translated": plan.get("question_translated", "")},
                            country=None if plan.get("country") == "both" else plan.get("country"))


# ------------------------------------------------------------------ task plan

DECOMPOSE_SCHEMA = {
    "type": "object",
    "properties": {
        "task_summary": {"type": "string"},
        "hazards": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "query_ko": {"type": "string"}, "query_en": {"type": "string"}},
            "required": ["name", "query_ko", "query_en"]}},
    },
    "required": ["task_summary", "hazards"],
}

DECOMPOSE_SYSTEM = """A worker describes a job. List the main workplace-safety hazard topics of this job that safety
rules would cover (for example hot work / fire, confined space / oxygen and gas, work at height / falls,
lockout of energy, forklifts and vehicles, heat, personal protective equipment, work permits).
Return 1 to {max_hazards} hazards, most important first. For each: a short name in {lang_name}, and one search
query in Korean and one in English that would find the rule text, in the words regulations use
(e.g. "밀폐공간 작업 전 산소 및 유해가스 농도 측정" / "confined space atmospheric testing before entry").
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
              stage: Callable[[str], None], country: str = "both") -> dict[str, Any]:
    acfg = cfg.get("agent", {})
    max_h = int(acfg.get("plan_max_hazards", 3))
    t0 = time.perf_counter()
    stage("plan")
    rec = call_llm_record(f"Job: {task}", light_cfg(cfg, 1024),
                          DECOMPOSE_SYSTEM.format(max_hazards=max_h, lang_name=LANG_NAME[lang]),
                          json_schema=DECOMPOSE_SCHEMA)
    try:
        dec = parse_json(rec["text"])
        hazards = [h for h in dec.get("hazards", []) if h.get("query_ko") or h.get("query_en")][:max_h]
    except ValueError:
        dec, hazards = {"task_summary": task}, []
    if not hazards:
        hazards = [{"name": task, "query_ko": "", "query_en": ""}]

    hits: list[Hit] = []
    per_hazard = int(acfg.get("plan_hits_per_hazard", 3))
    searched = []
    for h in hazards:
        stage("search")
        own = h.get(f"query_{lang}") or task
        found = plan_search(retriever, {"question": own, "query_ko": h.get("query_ko", ""),
                                        "query_en": h.get("query_en", ""), "country": country},
                            setup, per_hazard, rerank_candidates=int(acfg.get("plan_rerank_candidates", 6)))
        keep = [x for x in found if x.rerank_score is None or x.rerank_score >= float(acfg.get("plan_min_rerank", 0.05))]
        searched.append({"hazard": h["name"], "query": own, "found": len(keep)})
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
    "en": ("I'm SafetyAgent. Ask me about workplace-safety rules in Korean or English: I answer from Korean and US "
           "safety rules with the exact clause, and add a chart or checklist when it helps. I can also plan the "
           "safety checks for a job and draft a notice for your site. Try: \"What oxygen level is safe in a confined "
           "space?\""),
    "ko": ("저는 SafetyAgent입니다. 산업안전 규정에 대해 한국어나 영어로 물어보세요. 한국과 미국의 안전 규정을 근거로 "
           "조항을 표시해 답하고, 필요하면 그래프나 체크리스트도 함께 보여 드립니다. 작업 전 안전 점검 계획이나 현장 "
           "게시물 초안도 만들 수 있습니다. 예: \"밀폐공간 작업 시 적정 산소농도는?\""),
}


# ------------------------------------------------------------------ main entry

def run(question: str, history: list[tuple[str, str]], retriever: Retriever, cfg: dict[str, Any], setup: str,
        mode: str = "auto", lang: str | None = None,
        on_stage: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Handle one chat request. Returns JSON-ready data; the web app stores it as the message payload.
    `mode` "auto" lets the planner choose the tool; "answer", "task_plan" or "notice" force it (admin console)."""
    stage = on_stage or (lambda s: None)
    lang = lang if lang in LANG_NAME else detect_lang(question)
    t0 = time.perf_counter()
    stage("route")
    plan = plan_request(question, history, cfg)
    if mode in TOOLS and mode != "chitchat":
        plan["tool"] = mode
    tool = plan["tool"]
    out: dict[str, Any] = {"kind": "answer", "intent": tool, "plan": None, "route": plan, "lang": lang,
                           "setup": setup, "question": question, "mode": mode,
                           "standalone": plan["question"] if plan["question"] != question else None,
                           "search_query": plan.get(f"query_{lang}") or None, "country": plan["country"]}
    out.pop("plan")

    if tool == "chitchat":
        out |= {"kind": "chat", "text": CHITCHAT[lang], "refused": False, "cited": [], "evidence_hits": [],
                "search_query": None, "country": None}
        out["total_s"] = round(time.perf_counter() - t0, 2)
        return out

    if tool == "task_plan":
        res = plan_task(plan["question"], retriever, cfg, lang, setup, stage, plan["country"])
        hits = res["hits"]
        out |= {"kind": "plan", "plan": res["plan"], "plan_check": res.get("check", {}),
                "hazards_searched": res["hazards_searched"], "evidence_hits": hits,
                "refused": res["plan"] is None, "reason": res["reason"], "search_query": None,
                "cited": sorted({c for x in _plan_items(res["plan"]) for c in x["cite"]}) if res["plan"] else []}
        out["text"] = plan_as_text(res["plan"]) if res["plan"] else NOT_FOUND[lang]
        out["total_s"] = round(time.perf_counter() - t0, 2)
        return out

    k = int(cfg["retrieval"]["final_k"])
    compare = plan["visual"] == "compare" and plan["country"] == "both"
    hits = plan_search(retriever, plan, setup, 2 * k if compare else k, on_stage=stage)
    if compare:
        hits = balance_languages(hits, int(cfg.get("agent", {}).get("compare_per_language", 3)))
    out["timings"] = dict(retriever.timings)
    out["translated"] = getattr(retriever, "last_translation", None)

    if tool == "notice":
        stage("notice")
        res = draft_notice(plan["question"], hits, cfg, lang)
        out |= {"kind": "notice", "notice_content": res["content"], "notice_check": res["check"],
                "evidence_hits": hits, "refused": res["content"] is None, "reason": res["reason"],
                "cited": sorted({c for key in ("key_rules", "dos", "donts", "key_numbers")
                                 for x in (res["content"] or {}).get(key, []) for c in x["cite"]})}
        out["text"] = res["content"]["title"] if res["content"] else NOT_FOUND[lang]
        out["total_s"] = round(time.perf_counter() - t0, 2)
        return out

    stage("answer")
    ans = answer(plan["question"], hits, cfg, setup, lang=lang)
    out |= {"text": ans.text, "refused": ans.refused, "reason": ans.refusal_reason, "cited": ans.cited,
            "evidence_hits": hits, "llm_s": round(ans.llm_seconds, 2), "llm_cached": ans.llm_cached}
    if plan["visual"] in VISUAL_TYPES and not ans.refused:
        stage("visual")
        vis = make_visual(plan["question"], hits, cfg, lang, plan["visual"], answer_text=ans.text)
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
