import datetime
import threading

import pytest

from services.errors import QuotaExceeded
from services.limits import SessionUsage, UsageLimiter


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def make(clock=None, **kw):
    clock = clock or Clock()
    slept = []
    limiter = UsageLimiter(clock=clock, sleep=slept.append, **kw)
    return limiter, clock, slept


def test_session_paper_cap():
    limiter, _, _ = make()
    session = SessionUsage()
    for _ in range(limiter.session_papers):
        assert limiter.reserve_lesson(session)[0]
    ok, message = limiter.reserve_lesson(session)
    assert not ok and "papers" in message


def test_session_question_cap():
    limiter, _, _ = make()
    session = SessionUsage()
    for _ in range(limiter.session_questions):
        assert limiter.reserve_question(session)[0]
    assert not limiter.reserve_question(session)[0]


def test_daily_cap_blocks_then_resets_next_day():
    day = {"d": datetime.date(2026, 10, 9)}
    limiter = UsageLimiter(daily_lessons=2, today=lambda: day["d"], session_papers=99)
    for _ in range(2):
        assert limiter.reserve_lesson(SessionUsage())[0]
    assert limiter.lessons_left_today() == 0 and not limiter.reserve_lesson(SessionUsage())[0]
    day["d"] = datetime.date(2026, 10, 10)
    assert limiter.lessons_left_today() == 2


def test_reservation_is_atomic_under_concurrent_requests():
    limiter, _, _ = make(daily_lessons=5, session_papers=99)
    results = []

    def worker():
        results.append(limiter.reserve_lesson(SessionUsage())[0])

    threads = [threading.Thread(target=worker) for _ in range(40)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count(True) == 5  # never more than the cap, even when 40 arrive at once


def test_refund_gives_the_reservation_back():
    limiter, _, _ = make(daily_lessons=1)
    session = SessionUsage()
    assert limiter.reserve_lesson(session)[0]
    assert not limiter.reserve_lesson(SessionUsage())[0]
    limiter.refund_lesson(session)
    assert session.papers == 0 and limiter.reserve_lesson(SessionUsage())[0]


def test_only_one_generation_at_a_time():
    limiter, _, _ = make()
    assert limiter.try_start() and not limiter.try_start()
    limiter.finish()
    assert limiter.try_start()


def test_every_api_attempt_is_counted_against_the_request_budget():
    limiter, _, _ = make(daily_requests=3, min_seconds_between_requests=0)
    for _ in range(3):
        limiter.begin_api_attempt()
    with pytest.raises(QuotaExceeded):
        limiter.begin_api_attempt()
    assert not limiter.reserve_lesson(SessionUsage())[0]  # no new lesson once the request budget is gone


def test_repeated_quota_errors_start_a_cooldown_that_blocks_everyone():
    limiter, clock, _ = make(quota_error_threshold=3, cooldown_seconds=900, min_seconds_between_requests=0)
    for _ in range(3):
        limiter.note_quota_error()
        clock.t += 10
    assert limiter.cooldown_seconds_left() > 800
    ok, message = limiter.reserve_lesson(SessionUsage())
    assert not ok and "paused" in message and "example" in message.lower()
    with pytest.raises(QuotaExceeded):
        limiter.begin_api_attempt()
    clock.t += 901
    assert limiter.cooldown_seconds_left() == 0 and limiter.reserve_lesson(SessionUsage())[0]


def test_a_success_clears_the_quota_error_streak():
    limiter, _, _ = make(quota_error_threshold=3)
    limiter.note_quota_error(); limiter.note_quota_error()
    limiter.note_api_success()
    limiter.note_quota_error()
    assert limiter.cooldown_seconds_left() == 0


def test_old_quota_errors_age_out_of_the_window():
    limiter, clock, _ = make(quota_error_threshold=3, quota_window_seconds=600)
    limiter.note_quota_error(); limiter.note_quota_error()
    clock.t += 700
    limiter.note_quota_error()
    assert limiter.cooldown_seconds_left() == 0


def test_requests_are_spaced_out():
    limiter, _, slept = make(min_seconds_between_requests=4.0)
    limiter.begin_api_attempt()
    limiter.begin_api_attempt()
    assert slept and 3.9 <= slept[-1] <= 4.0


def test_daily_counts_survive_a_restart_when_a_state_file_is_given(tmp_path):
    path = str(tmp_path / "state.json")
    first = UsageLimiter(state_path=path, daily_lessons=3, session_papers=99)
    first.reserve_lesson(SessionUsage()); first.reserve_lesson(SessionUsage())
    second = UsageLimiter(state_path=path, daily_lessons=3, session_papers=99)
    assert second.lessons_left_today() == 1


def test_a_corrupt_state_file_is_ignored(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not json")
    assert UsageLimiter(state_path=str(path)).lessons_left_today() == 100
