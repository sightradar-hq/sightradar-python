<p align="center">
  <a href="https://sightradar.com">
    <img src="https://assets.sightradar.com/brand/sightradar-logo-lockup.svg" alt="SightRadar — Face Recognition API" width="360">
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
        print(m.photo_id, round(m.similarity, 3))
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

Index / search / detect / register-selfie accept exactly one image source:

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
