"""Tests for the score/similarity mapping, webhook signature helper, and retry.

These use a mocked ``urlopen`` so no network access is required.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import time
from contextlib import contextmanager
from unittest import mock

import pytest

from sightradar import SightRadar, verify_webhook_signature
from sightradar.errors import RateLimitError


class _FakeResponse:
    """Minimal stand-in for the urlopen context-manager response."""

    def __init__(self, status: int, payload: dict):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@contextmanager
def _mock_urlopen(response):
    with mock.patch(
        "sightradar.client.urlrequest.urlopen", return_value=response
    ) as m:
        yield m


def test_search_returns_numeric_score():
    """Engine sends {matches:[{photo_id, score}]}; .score must be numeric."""
    engine_payload = {
        "collection_id": "event-2026",
        "matches": [
            {"photo_id": "img-1", "score": 0.92},
            {"photo_id": "img-2", "score": 0.81},
        ],
    }
    sr = SightRadar(api_key="frs_test_key")
    with _mock_urlopen(_FakeResponse(200, engine_payload)):
        result = sr.search("event-2026", url="https://example.com/selfie.jpg")

    assert result.found
    first = result.matches[0]
    assert isinstance(first.score, float)
    assert first.score == pytest.approx(0.92)
    # Back-compat: similarity must mirror score, not be None.
    assert first.similarity == pytest.approx(0.92)
    assert first.photo_id == "img-1"


def test_verify_webhook_signature_valid():
    secret = "whsec_abc"
    ts = int(time.time())
    body = '{"event":"batch.completed"}'
    sig = hmac.new(
        secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    assert verify_webhook_signature(secret, ts, body, sig) is True


def test_verify_webhook_signature_rejects_bad_and_stale():
    secret = "whsec_abc"
    ts = int(time.time())
    body = '{"event":"batch.completed"}'
    good = hmac.new(
        secret.encode(), f"{ts}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    # Wrong signature.
    assert verify_webhook_signature(secret, ts, body, "deadbeef") is False
    # Stale timestamp beyond tolerance.
    old = ts - 10_000
    old_sig = hmac.new(
        secret.encode(), f"{old}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    assert verify_webhook_signature(secret, old, body, old_sig) is False


def test_retry_disabled_by_default_raises_on_429():
    from urllib import error as urlerror

    err = urlerror.HTTPError(
        "https://api.sightradar.com/v1/wallet", 429, "rate limited",
        hdrs=None, fp=io.BytesIO(b'{"error":"rate limited"}'),
    )
    sr = SightRadar(api_key="frs_test_key")  # max_retries=0
    with mock.patch(
        "sightradar.client.urlrequest.urlopen", side_effect=err
    ):
        with pytest.raises(RateLimitError):
            sr.wallet()


def test_retry_recovers_on_transient_503():
    from urllib import error as urlerror

    err503 = urlerror.HTTPError(
        "https://api.sightradar.com/v1/wallet", 503, "unavailable",
        hdrs=None, fp=io.BytesIO(b'{"error":"unavailable"}'),
    )
    ok = _FakeResponse(200, {"balance_credits": 500})
    seq = [err503, ok]

    def _side_effect(*a, **k):
        item = seq.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    sr = SightRadar(api_key="frs_test_key", max_retries=2)
    with mock.patch("sightradar.client.time.sleep"), mock.patch(
        "sightradar.client.urlrequest.urlopen", side_effect=_side_effect
    ):
        w = sr.wallet()
    assert w.balance_credits == 500


def test_submit_batch_validates_op():
    sr = SightRadar(api_key="frs_test_key")
    with pytest.raises(Exception):
        sr.submit_batch("c1", "search", [{"url": "x"}])


def test_submit_batch_posts_expected_payload():
    captured = {}

    class _Resp(_FakeResponse):
        pass

    def _side_effect(req, *a, **k):
        captured["method"] = req.get_method()
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return _Resp(200, {"batch_id": "b-1", "status": "queued", "op": "index"})

    sr = SightRadar(api_key="frs_test_key")
    with mock.patch(
        "sightradar.client.urlrequest.urlopen", side_effect=_side_effect
    ):
        batch = sr.submit_batch(
            "event-2026", "index", [{"url": "u1"}], webhook_endpoint_id="wh-1"
        )
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v1/batches")
    assert captured["body"]["op"] == "index"
    assert captured["body"]["webhook_endpoint_id"] == "wh-1"
    assert batch.batch_id == "b-1"
