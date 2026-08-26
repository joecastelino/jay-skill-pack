---
name: tekion-media-api
description: Add, read, or delete MEDIA (vehicle photos/videos/360s, and deal document files) in Tekion via the public OpenAPI. Covers the URL-reference model for Vehicle Inventory media and the 2-step presigned binary upload for Deal documents, plus how to prove write access without writing data. Use for "can we push photos into Tekion", VI image automation, vAuto/photographer feeds, or deal-doc uploads.
triggers:
  - tekion media api
  - add photos to tekion
  - upload images tekion
  - vehicle inventory media
  - push pictures into tekion
  - tekion photo automation
  - deal document upload tekion
---

# Tekion Media via OpenAPI

**Verified live across all 7 AMG stores 2026-08-26. Write access IS granted.**

There are **two completely different media surfaces** with different mechanics.
Picking the wrong one wastes a lot of time.

---

## 1. Vehicle Inventory media (photos / videos / 360s)

**URL-REFERENCE model — NOT a binary upload.** You host the file at a publicly
reachable URL and Tekion fetches it. There is **no multipart endpoint** for VI media.

| Action | Endpoint |
|---|---|
| Add (bulk) | `POST /vehicle-inventory/{vehicle-inventory-id}/media` |
| Get all (incl. premium) | `GET /vehicle-inventory/{vid}/media` |
| Get standard (dealer-uploaded + OEM) | `GET /vehicle-inventory/{vid}/media/standard-media` |
| Delete one | `DELETE /vehicle-inventory/{vid}/media/{media-id}` |

Body is a **JSON array** (bulk add; the whole request fails if any one record is invalid):

```json
[
  {"url":"https://your-cdn/photo1.jpg","fileName":"Front 3/4.jpg",
   "type":"IMAGE","sourceType":"DEALER"}
]
```

- `type` enum: `IMAGE` | `VIDEO` | `IMAGE_360_DEGREE` (anything else → 400 `VI251`)
- `sourceType`: use `DEALER` for dealer-supplied (OEM feed rows come back `null`)

### Getting a vehicle-inventory-id

```json
POST /vehicle-inventory:search
{"filters":[{"field":"status","operator":"IN","values":["STOCKED_IN"]}],
 "page":{"pageNo":1,"pageSize":50}}
```

- Key is **`field`**, NOT `name` → `name` returns 400 `VI274`
  ("Filter field cannot be blank/null if operator is not BOOL")
- Results live at `data.results[]` (not `data[]`)
- `medias` on a vehicle is just `{"link": "..."}` — a sub-resource pointer, fetch separately

**ID shape varies by store** — do not assume mongo hex:
- hex: `st`/`sv`/`bc`/`ar`/`tl` (e.g. `632a6056e7843f5161dd38e1`)
- `<dealerId>_<stock>`: `bt` (`1249_79071`), `vc` (`1891_V230081`)

---

## 2. Deal document media (true binary upload)

`POST /deals/{deal-id}/files/{file-id}/media/upload` — **2-step presigned**:

1. Send metadata → `{"contentLength":524344,"fileName":"sample.pdf","fileType":"application/pdf"}`
2. Response → `{mediaId, uploadUrl (presigned S3), uploadUrlExpiresAt, ...}`
3. **PUT the raw bytes to `uploadUrl`** before it expires

Limits: **10 MB max**; `.pdf .jpg .jpeg .png .bmp .heic`.
`file-id` = a **formId or documentId** (not arbitrary).

---

## Proving write access WITHOUT writing data

Send a deliberately invalid enum. Nothing persists either way:

```json
POST /vehicle-inventory/{vid}/media
[{"url":"x","fileName":"x.png","type":"BAD_ENUM","sourceType":"DEALER"}]
```

- **400** `"BAD_ENUM is an invalid value for the field media.type"` → endpoint **GRANTED**, validation live
- **403** `"app version ... does not support this API"` → blocked by the pilot app version

## PITFALLS

- **A 200 is NOT proof of a write.** Posting a record with a **missing `url`**
  returns `200 {"data":[{"id":null,"url":null,...}]}` — an **echo**, persisting
  nothing. Verified: 33 media rows before and after, 0 null-url rows. **Always
  re-GET and count** before claiming a write landed.
- Posting an **empty array** `[]` also returns `200 {"data":[]}`. Harmless no-op.
- **Sandbox is not usable for this.** `tekion-api/config.json` sandbox creds are
  unprovisioned (token request 400). Token endpoint is
  `POST /openapi/public/tokens` (**form-encoded**) — `/openapi/v4.0.0/tokens` is 404.
- Token generation is capped **20 per 15 min** — cache (`tekion_client.get_token`
  already caches to disk until ~5 min before expiry).
- `dealer_id` header must be the **full** `americanmotorscorporation_<id>_0`
  string; a bare number gives a misleading 403 "Missing context headers".

## Working snippet

```python
import sys, json, urllib.request
sys.path.insert(0, "/home/itadmin/tekion-api")
from tekion_client import load_config, get_token
cfg = load_config(); tok = get_token(cfg)
base = cfg["base_url"] + "/openapi/v4.0.0"
H = {"Authorization": f"Bearer {tok}", "app_id": cfg["app_id"],
     "dealer_id": cfg["dealers"]["st"], "Content-Type": "application/json"}

def call(method, ep, body=None):
    r = urllib.request.Request(base + ep, headers=H, method=method,
        data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=60) as f:
            return f.status, json.loads(f.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
```

## Related
- `tekion-vi-api-migration` — the VI data pull (2 AM cron) this sits alongside
- `tekion-api-upgrade-audit` — re-probing grants after an APC app version bump
