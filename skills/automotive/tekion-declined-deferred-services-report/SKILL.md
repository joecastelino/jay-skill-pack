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

### ⚠️ BOTH nudges above can catch ZERO — the reliable fix is a REFRESH BUTTON (verified 2026-08-20)
Real run: `/tmp/tekion_rec_headers.json` was 401-stale, :9223 was parked on `/ro/opcode` (Opcode List,
2,066 results, authenticated, dealer 876). Armed the hook → **polled 12× / 60s and captured 0 XHRs**.
The `focus` nudge did nothing. The `history.pushState('/ro/opcode')` soft-nav ALSO did nothing —
**because the page was ALREADY on `/ro/opcode`, so it wasn't a route change at all**. If you use the
pushState trick, push a route the SPA is NOT currently on (check `/url` first) or it's a no-op.

**What worked instantly:** click a visible refetch control on whatever page is already loaded.
On the Opcode List page that's the toolbar **`Reset`** button:
```python
api("/click","POST",{"text":"Reset"})   # plain text click works, no /mouse needed
time.sleep(4)
api("/eval","POST",{"js":"JSON.stringify((window.__jayHdrs||[]).map(x=>x.u))"})
# -> ["https://app.tekioncloud.com/api/service-module/u/opcode/search"]
```
Headers captured off `opcode/search` **replay fine on `recommendation/search`** (re-confirmed) — any
`/api/` request with >3 headers carries the same auth set. So: DON'T navigate to the Deferred Services
report just to re-capture; hook + hit whatever Reset/Search/Refresh button is already on screen.

