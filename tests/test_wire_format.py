"""Wire-format tests: these assert the exact JSON keys and query strings the
gateway/engine read, because the 1.0.x clients got them wrong (search-by-id
sent ``id`` instead of ``pointId``; register_selfie never sent ``userId``).
"""

from __future__ import annotations

import json
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest

from sightradar import SightRadar, SightRadarError


class _Resp:
    def __init__(self, status, payload):
        self.status = status
        self._body = json.dumps(payload).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _capture(payload, status=200):
    seen = {}

    def _side_effect(req, *a, **k):
        seen["method"] = req.get_method()
        u = urlparse(req.full_url)
        seen["path"] = u.path
        seen["query"] = parse_qs(u.query)
        seen["headers"] = {k.lower(): v for k, v in req.header_items()}
        seen["body"] = req.data
        return _Resp(status, payload)

    return seen, mock.patch("sightradar.client.urlrequest.urlopen", side_effect=_side_effect)


def test_search_by_id_sends_pointId():
    seen, patch = _capture({"collection_id": "c", "matches": [], "photo_ids": []})
    sr = SightRadar(api_key="frs_test")
    with patch:
        sr.search_by_id("c", "3f2b0c9a-0000-4000-8000-000000000001", threshold=0.5, limit=5)
    body = json.loads(seen["body"])
    assert body["pointId"] == "3f2b0c9a-0000-4000-8000-000000000001"
    assert "id" not in body
    assert body["threshold"] == 0.5 and body["limit"] == 5
    assert seen["path"] == "/v1/collections/c/search-by-id"


def test_register_selfie_json_sends_userId():
    seen, patch = _capture({"face_found": True, "point_id": "p1", "user_id": "u1"})
    sr = SightRadar(api_key="frs_test")
    with patch:
        res = sr.register_selfie("c", "u1", url="https://x/selfie.jpg", selfie_id="s1")
    body = json.loads(seen["body"])
    assert body == {"url": "https://x/selfie.jpg", "userId": "u1", "selfieId": "s1"}
    assert res.face_found and res.point_id == "p1"


def test_register_selfie_multipart_sends_userId_field():
    seen, patch = _capture({"face_found": True, "point_id": "p1"})
    sr = SightRadar(api_key="frs_test")
    with patch:
        sr.register_selfie("c", "u1", file=b"\xff\xd8jpegbytes")
    assert seen["headers"]["content-type"].startswith("multipart/form-data")
    assert b'name="userId"\r\n\r\nu1\r\n' in seen["body"]
    assert b'name="selfieId"' not in seen["body"]  # optional, omitted when None
    assert b'name="file"; filename="upload.jpg"' in seen["body"]


def test_register_selfie_requires_user_id():
    sr = SightRadar(api_key="frs_test")
    with pytest.raises(SightRadarError):
        sr.register_selfie("c", "", url="https://x/selfie.jpg")


def test_delete_collection_default_is_soft():
    seen, patch = _capture(
        {"status": "deletion_pending", "mode": "soft", "restorable": True,
         "workflow_id": "w1", "purge_after": "2026-10-01T00:00:00Z"}, status=202,
    )
    sr = SightRadar(api_key="frs_test")
    with patch:
        r = sr.delete_collection("c")
    assert seen["method"] == "DELETE" and seen["query"] == {}
    assert r.restorable is True and r.mode == "soft" and r.workflow_id == "w1"


def test_delete_collection_flags():
    seen, patch = _capture({"status": "deleting", "mode": "immediate", "restorable": False}, 202)
    sr = SightRadar(api_key="frs_test")
    with patch:
        sr.delete_collection("c", immediate=True, compliance=True, intent="erase")
    assert seen["query"] == {"immediate": ["true"], "compliance": ["true"], "intent": ["erase"]}


def test_restore_and_deletion_status_paths():
    seen, patch = _capture({"status": "active"})
    sr = SightRadar(api_key="frs_test")
    with patch:
        sr.restore_collection("c")
    assert (seen["method"], seen["path"]) == ("POST", "/v1/collections/c/restore")

    seen, patch = _capture({"collection_id": "c", "phase": "completed", "verified_zero": True,
                            "collection_status": "deleted", "attempts": 1})
    with patch:
        st = sr.deletion_status("c")
    assert seen["path"] == "/v1/collections/c/deletion" and st.erased


def test_photo_delete_and_restore_escape_photo_id():
    seen, patch = _capture({"deleted": True})
    sr = SightRadar(api_key="frs_test")
    with patch:
        sr.delete_photo("c", "a/b c", immediate=True)
    assert seen["path"] == "/v1/collections/c/photos/a%2Fb%20c"
    assert seen["query"] == {"immediate": ["true"]}
    with patch:
        sr.restore_photo("c", "a/b c")
    assert seen["path"] == "/v1/collections/c/photos/a%2Fb%20c/restore"


