"""Lightweight in-memory sliding-window rate limiting.

Deliberately dependency-free: a per-process {key: deque-of-timestamps} bucket
keyed by (route prefix, client IP). Suitable for single-process deployments
and development; swap for Redis-backed limiting before running multiple
processes behind a load balancer.

Returns a structured 429 JSON response with a Retry-After header — never a
stack trace or internal detail.
"""
import time
from collections import defaultdict, deque
from functools import wraps

from flask import jsonify, request

_buckets = defaultdict(deque)
_WINDOW_SECONDS = 3600


def rate_limit(limit_per_hour: int, key_prefix: str):
    """Decorator: allow up to `limit_per_hour` requests per IP per hour."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
            ip = ip.split(",")[0].strip()
            key = (key_prefix, ip)
            now = time.time()
            bucket = _buckets[key]
            while bucket and now - bucket[0] > _WINDOW_SECONDS:
                bucket.popleft()
            if len(bucket) >= limit_per_hour:
                wait = int(_WINDOW_SECONDS - (now - bucket[0])) if bucket else _WINDOW_SECONDS
                response = jsonify({
                    "error": "Too many attempts. Please wait a while and try again.",
                })
                response.status_code = 429
                response.headers["Retry-After"] = str(max(1, wait))
                return response
            bucket.append(now)
            return fn(*args, **kwargs)
        return wrapper

    return decorator
