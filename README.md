<p align="center">
  <a href="https://sightradar.com">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://assets.sightradar.com/brand/sightradar-logo-lockup-dark.png">
      <img src="https://assets.sightradar.com/brand/sightradar-logo-lockup.png" alt="SightRadar — Face Recognition API" width="360">
    </picture>
  </a>
</p>

<h1 align="center">SightRadar — Face Recognition API for Python</h1>

<p align="center">
  <strong>A high-accuracy face recognition API and a drop-in AWS Rekognition alternative.</strong><br>
  Official Python client for the <a href="https://sightradar.com">SightRadar</a> facial recognition API — face detection, 1:1 verification, and 1:N face search with zero runtime dependencies.
</p>

<p align="center">
  <a href="https://pypi.org/project/sightradar/"><img src="https://img.shields.io/pypi/v/sightradar?color=ff3b2f&label=pypi" alt="PyPI version"></a>
  <a href="https://pypi.org/project/sightradar/"><img src="https://img.shields.io/pypi/pyversions/sightradar" alt="Python versions"></a>
  <a href="https://github.com/sightradar-hq/sightradar-python/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/sightradar?color=1b1712" alt="License: MIT"></a>
  <a href="https://sightradar.com/docs"><img src="https://img.shields.io/badge/docs-sightradar.com-ffce4a" alt="Documentation"></a>
</p>

---

## What is SightRadar?

