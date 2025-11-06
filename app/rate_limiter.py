"""Rate limiter for controlling request rates across multiple threads."""

import time
import threading


class RateLimiter:
    """Thread-safe rate limiter for controlling request rate across multiple threads."""

    def __init__(self, requests_per_second: float):
        """
        Initialize the rate limiter.

        Args:
            requests_per_second: Maximum number of requests allowed per second.
                                Set to 0 or negative for no rate limiting.
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0
        self.last_request_time = 0
        self.lock = threading.Lock()

    def acquire(self):
        """
        Wait if necessary to respect rate limit.

        This method blocks until it's safe to make another request
        without exceeding the configured rate limit.
        """
        if self.requests_per_second <= 0:
            return

        with self.lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            self.last_request_time = time.time()
