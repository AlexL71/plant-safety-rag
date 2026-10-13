"""Answer generation.

All LLM calls go through `call_llm`. To replace Gemini with a local or on-premise model,
change only this function. Prompt building and citation parsing are added in Phase 2.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

from google.genai import types

from plant_rag.gemini_client import call_with_retry, get_client

log = logging.getLogger(__name__)


def _cache_path(cache_dir: Path, request: dict[str, Any]) -> Path:
    key = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return cache_dir / key[:2] / f"{key}.json"


def call_llm(prompt: str, cfg: dict[str, Any], system: str | None = None) -> str:
    """Return the model's text answer. Identical requests are served from cache/llm/ and never paid for twice."""
    llm = cfg["llm"]
    request = {
        "model": llm["model"],
        "system": system,
        "prompt": prompt,
        "temperature": llm["temperature"],
        "max_output_tokens": llm["max_output_tokens"],
    }
    path = _cache_path(cfg["paths"]["llm_cache_dir"], request)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["text"]

    client = get_client(cfg)
    gen_config = types.GenerateContentConfig(
        temperature=llm["temperature"],
        max_output_tokens=llm["max_output_tokens"],
        system_instruction=system,
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
    return text
