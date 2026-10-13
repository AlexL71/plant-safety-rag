"""The DocAgent engine: loads the plant_rag pipeline once and answers questions one at a time.

- Loading (indexes + reranker, ~20 s) runs in a background thread so the web server starts at once.
- Questions are serialized with a lock: the reranker uses all CPU cores, so parallel questions would only
  slow each other down on a laptop.
- PDF pages are rendered once with PyMuPDF and cached as PNG files.
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable

import pymupdf

from plant_rag.config import load_config, resolve_path
from plant_rag.generate import answer, condense_question, detect_lang, refusal_threshold
from plant_rag.ingest import read_manifest
from plant_rag.retrieve import Retriever

log = logging.getLogger(__name__)

SETUP_INFO = {
    "A": "BM25 keyword search",
    "B": "Dense (meaning) search",
    "C": "Hybrid: BM25 + dense (RRF)",
    "D": "Hybrid + reranker",
    "E": "Hybrid + reranker + query translation",
}


class Engine:
    def __init__(self, config_path: str | Path | None = None):
        self.cfg = load_config(config_path)
        self.web = self.cfg["web"]
        self.ready = False
        self.error: str | None = None
        self.retriever: Retriever | None = None
        self.chunks: dict[str, dict] = {}
        self.docs: dict[str, dict] = {}
        self.ask_lock = threading.Lock()
        self.pdf_lock = threading.Lock()  # PyMuPDF documents are not thread-safe
        self.page_dir = resolve_path(self.web["page_cache_dir"])
        self.started = time.time()
        self._load_docs()
        threading.Thread(target=self._load_pipeline, name="engine-load", daemon=True).start()

    # ---------------------------------------------------------------- loading
    def _load_docs(self) -> None:
        raw = self.cfg["paths"]["raw_dir"]
        for row in read_manifest(self.cfg["paths"]["manifest"]):
            pdf = raw / row["file_name"]
            if not pdf.exists():
                continue
            with pymupdf.open(pdf) as d:
                sizes = [[round(p.rect.width, 1), round(p.rect.height, 1)] for p in d]
            self.docs[row["doc_id"]] = {"doc_id": row["doc_id"], "title": row["title"], "lang": row["language"],
                                        "source_url": row["source_url"], "file": pdf, "pages": sizes}

    def _load_pipeline(self) -> None:
        try:
            t0 = time.perf_counter()
            retriever = Retriever(self.cfg)
            _ = retriever.reranker
            self.chunks = {c["chunk_id"]: c for c in retriever.chunks}
            for doc_id, d in self.docs.items():
                d["chunks"] = sum(1 for c in retriever.chunks if c["doc_id"] == doc_id)
            self.retriever = retriever
            self.ready = True
            log.info("Engine ready in %.1fs (%d chunks, %d documents)", time.perf_counter() - t0,
                     len(self.chunks), len(self.docs))
        except Exception as exc:  # shown on the status endpoint
            self.error = f"{type(exc).__name__}: {exc}"
            log.exception("Engine failed to load")

    def status(self) -> dict[str, Any]:
        return {"ready": self.ready, "error": self.error, "documents": len(self.docs),
                "chunks": len(self.chunks), "uptime_s": round(time.time() - self.started)}

    # ---------------------------------------------------------------- answering
    def run(self, question: str, history: list[tuple[str, str]], setup: str,
            on_stage: Callable[[str], None] | None = None, answer_lang: str | None = None) -> dict[str, Any]:
        """Answer one question (with chat history for follow-ups). Returns plain, JSON-ready data.
        `answer_lang` ("ko" / "en") forces the answer language; None follows the question."""
        lang = answer_lang or detect_lang(question)
        if not self.ready or self.retriever is None:
            raise RuntimeError(self.error or "The engine is still loading; try again in a few seconds.")
        stage = on_stage or (lambda s: None)
        with self.ask_lock:
            t0 = time.perf_counter()
            standalone = question
            if history:
                stage("condense")
                standalone = condense_question(question, history[-int(self.web["history_turns"]):], self.cfg)
            hits = self.retriever.search(standalone, setup=setup, on_stage=stage)
            timings = dict(self.retriever.timings)
            translated = self.retriever.last_translation if self.cfg["retrieval"]["setups"][setup].get("translate") else None
            stage("answer")
            ans = answer(standalone, hits, self.cfg, setup, lang=lang)
            total = time.perf_counter() - t0
        return {
            "question": question, "standalone": standalone if standalone != question else None,
            "setup": setup, "lang": lang, "lang_choice": answer_lang or "auto", "text": ans.text, "refused": ans.refused,
            "reason": ans.refusal_reason, "cited": ans.cited, "translated": translated,
            "threshold": refusal_threshold(self.cfg, setup),
            "evidence": [{"n": n, "chunk_id": h.chunk["chunk_id"],
                          "score": round(h.rerank_score, 4) if h.rerank_score is not None else round(h.score, 4)}
                         for n, h in enumerate(hits, 1)],
            "timings": {k: round(v, 2) for k, v in timings.items()},
            "llm_s": round(ans.llm_seconds, 2), "llm_cached": ans.llm_cached, "total_s": round(total, 2),
        }

    # ---------------------------------------------------------------- documents
    def passage(self, chunk_id: str, with_boxes: bool = False) -> dict[str, Any] | None:
        c = self.chunks.get(chunk_id)
        if not c:
            return None
        out = {k: c[k] for k in ("chunk_id", "doc_id", "title", "clause_id", "heading", "section",
                                 "page_start", "page_end", "lang", "text")}
        if with_boxes:
            out["boxes"] = c.get("boxes", [])
        return out

    def page_png(self, doc_id: str, page: int) -> Path:
        """Render one PDF page to PNG (cached). `page` is 1-based."""
        doc = self.docs[doc_id]
        if not 1 <= page <= len(doc["pages"]):
            raise IndexError(page)
        out = self.page_dir / doc_id / f"{page}.png"
        if out.exists():
            return out
        out.parent.mkdir(parents=True, exist_ok=True)
        zoom = float(self.web["page_zoom"])
        with self.pdf_lock, pymupdf.open(doc["file"]) as d:
            pix = d[page - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            tmp = out.with_suffix(".tmp")
            pix.save(str(tmp), output="png")
            tmp.replace(out)
        return out
