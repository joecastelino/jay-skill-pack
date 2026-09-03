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
