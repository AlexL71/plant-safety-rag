"""Search: BM25 + dense -> RRF -> reranker. Every stage can be switched on/off per setup.

Setups (configs/config.yaml, `retrieval.setups`), used for the ablation in Phase 3:
    A = BM25 only, B = dense only, C = hybrid (RRF), D = hybrid + reranker (default)

RRF (Reciprocal Rank Fusion) merges ranked lists by rank, not by score:
    score(chunk) = sum over lists of 1 / (rrf_k + rank)
so BM25 scores and cosine similarities never need to be on the same scale.

The reranker (BAAI/bge-reranker-v2-m3) reads question and passage together and outputs a relevance
score in 0..1. It is the slowest stage (CPU), so it only sees the top `rerank_candidates` passages.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

from plant_rag.embed import TASK_QUERY, embed_texts
from plant_rag.index import bm25_tokenize, chunks_path, file_sha256, index_paths, load_chunks, passage_text

log = logging.getLogger(__name__)


@dataclass
class Hit:
    chunk: dict
    score: float                                         # final ranking score of this setup
    ranks: dict[str, int] = field(default_factory=dict)  # 1-based rank per stage: bm25, dense, rrf, rerank
    rerank_score: float | None = None


class Retriever:
    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg
        self.rcfg = cfg["retrieval"]
        paths = index_paths(cfg)
        if not paths["meta"].exists():
            raise FileNotFoundError("Index not found. Run: python -m plant_rag.index")
        meta = json.loads(paths["meta"].read_text(encoding="utf-8"))
        self.chunks = load_chunks(cfg)
        if [c["chunk_id"] for c in self.chunks] != meta["chunk_ids"]:
            raise RuntimeError("chunks.jsonl does not match the index. Run: python -m plant_rag.index")
        if meta["chunks_sha256"] != file_sha256(chunks_path(cfg)):
            log.warning("chunks.jsonl changed since the index was built; consider re-running plant_rag.index")
        if meta["embedding_model"] != cfg["embedding"]["model"] or meta["embedding_dim"] != int(cfg["embedding"]["output_dim"]):
            raise RuntimeError("Embedding settings changed since the index was built. Run: python -m plant_rag.index")

        self.with_header = bool(meta["passage_header"])
        self.faiss = faiss.deserialize_index(np.frombuffer(paths["faiss"].read_bytes(), dtype=np.uint8))
        self.bm25 = BM25Okapi(json.loads(paths["bm25"].read_text(encoding="utf-8")))
        self._reranker = None
        self.timings: dict[str, float] = {}

    # ------------------------------------------------------------ stages
    def bm25_search(self, query: str, k: int, allowed: np.ndarray | None = None) -> list[tuple[int, float]]:
        scores = self.bm25.get_scores(bm25_tokenize(query))
        if allowed is not None:
            scores = np.where(allowed, scores, 0.0)
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top if scores[i] > 0]

    def dense_search(self, query: str, k: int, allowed: np.ndarray | None = None) -> list[tuple[int, float]]:
        q = embed_texts([query], TASK_QUERY, self.cfg)
        scores, idx = self.faiss.search(q, k if allowed is None else min(len(self.chunks), 4 * k))
        hits = [(int(i), float(s)) for i, s in zip(idx[0], scores[0]) if i >= 0 and (allowed is None or allowed[i])]
        return hits[:k]

    def country_mask(self, country: str | None) -> np.ndarray | None:
        """Chunks of one jurisdiction: "KR" = Korean documents, "US" = English (OSHA) documents, else all.
        In this corpus the document language and the country coincide (see data/manifest.csv)."""
        lang = {"KR": "ko", "US": "en"}.get((country or "").upper())
        if not lang:
            return None
        return np.array([c["lang"] == lang for c in self.chunks])

    @staticmethod
    def rrf(lists: list[list[tuple[int, float]]], rrf_k: int) -> list[tuple[int, float]]:
        fused: dict[int, float] = {}
        for ranked in lists:
            for rank, (i, _) in enumerate(ranked, start=1):
                fused[i] = fused.get(i, 0.0) + 1.0 / (rrf_k + rank)
        return sorted(fused.items(), key=lambda x: -x[1])

    @property
    def reranker(self):
        if self._reranker is None:
            import os

            import torch
            from sentence_transformers import CrossEncoder

            rc = self.cfg["reranker"]
            if rc["device"] == "cpu":
                torch.set_num_threads(int(rc.get("num_threads") or 0) or os.cpu_count() or 1)
            t0 = time.perf_counter()
            kwargs = dict(max_length=int(rc["max_length"]), device=rc["device"])
            try:  # use the local copy without asking the Hugging Face Hub (saves ~25 s at start-up)
                self._reranker = CrossEncoder(rc["model"], local_files_only=True, **kwargs)
            except Exception:  # not downloaded yet: download once (~2.3 GB)
                self._reranker = CrossEncoder(rc["model"], **kwargs)
            log.info("Reranker loaded in %.1fs", time.perf_counter() - t0)
        return self._reranker

    def rerank(self, query: str | dict[str, str], idxs: list[int]) -> list[float]:
        """Score passages. With a {lang: question} dict, each passage is scored against the question in its own
        language (the reranker scores cross-language pairs far lower; see setup E)."""
        def q_for(i: int) -> str:
            if isinstance(query, str):
                return query
            return query.get(self.chunks[i]["lang"], next(iter(query.values())))

        pairs = [(q_for(i), passage_text(self.chunks[i], self.with_header)) for i in idxs]
        scores = self.reranker.predict(pairs, batch_size=int(self.cfg["reranker"]["batch_size"]),
                                       show_progress_bar=False)
        return [float(s) for s in scores]

    def _rerank_pool(self, ranked: list[tuple[int, float]], lists: dict[str, list[tuple[int, float]]],
                     size: int | None = None) -> list[int]:
        """Candidates for the reranker: the top `rerank_min_per_list` of every search list first, then the
        best of the fused ranking, up to `rerank_candidates`.

        Why: for a Korean question whose answer is only in an English document, BM25 finds nothing in
        English, so RRF pushes the dense list's best hit down (seen: dense rank 2 -> RRF rank 18).
        """
        size = int(size or self.rcfg["rerank_candidates"])
        per_list = min(int(self.rcfg["rerank_min_per_list"]), size)
        if len(lists) > 4:  # planner: up to 3 query versions x 2 methods; at least 2 per list still reach the reranker
            per_list = max(2, min(per_list, size // len(lists)))
        pool: list[int] = []
        for lst in lists.values():
            for i, _ in lst[:per_list]:
                if i not in pool:
                    pool.append(i)
        for i, _ in ranked:  # fill up with the fused ranking
            if len(pool) >= size:
                break
            if i not in pool:
                pool.append(i)
        return pool

    # ------------------------------------------------------------ main entry
    def search(self, query: str, setup: str | None = None, k: int | None = None,
               on_stage: Callable[[str], None] | None = None, rerank_candidates: int | None = None,
               alt_queries: dict[str, str] | None = None, country: str | None = None) -> list[Hit]:
        """Return the top-k hits for `query` under `setup` (A–F). Stage times go to self.timings.
        `rerank_candidates` overrides the config (the task planner reranks fewer passages per hazard).

        Setup F ("planner": true) takes the agent's search plan: `alt_queries` = {"ko": ..., "en": ...} (the request
        rewritten in the documents' words, in both languages) are searched next to the original question, and
        `country` ("KR" / "US") limits the search to one jurisdiction. Passages in the other language are reranked
        against alt_queries["question_translated"] (a full question; the reranker reads questions, not keyword lists).
        Without a plan, F behaves like E.

        Setup E ("translate": true) also translates the question into the other corpus language (one cached
        LLM call), runs BM25 and dense search for both versions, and reranks each passage against the
        question in the passage's language.
        """
        setup = setup or self.rcfg["default_setup"]
        s = self.rcfg["setups"][setup]
        k = k or int(self.rcfg["final_k"])
        self.timings = {}
        lists: dict[str, list[tuple[int, float]]] = {}
        report = on_stage or (lambda name: None)  # progress hook for the web app

        queries = {"orig": query}
        query_lang: dict[str, str] = {}
        rerank_query: str | dict[str, str] = query
        allowed = self.country_mask(country) if s.get("planner") else None
        self.last_translation = None
        if s.get("planner") and alt_queries:
            from plant_rag.generate import detect_lang

            q_lang = detect_lang(query)
            query_lang["orig"] = q_lang
            for lang in ("ko", "en"):
                alt = (alt_queries.get(lang) or "").strip()
                if alt and alt != query:
                    queries[f"plan_{lang}"] = alt
                    query_lang[f"plan_{lang}"] = lang
            other = "en" if q_lang == "ko" else "ko"
            # each passage is reranked against the question in its own language: the user's question, or the
            # planner's translation of it (its keyword query only if there is no translation)
            translated = (alt_queries.get("question_translated") or "").strip()
            rerank_query = {q_lang: query, other: translated or alt_queries.get(other) or query}
            self.last_translation = alt_queries.get(other)
        elif s.get("translate") or s.get("planner"):
            from plant_rag.generate import detect_lang, translate_query

            report("translate")
            t0 = time.perf_counter()
            q_lang = detect_lang(query)
            other = "en" if q_lang == "ko" else "ko"
            translated = translate_query(query, other, self.cfg)
            self.timings["translate"] = time.perf_counter() - t0
            queries["tr"] = translated
            rerank_query = {q_lang: query, other: translated}
            self.last_translation = translated

        report("search")
        only_lang = {"KR": "ko", "US": "en"}.get((country or "").upper()) if allowed is not None else None
        for tag, q in queries.items():
            suffix = "" if tag == "orig" else f"_{tag}"
            # keywords in one language find nothing useful in documents of the other: skip that list
            if s["bm25"] and not (only_lang and query_lang.get(tag, only_lang) != only_lang):
                t0 = time.perf_counter()
                lists["bm25" + suffix] = self.bm25_search(q, int(self.rcfg["bm25_top_k"]), allowed)
                self.timings["bm25"] = self.timings.get("bm25", 0.0) + time.perf_counter() - t0
            if s["dense"]:
                t0 = time.perf_counter()
                lists["dense" + suffix] = self.dense_search(q, int(self.rcfg["dense_top_k"]), allowed)
                self.timings["dense"] = self.timings.get("dense", 0.0) + time.perf_counter() - t0  # incl. query embedding
        if not lists:
            raise ValueError(f"Setup {setup} enables neither BM25 nor dense search")

        if len(lists) > 1:
            ranked = self.rrf(list(lists.values()), int(self.rcfg["rrf_k"]))
            stage = "rrf"
        else:
            stage, ranked = next(iter(lists.items()))
        rank_of = {name: {i: r for r, (i, _) in enumerate(lst, 1)} for name, lst in lists.items()}
        if stage == "rrf":
            rank_of["rrf"] = {i: r for r, (i, _) in enumerate(ranked, 1)}

        if s["rerank"]:
            cands = self._rerank_pool(ranked, lists, rerank_candidates)
            report("rerank")
            t0 = time.perf_counter()
            scores = self.rerank(rerank_query, cands) if cands else []
            self.timings["rerank"] = time.perf_counter() - t0
            order = sorted(zip(cands, scores), key=lambda x: -x[1])
            hits = [Hit(self.chunks[i], sc, {n: m[i] for n, m in rank_of.items() if i in m} | {"rerank": r},
                        rerank_score=sc) for r, (i, sc) in enumerate(order[:k], 1)]
        else:
            hits = [Hit(self.chunks[i], sc, {n: m[i] for n, m in rank_of.items() if i in m})
                    for i, sc in ranked[:k]]
        return hits
