"""Thread-safe rate limiter for API calls."""

import threading
import time
from collections import deque
from typing import Optional


class RateLimiter:
    """Thread-safe sliding window rate limiter.

    Uses a sliding window approach to limit the number of requests
    within a given time period. Thread-safe for use with ThreadPoolExecutor.
    """

    def __init__(self, max_requests: int, time_window: float = 60.0):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the time window.
            time_window: Time window in seconds (default: 60.0 for per-minute limits).
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self._timestamps: deque = deque()
        self._lock = threading.Lock()

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request.

        Blocks until a request slot is available or timeout is reached.

        Args:
            timeout: Maximum time to wait in seconds. None means wait forever.

        Returns:
            True if permission was granted, False if timeout occurred.
        """
        start_time = time.time()

        while True:
            with self._lock:
                now = time.time()

                # Remove timestamps outside the sliding window
                while self._timestamps and self._timestamps[0] <= now - self.time_window:
                    self._timestamps.popleft()

                # Check if we can make a request
                if len(self._timestamps) < self.max_requests:
                    self._timestamps.append(now)
                    return True

                # Calculate wait time until oldest request expires
                wait_time = self._timestamps[0] + self.time_window - now

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False
                # Don't wait longer than remaining timeout
                wait_time = min(wait_time, timeout - elapsed)

            # Wait before retrying
            time.sleep(min(wait_time + 0.01, 1.0))  # Add small buffer, cap at 1 second

    def try_acquire(self) -> bool:
        """Try to acquire permission without blocking.

        Returns:
            True if permission was granted, False otherwise.
        """
        with self._lock:
            now = time.time()

            # Remove timestamps outside the sliding window
            while self._timestamps and self._timestamps[0] <= now - self.time_window:
                self._timestamps.popleft()

            # Check if we can make a request
            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(now)
                return True

            return False

    @property
    def current_count(self) -> int:
        """Get the current number of requests in the window."""
        with self._lock:
            now = time.time()
            # Clean up old timestamps
            while self._timestamps and self._timestamps[0] <= now - self.time_window:
                self._timestamps.popleft()
            return len(self._timestamps)

    @property
    def available_slots(self) -> int:
        """Get the number of available request slots."""
        return max(0, self.max_requests - self.current_count)


# Pre-configured rate limiters for common APIs
def create_openai_limiter() -> RateLimiter:
    """Create rate limiter for OpenAI API (3500 RPM)."""
    return RateLimiter(max_requests=3500, time_window=60.0)


def create_bls_limiter() -> RateLimiter:
    """Create rate limiter for BLS API (120 calls/min with key, 25 without)."""
    return RateLimiter(max_requests=100, time_window=60.0)  # Conservative limit


def create_bea_limiter() -> RateLimiter:
    """Create rate limiter for BEA API (100 calls/min)."""
    return RateLimiter(max_requests=80, time_window=60.0)  # Conservative limit
