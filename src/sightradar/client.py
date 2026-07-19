"""The synchronous SightRadar API client.

Zero hard dependencies — built on the Python standard library (``urllib``) so it
installs clean anywhere. File uploads use multipart/form-data; URL/GCS-key inputs
use JSON.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import mimetypes
import os
import random
import time
import uuid
from typing import Any, BinaryIO, Dict, List, Optional, Union
from urllib import error as urlerror
from urllib import request as urlrequest

from .errors import SightRadarError, error_for_status
from .models import (
    Batch,
    Collection,
    CompareResult,
    DetectResult,
    IndexResult,
    SearchResult,
    Wallet,
    Webhook,
)

__version__ = "1.0.2"

# HTTP statuses that are safe to retry when retries are enabled.
_RETRYABLE_STATUSES = frozenset({429, 502, 503})

DEFAULT_BASE_URL = "https://api.sightradar.com"

# A path-or-file the SDK can read bytes from for an upload.
FileLike = Union[str, bytes, BinaryIO, io.IOBase]


class SightRadar:
    """Client for the SightRadar face recognition API.

    Args:
        api_key: Your ``frs_<prefix>_<secret>`` key. Falls back to the
            ``SIGHTRADAR_API_KEY`` environment variable.
        base_url: Override the API base (defaults to the production gateway).
        timeout: Per-request timeout in seconds.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 0,
    ):
        key = api_key or os.environ.get("SIGHTRADAR_API_KEY")
        if not key:
            raise SightRadarError(
                "No API key. Pass api_key=... or set SIGHTRADAR_API_KEY."
            )
        self.api_key = key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Opt-in retries: when > 0, retry 429/502/503 with exponential backoff
        # + jitter, honoring Retry-After. Off (0) by default.
        self.max_retries = max(0, int(max_retries))

    # -- transport ----------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": f"sightradar-python/{__version__}",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        raw_body: Optional[bytes] = None,
        content_type: Optional[str] = None,
        query: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            from urllib.parse import urlencode

            params = {k: v for k, v in query.items() if v is not None}
            if params:
                url = f"{url}?{urlencode(params)}"

        headers = self._headers()
        data: Optional[bytes] = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif raw_body is not None:
            data = raw_body
            if content_type:
                headers["Content-Type"] = content_type

        attempt = 0
        while True:
            req = urlrequest.Request(
                url, data=data, method=method, headers=headers
            )
            try:
                with urlrequest.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read()
                    return self._parse(resp.status, body)
            except urlerror.HTTPError as e:
                # Retry only the designated transient statuses, and only when
                # retries are enabled and attempts remain.
                if (
                    e.code in _RETRYABLE_STATUSES
                    and attempt < self.max_retries
                ):
                    retry_after = _parse_retry_after(
                        e.headers.get("Retry-After") if e.headers else None
                    )
                    time.sleep(_backoff_delay(attempt, retry_after))
                    attempt += 1
                    continue
                body = e.read()
                self._raise(e.code, body)
            except urlerror.URLError as e:  # network / DNS / TLS
                raise SightRadarError(f"request failed: {e.reason}") from e

    @staticmethod
    def _parse(status: int, body: bytes) -> Any:
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise SightRadarError(
                f"non-JSON response (status {status})", status
            )

    @staticmethod
    def _raise(status: int, body: bytes) -> None:
        message = f"request failed ({status})"
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict) and parsed.get("error"):
                message = str(parsed["error"])
        except (json.JSONDecodeError, ValueError):
            if body:
                message = body.decode("utf-8", "replace")[:300]
        raise error_for_status(status, message)

    # -- multipart ----------------------------------------------------------

    def _multipart(
        self, file: FileLike, fields: Optional[Dict[str, Any]] = None
    ) -> tuple[bytes, str]:
        """Build a multipart/form-data body from a file + optional fields."""
        filename, content = _read_file(file)
        boundary = f"----sightradar{uuid.uuid4().hex}"
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        buf = io.BytesIO()

        def w(s: str) -> None:
            buf.write(s.encode("utf-8"))

        for k, v in (fields or {}).items():
            if v is None:
                continue
            w(f"--{boundary}\r\n")
            w(f'Content-Disposition: form-data; name="{k}"\r\n\r\n')
            w(f"{v}\r\n")

        w(f"--{boundary}\r\n")
        w(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n')
        w(f"Content-Type: {ctype}\r\n\r\n")
        buf.write(content)
        w(f"\r\n--{boundary}--\r\n")
        return buf.getvalue(), f"multipart/form-data; boundary={boundary}"

    # -- collections --------------------------------------------------------

    def create_collection(self, collection_id: str) -> Collection:
        """Create a collection. Idempotent-ish: a duplicate raises (409)."""
        d = self._request(
            "POST", "/v1/collections", json_body={"collection_id": collection_id}
        )
        return Collection.from_dict(d)

    def list_collections(
        self, *, q: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Collection]:
        """List your collections (server-side searchable via ``q``)."""
        d = self._request(
            "GET",
            "/v1/collections",
            query={"q": q, "limit": limit, "offset": offset},
        )
        items = d.get("collections", d) if isinstance(d, dict) else d
        return [Collection.from_dict(c) for c in (items or [])]

    def describe_collection(self, collection_id: str) -> Collection:
        d = self._request("GET", f"/v1/collections/{collection_id}")
        return Collection.from_dict(d)

    def delete_collection(self, collection_id: str) -> Dict[str, Any]:
        """Delete a collection and CASCADE every stored face/selfie. Irreversible."""
        return self._request("DELETE", f"/v1/collections/{collection_id}")

    # -- index / search -----------------------------------------------------

    def index(
        self,
        collection_id: str,
        *,
        url: Optional[str] = None,
        gcs_key: Optional[str] = None,
        photo_id: Optional[str] = None,
        file: Optional[FileLike] = None,
    ) -> IndexResult:
        """Detect, embed, and store every face in a photo.

        Provide exactly one image source: ``url``, ``gcs_key``, or ``file``.
        """
        path = f"/v1/collections/{collection_id}/index"
        if file is not None:
            body, ctype = self._multipart(file, {"photoId": photo_id})
            d = self._request("POST", path, raw_body=body, content_type=ctype)
        else:
            d = self._request(
                "POST", path, json_body=_image_body(url, gcs_key, photo_id)
            )
        return IndexResult.from_dict(d)

    def search(
        self,
        collection_id: str,
        *,
        url: Optional[str] = None,
        gcs_key: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        file: Optional[FileLike] = None,
        threshold: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> SearchResult:
        """Find every stored photo a person appears in, from one selfie.

        Provide one of ``url``, ``gcs_key``, ``embedding``, or ``file``.
        """
        path = f"/v1/collections/{collection_id}/search"
        if file is not None:
            body, ctype = self._multipart(
                file, {"threshold": threshold, "limit": limit}
            )
            d = self._request("POST", path, raw_body=body, content_type=ctype)
        else:
            payload: Dict[str, Any] = {}
            if embedding is not None:
                payload["embedding"] = embedding
            elif url is not None:
                payload["url"] = url
            elif gcs_key is not None:
                payload["gcsKey"] = gcs_key
            else:
                raise SightRadarError(
                    "search needs one of: url, gcs_key, embedding, or file"
                )
            if threshold is not None:
                payload["threshold"] = threshold
            if limit is not None:
                payload["limit"] = limit
            d = self._request("POST", path, json_body=payload)
        return SearchResult.from_dict(d)

    def search_by_id(
        self,
        collection_id: str,
        point_id: str,
        *,
        threshold: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> SearchResult:
        """Search using a previously-stored selfie point id."""
        payload: Dict[str, Any] = {"id": point_id}
        if threshold is not None:
            payload["threshold"] = threshold
        if limit is not None:
            payload["limit"] = limit
        d = self._request(
            "POST", f"/v1/collections/{collection_id}/search-by-id", json_body=payload
        )
        return SearchResult.from_dict(d)

    def register_selfie(
        self,
        collection_id: str,
        *,
        url: Optional[str] = None,
        gcs_key: Optional[str] = None,
        file: Optional[FileLike] = None,
        photo_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a selfie point you can later search by id."""
        path = f"/v1/collections/{collection_id}/selfies"
        if file is not None:
            body, ctype = self._multipart(file, {"photoId": photo_id})
            return self._request("POST", path, raw_body=body, content_type=ctype)
        return self._request("POST", path, json_body=_image_body(url, gcs_key, photo_id))

    # -- stateless ops ------------------------------------------------------

    def detect(
        self,
        *,
        url: Optional[str] = None,
        gcs_key: Optional[str] = None,
        file: Optional[FileLike] = None,
    ) -> DetectResult:
        """Locate and quality-gate faces in an image. Nothing is stored."""
        if file is not None:
            body, ctype = self._multipart(file)
            d = self._request("POST", "/v1/detect", raw_body=body, content_type=ctype)
        else:
            d = self._request("POST", "/v1/detect", json_body=_image_body(url, gcs_key))
        return DetectResult.from_dict(d)

    def compare(
        self,
        *,
        source_url: Optional[str] = None,
        target_url: Optional[str] = None,
        source_gcs_key: Optional[str] = None,
        target_gcs_key: Optional[str] = None,
        source_embedding: Optional[List[float]] = None,
        target_embedding: Optional[List[float]] = None,
    ) -> CompareResult:
        """1:1 similarity / verification between two faces. Nothing is stored."""
        payload: Dict[str, Any] = {}
        if source_url:
            payload["sourceUrl"] = source_url
        if target_url:
            payload["targetUrl"] = target_url
        if source_gcs_key:
            payload["sourceGcsKey"] = source_gcs_key
        if target_gcs_key:
            payload["targetGcsKey"] = target_gcs_key
        if source_embedding is not None:
            payload["source_embedding"] = source_embedding
        if target_embedding is not None:
            payload["target_embedding"] = target_embedding
        d = self._request("POST", "/v1/compare", json_body=payload)
        return CompareResult.from_dict(d)

    # -- account ------------------------------------------------------------

    def wallet(self) -> Wallet:
        """Get the current credit balance."""
        return Wallet.from_dict(self._request("GET", "/v1/wallet"))

    def usage(self, days: int = 30) -> Dict[str, Any]:
        """Usage report aggregated from the ledger."""
        return self._request("GET", "/v1/usage", query={"days": days})

    # -- batches ------------------------------------------------------------

    def submit_batch(
        self,
        collection_id: str,
        op: str,
        photos: List[Dict[str, Any]],
        *,
        webhook_endpoint_id: Optional[str] = None,
    ) -> Batch:
        """Submit an async batch job over many photos.

        Args:
            collection_id: Target collection.
            op: Batch operation — ``"index"`` or ``"match"``.
            photos: List of photo descriptors (e.g. ``{"url": ..., "photoId": ...}``).
            webhook_endpoint_id: Optional webhook to notify on completion.
        """
        if op not in ("index", "match"):
            raise SightRadarError("batch op must be 'index' or 'match'")
        payload: Dict[str, Any] = {
            "collection_id": collection_id,
            "op": op,
            "photos": photos,
        }
        if webhook_endpoint_id is not None:
            payload["webhook_endpoint_id"] = webhook_endpoint_id
        d = self._request("POST", "/v1/batches", json_body=payload)
        return Batch.from_dict(d)

    def get_batch(self, batch_id: str) -> Batch:
        """Get the status of a batch job."""
        d = self._request("GET", f"/v1/batches/{batch_id}")
        return Batch.from_dict(d)

    def list_batches(self, *, limit: Optional[int] = None) -> List[Batch]:
        """List batch jobs (most recent first)."""
        d = self._request("GET", "/v1/batches", query={"limit": limit})
        items = d.get("batches", d) if isinstance(d, dict) else d
        return [Batch.from_dict(b) for b in (items or [])]

    # -- webhooks -----------------------------------------------------------

    def register_webhook(
        self, url: str, *, secret: Optional[str] = None
    ) -> Webhook:
        """Register a webhook endpoint to receive event callbacks."""
        payload: Dict[str, Any] = {"url": url}
        if secret is not None:
            payload["secret"] = secret
        d = self._request("POST", "/v1/webhooks", json_body=payload)
        return Webhook.from_dict(d)

    def list_webhooks(self) -> List[Webhook]:
        """List registered webhook endpoints."""
        d = self._request("GET", "/v1/webhooks")
        items = d.get("webhooks", d) if isinstance(d, dict) else d
        return [Webhook.from_dict(w) for w in (items or [])]

    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Delete a webhook endpoint."""
        return self._request("DELETE", f"/v1/webhooks/{webhook_id}")


# -- webhook signature verification -----------------------------------------


def verify_webhook_signature(
    secret: str,
    timestamp: Union[str, int],
    body: Union[str, bytes],
    signature: str,
    tolerance_sec: int = 300,
) -> bool:
    """Verify a SightRadar webhook signature.

    The gateway signs each delivery with
    ``X-SightRadar-Signature = hex(HMAC-SHA256(secret, f"{timestamp}.{body}"))``
    and sends the ``timestamp`` in a companion header. This recomputes the HMAC
    in constant time and rejects deliveries whose timestamp is older than
    ``tolerance_sec`` (replay protection).

    Args:
        secret: The endpoint's signing secret.
        timestamp: The delivery timestamp (unix seconds) from the header.
        body: The exact raw request body (str or bytes).
        signature: The received hex signature.
        tolerance_sec: Max allowed clock skew / age, in seconds.

    Returns:
        ``True`` when the signature is valid and fresh, else ``False``.
    """
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False

    # Reject stale timestamps beyond tolerance (guards against replay).
    if tolerance_sec >= 0 and abs(time.time() - ts) > tolerance_sec:
        return False

    body_bytes = body.encode("utf-8") if isinstance(body, str) else bytes(body)
    signed = str(ts).encode("utf-8") + b"." + body_bytes
    expected = hmac.new(
        secret.encode("utf-8"), signed, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


# -- helpers ----------------------------------------------------------------


def _parse_retry_after(value: Optional[str]) -> Optional[float]:
    """Parse a ``Retry-After`` header (seconds form) into a float, if present."""
    if not value:
        return None
    try:
        secs = float(value.strip())
        return secs if secs >= 0 else None
    except (TypeError, ValueError):
        # HTTP-date form is not honored here; fall back to computed backoff.
        return None


def _backoff_delay(attempt: int, retry_after: Optional[float]) -> float:
    """Exponential backoff with jitter, capped; honors ``Retry-After``."""
    if retry_after is not None:
        return min(retry_after, 60.0)
    base = min(2.0 ** attempt, 30.0)
    return base + random.uniform(0, base * 0.25)


def _image_body(
    url: Optional[str], gcs_key: Optional[str], photo_id: Optional[str] = None
) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if url:
        body["url"] = url
    elif gcs_key:
        body["gcsKey"] = gcs_key
    else:
        raise SightRadarError("provide one of: url, gcs_key, or file")
    if photo_id:
        body["photoId"] = photo_id
    return body


def _read_file(file: FileLike) -> tuple[str, bytes]:
    """Resolve a path / bytes / file-object into (filename, content_bytes)."""
    if isinstance(file, str):
        with open(file, "rb") as fh:
            return os.path.basename(file), fh.read()
    if isinstance(file, (bytes, bytearray)):
        return "upload.jpg", bytes(file)
    # file-like object
    name = getattr(file, "name", "upload.jpg")
    content = file.read()
    if isinstance(content, str):
        content = content.encode("utf-8")
    return os.path.basename(str(name)), content
