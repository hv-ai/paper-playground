"""Daily AI headlines from publisher RSS feeds; no model calls or keys."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import re
import threading
import urllib.request
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

SOURCES = [('OpenAI', 'https://openai.com/news/rss.xml', 'openai.com'),
           ('Hugging Face', 'https://huggingface.co/blog/feed.xml', 'huggingface.co')]
MAX_BYTES = 1_500_000
PACIFIC = ZoneInfo('America/Los_Angeles')


@dataclass(frozen=True)
class Headline:
    title: str
    url: str
    source: str
    published: datetime


@dataclass(frozen=True)
class NewsSnapshot:
    items: tuple[Headline, ...]
    checked: datetime
    partial: bool = False
    stale: bool = False


def parse_feed(data: bytes, source: str, host: str, now: datetime) -> list[Headline]:
    if len(data) > MAX_BYTES or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Unsupported feed')
    root = ET.fromstring(data)
    items = []
    for entry in root.findall('./channel/item'):
        title = re.sub(r'<[^>]+>', '', entry.findtext('title', '')).strip()[:200]
        url = entry.findtext('link', '').strip()
        parsed = urlsplit(url)
        if not title or parsed.scheme != 'https' or parsed.hostname not in {host, 'www.' + host} or parsed.username or parsed.password:
            continue
        try:
            date = parsedate_to_datetime(entry.findtext('pubDate', ''))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, OverflowError):
            continue
        if now - timedelta(days=14) <= date <= now:
            items.append(Headline(title, url, source, date))
    return items


def fetch_feed(spec, now: datetime) -> list[Headline]:
    source, url, host = spec
    request = urllib.request.Request(url, headers={'User-Agent': 'PaperPlayground/1.0 (public RSS reader)'})
    with urllib.request.urlopen(request, timeout=4) as response:
        return parse_feed(response.read(MAX_BYTES + 1), source, host, now)


class NewsFeed:
    def __init__(self, fetcher=fetch_feed, clock=lambda: datetime.now(timezone.utc)):
        self.fetcher, self.clock = fetcher, clock
        self._snapshot = None
        self._retry_after = None
        self._lock = threading.Lock()

    def latest(self) -> NewsSnapshot:
        with self._lock:
            now = self.clock()
            snapshot = self._snapshot
            if snapshot and not snapshot.stale and snapshot.checked.astimezone(PACIFIC).date() == now.astimezone(PACIFIC).date():
                if not snapshot.partial or (self._retry_after and now < self._retry_after):
                    return snapshot
            if snapshot and self._retry_after and now < self._retry_after:
                return snapshot
            items, failures = [], 0
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = [pool.submit(self.fetcher, spec, now) for spec in SOURCES]
                for future in results:
                    try:
                        items.extend(future.result())
                    except Exception:
                        failures += 1
            unique = {item.url: item for item in items}
            fresh = tuple(sorted(unique.values(), key=lambda x: x.published, reverse=True)[:3])
            if failures == len(SOURCES) and snapshot:
                # Preserve timestamp and label old results explicitly on an outage.
                self._snapshot = NewsSnapshot(tuple(i for i in snapshot.items if now - i.published <= timedelta(days=14)), snapshot.checked, True, True)
            else:
                self._snapshot = NewsSnapshot(fresh, now, failures > 0)
            self._retry_after = now + timedelta(minutes=15) if failures else None
            return self._snapshot
