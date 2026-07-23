---
name: tekion-parts-appointments-recalls-only
description: Restrict Tekion Parts RO Sales appointment notifications to recall opcodes only (or any opcode subset) by mass-toggling the per-opcode "Consider for Parts preparation on Appointment" flag. Covers the Bulk Update UI, the underlying bulk-update API for scale, and full verification. Built for Glade at SCT 2026-07-20; applies to any store.
---

## Deployment log (durable state — memory tool was unavailable at save time)

- **SCT (876) — DEPLOYED 2026-07-21, FULLY COMPLETE 2026-07-23** (second-wave backlog sweep verified: 1,690→14, queue is recalls-only steady state; requested by Glade, SCT parts manager; Joe approved):
  - 922 active opcodes unchecked for "Consider for Parts preparation on Appointment" via Bulk Update.
  - Keep-list ON: **RECALL** (generic), **23TA13**, **23TC01**, **23TC05** — the only 3 Active opcodes in SCT's 106-opcode "Recalls" service type (50 Inactive / 53 Archived left checked, harmless).
  - Consequence: Parts gets NO appointment-prep notifications for anything non-recall at SCT (menus, tires, ToyotaCare pre-pull all silenced) — this was the explicit intent.
  - Maintenance caveat: **new opcodes default the checkbox ON** — future Toyota campaign codes (24TA.., 25TC..) auto-flow correctly, but any NEW non-recall opcode created later must be unchecked. A weekly sweep was offered to Joe but NOT yet scheduled.
- Other stores (BC/BT/TL/SV/AR/VC): not deployed; derive each store's recall opcode set fresh — never reuse SCT's list.
- Why not a list filter: Parts RO Sales → Appointments tab filter fields are only Appointment Date/Time, Appointment Status, Part Status, Counter Person — no opcode/recall field exists, so opcode-level config is the only clean path.

# Tekion — Parts Appointments for Recalls Only (parts-prep flag mass toggle)

Parts dept sees appointments in **Parts RO Sales → Appointments** ONLY for opcodes
whose **"Consider for Parts preparation on Appointment"** checkbox is ON
(Opcode Management → opcode → Parts section). It is **ON by default for ALL opcodes**
(KB0012918). Unchecking everything except the recall opcodes = the parts queue
becomes recalls-only. There is NO list-level recall filter on the Appointments tab
(filters = date/time, appointment status, part status, counter person only — KB0025115).

## Field name in API
`eligibleForPartPreparation` (bool) on the opcode object. Bulk section key =
`ELIGIBLE_FOR_PARTS_PREPARATION`.

## Procedure (verified SCT/876, 2026-07-20)
1. **Derive the keep-list.** Store may have a "Recalls" service type tab in
   /ro/opcode (SCT: 106 opcodes, only 3 ACTIVE). Also include the generic
   `RECALL` opcode (DIAGNOSTICS category) — Joe wanted it. SCT keep-list:
   `RECALL, 23TA13, 23TC01, 23TC05`. Confirm with Joe before executing.
