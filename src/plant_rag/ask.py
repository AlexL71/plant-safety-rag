"""Ask one question from the command line: answer + citations + timings.

    python -m plant_rag.ask "압력방출장치 설치 기준은?"
    python -m plant_rag.ask "What must a pre-startup safety review confirm?" --setup C --show-evidence
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from plant_rag.config import load_config
from plant_rag.generate import answer, format_location
from plant_rag.retrieve import Retriever

DISCLAIMER = "Reference tool, not legal or safety advice. Always check the cited source."


def snippet(text: str, n: int) -> str:
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= n else one_line[:n].rstrip() + " …"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):  # Korean output on non-UTF-8 Windows consoles
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Ask a question about the indexed safety documents.")
    parser.add_argument("question")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--setup", default=None, help="A=BM25, B=dense, C=hybrid, D=hybrid+rerank (default from config)")
    parser.add_argument("--show-evidence", action="store_true", help="also list evidence passages that were not cited")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    cfg = load_config(args.config)
    t0 = time.perf_counter()
    retriever = Retriever(cfg)
    t_load = time.perf_counter() - t0

    t0 = time.perf_counter()
    hits = retriever.search(args.question, setup=args.setup)  # first reranked search also loads the model
    t_search = time.perf_counter() - t0
    stage_times = dict(retriever.timings)

    ans = answer(args.question, hits, cfg)
    n_snip = int(cfg["answer"]["snippet_chars"])

    print("\n" + ans.text + "\n")
    shown = range(1, len(hits) + 1) if args.show_evidence or ans.refused else ans.cited
    if shown:
        print("Sources:" if not ans.refused else "Closest passages (not used):")
        for n in shown:
            h = hits[n - 1]
            score = f" | rerank {h.rerank_score:.3f}" if h.rerank_score is not None else ""
            mark = "" if n in ans.cited else "  (not cited)"
            print(f"  [{n}] {format_location(h.chunk)}{score}{mark}")
            print(f"      {snippet(h.chunk['text'], n_snip)}")
    if ans.refused:
        print(f"\n(refused: {ans.refusal_reason})")

    llm = "cached" if ans.llm_cached else f"{ans.llm_seconds:.1f}s"
    if ans.refusal_reason in ("low_score", "no_hits"):
        llm = "not called"
    stages = ", ".join(f"{k} {v:.2f}s" for k, v in stage_times.items())
    print(f"\n[setup {args.setup or cfg['retrieval']['default_setup']}] load {t_load:.1f}s | search {t_search:.1f}s "
          f"({stages}) | LLM {llm}")
    print(DISCLAIMER)


if __name__ == "__main__":
    main()
