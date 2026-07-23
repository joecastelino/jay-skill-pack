---
name: tekion-customer-email-change-investigation
description: Investigate WHO changed customer contact info (esp. email) and WHEN in Tekion — e.g. a service advisor swapping customer emails to addresses he controls to hijack CSI/survey scores. Covers finding all records on a given email via the OpenAPI customer search, the hard limits on audit data, and the RO-advisor attribution workaround that identifies the suspect.
triggers:
  - who changed customer email tekion
  - customer email tampering
  - survey manipulation advisor
  - csi fraud tekion
  - find customers by email tekion
  - when was customer modified tekion
---

# Tekion — Customer Email-Change / Survey-Fraud Investigation

## When to use
A customer's email was changed to an address someone controls (classic CSI/survey
manipulation: advisor points the survey email at himself so HE gets/answers it).
Goal: find every affected record, when it changed, and WHO did it.

## The hard limits (state these honestly up front)
- **No `modifiedBy` in the OpenAPI / UI.** Neither the OpenAPI customer object nor the
  customer-profile UI (`/core/customer/viewCustomer/<uuid>`) exposes a field-level
  audit log naming who edited a field. BUT the app's INTERNAL record carries
  `lastUpdatedByUserId` (record-level, = last editor) — pull it via the :9223 XHR-hook
  (see Step 2c). It's the strongest "who" available short of Tekion's admin audit trail,
  with the caveat that it's the LAST editor, not specifically who set the email. Tabs are Customer360 / General Information /
  Tax Exemptions / Sales / Service / Parts / Accounting / Vehicles / Attachments /
  Compliance / Transaction History — none is a change-log. The kebab only has
  Active/Inactive/On-Hold User + Create Dispute.
- **`lastUpdateTime` is record-level** (ms epoch), not per-field — pinpoints the
  email edit only if nothing else touched the record afterward.
- **Current scan is a FLOOR.** The search only sees records CURRENTLY on the email.
  Any record swapped back to the real customer after the survey fired is invisible.
  True count is higher.
- **Definitive who+when** lives only in Tekion's internal admin audit trail —
  request from Tekion support / dealer admin to corroborate.

## Step 1 — Find all records currently on the email (OpenAPI)
`GET /openapi/v4.0.0/customers?email=<addr>` works (param IS supported; also
lastName, phone, firstName, companyName, id, search, createdStart/EndTime,
start/endTime). Do NOT add `count` — it 400s with email. Loop all 7 dealers
(`tekion_client.load_config()["dealers"]`). `meta.total` per store = current count.
Then `?id=<customerId>` returns the full record incl `vehicles[].vin`,
`creationTime`, `lastUpdateTime`, `customerDetails.emailCommunications[].email`.

## Step 2 — Attribute WHO via RO advisor (the workaround that nails it)
RO search has **no customer filter** (filterable fields: opcode, make, status,
**vin**, documentNumber, documentId, creationTime, invoicedTime, closedTime,
modifiedTime, paytype; operators GT/GTE/LT/LTE/IN/NIN/BTW/BOOL using a `values`
ARRAY). But `vin` is filterable, and each customer record carries their VIN(s).