2. **Learn one batch via UI** (optional but proves permissions): /ro/opcode →
   Status filter = Active → header select-all checkbox (selects only the 50
   LOADED rows → button shows "Bulk Update (50)") → Bulk Update → page
   /ro/opcode/bulk-update with Default|Overrides tabs → "Search or Select
   Attribute" dropdown → pick "Consider for Parts preparation on Appointment"
   (scrollIntoView + real /mouse click; typing into combobox doesn't work) →
   uncheck the value checkbox → Update → toast "Bulk Opcode updated successfully".
3. **Scale via API** — capture headers with an XHR hook on `opcode/search`
   (h includes tekion-api-token, roleId, userId, dealerId, tek-siteId...), then
   in-page fetch loops:
   - Pull all ACTIVE opcodes: POST `/api/service-module/u/opcode/search`
     body `{"pageInfo":{"start":N,"rows":200},"searchText":"","sort":[{"order":"DESC","field":"createdTime"}],"filters":[{"field":"status","values":["ACTIVE"],"operator":"IN"}],"nextPageToken":null,"searchFields":["OPCODE","DESCRIPTION","CONSUMER_SCHEDULING_NAME"]}`
     — read `opcode`, `eligibleForPartPreparation` from data.hits.
   - Turn OFF in chunks of 100 w/ 1.5s pacing: POST
     `/api/service-module/u/opcode/bulk-update/default` body
     `{"opcodesToUpdate":[...codes...],"sectionsToUpdate":[{"section":"ELIGIBLE_FOR_PARTS_PREPARATION","selectionOperator":null}],"opcode":{"eligibleForPartPreparation":false}}`
   - Turn keep-list back ON with same call, `true`. (UI batches likely flipped
     the keeps off — ALWAYS re-enable keeps at the end.)
4. **Verify**: re-pull all actives, assert `stillOn == keep-list` exactly.
   SCT result: 926 active, 922 off, 4 on.

## Pitfalls
- UI select-all only selects loaded rows (50) — virtualized list. API path is
  the real scale method.
- The attribute dropdown option must be clicked via /mouse at scrollIntoView
  coords; there is no typeable filter input exposed.
- Batches 1-2 done via UI WILL include recall opcodes if they're in the loaded
  rows — re-enable keeps afterward (step 3c) and verify.
- **New opcodes default to parts-prep ON**: future recall campaign codes flow
  automatically (good), but new non-recall opcodes will too — needs a periodic
  sweep (cron) or manual uncheck at creation.
- Inactive/Archived opcodes untouched (can't be added to appointments), but a
  reactivated opcode returns with the flag ON.
- Store-wide effect: parts stops getting prep notifications for EVERYTHING
  non-recall (tires, menus). Confirm the store understands before running.
- Related Scheduling Settings knobs (General tab): "Notify Parts department of
  appointment part request" (immediately vs N days before), hold-parts-on-missed
  duration. Advisors can also mark a single appointment "no part needed".

## Verifying it worked / handling "it's not working" complaints (verified SCT 2026-07-21)

Joe/parts manager WILL report "it's not working" the day after deployment because the
**Pending Requests backlog does NOT retroactively clear** and the **Appointments tab still
lists every appointment** (the flag kills the parts-prep REQUEST/notification generation,
not appointment visibility). Prove it with data before touching anything:

1. **Re-verify the config** (step 4's active-opcode pull): `stillOn == keep-list` exactly.
2. **Audit part-request generation** via the Parts RO Sales list API —
   POST `/api/parts/fulfilment/u/web/search` (in-page XHR replay with captured headers;
   capture them by arming an XHR hook on `fulfilment/u/web/search` and clicking the page's
   Refresh button on /parts/ro-sales/appointment-request). Useful filters:
   - `{"field":"assetType","values":["APPOINTMENT"],"operator":"IN"}` — appointment-request
     rows only (RO-sourced rows have sourceLineType JOB/RECOMMENDATION, assetType null in
     the default query).
   - `{"field":"createdTime","values":[epochMs],"operator":"GTE"}` / `"LT"` — window before
     vs after the deployment time.
   - `{"field":"appointmentPartsStatus","values":["PART_REQUEST_PENDING"],"operator":"IN"}`
     — the actionable "Pending Requests" bucket Glade works.
   Read per-hit: `assetNumber` (appt #), `createdTime`, `status`, `appointmentPartsStatus`
   (NO_PARTS / PART_REQUEST_PENDING / COMPLETED).
3. **The proof pattern**: before-window shows a mix incl. PART_REQUEST_PENDING; after-window
   shows 100% NO_PARTS and the newest PART_REQUEST_PENDING row's createdTime predates the
   flip. SCT result: 270 appts w/ 30 pending in the 48h before vs 113 appts / 0 pending after;
   all 374 queue items were pre-change (newest 12:03 PM, flip ~1 PM).
4. Backlog options: let requests age out as appointment dates pass, or mass "no part needed"
   sweep (offer, don't assume).

## Bulk-clearing the stale Pending Requests backlog (executed SCT 2026-07-21, 344/345 cleared)

The UI has NO bulk action — per-request resolve only. The API path (all in-page XHR replay w/ captured
headers `window.__HP` from any fulfilment call; 415 error = you set Content-Type twice, the captured
headers already include it):

1. Pull targets: POST `/api/parts/fulfilment/u/web/search` filters
   `status IN [PENDING,IN_PROGRESS]` + `appointmentPartsStatus IN [PART_REQUEST_PENDING]` +
   `assetType IN [APPOINTMENT]`, includeFields id/assetNumber/createdTime. (SCT: 349.)
2. Per request: `PUT /parts/fulfilment/u/web/<id>?action=LOCK` (response = full record) →
   collect live acquisition ids `partAcquisitions.filter(p=>!p.deleted).map(p=>p.id)` →
   `PUT /parts/fulfilment/u/web/v2/fulfil/<id>` body
   `{requestToCreate:[],requestToUpdate:[],requestToDelete:[...liveIds],requestToUnassociate:[],priceCodeDetails:[],sorPartRequests:[],shouldAutoFulfill:true,masterPartUpdateAcceptedIds:[],masterPartUpdateIgnoredIds:[],prepaidSORDetail:[],status:"DRAFT"}`
   → `?action=UNLOCK`. Record leaves the bucket (→ SUBMITTED/NO_PARTS, or PARTS_AVAILABLE if no live lines).
3. Pitfalls: `status:"FULFILLED"` in the body → 500 "Status must be DRAFT" (DRAFT+shouldAutoFulfill=true
   is the working combo). Records on CLOSED appointments → 500 "can not update fulfilment in CLOSED state"
   — unclearable orphans (SCT has 1, appt 170599), ignore. Deleting lines places NO holds/orders
   (verified holdQty=0 after). Run the loop IN-PAGE async writing progress to window.__sweep and poll —
   345 records ≈ 4.5 min at 250ms pacing.
4. Verify: re-run the step-1 query (count → 1 orphan) + reload page and read the "Pending Requests" tile.

Detail-page gotchas while investigating: clicking a row opens
/parts/ro-sales/details/appointment-request/<fulfillmentId> and **LOCKS the appointment for
other users** — navigate back to the list promptly to release. Appointment detail JSON =
GET `/api/parts/proxy/u/fulfillment/<id>` → `{appointmentRequestDetails, appointmentDetails,
repairOrderDetails}`.

## CRITICAL: the flag alone generates ZERO requests — opcodes need a part attached (solved SCT 2026-07-21)

A Pending Request fires ONLY when (flag ON) **AND** (the job has requested parts). Recall opcodes
typically have NO parts attached (campaign parts are VIN-specific), so recall appointments book with
`appointmentPartsStatus: NO_PARTS` and **silently never appear** in Glade's queue. Symptom: Joe reports
"appointment 267104 has recall 25TA01, why doesn't it show up?" — config verifies fine, but the
appointment shows requested parts: 0.

**Fix = attach a FREE-TEXT placeholder part to each keep-list opcode — NOT a real part-master
record.** (Corrected 2026-07-21 after live test: mechanism below.)

**RESOLVED vs UNRESOLVED is what drives the queue.** The Pending Requests bucket is literally a
"parts dept must resolve these lines" workflow:
- **Free-text opcode part** (the dropdown `Create "NAME"` inline option; no part number, no
  inventory record) → acquisition lands with `sourceRequestedDetail.partNumber: null`,
  `partResolveType: null`, `priceType: COMPUTED_PRICE` → **UNRESOLVED → fires a Pending Request**.
  This is exactly how the pre-change TXM menu lines flooded the queue.
- **Real part-master part** attached to the opcode → acquisition arrives
  `partResolveType: RESOLVED`, `priceType: SOURCE_FIXED` → auto-resolved → **silently NEVER
  appears in Pending Requests** (Joe's live test appt 268528 proved this: acquisition created,
  queue stayed empty).

So: on /ro/opcode/edit/<OP> → Parts table blank row → type e.g. `RECALL PART - SEE VIN` → pick the
**`Create "..."` option** (ignore any real catalog matches) → qty 1, $0.00 → Update → confirm PUT
200 via XHR hook + hard remount (/home → back) showing the row persists.

**Pitfalls found:**
- **Do NOT use a real part-master record here** — it auto-resolves (see above). We built one
  (`RECALL PARTS`, non-stock, src 99, $0) on Joe's hunch, attached it, and requests skipped the
  queue; reverted to free-text. If you DO ever need a part-master: Create Part form traps =
  `#costPrice`/`#listPrice` are hidden-below-fold mandatory fields (Save fails "Please check the
  form errors" until both set), and the part-number downshift combobox needs char-by-char native
  value-setter typing then clicking its `Create "..."` option.
- **Verify a test booking via the fulfilment search API**, not just the tile: POST
  `/api/parts/fulfilment/u/web/search` with `searchText:"<apptNo>"` + `assetType IN [APPOINTMENT]`
  → hit's `partAcquisitions[].sourceRequestedDetail.partResolveType` tells you instantly whether
  it will queue (null/unresolved) or was swallowed (RESOLVED). The tile query itself (capture by
  clicking the tile) keys on `metaInformation.newPartRequestMetaInfo.acquisitionIdsSize GT 0` +
  status/appointmentPartsStatus filters — hand-PUTting that meta onto a fulfilment record 400s
  (`unexpected.error`); you cannot force a record into the bucket, the generation path must do it.
- **Legacy OEM-imported campaign opcodes (SCT: 23TA13/23TC01/23TC05) 500 on ANY update** — even
  clicking Update with ZERO changes returns `PUT /api/service-module/u/opcode/v2/<id>` →
  `500 {"status":"failed","errorDetails":{"params":[]}}`. Diagnostic: arm an XHR hook, click Update
  on the untouched form; if that 500s, the record itself is broken (malformed legacy fields), not
  your edit. Sanitizing suspect body fields (null labor times, trailing-space oemOpcodes,
  partsSalePricingType) did NOT fix it; direct GET on the v2 endpoint also 500s for these records.
  → Needs Tekion support; meanwhile attach the part to the generic RECALL opcode (which is what
  advisors actually book on) and move on.
- **No retro-generation**: appointments booked BEFORE the part was attached stay NO_PARTS. Advisor
  re-saving the appointment (or API re-trigger) regenerates. Verify end-to-end on the next NEW
  recall booking.
- The success-toast check `updated successfully` can miss; trust the hooked PUT status + hard
  remount re-read instead.

## CRITICAL #2: use a FREE-TEXT placeholder, NOT a real part-master record (solved SCT 2026-07-21)

A REAL inventory part (created in part master) attached to the opcode gets **auto-RESOLVED** at booking
(`sourceRequestedDetail.partResolveType: "RESOLVED"`, `priceType: "SOURCE_FIXED"`) — no parts action
needed → the request NEVER hits Pending Requests. The queue is literally an "unresolved parts" worklist.
The free-text `Create \"NAME\"` inline placeholder (no partNumber, priceType COMPUTED_PRICE) stays
UNRESOLVED → lands in Pending Requests, exactly like the TXM menu placeholders that flooded the queue
pre-change. **So: attach the free-text placeholder (e.g. \"RECALL PART - SEE VIN\"), and do NOT link a
part-master record.** (The part-master detour was tried and reverted; a real record is only needed if
the opcode PUT 500s without one — it didn't for RECALL.)

## CRITICAL #3: the notify-timing setting hides requests until N days before the appointment

Even a correctly-generated request is created with `invisible: true` (on the partAcquisition) when
Scheduling Settings → General → \"Notify Parts department of appointment part request few days before
scheduled time\" = N days and the appointment is further out than N. The Pending Requests tile query
excludes invisible rows → \"still not working\" symptom on test bookings made ≥N days out. Check
`partAcquisitions[].invisible` in the fulfilment search hit to diagnose. Fix/trial: flip the
\"...immediately\" ant-switch ON (same General tab), Save (PUT scheduling/u/settings/appointment 200 +
Success toast), then Summary tab → Run Scheduler. New bookings then surface instantly (verified by Joe
live); EXISTING hidden requests do NOT re-evaluate immediately — they surface as their window arrives
(or after overnight scheduler). Note: the setting is store-wide for all parts-prep-flagged opcodes.

## Final working SCT recipe (all four pieces required — do them in THIS order)
1. Parts-prep flag ON for keep-list only (bulk API method above).
2. Free-text placeholder part on each SAVABLE keep-list opcode (RECALL; the 3 legacy campaign codes 500).
3. Notify-immediately ON (or accept the N-day window as the store's workflow).
4. Backlog bulk-cleared LAST — after the notify flip + overnight scheduler, so hidden `invisible:true` requests have surfaced (see SECOND WAVE section).

## THE FINAL GATE: N-days-before notify window hides requests as `invisible:true` (solved 2026-07-21 PM)

Even with (flag ON) + (placeholder attached) + (acquisition generated), the request will NOT appear
in Pending Requests until close to the appointment date. Joe's second test appt **268534** (free-text
placeholder active, acquisition generated correctly) still "didn't show" — because its acquisition
carried **`invisible: true`** and the tile query filters `{"field":"invisible","operator":"NIN",
"values":[true]}`.

Controller: **Scheduling Settings** (`/dse-v2/scheduling-settings` → General tab) →
**"Notify Parts department of appointment part request few days before scheduled time"** — SCT = **3
days**, with the sibling toggle "…immediately" OFF. Requests generate at booking time but stay
invisible until N days before `appointmentTime`, then auto-surface in Glade's queue. 268534 was booked
5 days out → correctly hidden; would surface Jul 23. This ALSO retroactively explains why test appts
"never appeared" during earlier debugging — always compare appointmentTime vs the window before
concluding generation is broken.

**Correct diagnostic order for "I booked a recall appt and it's not in the queue":**
1. Fulfilment search on the appt number — **WITHOUT the assetType filter** (with
   `assetType IN [APPOINTMENT]`, brand-new records sometimes return 0 hits; the bare
   `{"searchText":"<apptNo>",...}` query found 268534 fine). Response key = `data.hits`.
2. Hit exists + `partAcquisitions` non-empty → **generation WORKS**. Read the acquisition's
   `invisible` flag and compare the appt's `appointmentTime` (epoch ms in
   sourceSearchDetail.appointmentTime) against the store's notify-days setting. Hidden-by-window =
   working as configured, not a bug.
3. Only if partAcquisitions is empty is it a generation failure (flag off / no part on opcode).
4. `appointmentPartsStatus: NO_PARTS` on the summary row does NOT mean no request — 268534 showed
   NO_PARTS while carrying a live invisible acquisition. Trust partAcquisitions, not the label.

Policy decision for the store: keep the N-day window (queue = near-term appts only, parts ordered
just-in-time) vs flip "notify immediately" ON (every recall booking surfaces at once). Surface the
choice to Joe — SCT left at 3 days pending his call. To test end-to-end same-day, book the test
appointment WITHIN the window (≤3 days out at SCT). (SCT was later flipped to immediately — see
SECOND WAVE below for the consequence.)

## SECOND WAVE: flipping notify-immediately ON surfaces the ENTIRE hidden backlog (hit SCT 2026-07-22)

Turning "notify immediately" ON does NOT only affect new bookings long-term: the **overnight
scheduler re-evaluates all existing `invisible:true` acquisitions** and surfaces them. SCT woke up
to **1,690 pre-change pending requests** flooding the queue (appt dates spanning months into the
future) the morning after the flip — Joe reported "I see more than just recalls" while looking at
a future date. The original backlog sweep (345) had only cleared what was VISIBLE at sweep time;
the N-day window was hiding the rest.

**Diagnostic proof pattern** (run before touching anything): pull all
`PART_REQUEST_PENDING + status IN [PENDING,IN_PROGRESS] + assetType APPOINTMENT` rows and bucket
by `createdTime` vs the flag-flip timestamp. SCT result: 1,690 created-before / **0 created-after**
→ config working, pure legacy backlog. Sample rows confirmed free-text placeholders like
"oil and filter" created at original booking time (Jan/Feb).

**So the full deployment sequence is: (1) flags, (2) placeholder part, (3) notify-immediately,
(4) THEN the backlog sweep — sweeping before the notify flip leaves the invisible remainder to
resurface.** If done out of order, just re-run the sweep on the second wave.

**Improved sweep loop (use this version)** — same LOCK → fulfil(DRAFT, delete live ids) → UNLOCK
per record, plus a **recall safety-skip**: after LOCK, inspect the record's live acquisitions and
if any `partName/partNumber/opcode` contains RECALL/23TA13/23TC01/23TC05 (store's keep-list),
UNLOCK and skip instead of clearing — protects legit recall requests mixed into the backlog.
Collect target ids first (paginate 200/page into a Map by id), run in-page async at 250ms pacing
writing progress to `window.__sweep` ({done,ok,recallSkipped,noLive,errors,errSamples}), poll from
outside. Throughput ≈ 1.4 records/sec → 1,690 ≈ 15–20 min. Expect a few
"can not update fulfilment in CLOSED state" 500s (closed-appointment orphans — unclearable,
harmless, count them and move on).

**Second-wave sweep VERIFIED COMPLETE at SCT 2026-07-23**: 1,690 → 14 remaining.
1,678 cleared, **11 recall-skipped preserved** — all carrying the "RECALL PART - SEE VIN"
placeholder on NEW post-flip bookings (268xxx appt series) = end-to-end proof the recalls-only
pipeline generates correctly. Stragglers: 1 CLOSED-appt orphan (170599) + **2 `noLive` records
(no live part lines — the fulfil(delete) step has nothing to delete, so they stay visible in
the queue as cosmetic leftovers; clear manually via the UI if the parts manager cares)**.
SCT deployment is DONE — steady state = queue shows only recall requests.

Also note: the fulfilment search hit's summary `partAcquisitions` often has empty
opcode/partName fields — to see what a request actually is, GET
`/api/parts/proxy/u/fulfillment/<id>` and read `appointmentRequestDetails.partAcquisitions[].sourceRequestedDetail`.

## KB references
KB0012918 (configure parts prep + opcode exclusion + bulk update note),
KB0012911 (order/hold/fulfill on appointments), KB0021854 (Part Status filter),
KB0025115 (appointment filters list).

## Related skills
tekion-scheduling, tekion-sitemap, tekion-kb-search-scrape, persistent-browser-server
