"""Find a paper on arXiv and download its PDF.

Safety notes:
- We never fetch a URL the visitor typed. We pull out an arXiv ID, check it against a strict
  pattern, and build the address ourselves, so this cannot be pointed at another site.
- Redirects are only followed inside arxiv.org.
- Downloads stop at the same size limit as uploads.
- Titles and authors from arXiv are treated as untrusted text and cleaned before display.
- Calls are spaced out (arXiv asks for no more than one request every 3 seconds).
"""
from __future__ import annotations

import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from safety.input_checks import MAX_UPLOAD_BYTES
from services.schema import SchemaError, clean_model_text

ALLOWED_HOSTS = {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}
NEW_ID = re.compile(r"^\d{4}\.\d{4,5}(v\d{1,3})?$")
OLD_ID = re.compile(r"^[a-z\-]{2,20}(\.[A-Za-z]{2})?/\d{7}(v\d{1,3})?$")
MAX_QUERY_CHARS = 300
MAX_API_BYTES = 300_000
_ATOM = "{http://www.w3.org/2005/Atom}"


class ArxivError(Exception):
    """A problem with the arXiv lookup. The message is safe to show the visitor."""


@dataclass
class Query:
    kind: str   # "id" or "title"
    value: str


@dataclass
class Match:
    arxiv_id: str
    title: str
    authors: str
    year: str
    date: str = ""  # YYYY-MM-DD of the first version


def is_arxiv_id(text: str) -> bool:
    return bool(NEW_ID.match(text) or OLD_ID.match(text))


def parse_query(text: str) -> Query:
    text = (text or "").strip()
    if not text:
        raise ArxivError("Type a paper title, an arXiv link or an arXiv ID first.")
    if len(text) > MAX_QUERY_CHARS:
        raise ArxivError("That is too long. Paste just the title, link or ID.")
    candidate = re.sub(r"^arxiv:\s*", "", text, flags=re.I)
    if re.match(r"^https?://", candidate, flags=re.I):
        parsed = urllib.parse.urlparse(candidate)
        if (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
            raise ArxivError("Only arxiv.org links are supported. For other papers, upload the PDF.")
        path = parsed.path
        for prefix in ("/abs/", "/pdf/"):
            if path.startswith(prefix):
                path = path[len(prefix):]
                break
        else:
            raise ArxivError("I could not find an arXiv ID in that link.")
        path = re.sub(r"\.pdf$", "", path).strip("/")
        if not is_arxiv_id(path):
            raise ArxivError("I could not find an arXiv ID in that link.")
        return Query("id", path)
    if is_arxiv_id(candidate):
        return Query("id", candidate)
    if "://" in candidate:
        raise ArxivError("Only arxiv.org links are supported. For other papers, upload the PDF.")
    return Query("title", " ".join(text.split()))


class _SameSiteRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlparse(newurl)
        if target.scheme != "https" or (target.hostname or "").lower() not in ALLOWED_HOSTS:
            raise ArxivError("arXiv sent me somewhere unexpected, so I stopped.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def default_fetch(url: str, max_bytes: int, timeout: float = 20.0) -> bytes:
    opener = urllib.request.build_opener(_SameSiteRedirects)
    request = urllib.request.Request(url, headers={"User-Agent": "PaperPlayground/1.0 (student project)"})
    chunks, total = [], 0
    with opener.open(request, timeout=timeout) as response:
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ArxivError("That file is too large.")
            chunks.append(chunk)
    return b"".join(chunks)


def _clean(value: str | None, limit: int) -> str:
    try:
        return clean_model_text(value or "", limit)
    except SchemaError:
        return ""


def parse_results(xml_bytes: bytes, limit: int = 3) -> list[Match]:
    """Read arXiv's Atom reply. Refuses anything with a DTD or entities (XML bomb protection)."""
    head = xml_bytes.lower()
    if b"<!doctype" in head or b"<!entity" in head:
        raise ArxivError("arXiv sent a reply I could not read safely.")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        raise ArxivError("arXiv sent a reply I could not read.") from None
    matches: list[Match] = []
    for entry in root.findall(_ATOM + "entry"):
        raw_id = (entry.findtext(_ATOM + "id") or "").strip()
        arxiv_id = raw_id.split("/abs/", 1)[-1] if "/abs/" in raw_id else ""
        if not is_arxiv_id(arxiv_id):
            continue
        title = _clean(entry.findtext(_ATOM + "title"), 200)
        if not title:
            continue
        names = [_clean(a.findtext(_ATOM + "name"), 60) for a in entry.findall(_ATOM + "author")]
        names = [n for n in names if n]
        authors = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
        published = (entry.findtext(_ATOM + "published") or "")[:10]
        year = published[:4]
        date = published if re.fullmatch(r"\d{4}-\d{2}-\d{2}", published) else ""
        matches.append(Match(arxiv_id, title, authors, year if year.isdigit() else "", date))
    return matches[:limit]


class ArxivClient:
    def __init__(self, fetch=default_fetch, min_gap: float = 3.0, clock=time.monotonic, sleep=time.sleep):
        self._fetch, self._gap, self._clock, self._sleep = fetch, min_gap, clock, sleep
        self._last = None
        self._lock = threading.Lock()

    def _get(self, url: str, max_bytes: int) -> bytes:
        with self._lock:  # one arXiv request at a time, spaced apart
            if self._last is not None:
                wait = self._gap - (self._clock() - self._last)
                if wait > 0:
                    self._sleep(wait)
            try:
                return self._fetch(url, max_bytes)
            except ArxivError:
                raise
            except urllib.error.HTTPError as error:
                print(f"arxiv HTTP {error.code} for {url}", file=sys.stderr)
                if error.code == 404:
                    raise ArxivError("arXiv could not find that paper.") from None
                raise ArxivError("arXiv is not answering right now. Try again, or upload the PDF.") from None
            except Exception as error:
                print(f"arxiv error: {type(error).__name__}: {error}", file=sys.stderr)
                raise ArxivError("I could not reach arXiv right now. Try again, or upload the PDF.") from None
            finally:
                self._last = self._clock()

    def _search(self, search_query: str | None = None, id_list: str | None = None,
                limit: int = 3, newest_first: bool = False) -> list[Match]:
        params = {"max_results": str(limit)}
        if search_query:
            params.update({"search_query": search_query, "sortBy": "submittedDate" if newest_first else "relevance"})
            if newest_first:
                params["sortOrder"] = "descending"
        if id_list:
            params["id_list"] = id_list
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
        return parse_results(self._get(url, MAX_API_BYTES), limit)

    def find(self, text: str) -> list[Match]:
        query = parse_query(text)
        if query.kind == "id":
            return self._search(id_list=query.value)
        words = re.sub(r"[^\w\s\-]", " ", query.value).split()
        if not words:
            raise ArxivError("Type a paper title, an arXiv link or an arXiv ID first.")
        found = self._search(search_query='ti:"' + " ".join(words) + '"')
        if not found:  # title was approximate: look for the words anywhere
            found = self._search(search_query=" AND ".join(f"all:{w}" for w in words[:8]))
        return found

    def download(self, arxiv_id: str) -> bytes:
        if not is_arxiv_id(arxiv_id):
            raise ArxivError("That does not look like an arXiv ID.")
        data = self._get(f"https://arxiv.org/pdf/{arxiv_id}", MAX_UPLOAD_BYTES)
        if not data.lstrip()[:5] == b"%PDF-":
            raise ArxivError("arXiv did not return a PDF for that paper.")
        return data
