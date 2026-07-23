---
name: tekion-declined-deferred-services-report
description: Pull declined/deferred services (recommendations customers said no to) for any/all AMG Tekion stores via the internal recommendation/search reporting API. Powers "most declined service", declined-services marketing lists (with customer phone/email), and deferred-dollars opportunity reports. Zero OpenAPI quota.
triggers:
  - declined services
  - deferred services
  - most declined service
  - declined recommendations
  - deferred recommendations report
---

# Tekion Declined/Deferred Services — Internal Reporting API

## What this solves
"Most declined service last 90 days", "declined services with customer contact info for marketing", "deferred dollars by store/advisor". The OpenAPI repair-orders endpoints return SOLD operations ONLY — declined/deferred recommendations are NOT in the public API (verified twice, 2026-06-17 and 2026-07-08). The data lives in the **Deferred Services** Standard Report (`/core/reports/service/deferredServices`) and its backing internal API, which this skill calls directly.

## The endpoint (cracked 2026-07-08 via XHR hook on the Deferred Services report)
```
POST https://app.tekioncloud.com/api/service-module/u/reporting/recommendation/search
```
Body:
```json
{"reportName":"RO_RECOMMENDATIONS","reportGroup":"RECOMMENDATION",
 "sort":[{"field":"roClosedTime","order":"DESC"}],
 "filters":[
   {"operator":"BTW","values":[<startMs>,<endMs>],"type":"roClosedTime","key":"roClosedTime","field":"roClosedTime"},
   {"field":"status","values":["DEFERRED"],"operator":"IN"},
   {"field":"comebackCompleted","values":[true],"operator":"NIN"}],
 "pageInfo":{"start":0,"rows":200},"nextPageToken":null}
```
- `status` values: `DEFERRED` (declined). Other statuses exist (approved/recommended) — the report UI filters DEFERRED.
- Response: `data.reportData.{count, hits[]}`.
- Each hit: `concern` (free-text service description), `opcodes[]`, `severity` (CRITICAL/CAUTION/Failed...), `jobAmounts.totalAmount` (**CENTS** — /100!), `customer.{name,email,phone}`, `vehicle.{vin,year,make,model,trim,mileageIn}`, `roNo`, `roClosedTime`, `primaryAdvisorId`, `type` (MPI), `universalId`, `approvedOrDeferredDetails.comment`, `followUpTime`.

## Auth — plain urllib with captured headers, WORKS ACROSS ALL STORES
Captured axios headers replay fine from Python outside the browser (same as bin APIs). **Header swap alone switches stores — NO UI dealer switching needed**: set `dealerId: <id>` and `tek-siteId: -1_<id>`. Verified all 7 (876/1251/1249/826/1092/6195/1891) return store-correct counts with one captured token.

