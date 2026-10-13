"""PDF -> page lines (PyMuPDF).

For every page we keep its lines with page number, position and font, because chunk.py uses
fonts and positions to find headings. Two PDF problems are fixed here:

1. Missing spaces: some Korean PDFs (KOSHA) contain no space characters; words are only
   separated by wider gaps. A space is inserted wherever the gap between two characters is
   larger than `space_gap_ratio` x font size.
2. Running headers and footers. Only lines in the first/last `header_edge_rows` rows of a page
   are candidates (rows = lines with the same top y). A candidate is removed when
   - it is a page number (first/last `page_number_rows` rows only), or
   - it is in the very first/last row and the exact same text sits at the same height (+-3 pt)
     on 2+ pages, or
   - the exact text repeats at the same height on `header_repeat_min_pages`+ pages, or
   - the text with digits ignored (e.g. "Frm 00360") repeats at the same height on at least
     `header_repeat_min_pages` pages and `header_repeat_ratio` of the document.
   Body lines are never candidates, so repeated table cells and short phrases on the Korean law's
   fixed line grid survive; numbered labels such as "<별표 1>", "<별표 2>" survive the last rule.
   (A fixed margin band does not work: CFR pages start 159 pt down, and Korean law pages put the
   first body line inside a 9% band.)
3. Unreadable glyphs: Hangul-word-processor equations (font "HyhwpEQ") come out as Unicode
   private-use characters that can't be decoded. Runs of 2+ become `unreadable_placeholder`
   (e.g. "[수식]"); single ones (often decorative quote marks) are dropped. Counts are logged.

Output: data/processed/pages.jsonl (one record per page) and data/processed/ingest_log.csv
(skipped pages and removed header/footer lines).

    python -m plant_rag.ingest --config configs/config.yaml
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pymupdf

from plant_rag.config import load_config

log = logging.getLogger(__name__)

# "12", "- 3 -", "iii" (no parentheses: "(ii)" is a list item, not a page number)
PAGE_NUMBER = re.compile(r"^[\s\-–—·]*(\d{1,4}|[ivxlcdm]{1,6})[\s\-–—·]*$", re.IGNORECASE)
PRIVATE_USE = re.compile(r"[-�]")
PRIVATE_USE_RUN = re.compile(r"[-�]{2,}")


def read_manifest(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _clean_unreadable(text: str, placeholder: str) -> tuple[str, int]:
    """Replace runs of private-use glyphs with a placeholder, drop single ones. Returns (text, n_glyphs)."""
    n = len(PRIVATE_USE.findall(text))
    if n:
        text = PRIVATE_USE_RUN.sub(f" {placeholder} ", text)
        text = re.sub(r"\s+", " ", PRIVATE_USE.sub("", text)).strip()
    return text, n


def _line_record(line: dict[str, Any], gap_ratio: float) -> dict[str, Any] | None:
    """Rebuild one line's text from its characters, inserting spaces at wide gaps.

    Rotated lines are skipped: in our PDFs the only non-horizontal text is a vertical print stamp in the
    CFR margin ("... with CFR") that would otherwise land in the middle of sentences.
    """
    dx, dy = line.get("dir", (1.0, 0.0))
    if abs(dx - 1.0) > 0.01 or abs(dy) > 0.01:
        return None
    chars = [(c, s) for s in line["spans"] for c in s["chars"]]
    if not chars:
        return None
    out: list[str] = []
    prev = None
    for c, span in chars:
        ch = c["c"]
        if prev is not None:
            pc, pspan = prev
            gap = c["bbox"][0] - pc["bbox"][2]
            size = max(span["size"], pspan["size"], 1.0)
            if gap > gap_ratio * size and not ch.isspace() and not pc["c"].isspace():
                out.append(" ")
        out.append(ch)
        prev = (c, span)
    text = re.sub(r"\s+", " ", "".join(out)).strip()
    if not text:
        return None

    # dominant font = the one covering most characters
    weight: Counter = Counter()
    for s in line["spans"]:
        bold = bool(s["flags"] & 16) or "bold" in s["font"].lower()
        weight[(round(s["size"], 1), s["font"], bold)] += len(s["chars"])
    size, font, bold = weight.most_common(1)[0][0]
    x0, y0, x1, y1 = line["bbox"]
    return {"text": text, "size": size, "font": font, "bold": bold,
            "x0": round(x0, 1), "y0": round(y0, 1), "x1": round(x1, 1), "y1": round(y1, 1)}


Y_TOL = 3.0  # pt: "same height" for running headers/footers


def _edge_rank(lines: list[dict[str, Any]]) -> list[int]:
    """For each line: its row distance from the nearest page edge (0 = first or last row)."""
    tops: list[float] = []
    for y in sorted(r["y0"] for r in lines):
        if not tops or y - tops[-1] > Y_TOL:
            tops.append(y)
    ranks = []
    for r in lines:
        k = next(i for i, t in enumerate(tops) if r["y0"] - t <= Y_TOL)
        ranks.append(min(k, len(tops) - 1 - k))
    return ranks


def _repeat_count(index: dict[str, list[tuple[int, float]]], key: str, y: float) -> int:
    """Number of distinct pages where `key` occurs at height y (+- Y_TOL)."""
    return len({pno for pno, y2 in index.get(key, []) if abs(y2 - y) <= Y_TOL})


def _merge_same_row(lines: list[dict[str, Any]], gap_ratio: float) -> list[dict[str, Any]]:
    """Merge consecutive lines on the same baseline that PyMuPDF split, e.g. at a font change.

    CFR prints "(b)" upright and "Definitions." in italics, and they come out as two lines; the
    clause rules need them on one line. Only neighbours in reading order with a small horizontal
    gap (< 2 x font size) are merged, so the two columns of a page are never joined.
    """
    out: list[dict[str, Any]] = []
    for rec in lines:
        if out:
            prev = out[-1]
            gap = rec["x0"] - prev["x1"]
            size = max(rec["size"], prev["size"])
            if abs(rec["y0"] - prev["y0"]) <= 2 and -1 <= gap < 2 * size:
                sep = " " if gap > gap_ratio * size else ""
                main = prev if len(prev["text"]) >= len(rec["text"]) else rec
                out[-1] = {**prev, "text": prev["text"] + sep + rec["text"], "x1": max(prev["x1"], rec["x1"]),
                           "y1": max(prev["y1"], rec["y1"]),
                           "size": main["size"], "font": main["font"], "bold": main["bold"]}
                continue
        out.append(rec)
    return out


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"\d+", "#", text))


def extract_pdf(pdf_path: Path, doc_id: str, cfg: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Return (pages, log_rows). Each page: {doc_id, page, width, height, lines: [...]}."""
    ing = cfg["ingest"]
    gap_ratio, min_chars = float(ing["space_gap_ratio"]), int(ing["min_page_chars"])
    pn_rows, edge_rows = int(ing["page_number_rows"]), int(ing["header_edge_rows"])
    min_pages = int(ing["header_repeat_min_pages"])

    pages: list[dict] = []
    with pymupdf.open(pdf_path) as doc:
        for pno, page in enumerate(doc, start=1):
            raw = page.get_text("rawdict")
            lines = [r for b in raw["blocks"] for ln in b.get("lines", []) if (r := _line_record(ln, gap_ratio))]
            pages.append({"doc_id": doc_id, "page": pno, "width": round(page.rect.width, 1),
                          "height": round(page.rect.height, 1), "lines": lines})

    # Running headers/footers: index every line by exact text and by digit-normalized text
    exact: dict[str, list[tuple[int, float]]] = defaultdict(list)
    normed: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for p in pages:
        for rec in p["lines"]:
            exact[rec["text"]].append((p["page"], rec["y0"]))
            normed[_norm(rec["text"])].append((p["page"], rec["y0"]))
    min_norm = max(min_pages, int(float(ing["header_repeat_ratio"]) * len(pages)))

    log_rows: list[dict] = []
    kept_pages: list[dict] = []
    for p in pages:
        ranks = _edge_rank(p["lines"]) if p["lines"] else []
        kept = []
        for rec, rank in zip(p["lines"], ranks):
            reason = None
            if rank < pn_rows and PAGE_NUMBER.match(rec["text"]):
                reason = "page_number"
            elif rank < edge_rows:
                n_exact = _repeat_count(exact, rec["text"], rec["y0"])
                if (rank == 0 and n_exact >= 2) or n_exact >= min_pages:
                    reason = "repeated_text"
                elif _repeat_count(normed, _norm(rec["text"]), rec["y0"]) >= min_norm:
                    reason = "repeated_pattern"
            if reason is None:
                kept.append(rec)
                continue
            log_rows.append({"doc_id": doc_id, "page": p["page"], "event": f"removed_{reason}", "text": rec["text"]})
        n_bad = 0
        for rec in kept:
            rec["text"], n = _clean_unreadable(rec["text"], ing["unreadable_placeholder"])
            n_bad += n
        if n_bad:
            log_rows.append({"doc_id": doc_id, "page": p["page"], "event": "unreadable_glyphs", "text": f"{n_bad} glyphs"})
        kept = [r for r in kept if r["text"]]
        p["lines"] = _merge_same_row(kept, gap_ratio)  # after header removal, so page numbers aren't merged into titles
        n_chars = sum(len(r["text"]) for r in kept)
        if n_chars < min_chars:
            log_rows.append({"doc_id": doc_id, "page": p["page"], "event": "skipped_low_text", "text": f"{n_chars} chars"})
            continue
        kept_pages.append(p)
    return kept_pages, log_rows


