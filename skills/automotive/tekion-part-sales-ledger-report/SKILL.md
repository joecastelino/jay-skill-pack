---
name: tekion-part-sales-ledger-report
description: Build a "parts sold" report (e.g. tires) for any Tekion store and period with ACTUAL invoiced dollars, split RO vs Sales Order (counter), by counterperson, from the internal part transaction ledger (activity-log API) — zero OpenAPI quota. Use when Joe asks "how many X did we sell" for a parts category, or when the OpenAPI quota is exhausted and RO-level pulls are blocked.
triggers:
  - tires sold report
  - parts sold by source code
  - sales order and ro split
  - part transaction ledger
  - tekion activity log
---

# Tekion Part-Sales Ledger Report (RO vs SO, actual $)

Proven end-to-end at TOL (dealer 1092) for "tires sold Q2 2026" — 1,176 net units,
$226,965 invoiced, RO/SO split + counterperson ranking, all via the :9223 browser
internal APIs. **Zero OpenAPI quota** — this is THE fallback when OVERALL_QUOTA is
exhausted, and honestly faster than the RO fan-out anyway.

## OVERALL_QUOTA outage facts (learned the hard way, 2026-07-07→09)

- An `OVERALL_QUOTA` 429 can persist **27+ hours** — that duration rules out the
  15-min rolling window and means the **30-day request bucket** was drained
  (2026-07-07 culprit: a stuck 2AM vi-api-pull retry-looping 7+ hrs). Recovery may
  need the **Tekion API rep**: ask (1) OVERALL_QUOTA limit & reset period,
  (2) current consumption on our key, (3) a reset given the runaway loop,
  (4) a limit raise for the 7-rooftop nightly footprint.
- **401 "could not be authenticated" mid retry-loop is NOT recovery** — it's the
  poller's ~2h OpenAPI token expiring. Re-probe with a FRESH token before
  declaring the quota restored.
- During an outage: kill ALL stale pollers/retry loops first
  (`pgrep -f 'wait_then_scrape|quota_watch|selfheal'`) — parallel watchers
  re-drain the bucket the instant it restores (thundering herd). At most ONE
  low-frequency probe (≥10 min interval, 1 lightweight call).
- All internal `/api/` browser-session paths (this ledger, source-code scrub,
  bulk velocity, Caliber dollars) keep working — route reports through them.

## Architecture (3 layers, in order)

1. **Source code part list** → the part-number universe for the category
   (e.g. TOL Source 302 "TIRES", 608 parts). Method = `tekion-source-code-parts-scrub`
   skill (download-icon → presigned S3 → in-browser fetch → base64 ferry → inlineStr xlsx).
2. **Sale-history groupByMonth** (`/api/wms/parts/u/inventory/utility/salehistory/groupByMonth`,
   body `{"partId":"M_TMNA_<PN>"}`) → fast unit counts per month. GOOD for a quick
   headline but it counts GROSS sale events (incl. later-reversed) and has no $ or
   RO/SO attribution. TOL Q2 gave 1,329 gross vs 1,176 net — expect ~10-15% inflation.
3. **Part transaction ledger** = `POST /api/parts/activity-log/u/search` → the ground
   truth. Every sale line with refType (RO vs SO), qty, unit sell/cost, customer,
   counterperson, timestamp.

## The activity-log endpoint (captured 2026-07-07)

Fire in-page via `fetch(url, {headers: window.__H, credentials:'include'})` (capture
`window.__H` once via setRequestHeader hook on any real XHR — see bulk-velocity entry).

```json
POST /api/parts/activity-log/u/search
{"tekRequest":{"sort":[{"field":"transactionTime","order":"ASC"}],
 "filters":[
  {"field":"partId","operator":"IN","values":["M_TMNA_..."],"key":"partId"},
  {"field":"transactionType","operator":"IN","values":["SALE"],"key":"transactionType"},
  {"field":"transactionTime","operator":"BTW","values":["<ms0>","<ms1>"],"key":"transactionTime"}],
 "page":{"pageNumber":1,"pageSize":100}}}
```

