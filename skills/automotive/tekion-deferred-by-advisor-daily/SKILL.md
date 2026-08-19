---
name: tekion-deferred-by-advisor-daily
description: Build the "work deferred/declined per DAY, broken down by service advisor" report for any AMG Tekion store — advisor ranking + trailing-day trend + per-advisor RO-level detail pages (PNG/PDF/CSV). Zero OpenAPI quota.
triggers:
  - deferred by advisor
  - declined work per day by advisor
  - daily deferred report
  - deferred work daily
---

# Deferred Work by Advisor — Daily

## Scripts
- Pull:   `/home/itadmin/tekion-reports/deferred_by_advisor_daily.py <STORE> <YYYY-MM-DD> [TREND_DAYS]`
- Render: `/home/itadmin/tekion-reports/render_deferred_by_advisor.py data/<store>-deferred-by-advisor-<date>.json`
- Outputs: `data/<STORE>-Deferred-By-Advisor-<date>.{png,pdf,csv}` (PNG = page 1 only; PDF = page 1 + one page per advisor with RO-level detail — Joe's standing preference for advisor reports).

## Data source
Internal `POST /api/service-module/u/reporting/recommendation/search`, `RO_RECOMMENDATIONS`,
`status IN [DEFERRED]`, `roClosedTime BTW [dayStart, dayEnd]` in **Pacific**.
Headers from `/tmp/tekion_rec_headers.json` (see `tekion-declined-deferred-services-report` for the
passive XHR-hook re-capture). Store switch = swap `dealerId` + `tek-siteId: -1_<id>` only.
$ are **CENTS** → /100. Offset pagination is fine at day granularity (<10K rows).

## CRITICAL: the index lags ~1 day
The deferred-services index rebuilds nightly (~11:45 PM). **Today always returns 0 at all 7 stores**
(verified 2026-08-18: today=0 everywhere, yesterday=SCT 97 / BC 46 / BT 289 / SV 19 / TL 125 / AR 4 / VC 28).
Also **Sundays are legitimately 0** (stores closed) — a 0 day is not a bug.
So "today's" report = run for **yesterday**; any daily cron must be scheduled for the morning AFTER.
Filtering on `createdTime`/`modifiedTime`/`lastDeferredTime` does NOT dodge the lag — same 0.

## Advisor names
`primaryAdvisorId` (UUID) → merge caches in `data/`: `advisor-name-cache.json` (fleet, 67 ids),
plus `bc-/bt-/sct-/tol-advisor-cache.json`. Unknown → resolve via OpenAPI
`GET /openapi/v4.0.0/users/{id}` with `dealer_id=americanmotorscorporation_<id>_0`.
**Gotcha:** `r["data"]` is sometimes a LIST — use `r["data"][0] if isinstance(list)`.
Name at `userNameDetails.completeNames[DISPLAY_NAME]`. Write new ids back to `advisor-name-cache.json`.
Note some ids resolve to non-advisor personas (e.g. BC `8c0d2da8…` = Dale Alexander, INVENTORY_MANAGER)
— they still carry deferred lines as RO primary advisor; keep them but don't assume they're writers.

## Reference run (BC / 1251, Mon 8/17/2026)
46 declined lines · 20 ROs · $23,179.47 · 21 Critical. Michael Reyes #1 ($6,233).

## Pitfalls
- `pdfinfo`/`pdftoppm` are NOT installed — QA extra PDF pages by re-rendering the HTML in Playwright
  and screenshotting a single `.page` div, then `vision_analyze`.
- Store brand colors/labels live in the `BRAND` dict of the renderer — add new stores there.
