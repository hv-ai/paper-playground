"""Step 1 of every request: turn an uploaded file into safe, clean, page-tagged text."""
from __future__ import annotations

from dataclasses import dataclass

from safety import input_checks as checks
from services.pdf_reader import Page, count_pages, read_pdf


class PaperRejected(Exception):
    """The upload was refused. The message is safe to show the visitor."""


OUTRO = ("\n\nThis playground is for text-based research papers (and similar public documents), so this file is not a fit. "
         "Thank you for your curiosity! 🙏 Please try another tool for this kind of file.")


def reject(reason: str) -> PaperRejected:
    return PaperRejected(reason + OUTRO)


@dataclass
class PreparedPaper:
    pages: list[Page]
    held_out: list[dict]
    hidden_chars_removed: int
    total_pages: int = 0  # pages in the original file; we read at most MAX_PAGES of them


def prepare_paper(data: bytes) -> PreparedPaper:
    result = checks.check_upload_bytes(data)
    if not result.ok:
        raise reject(result.message)
    try:
        total_pages = count_pages(data)
        result = checks.check_page_count(total_pages)
        if not result.ok:
            raise reject(result.message)
        pages = read_pdf(data, max_pages=checks.MAX_PAGES)
    except PaperRejected:
        raise
    except Exception:
        raise reject("🔒 I could not open that PDF. It may be damaged or password-protected.") from None

    hidden = sum(p.hidden_chars_removed for p in pages)
    pages = [Page(p.number, checks.clean_text(p.text), p.hidden_chars_removed) for p in pages]

    result = checks.check_text_amount(pages)
    if not result.ok:
        raise reject(result.message)

    markers = checks.find_confidential_markers(pages)
    if markers:
        raise reject("🙈 This looks confidential (it contains: " + ", ".join(markers[:3]) +
                     "). Paper Playground is for public documents only.")

    pages, held = checks.hold_out_suspicious(pages)
    if len(held) >= checks.MAX_HELD_OUT:
        raise reject("🛡️ This file has many sentences that try to give instructions to an AI, so I stopped.")
    return PreparedPaper(pages=pages, held_out=held, hidden_chars_removed=hidden, total_pages=total_pages)
