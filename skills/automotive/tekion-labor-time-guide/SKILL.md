---
name: tekion-labor-time-guide
description: Look up or bulk-pull Tekion's Labor Time Guide (OEM warranty labor-time data) for any store/vehicle. Covers the nav path, the underlying API (VIN or Make/Year/Model search), pagination, and the critical fact that THERE IS NO DOWNLOAD/EXPORT BUTTON in the UI — it's a live per-vehicle OEM feed, not a static file. Use when Joe asks to "download the labor time guide", "get OEM labor times", or look up warranty hours/parts/failure codes for a repair.
---

# Tekion Labor Time Guide

## What it is
The Labor Time Guide (LTG) is a standalone app tile that surfaces OEM-provided
warranty labor-time data (hours, material allowance, parts, failure codes, TSB/recall
numbers) per opcode, for a specific vehicle. It's normally accessed inline from within
an RO, but the standalone tile lets you look it up before/without an RO. KB0010775
("SERVICE APPS: Labor Time Guide") is the official doc — thin, UI-focused, no API detail.

**IMPORTANT — there is no bulk download/export.** The UI has zero Download/Export
buttons (verified 2026-08-05 by scanning `[class*=download],[class*=export]` — empty).
It's a live OEM feed queried per-vehicle; the manufacturer pushes updates on their own
cadence (real-time/biweekly/monthly depending on OEM). If Joe asks to "download the
labor time guide", **scope the ask first** — a single 2018 Camry alone returned
**1,471 opcodes**; a true full-catalog pull means looping every model × model-year,
which is a much bigger job than a UI export.

## Nav path (verified SCT/876, 2026-08-05)
1. Ensure the right dealer is active (`localStorage.currentActiveDealerId`) — see tekion-sitemap dealer switch.
2. App Grid (nine-dot icon, top-left ~x22,y32) → click it → "Labor Time Guide" appears
   under **Recently Used Apps** if used before (tile abbreviation "LG"); otherwise use
   the App Grid search box.
3. Direct URL once discovered: `https://app.tekioncloud.com/ro/labor-time-guide`
   (navigable directly like other SPA screens per tekion-sitemap rule 2).
4. Landing page = "SELECT VEHICLE DETAILS TO VIEW LABOR TIME GUIDE" with:
   - `input[placeholder="Search by VIN"]` (ant-input, straightforward `/type`-able)
   - OR three cascading selects: Select Make → Select Year → Select Model (these
     render as placeholder DIVs, not real `<input>`s, until clicked — see gotcha below)
   - `button` with exact text "Search" (bottom, ~x672,y410 on a 1280-wide viewport)

## Gotcha: Make/Year/Model dropdowns are NOT plain selects
Clicking the "Select Make" placeholder div focuses a REAL hidden `<input>` for typeahead,
but React re-renders the dropdown per keystroke so a value written via native setter
gets accepted as the input's value yet the dropdown list itself may not populate
reliably via headless `/type`. **VIN search is far more reliable** — one input, one
button, no cascading dropdown fuss. Get a VIN from any store's VI JSON
(`~/the-goods/data/<code>.json`, field `vin`) if you don't have one handy.

## The API (the actual reusable asset)
Three XHR calls fire on Search (captured via XHR-hook per tekion-sitemap pattern):
1. `POST /api/servicevehicle/u/v2/vehicle/vinlookup` — VIN decode (only fires for VIN search)
2. `POST /api/service-module/u/vps/laborTimeCategory` — category tree (left rail 00,01,02...71,72...)
3. `POST /api/service-module/u/vps/labor-time/all` — **the actual data**, paginated

