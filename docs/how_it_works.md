# How it works

Plain-English notes on each pipeline step: what it does, why it was built this way, which settings
matter, and what can go wrong. Written as each phase finishes.

Pipeline: **PDF → page lines → clause chunks → embeddings + keyword index → search → answer with citations.**
(Bold = built so far: everything up to the command-line demo, `python -m plant_rag.ask "…"`.)

---

## Step 0: Gemini access (Phase 0)

**What it does.** One place talks to the Gemini API (`gemini_client.py`). Two functions use it:
`call_llm()` in `generate.py` for answers and `embed_texts()` in `embed.py` for embeddings.

**Why this way.**
- *One client, one retry policy.* Temporary errors (429 "too many requests", 5xx server errors,
  timeouts) are retried with exponential backoff: wait 2 s, 4 s, 8 s, … plus a little randomness.
  A minimum gap between calls keeps us under rate limits.
- *Caches, so nothing is paid for twice.* Answers are saved as JSON files in `cache/llm/`, named by a
  hash of model + prompt + settings. Embeddings are saved in one SQLite file
  (`index/embedding_cache.sqlite`), keyed by model + vector size + task type + a hash of the text.
- *Swappable.* To use an in-house model later (needed for confidential documents), only these two
  functions change.

**Settings that matter** (`configs/config.yaml`): `llm.model`, `embedding.model`, `embedding.output_dim`,
`api.max_retries`, `api.min_interval_s`.

**What can go wrong.** A model name is retired (this happened: `gemini-2.5-flash` is closed to new keys).
Run `python -m plant_rag.smoke_test --list-models` to see what your key can use.

---

## Step 1: Reading PDFs (`ingest.py`, Phase 1)

**What it does.** Opens every PDF in `data/manifest.csv` with PyMuPDF and saves each page's lines,
with page number, position and font, to `data/processed/pages.jsonl`.

**Three problems it fixes.**

1. **Missing spaces in Korean PDFs.** KOSHA PDFs contain *no* space characters. Words are separated
   only by wider gaps on the page. We measure the gap between every two characters: about 5–7 pt
   between words, about 0 pt inside a word. A space is inserted when the gap is larger than
   `space_gap_ratio` × font size (0.15 × 12 pt ≈ 1.8 pt). This recovers the original spacing exactly.
   *Why not a Korean spacing model?* Kiwi's automatic spacing splits compound nouns
   (안전밸브 → 안전 밸브), which changes the text. Notebook 01 shows the three versions side by side.

2. **Running headers and footers** ("KOSHA GUIDE", "법제처 12 국가법령정보센터", CFR print codes,
   page numbers). They would pollute every chunk. A line is removed only if it is in the first or last
   rows of a page **and** repeats at the same height on several pages (or is a page number).
   Body lines are never touched, so repeated table cells survive.

3. **Undecodable equations.** Equations made with the Korean word processor's equation font come out as
   private-use characters with no meaning. Runs of them become `[수식]`; counts are logged.

Pages with almost no text (scans, figures) are skipped and listed in `data/processed/ingest_log.csv`.
Rotated text is skipped too: the US CFR PDF has a vertical print stamp in the margin ("… with CFR")
that otherwise lands in the middle of sentences.

**Settings that matter:** `ingest.space_gap_ratio`, `ingest.header_edge_rows`,
`ingest.header_repeat_min_pages`, `ingest.min_page_chars`.

**What can go wrong.** A scanned PDF has no text layer (we would need OCR, which is out of scope).
A new PDF layout may put headers somewhere unusual; check the "removed" table in notebook 01.

---

## Step 2: Splitting into clauses (`chunk.py`, Phase 1)

**What it does.** Turns page lines into chunks (`data/processed/chunks.jsonl`). Each chunk is one
clause, so a citation points to a real rule: document, clause, page.

**Clause rules per document type** (picked by the `doc_id` prefix, `chunking.doc_types`):

| Type | Example documents | Clause marker | Example `clause_id` |
|---|---|---|---|
| `kr_law` | 산업안전보건기준에 관한 규칙 | 제N조(제목) | `제261조 ①–②` |
| `kosha` | KOSHA guides (기술지원규정) | 1. / 4.2 / 8.2.2, `<부록 1>` | `8.2.1`, `부록 2` |
| `cfr` | 29 CFR 1910.119 | (a) Purpose. … (p), Appendix A–D | `(e)(1)–(2)` |
| `booklet` | OSHA 3132 | headings found by font (bold or a different typeface) | `Training / Initial Training` |

Numbered headings are accepted **only in order** (5. only after 4.). That stops list items, table
values like "12.4", and cross-references like "[부록 2]와 같다" from being mistaken for headings.
Tables of contents are detected (many "·······" lines near the front) and skipped.

**Size limit.** Chunks are at most `max_tokens` (500) tokens, counted with the **reranker's tokenizer**,
so every chunk fits the reranker without being cut off. A longer clause is split at its sub-items
((1), ①, …) and neighbours are packed back together up to 500 tokens. Anything still too long becomes
overlapping windows (`(part 2/4)` in `clause_id`; `overlap_tokens` = 50).

**Line joining.** PDF lines are joined into running text: English words hyphenated at a line end are
re-joined ("re-" + "quired"); for Korean line wraps, Kiwi decides whether a space belongs at the
break. List items and headings keep their own line.

**Each chunk stores:** `chunk_id, doc_id, doc_type, clause_id, heading, section, title, page_start,
page_end, lang, n_tokens, text, text_hash`. `section` holds the law's 편/장/절 path, useful for search
and for showing context.

