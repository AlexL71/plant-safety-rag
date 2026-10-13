"""Run the evaluation set over the search setups and compute metrics.

    python -m plant_rag.evaluate --split dev --setups A,B,C,D --run dev_v1
    python -m plant_rag.evaluate --split test --setups A,B,C,D --run test_v1
    python -m plant_rag.evaluate --split dev --run dev_v1 --limit 3          # quick smoke run

Per setup and question:
- Retrieval (answerable questions only, no API cost apart from cached query embeddings):
  Recall@5 = a gold chunk is in the top 5 ("hit rate"); MRR@10 = mean of 1/rank of the first gold chunk.
- Answers (only for `evaluate.answer_setups`, default C and D, to save cost): refusal, citations.
  Citation precision = cited passages that are gold chunks / all cited passages;
  "cites gold" = the answer cites at least one gold chunk.
- Refusal: correct refusals on unanswerable questions; false refusals on answerable ones.
- Latency: search seconds (CPU + query embedding) and LLM seconds (from the cache record).

Results go to eval/results/<run>/: per_question.jsonl (appended as it goes; a re-run skips rows that
were already done with the same settings, so an interrupted run resumes) and summary.csv.
Refusal-threshold tuning (dev only): the answer step is run with the pre-API threshold disabled, and
`threshold_sweep.csv` shows, for each candidate threshold, how many refusals would be correct/false.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from plant_rag.config import REPO_ROOT, load_config
from plant_rag.generate import answer
from plant_rag.retrieve import Retriever

log = logging.getLogger(__name__)


def load_questions(path: Path, split: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        qs = [json.loads(line) for line in f if line.strip()]
    return qs if split == "all" else [q for q in qs if q["split"] == split]


def settings_fingerprint(cfg: dict[str, Any], setup: str) -> str:
    """Rows are reused only if everything that affects them is unchanged."""
    keys = {k: cfg[k] for k in ("retrieval", "reranker", "embedding", "llm", "index")}
    keys["setup"] = setup
    keys["min_rerank_score"] = cfg["answer"]["min_rerank_score"]
    return hashlib.sha256(json.dumps(keys, sort_keys=True, default=str).encode()).hexdigest()[:12]


def evaluate_one(q: dict, setup: str, retriever: Retriever, cfg: dict[str, Any], with_answer: bool, k_eval: int) -> dict:
    t0 = time.perf_counter()
    hits = retriever.search(q["question"], setup=setup, k=k_eval)
    search_s = time.perf_counter() - t0
    gold = set(q["gold_chunk_ids"])
    ids = [h.chunk["chunk_id"] for h in hits]
    first_gold = next((r for r, i in enumerate(ids, 1) if i in gold), None)
    row = {
        "qid": q["qid"], "setup": setup, "split": q["split"], "type": q["type"], "lang": q["lang"],
        "cross_lingual": q.get("cross_lingual", False), "answerable": q["type"] != "unanswerable",
        "retrieved": ids, "scores": [round(h.score, 4) for h in hits],
        "top_rerank": round(hits[0].rerank_score, 4) if hits and hits[0].rerank_score is not None else None,
        "first_gold_rank": first_gold, "search_s": round(search_s, 2),
    }
    if with_answer:
        final_k = int(cfg["retrieval"]["final_k"])
        ans = answer(q["question"], hits[:final_k], cfg, setup)
        cited_ids = [hits[n - 1].chunk["chunk_id"] for n in ans.cited]
        row |= {
            "answer": ans.text, "refused": ans.refused, "refusal_reason": ans.refusal_reason,
            "cited": cited_ids, "cited_gold": sum(1 for i in cited_ids if i in gold),
            "llm_s": round(ans.llm_seconds, 2) if ans.refusal_reason not in ("low_score", "no_hits") else 0.0,
            "thoughts": ans.usage.get("thoughts_token_count", 0),
        }
    return row


def frac(n: int, d: int) -> str:
    return f"{n}/{d} = {100 * n / d:.0f}%" if d else "n/a"


def summarize(rows: list[dict]) -> list[dict]:
    """One summary row per setup; counts shown with percentages (small sets: a few questions move % a lot)."""
    out = []
    by_setup: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_setup[r["setup"]].append(r)
    for setup, rs in sorted(by_setup.items()):
        ans = [r for r in rs if r["answerable"]]
        cross = [r for r in ans if r["cross_lingual"]]
        hit5 = [r for r in ans if r["first_gold_rank"] and r["first_gold_rank"] <= 5]
        mrr = sum(1 / r["first_gold_rank"] for r in ans if r["first_gold_rank"] and r["first_gold_rank"] <= 10)
        s = {
            "setup": setup, "questions": len(rs),
            "recall@5": frac(len(hit5), len(ans)),
            "recall@5_cross_lingual": frac(sum(1 for r in cross if r in hit5), len(cross)),
            "mrr@10": f"{mrr / len(ans):.3f}" if ans else "n/a",
            "median_search_s": f"{sorted(r['search_s'] for r in rs)[len(rs) // 2]:.1f}",
        }
        answered = [r for r in rs if "refused" in r]
        if answered:
            a_ans = [r for r in answered if r["answerable"]]
            a_un = [r for r in answered if not r["answerable"]]
            given = [r for r in a_ans if not r["refused"]]
            n_cited = sum(len(r["cited"]) for r in given)
            s |= {
                "correct_refusals": frac(sum(1 for r in a_un if r["refused"]), len(a_un)),
                "false_refusals": frac(sum(1 for r in a_ans if r["refused"]), len(a_ans)),
                "answers_citing_gold": frac(sum(1 for r in given if r["cited_gold"] > 0), len(given)),
                "citation_precision": frac(sum(r["cited_gold"] for r in given), n_cited),
                "median_llm_s": f"{sorted(r['llm_s'] for r in answered)[len(answered) // 2]:.1f}",
            }
        out.append(s)
    return out


def threshold_sweep(rows: list[dict]) -> list[dict]:
    """For setup-D rows answered with the pre-API threshold off: refusals per candidate threshold."""
    rs = [r for r in rows if r.get("top_rerank") is not None and "refused" in r]
    out = []
    for t in (0.0, 0.001, 0.003, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5):
        ref = [(r, (r["top_rerank"] < t) or (r["refused"] and r["refusal_reason"] == "model")) for r in rs]
        correct = sum(1 for r, x in ref if x and not r["answerable"])
        false = sum(1 for r, x in ref if x and r["answerable"])
        out.append({"threshold": t, "correct_refusals": f"{correct}/{sum(1 for r in rs if not r['answerable'])}",
                    "false_refusals": f"{false}/{sum(1 for r in rs if r['answerable'])}", "net": correct - false})
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Evaluate retrieval and answers on eval/questions.jsonl.")
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--questions", default="eval/questions.jsonl")
    ap.add_argument("--split", default="dev", choices=["dev", "test", "test2", "all"])
    ap.add_argument("--setups", default="A,B,C,D")
    ap.add_argument("--run", required=True, help="name of the results folder under eval/results/")
    ap.add_argument("--limit", type=int, default=0, help="only the first N questions (quick check)")
    ap.add_argument("--tune-threshold", action="store_true",
                    help="dev only: answer with the pre-API refusal threshold off and write threshold_sweep.csv")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    cfg = load_config(args.config)
    if args.tune_threshold:
        if args.split != "dev":
            sys.exit("Tune the refusal threshold on the dev split only (test numbers must stay unseen).")
        cfg["answer"]["min_rerank_score"] = 0.0  # applies to every setup
    qpath = Path(args.questions) if Path(args.questions).is_absolute() else REPO_ROOT / args.questions
    questions = load_questions(qpath, args.split)
    if args.limit:
        questions = questions[: args.limit]
    setups = [s.strip() for s in args.setups.split(",") if s.strip()]
    answer_setups = set(cfg.get("evaluate", {}).get("answer_setups", ["C", "D"]))
    k_eval = int(cfg.get("evaluate", {}).get("k_eval", 10))

    run_dir = REPO_ROOT / "eval" / "results" / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    rows_path = run_dir / "per_question.jsonl"
    done: dict[tuple[str, str, str], dict] = {}
    if rows_path.exists():
        for line in open(rows_path, encoding="utf-8"):
            r = json.loads(line)
            done[(r["qid"], r["setup"], r["fingerprint"])] = r

    retriever = Retriever(cfg)
    rows: list[dict] = []
    total = len(questions) * len(setups)
    n = 0
    with open(rows_path, "a", encoding="utf-8") as f:
        for setup in setups:
            fp = settings_fingerprint(cfg, setup)
            for q in questions:
                n += 1
                key = (q["qid"], setup, fp)
                if key in done:
                    rows.append(done[key])
                    continue
                try:
                    row = evaluate_one(q, setup, retriever, cfg, setup in answer_setups, k_eval)
                except Exception as exc:  # keep going; the failed row is simply retried next run
                    log.error("%s / setup %s failed: %s", q["qid"], setup, exc)
                    continue
                row["fingerprint"] = fp
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                rows.append(row)
                gold = row["first_gold_rank"]
                print(f"[{n}/{total}] {setup} {q['qid']} gold@{gold if gold else '-'} "
                      f"{'refused' if row.get('refused') else ''} ({row['search_s']:.1f}s)", flush=True)

    summary = summarize(rows)
    write_csv(run_dir / "summary.csv", summary)
    for s in summary:
        print(json.dumps(s, ensure_ascii=False))
    if args.tune_threshold:
        for setup in setups:
            if not cfg["retrieval"]["setups"][setup]["rerank"] or setup not in answer_setups:
                continue
            sweep = threshold_sweep([r for r in rows if r["setup"] == setup])
            write_csv(run_dir / f"threshold_sweep_{setup}.csv", sweep)
            print(f"\nthreshold sweep (setup {setup}, dev):")
            for s in sweep:
                print(f"  {s['threshold']:<6} correct refusals {s['correct_refusals']:>6}  "
                      f"false refusals {s['false_refusals']:>6}  net {s['net']}")
    print(f"\nResults: {run_dir}")


if __name__ == "__main__":
    main()