def test_index_sends_idempotency_key_header():
    seen, patch = _capture({"collection_id": "c", "indexed": 1})
    sr = SightRadar(api_key="frs_test")
    with patch:
        sr.index("c", url="https://x/a.jpg", idempotency_key="k-123")
    assert seen["headers"]["idempotency-key"] == "k-123"


def test_batch_model_reads_gateway_counts():
    seen, patch = _capture({
        "batch_id": "b1", "collection_id": "c", "op": "index", "status": "completed",
        "total_photos": 10, "succeeded": 9, "failed": 1, "pending": 0, "claimed": 0,
        "created_at": "2026-09-01T00:00:00Z",
    })
    sr = SightRadar(api_key="frs_test")
    with patch:
        b = sr.get_batch("b1")
    assert (b.total_photos, b.succeeded, b.failed) == (10, 9, 1) and b.done


def test_batch_photos_path_and_cursor():
    seen, patch = _capture({"batch_id": "b1", "photos": [], "has_more": False})
    sr = SightRadar(api_key="frs_test")
    with patch:
        sr.get_batch_photos("b1", limit=100, after_index=499)
    assert seen["path"] == "/v1/batches/b1/photos"
    assert seen["query"] == {"limit": ["100"], "after_index": ["499"]}


def test_webhook_model_reads_endpoint_id_and_secret_once():
    seen, patch = _capture({"webhook_endpoint_id": "we1", "url": "https://h/x",
                            "status": "active", "secret": "whsec_1"})
    sr = SightRadar(api_key="frs_test")
    with patch:
        w = sr.register_webhook("https://h/x")
    assert w.webhook_endpoint_id == "we1" and w.webhook_id == "we1" and w.secret == "whsec_1"
    assert json.loads(seen["body"]) == {"url": "https://h/x"}


def test_register_selfie_never_forwards_photo_id_in_either_path():
    """photoId is the index key; the selfies endpoint does not accept it."""
    seen, patch = _capture({"face_found": True, "point_id": "p1"})
    sr = SightRadar(api_key="frs_test")
    with patch:
        sr.register_selfie("c", "u1", url="https://x/a.jpg")
    assert "photoId" not in json.loads(seen["body"])
    with patch:
        sr.register_selfie("c", "u1", file=b"\xff\xd8")
    assert b'name="photoId"' not in seen["body"]


def test_register_selfie_missing_user_id_makes_no_request():
    seen, patch = _capture({})
    sr = SightRadar(api_key="frs_test")
    with patch, pytest.raises(SightRadarError):
        sr.register_selfie("c", "", url="https://x/a.jpg")
    assert "path" not in seen


def test_collection_id_is_percent_encoded_in_every_path():
    """1.1.0 spliced collection_id raw into f-string paths; a non-ASCII or
    slash-bearing id crashed urllib with UnicodeEncodeError before any request."""
    cid = "événement 😀/2026?x"
    from urllib.parse import quote
    enc = quote(cid, safe="")
    sr = SightRadar(api_key="frs_test")
    calls = [
        (lambda: sr.describe_collection(cid), f"/v1/collections/{enc}", {}),
        (lambda: sr.collection_metrics(cid), f"/v1/collections/{enc}/metrics", {}),
        (lambda: sr.index(cid, url="https://x/a.jpg"), f"/v1/collections/{enc}/index", {"collection_id": cid, "indexed": 0}),
        (lambda: sr.search(cid, url="https://x/a.jpg"), f"/v1/collections/{enc}/search", {"matches": []}),
        (lambda: sr.search_by_id(cid, "1"), f"/v1/collections/{enc}/search-by-id", {"matches": []}),
        (lambda: sr.register_selfie(cid, "u", url="https://x/a.jpg"), f"/v1/collections/{enc}/selfies", {"face_found": True}),
        (lambda: sr.delete_collection(cid), f"/v1/collections/{enc}", {"status": "deletion_pending"}),
        (lambda: sr.restore_collection(cid), f"/v1/collections/{enc}/restore", {}),
        (lambda: sr.deletion_status(cid), f"/v1/collections/{enc}/deletion", {}),
        (lambda: sr.delete_photo(cid, "p/1"), f"/v1/collections/{enc}/photos/p%2F1", {}),
        (lambda: sr.restore_photo(cid, "p/1"), f"/v1/collections/{enc}/photos/p%2F1/restore", {}),
        (lambda: sr.get_batch("b/1"), "/v1/batches/b%2F1", {}),
        (lambda: sr.get_batch_photos("b/1"), "/v1/batches/b%2F1/photos", {}),
        (lambda: sr.delete_webhook("w/1"), "/v1/webhooks/w%2F1", {}),
    ]
    for fn, want_path, payload in calls:
        seen, patch = _capture(payload)
        with patch:
            fn()
        # urlparse() decodes nothing, so compare the raw encoded path
        assert seen["path"] == want_path, (seen["path"], want_path)
