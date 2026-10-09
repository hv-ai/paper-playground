"""A small in-memory cache so the same paper with the same settings never costs a second model call.

Bounded on purpose: at most `max_entries` lessons (least recently used goes first) and each one
expires after `ttl_seconds`. It lives in memory only, is keyed by a hash of the exact file, and
stores the finished lesson, not the PDF or its text. Failures are never cached.
"""
from __future__ import annotations

import copy
import hashlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from services.lesson import LessonOptions, LessonResult, prompt_fingerprint


@dataclass
class CachedLesson:
    result: LessonResult
    held_out: list
    hidden_chars_removed: int
    total_pages: int = 0


def make_key(pdf_bytes: bytes, options: LessonOptions, model: str) -> str:
    """Same file + same settings + same model + same prompt version = same key."""
    o = options.normalised()
    parts = [hashlib.sha256(pdf_bytes).hexdigest(), o.length, o.level, o.tone, str(o.beyond), model, prompt_fingerprint()]
    return "|".join(parts)


class LessonCache:
    def __init__(self, max_entries: int = 20, ttl_seconds: float = 24 * 3600, clock=time.time):
        self.max_entries, self.ttl, self._clock = max_entries, ttl_seconds, clock
        self._items: OrderedDict[str, tuple[float, CachedLesson]] = OrderedDict()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def get(self, key: str) -> CachedLesson | None:
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            stored_at, value = entry
            if self._clock() - stored_at > self.ttl:
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return copy.deepcopy(value)  # callers can never change what is stored

    def put(self, key: str, value: CachedLesson) -> None:
        with self._lock:
            self._items[key] = (self._clock(), copy.deepcopy(value))
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)
