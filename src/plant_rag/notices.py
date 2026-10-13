"""Safety notices (posters, leaflets, TBM sheets): evidence -> structured content -> checks -> translation.

1. `draft_notice` asks the model to fill a fixed JSON layout (headline, key rules, do / don't, key numbers),
   every line citing evidence numbers. `checks.check_elements` drops lines without a valid citation and lines
   with a number that is not in the cited passage.
2. `translate_notice` translates the checked content into a second language (e.g. for foreign workers) and
   back into the source language. The back-translation is stored next to each line so a reviewer who cannot
   read the second language can still compare meaning, and every line is checked automatically: the numbers in
   the translation and in the back-translation must equal the numbers in the original.
3. A person approves the notice in the web app before it is printed or shared; drafts carry a "DRAFT" mark.

The layout and printing live in the web app; this module only produces checked content.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from typing import TYPE_CHECKING, Any

from plant_rag.checks import check_elements, merge_stats, numbers_in
from plant_rag.generate import LANG_NAME, call_llm_record, parse_json
from plant_rag.visuals import evidence_block

if TYPE_CHECKING:
    from plant_rag.retrieve import Hit

log = logging.getLogger(__name__)

# Languages offered for the second language of a notice. KOSHA publishes materials for foreign workers in many of
# these; machine translation is marked "review before use".
NOTICE_LANGS = {
    "ko": "Korean", "en": "English", "vi": "Vietnamese", "th": "Thai", "id": "Indonesian", "ne": "Nepali",
    "uz": "Uzbek", "zh": "Chinese (Simplified)", "mn": "Mongolian", "km": "Khmer", "my": "Burmese",
    "tl": "Filipino", "si": "Sinhala", "bn": "Bengali", "ur": "Urdu", "ky": "Kyrgyz", "lo": "Lao",
}
LINE_LISTS = ("key_rules", "dos", "donts")

_CITE = {"type": "array", "items": {"type": "integer"}}
_LINE = {"type": "object", "properties": {"text": {"type": "string"}, "cite": _CITE}, "required": ["text", "cite"]}
SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "key_rules": {"type": "array", "items": _LINE},
        "dos": {"type": "array", "items": _LINE},
        "donts": {"type": "array", "items": _LINE},
        "key_numbers": {"type": "array", "items": {"type": "object", "properties": {
            "label": {"type": "string"}, "value": {"type": "string"}, "cite": _CITE},
            "required": ["label", "value", "cite"]}},
    },
    "required": ["found", "title", "key_rules"],
}

SYSTEM = """You write a workplace safety notice (a poster to print and post on site) from evidence passages.
Use ONLY the numbered passages. Never add rules, numbers or advice that are not in them.

