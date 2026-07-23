---
name: tekion-customer-email-fraud-scan
description: Detect CSI/survey-manipulation fraud by scanning Tekion customer records for redirect emails via the OpenAPI customer-search endpoint (GET /customers?email=). Two modes — KNOWN-EMAIL mode scans all 7 AMG stores for a suspect email Joe names (returns every record currently pointing at it + lastUpdateTime timeline); DISCOVERY mode pages a store's whole customer base to find ALL emails shared across 3+ unrelated customers, then attributes each to the RO-creating advisor (single-advisor-lock = bad actor) to surface ADDITIONAL bad actors beyond the first. Use when Joe says an advisor swapped customer emails to redirect surveys/CSI, asks "how many customers have email X" / "when was this changed", or "find anything else / who else is doing this." Covers the count-param 400 trap, the floor-not-total caveat, the no-modifiedBy / no-change-history API limits, the exclude-staff-domain+dummy-placeholder rules, and the >=85% single-advisor-lock classification threshold.
---

# Tekion Customer-Email Fraud Scan (CSI / survey manipulation)

## When to use
An employee (usually a service advisor) is suspected of editing customer email
addresses in Tekion to a handful of addresses **they control**, so the
manufacturer CSI/survey goes to them instead of the real customer (lets them
self-rate, or kill a bad survey). Joe gives you one or more suspect email
addresses and asks "how many times / how many customers / when."

This skill finds **how many customer records CURRENTLY carry each suspect email**,
across all 7 stores, with a per-record **lastUpdateTime** timeline. It does NOT
(and via API cannot) name the employee or count reverted edits — see Limits.

## Source of truth
Tekion **public OpenAPI** customer search — `GET /openapi/v4.0.0/customers`.
- No browser, no OTP, no caliber lock. Uses the OpenAPI app token.
- Client: `/home/itadmin/tekion-api/tekion_client.py` (`load_config`, `get_token`, `api_get`).
- Dealer IDs live in `tekion-api/config.json` -> `dealers` (ar/bc/bt/st/sv/tl/vc).
- Spec: `/home/itadmin/dealerdetail/specs/apis/customer__get-customers.json`.

## The customer search endpoint
`GET /openapi/v4.0.0/customers?email=<addr>` — query params include:
`email, lastName, firstName, phone, companyName, id, customerType, search`
(general partial match), plus time windows `startTime/endTime` (modified, 7-day
lookback default) and `createdStartTime/createdEndTime`, and `nextFetchKey`.

Response: `{data:[...], meta:{total,...}}`. Each row is an
`OpenApiCustomerResponseDTO`:
`id, displayId, status, customerDetails, insurances, vehicles, creationTime, lastUpdateTime`
- `creationTime` / `lastUpdateTime` = **epoch MILLISECONDS** (int64).
- Email lives at `customerDetails.emailCommunications[].email` (no per-field stamp).
- Name at `customerDetails.name.{firstName,lastName}` (individual) or `businessName`.

## CRITICAL GOTCHA — do NOT send `count`
Sending `count` (or other pagination params) **with** `email` returns
`HTTP 400 invalid.input.error "Invalid QueryParam"`. **`email` alone works and
returns 200.** Just send `{"email": addr}`. (The whole-fleet scan once returned
400 on all 7 stores purely because `count:100` was tacked on.) An empty result is
`200 {data:[], meta:{total:0}}` — that's "no current matches," not an error.

## Procedure
1. Confirm the suspect email(s) with Joe.
2. Run the all-stores scan (see scripts/scan_email.py): for each dealer code,
   for each email, call `GET /customers?email=<addr>` (email param ONLY).
   Print `total` per (store,email). ~0.4s sleep between calls is plenty (no 429s
   seen at this volume).
3. For the store(s) with hits, pull detail: name, displayId, status,
   creationTime, lastUpdateTime. **Sort by lastUpdateTime** = the tamper timeline.
   Convert ms->Pacific (PDT = UTC-7; use -8 in winter / proper tz if exact).
4. Report: per-email count, store, the timeline, and FLAG clustering — e.g.
   N records stamped the **exact same minute** after hours = a bulk-edit session
   (strong smoking gun). Save raw + detail JSON under `/home/itadmin/` (persists;
   `~` is wiped on daily reset).

