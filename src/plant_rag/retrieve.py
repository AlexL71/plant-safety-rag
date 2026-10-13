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
from typing import Any

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
    def bm25_search(self, query: str, k: int) -> list[tuple[int, float]]:
        scores = self.bm25.get_scores(bm25_tokenize(query))
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top if scores[i] > 0]

    def dense_search(self, query: str, k: int) -> list[tuple[int, float]]:
        q = embed_texts([query], TASK_QUERY, self.cfg)
        scores, idx = self.faiss.search(q, k)
        return [(int(i), float(s)) for i, s in zip(idx[0], scores[0]) if i >= 0]

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
            self._reranker = CrossEncoder(rc["model"], max_length=int(rc["max_length"]), device=rc["device"])
            log.info("Reranker loaded in %.1fs", time.perf_counter() - t0)
        return self._reranker

    def rerank(self, query: str, idxs: list[int]) -> list[float]:
        pairs = [(query, passage_text(self.chunks[i], self.with_header)) for i in idxs]
        scores = self.reranker.predict(pairs, batch_size=int(self.cfg["reranker"]["batch_size"]),
                                       show_progress_bar=False)
        return [float(s) for s in scores]

    def _rerank_pool(self, ranked: list[tuple[int, float]], lists: dict[str, list[tuple[int, float]]]) -> list[int]:
        """Candidates for the reranker: the top `rerank_min_per_list` of every search list first, then the
        best of the fused ranking, up to `rerank_candidates`.

        Why: for a Korean question whose answer is only in an English document, BM25 finds nothing in
        English, so RRF pushes the dense list's best hit down (seen: dense rank 2 -> RRF rank 18).
        """
        size, per_list = int(self.rcfg["rerank_candidates"]), int(self.rcfg["rerank_min_per_list"])
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
    def search(self, query: str, setup: str | None = None, k: int | None = None) -> list[Hit]:
        """Return the top-k hits for `query` under `setup` (A/B/C/D). Stage times go to self.timings."""
        setup = setup or self.rcfg["default_setup"]
        s = self.rcfg["setups"][setup]
        k = k or int(self.rcfg["final_k"])
        self.timings = {}
        lists: dict[str, list[tuple[int, float]]] = {}

        if s["bm25"]:
            t0 = time.perf_counter()
            lists["bm25"] = self.bm25_search(query, int(self.rcfg["bm25_top_k"]))
            self.timings["bm25"] = time.perf_counter() - t0
        if s["dense"]:
            t0 = time.perf_counter()
            lists["dense"] = self.dense_search(query, int(self.rcfg["dense_top_k"]))
            self.timings["dense"] = time.perf_counter() - t0  # includes the query-embedding API call
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
            cands = self._rerank_pool(ranked, lists)
            t0 = time.perf_counter()
            scores = self.rerank(query, cands) if cands else []
            self.timings["rerank"] = time.perf_counter() - t0
            order = sorted(zip(cands, scores), key=lambda x: -x[1])
            hits = [Hit(self.chunks[i], sc, {n: m[i] for n, m in rank_of.items() if i in m} | {"rerank": r},
                        rerank_score=sc) for r, (i, sc) in enumerate(order[:k], 1)]
        else:
            hits = [Hit(self.chunks[i], sc, {n: m[i] for n, m in rank_of.items() if i in m})
                    for i, sc in ranked[:k]]
        return hits
