from collections import defaultdict, deque
from threading import Lock
from time import time


class SlidingWindowLimiter:
    def __init__(self):
        self._events: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time()
        with self._lock:
            bucket = self._events[key]
            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return False, retry_after
            bucket.append(now)
            return True, 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)


login_limiter = SlidingWindowLimiter()
register_limiter = SlidingWindowLimiter()
proof_limiter = SlidingWindowLimiter()
member_limiter = SlidingWindowLimiter()
