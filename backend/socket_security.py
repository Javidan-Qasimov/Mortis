"""Small, process-local abuse controls for Socket.IO events."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from config import SOCKET_MESSAGE_LIMIT, SOCKET_MESSAGE_WINDOW_SECONDS


class SlidingWindowRateLimiter:
    """Limit each client to a number of events inside a rolling window."""

    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, client_key):
        now = monotonic()
        with self._lock:
            events = self._events[client_key]
            while events and events[0] <= now - self.window_seconds:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


message_rate_limiter = SlidingWindowRateLimiter(
    SOCKET_MESSAGE_LIMIT, SOCKET_MESSAGE_WINDOW_SECONDS
)
