"""Build the search indexes from data/processed/chunks.jsonl.

- Dense (meaning) index: Gemini embeddings (cached, see embed.py) in a FAISS IndexFlatIP.
  Vectors are L2-normalized, so inner product = cosine similarity; exact search is fast at this size.
- Keyword index: BM25 tokens. Korean is split into morphemes with Kiwi (so 설비의 / 설비를 both give
  설비); English words are lowercased.

Each chunk is indexed as a "passage": a short header (document title | law part/chapter | clause
heading) + the chunk text. The header gives short clauses context ("2. 적용범위" alone says little).

Outputs in index/: faiss.index, bm25_tokens.json, meta.json (chunk order + fingerprint of the inputs).
FAISS is written with serialize_index() + normal file I/O, because faiss.write_index() can fail on
Windows paths with non-ASCII characters (this repo lives under "Рабочий стол").

    python -m plant_rag.index --config configs/config.yaml
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from plant_rag.chunk import get_kiwi
from plant_rag.config import load_config
from plant_rag.embed import TASK_DOCUMENT, embed_texts

log = logging.getLogger(__name__)

# Kiwi part-of-speech tags kept for BM25: nouns, numbers, foreign words (English), Hanja, roots,
# verb/adjective stems. Particles and endings (의, 를, 하여야 한다) are dropped.
BM25_TAGS = {"NNG", "NNP", "NNB", "NR", "SL", "SH", "SN", "XR", "VV", "VA"}


def chunks_path(cfg: dict[str, Any]) -> Path:
    return cfg["paths"]["processed_dir"] / "chunks.jsonl"


def load_chunks(cfg: dict[str, Any]) -> list[dict]:
    path = chunks_path(cfg)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run: python -m plant_rag.ingest, then python -m plant_rag.chunk")
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def passage_text(chunk: dict, with_header: bool = True) -> str:
    """Text used for embedding, BM25 and reranking: header line + chunk text."""
    if not with_header:
        return chunk["text"]
    header = " | ".join(x for x in (chunk["title"], chunk.get("section", ""), chunk.get("heading", "")) if x)
    return f"{header}\n{chunk['text']}"


def bm25_tokenize(text: str) -> list[str]:
    """Kiwi morphemes for Korean, lowercased words for English (Kiwi tags English as SL)."""
    return [t.form.lower() for t in get_kiwi().tokenize(text) if t.tag in BM25_TAGS]


def index_paths(cfg: dict[str, Any]) -> dict[str, Path]:
    d: Path = cfg["paths"]["index_dir"]
    return {"faiss": d / "faiss.index", "bm25": d / "bm25_tokens.json", "meta": d / "meta.json"}


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def build(cfg: dict[str, Any]) -> None:
    chunks = load_chunks(cfg)
    with_header = bool(cfg["index"]["passage_header"])
    passages = [passage_text(c, with_header) for c in chunks]
    paths = index_paths(cfg)
    paths["faiss"].parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    vecs = embed_texts(passages, TASK_DOCUMENT, cfg, show_progress=True)
    t_embed = time.perf_counter() - t0
    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(np.ascontiguousarray(vecs, dtype=np.float32))
    _write_bytes_atomic(paths["faiss"], faiss.serialize_index(index).tobytes())

    t0 = time.perf_counter()
    tokens = [bm25_tokenize(p) for p in passages]
    t_bm25 = time.perf_counter() - t0
    _write_bytes_atomic(paths["bm25"], json.dumps(tokens, ensure_ascii=False).encode("utf-8"))

    meta = {
        "chunk_ids": [c["chunk_id"] for c in chunks],
        "chunks_sha256": file_sha256(chunks_path(cfg)),
        "embedding_model": cfg["embedding"]["model"],
        "embedding_dim": int(vecs.shape[1]),
        "passage_header": with_header,
        "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _write_bytes_atomic(paths["meta"], json.dumps(meta, ensure_ascii=False, indent=1).encode("utf-8"))
    log.info("Indexed %d chunks | embeddings %.1fs | BM25 tokenizing %.1fs | dim %d",
             len(chunks), t_embed, t_bm25, vecs.shape[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS + BM25 indexes from chunks.jsonl.")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    build(load_config(args.config))


if __name__ == "__main__":
    main()
