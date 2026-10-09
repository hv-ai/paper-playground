"""Check that each key fact's quote really appears in the paper.

What this proves, and what it does not:
- PROVES: the quoted words appear, in that exact order, on the cited PDF page. We use an exact
  match after only conservative clean-up (whitespace, line-end hyphenation, typographic quotes
  and dashes, upper/lower case). Digits, decimal points and signs are never altered or ignored,
  so "28.4" can never match "98.4".
- DOES NOT PROVE: that the quote supports the claim next to it. That needs a separate
  assessment. As a small guard we flag claims that mention a number that is missing from
  their own quote, so a reader knows to look closer.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from services.pdf_reader import Page

MIN_QUOTE_CHARS = 25

_QUOTE_MAP = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                            "−": "-", "–": "-", "—": "-", "‐": "-", "‑": "-"})
_EDGE_JUNK = " \t\n\"'."
_HYPHEN_JOIN = re.compile(r"(?<=[A-Za-z])-[ \t]*\n[ \t]*(?=[a-z])")  # "dis-\npensing" -> "dispensing"
_HYPHEN_KEEP = re.compile(r"-[ \t]*\n[ \t]*")                       # "state-\nof-art" -> "state-of-art"
_NUMBER = re.compile(r"(?<![\w.])([-+]?)(\d[\d,]*(?:\.\d+)?)")


def _tidy(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_QUOTE_MAP)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return " ".join(text.split()).casefold()


def normalise_quote(quote: str) -> str:
    return _tidy(quote).strip(_EDGE_JUNK)


def page_variants(page_text: str) -> list[str]:
    """The page text with each reasonable reading of a line-end hyphen."""
    return [_tidy(page_text),
            _tidy(_HYPHEN_JOIN.sub("", page_text)),
            _tidy(_HYPHEN_KEEP.sub("-", page_text))]


def _found_with_clean_edges(q: str, text: str) -> bool:
    """q is in text, and the match does not cut a number short or drop its sign.
    ('28' must not match inside '28.4', and '3.5' must not match inside '-3.5'.)"""
    start = text.find(q)
    while start != -1:
        end = start + len(q)
        before = text[start - 1] if start > 0 else ""
        before2 = text[start - 2] if start > 1 else ""
        after = text[end] if end < len(text) else ""
        after2 = text[end + 1] if end + 1 < len(text) else ""
        bad_end = q[-1].isdigit() and (after.isdigit() or (after in ".," and after2.isdigit()))
        bad_start = q[0].isdigit() and (before.isdigit() or before in "+-" and before != ""
                                        or (before in ".," and before2.isdigit()))
        if not (bad_end or bad_start):
            return True
        start = text.find(q, start + 1)
    return False


def quote_in_page(quote: str, page_text: str) -> bool:
    q = normalise_quote(quote)
    return len(q) >= MIN_QUOTE_CHARS and any(_found_with_clean_edges(q, v) for v in page_variants(page_text))


def numbers_in(text: str) -> set[str]:
    """Numbers with their sign, as comparable strings: '28.4', '-3.5', '2014'."""
    found = set()
    for sign, digits in _NUMBER.findall(_tidy(text)):
        found.add(("-" if sign == "-" else "") + digits.replace(",", ""))
    return found


def numbers_missing_from_quote(fact_text: str, quote: str) -> list[str]:
    in_quote = {n.lstrip("-") for n in numbers_in(quote)} | numbers_in(quote)
    return sorted(n for n in numbers_in(fact_text) if n not in in_quote)


@dataclass
class FactResult:
    fact: dict
    status: str  # 'matched' | 'page_corrected' | 'unmatched'
    reason: str = ""
    numbers_not_in_quote: list[str] = field(default_factory=list)


def verify_fact(fact: dict, pages: list[Page]) -> FactResult:
    quote = fact["quote"]
    if len(normalise_quote(quote)) < MIN_QUOTE_CHARS:
        return FactResult(fact, "unmatched", "quote too short to check")
    flags = numbers_missing_from_quote(fact["fact"], quote)
    by_number = {p.number: p for p in pages}
    claimed = by_number.get(fact["page"])
    if claimed is not None and quote_in_page(quote, claimed.text):
        return FactResult({**fact}, "matched", numbers_not_in_quote=flags)
    for page in pages:
        if quote_in_page(quote, page.text):
            return FactResult({**fact, "page": page.number}, "page_corrected",
                              f"cited page {fact['page']}, found on page {page.number}", flags)
    return FactResult(fact, "unmatched", "quote not found in the paper")


def verify_facts(facts: list[dict], pages: list[Page]) -> tuple[list[dict], list[FactResult]]:
    """Return (facts whose quote matched, results for facts that were dropped)."""
    kept: list[dict] = []
    dropped: list[FactResult] = []
    for fact in facts:
        result = verify_fact(fact, pages)
        if result.status == "unmatched":
            dropped.append(result)
        else:
            kept.append({**result.fact, "status": result.status, "numbers_not_in_quote": result.numbers_not_in_quote})
    return kept, dropped
