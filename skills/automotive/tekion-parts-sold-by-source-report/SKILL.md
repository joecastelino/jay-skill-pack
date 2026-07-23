---
name: tekion-parts-sold-by-source-report
description: Build a "units of X sold in a period" report (tires, batteries, brakes, BG products, wipers...) for any Tekion store using the Source Code part list + bulk salehistory API — NO OpenAPI quota, no RO fan-out. Use when Joe asks "how many tires/batteries/etc were sold last month/quarter" and the category maps to a parts Source Code. Verified TOL tires Q2 2026.
triggers:
  - tires sold report
  - how many tires sold
  - parts sold by category
  - batteries sold last month
  - source code sales report
---

# Parts-Category Sales Report via Source Code (zero OpenAPI quota)

Count units of a parts CATEGORY sold over a period by combining the Source
Code part-list export with the bulk `salehistory/groupByMonth` internal API.
Verified: TOL (dealer 1092) tires Q2 2026 = 1,329 units in ~20 min, while the
OpenAPI RO-scan approach was dead-blocked on `OVERALL_QUOTA` 429s.

## When to use vs the RO-scan approach
- **USE THIS** when the category has its own Source Code (TIRES, BATT, BRAKES,
  BG PRODUCTS, GAS/OIL, FILTERS/WIPERS...) and Joe wants UNITS + estimated $.
  It's browser-internal-API only — burns ZERO OpenAPI quota, immune to the
  shared 429 limits, and 10-100x faster than RO fan-out.
- **USE THE RO SCAN** (tekion-openapi-repair-orders / alignment-report pattern)
  when Joe needs: actual INVOICED dollars, advisor breakdown, pay-type split,
  or per-RO detail. salehistory gives month-granularity UNITS only.
- Joe explicitly suggested "get it through source code" when the API quota was
  exhausted (2026-07-07) — offer this path proactively whenever a category
  report is blocked or slow.

## Limitation to state in the report (be honest)
salehistory = units/month only. $ figures are ESTIMATES = units × CURRENT
list/cost from the parts master (prices may have changed mid-period, and
actual sell price ≠ list). Say so in the deliverable; offer the RO-level pull
as a follow-up cross-check.

## Procedure (all via :9223 persistent browser)

1. **Auth**: check :9223 — if bounced to /login, run
   `$VPY /home/itadmin/tekion-auth/login.py` then restore per
   persistent-browser-server skill (cookies via /cookies + 21 localStorage keys
   one-at-a-time via /eval, param is `js` NOT `expression`). Switch dealer via
   the UI pill (/mouse on pill ≈x1130,y32, then /mouse on the store leaf found
   by innerText match) — verify `localStorage.currentActiveDealerId` flipped.

2. **Find the category's source code**: arm the XHR header-capture hook
   (setRequestHeader override → `window.__H` once a `tekion-api-token` header
   appears), drive the SPA to `/parts/source-codes/list` (pushState+PopStateEvent
   after first load so the hook survives), then in-page
   `fetch('/api/parts/proxy/u/settings/source-code',{headers:window.__H})` →
   all source codes w/ id+code+description. TL: 302=TIRES, 107=BATT,
   500=TOYOTA BRAKES, 106=BG PRODUCTS, 150=GAS/OIL/GREASE,
   109=FILTERS/WIPERS/COOLANT/CLIPS, 105=DO NOT STOCK. Source codes are
   PER-STORE — always pull the list, never assume.

3. **Export the source's part list**: click the code cell in the list (cold
   navigate to /edit/<id> renders empty shell), click "List of Parts" tab,
   arm presignedurl XHR hook, click `.icon-download1`, wait ~12s, click the
   "Download" toast span, then in-browser fetch the S3 xlsx → base64 →
   ferry out in ≤16k chunks (json_parse, not json.loads). Parse inlineStr xlsx
   with ET.iterparse. Full mechanics in tekion-source-code-parts-scrub Step 2-3.

4. **Bulk sale history**: install the `window.__harv` concurrent worker
   (tekion-source-code-parts-scrub has the template) hitting
   `POST /api/wms/parts/u/inventory/utility/salehistory/groupByMonth` with
   `{"partId":"M_TMNA_<PN>"}` (inventoryId ignored). Filter the response to the
   target period's {year, month} pairs in-page to keep payloads small.
   608 parts @ conc 8 ≈ 16s, zero errors. Works fine at TL (not just SCT).

5. **Aggregate + deliver**: units by month + by part; est_rev = units×list,
   est_cost = units×cost from the export columns (PART COST idx 8, PART LIST
   PRICE idx 10 — money strings need $/comma strip). Deliverables Joe wants:
   Toyota-red scorecard PNG (KPI cards: total units hero, distinct parts,
   est rev, est gross; month strip; top-12 table w/ red bars) + PDF + multi-tab
   xlsx (Summary / By Part / Full source list) + CSV. vision_analyze the PNG,
   then Stacey emails (for "email ME" = To Joe, data-URI inline PNG not CID,
   ask for terse "SENT <msg-id>" reply). Verify in INBOX, not Sent.

## Quota-exhaustion context (why this skill exists)
`429 OVERALL_QUOTA` (app-wide, distinct from the 15-min OVERALL_RATELIMIT) can
block ALL OpenAPI consumers for an extended time. Root cause seen 2026-07-07:
the 2 AM vi-api-pull.py got stuck in retry loops for 7+ hours re-burning quota
— kill the stuck process + rm /tmp/tekion-vi.lock, then park a quota watcher
(probe 1-row search every 20 min, auto-resume the blocked job on 200) instead
of letting anything blind-retry. Checkpoint enumeration scans BY MONTH so a
resume never redoes completed months.

## Pitfalls
- "Last quarter" = the just-completed calendar quarter; state the window.
- The source export's ON HAND is NOW, not end-of-period — label it "On Hand Now".
- Parts with sales but no longer in the source (moved/deleted) are missed;
  cross-check part count vs expectation if totals look light.
- A category can straddle sources (e.g. some tires in RETAIL/NON-TOYOTA 303) —
  eyeball the source list for sibling codes and say which you included.
- All salehistory fetches need `window.__H` (axios headers) — bare fetch 500s.
