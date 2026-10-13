"""Text embeddings.

All embedding calls go through `embed_texts`. To replace the Gemini embedding API with a local
model, change only this module. Vectors are cached in SQLite by (model, output size, task type, text hash),
so a text is never sent twice and an interrupted run resumes where it stopped.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterator

import numpy as np
from google.genai import types

from plant_rag.gemini_client import call_with_retry, get_client

log = logging.getLogger(__name__)

TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"  # for chunks
TASK_QUERY = "RETRIEVAL_QUERY"        # for questions


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cache_key(model: str, dim: int, task_type: str, text: str) -> str:
    return f"{model}|{dim}|{task_type}|{text_hash(text)}"


def _open_cache(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE IF NOT EXISTS emb (key TEXT PRIMARY KEY, vec BLOB NOT NULL)")
    return con


def _batches(items: list[int], size: int) -> Iterator[list[int]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def l2_normalize(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.clip(norms, 1e-12, None)


def embed_texts(texts: list[str], task_type: str, cfg: dict[str, Any], show_progress: bool = False) -> np.ndarray:
    """Return an (n, output_dim) float32 array of L2-normalized vectors, in the same order as `texts`."""
    emb = cfg["embedding"]
    model, dim, batch_size = emb["model"], int(emb["output_dim"]), int(emb["batch_size"])
    keys = [_cache_key(model, dim, task_type, t) for t in texts]
    out = np.zeros((len(texts), dim), dtype=np.float32)

    con = _open_cache(cfg["paths"]["embedding_cache"])
    try:
        cached: dict[str, bytes] = {}
        unique_keys = list(dict.fromkeys(keys))
        for i in range(0, len(unique_keys), 500):  # stay under SQLite's parameter limit
            part = unique_keys[i : i + 500]
            rows = con.execute(f"SELECT key, vec FROM emb WHERE key IN ({','.join('?' * len(part))})", part)
            cached.update(rows.fetchall())

        missing: list[int] = []
        seen: set[str] = set()
        for i, k in enumerate(keys):
            if k not in cached and k not in seen:
                missing.append(i)
                seen.add(k)
        log.info("Embeddings: %d texts, %d cached, %d to request", len(texts), len(texts) - len(missing), len(missing))

        if missing:
            client = get_client(cfg)
            config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=dim)
            batches = list(_batches(missing, batch_size))
            if show_progress:
                from tqdm import tqdm

                batches = tqdm(batches, desc="Embedding", unit="batch")
            for batch in batches:
                contents = [texts[i] for i in batch]
                resp = call_with_retry(
                    lambda: client.models.embed_content(model=model, contents=contents, config=config),
                    cfg,
                    what=f"embed_content({model}, n={len(contents)})",
                )
                if len(resp.embeddings) != len(batch):
                    raise RuntimeError(f"Expected {len(batch)} embeddings, got {len(resp.embeddings)}")
                vecs = l2_normalize(np.asarray([e.values for e in resp.embeddings], dtype=np.float32))
                if vecs.shape[1] != dim:
                    raise RuntimeError(f"Expected vectors of size {dim}, got {vecs.shape[1]}")
                rows = [(keys[i], v.tobytes()) for i, v in zip(batch, vecs)]
                con.executemany("INSERT OR REPLACE INTO emb (key, vec) VALUES (?, ?)", rows)
                con.commit()  # commit per batch, so an interruption loses at most one batch
                cached.update(rows)
    finally:
        con.close()

    for i, k in enumerate(keys):
        out[i] = np.frombuffer(cached[k], dtype=np.float32)
    return out
