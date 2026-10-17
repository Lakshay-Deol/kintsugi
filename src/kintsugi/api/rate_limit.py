"""Per-IP and global rate limiting for /answer endpoint.
Returns a clear "demo busy" message on limit exceeded.
"""
from __future__ import annotations

import time
import threading
import logging
from collections import defaultdict

from kintsugi.config import get_config

log = logging.getLogger(__name__)

_lock = threading.Lock()
_ip_buckets: dict[str, list[float]] = defaultdict(list)
_global_bucket: list[float] = []


def _clean(bucket: list[float], window: float, now: float) -> list[float]:
    return [t for t in bucket if now - t < window]


def check_rate_limit(client_ip: str) -> tuple[bool, str]:
    """
    Returns (allowed: bool, error_message: str).
    If allowed, returns (True, "").
    If rate-limited, returns (False, user-facing message).
    """
    cfg = get_config()
    window = cfg.rate_limit_window_seconds
    now = time.monotonic()

    with _lock:
        global _global_bucket

        _global_bucket = _clean(_global_bucket, window, now)
        _ip_buckets[client_ip] = _clean(_ip_buckets[client_ip], window, now)

        # Global check first
        if len(_global_bucket) >= cfg.rate_limit_global:
            log.warning("Global rate limit hit from IP %s", client_ip)
            return False, (
                "The Kintsugi demo is busy right now (global limit reached). "
                "Please try again in a minute. This is a free demo — limits exist to preserve "
                "the Gemma API quota for all users."
            )

        # Per-IP check
        if len(_ip_buckets[client_ip]) >= cfg.rate_limit_per_ip:
            log.warning("Per-IP rate limit hit for %s", client_ip)
            return False, (
                f"You've made too many requests recently. "
                f"Please wait {window} seconds and try again. "
                "(Limit: {cfg.rate_limit_per_ip} requests per {window}s per IP)"
            )

        # Record request
        _global_bucket.append(now)
        _ip_buckets[client_ip].append(now)
        return True, ""
