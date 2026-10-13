"""Visual explanations: evidence passages -> one structured visual spec (JSON), checked before it is shown.

The model never writes chart code. It fills one of five fixed types, and the web app draws them:

    steps      a procedure in order (e.g. work-permit flow)
    checklist  things to confirm or provide before/while working
    compare    Korea vs US (or two documents) side by side, one row per aspect
    limits     numeric thresholds on a scale (e.g. oxygen 18-23.5 % for a safe atmosphere)
    intervals  time periods and frequencies (inspection every year, fire watch 30 minutes ...)

Every element cites evidence numbers [n]. `checks.check_elements` then drops elements without a valid citation
and elements with a number that is not in the cited passage (numbers guard). If too little survives, there is
no visual (the text answer stays). The check statistics are returned so they can be evaluated.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from plant_rag.checks import CheckResult, check_elements, merge_stats
from plant_rag.generate import LANG_NAME, call_llm_record, format_location, parse_json

if TYPE_CHECKING:
    from plant_rag.retrieve import Hit

log = logging.getLogger(__name__)

VISUAL_TYPES = ("steps", "checklist", "compare", "limits", "intervals")
INTERVAL_UNITS = ("minutes", "hours", "days", "weeks", "months", "years")

_CITE = {"type": "array", "items": {"type": "integer"}}
SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": [*VISUAL_TYPES, "none"]},
        "title": {"type": "string"},
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "label": {"type": "string"}, "detail": {"type": "string"}, "cite": _CITE},
            "required": ["label", "cite"]}},
        "left_label": {"type": "string"},
        "right_label": {"type": "string"},
        "rows": {"type": "array", "items": {"type": "object", "properties": {
            "aspect": {"type": "string"}, "left": {"type": "string"}, "right": {"type": "string"},
            "cite_left": _CITE, "cite_right": _CITE},
            "required": ["aspect", "left", "right", "cite_left", "cite_right"]}},
        "limits": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "unit": {"type": "string"},
            "bound": {"type": "string", "enum": ["range", "below", "above"]},
            "low": {"type": "number"}, "high": {"type": "number"},
            "note": {"type": "string"}, "cite": _CITE},
            "required": ["name", "unit", "bound", "cite"]}},
        "intervals": {"type": "array", "items": {"type": "object", "properties": {
            "label": {"type": "string"}, "value": {"type": "number"},
            "unit": {"type": "string", "enum": list(INTERVAL_UNITS)},
            "kind": {"type": "string", "enum": ["every", "within", "at_least", "at_most"]},
            "cite": _CITE},
            "required": ["label", "value", "unit", "kind", "cite"]}},
    },
    "required": ["type", "title"],
}

SYSTEM = """You turn evidence passages about workplace-safety rules into ONE structured visual.
Use ONLY the numbered passages. Never add facts, numbers or rules that are not in them.

Pick the type (or use the requested one if it fits the passages):
- steps: a procedure or sequence (do A, then B ...). Fill `items` in order.
- checklist: things to confirm, provide or wear. Fill `items`.
- compare: two jurisdictions or documents side by side (left = Korea, right = US, unless the question says
  otherwise). Fill `left_label`, `right_label` and `rows` (one row per aspect; write "-" with an empty cite list
  if a side does not cover that aspect).
- limits: numeric thresholds (concentrations, heights, distances, loads). Fill `limits`: bound "range" uses low
  and high, "below" means the value must stay under `high`, "above" means at least `low`.
- intervals: time periods and frequencies. Fill `intervals` (value + unit; kind "every" for repeating duties,
  "within" for deadlines, "at_least"/"at_most" for durations).
If the passages do not support a useful visual, return type "none".

