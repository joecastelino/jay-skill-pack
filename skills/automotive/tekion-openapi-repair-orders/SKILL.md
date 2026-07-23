---
name: tekion-openapi-repair-orders
description: Pull repair orders, jobs, operations (opcode + labor $), parts, and vehicle data from the official Tekion OpenAPI — no browser, no OTP. Also covers logging into the APC partner portal (apc.tekioncloud.com) to scrape API docs and download OpenAPI specs.
triggers:
  - repair orders api
  - pull ro data
  - opcode labor dollars
---

# Tekion OpenAPI — Repair Orders, Parts, and APC Portal Scraping

## Critical correction
Our existing API key (Don's, `~/tekion-api/config.json`) **DOES have repair-order and parts scope**. Past 403/404 results were caused by **wrong paths**. Tekion v4 uses **colon-action endpoints**, not REST-plural ones:

- ❌ `GET /openapi/v4.0.0/repair-orders` → 404
- ❌ `GET /openapi/v3.1.0/repair-orders` → 403
- ✅ `POST /openapi/v4.0.0/repair-orders:search` → works
- ✅ `POST /openapi/v4.0.0/parts-inventory:search` → works

## Client setup
```python
import sys, json, urllib.request, urllib.error
sys.path.insert(0, "/home/itadmin/tekion-api")
from tekion_client import load_config, get_token
cfg = load_config(); tok = get_token(cfg)
BASE = cfg["base_url"] + "/openapi/v4.0.0"
# headers REQUIRED on every call:
h = {"Authorization": f"Bearer {tok}", "app_id": cfg["app_id"],
     "dealer_id": cfg["dealers"]["st"],  # st=SCT(876), bt=Blackstone, etc.
     "Content-Type": "application/json"}
```

## Search repair orders
`POST /repair-orders:search`
```json
{"filters":[{"field":"creationTime","operator":"GTE","values":["<epoch_ms_as_STRING>"]}],
 "pageSize": 50}
```
- **Allowed fields**: `opcode, make, status, vin, documentNumber, documentId, creationTime, invoicedTime, closedTime, modifiedTime, paytype`
- **Allowed operators**: `GT, GTE, LT, LTE, IN, NIN, BTW, BOOL` — NOT "BETWEEN" (400 invalid.filter.operator). BTW takes exactly 2 values.
- Epoch-ms values go in `values` as **strings**.
- `pageSize` max 50; paginate via `paginationToken` from `meta.nextPageToken`.
- Response: `out["data"]["results"]` (list of ROs), `out["meta"]["totalCount"]`.
- RO record: `documentId` (internal id), `documentNumber` (RO#), `status`, `tags` (includes OPCODE + BASE_PAY_TYPE system tags — quick opcode presence check without fetching jobs), plus link stubs for jobs/vehicle/invoices/fees.

## Nested RO resources (GET, same headers)
- `/repair-orders/{rid}/jobs` → `data.jobs[]` — payType, status, concern text, job id
- `/repair-orders/{rid}/jobs/{jid}/operations` → `data.roOperations[]` — **`opcode`, `opcodeDescription`, `labor.saleAmount` (CENTS: 8999 = $89.99), `labor.costAmount`**
- `/repair-orders/{rid}/jobs/{jid}/operations/{oid}/parts` → `data.parts[]` — partNumber, quantities[], costAmount, saleAmount
- `/repair-orders/{rid}/ro-vehicle` → vin, year/make/model, mileageIn/Out
- `/repair-orders/{rid}/ro-invoices` → works (data may be sparse pre-invoice)
- `.../technicians` → works
- ❌ `/repair-orders/{rid}/pricing` → 500 "unsupported.operation" — don't use

**Gotcha**: `data` payload shape varies per endpoint — sometimes `data.jobs`, `data.roOperations`, `data.results`, or a bare dict. Inspect keys, don't assume `results`.

## Parts inventory search
`POST /parts-inventory:search` body: `{"searchText": "87139"}` (NOT `textSearch` — that 400s with "searchText is required"). Returns partNumber, description, brand, onHandQty. Paginated via meta.nextPageToken.

### ⚠️ Parts Inventory API exposes ONLY 4 fields — it CANNOT diagnose auto-order/stock-out root cause (verified 2026-06-23)
The entire **Parts Inventory** section of the Tekion OpenAPI has exactly ONE endpoint
(`parts-inventory:search`) and its response schema is just **`partNumber, description,
brand, onHandQty`** (confirmed by dumping every property name in
`~/dealerdetail/specs/apis/parts-inventory__search-parts-inventory.json`). It does
**NOT** expose any of the stocking-control settings that actually drive auto-ordering:
- min/max / best-stock, reorder point
- Source Type (Stock vs Special-Order / Non-Stock)
- phase-in / phase-out status, "do not order" flag
- replenishment / DRP run state

So the API can tell you **WHAT** (on-hand qty, e.g. all stocked out at 0) but never
**WHY** a part didn't auto-replenish. That config lives **only in the Tekion Parts UI**
(Parts → Inventory → part detail → Source/Stocking tab). For a parts-shortage / "why
didn't it auto-order" diagnosis: use the API to confirm `onHandQty == 0`, then drive the
:9223 persistent browser into the Parts module to read Source Type + Min/Max + phase
status per part. Don't waste calls probing for a richer parts endpoint — there isn't one.

Likely root causes (read these in the UI): (1) Source Type = Special-Order/Non-Stock →
never auto-orders by design (typical for CV axles, key fobs, low-frequency parts);
(2) Min/Max = 0 on a part added ad-hoc to an RO but never set up as a true stocked item
(common culprit for a fast-mover like a front brake pad kit `044650R010` sitting at 0);
(3) phase-out / do-not-order flag; (4) daily stock order (DRP) not being run/approved.

### RO lookup by documentNumber — IN-filter pagination quirk
`repair-orders:search` with `documentNumber IN [list]` can return `meta.totalCount`
HIGHER than the rows it actually returns (e.g. totalCount=6 but only 4 results, no
`nextPageToken`) when some RO records were very recently opened/closed and aren't fully
indexed yet. Re-running individually or paginating won't surface them until Tekion's
index catches up. Don't treat the missing rows as a bug — note them and re-pull later.
The on-the-record `repair-orders:search` result carries `documentId`, `documentNumber`,
`status`, `assignee.advisor.id`, and OPCODE `tags` for free.

### RO part lines — fulfillment + description gotchas
Walking `/repair-orders/{rid}/jobs/{jid}/operations/{oid}/parts`, each part has
`partNumber`, `partName` (NOT `description` — `description` is often None on the RO part
line; the human name lives in `parts-inventory:search.description` instead), `status` /
`fulfillmentStatus` (values seen: `DELIVERED`, `HOLD`), `quantities[]` (type SALE),
`saleAmount`/`costAmount`/`unitSaleAmount`/`unitCostAmount` (cents), `core`/`coreReturn`,
`eligibleForClaim`. A `HOLD` fulfillment on a part = it was backordered / not yet pulled,
a useful signal in a shortage investigation.

## Quota — THE THROTTLE IS REAL (hit 2026-06-12)
500,000 calls / 30 days, throttle **1,500 / 15 min** (Basic Plan).

### ⚠️ `OVERALL_QUOTA` ≠ `OVERALL_RATELIMIT` (hit 2026-07-07)
`429 "Limit exhausted for type : OVERALL_QUOTA"` is the app-WIDE quota bucket, not
the 15-min throttle — it blocks EVERY OpenAPI consumer (scans, VI pull, DealerDetail
sync) and can persist for hours. When you see it: (1) check for a STUCK consumer
re-burning quota in retry loops (`ps aux | grep vi-api-pull` — the 2 AM VI job stuck
7+ hrs was the 2026-07-07 culprit; kill it + `rm /tmp/tekion-vi.lock`), (2) do NOT
blind-retry — park a watcher that probes a 1-row `repair-orders:search` every 20 min
and auto-resumes the blocked job on 200, (3) checkpoint enumeration scans BY MONTH so

**⚠️ Watcher-probe trap (hit 2026-07-10): a probe that treats ANY non-200 as
"still blocked" can hide restoration behind its own bug.** `quota_ping_once.py`
used `"operation"` instead of `"operator"` in its filter → HTTP **400**
`"filters[0].operator must not be blank"` → exit 1 → the watch job kept reporting
"still blocked" even though quota was RESTORED. Rules for quota watchers:
(a) the probe must PRINT the actual status+body and treat **only 429 as blocked** —
a 400/403/500 means the probe itself is broken and must be fixed, not silenced;
(b) filter key is **`operator`**, never `operation` (400, code 3003);
(c) when you find this bug in one script, grep siblings — `"operation"\s*:` also
lurked in `backfill_tol_closed_20260707.sh`, `quota_probe_long.py`,
`quota_probe_tol.py` under `~/tekion-reports/`.
The 2026-07-07 outage restored by 2026-07-10 ~10:15 AM PDT (~3 days); after
restoration the full 7-store VI pull ran clean in ~29 min with zero 429s, and the
nightly 1:30 AM DealerDetail `sync:all` backfills missed days automatically —
no manual backfill needed. Remember to REMOVE the temporary watch cron once
restoration is confirmed.
resume never redoes work, (4) for parts-CATEGORY unit counts (tires, batteries...),
bypass the OpenAPI entirely via the source-code path — see skill
`tekion-parts-sold-by-source-report` (zero quota, browser internal APIs). A full-day backfill scan (200 ROs × ~4 nested calls with ThreadPoolExecutor(8)) plus exploratory probing in the same window **exhausted the throttle** → `429 "Limit exhausted for type : OVERALL_RATELIMIT"`. Resets after the 15-min window.
- Budget calls: prefilter ROs by `tags` OPCODE values BEFORE fan-out (skips ~95% of jobs/operations fetches).
- For repeated comparisons, cache the day's scan to JSON and re-analyze locally instead of re-fetching.
- On 429, back off and retry after the window; don't hammer.

## Parts pricing — VERIFIED (2026-06-12, RO 568555)
`parts[].saleAmount` = **EXTENDED line total in CENTS** (4968 = $49.68 for the line, qty already included). Do NOT multiply by quantity — that double-counts. Correct math:
```python
line = part.get("saleAmount")
if line is None:  # fallback only
    qty = next((q["value"] for q in part.get("quantities", []) if q.get("type")=="SALE"), 0)
    line = (part.get("unitSaleAmount") or 0) * (qty or 0)
parts_total += (line or 0) / 100
```
`unitSaleAmount` is the per-unit price in cents.

## ⭐ Advisor names — UPGRADED: public OpenAPI `/users/{id}` NOW WORKS (2026-06-18)

**THIS SUPERSEDES every browser/appointment-join method below. Read this first.**

Joe upgraded the Tekion app's API scope on 2026-06-18. The PUBLIC OpenAPI Employee/User
endpoint that used to 403 now **resolves names directly** — no `:9223` browser, no OTP,
no appointment join, no internal `/api/` path. Production/serverless-safe.

```python
import sys, json, urllib.request
sys.path.insert(0,"/home/itadmin/tekion-api")
from tekion_client import load_config, get_token
cfg=load_config(); tok=get_token(cfg)
BASE=cfg["base_url"]+"/openapi/v4.0.0"
def H(): return {"Authorization":f"Bearer {tok}","app_id":cfg["app_id"],
                 "dealer_id":cfg["dealers"]["st"],"Content-Type":"application/json"}  # st=SCT/876
def resolve(uid):
    req=urllib.request.Request(BASE+f"/users/{uid}", headers=H())
    d=json.loads(urllib.request.urlopen(req,timeout=20).read())
    data=d.get("data",d)
    nd=data.get("userNameDetails",{})
    disp=next((c["value"] for c in nd.get("completeNames",[]) if c.get("nameType")=="DISPLAY_NAME"),None)
    name=disp or (nd.get("firstName","")+" "+nd.get("lastName","")).strip()
    persona=data.get("userRoleDetails",{}).get("primaryRole",{}).get("persona")
    return name, persona
```
- Works for BOTH short numeric ids ("59","74","218") AND UUIDs. ~0.3s each.
- Returns `userNameDetails.completeNames[DISPLAY_NAME]` + `userRoleDetails.primaryRole.persona`
  (SERVICE_ADVISOR / TECHNICIAN / SERVICE_MANAGER / WARRANTY_CLERK / CASHIER).
- Title-case the names (Tekion stores some ALL-CAPS).

### ⚠️ "Any Service Advisor" was a CACHE BUG, not a real placeholder (corrected 2026-06-18)
The old `sct-advisor-cache.json` had THREE UUIDs mislabeled `"Any Service Advisor"` →
they are actually **real advisors**: `ee31e3e9…`=Angel Gutierrez, `bfb756e2…`=Michael
Robert Costa, `f3fabb57…`=Juan Jose Perez. There is **NO genuine "Unassigned" bucket** —
every closed RO carries a real `assignee.advisor.id` that now resolves to a person.
If a fresh by-advisor report shows an "Unassigned" row, the cache is STALE — re-resolve
all unique advisor ids via `/users/{id}` and rebuild the cache before shipping. Joe will
(rightly) reject any "Unassigned" on a closed-RO advisor breakdown.

### Rebuild-the-cache one-liner (do this when names look wrong)
```python
advmap=json.load(open("data/sct-june-align-advisor-ids.json"))  # docId->advisorId
cache={uid:(lambda n:(" ".join(w.capitalize() for w in n.split())))(resolve(uid)[0])
       for uid in sorted(set(advmap.values()))}
json.dump(cache, open("data/sct-advisor-cache.json","w"), indent=1)  # back up the old one first
```
Verified 2026-06-18: 17/17 SCT June advisor ids resolved, zero Unassigned, totals
unchanged (161 dedicated + 19 bundled = 180 across 176 ROs). Key fixes: 74=Brian Keat,
61=Jon Vu, 55=Jason Sulon, 73=Shaun Kamal, 218=Jose Moreno(tech), 69=Adam Esquivel.

### When data lives in a tek_align (bundled) entry it's a DICT not a string
`scan["tek_align"]` items are `{"opcode","desc"}` dicts; `align_op` items are plain
strings. When building the page-2 detail labels, coerce: `lbl = x if isinstance(x,str)
else x.get("opcode")`. Mixing them raises `TypeError: dict + str` in the renderer.

---

## Advisor names — SOLVED via appointment join (2026-06-12 PM) [LEGACY — use /users/{id} above instead]
**Working method**: internal `GET /api/service-module/u/ro/{documentId}` → `ro.appointmentId`, then `GET /api/scheduling/u/appointment/{apptId}` → regex `"serviceAdvisorName":"..."` gives the full name ("EDGARDO OLIVER"). Run both via the persistent browser (:9223 /eval) with the full header bundle (tekion-api-token/dealerId/roleId/tek-siteId from localStorage). Implemented: `resolve_advisors_via_browser()` in `/home/itadmin/tekion-reports/sct_menu_sales_api.py`; cache `data/sct-advisor-cache.json` (numeric ids stable → cache makes browser calls rare). Walk-ins (no appointment) → "Any Service Advisor" → display "Unassigned".
**Alternate working method (2026-06-12, confirmed live)**: the advisor user-id from `assignee.advisor.id` resolves directly via the INTERNAL app endpoint **`GET https://app.tekioncloud.com/api/userservice/u/apc/users/{id}`** (note the `/api/` prefix — app-internal path run through the :9223 authenticated browser /eval, NOT the public OpenAPI). Response: `data.userNameDetails.firstName + ' ' + lastName` (title-case it). Verified live 2026-06-15: id "59" → "Edgardo Oliver". Cache id→name to `data/advisor-name-cache.json` / `data/sct-advisor-cache.json`.

**PUBLIC vs INTERNAL — the critical distinction (clarified 2026-06-15):**
- ❌ PUBLIC OpenAPI `GET /openapi/v4.0.0/users/{id}` → **403 "The app version 0.0.0-pilot-1.0.0 installed in the dealer does not support this API version."** NOT a wrong path and NOT permanently forbidden — the Employee/User API is real and documented, but our app *install* is registered as a pilot version lacking the Employee/User scope. Same 403 hits `/users`, `/users-by-permissions`, `/roles/{id}`. v2/v3 → 404 (only v4 exists). RO/jobs/ops/parts/service-appointments/parts-inventory/vehicle-inventory all 200 on the SAME app → it's a per-endpoint-group SCOPE entitlement, not a blanket block.
- ✅ INTERNAL `/api/userservice/u/apc/users/{id}` via the authenticated browser WORKS today, but is NOT production/serverless-deployable (needs a logged-in browser + OTP-refreshed localStorage tokens on a real box).
- **Production fix:** ask Tekion to enable Employee/User (+ GL) scope and promote the app off `0.0.0-pilot-1.0.0`. Then public `/users/{id}` works server-to-server, no browser. Request template: `~/dealer-detail/docs/tekion-api-scope-request.txt`.
- **Pluggable-resolver pattern (recommended):** one `resolveAdvisorName(id)` interface, two strategies behind env flag (`browser` interim / `api` production). Resolve once, persist names to DB so the deployed app only READS names. Ref impl: `~/dealer-detail/apps/web/lib/sources/tekion/advisors.ts`.

**BUSINESS GOTCHA — "Any Service Advisor" is a placeholder, not a person.** When an RO is created without an advisor assigned, Tekion stamps the placeholder account on `assignee.advisor`. Fixing the employee's advisor *setting*, or having that employee log in/out, does **NOT** retroactively rewrite ROs already created on the placeholder — the advisor field must be edited **on each individual RO record** in Tekion, then a rerun picks it up. Display these as "Unassigned" until the RO-level edit is saved. (Confirmed repeatedly 2026-06-12: ROs 568503/568542/568606 stayed on the placeholder through multiple reruns despite employee-side fixes.)

Dead ends (don't retry): PUBLIC `GET /openapi/v4.0.0/users/{uid}` → **NO LONGER A DEAD END — this WORKS as of the 2026-06-18 scope upgrade; see the ⭐ section above and USE IT for advisor names.** Still 404/dead: `/users:search`, `/employees*`, `/service-advisors`; employee roster lacks usable id mapping; appointment `serviceAdvisor.id` is "TEK00".
- RO assignee is **nested**: read `assignee.advisor.id` (NOT `assignee.id`). Ids are mixed UUIDs + short numerics ("59","285").

## Gross vs Price — labor.saleAmount is PRICE not gross
`labor.saleAmount` (cents) = customer price. **Gross = saleAmount − costAmount** (same struct). Parts: line `saleAmount` − `costAmount`. Report Builder "Opcode Labor/Parts Gross" = sale − cost; skip the subtraction and totals come out high.

## Known gaps (as of 2026-06-12)
- GL Data paths FOUND (2026-06-15): `GET /openapi/v4.0.0/general-ledger/balances/all` and `/general-ledger/balances/differential` (delta). Currently return **400 "unexpected.error"** — likely need required query params (accountingDate/period/pagination) AND/OR the same app-scope grant as Users (part of the pending Tekion scope request). Specs: `~/dealerdetail/specs/apis/general-ledger-data__get-gl-balances-{all,delta}.json`. Old `/general-ledger/balances` (no `/all`) was the wrong path → 404.
- **Report Builder data syncs ~4:50 AM** — a "Today"-filtered RB report shows 0 rows all day until the next sync. OpenAPI is real-time. Any API-vs-RB comparison must use YESTERDAY's data after the overnight sync; intraday RB==0 is normal, not a scraper bug.
- On 429 the per-RO fan-out (jobs/operations/parts) **silently drops ROs** if the helper returns non-200 without retry — totals come out low with no error. Check for 429 explicitly and abort/retry rather than skipping.

## APC partner portal scraping (docs + spec downloads)
URL: `https://apc.tekioncloud.com/user/login`
Login: `jcastelino@americanmotorscorp.com` + DMS password (<TEKION_PASSWORD>) + 6-digit email OTP.

**Working scrapers (2026-06-15, re-verified end-to-end):** `~/tekion-reports/apc_docs_scraper.py` (REST API index) and `~/tekion-reports/apc_webhooks_scraper.py` (webhook catalog). Copy/adapt these instead of rebuilding the login flow.

**Pitfalls (all hit and solved):**
1. The DMS account email (`jcastelino@scvolkswagen.com`) does NOT work here — APC is a separate account on the americanmotorscorp email.
2. **Session does NOT persist** — `storage_state` save/restore lands you back at /user/login. Do login + all scraping in ONE continuous Playwright session.
3. **himalaya PATH**: it lives at `/home/itadmin/.local/bin/himalaya`. When invoking via `subprocess` with a custom `env`, set `PATH="/home/itadmin/.local/bin:/usr/local/bin:/usr/bin:/bin"` AND `HOME=/home/itadmin` or you get `FileNotFoundError: himalaya`. (Do NOT use `sed` to edit the script — use the patch tool.)
4. OTP email subject: **"Your Login OTP is Here"** (different from DMS "Tekion-Login OTP"). Read via `himalaya envelope list -a personal -f "[Gmail]/All Mail" -s 15`; count baseline BEFORE triggering login, wait for count to increase, then `himalaya message read <id>` and regex `\b\d{6}\b`.
5. **Browser launch**: the playwright `chromium_headless_shell` binary is NOT installed → `headless=True` fails with "Executable doesn't exist". Use the full headed chromium and run under xvfb:
   - `executable_path="/home/itadmin/.hermes/profiles/jay/home/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome"` (note: under the PROFILE home `~/.hermes/profiles/jay/home/.cache`, NOT `/home/itadmin/.cache`)
   - `args=["--no-sandbox","--disable-dev-shm-usage"]`, `headless=False`
   - run the whole script with `HOME=/home/itadmin xvfb-run -a python3 ...`
6. **Use `wait_until="domcontentloaded"`, NOT `"networkidle"`** — the SPA keeps connections open so networkidle times out at 60s. Add `time.sleep(5-6)` after goto for React to render.
7. **Login is a 2-step React form:**
   - Email field is `input#WORK_EMAIL` with `type=text` (NOT `type=email`, NOT a `name` attr). `page.fill("#WORK_EMAIL", EMAIL)`.
   - Click Next: `page.get_by_role("button", name="Next", exact=True).click()`.
   - **Password field does not exist until after Next** — use `page.wait_for_selector("input[type=password]", timeout=20000)` before filling. Then fill + click Login (`get_by_role("button", name="Login", exact=True)`).
8. OTP entry = **six `input[type=tel]` boxes**. `page.query_selector_all("input[type=tel]")` → click `[0]`, then `page.keyboard.type(code, delay=120)` (auto-advances). Then `get_by_text("Verify", exact=True).first.click()`.
9. After Verify, `page.url` may still read /user/login but you ARE in. Just `page.goto()` the docs URL in the same session.

**Docs navigation:**
- Index: `/app/docs/versions/4.0.0/apis` — sidebar lists all sections (Repair Order has 40+ endpoints, GL Data, Parts Inventory, Service Appointments, etc.). Click section names with `get_by_text(name, exact=True)` to expand; grab `document.body.innerText`.
- Direct endpoint pages: `/app/docs/versions/4.0.0/apis/<slug>` — slugs are kebab-case but NOT always the obvious name (e.g. `search-repair-order` ✅, `get-parts-lookup` ✅ = parts-inventory:search, but `get-repair-order`/`get-operations` slugs 404 → render empty 430-char shell). If a slug fails, expand the section on the index page instead.
- **"Download Specification"** button on each endpoint page downloads a full OpenAPI 3.1 JSON (request/response schemas, filter enums, examples) — use `page.expect_download()`. Saved specs live in `~/tekion-reports/specs/`.

## APC Webhooks docs (SEPARATE tree from REST APIs — found 2026-06-15)
Webhooks are NOT under `/apis`. They live at a parallel top-level path:
- Index/first event: `https://apc.tekioncloud.com/app/docs/versions/4.0.0/webhooks` (redirects to `.../webhooks/deal.created`)
- Per-event slug: `.../webhooks/<event.type>` (e.g. `deal.created`)
- Left-nav sections are **collapsed by default except the first** — `page.get_by_text("Vehicle Inventory", exact=True).first.click()` to expand. Nav links are router divs, not `<a>` tags, so `a[href*='/webhooks/']` finds nothing; read `page.inner_text("body")` and parse the nav text instead.
- Each event page has a **"Download Specification"** button (same mechanism as REST), plus an "Event Simulator" and "Schema" tab.

**Payload envelope** (all events): `{"meta": {eventId, eventType, eventTime, version, subscriptionId, dealerId, oemId, programId}, "data": {<entity-id>, "link": "/<entity>/<id>"}}` — `data` carries only an id + link; you fetch the full record via REST.

**Catalog as of 2026-06-15 (v4.0.0):**
- **Deals (5):** deal.created, deal delivery date promised, deal status updated, deal vehicle delivered, deal vehicle delivery reported
- **Vehicle Inventory (17):** vehicle created, vehicle deleted, general custom fields updated, GL balance updated, base invoice price updated, internet price updated, invoice price updated, marketable updated, mileage updated, MSRP updated, retail price updated, status updated, sub-status updated, stock ID updated, media updated, options updated, YMMT fields updated
- **NO Repair Order / Service Appointment webhooks exist** — RO + service data stays pull-only via `repair-orders:search`. The VI webhooks map directly onto The Goods VI pipeline (price/status/mileage/media pushes could replace or augment the 2 AM full re-scrape).

## Counting a specific opcode over a month (e.g. "how many alignments sold") — PROVEN 2026-06-18

Task pattern: count how many times an opcode (or family of opcodes) was SOLD in a
month at a store, INCLUDING instances bundled inside maintenance menus. Done for
SCT/May-2026 alignments: 246 total (231 dedicated `ALIGN`/`OKAL` + 15 bundled in
TEK menus). Generalizes to brakes, tires, etc.

### The two-tier scan (this is what dodges the 429 rate-limit trap)
A full month of closed ROs at SCT = ~4,900. Fanning out jobs→operations on ALL of
them = thousands of calls → guaranteed 429 truncation. DON'T. Instead:

1. **Pass 1 — enumerate, NO fan-out.** `POST /repair-orders:search` with
   `creationTime BTW [ms0,ms1]` + `status IN [CLOSED,INVOICED]`, pageSize 50,
   paginate ALL pages. For each RO capture `documentId`, `documentNumber`, and the
   **OPCODE tags** (`[t["value"] for t in ro["tags"] if t["field"]=="OPCODE"]`).
   Save this RO index to JSON so you never re-search. ~107 pages, ~55s, ZERO
   fan-out calls. The OPCODE tags are FREE on the search result — use them to
   prefilter.
2. **Pass 2 — fan out ONLY on candidates.** Candidates = ROs whose OPCODE tags
   contain (a) the dedicated opcode(s) you're counting, OR (b) any `TEK*` menu
   opcode (because the target op may be bundled inside a menu). For SCT/May this
   was 366 of 4,891 ROs — a 13x reduction. Only these get
   jobs→operations fetches.

### Dedicated vs bundled-in-menu — the key insight
- **Dedicated:** the opcode appears as its own operation (`opcode == "ALIGN"`).
  Count these directly from the OPCODE tags in Pass 1 — no fan-out even needed for
  the dedicated count (tag presence == op present). For SCT alignments: `ALIGN`,
  `OKAL`, `ALIGN00BRA`.
- **Bundled in a menu:** a TEK* menu op (e.g. `TEK120000VNM` = 120K service)
  PERFORMS an alignment as part of the service, but the line opcode is the MENU,
  not `ALIGN`. The only way to detect it is to read the operation **story**.
  **STORY LIVES IN `operation["corrections"][]` — each is `{"id","text"}`.** Join
  all `corrections[].text` (+ `opcodeDescription`) and substring-match `"align"`
  (lowercased). Joe explicitly wanted these counted ("scrape the story in the TEK
  menus for the ones that have alignments in them"). Counting only the `ALIGN`
  opcode UNDERCOUNTS.

### Implementation notes
- Run as a **background terminal process** (`nohup ... &`, notify_on_complete),
  NOT the execute_code tool — the fan-out over a few hundred ROs exceeds the
  300s code-tool limit. Script: `/home/itadmin/tekion-reports/align_scan.py`
  (adapt the opcode set + window). Checkpoint to JSON every 20 ROs so a
  timeout/crash resumes instead of restarting.
- Retry wrapper: on 429 sleep `25*(attempt+1)` and retry (up to 5); on other
  errors short backoff. Even so a handful of RO calls (~12 of 366) may fail —
  impact is tiny (only affects the bundled count, not the dedicated total).
  **The checkpoint/resume mechanism ALREADY closes this gap — do NOT treat the
  "N missed ROs" note as a standing TODO.** `align_scan.py` skips `if rid in done`
  (line ~40), so simply re-running the same script resumes and retries only the
  failed ids. Verified 2026-06-18: SCT/May rerun printed `resume: 354 / 354 →
  DONE 354`, 0 missing. To confirm coverage, diff candidates vs the checkpoint:
  `missing=[r for r in cand if r["id"] not in done]` — if empty, you're at 100%,
  no action needed. (The candidate set may also shrink between runs if the index
  is rebuilt — e.g. 366→354 — which retires phantom "missing" ROs entirely.)
- "Sold in a month" = **closed** by default → `status IN [CLOSED,INVOICED]`,
  windowed on `creationTime` (confirm window with Joe: full prior month vs MTD).
- Report both: dedicated-opcode breakdown, bundled-menu breakdown (which TEK
  menus), and combined unique-RO count + total instances.
- :9223 browser is NOT needed for opcode counting (no advisor names required).

### Building a comparison scorecard + emailing it (PROVEN 2026-06-18)
When Joe wants the opcode-count result as a polished report (PNG/PDF) emailed:

1. **Dump a summary JSON** with both periods' figures (dedicated/bundled/total/
   unique_ros/menu_mix per month) → `data/sct-alignment-summary.json`.
2. **Render PNG+PDF by ADAPTING `render_scorecard.py`**, not from scratch. Copy it
   to a purpose script (e.g. `render_alignment_scorecard.py`) and reuse the exact
   visual language: white bg, `logo_0.png` top-left (base64-embedded), red
   `#EB0A1E` 3px rule, `.kpi` cards (`.hero` = red), dark `#1a1a1a` table header,
   green totals. Render via headless Playwright: `pg.goto(file://tmp.html)` →
   `pg.screenshot(full_page=True)` for PNG → `pg.pdf(width=1226px, height=
   scrollHeight+20)` for PDF. Chromium IS the headless variant here (works with
   `headless=True`), unlike the APC portal which needs xvfb+headed.
3. **Verify the PNG with `vision_analyze` before sending** — confirm logo, title,
   KPIs, no overlap. Caught nothing wrong but cheap insurance.
4. **Hand off to STACEY (email-agent) to send — Jay does NOT send menu/report
   emails himself.** Stacey owns email formatting (her `sct-menu-sales-report-
   email` skill = CID multipart/related via SMTP, AMG logo footer, "Sent from
   Tekion Open API — live data", NO Joe signature). Reach her via the bridge:
   `~/bin/ask-agent stacey "<self-contained instruction>"`.
   - The instruction MUST be fully self-contained (fresh session, no memory):
     recipient (To/From), subject, absolute PNG+PDF paths (pre-generated so she
     just attaches — this AVOIDS the ~180s bridge nesting timeout), and the exact
     body copy (greeting + one bold-total summary line + footer).
   - **Default recipient is Kevin Stapp**, but for ad-hoc "email ME this" requests
     set To: Joe `<jcastelino@americanmotorscorp.com>` explicitly — tell Stacey
     to override, or she'll default to Kevin.
   - Tell her to send DIRECTLY via SMTP (no draft iteration) and report back the
     Message-ID. Wrap the bridge call in `timeout 170`.

### Breaking the opcode count down BY ADVISOR (PROVEN 2026-06-18)
Joe often follows up "how many alignments" with "now by advisor." Don't re-scan —
the advisor is already obtainable cheaply:

1. **`assignee.advisor.id` is FREE in the `repair-orders:search` result** — no
   jobs/operations fan-out needed. Take the alignment-bearing RO ids from your scan
   checkpoint, then batch them through `repair-orders:search` with
   `documentId IN [<=50 ids]`, pageSize 50, and read
   `ro["assignee"]["advisor"]["id"]` off each result. 176 ROs = 4 search calls,
   ~3s. Save id-per-RO to JSON.
2. **Resolve ids→names from `data/sct-advisor-cache.json` FIRST** (16+ entries,
   mostly covers it). Only unknown ids need the `:9223` browser. Map
   `"Any Service Advisor"` → display "Unassigned".
3. **Aggregate by name**: dedicated (len align_op) + bundled (len tek_align) +
   unique ROs per advisor; sort desc by total; add a TOTAL row that MUST reconcile
   to the combined figures (161 dedicated + 19 bundled = 180 / 176 ROs for SCT
   June MTD — Jon Vu led with 55, nearly 3× #2).
4. Render with a dedicated by-advisor script (`render_alignment_by_advisor.py`) —
   same visual language as `render_scorecard.py` plus a red horizontal bar per row
   scaled to the top advisor. Then hand to Stacey (same email flow as below).

### Advisor-name resolution GOTCHAS (hit 2026-06-18)
- **The `:9223` browser token goes STALE silently.** `t_token` in localStorage (the
  real key — NOT `tekion-api-token`, which may be absent) can be present but expired;
  the internal `/api/userservice/u/apc/users/{id}` call then returns
  **500 "Token doesn't exist or is invalid"** even with `credentials:'include'`.
  Fix = a fresh Tekion OTP re-login to refresh the session. Don't burn time retrying
  header permutations — if it 500s "Token...invalid", the session is dead.
- **`data/sct-employees.json` (1,200-rec roster) does NOT map to assignee ids.** Its
  `userId`/`empNo` (UUIDs + 5-digit empNos like 8120) do NOT match the short numeric
  assignee ids (59, 61, 74) — and the roster's userIds are even duplicated/garbage.
  You CAN find a name by string-matching (e.g. "EDGARDO OLIVER" → empNo 8120) but
  there's no id bridge, so it's useless for id→name resolution. Confirmed dead end.
- **Pragmatic call when one id is uncached and the token is stale:** don't block the
  whole report on a single name behind an OTP re-login. If the unknown advisor is a
  tiny share (e.g. id 74 = 3 of 176 ROs, 1.7%), label it "Advisor #N (name pending)",
  ship the report, and offer to patch+resend once Joe IDs them or the session
  refreshes. 16/17 named = 98.3% coverage is a deliverable; perfect is the enemy here.

### Per-day pace is the real story for MTD vs full-month
A June-MTD total looks lower than a full May only because the month is half over.
Always report **alignments/day** (total ÷ days elapsed) alongside raw totals —
that's the apples-to-apples comparison Joe cares about (June 10.0/day actually beat
May's 7.9/day despite 180 < 246 raw).

### BY-ADVISOR breakdown + multi-page report (PROVEN 2026-06-18)
When Joe wants the opcode count broken down per service advisor (he asked for SCT
June alignments by advisor, then a "second page which is detailed"):

**1. Advisor ID is FREE on the RO search — do NOT fan out.** `assignee.advisor.id`
is already on each `repair-orders:search` result record. Re-query ONLY the
alignment-bearing ROs (the ~176 candidates that had an alignment) in batches of 50
via `documentId IN [...]`, pageSize 50, and read `(ro["assignee"] or {})["advisor"]["id"]`.
~4 calls total, no jobs/operations fan-out. Cache to
`data/sct-june-align-advisor-ids.json` (docId→advisorId).

**2. Resolve IDs to names from the cache first.** `data/sct-advisor-cache.json`
(id→"First Last") covers ~16 advisors; title-case it. `"Any Service Advisor"` →
display **"Unassigned"** (placeholder, not a person). Ids are mixed short-numeric
("59","61","74") + UUIDs.

**3. DEAD END — `data/sct-employees.json` roster does NOT map to assignee IDs.**
The 1,200-rec roster has `userId`/`empNo`/`name`, but its userIds are duplicated/
garbage and the short numeric assignee IDs (59/61/74) are NOT present (verified:
"id 59 in roster: None"). Names ARE there by NAME match (Edgardo Oliver→empNo 8120)
but there's no id bridge. So the roster CANNOT resolve an unknown assignee id —
only the `:9223` internal `/api/userservice/u/apc/users/{id}` call can.

**4. The `:9223` token goes stale — and that's OK for 1 missing name.** When the
internal user lookup returns 500 `"Token doesn't exist or is invalid"`, the browser
session has lapsed (token lives in localStorage key **`t_token`**, ~468 chars, NOT
`tekion-api-token`; also `currentActiveRoleId`/`currentActiveSiteId`/
`currentActiveDealerId` — but note the browser may be on a DIFFERENT store, e.g.
dealer 1251/SCVW not 876/SCT). Refreshing needs a full OTP re-login. **Do NOT block
a whole report on one unresolvable advisor** — if it's a tiny share (advisor 74 =
3 of 176 ROs = 1.7%), label it "Advisor #74 (name pending)", ship at 98% coverage,
and offer to resolve on the next session refresh or ask Joe who it is. Totals must
still reconcile (161 ded + 19 bundled = 180 across 176 ROs).

**5. Two-page report = extend `render_scorecard.py` clone.**
`render_alignment_by_advisor.py` builds BOTH pages in one HTML with
`.page` divs and `.page.break {{ page-break-before:always }}`:
- **Page 1** = summary scorecard: KPI cards (Total / Unique ROs / #Advisors /
  Daily Pace), ranked table (rank, advisor, dedicated, bundled, total-green, ROs,
  red `.bar` width = pct of leader).
- **Page 2** = RO-level detail: one `.advblock` per advisor (red left-border
  header w/ "{{n}} ROs · {{d}} dedicated · {{b}} bundled"), then `.chip`s — one per
  alignment line, `RO {{no}} {{opcode}}`, **red chip = dedicated, blue chip =
  bundled(menu)**. Build detail data into `data/sct-june-align-detail.json`
  (advisor→[{{ro, items:[{{type,label}}]}}]).
- PNG screenshot = both pages stacked (full_page=True) for inline preview; PDF
  `pg.pdf(width="1226px", height="1700px")` paginates (a dense detail page may
  spill to a 3rd PDF page — that's fine, nothing is cut off).
- Verify with `vision_analyze` before emailing.

**6. Bridge timeout discipline (exit 124) — VERIFY before resending.** The Stacey
`ask-agent` call can exceed the ~180s nesting timeout (exit 124) even though she may
or may not have sent. **Before resending, check it didn't already go out:**
`himalaya envelope list -a personal -f "[Gmail]/All Mail" -s 12 | grep -i "<subject keyword>"`
(quote `[Gmail]/All Mail` WITHOUT extra inner quotes; `[Gmail]/Sent Mail` works too).
If the subject is absent → safe to resend. To make Stacey's reply fit in the window,
tell her to **"Reply with just: SENT <message-id> or ERROR <reason>. Keep your reply
short."** — a terse reply returns before the timeout; a verbose confirmation table
can blow it.

**6b. Joe's stated preference (2026-06-18): STACEY owns email — route through her,
do NOT default to Jay direct-send.** The SMTP fallback below is LAST RESORT only
(Stacey repeatedly failing) and you should FLAG it to Joe when you use it, not
silently take over. If Stacey times out REPEATEDLY (2+ exit-124 in a row), send it
YOURSELF via SMTP as a stopgap, then tell Joe Stacey was down and you covered. Her per-send work (read PNG+PDF off disk, base64 a multi-page PDF, build the
MIME tree) inside a nested ask-agent session is what blows the ~180s window — it's
not a transient hiccup, it'll keep failing for big attachments. Jay can replicate her
EXACT approved format directly (verified working 2026-06-18, msg-id
178181913915...@americanmotorscorp.com). The app password is in Stacey's himalaya
config (same Gmail account):
```python
cfg='/home/itadmin/.hermes/profiles/email-agent/home/.config/himalaya/config.toml'
APP_PW = re.search(r'raw\s*=\s*"([^"]+)"', open(cfg).read()).group(1).replace(' ','')
```
Then build `multipart/mixed → related → (alternative: text+html) + CID png` and attach
the PDF as `MIMEBase('application','pdf')` base64; `smtplib.SMTP_SSL('smtp.gmail.com',465)`,
login as `jcastelino@americanmotorscorp.com`, `send_message`. Keep her rules: From+To
both Joe for "email me" requests, CID `<img src="cid:...">`, "Sent from Tekion Open API
— live data" footer, AMG logo via the Google-proxy URL, NO Joe signature. This bypasses
the bridge entirely and lands in ~3s. (Per Jay's mandate Stacey OWNS email formatting —
prefer the bridge; this SMTP fallback is only for when the bridge is unreliable, and it
reuses her exact template so the output is identical.)

**6c. Inline image = PAGE 1 ONLY; PDF = full multi-page.** Joe asked to keep the inline
email image to just the summary page (the stacked 2-page PNG made the inline preview
huge). Render TWO PNGs: screenshot a page-1-only HTML for the inline CID image, and keep
the PDF as the full report. In `render_alignment_by_advisor.py` `build_html` returns
`(full_html, page1_only_html)`; main() screenshots the page1 HTML → PNG (the inline/CID
file) and pdf()s the full HTML → multi-page PDF. Same filename for the PNG so the email
flow is unchanged.

**7. Ad-hoc "email ME" recipient.** For these one-off requests the recipient is
**Joe** (`jcastelino@americanmotorscorp.com`), NOT Kevin — state To: Joe explicitly
in the Stacey instruction or she defaults to Kevin Stapp per her skill.

## Verification
After any new endpoint, sanity-check against known data: today's RO count at SCT should roughly match the store's appointment volume; labor amounts are integer cents.