def run(cfg: dict[str, Any]) -> None:
    paths = cfg["paths"]
    out_dir: Path = paths["processed_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    pages_path, log_path = out_dir / "pages.jsonl", out_dir / "ingest_log.csv"

    all_logs: list[dict] = []
    n_docs = n_pages = 0
    tmp = pages_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for row in read_manifest(paths["manifest"]):
            pdf = paths["raw_dir"] / row["file_name"]
            if not pdf.exists():
                log.warning("Missing file, skipped: %s", pdf.name)
                all_logs.append({"doc_id": row["doc_id"], "page": "", "event": "missing_file", "text": row["file_name"]})
                continue
            try:
                pages, logs = extract_pdf(pdf, row["doc_id"], cfg)
            except Exception as exc:  # a broken PDF should not stop the other documents
                log.error("Failed to read %s: %s", pdf.name, exc)
                all_logs.append({"doc_id": row["doc_id"], "page": "", "event": "read_error", "text": str(exc)})
                continue
            for p in pages:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
            all_logs.extend(logs)
            n_docs += 1
            n_pages += len(pages)
            skipped = sum(1 for r in logs if r["event"] == "skipped_low_text")
            log.info("%-28s %3d pages kept, %d skipped, %d header/footer lines removed",
                     row["doc_id"], len(pages), skipped, sum(1 for r in logs if r["event"].startswith("removed")))
    tmp.replace(pages_path)

    with open(log_path, "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: opens correctly in Excel
        w = csv.DictWriter(f, fieldnames=["doc_id", "page", "event", "text"])
        w.writeheader()
        w.writerows(all_logs)
    log.info("Done: %d documents, %d pages -> %s (log: %s)", n_docs, n_pages, pages_path.name, log_path.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract page lines from the PDFs listed in the manifest.")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run(load_config(args.config))


if __name__ == "__main__":
    main()
