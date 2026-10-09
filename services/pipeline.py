"""Step 1 of every request: turn an uploaded file into safe, clean, page-tagged text."""
from __future__ import annotations

from dataclasses import dataclass

from safety import input_checks as checks
from services.pdf_reader import Page, count_pages, read_pdf


class PaperRejected(Exception):
    """The upload was refused. The message is safe to show the visitor."""


@dataclass
class PreparedPaper:
    pages: list[Page]
    held_out: list[dict]
    hidden_chars_removed: int


def prepare_paper(data: bytes) -> PreparedPaper:
    result = checks.check_upload_bytes(data)
    if not result.ok:
        raise PaperRejected(result.message)
    try:
        result = checks.check_page_count(count_pages(data))
        if not result.ok:
            raise PaperRejected(result.message)
        pages = read_pdf(data, max_pages=checks.MAX_PAGES)
    except PaperRejected:
        raise
    except Exception:
        raise PaperRejected("I could not open that PDF. It may be damaged or password-protected.") from None

    hidden = sum(p.hidden_chars_removed for p in pages)
    pages = [Page(p.number, checks.clean_text(p.text), p.hidden_chars_removed) for p in pages]

    result = checks.check_text_amount(pages)
    if not result.ok:
        raise PaperRejected(result.message)

    markers = checks.find_confidential_markers(pages)
    if markers:
        raise PaperRejected("This paper looks confidential (it contains: " + ", ".join(markers[:3]) +
                            "). Paper Playground is for public papers only.")

    pages, held = checks.hold_out_suspicious(pages)
    return PreparedPaper(pages=pages, held_out=held, hidden_chars_removed=hidden)
