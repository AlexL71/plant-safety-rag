"""Evaluate the agent layer: the planner and the visuals.

    python -m plant_rag.eval_agent --part router --run agent_v4        # 52 requests, one light model call each
    python -m plant_rag.eval_agent --part tasks --run agent_v4         # 12 visual requests end to end (searches)
    python -m plant_rag.eval_agent --part all --run agent_v4

Inputs: eval/agent/router_cases.jsonl (request, optional chat history, and the expected tool; optionally the expected
visual ("any" = any type), country, and terms of which at least one must appear in the planner's search queries)
and eval/agent/task_cases.jsonl.
Outputs in eval/results/<run>/: router.jsonl, tasks.jsonl (one row per case, with the answer, the produced visual,
its evidence ids and the automatic check statistics), and summary.json.

Automatic metrics (no human needed):
- planner: tool accuracy with a confusion table, and visual / country / search-term accuracy where a case sets them.
- visuals: produced %, requested type produced %, elements kept after the citation check + numbers guard.
Faithfulness of what is shown (does each element match its cited passage?) is graded separately with
eval/faithfulness_rubric.md and stored next to these files.
Rows already in the output files are skipped, so an interrupted run resumes.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from plant_rag import agent
from plant_rag.config import REPO_ROOT, load_config
from plant_rag.retrieve import Retriever

log = logging.getLogger(__name__)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_router(cfg: dict[str, Any], out: Path) -> list[dict]:
    cases = read_jsonl(REPO_ROOT / "eval/agent/router_cases.jsonl")
    done = {r["id"]: r for r in read_jsonl(out)}
    rows = []
    with open(out, "a", encoding="utf-8") as f:
        for c in cases:
            if c["id"] in done:
                rows.append(done[c["id"]])
                continue
            t0 = time.perf_counter()
            r = agent.plan_request(c["text"], [tuple(t) for t in c.get("history", [])], cfg)
            row = {**c, "predicted": r["tool"], "predicted_visual": r["visual"], "predicted_country": r["country"],
                   "question": r["question"], "query_ko": r["query_ko"], "query_en": r["query_en"], "reason": r["reason"],
                   "seconds": round(time.perf_counter() - t0, 2)}
            row |= _grade_plan(c, r)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            rows.append(row)
            print(f"{c['id']} {c['tool']:>9} -> {r['tool']:<9} {r['visual']:<9} {r['country']:<4} "
                  f"{'ok' if row['correct'] else 'WRONG'} | {r['query_ko']} | {r['query_en']}", flush=True)
    return rows


def _grade_plan(case: dict, plan: dict) -> dict[str, bool]:
    """Checks for one planner output; a check is only made when the case sets that field."""
    g = {"tool_ok": plan["tool"] == case["tool"]}
    if "visual" in case:
        g["visual_ok"] = plan["visual"] != "none" if case["visual"] == "any" else plan["visual"] == case["visual"]
    if "country" in case:
        g["country_ok"] = plan["country"] == case["country"]
    if "terms" in case:
        queries = f"{plan['query_ko']} {plan['query_en']}".lower()
        g["terms_ok"] = any(t.lower() in queries for t in case["terms"])
    return g | {"correct": all(g.values())}


def run_tasks(cfg: dict[str, Any], out: Path, setup: str) -> list[dict]:
    cases = read_jsonl(REPO_ROOT / "eval/agent/task_cases.jsonl")
    done = {r["id"]: r for r in read_jsonl(out)}
    retriever = None
    rows = []
    with open(out, "a", encoding="utf-8") as f:
        for c in cases:
            if c["id"] in done:
                rows.append(done[c["id"]])
                continue
            retriever = retriever or Retriever(cfg)
            t0 = time.perf_counter()
            res = agent.run(c["text"], [], retriever, cfg, setup, lang=c["lang"])
            hits = res.pop("evidence_hits", [])
            row = {**c, "intent": res["intent"], "plan_route": res.get("route"), "refused": res.get("refused"), "reason": res.get("reason"),
                   "evidence": [h.chunk["chunk_id"] for h in hits], "seconds": round(time.perf_counter() - t0, 1)}
            v = res.get("visual")
            row |= {"answer": res.get("text"), "visual": v, "visual_check": res.get("visual_check", {}),
                    "visual_reason": res.get("visual_reason", ""), "produced": bool(v),
                    "type_ok": bool(v) and v["type"] == c["expect_type"]}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            rows.append(row)
            print(f"{c['id']} {c['part']:<6} produced={row.get('produced')} ({row['seconds']}s)", flush=True)
    return rows


def summarize(router: list[dict], tasks: list[dict]) -> dict[str, Any]:
    s: dict[str, Any] = {}
    if router:
        conf: dict[str, Counter] = defaultdict(Counter)
        for r in router:
            conf[r["tool"]][r["predicted"]] += 1

        def acc(rows: list[dict], key: str) -> str:
            graded = [r for r in rows if key in r]
            return f"{sum(r[key] for r in graded)}/{len(graded)}"

        planner_cases = [r for r in router if r["id"].startswith("q")]
        s["router"] = {"all_checks": acc(router, "correct"), "tool": acc(router, "tool_ok"),
                       "visual": acc(router, "visual_ok"), "country": acc(router, "country_ok"),
                       "search_terms": acc(router, "terms_ok"),
                       "planner_cases_all_checks": acc(planner_cases, "correct"),
                       "by_language": {lang: acc([r for r in router if r["lang"] == lang], "correct") for lang in ("ko", "en")},
                       "visual_added_to_plain_questions": acc([r | {"v": r["predicted_visual"] != "none"} for r in router
                                                               if r["tool"] == "answer" and "visual" not in r], "v"),
                       "confusion": {k: dict(v) for k, v in conf.items()},
                       "wrong": [r["id"] for r in router if not r["correct"]]}

    def checks(rows: list[dict], key: str) -> dict[str, int]:
        total: Counter = Counter()
        for r in rows:
            total.update(r.get(key) or {})
        return dict(total)

    vis = [r for r in tasks if r["part"] == "visual"]
    if vis:
        s["visuals"] = {"produced": f"{sum(r['produced'] for r in vis)}/{len(vis)}",
                        "requested_type": f"{sum(r['type_ok'] for r in vis)}/{len(vis)}",
                        "elements": checks(vis, "visual_check"),
                        "not_produced": {r["id"]: r.get("visual_reason") or r.get("reason") for r in vis if not r["produced"]}}
    secs = [r["seconds"] for r in tasks]
    if secs:
        s["median_seconds"] = sorted(secs)[len(secs) // 2]
    return s


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Evaluate SafetyAgent's planner and visuals.")
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--part", choices=["router", "tasks", "all"], default="all")
    ap.add_argument("--run", required=True)
    ap.add_argument("--setup", default=None, help="search setup (default: default_setup in the config)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    cfg = load_config(args.config)
    run_dir = REPO_ROOT / "eval" / "results" / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    router = run_router(cfg, run_dir / "router.jsonl") if args.part in ("router", "all") else read_jsonl(run_dir / "router.jsonl")
    tasks = run_tasks(cfg, run_dir / "tasks.jsonl", args.setup or cfg["retrieval"]["default_setup"]) if args.part in ("tasks", "all") else read_jsonl(run_dir / "tasks.jsonl")
    summary = summarize(router, tasks)
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
