"""Answer generation: prompt with numbered evidence -> Gemini -> answer with [n] citations.

All LLM calls go through `call_llm_record` / `call_llm`. To replace Gemini with a local or on-premise
model, change only these functions.

Refusal happens in two places:
1. Before the API call: if the best reranker score is below `answer.min_rerank_score`, we answer
   "not found" without calling the model (no cost, no chance to hallucinate).
2. In the prompt: the model must reply with the exact "not found" sentence if the evidence does not
   contain the answer.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from google.genai import types

from plant_rag.gemini_client import call_with_retry, get_client

if TYPE_CHECKING:
    from plant_rag.retrieve import Hit

log = logging.getLogger(__name__)

NOT_FOUND = {
    "en": "Not found in the provided documents.",
    "ko": "제공된 문서에서 찾을 수 없습니다.",
}
LANG_NAME = {"en": "English", "ko": "Korean"}

SYSTEM_PROMPT = """You answer questions about industrial process-safety standards and regulations.
Use ONLY the numbered evidence passages in the user message. Never use outside knowledge.

Rules:
1. Write the answer in {lang_name}, even if the evidence is in another language. Keep clause numbers,
   units and numeric values exactly as written in the evidence.
2. Every sentence that states a fact must end with the number(s) of the passage(s) that support it,
   like [1] or [2][3]. Cite only passages that really support the sentence.
3. Answer whenever the passages contain relevant information, even if they use a slightly different
   term than the question (e.g. 변경관리 vs 변경요소관리, "PHA" vs "process hazard analysis").
4. If the passages answer only part of the question, answer that part and say which part is not covered.
5. Only if NONE of the passages contains information that answers the question, reply with exactly
   this sentence and nothing else:
   {not_found}
6. Be concise: a direct answer first, then the key conditions or numbers. No introduction."""


# ------------------------------------------------------------------ LLM call

def _cache_path(cache_dir: Path, request: dict[str, Any]) -> Path:
    key = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return cache_dir / key[:2] / f"{key}.json"


def call_llm_record(prompt: str, cfg: dict[str, Any], system: str | None = None) -> dict[str, Any]:
    """Call the LLM (or read the cache). Returns the cached record plus "cached": True/False.

    Identical requests are served from cache/llm/ and never paid for twice.
    """
    llm = cfg["llm"]
    request = {
        "model": llm["model"],
        "system": system,
        "prompt": prompt,
        "temperature": llm["temperature"],
        "max_output_tokens": llm["max_output_tokens"],
    }
    thinking = llm.get("thinking_level")
    if thinking:  # only part of the cache key when set, so older cached calls stay valid
        request["thinking_level"] = thinking
    path = _cache_path(cfg["paths"]["llm_cache_dir"], request)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")) | {"cached": True}

    client = get_client(cfg)
    gen_config = types.GenerateContentConfig(
        temperature=llm["temperature"],
        max_output_tokens=llm["max_output_tokens"],
        system_instruction=system,
        thinking_config=types.ThinkingConfig(thinking_level=thinking.upper()) if thinking else None,
    )
    t0 = time.perf_counter()
    resp = call_with_retry(
        lambda: client.models.generate_content(model=llm["model"], contents=prompt, config=gen_config),
        cfg,
        what=f"generate_content({llm['model']})",
    )
    seconds = time.perf_counter() - t0

    text = resp.text or ""
    finish = str(resp.candidates[0].finish_reason) if resp.candidates else None
    usage = resp.usage_metadata.model_dump(exclude_none=True) if resp.usage_metadata else {}
    if not text:
        log.warning("Empty answer from %s (finish_reason=%s)", llm["model"], finish)
    elif finish and "MAX_TOKENS" in finish:
        log.warning("Answer cut off by max_output_tokens (thinking tokens: %s); raise llm.max_output_tokens",
                    usage.get("thoughts_token_count"))

    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "request": request,
        "text": text,
        "finish_reason": finish,
        "usage": usage,
        "seconds": round(seconds, 3),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)  # atomic: no half-written cache files if interrupted
    return record | {"cached": False}


def call_llm(prompt: str, cfg: dict[str, Any], system: str | None = None) -> str:
    """Return only the model's text answer (see call_llm_record)."""
    return call_llm_record(prompt, cfg, system)["text"]


# ------------------------------------------------------------------ query translation (setup E)

TRANSLATE_PROMPT = """Translate this question about industrial process safety into {lang_name}.
Keep numbers, units, equipment tags, abbreviations (PSM, HAZOP, MOC, PSSR, LEL ...) and regulation names.
Use the technical terms an engineer would use in {lang_name}. Output only the translated question.

Question: {question}"""


def translate_query(question: str, target_lang: str, cfg: dict[str, Any]) -> str:
    """Translate a question with the LLM (cached like every LLM call). Used so that keyword search and the
    reranker can compare the question with passages in the other language."""
    tcfg = cfg["retrieval"]["query_translation"]
    sub = {**cfg, "llm": {**cfg["llm"], "model": tcfg.get("model") or cfg["llm"]["model"],
                          "thinking_level": tcfg.get("thinking_level"), "max_output_tokens": 512}}
    prompt = TRANSLATE_PROMPT.format(lang_name=LANG_NAME[target_lang], question=question)
    return call_llm_record(prompt, sub)["text"].strip()


