"""Read a PDF into page-tagged text, leaving out text a human reader could not see.

Hidden text is a known way to smuggle instructions into a document: white text,
tiny text, or text placed off the page. We drop those characters before anything
reaches the model, and we count how many were removed so the app can say so.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import pdfplumber

MIN_VISIBLE_FONT_SIZE = 3.0  # points; smaller than this is not readable by a person
WHITE_LEVEL = 0.98


@dataclass
class Page:
    number: int  # 1-based position in the PDF (not the printed page label)
    text: str
    hidden_chars_removed: int = 0


def _stream(source):
    return io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source


def _is_white(color) -> bool:
    """True if a fill colour is white (gray, RGB or CMYK)."""
    if color is None:
        return False
    if isinstance(color, (int, float)):
        return color >= WHITE_LEVEL
    try:
        values = [float(v) for v in color]
    except (TypeError, ValueError):
        return False  # e.g. a pattern name: not a plain colour
    if len(values) in (1, 3):
        return all(v >= WHITE_LEVEL for v in values)
    if len(values) == 4:  # CMYK: all zeros is white
        return all(v <= 1 - WHITE_LEVEL for v in values)
    return False


def _is_hidden_char(obj, page_width: float, page_height: float) -> bool:
    if obj.get("object_type") != "char":
        return False
    if obj.get("size", 10) < MIN_VISIBLE_FONT_SIZE:
        return True
    if _is_white(obj.get("non_stroking_color")):
        return True
    if obj["x1"] < 0 or obj["x0"] > page_width or obj["bottom"] < 0 or obj["top"] > page_height:
        return True  # sits outside the visible page
    return False


def count_pages(source) -> int:
    with pdfplumber.open(_stream(source)) as pdf:
        return len(pdf.pages)



def find_gutter(words: list[dict], page_width: float):
    """Find the empty vertical strip between two text columns, or None for a one-column page.

    A strip counts as a gutter if it sits near the middle of the page, is at least 8 points wide,
    and almost no words cross it (a few full-width lines such as a title or a caption are allowed).
    Both sides must hold a real share of the words, so a page with one narrow margin note is not split.
    """
    if len(words) < 120:
        return None
    lo, hi = int(page_width * 0.30), int(page_width * 0.70)
    allowed = max(3, int(len(words) * 0.03))
    runs, start = [], None
    for x in range(lo, hi + 1):
        crossing = sum(1 for w in words if w["x0"] < x < w["x1"])
        if crossing <= allowed:
            start = x if start is None else start
        elif start is not None:
            runs.append((start, x - 1))
            start = None
    if start is not None:
        runs.append((start, hi))
    runs = [r for r in runs if r[1] - r[0] >= 8]
    if not runs:
        return None
    left, right = max(runs, key=lambda r: (r[1] - r[0]) - abs((r[0] + r[1]) / 2 - page_width / 2) * 0.2)
    mid = (left + right) / 2
    on_left = sum(1 for w in words if w["x1"] <= mid)
    on_right = sum(1 for w in words if w["x0"] >= mid)
    if min(on_left, on_right) < len(words) * 0.25:
        return None
    return left, right


def extract_page_text(page) -> str:
    """Page text in reading order: each column top to bottom, full-width lines where they sit."""
    words = page.extract_words(x_tolerance=1.5, keep_blank_chars=False)
    gutter = find_gutter(words, page.width)
    if gutter is None:
        # x_tolerance=1.5 stops words being glued together (a bug we hit on day 1)
        return page.extract_text(x_tolerance=1.5) or ""
    g_left, g_right = gutter
    mid = (g_left + g_right) / 2
    # Group words into lines, then mark the lines that cross the gutter (titles, captions, page numbers).
    lines: list[dict] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(w["top"] - lines[-1]["top"]) <= 3:
            line = lines[-1]
            line["bottom"] = max(line["bottom"], w["bottom"])
        else:
            line = {"top": w["top"], "bottom": w["bottom"], "full": False}
            lines.append(line)
        if w["x0"] < g_right and w["x1"] > g_left:
            line["full"] = True
    # Full-width lines split the page into bands; inside a band, read the left column then the right.
    parts: list[str] = []
    band_top = None
    def flush(top, bottom):
        if top is None:
            return
        for x0, x1 in ((0, mid), (mid, page.width)):
            text = page.crop((x0, max(top - 1, 0), x1, min(bottom + 1, page.height))).extract_text(x_tolerance=1.5)
            if text and text.strip():
                parts.append(text)
    band_bottom = None
    for line in lines:
        if line["full"]:
            flush(band_top, band_bottom)
            band_top = band_bottom = None
            text = page.crop((0, max(line["top"] - 1, 0), page.width, min(line["bottom"] + 1, page.height))).extract_text(x_tolerance=1.5)
            if text and text.strip():
                parts.append(text)
        else:
            band_top = line["top"] if band_top is None else band_top
            band_bottom = line["bottom"]
    flush(band_top, band_bottom)
    return "\n".join(parts)


def read_pdf(source, max_pages: int = 40) -> list[Page]:
    """Return one Page per PDF page (up to max_pages) with hidden text removed."""
    pages: list[Page] = []
    with pdfplumber.open(_stream(source)) as pdf:
        for number, page in enumerate(pdf.pages[:max_pages], start=1):
            width, height = page.width, page.height
            visible = page.filter(lambda obj: not _is_hidden_char(obj, width, height))
            text = extract_page_text(visible)
            removed = len(page.chars) - len(visible.chars)
            pages.append(Page(number=number, text=text, hidden_chars_removed=removed))
    return pages