### Request body (labor-time/all)
```json
{
  "vin": "4T1B31HK5JU506571",
  "partialLaborOpcodeDescription": "",
  "make": "Toyota",
  "model": "Camry",
  "year": 2018,
  "pageInfo": {"start": 0, "rows": 100},
  "root": null
}
```
`partialLaborOpcodeDescription` = free-text filter on opcode description (leave "" for all).
`pageInfo.rows` — tested up to 100 via UI-driven request (raw `fetch()` replay with a
bare `fetch` FAILED with 500 "Token doesn't exist or is invalid" — the app's axios
interceptor injects auth a plain in-page `fetch` doesn't get; **must drive the UI itself**
via XHR hook capture, not replay-by-fetch. See tekion-sitemap "internal data APIs" pattern
— same auth trap as the parts velocity endpoints.)

### Response shape
```json
{
  "data": {
    "vin": "...", "year": 2018, "make": "Toyota", "model": "Camry",
    "count": 1471,
    "pageInfo": {"start": 0, "rows": 100},
    "sortKeys": [{"key":"opCode","displayName":"Opcode"}, {"key":"opCodeDesc",...}],
    "data": [
      {"opCode":"322996","opCodeDescription":"OTHERS",
       "category":{"name":"05","alias":"05","subCategory":{"name":"10","alias":"10","leaf":true},"leaf":false}}
      // ... `rows` entries per page
    ]
  }
}
```
`count` = total rows for that vehicle (paginate `pageInfo.start` by `rows` until `start >= count`).
Clicking an individual opcode row surfaces the FULL detail (Labor Action Code, hours,
material allowance, parts info, supply info, failure codes, related opcodes per KB0010775)
via a presumed opcode-detail endpoint — not yet captured; would need one more XHR-hook
pass on an opcode click if per-opcode detail (hours/parts) needs to be bulk-harvested too.
The list endpoint above only returns opCode/description/category, NOT hours — hours are
on the detail view per opcode.

## CRITICAL — pagination wall (confirmed 2026-08-08, control-tested)
`labor-time/all` reliably returns data for the first ~75-100 rows (small page sizes,
e.g. rows=25-50, work fine for early offsets) but **past roughly offset 75-100 the
endpoint starts throwing a bare 500 and never recovers**, regardless of:
- page size (tried 100, 50, 25 — same wall, just at different offset/page-count)
- dealer (reproduced identically on SCT/876 AND BC/1251 — NOT store-specific)
- vehicle (reproduced on multiple different VINs/models — NOT vehicle-specific)
This means it's a genuine bug/hard limit in Tekion's own API, not something to retry
or back off around from our side. **A full bulk export of a vehicle's ~1,400+ opcode
list is NOT currently achievable via this endpoint** — only the first ~75-100 rows are
retrievable. Do not sink more time into pagination workarounds (retry/backoff loops,
token refresh between batches, slower pacing) — all were tried 2026-08-08 and none
cleared the wall. If Joe needs the full list, this is a "report to Tekion/APC support
as an API bug" situation, not a scripting problem.

## If Joe wants an actual bulk export
1. Get explicit scope: which make(s), which model(s)/year(s) — do NOT default to "all Toyota ever".
2. For the requested scope, loop `labor-time/all` with pagination (rows=100) per model/year
   to harvest the opcode/category list — driven through the UI (not raw fetch, per auth trap above).
   **Expect to only get the first ~75-100 rows per vehicle** per the pagination wall above —
   set that expectation with Joe BEFORE running the full loop, not after.
3. If Joe wants HOURS per opcode (not just the code/description list), a second harvest pass
   is needed hitting the opcode-detail endpoint — capture it first via one manual opcode click
   with the XHR hook installed, same pattern as this skill's discovery method.
4. Export to Excel/CSV, not a screenshot — this is tabular OEM reference data.

## Related skills
- tekion-sitemap — dealer switch, App Grid nav, internal-API auth-trap pattern (fetch 500s, must drive UI)
- tekion-opcode-labor-billing-audit — audits BILLED labor hours on ROs (downstream of LTG, not the same thing)
- persistent-browser-server — the :9223 HTTP API used throughout
