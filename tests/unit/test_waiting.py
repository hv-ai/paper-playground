import threading

from services.waiting import WaitingRoom
from services.limits import UsageLimiter, SessionUsage


def test_fifo_and_generation_lock_are_preserved_for_five_visitors():
    room, limiter = WaitingRoom(), UsageLimiter()
    tickets = [room.join() for _ in range(5)]
    assert [room.touch(t) for t in tickets] == [1, 2, 3, 4, 5]
    for i, ticket in enumerate(tickets):
        if i < 4:
            assert not room.claim(tickets[i + 1], limiter)
        assert room.claim(ticket, limiter)
        if i < 4:
            assert not room.claim(tickets[i + 1], limiter)
            assert room.touch(tickets[i + 1]) == 1
        limiter.finish()


def test_cancel_expiry_capacity_and_no_allowance_for_waiting():
    now = [0]
    room = WaitingRoom(capacity=2, ttl_seconds=10, clock=lambda: now[0])
    first, second = room.join(), room.join()
    assert room.join() is None
    room.cancel(first)
    assert room.touch(second) == 1
    assert room.join()
    now[0] = 11
    assert room.touch(second) is None
    assert room.join()
    usage = SessionUsage()
    assert usage.papers == 0


def test_parallel_claims_cannot_start_multiple_generations():
    room, limiter = WaitingRoom(), UsageLimiter()
    tickets = [room.join() for _ in range(5)]
    results = []
    threads = [threading.Thread(target=lambda t=t: results.append(room.claim(t, limiter))) for t in tickets]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1
    limiter.finish()


def test_waiter_heartbeats_keep_its_place_without_reviving_expired_ticket():
    now = [0]
    room = WaitingRoom(ttl_seconds=10, clock=lambda: now[0])
    first, second = room.join(), room.join()
    now[0] = 8
    assert room.touch(second) == 2
    now[0] = 11
    assert room.touch(second) == 1
    assert room.touch(first) is None
