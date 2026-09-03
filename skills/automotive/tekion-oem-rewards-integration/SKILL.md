---
name: tekion-oem-rewards-integration
description: Answer "can GM Rewards / OEM rewards show on the customer screen or cashiering?" and CHECK whether the My GM Rewards 2.0 integration is enabled at a store by inspecting a live cashiering invoice. Covers the KB article set, where rewards display in the workflow, the manual-tender-vs-integrated-card tell, and how to request enablement. Verified at BC (1251) 2026-09-03.
triggers:
  - gm rewards on cashiering
  - oem rewards customer screen
  - my gm rewards integration
  - is gm rewards enabled
  - rewards points on invoice
  - check oem rewards enablement
---

# Tekion My GM Rewards 2.0 / OEM Rewards Integration

## The canonical KB articles (searched "GM Rewards" in the ServiceNow KB)
- **KB0013265** — My GM Rewards 2.0 Updates (overview + prerequisites)
- **KB0016771** — My GM Rewards 2.0 Integrations (WHERE it displays)
- **KB0016773** — HOW TO: Redeem reward points for payments (cashiering steps + permissions)
- **KB0016858** — Updates & Integrations video
- Related: KB0025690 (rewards refund), KB0025045 (cancel a rewards payment), KB0023596 (why can't redeem all points)

## What the integration does (from the KBs)
When enabled, the customer's **My GM Rewards card** (Total Redeemable **Dollars** — NOT a raw
points count) displays across: Appointment Scheduling, Web/Mobile Check-In, Repair Order
(under Customer Information), **Cashiering** (below the other payment modes, with a Redeem
section: redemption amount auto-defaults to max + last-4-of-member-number verification),
PDF downloads (estimate/invoice show redeemable amount below total), and Customer
Management → OEM Rewards section. A yellow star icon next to the customer name marks
enrolled members throughout the service workflow.

Key facts:
- Requires customer email **verification** first — no verify, no card data.
- Rewards cover **labor/parts/accessories only — never taxes or fees**.
- Redemption void only until **midnight of payment date**.
- If the store is program-INELIGIBLE, the card still displays but Redeem is hidden.
- **SALES ORDERS (counter sales) are NOT in the documented integration surface** — every
  redemption reference is RO-scoped. Don't claim SO support; refer to PSM.
- Permissions needed: Cashiering Repair Order View + Pay (Roles → Permissions → Service → Cashiering).

## Enablement is Tekion-side only
Not a dealer-flippable setting. Email **support@tekion.com** or the PSM requesting
"My GM Rewards 2.0 integration" for the store (give the full dealer string, e.g.
americanmotorscorporation_1251).

## ⚠️ BC ENABLEMENT STATUS — CORRECTED (Joe, 2026-09-03)
My GM Rewards 2.0 IS ENABLED at BC (1251). My earlier "not enabled" verdict was WRONG — two bad tests:
(1) checked the OEM Reward tender on a FLEET invoice (EXECUTIVE AUTO); (2) re-checked on RO 102371
(enrolled member Sylvester Smith) but BOTH payers were third-party (PORTFOLIO + External Service
Customer) — the rewards card only renders on the CUSTOMER's own pay section w/ verified email, so
neither test could show it. PROOF the integration is live = the Customer Management → OEM Rewards
tab fires the real-time gm-rewards/account-details call to GM and renders balances (verified).
LESSON: the manual "OEM Reward Details" tender form co-exists with 2.0 — its presence proves NOTHING
about enablement. To verify cashiering display, you need a pending CP invoice where the payer IS an
enrolled, email-verified member. Don't call "not enabled" off fleet/third-party-payer invoices.

## How to CHECK if it's enabled (verified live, BC 2026-09-03)
Ground truth = a live cashiering invoice. Read-only, safe on production.

1. Auth: `login.py` (see `tekion-autonomous-login`). NOTE: `--check`/ALIVE can lie —
   if injection renders the login form, `login.py --force`. Default dealer after
   login = BC/1251.
2. Navigate `/ro/invoices` (NOT `/service/cashiering` — blank shell; NOT `/cashiering` —
   bounces to /home). Redirects to `/ro/invoices/REPAIR_ORDER` = the Cashiering list.