Rules:
1. Write all labels in {lang_name}. Keep numbers, units and clause numbers exactly as in the passages.
2. Every element cites the passage number(s) that support it (cite, cite_left, cite_right).
3. 3 to 8 elements. Labels at most 60 characters, details at most 140.
4. Title: what the visual shows, at most 60 characters."""

JURISDICTION = {"ko": "Korea", "en": "US"}


def evidence_block(hits: list[Hit]) -> str:
    blocks = []
    for n, h in enumerate(hits, 1):
        c = h.chunk
        blocks.append(f"[{n}] ({JURISDICTION.get(c['lang'], c['lang'])}) {format_location(c)}\n{c['text']}")
    return "\n\n".join(blocks)


def _check(spec: dict, passages: dict[int, dict]) -> tuple[dict, dict[str, Any]]:
    """Run the citation check and numbers guard on the elements of a spec. Returns (cleaned spec, stats)."""
    kind = spec["type"]
    out = {k: spec[k] for k in ("type", "title") if k in spec}
    if kind in ("steps", "checklist"):
        res = check_elements(spec.get("items") or [], ("label", "detail"), passages)
        out["items"] = res.kept
        results = [res]
    elif kind == "limits":
        lims = [{**x, "low_s": str(x.get("low", "")) if x.get("bound") in ("range", "above") else "",
                 "high_s": str(x.get("high", "")) if x.get("bound") in ("range", "below") else ""}
                for x in spec.get("limits") or []]
        res = check_elements(lims, ("name", "note", "low_s", "high_s"), passages)
        out["limits"] = [{k: v for k, v in x.items() if k not in ("low_s", "high_s")} for x in res.kept]
        results = [res]
    elif kind == "intervals":
        ivs = [{**x, "value_s": str(x.get("value", ""))} for x in spec.get("intervals") or []]
        res = check_elements(ivs, ("label", "value_s"), passages)
        out["intervals"] = [{k: v for k, v in x.items() if k != "value_s"} for x in res.kept]
        results = [res]
    elif kind == "compare":
        rows, res = [], CheckResult()
        for row in spec.get("rows") or []:
            side_ok = True
            for side in ("left", "right"):
                text, cites = str(row.get(side) or "").strip(), row.get(f"cite_{side}") or []
                if text in ("", "-", "—") and not cites:
                    continue  # this side does not cover the aspect: allowed, nothing to check
                r = check_elements([{"t": text, "aspect": row.get("aspect", ""), "cite": cites}], ("t",), passages)
                if r.dropped:
                    side_ok = False
                    res.dropped.append({"element": row, "reason": r.dropped[0]["reason"]})
                    break
                row = {**row, f"cite_{side}": r.kept[0]["cite"]}
            if side_ok:
                res.kept.append(row)
                rows.append(row)
        out |= {"left_label": spec.get("left_label") or "Korea", "right_label": spec.get("right_label") or "US",
                "rows": rows}
        results = [res]
    else:
        return out, {"elements": 0, "kept": 0, "dropped": 0}
    return out, merge_stats(*results)


def n_elements(spec: dict) -> int:
    return len(spec.get("items") or spec.get("rows") or spec.get("limits") or spec.get("intervals") or [])


def make_visual(question: str, hits: list[Hit], cfg: dict[str, Any], lang: str = "en",
                preferred: str | None = None, answer_text: str | None = None) -> dict[str, Any]:
    """Return {"visual": spec or None, "check": stats, "reason": str, "llm_s": float}."""
    if not hits:
        return {"visual": None, "check": {}, "reason": "no_evidence", "llm_s": 0.0}
    vcfg = cfg.get("visuals", {})
    sub = {**cfg, "llm": {**cfg["llm"], "max_output_tokens": int(vcfg.get("max_output_tokens", 4096)),
                          "thinking_level": vcfg.get("thinking_level") or cfg["llm"].get("thinking_level")}}
    want = preferred if preferred in VISUAL_TYPES else "choose the best type"
    prompt = (f"Question: {question}\nRequested type: {want}\n"
              + (f"\nAnswer already given to the user (for context, cite passages not this):\n{answer_text}\n" if answer_text else "")
              + f"\nEvidence passages:\n\n{evidence_block(hits)}")
    rec = call_llm_record(prompt, sub, SYSTEM.format(lang_name=LANG_NAME.get(lang, "English")), json_schema=SCHEMA)
    try:
        spec = parse_json(rec["text"])
    except ValueError as exc:
        log.warning("Visual: %s", exc)
        return {"visual": None, "check": {}, "reason": "invalid_json", "llm_s": rec.get("seconds", 0.0)}
    if spec.get("type") not in VISUAL_TYPES:
        return {"visual": None, "check": {}, "reason": "model_chose_none", "llm_s": rec.get("seconds", 0.0)}
    passages = {n: h.chunk for n, h in enumerate(hits, 1)}
    cleaned, stats = _check(spec, passages)
    min_el = int(vcfg.get("min_elements", 2))
    if n_elements(cleaned) < min_el:
        return {"visual": None, "check": stats, "reason": "too_few_checked_elements", "llm_s": rec.get("seconds", 0.0),
                "raw": spec}
    cleaned["lang"] = lang
    return {"visual": cleaned, "check": stats, "reason": "", "llm_s": rec.get("seconds", 0.0), "raw": spec}
