import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.auth.rate_limit import (
    InMemoryRateLimiter,
    RateLimitPolicy,
    TooManyAttempts,
    auth_rate_limit_key,
    check_auth_rate_limit,
    record_auth_failure,
    record_auth_success,
)


class RateLimitTest(unittest.TestCase):
    def test_limiter_blocks_after_configured_failures(self):
        limiter = InMemoryRateLimiter()
        policy = RateLimitPolicy(attempts=2, window_seconds=60, lockout_seconds=30)
        key = "test:127.0.0.1:user"

        limiter.check(key, policy)
        limiter.record_failure(key, policy)
        limiter.check(key, policy)
        limiter.record_failure(key, policy)

        with self.assertRaises(TooManyAttempts):
            limiter.check(key, policy)

    def test_success_clears_failures(self):
        limiter = InMemoryRateLimiter()
        policy = RateLimitPolicy(attempts=2, window_seconds=60, lockout_seconds=30)
        key = "test:127.0.0.1:user"

        limiter.record_failure(key, policy)
        limiter.record_success(key)
        limiter.check(key, policy)
        limiter.record_failure(key, policy)
        limiter.check(key, policy)

    def test_key_normalizes_username(self):
        request = SimpleNamespace(client=SimpleNamespace(host="192.0.2.10"))

        self.assertEqual(
            auth_rate_limit_key("web-login", " Haruto ", request),
            "web-login:192.0.2.10:haruto",
        )

    def test_route_helpers_raise_http_429(self):
        key = "helper:127.0.0.1:user"
        policy = RateLimitPolicy(attempts=1, window_seconds=60, lockout_seconds=30)

        record_auth_failure(key, policy)
        with self.assertRaises(HTTPException) as raised:
            check_auth_rate_limit(key, policy)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn("Retry-After", raised.exception.headers)
        record_auth_success(key)


if __name__ == "__main__":
    unittest.main()
