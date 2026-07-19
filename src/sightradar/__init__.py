"""SightRadar — official Python client for the face recognition API.

Quickstart
----------
    from sightradar import SightRadar

    sr = SightRadar(api_key="frs_...")          # or set SIGHTRADAR_API_KEY
    sr.create_collection("event-2026")
    sr.index("event-2026", url="https://example.com/group.jpg")
    result = sr.search("event-2026", url="https://example.com/selfie.jpg")
    for m in result.matches:
        print(m.photo_id, m.score)

The API is Rekognition-compatible in shape but exposed through a small, explicit
surface here. Every call raises :class:`SightRadarError` on a non-2xx response.
"""

from .client import SightRadar, verify_webhook_signature
from .errors import (
    SightRadarError,
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
)
from .models import (
    Collection,
    SearchResult,
    Match,
    IndexResult,
    CompareResult,
    DetectResult,
    Wallet,
    Batch,
    Webhook,
)

__version__ = "1.0.2"

__all__ = [
    "SightRadar",
    "verify_webhook_signature",
    "SightRadarError",
    "AuthenticationError",
    "InsufficientCreditsError",
    "NotFoundError",
    "RateLimitError",
    "Collection",
    "SearchResult",
    "Match",
    "IndexResult",
    "CompareResult",
    "DetectResult",
    "Wallet",
    "Batch",
    "Webhook",
    "__version__",
]
