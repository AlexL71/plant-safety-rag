"""Page lines -> clause-based chunks (data/processed/chunks.jsonl).

Each document type has its own clause rules (chosen by doc_id prefix, see `chunking.doc_types`):
- kosha   : KOSHA guides. Sections "1. 목적", sub-sections "4.2", "8.2.2"; appendices "<부록 1>".
- kr_law  : Korean law. Articles "제261조(안전밸브 등의 설치)", with 편/장/절 kept as `section`.
- cfr     : US CFR section. Paragraphs "(a) Purpose." ... "(p) Trade secrets.", appendices A-D.
- booklet : Documents without numbered clauses (e.g. OSHA 3132). Headings found by font.

Numbered headings are accepted only in sequence (e.g. "5." only after "4."), so list items and
cross-references are not mistaken for headings. A clause longer than `max_tokens` is split at its
sub-items ((1), ①, ...) and packed back together up to `max_tokens`; anything still too long is cut
into overlapping windows. Tokens are counted with the reranker's tokenizer, so every chunk fits
the reranker input.

    python -m plant_rag.chunk --config configs/config.yaml
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from plant_rag.config import load_config
from plant_rag.ingest import read_manifest

log = logging.getLogger(__name__)

TOC_LEADER = re.compile(r"(·{5,}|\.{6,}|…{3,})")
TOC_ENTRY = re.compile(r"(·{5,}|\.{6,}|…{3,})\s*([\divxlc]{1,4})?\s*$", re.IGNORECASE)  # "... 12" or bare leaders
LIST_START = re.compile(r"^(\(\d{1,2}\)|\([가-하]\)|\([a-zA-Z]\)|\([ivx]{1,5}\)|[①-⑳]|\d{1,2}\.\s|[•∘◦○▪■□※]|-\s|제\d+조)")
# "가. 나. 다." items only count after a finished sentence: "…설치하여야 한" + "다. 다만" is a wrap
HANGUL_ITEM = re.compile(r"^[가-하]\.\s")
SENTENCE_END = re.compile(r"[.:;)>」\]]\s*$")
HANGUL = re.compile(r"[가-힣]")


@dataclass
class Line:
    text: str
    page: int
    size: float
    font: str
    bold: bool
    y0: float = 0.0
    x0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0


@dataclass
class Section:
    clause_id: str
    heading: str
    lines: list[Line]
    section: str = ""                     # higher-level context, e.g. law part/chapter
    heading_alone: bool = False           # first line is only a heading (keep a line break after it)
    sub_pattern: re.Pattern | None = None  # sub-item marker used to split long clauses
    sub_sep: str = " "                    # "(e)" + "" + "(1)" vs "제261조" + " " + "①"


@dataclass
class Chunk:
    clause_id: str
    heading: str
    section: str
    lines: list[Line] = field(default_factory=list)
    text: str = ""


# ---------------------------------------------------------------- text joining

@lru_cache(maxsize=1)
def get_kiwi():
    """One shared Kiwi (Korean morphological analyzer) instance; loading takes ~1 s."""
    from kiwipiepy import Kiwi

    return Kiwi()


def _space_at_junction(left: str, right: str) -> bool:
    """Korean line wrap: ask Kiwi whether a space belongs between the last word and the next word."""
    a = re.search(r"\S+$", left).group()[-8:]
    b = re.match(r"\S+", right).group()[:8]
    spaced = get_kiwi().space(a + b, reset_whitespace=False)
    n = 0
    for i, ch in enumerate(spaced):
        if ch != " ":
            n += 1
        if n == len(a):
            return i + 1 < len(spaced) and spaced[i + 1] == " "
    return False


def join_lines(lines: list[Line], heading_alone: bool = False) -> str:
    """Join PDF lines into running text. Keeps a line break before list items and after a heading."""
    out = ""
    for k, ln in enumerate(lines):
        t = ln.text.strip()
        if not t:
            continue
        if not out:
            out = t
        elif (k == 1 and heading_alone) or LIST_START.match(t) or (HANGUL_ITEM.match(t) and SENTENCE_END.search(out)):
            out += "\n" + t
        elif out.endswith("-") and len(out) > 1 and out[-2].isalpha() and t[0].islower():
            out = out[:-1] + t  # English hyphenation at line end: "re-" + "quired"
        elif HANGUL.match(out[-1]) and HANGUL.match(t[0]):
            out += (" " if _space_at_junction(out, t) else "") + t
        else:
            out += " " + t
    return out


# ---------------------------------------------------------------- splitters

def _new(sections: list[Section], **kw) -> Section:
    sec = Section(lines=[], **kw)
    sections.append(sec)
    return sec


KOSHA_TOP = re.compile(r"^(\d{1,2})\.(?!\d)\s*(\S.{0,60})$")  # "5. 오리피스…", not the table value "12.4"
KOSHA_SUB = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\.(\d{1,2}))?\.?\s+(\S.{0,60})$")
KOSHA_APPX = re.compile(r"^[<\[]\s*(부록|별표|별지|부표|서식)\s*(?:양식\s*)?(\d*)\s*[>\]]")  # also "<별지 양식3>"
KOSHA_REF_TAIL = re.compile(r"^\s*(의|을|를|에|와|과|으로|로|은|는|이|가|참조|및)")  # "[부록 2]와 같다." is a reference
KOSHA_APPX_HEAD = re.compile(r"^(\d{1,2})\.\s*[가-힣A-Za-z]")  # numbered headings inside an appendix
KOSHA_ITEM = re.compile(r"^\((\d{1,2})\)\s")


def split_kosha(lines: list[Line], doc_id: str) -> list[Section]:
    sections: list[Section] = []
    cur = _new(sections, clause_id="개요", heading="개요", sub_pattern=KOSHA_ITEM)
    last_top, last_sub, top_heading, in_appendix = 0, (0, 0), "", False
    for ln in lines:
        t = ln.text
        m_appx = KOSHA_APPX.match(t)
        if m_appx and (len(t) > 50 or KOSHA_REF_TAIL.match(t[m_appx.end():])):
            m_appx = None  # a cross-reference in running text, not an appendix heading
        m_sub = KOSHA_SUB.match(t)
        m_top = KOSHA_TOP.match(t)
        if m_appx:
            in_appendix = True
            label = f"{m_appx.group(1)} {m_appx.group(2)}".strip()
            cur = _new(sections, clause_id=label, heading=t, heading_alone=True, sub_pattern=KOSHA_APPX_HEAD)
        elif not in_appendix and m_sub and int(m_sub.group(1)) == last_top:
            num = (int(m_sub.group(2)), int(m_sub.group(3) or 0))
            if num > last_sub:
                last_sub = num
                cid = ".".join(g for g in m_sub.groups()[:3] if g)
                cur = _new(sections, clause_id=cid, heading=f"{top_heading} > {t}", heading_alone=True,
                           sub_pattern=KOSHA_ITEM)
        elif not in_appendix and m_top and int(m_top.group(1)) == last_top + 1:
            last_top, last_sub, top_heading = int(m_top.group(1)), (0, 0), t
            cur = _new(sections, clause_id=m_top.group(1), heading=t, heading_alone=True, sub_pattern=KOSHA_ITEM)
        cur.lines.append(ln)
    return sections


LAW_DIV = re.compile(r"^제(\d+)(편|장|절)\s+(.+)$")
LAW_ART = re.compile(r"^제(\d+)조(?:의(\d+))?\s*(?:\(([^)]*)\)|(삭제))")
LAW_ADDENDA = re.compile(r"^부\s*칙\b")
LAW_PARA = re.compile(r"^([①-⑳])")


def split_kr_law(lines: list[Line], doc_id: str) -> list[Section]:
    sections: list[Section] = []
    cur = _new(sections, clause_id="개요", heading="개요", sub_pattern=LAW_PARA)
    divs: dict[str, str] = {}
    last, prefix = (0, 0), ""
    for ln in lines:
        t = ln.text
        m_div, m_art = LAW_DIV.match(t), LAW_ART.match(t)
        if LAW_ADDENDA.match(t):
            last, prefix, divs = (0, 0), "부칙 ", {}
            cur = _new(sections, clause_id="부칙", heading=t, section=t, heading_alone=True, sub_pattern=LAW_PARA)
            divs["부칙"] = t
        elif m_div and not prefix:
            level = m_div.group(2)
            divs[level] = t
            if level == "편":
                divs.pop("장", None)
                divs.pop("절", None)
            elif level == "장":
                divs.pop("절", None)
            continue  # division titles go into `section`, not into the text
        elif m_art:
            num = (int(m_art.group(1)), int(m_art.group(2) or 0))
            if num > last:
                last = num
                art = f"제{num[0]}조" + (f"의{num[1]}" if num[1] else "")
                title = m_art.group(3) or m_art.group(4) or ""
                section = " ".join(divs[k] for k in ("편", "장", "절", "부칙") if k in divs)
                cur = _new(sections, clause_id=prefix + art, heading=f"{prefix}{art}({title})", section=section,
                           sub_pattern=LAW_PARA)
        cur.lines.append(ln)
    return sections


CFR_PARA = re.compile(r"^\(([a-z])\)\s+([A-Z][^.;:—]{1,90}?)\s*[.—]")
CFR_SUB = re.compile(r"^\((\d{1,2})\)\s")
CFR_APPX = re.compile(r"^Appendix\s+([A-Z])\s+to\s+§", re.IGNORECASE)
CFR_ANY_SECTION = re.compile(r"^§\s*(\d+\.\d+)\s*($|[A-Z])")  # "§ 1910.119" alone or with its title
NUMBERED_HEAD = re.compile(r"^(\d{1,2})\.\s+[A-Z]")


def split_cfr(lines: list[Line], doc_id: str) -> list[Section]:
    m = re.search(r"(\d+\.\d+)", doc_id)
    sec_no = m.group(1) if m else ""
    sections: list[Section] = []
    cur: Section | None = None
    expected = "a"
    for ln in lines:
        t = ln.text
        m_any = CFR_ANY_SECTION.match(t)
        if m_any:
            if m_any.group(1) == sec_no and cur is None:
                cur = _new(sections, clause_id=f"§ {sec_no}", heading=t, sub_pattern=CFR_SUB, sub_sep="")
            elif cur is not None and m_any.group(1) != sec_no:
                break  # next CFR section starts: stop
        if cur is None:
            continue  # text of the previous CFR section on the first page
        m_appx, m_para = CFR_APPX.match(t), CFR_PARA.match(t)
        if m_appx:
            expected = None  # no more lettered paragraphs after the appendices start
            cur = _new(sections, clause_id=f"Appendix {m_appx.group(1).upper()}", heading=t,
                       sub_pattern=NUMBERED_HEAD)
        elif expected and m_para and m_para.group(1) == expected:
            cur = _new(sections, clause_id=f"({expected})", heading=f"({expected}) {m_para.group(2)}",
                       sub_pattern=CFR_SUB, sub_sep="")
            expected = chr(ord(expected) + 1)
        cur.lines.append(ln)
    return sections


def split_booklet(lines: list[Line], doc_id: str) -> list[Section]:
    chars: Counter = Counter()
    for ln in lines:
        chars[(ln.font.split("-")[0], ln.size)] += len(ln.text)
    body_family, body_size = chars.most_common(1)[0][0]

    def is_heading(ln: Line) -> bool:
        t = ln.text
        if len(t) > 80 or t[-1] in ".,;:" or t.replace(" ", "").isdigit() or ln.size < body_size - 0.5:
            return False
        return ln.bold or ln.font.split("-")[0] != body_family

    sections: list[Section] = []
    cur = _new(sections, clause_id="Front matter", heading="Front matter")
    chapter, prev_heading = "", False
    for ln in lines:
        if is_heading(ln):
            level1 = ln.size > body_size + 0.5
            prev = cur.lines[-1] if cur.lines else None
            wrapped = (prev_heading and prev is not None and len(cur.lines) <= 2 and prev.page == ln.page
                       and prev.font == ln.font and prev.size == ln.size and 0 < ln.y0 - prev.y0 <= 2 * ln.size)
            if wrapped:  # heading wrapped over two lines
                cur.lines.append(ln)
                name = " ".join(x.text for x in cur.lines)
                if level1:
                    chapter = name
                cur.clause_id = name if level1 else f"{chapter} / {name}" if chapter else name
                cur.heading = cur.clause_id
                continue
            if level1:
                chapter = ln.text
            cid = ln.text if level1 or not chapter else f"{chapter} / {ln.text}"
            cur = _new(sections, clause_id=cid, heading=cid, heading_alone=True)
            prev_heading = True
        else:
            prev_heading = False
        cur.lines.append(ln)
    return sections


SPLITTERS: dict[str, Callable[[list[Line], str], list[Section]]] = {
    "kosha": split_kosha,
    "kr_law": split_kr_law,
    "cfr": split_cfr,
    "booklet": split_booklet,
}


# ---------------------------------------------------------------- size control

@lru_cache(maxsize=2)
def _tokenizer(name: str):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(name)


def count_tokens(text: str, tokenizer_name: str) -> int:
    return len(_tokenizer(tokenizer_name)(text, add_special_tokens=False)["input_ids"])


def _hard_split(ln: Line, max_tokens: int, overlap: int, tok_name: str) -> list[Line]:
    """Split one very long line (e.g. a flattened table) by token offsets."""
    enc = _tokenizer(tok_name)(ln.text, add_special_tokens=False, return_offsets_mapping=True)
    offs = enc["offset_mapping"]
    step = max(1, max_tokens - overlap)
    parts = []
    for s in range(0, len(offs), step):
        e = min(s + max_tokens, len(offs))
        parts.append(Line(ln.text[offs[s][0]: offs[e - 1][1]], ln.page, ln.size, ln.font, ln.bold,
                          ln.y0, ln.x0, ln.x1, ln.y1))
        if e == len(offs):
            break
    return parts


def _windows(lines: list[Line], counts: list[int], max_tokens: int, overlap: int) -> list[list[Line]]:
    """Greedy windows of whole lines, each <= max_tokens, repeating ~overlap tokens of trailing lines."""
    out: list[list[Line]] = []
    start = 0
    while start < len(lines):
        total, end = 0, start
        while end < len(lines) and (total + counts[end] <= max_tokens or end == start):
            total += counts[end]
            end += 1
        out.append(lines[start:end])
        if end >= len(lines):
            break
        back, k = 0, end
        while k - 1 > start and back + counts[k - 1] <= overlap:
            k -= 1
            back += counts[k]
        start = k
    return out


def size_section(sec: Section, cfg: dict[str, Any]) -> list[Chunk]:
    ch = cfg["chunking"]
    max_t, overlap, tok = int(ch["max_tokens"]), int(ch["overlap_tokens"]), ch["tokenizer"]

    lines: list[Line] = []
    for ln in sec.lines:  # split pathological single lines first
        lines.extend(_hard_split(ln, max_t, overlap, tok) if count_tokens(ln.text, tok) > max_t else [ln])
    counts = [count_tokens(ln.text, tok) + 1 for ln in lines]
    base = dict(heading=sec.heading, section=sec.section)

    if sum(counts) <= max_t:
        return [Chunk(clause_id=sec.clause_id, lines=lines, **base)]

    # 1) split at sub-items, 2) pack neighbours up to max_tokens, 3) window anything still too long.
    # The first group's label comes from a marker inside the heading line, e.g. "제261조(...) ① 사업주는".
    intro = ""
    if sec.sub_pattern in (KOSHA_ITEM, CFR_SUB, LAW_PARA):
        m = re.search(r"[\s—–-]" + sec.sub_pattern.pattern.lstrip("^"), lines[0].text)  # also "Contractors—(1)"
        intro = m.group(1) if m else ""
    groups: list[tuple[str, list[int]]] = [(intro, [])]
    for i, ln in enumerate(lines):
        m = sec.sub_pattern.match(ln.text) if sec.sub_pattern else None
        if m and i > 0:
            groups.append((m.group(1) if m.lastindex else m.group(0), []))
        groups[-1][1].append(i)
    groups = [g for g in groups if g[1]]

    def label(subs: list[str]) -> str:
        """e.g. "(e)(1)–(3)", "제261조 ①–②"; an unlabeled clause start reads "(h)–(2)" (start of (h) to (2))."""
        starts_unlabeled = bool(subs) and subs[0] == ""
        subs = [s for s in subs if s]
        if not subs:
            return sec.clause_id
        fmt = (lambda s: f"({s})") if sec.sub_pattern in (KOSHA_ITEM, CFR_SUB) else (lambda s: s)
        if starts_unlabeled:
            return f"{sec.clause_id}–{fmt(subs[-1])}"
        rng = fmt(subs[0]) if len(subs) == 1 else f"{fmt(subs[0])}–{fmt(subs[-1])}"
        return f"{sec.clause_id}{sec.sub_sep}{rng}"

    chunks: list[Chunk] = []
    pack_subs: list[str] = []
    pack_idx: list[int] = []

    def flush() -> None:
        if pack_idx:
            chunks.append(Chunk(clause_id=label(pack_subs), lines=[lines[i] for i in pack_idx], **base))
        pack_subs.clear()
        pack_idx.clear()

    for sub, idx in groups:
        g_tokens = sum(counts[i] for i in idx)
        if g_tokens > max_t:
            flush()
            wins = _windows([lines[i] for i in idx], [counts[i] for i in idx], max_t, overlap)
            for k, w in enumerate(wins, 1):
                chunks.append(Chunk(clause_id=f"{label([sub])} (part {k}/{len(wins)})", lines=w, **base))
        elif sum(counts[i] for i in pack_idx) + g_tokens > max_t:
            flush()
            pack_subs.append(sub)
            pack_idx.extend(idx)
        else:
            pack_subs.append(sub)
            pack_idx.extend(idx)
    flush()
    return chunks


# ---------------------------------------------------------------- driver

def doc_type_for(doc_id: str, cfg: dict[str, Any]) -> str:
    for prefix, kind in (cfg["chunking"].get("doc_types") or {}).items():
        if doc_id.startswith(prefix):
            return kind
    return "booklet"


def _is_toc_page(page: dict, n_pages: int, min_leaders: int) -> bool:
    """A table of contents: near the front of the document, with many lines ending in dot leaders
    (+ page number). The position check keeps dotted lists such as CFR Appendix A (chemical ... CAS ... TQ)."""
    if page["page"] > max(5, 0.25 * n_pages):
        return False
    return sum(1 for r in page["lines"] if TOC_ENTRY.search(r["text"])) >= min_leaders


def chunk_document(doc_id: str, pages: list[dict], meta: dict[str, str], cfg: dict[str, Any]) -> list[dict]:
    kind = doc_type_for(doc_id, cfg)
    min_leaders = int(cfg["chunking"]["toc_min_leader_lines"])
    n_pages = max(p["page"] for p in pages)
    lines = [Line(TOC_LEADER.sub(" ... ", r["text"]).strip(), p["page"], r["size"], r["font"], r["bold"], r["y0"],
                  r["x0"], r["x1"], r["y1"])
             for p in sorted(pages, key=lambda p: p["page"]) if not _is_toc_page(p, n_pages, min_leaders)
             for r in p["lines"] if TOC_LEADER.sub("", r["text"]).strip()]
    sections = SPLITTERS[kind](lines, doc_id)

    min_chars, tok = int(cfg["chunking"]["min_chars"]), cfg["chunking"]["tokenizer"]
    records: list[dict] = []
    for sec in sections:
        for ch in size_section(sec, cfg):
            first_is_heading = sec.heading_alone and ch.lines and ch.lines[0] is sec.lines[0]
            text = join_lines(ch.lines, heading_alone=first_is_heading)
            if len(text) < min_chars:
                continue
            records.append({
                "chunk_id": f"{doc_id}::{len(records):04d}",
                "doc_id": doc_id,
                "doc_type": kind,
                "clause_id": ch.clause_id,
                "heading": ch.heading,
                "section": ch.section,
                "title": meta["title"],
                "page_start": min(ln.page for ln in ch.lines),
                "page_end": max(ln.page for ln in ch.lines),
                "lang": meta["language"],
                "n_tokens": count_tokens(text, tok),
                "text": text,
                "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                # where the chunk sits in the PDF: one [page, x0, y0, x1, y1] box per line (PDF points),
                # used by the app to outline the passage on the original page
                "boxes": [[ln.page, round(ln.x0, 1), round(ln.y0, 1), round(ln.x1, 1), round(ln.y1, 1)]
                          for ln in ch.lines],
            })
    return records


def run(cfg: dict[str, Any]) -> None:
    paths = cfg["paths"]
    pages_path: Path = paths["processed_dir"] / "pages.jsonl"
    out_path: Path = paths["processed_dir"] / "chunks.jsonl"
    if not pages_path.exists():
        raise FileNotFoundError(f"{pages_path} not found. Run: python -m plant_rag.ingest")

    by_doc: dict[str, list[dict]] = defaultdict(list)
    with open(pages_path, encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            by_doc[p["doc_id"]].append(p)
    meta = {r["doc_id"]: r for r in read_manifest(paths["manifest"])}

    tmp = out_path.with_suffix(".tmp")
    total = 0
    with open(tmp, "w", encoding="utf-8") as f:
        for doc_id, pages in by_doc.items():
            if doc_id not in meta:
                log.warning("%s is in pages.jsonl but not in the manifest; skipped", doc_id)
                continue
            recs = chunk_document(doc_id, pages, meta[doc_id], cfg)
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            toks = [r["n_tokens"] for r in recs] or [0]
            parts = sum(1 for r in recs if "(part " in r["clause_id"])
            log.info("%-28s %-7s %4d chunks | tokens median %3d, max %3d | %d windowed",
                     doc_id, doc_type_for(doc_id, cfg), len(recs), statistics.median(toks), max(toks), parts)
            total += len(recs)
    tmp.replace(out_path)
    log.info("Done: %d chunks -> %s", total, out_path.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Split extracted pages into clause-based chunks.")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx", "huggingface_hub", "transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    run(load_config(args.config))


if __name__ == "__main__":
    main()
