# SightRadar — Python client

Official Python client for the [SightRadar](https://sightradar.com) face
recognition API. Zero runtime dependencies (built on the standard library).

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

## Core workflow

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

# 1:1 verification between two faces.
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

## License

MIT