## Reporting to Joe
- Lead with the count per email + which store (almost certainly ONE store — that
  localizes the bad actor).
- Give the lastUpdateTime timeline and call out same-minute / after-hours clusters.
- State the two caveats EVERY time (see Limits) — never let the count read as the
  full total or as proof of who.
- Offer next steps: (a) go into the Tekion UI customer audit/activity log to get
  WHO + the reverted edits; (b) build an Excel of the hits via Stacey for HR/compliance.

## LIMITS — be honest, do not overstate (Joe rejects overstated claims)
1. **Count is a FLOOR, not the total.** The API only sees records *currently*
   pointing at the email. The scheme is swap-in -> survey fires -> swap-back to the
   real customer; every reverted record is INVISIBLE to this scan. True count is
   higher (often much higher).
2. **No `modifiedBy` / `updatedBy` field anywhere** in the customer schema. The API
   gives WHEN (caveated), never WHO. Naming the employee requires the Tekion UI.
3. **`lastUpdateTime` is record-level, not field-level.** It reflects the *last*
   touch to the whole record — if a phone/address/RO-link changed after the email
   edit, the stamp is that later change, not the email change.
4. **No change history / no old->new diff** via API. Current state + one timestamp only.
5. The full count (incl. reverted) and the employee identity live in the **Tekion UI
   customer profile audit/activity log**, NOT the API. Whether that log exists at
   field level was NOT yet confirmed — go look in the UI, don't guess (NEVER-GUESS rule).

## DISCOVERY MODE — find the OTHER redirect emails (and OTHER bad actors)
The known-email scan above only finds emails Joe already named. The high-value
follow-up (verified 2026-06-29) is to discover ALL redirect emails AND surface
additional employees doing the same thing. Guessing email variants of one suspect
(joesclassics1/3@, work email, etc.) is a DEAD END — it found nothing. The winning
method is fingerprint discovery + per-email advisor attribution:

### Step 1 — fleet/store-wide shared-email scan (the fingerprint)
Page the store's ENTIRE customer base over a 6-month window and tally every email
that appears on **3+ DISTINCT customers** (an email shared by many unrelated people
is the fraud fingerprint). Mechanics that matter:
- Window the customer list by `modifiedTime` in **weekly slices** (`startTime`/`endTime`
  ms) to keep each page set small; paginate within a slice via `nextFetchKey`.
- This is SLOW (~26.6k records over 26 weeks, ~75s/week). Run it as a
  **background process with checkpointing** to a JSON file after each weekly
  window (`notify_on_complete=True`) — a 300s inline run will time out. Resume-safe.
- Output: `shared` = {email -> [customer rows]}. Keep only count >= 3.

### Step 2 — exclude the noise BEFORE attribution
Three buckets are NOT fraud, drop them:
- **Dummy placeholders**: `na@`, `none@none.com`, `noemail@`, `n/a@`, etc.
- **Staff @tol-av.com (dealership domain) emails**: e.g. `jbelmontes@tol-av.com`,
  `spreston@tol-av.com` — these show high counts but are SCATTERED across many
  advisors (a real shop contact email), NOT a single-advisor lock. Exclude.
- **Genuine family/shared emails**: real-looking address on a handful of people
  with NO single-advisor dominance.

### Step 3 — per-email advisor attribution (the "who")
For each surviving candidate email, run the SAME VIN->RO->creator method as the
`tekion-customer-email-change-investigation` skill: collect every VIN across that
email's customers, `POST /repair-orders:search` by VIN, resolve each RO's
creator/advisor userId via `GET /users/{id}`, and tally. Run all candidates in one
background script (`/home/itadmin/tl-attribute-candidates.py` is the template).

### Step 4 — classify by the single-advisor-lock rule
For each email compute `creator% = (#customers whose RO creator = top advisor) / #customers`:
- **>= 85%  -> FRAUD SIGNAL** (single-advisor lock — one advisor created nearly
  every RO for an otherwise-unrelated customer set = he owns that redirect email).
- **0.60-0.85 -> LIKELY** (strong skew; report but label as such).
- **scattered / < 0.60 -> EXCLUDE** (genuine shared email or staff contact).
Group the FRAUD/LIKELY emails BY attributed employee. This is what turns "one
advisor, 33 records" into the real picture.

