import time
from dataclasses import dataclass
from threading import Lock

from fastapi import HTTPException, Request, status

from app.config import settings


@dataclass(frozen=True)
class RateLimitPolicy:
    attempts: int
    window_seconds: int
    lockout_seconds: int


class TooManyAttempts(Exception):
    def __init__(self, retry_after: int):
        super().__init__("Too many authentication attempts")
        self.retry_after = retry_after


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, list[float]] = {}
        self._blocked_until: dict[str, float] = {}
        self._lock = Lock()

    def check(self, key: str, policy: RateLimitPolicy) -> None:
        if policy.attempts <= 0:
            return

        now = time.monotonic()
        with self._lock:
            blocked_until = self._blocked_until.get(key)
            if blocked_until and blocked_until > now:
                raise TooManyAttempts(max(1, int(blocked_until - now)))
            if blocked_until:
                self._blocked_until.pop(key, None)

            self._attempts[key] = self._prune(self._attempts.get(key, []), now, policy)

    def record_failure(self, key: str, policy: RateLimitPolicy) -> None:
        if policy.attempts <= 0:
            return

        now = time.monotonic()
        with self._lock:
            attempts = self._prune(self._attempts.get(key, []), now, policy)
            attempts.append(now)
            if len(attempts) >= policy.attempts:
                self._blocked_until[key] = now + policy.lockout_seconds
                self._attempts.pop(key, None)
            else:
                self._attempts[key] = attempts

    def record_success(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
            self._blocked_until.pop(key, None)

    @staticmethod
    def _prune(
        attempts: list[float],
        now: float,
        policy: RateLimitPolicy,
    ) -> list[float]:
        cutoff = now - policy.window_seconds
        return [attempt for attempt in attempts if attempt >= cutoff]


auth_rate_limiter = InMemoryRateLimiter()


def auth_rate_limit_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        attempts=settings.AUTH_RATE_LIMIT_ATTEMPTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
        lockout_seconds=settings.AUTH_RATE_LIMIT_LOCKOUT_SECONDS,
    )


def auth_rate_limit_key(scope: str, username: str, request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{scope}:{client_host}:{username.strip().lower()}"


def check_auth_rate_limit(key: str, policy: RateLimitPolicy | None = None) -> None:
    policy = policy or auth_rate_limit_policy()
    try:
        auth_rate_limiter.check(key, policy)
    except TooManyAttempts as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc


def record_auth_failure(key: str, policy: RateLimitPolicy | None = None) -> None:
    auth_rate_limiter.record_failure(key, policy or auth_rate_limit_policy())


def record_auth_success(key: str) -> None:
    auth_rate_limiter.record_success(key)