Write for workers on site, in {lang_name}: short, plain, imperative sentences ("Wear a safety helmet ...").
- title: a short headline, at most 40 characters.
- subtitle: one line saying what the notice is about, at most 90 characters.
- key_rules: the 3 to 5 most important rules, each at most 120 characters.
- dos / donts: 0 to 4 short lines each, only if the passages support them.
- key_numbers: 0 to 4 important values (limit, distance, time), value exactly as in the passage with its unit.
Every line cites the passage number(s) that support it. Keep numbers and units exactly as in the passages.
If the passages do not contain rules about the requested topic, set found to false and leave the lists empty."""

TRANSLATE_SYSTEM = """You translate a workplace safety notice. Translate every text field from {src} into {dst}
for workers on a construction or factory site: plain words, short sentences. Keep the JSON structure, keep every
number, unit and citation list exactly, do not add or drop content. Output only the JSON."""

_TR_LINE = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
TR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"}, "subtitle": {"type": "string"},
        "key_rules": {"type": "array", "items": _TR_LINE},
        "dos": {"type": "array", "items": _TR_LINE},
        "donts": {"type": "array", "items": _TR_LINE},
        "key_numbers": {"type": "array", "items": {"type": "object", "properties": {
            "label": {"type": "string"}, "value": {"type": "string"}}, "required": ["label", "value"]}},
    },
    "required": ["title", "key_rules"],
}


def _sub_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    ncfg = cfg.get("notices", {})
    return {**cfg, "llm": {**cfg["llm"], "max_output_tokens": int(ncfg.get("max_output_tokens", 4096)),
                           "thinking_level": ncfg.get("thinking_level") or cfg["llm"].get("thinking_level")}}


def draft_notice(topic: str, hits: list[Hit], cfg: dict[str, Any], lang: str = "ko") -> dict[str, Any]:
    """Return {"content": checked content or None, "check": stats, "reason": str, "llm_s": float}."""
    if not hits:
        return {"content": None, "check": {}, "reason": "no_evidence", "llm_s": 0.0}
    prompt = f"Notice topic: {topic}\n\nEvidence passages:\n\n{evidence_block(hits)}"
    rec = call_llm_record(prompt, _sub_cfg(cfg), SYSTEM.format(lang_name=NOTICE_LANGS.get(lang, "English")),
                          json_schema=SCHEMA)
    try:
        raw = parse_json(rec["text"])
    except ValueError as exc:
        log.warning("Notice: %s", exc)
        return {"content": None, "check": {}, "reason": "invalid_json", "llm_s": rec.get("seconds", 0.0)}
    if not raw.get("found", True):
        return {"content": None, "check": {}, "reason": "not_found", "llm_s": rec.get("seconds", 0.0), "raw": raw}

    passages = {n: h.chunk for n, h in enumerate(hits, 1)}
    results, content = [], {"title": raw.get("title", "").strip(), "subtitle": raw.get("subtitle", "").strip()}
    for key in LINE_LISTS:
        r = check_elements(raw.get(key) or [], ("text",), passages)
        content[key] = r.kept
        results.append(r)
    r = check_elements(raw.get("key_numbers") or [], ("label", "value"), passages)
    content["key_numbers"] = r.kept
    results.append(r)
    stats = merge_stats(*results)
    if not content["key_rules"]:
        return {"content": None, "check": stats, "reason": "no_checked_rules", "llm_s": rec.get("seconds", 0.0),
                "raw": raw}
    content["lang"] = lang
    return {"content": content, "check": stats, "reason": "", "llm_s": rec.get("seconds", 0.0), "raw": raw}


# ------------------------------------------------------------------ translation + back-translation check

def _strip_for_translation(content: dict) -> dict:
    out = {"title": content.get("title", ""), "subtitle": content.get("subtitle", "")}
    for key in LINE_LISTS:
        out[key] = [{"text": x["text"]} for x in content.get(key) or []]
    out["key_numbers"] = [{"label": x["label"], "value": x["value"]} for x in content.get("key_numbers") or []]
    return out


def _translate(content: dict, src: str, dst: str, cfg: dict[str, Any]) -> dict:
    system = TRANSLATE_SYSTEM.format(src=NOTICE_LANGS.get(src, src), dst=NOTICE_LANGS.get(dst, dst))
    rec = call_llm_record(json.dumps(_strip_for_translation(content), ensure_ascii=False, indent=1), _sub_cfg(cfg), system, json_schema=TR_SCHEMA)
    return parse_json(rec["text"])


def _fields(content: dict) -> list[tuple[str, str]]:
    """(field path, text) for every translatable text, in a fixed order."""
    out = [("title", content.get("title", "")), ("subtitle", content.get("subtitle", ""))]
    for key in LINE_LISTS:
        out += [(f"{key}.{i}", x.get("text", "")) for i, x in enumerate(content.get(key) or [])]
    out += [(f"key_numbers.{i}", f"{x.get('label', '')} {x.get('value', '')}")
            for i, x in enumerate(content.get("key_numbers") or [])]
    return out


def translate_notice(content: dict, target: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Translate checked content into `target` and back. Returns {"translation", "back", "line_checks", "ok"}.

    A line passes when the numbers (as a multiset) in the original, the translation and the back-translation are
    equal. Structure must match too (same number of lines per list)."""
    src = content.get("lang", "ko")
    if target == src or target not in NOTICE_LANGS:
        raise ValueError(f"unsupported target language: {target}")
    tr = _translate(content, src, target, cfg)
    back = _translate({**tr, "lang": target}, target, src, cfg)
    orig_f, tr_f, back_f = _fields(content), _fields(tr), _fields(back)
    checks = []
    tr_map, back_map = dict(tr_f), dict(back_f)
    for path, text in orig_f:
        if not text:
            continue
        t, b = tr_map.get(path), back_map.get(path)
        n0 = Counter(numbers_in(text))
        ok = t is not None and b is not None and Counter(numbers_in(t)) == n0 and Counter(numbers_in(b)) == n0
        checks.append({"field": path, "ok": ok, "back": b or ""})
    # keep the citation lists of the original lines in the translation
    for key in LINE_LISTS:
        for i, x in enumerate(tr.get(key) or []):
            if i < len(content.get(key) or []):
                x["cite"] = content[key][i]["cite"]
    for i, x in enumerate(tr.get("key_numbers") or []):
        if i < len(content.get("key_numbers") or []):
            x["cite"] = content["key_numbers"][i]["cite"]
    tr["lang"] = target
    return {"translation": tr, "back": back, "line_checks": checks,
            "ok": all(c["ok"] for c in checks) and len(tr_f) == len(orig_f)}