Response `data.count` + `data.hits[]`. Useful hit fields: `partNumber`,
`transactionTime`, `refNumber` (RO# or SO#), `refAsset.type`
(**FULFILMENT**=RO / **SALES_ORDER**=counter / **CUSTOMER**=return-to-stock),
`subType` (FILLED / UN_FILLED / null), `deltaOnHandQty` (negative=sale,
positive=reversal/unfill), `unitSellingPrice`, `unitTotalCostPrice` (real DOLLARS,
not cents), `customer.customerName`, `soldByName`, `beforeOnHandQty/afterOnHandQty`.
Other transactionTypes: PURCHASE (PO received), adjustments — filter SALE only.

### ⚠️ PAGINATION IS BROKEN — pageNumber is IGNORED (the #1 trap)
The endpoint returns max ~20 rows regardless of pageSize/pageNumber; requesting
page 2 returns the SAME rows. A naive "while rows<count page++" loop silently
duplicates and/or truncates (I got 1,142 rows w/ dupes, then 302 rows, for a true
1,006). **FIX = recursive time-window bisection**: query the window; if
`count > hits.length`, split [t0,t1] at midpoint and recurse; collect into a dict
keyed by hit `id` (dedupes overlap). 16 batches × 40 partIds over 3 months ran in
~20s. Batch partIds ~40 per query to keep counts small.

## Classification rules (verified against DOM Transactions tab)

- `refAsset.type == FULFILMENT` → **RO sale** (Parts RO Sales / "RO filled" in UI).
- `refAsset.type == SALES_ORDER` → **counter Sales Order**.
- `refAsset.type == CUSTOMER` → **customer RETURN to stock** (qty positive, sell=0)
  — report separately, do NOT count as sales or negative sales.
- `deltaOnHandQty < 0` = sale of |qty|; `> 0` on FULFILMENT/SALES_ORDER =
  unfill/reversal → SUBTRACT (net = filled − unfilled).
- Net revenue = Σ |qty|·unitSellingPrice signed the same way; GP = rev − cost.
- Expect ~20% of RO lines to be UN_FILLED reversals (TOL: 300 of 1,471 units) —
  reporting gross without netting is materially wrong.
- Internal fills at/below cost (e.g. used-car recon, sell price 0-cost) produce
  NEGATIVE GP for that counterperson (TOL: Jorge Belmontes −$7.7K) — flag, don't hide.

## Recipe

1. :9223 alive? Check dealer + `t_token`. If /login: run
   `login.py` (tekion-autonomous-login), inject storage_state cookies + 21
   localStorage keys, switch dealer via the UI pill (localStorage set does NOT work).
2. Pull the source-code part list (scrub skill) → part numbers → `M_TMNA_` partIds.
   NOTE: `M_TMNA_` prefix is Toyota; other OEMs differ — read a partId off any
   captured XHR at that store first.
3. Capture `window.__H` (setRequestHeader hook), install the recursive
   `window.__ledger3(pids, t0, t1)` harvester, loop batches of 40 from Python via
   /eval (json_parse for lenient parsing).
4. Aggregate: channel split, monthly, by `soldByName` (title-cased), by part;
   detail lines for the CSV.
5. Deliver: Toyota-red scorecard PNG (page-1) + PDF + multi-tab xlsx
   (Summary / By Counterperson / By Part / Transaction Detail) + CSV; vision-verify
   PNG; email via Stacey (inline base64 data-URI PNG, NOT CID; To: Joe for
   "email me"; verify in INBOX not Sent).

## Variant: fast-mover stocking list / express (TXM) cabinet pars (proven TL 2026-07-16)

Joe asked \"what parts should I stock in a TXM fast-mover cabinet at TL and daily
quantities.\" Same ledger endpoint, but WHOLE-STORE instead of one source code:

- Skip the source-code part list — query the ledger with NO partId filter
  (transactionType=SALE only, 30-day transactionTime window) and time-bisect.
  TL 30 days ≈ 28k rows; runs fine in batched windows.
- Aggregate NET units (FULFILMENT + SALES_ORDER, minus UN_FILLED, exclude
  CUSTOMER returns) per part → avg/day AND busiest single day.
- **Par methodology Joe accepted**: cabinet par = busiest single day in last
  30 + small buffer, so one nightly refill never runs the cabinet dry mid-day.
  Note days-open (TL sells 7 days/week) when computing avg/day.
- **Exclude from a cabinet list**: bulk oil (dispensed not shelved), body-shop
  clips/rivets (counter traffic), spark plugs (lumpy full-set bursts — peak day
  18 then a week of nothing; mention them but don't par them).
- Group output: Oil Change Core / Cabin Filters / Engine Air Filters /
  Wipers (Toyota TA series) & Misc (CR2032, ATF gaskets). At TL the top 4
  (90430-12031 drain gasket ~66/day, 90915-YZZN1 filter ~56/day, 04152-YZZA1
  cartridge ~17/day, 87139-YZZ93 cabin ~8/day) = ~80% of volume — call out
  which shelves to oversize.
- Deliver: table in email body + xlsx (e.g. TL-TXM-Cabinet-Stocking-List.xlsx)
  via Stacey; offer a printable count-sheet like the SCT back-counter sheet.

## Numbers reconciliation (Joe will ask)
sale-history groupByMonth (gross events, list-price est.) ≥ ledger net invoiced.
TOL Q2: 1,329 gross/est-$288K-list vs 1,176 net/$226,965 actual (avg $193 vs $217
list). State both and why they differ.

## Files (TOL Q2 2026 reference run)
`/home/itadmin/tekion-reports/data/`: tol-source302-rows.json (part list),
tol-tire-q2-velocity.json (groupByMonth), tol-tire-q2-ledger.json (1,006 ledger rows),
tol-tire-q2-final.json (aggregates), TOL-Tires-Q2-2026-RO-SO.{png,pdf,xlsx},
TOL-Tires-Q2-2026-detail.csv.

## Pitfalls
- pageNumber ignored → time-bisection only (above).
- CUSTOMER rows are returns, not sales — excluding them changed TOL from
  "1,329 sold" to the correct 1,176 net + 216 returned.
- unitSellingPrice/unitTotalCostPrice are DOLLARS here (unlike OpenAPI cents).
- `adjustment/search` (searchText=PN) is ONLY manual adjustments, not sales.
- The Transactions tab often loads from React-Query cache → your XHR hook sees
  nothing; click the filter "Reset" button to force a refetch when discovering
  endpoints.
- Timestamps are epoch-ms; use Pacific (UTC-7) for month bucketing.