Capture once per session:
1. :9223 authenticated browser → navigate `/core/reports` → click "Deferred Services" row (scrollIntoView first, it's below fold; category = Service).
2. Install XHR hook filtering `recommendation/search`, capture `this.__h` (headers dict set via setRequestHeader override) — save to `/tmp/tekion_rec_headers.json`.
3. Trigger a refetch by clicking the report's `Reset` button (top toolbar, ~x638,y164).

**STALE-TOKEN REFRESH — PASSIVE capture, zero navigation (proven 2026-07-12):**
`/tmp/tekion_rec_headers.json` goes 401-stale after a session refresh. If the
shared :9223 session is BUSY (someone mid-edit — do NOT navigate away), re-capture
without touching the page: arm a hook overriding `XMLHttpRequest.prototype.open/
setRequestHeader/send` that stashes `{u, h}` into `window.__jayHdrs` for ANY
`/api/` request with >3 headers, then just poll — the idle app fires its own XHRs
(heartbeat/part-lookup) within ~1-2 min. Same header dict works for other internal
GETs too (e.g. menu config `GET /api/service-module/u/opcode/service-menu/<id>`;
note `/u/serviceMenu/<id>` is 404). Swap `dealerId`/`tek-siteId` per store as usual.

Header keys needed: `tekion-api-token, roleId, userId, tenantname, dealerId, tek-siteId, original-userid, original-tenantid, clientId, locale, program, applicationId, subApplicationId, productIds, Content-Type, Accept`.

## Pagination — ES 10K offset cap, use TIME-CURSOR not offset
`pageInfo.start` offset pagination **breaks past ~10,000** (`reportData` comes back null → the naive loop crashes). Also offset+sort loses a few rows. Working pattern (script `/home/itadmin/tekion-reports/deferred_services_90d.py`):
- sort `roClosedTime DESC`, always `start:0, rows:200`
- after each page, set window upper bound `hi = min(roClosedTime of page)` and re-query `BTW [start, hi]`
- dedupe by `universalId`; stop when hits empty / short page / seen>=count / 3 stalls.
- ~0.35s pacing; each store finishes in seconds-to-a-minute. Whole fleet (40K rows) ≈ 2 min. Run as background terminal job.
- Expect ~99% capture (boundary-timestamp rows overlap-fetch mostly recovers; a fraction of a % loss is fine for aggregates — note it if precision matters).

## PART NUMBERS per declined line (cracked 2026-07-14, TL filters/wipers pricing)
Search hits have NO parts. Fetch `GET /api/service-module/u/ro/{roId}` (same headers; note it's `/u/ro/`, NOT `/u/repairorder/`) → `data.recommendations[]` keyed by the hit's `id` → `operations[].parts[]` = `{partLineId, partName, partNumber, quantity, unitPrice(CENTS), status}`. Gotchas: `partNumber` is often NULL — real number lives in `partLineId` as `ADHOC_<PARTNUM>` (strip `ADHOC_`) or as the prefix of `partName` before " - ". A bare `ADHOC_AZ` = advisor typed no part number (flag as UNKNOWN). Cabin-filter lines often carry TWO parts (OEM 87139-x + "7073"). CORRECTED 2026-07-14: 7073 is NOT a charcoal/premium filter — TL inventory shows it's "Frigi Fresh Unscented" (BG FRIGI-FRESH A/C deodorizer), brand/oemCode=OTHER, partSourceType=dealer, aftermarket BG product (cost $15.05/list $25.13 at TL). The pairing = OEM filter + BG deodorizer bundled as the premium cabin service. Genuine Toyota premium charcoal filters are the 87139-YZZ series. Also: withPart/search accepts a partNumber filter ({"filters":{"partNumber":{"key":"partNumber","values":["7073"]}}}) — the way to find hex partIds for dealer-sourced parts; dealer cost lives at partInventory.inventoryPartDetail.cost (DOLLARS, not cents, in this API). Fan-out ~0.5s/RO incl pacing; 133 ROs ≈ 70s. Zero OpenAPI quota.

## Segmenting by MOBILE SERVICE (or Wait/Drop-off/Lyft) — cracked 2026-07-20
"Which deferred recs came from mobile service?" — the recommendation hits themselves CANNOT answer this:
- `serviceMode` is ALWAYS "REGULAR" (filtered NIN REGULAR = 0 rows at all 7 stores; MOBILE/MOBILE_SERVICE values = 0). Dead end.
- `serviceTypeIds` has no Mobile type (SCT list cached at `~/tekion-reports/data/sct-service-types.json` — Main Service, Maintenance Service, Recalls, etc., no Mobile).
- `roDepartmentId` values (`876_department_03`, hex ids) have NO resolvable department endpoint (all guessed `/department/list` paths 404).

**The working method = RO TRANSPORTATION TYPE via OpenAPI (zero internal-API guessing):**
1. Collect unique `roId`s from the deferred hits.
2. Batch `POST /openapi/v4.0.0/repair-orders:search` with `documentId IN [<=50 ids]` — each result carries `transportation.id` for FREE (no fan-out).
3. `GET /openapi/v4.0.0/transportation-types` (bare GET, no :search) lists the store's types by name: SCT has DROP OFF / WAIT / TXM-WAITING / Lyft / **MOBILE** (`c138acaf-7478-45b4-8fc2-edc94fe8d7c4`) / TXM-DROPP OFF. IDs are per-store — always fetch the list, match on `name`.
4. Filter deferred hits to ROs whose transportation id == the MOBILE type id.
Cost: 1,449 ROs = 29 search calls ≈ 22s. June 2026 SCT result: 35 deferred lines / 24 mobile ROs / $9,300.85 (pattern: cabin+engine filters ~$72 each dominate count; tires/suspension dominate $).
Same method segments deferred recs by Waiter vs Drop-off vs Lyft.

## Passive header re-capture on a fully IDLE page (extends the stale-token section)
If the armed hook catches nothing in ~2 min (page truly idle, e.g. parked on opcode bulk-update), don't keep waiting:
1. Nudge React Query: `window.dispatchEvent(new Event('focus'))` + redefine `document.visibilityState='visible'` + dispatch `visibilitychange`.
2. Still nothing → SPA soft-nav (keeps hooks alive): `history.pushState({},'','/ro/opcode'); window.dispatchEvent(new PopStateEvent('popstate',{state:{}}))` — the route change fires XHRs within seconds (captured `groupFilter/OPCODE_LIST/filter/preference/list` headers this way; any >3-header /api/ request works for the recommendation/search auth).
Also note :9223 /eval takes `{"js": "..."}` (key is `js`, not code/expr/expression).

## Aggregation gotchas
- **$ are CENTS** — divide by 100 (forgetting = $27.8M cabin filters).
- `concern` is FREE TEXT — same service appears under many wordings (e.g. SCT writes "CUSTOMER AUTHORIZED REPLACEMENT OF CABIN AIR FILTER", BT writes "REPLACE CABIN AIR FILTER"). For "most declined service" bucket with regex categories (cabin filter / engine filter / tires / alignment / brakes / battery / fluid exchanges / wipers...), don't rank raw strings.
- `opcodes[]` is often just `REC` (generic recommendation opcode) — not reliable for categorization; use concern text.
- Advisor = `primaryAdvisorId` → resolve via OpenAPI `/users/{id}` (tekion-openapi-repair-orders skill).

## Reference result (2026-07-08, 90-day window)
40,603 deferred lines, $17.5M fleet-wide. #1 by count = cabin air filter (5,352). #1 by $ = tires ($2.59M). Store volumes: BT 13.8K, TL 9.4K, SCT 9.0K, BC 2.9K, SV 2.9K, VC 2.6K, AR 461.
Outputs: `~/tekion-reports/data/deferred-services-90d.json` (per-store top-25 + fleet top-40) and `...-raw.jsonl` (row-level: store, ro, concern, severity, amt, advisorId, roClosedTime).

## Related Standard Reports (same module, likely same API pattern)
"Advisor Top Recommendations" (recommended/sold/deferred by advisor + opcode), "Advisor Recommendations" (conversion metrics), "Advisor Recommendation Channel Report". If Joe wants advisor conversion rates, hook those reports the same way.

## Per-store report + email delivery (proven BC, 2026-07-08)
When Joe asks for a single-store cut ("just Blackstone GM"):
- Filter the raw jsonl cheaply: `[json.loads(l) for l in open(RAW) if '"store": "BC"' in l]` — no re-pull needed.
- Renderer: `/home/itadmin/tekion-reports/render_bc_declined_90d.py` — Blackstone black/gold light format (brand header, 4 KPI cards: declined lines / deferred $ / flagged Critical / #1 named service, ranked category table with bars). Outputs PNG + PDF + CSV to `data/BC-Declined-Services-90d.*`. Clone + reskin for other stores (SCT/TL red, etc.).
- **RANKING GOTCHA (vision QA caught this):** the "Other / misc" bucket is usually the LARGEST raw bucket (~30-42%) — if you sort purely by count, "Other" ranks #1 and the report looks broken/lazy. Sort with `key=lambda kv: (kv[0].startswith("Other"), -kv[1]["n"])` to pin Other to the bottom, scale bars off the largest NAMED category (cap at 100%), and make the #1 KPI card show the top *named* service. Always vision_analyze the PNG before emailing.
- Store-specific "Other" mining is valuable: at BC the uncategorized pile revealed declined **mileage service menus** (7.5K/15K/30K/45K/60K Basic Normal ≈ 258 declines), **TPMS/sensors**, **TEAR DOWN** (17 declines but $86K), diesel fuel filters — add these as categories for GM stores.
- Severity is worth surfacing: `severity == "CRITICAL"` count per category (BC: 808 of 2,903).
- Email via Stacey: helper lives at `/home/itadmin/.hermes/profiles/jay/home/bin/ask-agent` (the `/home/itadmin/bin/ask-agent` path does NOT exist — exit 127). Pass the instruction via a temp file (`"$(cat /tmp/msg.txt)"`) to avoid quoting hell. For "email ME" = From==To==Joe: demand base64 data-URI inline PNG (not CID), PDF+CSV attachments, and the imaplib INBOX append — then verify in INBOX with himalaya. Expect TWO inbox copies (SMTP delivery + append) — tell Joe it's the self-send quirk, both identical.

## Pitfalls
- Don't `curl` `document.body.innerText` through the terminal tool and pipe to python — big result hangs; use execute_code with urllib against :9223.
- The report UI itself shows Labor/Parts split; the API's `jobAmounts.totalAmount` is the combined deferred amount. `cpInvoice.laborAmount` etc. exist per-paytype if a split is needed.
- Report data updates DAILY (~11:46 PM last-updated seen) — it's not real-time; fine for 90-day windows.