**What can go wrong.**
- Tables are flattened into lines of text; numbers lose their column headers.
- Pages are the PDF's page numbers (what a PDF viewer shows), not the printed page numbers.
- If a heading is missed, the clause before it becomes too long and is cut into windows. Check the
  clause list per document in notebook 01 against the document's table of contents.
- `chunk_id`s are numbered in order, so changing chunk settings renumbers them. Evaluation gold labels
  should be re-checked after re-chunking.

**Run:**

```
python -m plant_rag.ingest
python -m plant_rag.chunk
```

Then open `notebooks/01_explore_docs.ipynb` to check the result.

---

## Step 3: Building the indexes (`index.py`, Phase 2)

**What it does.** Builds two search indexes over all chunks and saves them in `index/`.

- **Meaning search (dense).** Each chunk is turned into a vector of 768 numbers by Gemini's embedding
  model (`gemini-embedding-001`). Texts with similar meaning get similar vectors, even across
  languages (a Korean question can find an English paragraph). FAISS stores the vectors and finds the
  closest ones. All vectors have length 1, so "closest" = highest cosine similarity.
- **Keyword search (BM25).** Classic word matching that rewards rare words. Korean is first split into
  morphemes with Kiwi (설비의, 설비를 → 설비), and particles/endings are dropped; English is lowercased.

Each chunk is indexed with a **header**: `document title | law part/chapter | clause heading`, then the
text. A short clause like "2. 적용범위" says little by itself; the header tells search which guide it
belongs to.

**Cost and time (10 documents, 1,156 chunks):** 37 s for embeddings (24 API batches, about US$0.05,
paid once: vectors are cached in `index/embedding_cache.sqlite`), 7 s for Korean word splitting.

**Settings:** `embedding.model`, `embedding.output_dim`, `embedding.batch_size`, `index.passage_header`.

**What can go wrong.** If chunks change, the index must be rebuilt (`python -m plant_rag.index`); the
search code refuses to run on a mismatched index. Only new or changed chunks are sent to the API.

---

## Step 4: Search (`retrieve.py`, Phase 2)

**What it does.** Finds the 5 best passages for a question, in up to four stages:

1. **BM25** top 50 and **dense** top 50.
2. **RRF (Reciprocal Rank Fusion)** merges the two lists by rank: each passage gets
   `1/(60 + rank)` from each list it appears in. Ranks are used because BM25 scores (e.g. 10.8) and
   cosine similarities (e.g. 0.75) are on different scales.
3. **Reranker** (`BAAI/bge-reranker-v2-m3`, runs locally on CPU). Unlike the embedding model, which
   encodes question and passage separately, it reads them *together* and outputs a relevance score
   from 0 to 1. More accurate, but slow, so it only sees 10 candidates.
4. The top 5 go to the answer step.

The four **setups** for the Phase 3 comparison switch stages on/off: A = BM25 only, B = dense only,
C = hybrid (RRF), D = hybrid + reranker (default).

**Two lessons from the hand test.**
- *Cross-language and RRF.* For a Korean question whose answer is only in the English CFR, BM25 finds
  only Korean passages. Meaning search ranked the right CFR paragraph #2, but after fusion it fell to
  #18, outside the reranker's 10 candidates. Fix: the top 3 of each list always reach the reranker
  (`rerank_min_per_list`), then the fused ranking fills the rest.
- *The reranker is weaker across languages.* The same CFR paragraph scored 0.997 for the English
  question but 0.021 for the Korean one. It still ranked #2, so the answer was right, but a high
  refusal threshold would wrongly refuse such questions (see Step 5).

**Speed on the laptop CPU** (8 threads): model load ~10 s (once per process), then ~1.8 s per
candidate, so ~15–20 s per question with 10 candidates. Everything else takes under 3 s.
`max_length: 256` would halve this but cuts long clauses; to be measured in Phase 3.

**Settings:** `retrieval.*` (`bm25_top_k`, `dense_top_k`, `rrf_k`, `rerank_candidates`,
`rerank_min_per_list`, `final_k`), `reranker.max_length`, `reranker.num_threads`.

---

## Step 5: Answering with citations (`generate.py`, `ask.py`, Phase 2)

**What it does.** Sends the question and the 5 numbered passages to Gemini (`gemini-3.8-flash`,
temperature 0) with strict rules:

- answer in the question's language (Korean question → Korean answer, even from English evidence);
- every factual sentence ends with `[n]` citations; only the passages may be used;
- answer when passages use a slightly different term (변경관리 vs 변경요소관리);
- only if no passage is relevant, reply with an exact "not found" sentence.

The `[n]` numbers are then mapped back to document, clause and page for display.

**Refusing ("not found").** Two layers:
1. *Before the API call:* if the best reranker score is below `answer.min_rerank_score` (0.01), we
   refuse without calling the model. No cost and no risk of a made-up answer.
2. *By the model:* if the passages don't contain the answer.

The threshold is low on purpose (cross-language scores are low, see Step 4). It will be tuned on the
dev questions in Phase 3.

**Hand test (Phase 2):** 10 questions (5 Korean, 5 English, including cross-language and 2 questions the
documents cannot answer). All 10 behaved as expected; report in `eval/results/phase2_hand_test.md`.
LLM time 4–16 s; the model also spends 150–1,900 "thinking" tokens per answer (billed as output).
`llm.thinking_level` can lower that.

**Run:**

```
python -m plant_rag.index
python -m plant_rag.ask "안전밸브는 어떤 설비에 설치해야 하나요?"
python -m plant_rag.ask "What must a hot work permit document?" --setup C --show-evidence
```