For each affected customer, for each VIN:
```
POST /openapi/v4.0.0/repair-orders:search          (MUST include full /openapi/v4.0.0 prefix or 404)
body: {"filters":[{"field":"vin","operator":"IN","values":[VIN]}],
       "pageSize":50,"sort":[{"field":"modifiedTime","order":"DESC"}]}
```
Response = `data.results[]`, each with `primaryCustomer.id`, **`createdByUserId`**
(LinkedResource), `assignee.advisor` (LinkedResource), `modifiedTime`,
`documentNumber`. Resolve user ids:
```
GET /openapi/v4.0.0/users/<uuid>
```
→ `data.userNameDetails.completeNames` is a **LIST** `[{nameType:"DISPLAY_NAME",value}]`
(NOT a dict — parse as list or you'll silently get nothing), plus
`userRoleDetails.primaryRole.persona` and `employeeDetails.employeeDisplayNumber`.
Deactivated/unknown ids → 400 `no.user.found` (skip; usually a minority of old ROs).

**The signal:** count, per advisor, how many of the affected customers they were
the advisor / RO-creator on. The advisor appearing across (near) ALL of them is the
suspect — in the verified 2026-06-29 TL case, Joe Garcia (emp #243) was advisor on
33/33 and creator on 32/33 while the next-closest advisor hit only 8. That ratio IS
the finding (corroborative attribution, not a system audit entry — say so).

## Step 2b — DISCOVER unknown redirect emails (fleet-wide shared-email sweep)
When you don't yet know all the addresses (or want to catch OTHER employees doing
the same), sweep the whole store's recently-modified customers and flag any email
shared across many UNRELATED customers. Verified 2026-06-29 at TL.

- Customer search supports a **modified-time window**: `startTime`/`endTime` (ms
  epoch). Docs say ~7-day lookback per window, so loop week-by-week (26 weeks ≈ 6mo).
  Paginate each window with **`nextFetchKey`** (from `meta.nextFetchKey`). NOTE the
  two different page-token names across endpoints: customer search = `nextFetchKey`;
  RO `:search` = **`meta.nextPageToken`** (NOT paginationToken/nextFetchKey). RO
  `:search` also returns `meta.totalCount` (e.g. 79,851 ROs in a 6-mo window — too
  many to page, which is why the per-VIN approach in Step 2 is preferred for RO data).
- Tally `customerDetails.emailCommunications[].email` (lowercased) → set of distinct
  customerIds per email. Flag emails shared by ≥3 distinct customers.
- This is SLOW (a 1-week window can be 40+ pages; ~4,000 customers/week at TL). RUN
  IT AS A BACKGROUND PROCESS with per-week checkpointing to a JSON file (a 90-day
  in-line `execute_code` run TIMES OUT at 300s). Launch with explicit
  `/usr/bin/bash -c 'python3 script.py > log 2>&1'` + `notify_on_complete=true`;
  `ast.parse` the script first.
- **Triage the hits — most shared emails are NOT fraud:**
  - **Dummy/placeholder emails** (`none@none.com`, `noemail@noemail.com`,
    `noemail@gmail.com`, `none@gmail.com`, `noname@noname.com`, etc.) are entered by
    advisors when a customer has no email — high counts (100s–1000s), IGNORE.
  - **Family/shared real emails** show up on 3–5 customers with the SAME surname —
    usually legit, low priority.
  - **RED FLAGS:** (a) an email on many customers with MANY DIFFERENT surnames
    (compute surname diversity: `len(set(lastname))` ≈ count); (b) a **STAFF email**
    (`*@tol-av.com` or any dealer domain) sitting on customer records — that's the
    exact redirect fingerprint (at TL, besides Joe Garcia's gmail/icloud, the sweep
    surfaced `jbelmontes@tol-av.com` on 15 customers, 0 matching surnames = a likely
    SECOND offender). Run Step 2 advisor-attribution on each red-flag email's
    customers to confirm who built those records.

## Step 2c — The REAL audit field via the app's INTERNAL API (best "who", added 2026-06-29)
The public OpenAPI customer object has no `modifiedBy`, BUT Tekion's **internal**
customer record (the one the app's own UI fetches) DOES carry
**`lastUpdatedByUserId`** — the system's record of who last edited that customer.
This is a genuine audit field, far stronger than RO-advisor inference. Get it via
the logged-in :9223 browser with an XHR hook (a cold in-page `fetch()` to `/api/...`
FAILS auth — "Token doesn't exist or is invalid" — you MUST let the app fire its own
authenticated XHR and capture the response):

1. In :9223 (authenticated, correct dealer), install an XHR hook that pushes any
   response whose URL matches `/customers/<id>` into `window.__cap` (override
   `XMLHttpRequest.prototype.open`+`send`, grab `responseText` on 'load'). Add a
   fetch hook too for safety, but these calls are XHR.
2. For each customerId, drive the SPA via **`history.pushState` + `PopStateEvent`**
   (NOT `/navigate` — a full reload WIPES the hooks) to
   `/core/customer/viewCustomer/<id>`, wait ~2.5s, then read the captured response
   for `/api/cms/u/customers/<id>?recip...` (~7KB JSON).
3. Parse: `data.lastUpdatedByUserId`, `data.modifiedTime` (ms), `data.firstName/
   lastName/companyName`, `data.displayId`, `data.email`. Loop all affected IDs as a
   **background process** with per-ID checkpointing (≈3s/record; 100+ records exceeds
   the 300s inline limit).
4. Resolve `lastUpdatedByUserId` → name. Prefer the OpenAPI `/users/<id>` cache from
   Step 2; for stragglers the app's `/search/v2` (global "Search here..." box) or the
   employee module roster can resolve them via the same XHR-hook capture.

**CRITICAL NUANCE — do NOT overstate this field:** `lastUpdatedByUserId` is whoever
touched the record MOST RECENTLY, *not necessarily who set the fraud email*. If the
advisor planted the email in March and a different advisor opened that customer for
normal service in May, the "last editor" flips to the second advisor even though the
fraud email (still on file) was the first advisor's doing. So split the records:
  - **STRONGEST**: email-on-file is a scheme address AND the suspect is the recorded
    last editor (verified TL case: Joe Garcia last editor on 36).
  - **Weaker**: carries a scheme email but last-edited by someone else (normal
    rotation; at TL, 81 of 117 — still hold the fraud email but don't individually
    prove the suspect via this field). Report both layers, color-coded, and say plainly
    that even this audit field isn't a per-field "who set the email" entry — that still
    needs Tekion's internal admin audit trail via support ticket.

## OpenAPI 403 "Missing or invalid context headers" — endpoint family can go dark mid-task
Seen 2026-06-29: the ENTIRE `/customers` (and later `/users`) OpenAPI endpoint family
began returning `403 "Missing or invalid context headers"` partway through a session,
even with a freshly forced token and the documented headers (Authorization, app_id,
dealer_id, Content-Type) — while `/repair-orders`, `/vehicle-inventory` still worked.
This is NOT a rate limit (those return 429) and NOT fixable by guessing extra headers
(the by-ID spec lists a required `Content-Type` header your GET client omits — adding
it flips 400→403 but still blocks). It is a gateway/scope condition: the app's
customer-API scope may have been toggled, or a required context header changed
server-side. **Fallback that works regardless: pull the data through the logged-in app
via the :9223 XHR-hook (Step 2c).** Flag the API-scope issue to Joe afterward; it's
worth checking the integration's customer scope. Intermittent 400-vs-403 on the same
call ≈ the gateway is in this state, not a param bug.

## Step 3 — Report (multi-tab xlsx, route via Stacey)
Sheets: **Summary** (suspect + caveats), **Affected Customers** (name, customerId,
email, lastUpdateTime, advisors-on-their-ROs), **Advisor Ranking** (highlight the
suspect row red). Save to `/home/itadmin/tekion-reports/data/`. This is sensitive
HR/fraud material — deliver the file and CONFIRM the destination with Joe before
emailing; don't auto-blast.

## Browser bits (only needed to eyeball a profile; not for the data)
Login via `~/tekion-auth/login.py`, inject into :9223 (see persistent-browser-server
skill), switch dealer via the pill → "Search Dealership" box (list is alphabetical,
target store below fold). Customer Management = left-nav **CM** = `/core/customer`;
expand the filter-bar search icon (≈x1188,y273) → "Search..." box; click a row →
`/core/customer/viewCustomer/<uuid>`.

## Pitfalls
- `email` + `count` together → 400. Use email alone.
- RO search without `/openapi/v4.0.0` prefix → 404. The `:search` colon path is correct.
- `completeNames` is a list, not a dict — the #1 silent-failure trap.
- Don't overstate: "who" here = attribution by advisor frequency, not a modifiedBy field.
- Probe address VARIANTS of a known fraud email (e.g. joesclassics@, joesclassics1/3@,
  same handle @icloud/@yahoo, the suspect's own work email) — cheap `?email=` calls;
  in the TL case there were exactly 2 (no variants), but confirming that is worth it.
- Page-token names differ by endpoint: customer search `meta.nextFetchKey`,
  RO `:search` `meta.nextPageToken`. Using the wrong key silently stops after page 1.
- If the OpenAPI `/customers` family 403s mid-task ("Missing or invalid context
  headers"), don't fight it — switch to the :9223 internal-API XHR-hook (Step 2c). A
  cold in-page `fetch('/api/...')` will NOT authenticate; only the app's own fired XHR
  carries the auth interceptor. Drive the SPA with `pushState`+`PopStateEvent`, never a
  full `/navigate` (which wipes the hooks).
