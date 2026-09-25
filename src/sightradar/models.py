"""Typed response models.

These are lightweight dataclasses built from the JSON the API returns. Each has
a ``from_dict`` constructor that is tolerant of unknown/extra fields (forward
compatible) and exposes the raw payload via ``.raw`` for anything not modelled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Collection:
    collection_id: str
    status: str
    photo_count: int = 0
    face_count: int = 0
    selfie_count: int = 0
    created_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Collection":
        return cls(
            collection_id=d.get("collection_id", ""),
            status=d.get("status", ""),
            photo_count=d.get("photo_count", 0) or 0,
            face_count=d.get("face_count", 0) or 0,
            selfie_count=d.get("selfie_count", 0) or 0,
            created_at=d.get("created_at"),
            raw=d,
        )


@dataclass
class Match:
    photo_id: Optional[str] = None
    score: Optional[float] = None
    similarity: Optional[float] = None
    point_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Match":
        # The engine returns cosine similarity as ``score``; older/other shapes
        # may send ``similarity``. Populate both so ``.score`` is primary and
        # ``.similarity`` stays valid for back-compat.
        score = d.get("score", d.get("similarity"))
        return cls(
            photo_id=d.get("photo_id") or d.get("photoId"),
            score=score,
            similarity=score,
            point_id=d.get("point_id") or d.get("id"),
            raw=d,
        )


@dataclass
class SearchResult:
    collection_id: str = ""
    matches: List[Match] = field(default_factory=list)
    photo_ids: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    model_version: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def found(self) -> bool:
        """True when at least one match was returned."""
        return len(self.matches) > 0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SearchResult":
        return cls(
            collection_id=d.get("collection_id", ""),
            matches=[Match.from_dict(m) for m in d.get("matches", []) or []],
            photo_ids=list(d.get("photo_ids", []) or []),
            reason=d.get("reason"),
            model_version=d.get("model_version"),
            raw=d,
        )


@dataclass
class IndexResult:
    collection_id: str = ""
    photo_id: Optional[str] = None
    indexed: int = 0
    detected_face_count: int = 0
    rejected_face_count: int = 0
    faces: List[Dict[str, Any]] = field(default_factory=list)
    model_version: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IndexResult":
        return cls(
            collection_id=d.get("collection_id", ""),
            photo_id=d.get("photo_id") or d.get("photoId"),
            indexed=d.get("indexed", 0) or 0,
            detected_face_count=d.get("detected_face_count", 0) or 0,
            rejected_face_count=d.get("rejected_face_count", 0) or 0,
            faces=list(d.get("faces", []) or []),
            model_version=d.get("model_version"),
            raw=d,
        )


@dataclass
class CompareResult:
    face_found: bool = False
    similarity: Optional[float] = None
    match: bool = False
    threshold: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CompareResult":
        return cls(
            face_found=bool(d.get("face_found", False)),
            similarity=d.get("similarity"),
            match=bool(d.get("match", False)),
            threshold=d.get("threshold"),
            raw=d,
        )


@dataclass
class DetectResult:
    detected_face_count: int = 0
    gated_face_count: int = 0
    faces: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DetectResult":
        return cls(
            detected_face_count=d.get("detected_face_count", 0) or 0,
            gated_face_count=d.get("gated_face_count", 0) or 0,
            faces=list(d.get("faces", []) or []),
            raw=d,
        )


@dataclass
class Wallet:
    balance_credits: int = 0
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Wallet":
        return cls(balance_credits=d.get("balance_credits", 0) or 0, raw=d)


@dataclass
class Batch:
    """A batch job as returned by submit / get / list.

    ``total_photos``, ``succeeded``, ``failed``, ``pending`` and ``claimed`` are
    the gateway's per-status counts. ``submit_batch`` only returns
    ``batch_id``, ``total_photos``, ``status`` and ``message``; poll
    :meth:`~sightradar.SightRadar.get_batch` for the rest.
    """

    batch_id: Optional[str] = None
    collection_id: str = ""
    op: Optional[str] = None
    status: Optional[str] = None
    total_photos: int = 0
    succeeded: int = 0
    failed: int = 0
    pending: int = 0
    claimed: int = 0
    message: Optional[str] = None
    created_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def done(self) -> bool:
        """True once every photo has a terminal outcome."""
        return self.total_photos > 0 and self.succeeded + self.failed >= self.total_photos

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Batch":
        return cls(
            batch_id=d.get("batch_id") or d.get("id"),
            collection_id=d.get("collection_id", ""),
            op=d.get("op"),
            status=d.get("status"),
            total_photos=d.get("total_photos", 0) or 0,
            succeeded=d.get("succeeded", 0) or 0,
            failed=d.get("failed", 0) or 0,
            pending=d.get("pending", 0) or 0,
            claimed=d.get("claimed", 0) or 0,
            message=d.get("message"),
            created_at=d.get("created_at"),
            raw=d,
        )


@dataclass
class Webhook:
    """A registered webhook endpoint. ``secret`` is present ONLY in the
    register response when the server generated it — store it then."""

    webhook_endpoint_id: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None
    secret: Optional[str] = None
    created_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def webhook_id(self) -> Optional[str]:
        """Back-compat alias for ``webhook_endpoint_id``."""
        return self.webhook_endpoint_id

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Webhook":
        return cls(
            webhook_endpoint_id=d.get("webhook_endpoint_id") or d.get("id"),
            url=d.get("url"),
            status=d.get("status"),
            secret=d.get("secret"),
            created_at=d.get("created_at"),
            raw=d,
        )


@dataclass
class SelfieResult:
    """Result of registering a selfie. ``point_id`` is the id you pass to
    ``search_by_id``. On an idempotent replay the volatile fields
    (embedding, det_score, quality_passed, model_version) are absent."""

    face_found: bool = False
    reason: Optional[str] = None
    collection_id: str = ""
    user_id: Optional[str] = None
    selfie_id: Optional[str] = None
    point_id: Optional[str] = None
    embedding: Optional[List[float]] = None
    det_score: Optional[float] = None
    quality_passed: Optional[bool] = None
    model_version: Optional[str] = None
    replayed: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SelfieResult":
        return cls(
            face_found=bool(d.get("face_found", False)),
            reason=d.get("reason"),
            collection_id=d.get("collection_id", ""),
            user_id=d.get("user_id"),
            selfie_id=d.get("selfie_id"),
            point_id=d.get("point_id"),
            embedding=d.get("embedding"),
            det_score=d.get("det_score"),
            quality_passed=d.get("quality_passed"),
            model_version=d.get("model_version"),
            replayed=bool(d.get("replayed", False)),
            raw=d,
        )


@dataclass
class DeletionReceipt:
    """202 body from ``delete_collection``. ``restorable`` is True for a soft
    delete; ``purge_after`` is when erasure begins."""

    status: str = ""
    mode: Optional[str] = None
    workflow_id: Optional[str] = None
    restorable: bool = False
    purge_after: Optional[str] = None
    message: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DeletionReceipt":
        return cls(
            status=d.get("status", ""),
            mode=d.get("mode"),
            workflow_id=d.get("workflow_id"),
            restorable=bool(d.get("restorable", False)),
            purge_after=d.get("purge_after"),
            message=d.get("message"),
            raw=d,
        )


@dataclass
class DeletionStatus:
    """Authoritative lifecycle of a collection deletion. The vectors are gone
    only when ``phase == "completed"`` and ``verified_zero`` is True."""

    collection_id: str = ""
    phase: str = ""
    collection_status: str = ""
    verified_zero: bool = False
    attempts: int = 0
    deletion_class: Optional[str] = None
    workflow_id: Optional[str] = None
    workflow_status: Optional[str] = None
    purge_after: Optional[str] = None
    requested_at: Optional[str] = None
    completed_at: Optional[str] = None
    last_error: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def erased(self) -> bool:
        return self.phase == "completed" and self.verified_zero

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DeletionStatus":
        return cls(
            collection_id=d.get("collection_id", ""),
            phase=d.get("phase", ""),
            collection_status=d.get("collection_status", ""),
            verified_zero=bool(d.get("verified_zero", False)),
            attempts=d.get("attempts", 0) or 0,
            deletion_class=d.get("deletion_class"),
            workflow_id=d.get("workflow_id"),
            workflow_status=d.get("workflow_status"),
            purge_after=d.get("purge_after"),
            requested_at=d.get("requested_at"),
            completed_at=d.get("completed_at"),
            last_error=d.get("last_error"),
            raw=d,
        )
