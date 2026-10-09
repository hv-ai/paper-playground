"""Usage limits that protect the app's availability on a free tier.

What they do: one generation at a time; a per-visit allowance; daily caps on lessons, questions
and API requests; a minimum gap between API calls; and a cooldown that pauses generation after
repeated quota errors so visitors cannot keep hammering an exhausted quota.

What they do NOT do: stop a determined abuser. A visitor can start a new session to get a new
per-visit allowance, and the daily counters live in this process (they are also saved to a small
file when a path is given, which survives reruns but not a fresh deploy). The daily caps and the
cooldown are what protect the quota; the provider's own limit is the hard backstop.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from services.errors import QuotaExceeded

PACIFIC = ZoneInfo("America/Los_Angeles")


def _today():
    return datetime.now(PACIFIC).date()


@dataclass
class SessionUsage:
    papers: int = 0
    questions: int = 0


class UsageLimiter:
    def __init__(self, daily_lessons: int = 100, daily_questions: int = 300, daily_requests: int = 400,
                 session_papers: int = 2, session_questions: int = 8,
                 min_seconds_between_requests: float = 4.0,
                 quota_error_threshold: int = 3, quota_window_seconds: float = 600.0,
                 cooldown_seconds: float = 900.0,
                 today=_today, clock=time.time, sleep=time.sleep, state_path: str | None = None):
        self.daily_lessons, self.daily_questions, self.daily_requests = daily_lessons, daily_questions, daily_requests
        self.session_papers, self.session_questions = session_papers, session_questions
        self.min_gap = min_seconds_between_requests
        self.quota_error_threshold, self.quota_window = quota_error_threshold, quota_window_seconds
        self.cooldown_seconds = cooldown_seconds
        self._today, self._clock, self._sleep = today, clock, sleep
        self._state_path = state_path
        self._busy = threading.Lock()      # one generation at a time
        self._counts = threading.Lock()    # protects every counter below
        self._day = today()
        self._lessons = self._questions = self._requests = 0
        self._quota_errors: list[float] = []
        self._cooldown_until = 0.0
        self._last_request = 0.0
        self._load()

    # ---- persistence (best effort) ------------------------------------------------------
    def _load(self):
        if not self._state_path:
            return
        try:
            with open(self._state_path, encoding="utf-8") as handle:
                state = json.load(handle)
            if state.get("day") == self._day.isoformat():
                self._lessons = int(state.get("lessons", 0))
                self._questions = int(state.get("questions", 0))
                self._requests = int(state.get("requests", 0))
                self._cooldown_until = float(state.get("cooldown_until", 0.0))
        except (OSError, ValueError, TypeError):
            pass

    def _save(self):
        if not self._state_path:
            return
        try:
            tmp = self._state_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump({"day": self._day.isoformat(), "lessons": self._lessons, "questions": self._questions,
                           "requests": self._requests, "cooldown_until": self._cooldown_until}, handle)
            os.replace(tmp, self._state_path)
        except OSError:
            pass

    def _roll(self):
        current = self._today()
        if current != self._day:
            self._day, self._lessons, self._questions, self._requests = current, 0, 0, 0
            self._save()

    # ---- read-only views ----------------------------------------------------------------
    def lessons_left_today(self) -> int:
        with self._counts:
            self._roll()
            return max(0, self.daily_lessons - self._lessons)

    def cooldown_seconds_left(self) -> int:
        with self._counts:
            return max(0, int(self._cooldown_until - self._clock()))

    def _cooldown_message(self) -> str:
        minutes = max(1, -(-int(self._cooldown_until - self._clock()) // 60))
        return (f"Generation is paused for about {minutes} minute(s) because the free quota looks used up. "
                "The example lessons still work.")

    # ---- the generation slot ------------------------------------------------------------
    def try_start(self) -> bool:
        """Claim the single generation slot. Returns False if someone else is using it."""
        return self._busy.acquire(blocking=False)

    def finish(self):
        if self._busy.locked():
            self._busy.release()

    # ---- check and reserve in one atomic step (call after try_start) ---------------------
    def reserve_lesson(self, session: SessionUsage) -> tuple[bool, str]:
        with self._counts:
            self._roll()
            if self._clock() < self._cooldown_until:
                return False, self._cooldown_message()
            if session.papers >= self.session_papers:
                return False, f"You have used your {self.session_papers} papers for this visit."
            if self._lessons >= self.daily_lessons or self._requests >= self.daily_requests:
                return False, "Today's free capacity is used up. Please try again tomorrow, or open an example lesson."
            self._lessons += 1
            session.papers += 1
            self._save()
            return True, ""

    def refund_lesson(self, session: SessionUsage):
        """Give a reservation back when no model call was made (for example, the file was rejected)."""
        with self._counts:
            self._lessons = max(0, self._lessons - 1)
            session.papers = max(0, session.papers - 1)
            self._save()

    def reserve_question(self, session: SessionUsage) -> tuple[bool, str]:
        with self._counts:
            self._roll()
            if self._clock() < self._cooldown_until:
                return False, self._cooldown_message()
            if session.questions >= self.session_questions:
                return False, f"You have used your {self.session_questions} questions for this visit."
            if self._questions >= self.daily_questions or self._requests >= self.daily_requests:
                return False, "Today's question capacity is used up. Please try again tomorrow."
            self._questions += 1
            session.questions += 1
            self._save()
            return True, ""

    def refund_question(self, session: SessionUsage):
        with self._counts:
            self._questions = max(0, self._questions - 1)
            session.questions = max(0, session.questions - 1)
            self._save()

    # ---- hooks for the model client: every API attempt goes through here ------------------
    def begin_api_attempt(self):
        """Count one API attempt, or refuse it (QuotaExceeded) during a cooldown or when out of budget."""
        with self._counts:
            self._roll()
            now = self._clock()
            if now < self._cooldown_until:
                raise QuotaExceeded(self._cooldown_message())
            if self._requests >= self.daily_requests:
                raise QuotaExceeded("Today's free request budget is used up.")
            wait = self._last_request + self.min_gap - now
            self._requests += 1
            self._last_request = now + max(0.0, wait)
            self._save()
        if wait > 0:
            self._sleep(wait)  # stay under the per-minute limit; safe because only one generation runs at a time

    def note_quota_error(self):
        """Record a quota error. Repeated errors start a cooldown."""
        with self._counts:
            now = self._clock()
            self._quota_errors = [t for t in self._quota_errors if now - t < self.quota_window] + [now]
            if len(self._quota_errors) >= self.quota_error_threshold:
                self._cooldown_until = now + self.cooldown_seconds
                self._quota_errors = []
                self._save()

    def note_api_success(self):
        with self._counts:
            self._quota_errors = []