### Discovery result (2026-06-29) — DON'T assume it's one person
The expanded scan turned up **4 employees, 13 redirect emails, 229 records** at TL —
not the single advisor from the first pass:
- **Joe Garcia (#243)** — 9 emails / 156 records (FIVE at 100% lock: joesclassics2,
  sophialet204, laurelfingreenleaf, jgambina, dacr73; + brothapleez 94%; + 3 strong-skew).
- **Victoria Cuevas (#167)** — csn@gmail.com, 35 records, 86%.
- **Nancy Rojo (#162)** — jessica.scott5757 (91%) + ksunshine501 (75%), 31 records.
- **Mauricio Orellana (#113)** — meorellana13@gmail.com, 7 records, 71% (email
  literally contains his name+initials+emp# — a self-identifying tell).
Lesson: once you have ONE confirmed bad actor, ALWAYS run discovery mode — survey
manipulation tends to be a shop-culture problem, not a lone actor. An employee's
own-name email on many unrelated customers is an especially strong tell.

## GOTCHA — `403 "Missing or invalid context headers"` (endpoint block, NOT rate limit)
Verified 2026-06-29: the entire `/customers` endpoint family can suddenly start
returning `403 {"error":"Forbidden","message":"Missing or invalid context headers."}`
on EVERY call — both search (`?email=`) and by-ID (`/customers/{id}`) — even with a
freshly force-minted token and all documented headers (Authorization, app_id,
dealer_id, Content-Type). Meanwhile RO-search, vehicle-inventory, and `/users/{id}`
keep working fine. Diagnosis:
- This is **NOT a 429 rate limit** (429 returns a different body and clears with backoff).
  Waiting 4+ min and force-refreshing the token does NOT fix it.
- It is a **gateway-level access/scope or required-context-header change** scoped to
  the customer module specifically. The customer API needs a tighter context than the
  others; the app's customer-API scope may have been toggled off, or Tekion added a
  required context header that isn't in the public spec.
- Symptom can flap between `403 "Missing or invalid context headers"` and `400 Bad Request`
  call-to-call — both mean the same \"customer endpoint is blocked right now,\" do NOT
  read the 400 as the count-param trap (that has body `invalid.input.error`).
- **NEVER-GUESS rule applies**: do not invent undocumented context headers to brute past
  it. Stop, tell Joe the customer scope looks blocked, and either (a) wait and retry
  later, or (b) use the **browser fallback**, or (c) have Joe check the customer-module
  API scope in the Tekion app.

### By-ID endpoint quirk
`GET /openapi/v4.0.0/customers/{customerId}` (spec
`customer__get-customer.json`) lists **`Content-Type` as a REQUIRED header** — the
shared `tekion_client.api_get` GET helper omits it, so a bare call 400s. Add
`Content-Type: application/json`. (But note: when the whole module is in the 403 block
above, even adding Content-Type still 403s — the block supersedes.)

### Browser fallback when the customer API is blocked
The logged-in Tekion UI session (persistent browser on :9223, Customer Management
`/core/customer`) runs under Joe's USER context and is unaffected by the API context
block. To resolve names/displayId/lastUpdate for a list of customer IDs you already
have (e.g. from the discovery checkpoint, which stores IDs only): switch to the store
(TL=1092), open each `/core/customer/viewCustomer/<id>` (or search by displayId), and
read the profile. Slower but reliable and API-independent. Prefer this over hammering
a blocked endpoint.

### What survives an API block
The discovery checkpoint `tl-shared-emails.json` stores `shared` = {email -> [customer
**IDs only**]} — no names/timestamps. The first-pass detail file
`survey-fraud-TL-detail.json` DOES have full name+displayId+creationTime+lastUpdateTime
for the originally-named emails. So if the customer API blocks mid-task, you can still
deliver the originally-detailed emails immediately from disk and only the NEWLY
discovered emails need the browser fallback to resolve.

## Verified result (first run, 2026-06-29)
Two suspect emails (`joesclassics2@gmail.com`, `brothapleez@icloud.com`) -> all 33
current hits at **Toyota of Lancaster (TL)** only (17 + 16), zero at the other 6
stores. Timeline spanned Dec 2024 -> Jun 2026; **11 records stamped the identical
minute 2026-03-19 22:22 PT** (after-hours bulk edit). Confirmed the count-param 400
trap and that email-alone returns 200.
