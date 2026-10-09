"""Input safety checks: run on everything that comes from an uploaded file.

The paper is untrusted. These checks (1) refuse files we should not process,
(2) clean the text, (3) hold out sentences that look like instructions to an AI,
and (4) wrap what is left as data with a random tag the paper cannot guess.
"""
from __future__ import annotations

import re
import secrets
import unicodedata
from dataclasses import dataclass

from services.pdf_reader import Page

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_REJECT_PAGES = 300  # beyond this it is a book or a manual, not something we can explain
MAX_HELD_OUT = 8  # this many instruction-like sentences means the file is not a normal document
MAX_PAGES = 80  # longer files are trimmed to the first 80 pages, not rejected
MIN_TEXT_CHARS = 1500  # fewer than this usually means a scanned PDF with no text layer
CONFIDENTIAL_SCAN_PAGES = 3
MAX_PROMPT_CHARS = 300_000  # about 75K tokens: inside the free-tier 250K tokens-per-minute limit

CONFIDENTIAL_PATTERNS = [
    r"\bconfidential\b",
    r"\binternal use only\b",
    r"\bdo not (distribute|share|copy)\b",
    r"\bproprietary (and|&) confidential\b",
    r"\bnot for (public )?(release|distribution)\b",
    r"\battorney[- ]client\b",
    r"\bprivileged\b.{0,20}\bconfidential\b",
]

INJECTION_PATTERNS = [
    r"ignore (all |any |the |your )?(previous|prior|above|earlier|preceding) (instructions?|prompts?|rules?|messages?)",
    r"disregard (all |any |the |your )?(previous|prior|above|earlier|preceding|system)",
    r"forget (everything|all|your|the) (above|previous|prior|instructions?|rules?)",
    r"(reveal|show|print|repeat|output|display|leak) (me )?(your |the )?(system|hidden|initial|secret) (prompt|instructions?|message)",
    r"\bsystem prompt\b",
    r"you are (now|no longer)\b",
    r"\b(developer|dan|jailbreak|god|admin) mode\b",
    r"\bnew (instructions?|rules?|task)\s*:",
    r"do not (follow|obey) (the )?(above|previous|prior|earlier)",
    r"<\s*/?\s*(system|assistant|user|paper\w*|instructions?)\b",
    r"<\|[^>]{0,40}\|>",
    r"\bbegin (system|instructions?)\b",
    r"(send|post|upload|exfiltrate|email).{0,50}(api[ _-]?key|secret|password|token)",
    r"(respond|reply|answer|output) (only )?with the (word|text|string)",
]

_CONF_RE = [re.compile(p, re.I) for p in CONFIDENTIAL_PATTERNS]
_INJ_RE = [re.compile(p, re.I | re.S) for p in INJECTION_PATTERNS]
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class CheckResult:
    ok: bool
    message: str = ""


def check_upload_bytes(data: bytes) -> CheckResult:
    if not data:
        return CheckResult(False, "📭 That file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        return CheckResult(False, f"📦 That file is too large (the limit is {mb} MB).")
    if not data.lstrip()[:5] == b"%PDF-":
        return CheckResult(False, "🤔 That does not look like a real PDF file.")
    return CheckResult(True)


def check_page_count(count: int) -> CheckResult:
    if count < 1:
        return CheckResult(False, "📭 That PDF has no pages.")
    if count > MAX_REJECT_PAGES:
        return CheckResult(False, f"📚 That file has {count} pages. That is more like a book or a manual than a paper.")
    return CheckResult(True)


def check_text_amount(pages: list[Page]) -> CheckResult:
    total = sum(len(p.text.strip()) for p in pages)
    if total < MIN_TEXT_CHARS:
        return CheckResult(False, "🖼️ I could not find enough readable text. It looks like a scanned or image-only PDF.")
    return CheckResult(True)


def find_confidential_markers(pages: list[Page], scan_pages: int = CONFIDENTIAL_SCAN_PAGES) -> list[str]:
    """Look for markings such as 'Confidential' on the first pages."""
    found: list[str] = []
    for page in pages[:scan_pages]:
        for regex in _CONF_RE:
            match = regex.search(page.text)
            if match and match.group(0).lower() not in found:
                found.append(match.group(0).lower())
    return found


def clean_text(text: str) -> str:
    """Normalise unicode and remove invisible characters (zero-width, bidi, control)."""
    text = unicodedata.normalize("NFKC", text)  # also turns ligatures like 'ﬁ' into 'fi'
    kept = []
    for ch in text:
        category = unicodedata.category(ch)
        if category == "Cf":  # zero-width, bidirectional and other format characters
            continue
        if category == "Cc" and ch not in "\n\t":
            continue
        kept.append(ch)
    text = "".join(kept)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def looks_like_instruction(sentence: str) -> bool:
    return any(regex.search(sentence) for regex in _INJ_RE)


def hold_out_suspicious(pages: list[Page]) -> tuple[list[Page], list[dict]]:
    """Remove sentences that look like instructions to an AI. Returns (pages, held_out)."""
    cleaned: list[Page] = []
    held: list[dict] = []
    for page in pages:
        sentences = _SENTENCE_SPLIT.split(page.text)
        keep = []
        for sentence in sentences:
            if looks_like_instruction(sentence):
                held.append({"page": page.number, "snippet": " ".join(sentence.split())[:140]})
            else:
                keep.append(sentence)
        cleaned.append(Page(page.number, " ".join(keep) if len(keep) != len(sentences) else page.text,
                            page.hidden_chars_removed))
    return cleaned, held


def wrap_untrusted(text: str) -> tuple[str, str]:
    """Wrap text in a random tag. Returns (tag, wrapped). The paper cannot guess the tag,
    so it cannot close the tag early and 'escape' into the instructions."""
    while True:
        tag = "paper_" + secrets.token_hex(6)
        if tag not in text:
            break
    return tag, f"<{tag}>\n{text}\n</{tag}>"
