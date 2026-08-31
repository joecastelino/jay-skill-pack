---
name: tekion-parts-gross-fleet-mtd
description: Pull TOTAL PARTS GROSS (revenue, cost, gross, GP%, RO vs counter split, by counterperson, by day) for any period across any/all 7 AMG stores from the Tekion part transaction ledger. Zero OpenAPI quota. Use when Joe asks for parts gross / parts sales numbers MTD, last month, or a custom window.
triggers:
  - parts gross report
  - total parts gross
  - parts sales month to date
  - parts gross MTD
  - parts revenue and cost by store
  - parts gross by counterperson
---

# Fleet Parts Gross (MTD / any period) — ledger method

Produces revenue, cost, **parts gross**, GP%, units, RO-vs-counter split, per-counterperson
and per-day breakdowns for 1–7 stores. Verified full fleet August 2026: 119,633 ledger lines,
$6.05M revenue / $1.28M gross, expected==retrieved on all 217 store-days, ~7 min wall clock.

**Zero OpenAPI quota** — pure internal browser API, so it cannot be blocked by 429
OVERALL_QUOTA and does not collide with the nightly VI/dealer-detail pulls.

## Why not OpenAPI
There is **no parts sales-order endpoint** in the granted OpenAPI scope (never granted by
Tekion). Parts gross therefore MUST come from the internal ledger via an authenticated
browser session. State this plainly if asked "can you do it through the API" — the answer
is yes, but it's the internal API, and it needs :9223 alive (so daytime runs only; the
1:16AM `cron-tekion.sh` Caliber job owns the browser at night).

## Preflight
```bash
curl -s http://127.0.0.1:9223/health          # {"status":"ok"}
pgrep -af 'cron-tekion|vi-api-pull'           # must be idle
curl -s -X POST http://127.0.0.1:9223/eval -H 'Content-Type: application/json' \
  -d '{"js":"JSON.stringify({u:location.href,d:localStorage.currentActiveDealerId,t:(localStorage.t_token||\"\").length})"}'
```
`t` must be ~536 (real JWT). If the URL is `/login`, re-auth per persistent-browser-server.
The **active dealer does not matter** — this method switches store by header swap.

## The pull (ONE self-contained eval, fire-and-forget + poll)
Endpoint `POST /api/parts/activity-log/u/search`, body shape:
```json
{"tekRequest":{"filters":[
  {"field":"transactionTime","operator":"BTW","values":["<ms0>","<ms1>"]},
  {"field":"refType","operator":"IN","values":["FULFILMENT","SALES_ORDER"]}],
  "pageInfo":{"start":0,"rows":500}}}
```
- Build headers **in-page from localStorage** (`mkH(dealer)` — see
  tekion-part-sales-ledger-report; the JWT is MASKED if ferried out via /eval).
- Loop `start += 500` until `start >= count`. Offset pagination works correctly here
  (unlike the `page:{pageNumber}` shape) — no time-bisection needed.
- **One query per store per DAY.** Day-slicing keeps each `count` small, gives a free
  by-day series, and makes gaps individually re-runnable. Pacific midnights:
  `Date.UTC(y, m-1, d, 7, 0, 0)` (UTC-7 PDT), window `t0 .. t0+86400000-1`.
- Dealer switch = swap `dealerId` + `tek-siteId` only. Assert `hits[0].dealerId` matches.
- Retry wrapper: 4 attempts, 15s sleep on 429, 3s on other errors; push failures to a
  `daysfail[]` so partial success is visible rather than silent.
- **Aggregate IN-PAGE**, ferry only the rollup (~47KB for the fleet-month) in ≤15KB
  slices. Never ferry 119K raw rows.
- Runtime exceeds the ~130s `/eval` cap → run async, set `window.__DONE`, poll
  `{done, prog, fail}` every ~28s. Note `execute_code` has its own 300s cap: keep the
  poll loop under ~8 iterations per call or it gets killed mid-wait.

