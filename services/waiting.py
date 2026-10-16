"""Small FIFO waiting room. Tickets contain no PDF text or credentials.

Open sessions renew their tickets; abandoned waiters expire. A claim acquires the
existing generation limiter atomically before removing the first ticket.
"""
from collections import OrderedDict
import threading
import time
import uuid


class WaitingRoom:
    def __init__(self, capacity=8, ttl_seconds=180, clock=time.monotonic):
        self.capacity, self.ttl, self.clock = capacity, ttl_seconds, clock
        self._tickets = OrderedDict()
        self._lock = threading.Lock()

    def _expire(self):
        cutoff = self.clock() - self.ttl
        for ticket, touched in list(self._tickets.items()):
            if touched < cutoff:
                del self._tickets[ticket]

    def join(self):
        with self._lock:
            self._expire()
            if len(self._tickets) >= self.capacity:
                return None
            ticket = uuid.uuid4().hex
            self._tickets[ticket] = self.clock()
            return ticket

    def touch(self, ticket):
        """Return one-based waiting position, or None for an expired ticket."""
        with self._lock:
            self._expire()
            if ticket not in self._tickets:
                return None
            self._tickets[ticket] = self.clock()
            return list(self._tickets).index(ticket) + 1

    def claim(self, ticket, limiter):
        with self._lock:
            self._expire()
            if not self._tickets or next(iter(self._tickets)) != ticket:
                return False
            if not limiter.try_start():
                return False
            del self._tickets[ticket]
            return True

    def cancel(self, ticket):
        with self._lock:
            self._tickets.pop(ticket, None)