Merge (don't blind-overwrite) the new dict over the old file so no key is lost, then `json.dump` to
`/tmp/tekion_rec_headers.json`. Captured `dealerId` will be whatever store :9223 sits on (876 here) —
irrelevant, the pull scripts swap `dealerId`/`tek-siteId` per target store (pulled BC/1251 fine).

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

## Customer-level marketing lists — FILTER INTERNAL/WHOLESALE (learned 2026-09-03, BC)
When Joe asks for a CUSTOMER list (marketing/BDC follow-up) rather than a service ranking,
raw hits are contaminated by house/wholesale accounts — at BC the internal account
`americanmotorscorporation - 1251` was the #1 "customer" (204 lines / $81K), plus LITHIA
HYUNDAI wholesale rows. Filter with:
`re.compile(r"americanmotors|lithia|hyundai of fresno|wholesale|\(L0\d+\)|body shop|auto sales|motors? inc|dealer", re.I)`
against `customer.name` (BC 30d: 833 raw lines → 622 retail, $661K → $557K). Then roll up
per customer: (name,email,phone) key → lines, deferred $, vehicles set, last RO date,
sample services; rank by $. ~96% of retail customers have email, ~100% phone — good list.

## Trade-in ACQUISITION target list ("declined worth over $X" → buy the customer's car, built 2026-09-03 BC)
Joe's use case: customers who declined big repair bills are prime trade-in targets ("instead of the
$14K transmission, sell us the car"). Recipe on top of the standard pull:
1. Pull 30d DEFERRED hits (headers in /tmp/tekion_rec_headers.json often still live — test with a
   rows:5 probe before re-capturing).
2. Apply the INTERNAL/wholesale filter (regex above), then a SECOND commercial-account filter the
   internal regex MISSES — body shops / rental / dealers that are retail-named:
   `re.compile(r"collision|autoplex|auto\s*(center|centre|sales|body|group|plex)|sierra auto|towing|fleet|rental|leasing|\bllc\b|\binc\b|\bcorp\b|insurance|adjuster|copart|manheim|enterprise|u-?haul|city of|county of", re.I)`
   (BC caught: SIERRA AUTO, FRESNO AUTOPLEX, CALIBER COLLISION, Enterprise, A&E Industrial INC).
3. Roll up per VEHICLE: key = VIN (fallback "NAME:"+name); sum jobAmounts.totalAmount/100;
   threshold >= $1,000 (or Joe's figure). Keep: name/phone/email, year/make/model/VIN/mileageIn,
   total $, line count, CRITICAL count, RO#s + last roClosedTime, top 3-4 concerns with $ each.
4. Rank by total declined $. High-mileage blown transmission/engine rows top the list = the pitch.
5. Deliverables: landscape-letter PDF (weasyprint, /home/itadmin/tekion-reports/render_bc_trade_targets.py —
   BC black/gold wordmark, KPI cards: #vehicles / combined $ / critical lines / phone coverage;
   one row per vehicle with contact + top services) + working CSV with full contact columns.
   pdf2image/pdftoppm/pymupdf NOT installed — QA the layout by browser_navigate to the file:// HTML instead.
6. BC 30d reference: 821 raw hits → 622 retail lines ($556K) → 128 vehicles ≥$1K → 123 after
   commercial filter, $421K combined, 123/123 phones. Data saved
   data/bc-declined-1k-trade-30d{,-retail}.json + BC-Declined-Over1K-TradeTargets-30d.{pdf,csv}.
No GM Rewards filter needed for this cut ("regardless if they had GM rewards or not").

## "Rewards members who declined service" (GM Rewards cross-ref, asked 2026-09-03)
Rewards ENROLLMENT is NOT queryable anywhere in Tekion data (API or internal) when the
My GM Rewards 2.0 integration is NOT enabled at the store (BC verified not enabled —
see tekion-oem-rewards-integration). Don't burn time hunting an endpoint. Answer with
the 3 options: (1) request integration enablement from support@tekion.com/PSM (durable
fix — then enrolled members surface in Tekion and the combined report is automatable),
(2) get a rewards member export from GM Global Connect and match on name/email/phone
against this report, (3) deliver the full declined list and let BDC check rewards at
contact time. Joe accepted this framing.

## WEEKLY BC "Trade-In Acquisition Targets" report (Joe, 2026-09-03)
Joe's use case: buy customers' cars on trade when they decline big repair bills.
Report = per-VEHICLE rollup of DEFERRED lines, keep total >= $1,000, retail only,
NO GM Rewards involvement. Script (self-contained pull->render->email):
`/home/itadmin/tekion-reports/bc_declined_trade_weekly.py` — window = previous
Friday 00:00 PT -> Thursday 23:59:59 PT; cron `72085b2d49e1` Fridays 6 AM.
Emails via jay_mail SMTP: **To Art Markarian <amarkarian@blackstonegm.com>,
CC Ruben Estrada <Restrada@blackstonegm.com> + Joe**. Exit 2 = stale
/tmp/tekion_rec_headers.json (re-capture passively, re-run).
Key mechanics beyond the standard pull:
- Rollup key = VIN (fallback customer name); rank by total declined $.
- TWO filters: INTERNAL regex (house/wholesale) on every line + COMM regex
  (collision|autoplex|rental|leasing|LLC|Inc|towing|insurance|copart|manheim...)
  on the rolled-up name — commercial accounts are not trade targets.
- Each row: contact, VIN, mileage, RO#s + close date, top declined services w/ $,
  critical-line count. PDF (landscape letter, BC black/gold wordmark, weasyprint)
  + CSV. One-off 30d version: render_bc_trade_targets.py + data files
  BC-Declined-Over1K-TradeTargets-30d.* (30d ref: 123 targets / $421K).
- jay_mail multi-CC fix (2026-09-03): send_report now splits comma-separated cc
  strings into individual SMTP envelope rcpts — older copies passed the whole
  string as one rcpt and Gmail would reject multi-address CCs.

## \"Approval required for declined service over $X\" (Joe asked 2026-09-04) — NO NATIVE TEKION FEATURE
Verified live (BC, Approval Settings walkthrough 2026-09-04): Tekion has **no approval gate on\ndeclined/deferred work and no dollar-threshold trigger anywhere** in its approval workflow.\nWhat exists natively:\n- `Enable RO Approval flow` (Service Settings → General Setup) gates by **pay type only** —\n  adding jobs, changing pay types, and \"Recommendations require Approval before sending to the\n  Customer.\" No $ condition, and it fires BEFORE the customer sees the rec, not after a decline.\n- Once sent, customer approves/declines freely; a decline just falls into Deferred Recommendation\n  Rules (retention/resurfacing periods) — zero approver hook.\n- Approvers aren't even set in the UI — that requires an email to support@tekion.com.\nSo \"declined service ≥ $1,000 needs manager approval\" CANNOT be configured inside Tekion.\nThe real answer = build it externally on THIS skill's API (zero quota): poll DEFERRED hits every\n15–30 min, any line/rollup ≥ threshold → Slack/email the service manager (RO#, customer, vehicle,\nconcern, $, advisor), require acknowledgment or re-escalate to Joe, daily rollup of unacked items.\nOffered to Joe 2026-09-04 — pending his pick of stores/approver/channel before building.\n\n## Pitfalls
- Don't `curl` `document.body.innerText` through the terminal tool and pipe to python — big result hangs; use execute_code with urllib against :9223.
- The report UI itself shows Labor/Parts split; the API's `jobAmounts.totalAmount` is the combined deferred amount. `cpInvoice.laborAmount` etc. exist per-paytype if a split is needed.
- Report data updates DAILY (~11:46 PM last-updated seen) — it's not real-time; fine for 90-day windows.
