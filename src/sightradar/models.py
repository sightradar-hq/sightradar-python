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
    similarity: Optional[float] = None
    point_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Match":
        return cls(
            photo_id=d.get("photo_id") or d.get("photoId"),
            similarity=d.get("similarity"),
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