CONDENSE_PROMPT = """You rewrite follow-up questions in a chat about industrial process-safety documents.
Given the earlier conversation and the new message, write ONE self-contained question that can be searched
without the conversation (resolve "it", "that", "and for tanks?" etc.). Keep the language of the new message,
keep numbers, units and technical terms. If the new message is already self-contained, return it unchanged.
Output only the question.

Conversation:
{history}

New message: {question}"""


def condense_question(question: str, history: list[tuple[str, str]], cfg: dict[str, Any]) -> str:
    """Turn a chat follow-up into a standalone question (one cached LLM call). `history` = [(question, answer), ...]."""
    if not history:
        return question
    turns = []
    for q, a in history[-3:]:  # the last few exchanges are enough context
        turns.append(f"User: {q}\nAssistant: {re.sub(r'\s*\[\d+\]', '', a)[:600]}")
    tcfg = cfg["retrieval"]["query_translation"]  # same light settings as translation
    sub = {**cfg, "llm": {**cfg["llm"], "model": tcfg.get("model") or cfg["llm"]["model"],
                          "thinking_level": tcfg.get("thinking_level"), "max_output_tokens": 1024}}
    out = call_llm_record(CONDENSE_PROMPT.format(history="\n\n".join(turns), question=question), sub)["text"].strip()
    return out or question


# ------------------------------------------------------------------ answering

@dataclass
class Answer:
    question: str
    lang: str
    text: str
    refused: bool
    refusal_reason: str = ""                                # "low_score", "no_hits", "model" or ""
    cited: list[int] = field(default_factory=list)          # 1-based evidence numbers cited in the text
    evidence: list[Hit] = field(default_factory=list)
    llm_seconds: float = 0.0
    llm_cached: bool = False
    usage: dict[str, Any] = field(default_factory=dict)


def detect_lang(text: str) -> str:
    """Korean if the question contains Hangul, otherwise English."""
    return "ko" if re.search(r"[가-힣]", text) else "en"


def format_location(chunk: dict) -> str:
    pages = f"p. {chunk['page_start']}" if chunk["page_start"] == chunk["page_end"] else \
        f"pp. {chunk['page_start']}–{chunk['page_end']}"
    return f"{chunk['title']}, {chunk['clause_id']}, {pages}"


def build_prompt(question: str, hits: list[Hit], lang: str) -> tuple[str, str]:
    system = SYSTEM_PROMPT.format(lang_name=LANG_NAME[lang], not_found=NOT_FOUND[lang])
    blocks = []
    for n, h in enumerate(hits, 1):
        c = h.chunk
        context = f" ({c['section']})" if c.get("section") else ""
        blocks.append(f"[{n}] {format_location(c)}{context}\n{c['text']}")
    prompt = f"Question: {question}\n\nEvidence passages:\n\n" + "\n\n".join(blocks)
    return system, prompt


def parse_citations(text: str, n_evidence: int) -> list[int]:
    """Distinct cited numbers in order of first use; numbers outside 1..n are ignored."""
    seen: list[int] = []
    for m in re.finditer(r"\[(\d+(?:\s*[,，]\s*\d+)*)\]", text):  # [1] and [1, 2]
        for num in re.split(r"\s*[,，]\s*", m.group(1)):
            n = int(num)
            if 1 <= n <= n_evidence and n not in seen:
                seen.append(n)
    return seen


def is_refusal(text: str) -> bool:
    t = text.strip()
    return any(t.startswith(s.rstrip(".")) for s in NOT_FOUND.values())


def refusal_threshold(cfg: dict[str, Any], setup: str | None = None) -> float:
    """`answer.min_rerank_score` is a number, or a {setup: number} map (tuned per setup on the dev split)."""
    t = cfg["answer"]["min_rerank_score"]
    if isinstance(t, dict):
        setup = setup or cfg["retrieval"]["default_setup"]
        return float(t.get(setup, t.get("default", 0.0)))
    return float(t)


def answer(question: str, hits: list[Hit], cfg: dict[str, Any], setup: str | None = None) -> Answer:
    lang = detect_lang(question)
    if not hits:
        return Answer(question, lang, NOT_FOUND[lang], True, "no_hits")
    top = hits[0].rerank_score
    threshold = refusal_threshold(cfg, setup)
    if top is not None and top < threshold:
        return Answer(question, lang, NOT_FOUND[lang], True, "low_score", evidence=hits)

    system, prompt = build_prompt(question, hits, lang)
    rec = call_llm_record(prompt, cfg, system)
    text = rec["text"].strip()
    refused = is_refusal(text)
    return Answer(
        question=question, lang=lang, text=text, refused=refused,
        refusal_reason="model" if refused else "",
        cited=[] if refused else parse_citations(text, len(hits)),
        evidence=hits, llm_seconds=float(rec.get("seconds", 0.0)), llm_cached=bool(rec["cached"]),
        usage=rec.get("usage", {}),
    )