3. Open any **Pending** CP invoice: click the RO# cell (`.roid-wrapper.pointer`) →
   `/ro/invoices/REPAIR_ORDER/<objectId>`.
4. **The tell**, in the payment section (Due Amount → Mode of Payment):
   - **NOT enabled**: modes = `Credit/Debit Card | Cash | Check | OEM Reward | Other | Gift Card`,
     and clicking **OEM Reward** opens only blank manual fields (`OEM Reward Details`:
     Amount*, ID, Transaction Date, Payment Notes). That's the generic manual tender —
     cashier keys the amount by hand from the GM portal.
   - **Enabled**: a **My GM Rewards card** renders below the payment modes with the
     customer's redeemable dollar balance + a **Redeem** section (amount defaults to max,
     Last 4 Digits field). Grep innerText for `GM Rewards|Redeem|Redemption|Last 4`.

Script: `/home/itadmin/tekion-reports/bc_gmrewards_check.py` (standalone headless
Playwright + storage_state; adapt dealer check for other stores).

## Pitfalls hit building this
- **:9225/:9223 persistent instances flaked** (SPA bounced to /home mid-click, then the
  server endpoint itself HTTP 500'd). Per `persistent-browser-server` skill: on a 500,
  do NOT retry — go straight to standalone headless Playwright with
  `.tekion-storage-state.json`. That worked first try.
- **Invoice detail innerText is only ~830 chars when fully rendered** — small page, don't
  poll waiting for >3000 chars like RO pages. `Mode of Payment` present = loaded.
- The "OEM Reward Details" form only appears AFTER clicking the OEM Reward mode (real
  `page.mouse.click` on the visible element center).
- Discover left-rail app URLs generically: `[...document.querySelectorAll('a')]` → href map
  (that's how `/ro/invoices` was found; C = Cashiering).

## GM Rewards ENROLLMENT lookup per customer (cracked 2026-09-03 — works WITHOUT the 2.0 integration)
Customer Management stores rewards enrollment on the customer record even when the
cashiering integration is NOT enabled. Backing API (internal, replayable with captured
headers from /tmp/tekion_rec_headers.json + dealerId/tek-siteId swap — same auth set as
recommendation/search):
```
POST https://app.tekioncloud.com/api/lookup/search
{"CUSTOMER":{"filters":[{"field":"status","operator":"IN","values":["ACTIVE"]}],
 "searchText":"<name or email>","pageInfo":{"start":0,"rows":3},"sort":[]}}
```
Response: `data.CUSTOMER.{count, entities[]}` (NOT hits[]). Each entity's `data` node has:
- `customerRewardsInfos`: `[{"oem":"gm","redeemMyRewards":true,"rewardIds":[{"rewardId":"<email>","primary":true}]}]` — populated = ENROLLED member. rewardId is usually the member's email.
- Also present (usually null at BC): `oemRewardInfos`, `oemLoyaltyInfo` {loyaltyNumber, fordCompCode, chryslerCompCode, volvoCompCode}, `loyaltyInfoByOEMs`.
- The stored record is ENROLLMENT only — but see the LIVE BALANCE endpoint below (Joe corrected me on this 2026-09-03: the Customer Management → OEM Rewards tab DOES show $ even without the 2.0 cashiering integration).

## LIVE GM Rewards BALANCE lookup (cracked 2026-09-03 — Customer Mgmt OEM Rewards tab)
The OEM Rewards tab fires a real-time call to GM (takes ~2-4s — it's GM's loyalty system, not Tekion storage):
```
POST https://app.tekioncloud.com/api/service-module/u/gm-rewards/account-details
{"transactionDate":"MM/DD/YYYY","emailAddress":"<rewardId email>","memberNumber":""}
```
Same captured-header auth set (any /api/ headers w/ tekion-api-token etc.; dealerId/tek-siteId swap per store).
Response `data`:
- `redemptionInformation."LOY Member"`: `"Total Dollars"`, `"Total Points"` (comma-formatted strings), Tier, `"Dealer Eligible For Redeem"`.
- `accountInformation.loyMember`: `totalDollars`, `totalPoints`, `status` ("Active"), `canRedeem`, `memberNumber`, `memberNumberMasked`, currentTier, spendTrackers.
- `memberInformation`: name/address, full member number.
Pace ~0.6s/call; 44 lookups ≈ 2.5 min. Keyed by the rewardId EMAIL from customerRewardsInfos.
DISCOVERY PITFALLS: customer detail page is NOT directly routable (`/core/customer/detail/<id>` renders empty)
— must go list (`/core/customer`) → in-page search input (placeholder "Search...", y>100, NOT the global
"Search here..." top bar) → type + ENTER (no Enter = no filter) → click result row (y>300) → click "OEM Rewards"
left-rail tab. Probe script: `~/tekion-reports/bc_oemrewards_via_list.py` (XHR+fetch hook via add_init_script).
BC combo result 2026-09-03: 44 members / $3,335.54 live rewards $ vs $61.7K deferred.
Output: `~/tekion-reports/data/BC-GMRewards-members-declined-30d-with-balances.csv`.
- Batch fetch by id: `POST /api/lookup/ids` `{"CUSTOMER":{"ids":[...]}}` same shape.
- Pace ~0.25s; 360 lookups ≈ 2.5 min. Search by email first, fall back to name.

Proven combo report (2026-09-03): declined services 30d (tekion-declined-deferred-services-report)
→ dedupe to customers → lookup/search each → filter customerRewardsInfos populated.
BC result: 360 declined-svc customers → 44 GM Rewards members / 79 lines / $61.7K deferred.
Output: `~/tekion-reports/data/BC-GMRewards-members-declined-30d.csv`. Probe script (browser
XHR-hook discovery path): `~/tekion-reports/bc_custmgmt_rewards_probe.py`.

## LAPSED-MEMBERS report ("Rewards members not in for 6-12 months") — 2026-09-03
Script: `~/tekion-reports/bc_gmrewards_lapsed_6to12.py` (adapt window/store). 3 phases:
1. **Last-visit map**: enumerate 12 months of CLOSED/INVOICED ROs via OpenAPI
   `repair-orders:search` in 30-day `creationTime BTW` windows (paginationToken chaining is
   SAFE for creationTime — the bisection bug is closedTime-only). The customer id is FREE on
   each result: `primaryCustomer.id` (a `{link,id}` stub — no fan-out needed). Reduce to
   {customerId: (max creationTime, RO#)}; checkpoint the RO index per window
   (`data/bc-lapsed-ro-index.json`) so 429s resume.
2. **Enrollment check IN BATCH**: `POST /api/lookup/ids` `{"CUSTOMER":{"ids":[<=50 ids]}}`
   (captured-header auth, dealerid/tek-siteid swap) — 50 customers per call vs 1-per-call
   lookup/search; filter `customerRewardsInfos` populated w/ oem=="gm", take the primary
   rewardId (email).
3. **Live balances**: gm-rewards/account-details per member (pace 0.6s), same as the
   declined-services combo.
Lapsed filter = `t12 <= lastVisit < t6`. Sort output by live Rewards $ (the callback
priority). Phase 1 dominates runtime (~25K ROs ≈ 500 search pages ≈ 15-25 min) — run
background w/ notify_on_complete, never execute_code.

## Cross-references
- **"Pull rewards members who did X" reports are IMPOSSIBLE pre-enablement** (confirmed
  2026-09-03, Joe's "GM Rewards customers who declined service" ask): enrollment/points
  data exists NOWHERE in Tekion (no API, no internal endpoint, no customer field) until
  the integration is on. Workarounds: GM Global Connect member export matched by
  name/email/phone, or deliver the unfiltered customer list for BDC to check at contact
  time. Requesting enablement is the durable fix — pitch it.
- `tekion-declined-deferred-services-report` (the declined-customer list half of that ask),
  `tekion-sitemap` (Cashiering row), `tekion-autonomous-login`, `persistent-browser-server`,
  `tekion-kb-search-scrape` (KB SSO bootstrap: navigate `app.tekioncloud.com/core/knowledge-base/search`).
