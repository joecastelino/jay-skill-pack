---
name: tekion-ro-fee-waiver-investigation
description: Investigate whether a specific Tekion Misc/RO-level Fee (e.g. LYFT ride-share charge, shop supply fee, diagnostic fee) is being silently zeroed out on customer-pay ROs while the rest of the ticket bills normally — i.e. someone quietly waiving a charge without a documented coupon/discount. Use when asked "is advisor/manager X hiding/not charging for Y" or "why did our [fee] revenue drop."
triggers:
  - not charging customers for
  - hiding a fee
  - waiving a charge
  - lyft fee not billed
  - fee revenue dropped
---

# Tekion RO Fee Waiver Investigation (e.g. "Tony isn't charging for Lyft")

## When to use
Joe/a store manager suspects an advisor or manager is silently NOT charging
customers for a specific RO-level Misc Fee (ride-share, shop supplies, hazmat,
diagnostic, etc.) even though the fee line exists on the RO. This is a **fee
waiver / revenue-leakage detection**, not a normal reporting task — the signal
you're hunting for is "$0 on a fee line that should have a real amount, on an
otherwise fully-billed customer-pay RO."

## Core data model (OpenAPI, verified 2026-08-18 on BT/Lyft)
- `repair-orders:search` result carries a **free** `transportation` LinkedResource
  (`{link,id}`) per RO — resolves via `GET /transportation-types/{id}` →
  `{"data":{"name": "RIDE_SHARE"|"DROP OFF"|"RENTAL"|"WAIT", ...}}`. Sample a few
  ROs to discover the full id→name set for the store (don't assume Lyft's id is
  fixed across stores — it wasn't checked cross-store).
- `GET /repair-orders/{roId}/ro-fees` → `data.roFees[]`, each:
  `{feeCode, fee:{id,link}, saleAmount, costAmount, unitSaleAmount, priceType
  (SYSTEM_CALCULATED|USER_OVERRIDDEN), source (SYSTEM|USER|EXTERNAL), quantity}`.
  **Dollar amounts are CENTS.** `feeCode` for Lyft = `"LYFT"`. A fee row existing
  with `saleAmount: 0` means the fee WAS added to the RO (advisor engaged the
  ride-share workflow) but the dollar amount never got populated/was zeroed.
- `GET /repair-orders/{roId}/ro-coupons` → if `{}` (empty), there is NO documented
  discount/coupon justifying a $0 fee — rules out "legit comp with a paper trail."
- `GET /repair-orders/{roId}/ro-invoices` → `data.roInvoices[]`, filter
  `payType=="CUSTOMER_PAY"` → `invoiceAmount` (cents). If this is POSITIVE while
  the fee of interest is $0, the customer WAS billed for the rest of the ticket —
  proving selective zeroing of just that one fee line, not a full RO comp.
- RO record also carries `createdByUserId.id` and `modifiedByUserId.id` for free —
  useful to see who touched the RO last, though this is RO-level granularity, NOT
  a field-level edit log (see Limitations below).

## Method
1. **Pull the RO index for the window** via `creationTime GTE` (or `BTW`),
   pageSize 50, follow `nextPageToken` (plain pagination works fine on
   `creationTime`, no bisection needed — bisection is only required for
   `closedTime` windows per `tekion-openapi-repair-orders`).
2. **Filter to the transportation type of interest** + `status IN
   [CLOSED,INVOICED]` (or broader if the user wants open ROs too) + BASE_PAY_TYPE
   tag includes `CUSTOMER_PAY`.
3. **Fan out `ro-fees` on the candidate set** (ThreadPoolExecutor(6), retry on 429
   with `time.sleep(25*(attempt+1))`, checkpoint to JSON every ~20 so a
   kill/timeout resumes — reuse the checkpoint/resume pattern from
   `tekion-openapi-repair-orders`). Flag ROs where the target `feeCode` is present
   with `saleAmount == 0`.
4. **Cross-check each flagged RO**: pull `ro-coupons` (should be empty) and
   `ro-invoices` CUSTOMER_PAY `invoiceAmount` (should be > 0 if selective, not a
   full comp) to confirm the "quietly waived just this one line" pattern rather
   than a legitimate documented discount or a fully-comped RO.
5. **Resolve advisor names** via `/users/{id}` (see `tekion-openapi-repair-orders`
   ⭐ section) for both `assignee.advisor.id` (who owns the RO) and
   `modifiedByUserId.id` (who last saved it).
6. **Look for a disproportionate "last modifier."** Compute: (a) overall zero-fee
   rate across all candidates, (b) for each user who appears as `modifiedByUserId`
   on ANY candidate RO, their personal zero-fee rate among ROs they last-touched.
   A rate 2-3x+ the baseline, concentrated on one person (especially someone
   senior like a Service Director who wouldn't normally need to re-touch a
   closed RO), is the actionable signal.
7. **Trend it by month** (`creationTime` → month) to corroborate a "this started
   recently" claim — bucket zero-rate% per month, don't just give a raw count.

## Limitations (OpenAPI) — but see the UI Audit Logs method below, which SOLVES this
- The public OpenAPI has **NO field-level audit/history endpoint** for fees
  (`/history`, `/audit`, `/activity` all 404 — confirmed in
  `tekion-openapi-repair-orders`). `modifiedByUserId` is the RO's last-saver,
  not proof that THIS PERSON zeroed THIS FEE LINE specifically. Treat pure-API
  correlation as a lead, not a conclusion — see the worked example below where
  `modifiedByUserId` correlation pointed at the WRONG person.
- `priceType: SYSTEM_CALCULATED` with `saleAmount: 0` is itself a little odd —
  if it were truly system-calculated it should reflect the actual ride cost; a
  $0 value alongside `source: USER` suggests a person touched it, not that the
  system genuinely calculated zero.

## ⭐ DEFINITIVE PROOF: the RO's built-in "Audit Logs" drawer (verified 2026-08-18)

Every Tekion RO detail page has a **field-level edit history** exposed in the UI —
this gets you the exact old→new value, the exact user, and the exact timestamp for
a fee edit. It fully resolves the `modifiedByUserId`-is-just-a-proxy limitation
above. Use the persistent browser (`:9223`, see `persistent-browser-server` skill).

**How to open it:**
1. Navigate to `https://app.tekioncloud.com/ro/repair-orders/{roId}` (get `roId`
   from the OpenAPI RO record's `fees.id` / `invoices.id` link — same id as the RO
   document's own `_id`).
2. Click the kebab (⋮) menu in the RO header: selector
   `.ro_KebabMenuTrigger_kebabMenuTrigger__x1sbQKzWtx`. **Use `/click` with this
   CSS selector, NOT `/mouse` with computed x/y coordinates** — the element's
   bounding-rect can sit partially or fully OFF the 1280px viewport (e.g. x:1262,
   right:1302), so a coordinate click silently misses and can land on an unrelated
   page (seen: landed on `/ro/opcode/add`). Selector-based `/click` finds and
   clicks the real element regardless of on/off-screen position.
3. In the opened menu, find "Audit Logs" by text match (`textContent.trim()===
   'Audit Logs'`, no children) and `/mouse`-click ITS computed center — this one
   is reliably inside the viewport once the menu renders.
4. The Audit Logs drawer opens with a `.ro_rightDrawer_modalScroll__ri6PwshvMm`
   scroll container. It's **virtualized/paginated** — only ~15-20 entries render
   initially. Loop `el.scrollTop = el.scrollHeight` ~10-15x with a short sleep
   between each to force more entries to load, then read `el.innerText` for the
   full log (grew from 1.6KB to 12.6KB after scrolling in the verified case).

**What a fee-zeroing edit looks like in the log** (real example, RO #147340):
```
Jul 29 2026 1:57 PM — by JONATHAN SALDANA-BACA
Fee Details
  Overridden Sale Amount : 5292 → 0        (i.e. $52.92 → $0.00, in CENTS)
  Pricing Type : FLAT_PRICE → None
  Fee Min Amount / Max Amount / Flat Price : 0.0 → None
```
This is a genuine manual override on the fee's dollar field — not a coupon
(`ro-coupons` was independently confirmed empty), not a system recalculation.

**CRITICAL correction this method produced**: pure `modifiedByUserId` correlation
(the OpenAPI-only method above) had flagged **Tony Garcia** (BT Service Director)
as overrepresented among zero-fee ROs' last-modifiers. The real Audit Log showed
Tony's ONLY touches on that RO were routine end-of-day closing actions
(`CP Status: Paid→Closed`, `I Status: Invoiced→Closed`) — normal manager duties,
NOT the fee edit. The actual fee-zeroing edit was made by a **different**
employee (Jonathan Saldana-Baca) earlier the same day. **Lesson: `modifiedByUserId`
last-save correlation can implicate the wrong person** — a manager who closes ROs
at day's end will always show up as "last modifier" on many ROs regardless of who
touched the fee. Always pull the real Audit Log on flagged ROs before naming a
specific person to Joe/a store manager.

**Internal API behind the drawer** (discovered via XHR hook, NOT directly
callable): `POST /api/roaudit/u/v1.0.0/audit/logs` with body
`{"parentAssetId":"<roId>","parentAssetType":"REPAIR_ORDER","pageSize":20,
"pageToken":""}`. A raw XHR/fetch replay of this call from the page (even with a
valid `t_token` in localStorage) returns `500 {"message":"Token doesn't exist or
is invalid"}` — same as other Tekion internal APIs, the app's axios interceptor
attaches auth that a bare XHR/fetch can't replicate. **You must drive the actual
UI click** (steps 1-4 above) to get real data; don't waste time trying to call
this endpoint directly.

**Navigation pitfalls hit while doing this at scale:**
- The dealer context (`localStorage.currentActiveDealerId`) can silently flip
  back to the default dealer (1251/BC) on/after a `/navigate` call, especially
  right after a failed nav (e.g. "No such ro exist" error page). **Re-check
  `currentActiveDealerId` after every navigate**, and if wrong, re-switch via the
  UI dealer pill (top-right "BC"/"BT" text, click it, then click the target store
  name in the popover — setting the localStorage key directly does NOT work, it
  gets reset on next paint).
- A stray `/mouse` click that misses (goes to an off-screen element) can silently
  navigate the whole SPA to an unrelated route (`/ro/opcode/add`) with no error —
  always verify `/url` after any click before assuming you're still on the RO.
- Re-arm any XHR hooks (`window.__auditHook` etc.) after every `/navigate` — a
  full page nav resets `window` state.

## ⭐ SCALING the Audit Log pull across ALL flagged ROs (verified 2026-08-19, 79 ROs)
Doing steps 1-4 by hand per RO is too slow. The working at-scale pattern:
1. Build the flagged-RO list from the fee-scan checkpoint, mapping each fee `id`
   back to the RO's internal `_id` + `documentNumber` via the cached RO index
   (`/tmp/bt_ros_70d.json`) — join on the `fees[].id` link.
2. **Arm a PERSISTENT XHR hook once**, then drive the UI per RO. The
   `POST /api/roaudit/u/v1.0.0/audit/logs` call is XHR (a `window.fetch` hook
   MISSES it). Override `XMLHttpRequest.prototype.open`+`send`, push
   `responseText` on 'load' when the url matches `/audit/logs`, into
   `window.__auditCap`. You get the **raw JSON** (richer + easier to parse than
   scraping `innerText` off the drawer).
3. Loop the ROs in a **background script** (`/usr/bin/bash`, `notify_on_complete`)
   — ~6s per RO, so 79 ROs ≈ 8 min, well past the 300s inline limit. Checkpoint
   to JSON per RO so a kill resumes. Per RO: `/navigate` to
   `/ro/repair-orders/{roId}` → re-arm hook (nav wipes `window`) → `/click` the
   kebab selector → text-match + click "Audit Logs" → poll `window.__auditCap`
   → save raw JSON.
4. **Direct RO-to-RO `/navigate` was stable** in the verified run — the dealer
   context did NOT flip when going straight from one valid RO url to another. The
   flip-to-1251 problem was triggered by FAILED navs / error pages. Still assert
   `currentActiveDealerId` per iteration (cheap), but don't build a heavy
   re-switch dance into the loop.
5. Parse each log for entries whose change block contains the fee fields
   (`Overridden Sale Amount`, `Pricing Type`, `Fees ... Added/Deleted Fees`) and
   attribute to the entry's user name. **Tally "fee editors" SEPARATELY from
   incidental "RO closers"** (`CP Status: Paid→Closed`, `I Status:
   Invoiced→Closed`) — conflating them is exactly the error that misidentified
   Tony Garcia.
6. Resolving user names via OpenAPI `/users/{id}`: `userNameDetails.completeNames`
   is a **LIST** `[{nameType:"DISPLAY_NAME",value}]`, NOT a dict — treating it as
   a dict silently yields nothing (recurring trap).

**Reconcile your flagged count before reporting.** The fee-scan checkpoint file
grew from 30 → 79 zero-fee ROs between the first analysis and the re-read (the
scan kept appending after the first partial read). Always re-read the checkpoint
fresh and state the final N — don't quote a mid-scan number to Joe.

## Worked example (BT / Lyft / Tony Garcia, 2026-08-18)
70-day BT scan: 895 CUSTOMER_PAY CLOSED/INVOICED ride-share ROs. 30 (3.4%) had
`feeCode=LYFT` with `saleAmount=0`; 19 of those 30 still had a positive CP
invoice total (selective zeroing, not a full comp); zero `ro-coupons` on any of
them (no documented discount). Monthly zero-rate: June 1.2% → July 4.0% → Aug
4.4% (matches a "started ~2 months ago" complaint). Antonio "Tony" Garcia
(BT Service Director, id `e8393eb2-bd0b-4943-942f-86cb5246624e`) was the
`modifiedByUserId` on 6 of the 30 flagged ROs — vs. an expected ~2 by his overall
share of last-touched ROs (57/895) — a ~3x concentration, on someone who
shouldn't normally need to re-save a closed RO. Reported as a strong signal with
the audit-trail caveat, and offered UI-level financial-log confirmation as the
next step.

**FINAL OUTCOME of that case (2026-08-19) — the correction that matters:** a full
re-read of the fee-scan checkpoint gave **79** flagged zero-LYFT-fee ROs (not 30 —
the background scan was still appending when the first analysis ran). The Audit
Log pull identified **JONATHAN SALDANA-BACA** as the person manually setting the
LYFT fee's `Overridden Sale Amount` to 0. **Tony Garcia was NOT the culprit** —
his appearances were day-end RO-closing status changes only. Note the extra
sensitivity here: Tony Garcia is also the BT store contact who RECEIVES Jay's
daily BT menu-sales emails, so a wrong accusation goes to the wrong place fast.
This is HR/fraud-sensitive material — deliver findings to Joe directly and
confirm before any wider distribution; do not auto-email a named-suspect report.

## Generalization
Swap `feeCode` (e.g. `"LYFT"` → shop-supply/hazmat/diagnostic fee code — look
these up via a sample `ro-fees` pull first if unknown) and the `transportation`
type filter (or drop it entirely if the fee isn't transportation-linked) to reuse
this for any "is someone hiding/not charging for X fee" investigation.
