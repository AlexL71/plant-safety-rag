"""Recall@5 per search setup: first test set on 10 vs 29 documents, and the new test set (test2).

    python notebooks/make_v2_figure.py      # -> docs/figures/recall_v2.png
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUNS = [("test_v1", "Test set 1 · 10 docs"), ("test_v2", "Test set 1 · 29 docs"), ("test2_v1", "Test set 2 (new topics) · 29 docs")]
COLORS = ["#b9c3ea", "#1428a0", "#00a3e0"]


def recall(run: str) -> dict[str, float]:
    with open(ROOT / "eval" / "results" / run / "summary.csv", encoding="utf-8-sig") as f:
        return {r["setup"]: float(r["recall@5"].split("=")[1].strip(" %")) for r in csv.DictReader(f)}


def main() -> None:
    data = [(label, recall(run)) for run, label in RUNS]
    setups = ["A", "B", "C", "D", "E"]
    names = {"A": "A · BM25", "B": "B · Dense", "C": "C · Hybrid", "D": "D · +Reranker", "E": "E · +Translation"}
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    w = 0.26
    for i, (label, r) in enumerate(data):
        xs = [k + (i - 1) * w for k in range(len(setups))]
        bars = ax.bar(xs, [r.get(s, 0) for s in setups], w - 0.02, label=label, color=COLORS[i])
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1, f"{b.get_height():.0f}", ha="center", fontsize=7.5)
    ax.set_xticks(range(len(setups)), [names[s] for s in setups])
    ax.set_ylabel("Recall@5 (%)")
    ax.set_ylim(0, 110)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("Right clause in the top 5, by search setup", fontsize=11, loc="left")
    fig.tight_layout()
    out = ROOT / "docs" / "figures" / "recall_v2.png"
    fig.savefig(out)
    print(out)


if __name__ == "__main__":
    main()