## Math (get this exactly right)
- `qty = -deltaOnHandQty` → positive = sale, negative = UN_FILLED reversal. **Net them.**
  Reversals are material: ~8% of fleet revenue in Aug 2026.
- `revenue = qty * unitSellingPrice`, `cost = qty * unitTotalCostPrice`.
  **These are DOLLARS on this endpoint, not cents** (unlike OpenAPI).
- `gross = revenue - cost`. Skip `type=='LOCK'` rows and `deltaOnHandQty==0`.
- Channel: `refType=='SALES_ORDER'` → counter; `FULFILMENT` → RO.
- `refType=='CUSTOMER'` rows are returns-to-stock — excluded by the refType filter already.
- Counterperson = `soldByName` (uppercase-trim; expect an `UNKNOWN` bucket for
  system/nightly postings — usually small and often net-negative from reversals).
- **Track a separate at/below-cost segment** (`qty>0 && unitSellingPrice <= unitTotalCostPrice`)
  = internal/recon/warranty fills. Report both blended GP% and ex-internal GP%; these lines
  legitimately post negative gross and will otherwise look like a data error.

## Reconciliation gate (do NOT skip — Joe checks numbers)
Sum the first-page `count` per store-day as `expected`; compare to distinct ids collected.
Report `expected == retrieved` and the failed-day count in the deliverable footer. Aug 2026
run: 119,633/119,633, 0 fails. If they differ, re-run only the gap days.

## Deliverable
HTML → screenshot (house style, NOT matplotlib) + multi-tab xlsx.
- KPI cards: Total Parts Gross (hero) / Revenue / Cost / RO Gross / Counter Gross.
- Store table sorted by gross w/ inline bars, fleet total row, negative counter gross in red.
- Daily fleet-gross bar strip.
- xlsx tabs: Summary / By Counterperson / By Day / Top Parts.
- **Render via `:9225/screenshot`** — it returns JSON `{"screenshot":"<base64>"}`, decode to
  PNG. The venv's `playwright` python import is BROKEN on this box
  (`AttributeError: module 'inspect' has no attribute 'FrameInfo'`) so a standalone
  screenshot script fails; and :9225 has no POST `/screenshot` (GET only, no options).
- **Branding: use the AMERICAN MOTORS text wordmark for fleet reports.** Never `logo_0.png`
  / `logo_st.png` — both are Stevens Creek Toyota and would misbrand a fleet report.
  `vision_analyze` the PNG before sending (check for cropping + wrong branding).
- Flag a partial trailing day if run intraday (today's rows are only through the run time).

## Reading the output
- Toyota stores land ~21-23% GP; VW stores much higher (SV 45.9%, VC 31.7%) on lower volume.
- **A GM/Chevy store's low blended GP is usually the wholesale desk, not a problem.** BC
  Aug 2026 = 11.8% blended but 33.2% ex-internal: $350K of at/below-cost volume and
  **negative counter gross**, concentrated in a few counter-only reps (Matthew Murphy
  −$12.9K, Mark Corrente −$15.1K, Raymond Padilla −$4.3K, all ~100% SALES_ORDER) plus
  reman engines/transmissions sold under cost. Segment before calling it a defect.

## Files
`/home/itadmin/tekion-reports/data/parts-gross-mtd-aug2026.json` (aggregates),
`AMG-Parts-Gross-MTD-Aug2026.{png,xlsx}`.

## Pitfalls
- JWT is masked when read out of the browser → build headers in-page (see above).
- `window.__H` from a previous turn is dead after any SPA reload — rebuild every run.
- `/home/itadmin/sct-physical-2025/api-headers.json` expires (AUTH401) — don't trust it.
- Don't run while `cron-tekion.sh` is live; it drifts the dealer and owns :9223.
- Ledger is transactional, not GL-posted — it will NOT tie to the penny against
  accounting parts gross. Offer `/general-ledger/balances/all` for a GL cross-check.