**SightRadar** is a fast, accurate, and affordable **face recognition API** for developers. This is the official **Python SDK** — a thin, fully-typed wrapper over the [SightRadar facial recognition API](https://sightradar.com) that lets you add **face detection**, **face matching**, **1:1 face verification**, and **1:N face search** to any application in minutes.

If you are looking for an **AWS Rekognition alternative** with **high-accuracy face recognition**, simpler pricing, and a cleaner API, SightRadar is built for you. The SDK has **zero runtime dependencies** (built entirely on the Python standard library), supports Python 3.8+, and ships typed responses for every endpoint.

- 🎯 **High-accuracy facial recognition** — state-of-the-art embeddings with quality gating for reliable matches
- ⚡ **Fast face search** — index millions of faces and search a collection with a single selfie
- 🔁 **Drop-in AWS Rekognition alternative** — familiar `index` / `search` / `detect` / `compare` operations
- 💸 **Transparent, usage-based pricing** — pay per call, no minimums ([see pricing](https://sightradar.com/pricing))
- 🪶 **Zero dependencies** — pure standard-library client, easy to audit and vendor

> Get a free API key at **[sightradar.com](https://sightradar.com/login)** and start building.

## SightRadar vs. AWS Rekognition

Already wrote code against **AWS Rekognition**? SightRadar mirrors the operations you know — `IndexFaces`, `SearchFacesByImage`, `DetectFaces`, `CompareFaces` — so migrating is mostly a find-and-replace, not a rewrite. See the [migration guide](https://sightradar.com/migrate).

| | SightRadar | AWS Rekognition |
|---|---|---|
| Face detection API | ✅ | ✅ |
| 1:1 face verification (compare) | ✅ | ✅ |
| 1:N face search (collections) | ✅ | ✅ |
| Selfie / liveness-style registration | ✅ | ⚠️ limited |
| Zero-dependency SDK | ✅ | ❌ (boto3) |
| Transparent per-call pricing | ✅ | ⚠️ complex tiers |
| Free API key to start | ✅ | ⚠️ AWS account required |

## Install

```bash
pip install sightradar
```

## Authenticate

Create an API key in the [console](https://sightradar.com/login), then pass it
directly or via the `SIGHTRADAR_API_KEY` environment variable.

```python
from sightradar import SightRadar

sr = SightRadar(api_key="frs_...")   # or: SightRadar() with SIGHTRADAR_API_KEY set
```

## Core workflow — index and search faces

```python
# 1. Create a collection to hold faces.
sr.create_collection("event-2026")

# 2. Index faces from photos (URL, GCS key, or a local file).
sr.index("event-2026", url="https://example.com/group.jpg")
sr.index("event-2026", file="/path/to/photo.jpg", photo_id="img-42")

# 3. Search the collection with one selfie.
result = sr.search("event-2026", url="https://example.com/selfie.jpg")
if result.found:
    for m in result.matches:
        print(m.photo_id, round(m.score, 3))
else:
    print("no match:", result.reason)
```

## Stateless operations (nothing stored)

```python
# Detect + quality-gate faces in an image.
det = sr.detect(url="https://example.com/photo.jpg")
print(det.detected_face_count, det.gated_face_count)

# 1:1 face verification between two faces.
cmp = sr.compare(
    source_url="https://example.com/a.jpg",
    target_url="https://example.com/b.jpg",
)
print(cmp.match, cmp.similarity)
```

## Selfies and search by id

Register one selfie per person, then search with the returned ``point_id``
instead of re-uploading an image (cheaper: the search-by-id tier).

```python
reg = sr.register_selfie("event-2026", "user-42", url="https://example.com/selfie.jpg")
hits = sr.search_by_id("event-2026", reg.point_id, limit=20)
```

## Deleting (soft by default, restorable)

```python
# Soft delete: stops serving now, erased after the grace window. Undo with restore.
receipt = sr.delete_collection("event-2026")     # receipt.restorable is True
sr.restore_collection("event-2026")

# Immediate / compliance (GDPR / BIPA) erasure — NOT restorable.
sr.delete_collection("event-2026", compliance=True)
status = sr.deletion_status("event-2026")        # status.erased -> phase completed + verified_zero

# One photo's faces only.
sr.delete_photo("event-2026", "img-42")
sr.restore_photo("event-2026", "img-42")
```

## Batches and webhooks

```python
wh = sr.register_webhook("https://your.app/sightradar")
# wh.secret is returned ONCE — store it.

batch = sr.submit_batch(
    "event-2026", "index",                       # or "match"
    [{"url": "https://example.com/1.jpg", "external_id": "img-1"}],
    webhook_endpoint_id=wh.webhook_endpoint_id,
)
status = sr.get_batch(batch.batch_id)            # .succeeded / .failed / .pending / .done
page = sr.get_batch_photos(batch.batch_id)       # per-photo results, paginated

# In your webhook handler (raw body, not parsed JSON):
from sightradar import verify_webhook_signature
ok = verify_webhook_signature(
    stored_secret,
    request.headers["X-SightRadar-Timestamp"],
    request.get_data(),                          # raw bytes
    request.headers["X-SightRadar-Signature"],
)
```

## Retries and idempotency

Retries are off by default. Pass ``max_retries`` to retry 429/502/503 with
backoff. Pass ``idempotency_key`` on billable calls so a retry can never
double-charge you.

```python
sr = SightRadar(api_key="frs_...", max_retries=3)
sr.index("event-2026", url="https://example.com/a.jpg", idempotency_key="photo-a-v1")
```

## Account

```python
print(sr.wallet().balance_credits)
print(sr.usage(days=30))
```

## Errors

Every non-2xx response raises a typed exception:

```python
from sightradar import (
    SightRadarError,            # base
    AuthenticationError,        # 401
    InsufficientCreditsError,   # 402
    NotFoundError,              # 404
    RateLimitError,             # 429
)

try:
    sr.describe_collection("missing")
except NotFoundError as e:
    print(e.status_code, e.message)
```

## Image inputs

Index / search / detect / register_selfie accept exactly one image source (register_selfie also needs ``user_id``):

- `url=` — a public image URL
- `gcs_key=` — a Google Cloud Storage object key
- `file=` — a local path, `bytes`, or a file-like object (uploaded as multipart)

`search` additionally accepts `embedding=` (a 512-d vector).

## Resources

- 🌐 **Website:** [sightradar.com](https://sightradar.com)
- 📚 **API documentation:** [sightradar.com/docs](https://sightradar.com/docs)
- 🔑 **Get an API key:** [sightradar.com/login](https://sightradar.com/login)
- 💸 **Pricing:** [sightradar.com/pricing](https://sightradar.com/pricing)
- 🔄 **Migrate from AWS Rekognition:** [sightradar.com/migrate](https://sightradar.com/migrate)
- 📦 **Node.js / TypeScript SDK:** [github.com/sightradar-hq/sightradar-node](https://github.com/sightradar-hq/sightradar-node)

## License

MIT © [SightRadar](https://sightradar.com)

---

<p align="center">
  <sub>
    SightRadar — high-accuracy <a href="https://sightradar.com">face recognition API</a> and <a href="https://sightradar.com/migrate">AWS Rekognition alternative</a>.
    Face detection, facial recognition, 1:1 verification, and 1:N face search for developers.
  </sub>
</p>
