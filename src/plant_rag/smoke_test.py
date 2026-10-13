"""Phase 0 smoke test: one answer call + one embedding call, each repeated to prove the cache works.

    python -m plant_rag.smoke_test --list-models     # show models this API key can use (free call)
    python -m plant_rag.smoke_test                   # run the test (a few hundred tokens, well under US$0.01)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time

import numpy as np

from plant_rag.config import load_api_key, load_config
from plant_rag.embed import TASK_DOCUMENT, TASK_QUERY, embed_texts
from plant_rag.gemini_client import api_call_count, call_with_retry, get_client
from plant_rag.generate import call_llm


def list_models(cfg: dict) -> None:
    client = get_client(cfg)
    models = call_with_retry(lambda: list(client.models.list()), cfg, what="models.list")
    for action in ("generateContent", "embedContent"):
        names = sorted(
            m.name.removeprefix("models/") for m in models if action in (getattr(m, "supported_actions", None) or [])
        )
        print(f"\n[{action}] {len(names)} models")
        for n in names:
            print("  ", n)


def run(cfg: dict) -> None:
    _, source = load_api_key(cfg)
    print(f"API key: loaded from {source}")
    print(f"Answer model: {cfg['llm']['model']} | Embedding model: {cfg['embedding']['model']} "
          f"(dim {cfg['embedding']['output_dim']})")

    # 1) Answer model, then the same call again (must come from cache)
    prompt = "In one short sentence, what does a pressure relief valve do? Answer in Korean."
    for label in ("first call", "second call"):
        before, t0 = api_call_count(), time.perf_counter()
        text = call_llm(prompt, cfg)
        print(f"\n[LLM {label}] API requests: {api_call_count() - before} | {time.perf_counter() - t0:.2f}s")
        print("  answer:", text.strip()[:300])
    newest = max(cfg["paths"]["llm_cache_dir"].rglob("*.json"), key=lambda p: p.stat().st_mtime)
    usage = json.loads(newest.read_text(encoding="utf-8"))["usage"]
    print("  token usage:", {k: v for k, v in usage.items() if k.endswith("token_count")})

    # 2) Embeddings: Korean / English on the same topic, plus an unrelated sentence
    docs = [
        "압력방출장치는 설비의 최고사용압력 이하에서 작동하도록 설정하여야 한다.",
        "Pressure relief devices shall be set to operate at or below the maximum allowable working pressure.",
        "The staff cafeteria serves lunch from 11:30 to 13:00.",
    ]
    query = "안전밸브 설정압력 기준"
    for label in ("first call", "second call"):
        before, t0 = api_call_count(), time.perf_counter()
        d = embed_texts(docs, TASK_DOCUMENT, cfg)
        q = embed_texts([query], TASK_QUERY, cfg)
        print(f"\n[Embedding {label}] API requests: {api_call_count() - before} | {time.perf_counter() - t0:.2f}s")
    print(f"  shape: {d.shape}, norms: {np.round(np.linalg.norm(d, axis=1), 4).tolist()}")
    sims = (d @ q[0]).round(3).tolist()
    print(f"  query: {query}")
    for s, t in zip(sims, docs):
        print(f"    {s:+.3f}  {t[:70]}")
    ok = sims[0] > sims[2] and sims[1] > sims[2]
    print(f"  cross-language check (both relief-valve sentences beat the unrelated one): {'PASS' if ok else 'FAIL'}")


def main() -> None:
    # Korean output on Windows consoles that are not UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--list-models", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx", "google_genai"):  # request URLs and SDK notices
        logging.getLogger(noisy).setLevel(logging.WARNING)

    cfg = load_config(args.config)
    list_models(cfg) if args.list_models else run(cfg)


if __name__ == "__main__":
    main()
