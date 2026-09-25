"""Password hashing, signed session tokens and a small in-memory rate limiter (stdlib only)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import threading
import time
from collections import deque

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, digest = stored.split("$")
        if algo != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=32
        )
        return hmac.compare_digest(candidate, _unb64(digest))
    except (ValueError, TypeError):
        return False


SESSION_TTL_SECONDS = 30 * 24 * 3600


def sign_session(user_id: int, secret: str, ttl: int = SESSION_TTL_SECONDS) -> str:
    payload = f"{user_id}.{int(time.time()) + ttl}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    return f"{_b64(payload.encode())}.{_b64(sig)}"


def read_session(token: str, secret: str) -> int | None:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        payload = _unb64(payload_b64)
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(sig_b64)):
            return None
        user_id, expires = payload.decode().split(".")
        if int(expires) < time.time():
            return None
        return int(user_id)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


class RateLimiter:
    """Sliding-window limiter. In-memory, so it is per process (run a single worker)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: float = 60.0) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            if len(self._hits) > 50_000:  # keep memory bounded
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > window]:
                    self._hits.pop(k, None)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()
