"""Exception types raised by the SightRadar client."""

from __future__ import annotations

from typing import Optional


class SightRadarError(Exception):
    """Base error for all non-2xx API responses and transport failures.

    Attributes:
        message: Human-readable error message (from the API ``error`` field when present).
        status_code: HTTP status code, or ``None`` for transport-level failures.
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.status_code is not None:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(SightRadarError):
    """Raised on 401 — the API key is missing, malformed, or revoked."""


class InsufficientCreditsError(SightRadarError):
    """Raised on 402 — the wallet does not have enough credits for the operation."""


class NotFoundError(SightRadarError):
    """Raised on 404 — the collection, key, or resource does not exist."""


class RateLimitError(SightRadarError):
    """Raised on 429 — too many requests; back off and retry."""


def error_for_status(status_code: int, message: str) -> SightRadarError:
    """Map an HTTP status to the most specific error subclass."""
    if status_code == 401:
        return AuthenticationError(message, status_code)
    if status_code == 402:
        return InsufficientCreditsError(message, status_code)
    if status_code == 404:
        return NotFoundError(message, status_code)
    if status_code == 429:
        return RateLimitError(message, status_code)
    return SightRadarError(message, status_code)
