"""Deterministic checks for model output that will be shown, printed or posted: citations and numbers.

Used by visuals, task plans and notices. Nothing here calls a model, so the checks are cheap, repeatable and
easy to explain:

- Citation check: every element must cite at least one evidence passage, and only passages that exist.
- Numbers guard: every number in an element must appear in the text of a passage that element cites
  (after normalising "1,000" -> "1000" and full-width digits). A safety notice that says "19.5%" when the cited
  clause says "18%" is dropped instead of printed.

Both return the element list split into kept and dropped, with a reason per dropped element, so the caller
can report how much was removed (that rate is an evaluation metric).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def normalize_number(s: str) -> str:
    """"1,000" -> "1000", "0.50" -> "0.5", "07" -> "7"; keeps decimals."""
    s = s.replace(",", "")
    whole, _, frac = s.partition(".")
    whole = whole.lstrip("0") or "0"
    frac = frac.rstrip("0")
    return f"{whole}.{frac}" if frac else whole


def numbers_in(text: str) -> list[str]:
    """Normalised numbers in a text (full-width digits are folded to ASCII first)."""
    t = unicodedata.normalize("NFKC", text or "")
    out = []
    for m in NUMBER.finditer(t):
        raw = m.group(0)
        # "1.2.3" style clause numbers: check each part separately
        parts = raw.split(".") if raw.count(".") > 1 else [raw]
        out.extend(normalize_number(p) for p in parts if p)
    return out


# Number words in the sources count as their digits ("every three years" supports 3, "a half hour" 0.5 and 30
# minutes, "annually" 1 per year), so a visual may write the digit.
WORD_NUMBERS = {
    "one": ["1"], "two": ["2"], "three": ["3"], "four": ["4"], "five": ["5"], "six": ["6"], "seven": ["7"],
    "eight": ["8"], "nine": ["9"], "ten": ["10"], "eleven": ["11"], "twelve": ["12"], "fifteen": ["15"],
    "twenty": ["20"], "thirty": ["30"], "forty": ["40"], "fifty": ["50"], "hundred": ["100"],
    "half": ["0.5", "30"], "annually": ["1", "12"], "annual": ["1", "12"], "yearly": ["1", "12"],
    "monthly": ["1"], "weekly": ["1"], "daily": ["1"], "quarterly": ["3"], "once": ["1"], "twice": ["2"],
    "매년": ["1"], "매월": ["1"], "매일": ["1"], "반기": ["6"], "분기": ["3"],
}
WORD_RE = re.compile(r"[A-Za-z]+|매년|매월|매일|반기|분기")


def passage_numbers(passages: Iterable[dict]) -> set[str]:
    nums: set[str] = set()
    for p in passages:
        for key in ("text", "clause_id", "title", "heading"):
            value = str(p.get(key) or "")
            nums.update(numbers_in(value))
            for w in WORD_RE.findall(value):
                nums.update(WORD_NUMBERS.get(w.lower(), []))
    return nums


@dataclass
class CheckResult:
    kept: list[dict] = field(default_factory=list)
    dropped: list[dict] = field(default_factory=list)   # {"element": ..., "reason": ...}

    @property
    def total(self) -> int:
        return len(self.kept) + len(self.dropped)

    def stats(self) -> dict[str, int]:
        reasons: dict[str, int] = {}
        for d in self.dropped:
            reasons[d["reason"]] = reasons.get(d["reason"], 0) + 1
        return {"elements": self.total, "kept": len(self.kept), "dropped": len(self.dropped), **reasons}


CITE_MARKS = re.compile(r"\s*\[\d+(?:\s*[,，]\s*\d+)*\]")   # "[2]", "[1, 2, 3]" written into the text
LEAD_ENUM = re.compile(r"^\s*\d{1,2}[.)]\s+")                # "4. 작업허가서 발급" (the visual numbers steps itself)


def clean_text_fields(el: dict, keys: tuple[str, ...]) -> dict:
    """Remove citation marks and leading list numbers the model sometimes writes into text fields: they are not
    content, would be checked as numbers by the guard, and the page shows citations and step numbers itself."""
    out = dict(el)
    for k in keys:
        if isinstance(out.get(k), str):
            out[k] = LEAD_ENUM.sub("", CITE_MARKS.sub("", out[k])).strip()
    return out


def check_elements(elements: list[dict], text_keys: tuple[str, ...], passages: dict[int, dict],
                   cite_key: str = "cite", allow_uncited: bool = False,
                   extra_numbers: Iterable[str] = ()) -> CheckResult:
    """Keep elements whose citations are valid and whose numbers all appear in a cited passage.

    `passages` maps evidence number (1-based) -> chunk dict. `text_keys` are the element fields to scan for
    numbers. `extra_numbers` are always allowed (e.g. numbers the user typed in the question).
    """
    res = CheckResult()
    allowed_extra = {normalize_number(n) for n in extra_numbers}
    for el in elements:
        el = clean_text_fields(el, text_keys)
        cites = [c for c in (el.get(cite_key) or []) if isinstance(c, int)]
        valid = [c for c in cites if c in passages]
        if not valid and not allow_uncited:
            res.dropped.append({"element": el, "reason": "no_valid_citation"})
            continue
        el = {**el, cite_key: valid}
        allowed = passage_numbers(passages[c] for c in valid) | allowed_extra
        text = " ".join(str(el.get(k) or "") for k in text_keys)
        missing = [n for n in numbers_in(text) if n not in allowed]
        if missing:
            res.dropped.append({"element": el, "reason": "number_not_in_source", "numbers": missing})
            continue
        res.kept.append(el)
    return res


def merge_stats(*results: CheckResult) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for r in results:
        for k, v in r.stats().items():
            out[k] = out.get(k, 0) + v
    return out
