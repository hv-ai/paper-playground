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


def read_pdf(source, max_pages: int = 40) -> list[Page]:
    """Return one Page per PDF page (up to max_pages) with hidden text removed."""
    pages: list[Page] = []
    with pdfplumber.open(_stream(source)) as pdf:
        for number, page in enumerate(pdf.pages[:max_pages], start=1):
            width, height = page.width, page.height
            visible = page.filter(lambda obj: not _is_hidden_char(obj, width, height))
            # x_tolerance=1.5 stops words being glued together (a bug we hit on day 1)
            text = visible.extract_text(x_tolerance=1.5) or ""
            removed = len(page.chars) - len(visible.chars)
            pages.append(Page(number=number, text=text, hidden_chars_removed=removed))
    return pages
