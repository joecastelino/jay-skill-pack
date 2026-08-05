---
name: tekion-apc-quota-usage-investigation
description: Investigate REAL Tekion OpenAPI quota/429 usage per dealer using the APC portal's Transaction Dashboard (ground truth, not assumptions) — find which store/endpoint is burning quota, when Joe says "don't assume, go check the APC portal". Also covers what Plan Details and Usage Dashboard actually show (and don't).
triggers:
  - why is only one store hitting quota
  - check apc transaction dashboard
  - don't assume go check tekion apc
  - what's using our api quota
  - 429 dealer quota investigation
---

# Tekion APC Quota/Usage Investigation

Use this whenever a DEALER_QUOTA or OVERALL_QUOTA 429 needs root-causing with HARD
DATA instead of inference from our own scraper logs. Joe explicitly wants "go on the
Tekion APC and see what's actually going on, I don't want assumptions" — this skill
is how you answer that with live evidence.

## Prerequisite: persistent APC browser on :9224

Check first: `curl -s -m 5 http://localhost:9224/health`. If not responding, start it:
```bash
cd /home/itadmin/persistent-browser-apc
HOME=/home/itadmin xvfb-run -a node server.js > /tmp/pb9224_start.log 2>&1
```
Run via `terminal(background=true)` — a bare `&` foreground command errors out.
Wait ~6s, re-check `/health`. If the browser context is already logged in (it usually
is — session persists across turns/days), `POST /eval {"js":"window.location.href"}`
will show `about:blank` (fresh tab) but navigating to any `/app/...` URL lands you
authenticated without a fresh OTP login. Only fall back to full OTP login (see
`tekion-api-upgrade-audit` skill Step 8 APC browser automation note) if you land on
a login page.

## The three portal tiles that matter (9-dot grid, top-left ≈22,32)

1. **Plan Details** (`/app/plan-details`) — shows **QUOTA LIMITS ONLY**, not actual
   usage. Table of every API name with "Quota Limit Per Dealer Per 30 days" and
   "Throttle Limit Per Dealer Per 15 mins". Useful to know the ceiling, useless for
   "what's actually being consumed."
2. **Usage Dashboard** (`/app/usage-dashboard`) — **PAYWALLED**. Renders "Access
   Denied — To access Usage Dashboard, please reach out to Tekion APC Team and
   upgrade your account to new pricing plans." Don't waste time here; it's not a
   config issue, it's a plan-tier lock.
3. **Transaction Dashboard** (`/app/transaction-dashboard/list` — NOTE the `/list`
   suffix, guessing `/app/transaction-dashboard` alone 404s) — **THIS is the ground
   truth**. Per-request log: API Endpoint, HTTP Status, Request ID, Request Time,
   Response Time, App Name, Dealer, OEM ID, Program ID, Product Tier, User Name.
   Has tabs API / Feeds / Historical Extracts. This is where you find exactly which
   dealer + which endpoint + what HTTP status, request by request.

Don't guess these routes from memory — click through the 9-dot grid tile each time
(find the tile div by exact innerText via eval, click its center) since routes can
shift; verify via `/url` after navigating.

## Reading data without fighting the filter UI (recommended shortcut)

The Transaction Dashboard's own default view (no filters) already shows the most
recent rows across ALL dealers, sorted by Request Time descending. For a quick "is
it just one store" check, just read `document.body.innerText` on the unfiltered
page — Dealer name and HTTP Status are both in the visible text of every row. This
answered "is it SCT-only" in under a minute without any filter interaction.

## The filter panel — pitfalls (if you actually need aggregate counts)

The left filter panel is a rules-builder: each row = Field dropdown / Operator
dropdown / Value multi-select. Confirmed painful to drive via blind mouse
coordinates:

- **Filter panel toggle** = the `icon-filter` div at ~(88,214). Panel state
  (open/expanded rows) SURVIVES toggling closed and reopening — don't assume you
  lost your filter progress.
- **Add Filter** link position drifts depending on how many rows already exist —
  always re-query it by exact innerText match, don't hardcode y-coordinates between
  turns.
- **Field-name dropdown** (3rd/4th row) opens a list (Application Name, Response
  Time, Product Tier, Sandbox, API Version, User Name, HTTP Status, Dealer Name...)
  — click the exact option by innerText match, not by assumed row height.
- **Value multi-select** (Dealer Name, HTTP Status, etc.) is a virtualized
  react-select-style list with its own internal search input. Typing into the WRONG
  input (there are multiple `<input>`s on the page including the global date-picker)
  can accidentally open a date/time picker calendar instead — always verify with a
  screenshot after typing, don't assume the type landed where intended.
- **"N Selected" summary text can be STALE/wrong** relative to the actual
  `input[type=checkbox]:checked` DOM state (saw "2 Selected" when only 1 checkbox
  was actually checked). ALWAYS verify the real selection via:
  `document.querySelectorAll('input[type=checkbox]')` filtered to `.checked`, not
  the summary label.
- **Two "Apply" buttons stack near each other**: one closes just the value dropdown,
  one applies the whole filter panel and refetches the table. Distinguish by
  `getBoundingClientRect()` — after clicking the dropdown-level Apply, re-query for
  the panel-level Apply button fresh (its y-coordinate shifts once the dropdown
  collapses).
- Net lesson: for anything beyond a quick "which store" glance, driving this UI
  reliably burns a lot of turns. Prefer the API-hook method below instead.

## Better method: hook the underlying metrics API directly

The Transaction Dashboard's own frontend calls a real backend endpoint you can query
directly once you know its shape — found via performance entries:
```js
[...new Set(Array.from(window.performance.getEntriesByType('resource'))
  .map(r => r.name).filter(n => n.includes('/api/')))]
```
Revealed: `POST https://apc.tekioncloud.com/api/apc-core/u/vendor/api-metrics/search`
— this is almost certainly the real aggregation endpoint behind both the Transaction
Dashboard table AND (probably) the paywalled Usage Dashboard. To learn its exact
request/response schema without more blind UI clicking, hook `window.fetch` BEFORE
triggering any dashboard action (refresh icon, filter apply, tab switch):
```js
window.__captured = [];
var _fetch = window.fetch;
window.fetch = function(...args) {
  var url = args[0], opts = args[1] || {};
  if (String(url).includes('api-metrics/search')) {
    var reqBody = opts.body;
    return _fetch.apply(this, args).then(r => {
      var rc = r.clone();
      rc.text().then(t => window.__captured.push({url:String(url), reqBody, respBody:t.slice(0,3000)}));
      return r;
    });
  }
  return _fetch.apply(this, args);
};
```
Then click the refresh icon (`icon-refresh` class, near the result-count text) or
change any filter, then read `window.__captured` via eval. Once you have the real
request body shape (likely `{dealerId, startDate, endDate, apiName, ...}` similar to
other apc-core search endpoints), you can call it directly with different
date/dealer params instead of fighting the multi-select UI — same pattern as the
"Tekion BULK VELOCITY API" and "PART TRANSACTION LEDGER API" tricks already used
elsewhere (see Jay's memory: XHR/fetch hooking to reverse-engineer internal Tekion
endpoints is a proven, repeatable technique).

## Screenshot capture gotcha

`GET /screenshot` on the persistent-browser-apc server returns `{"screenshot":
"<base64 PNG>"}` as JSON, NOT a raw PNG file — `vision_analyze` rejects the raw
response ("Only real image files are supported"). Always decode first:
```python
import json, base64
d = json.load(open('/tmp/shot.json'))
open('/tmp/shot_real.png','wb').write(base64.b64decode(d['screenshot']))
```
then pass the `_real.png` path to `vision_analyze`.

## Status log
- 2026-08-05: Confirmed via Transaction Dashboard raw text (no filters needed) that
  SCT-only was throwing 429 DEALER_QUOTA on `GET .../jobs/{id}/operations` while
  every other visible row (all 7 dealers, Search Repair Order / Get Jobs) was 200.
  Discovered `api-metrics/search` endpoint as the likely real quota-usage source but
  did not finish capturing its schema — next session should hook fetch, trigger one
  dashboard action, and read `window.__captured` to get the exact request/response
  shape, then query it directly filtered to dealer=876 across API names to identify
  which specific job/endpoint is consuming SCT's quota disproportionately (candidate
  suspects: SCT Menu Sales Opened/Closed MTD scorecard scans, or the 15-min
  recovery-watcher retry loops themselves compounding the drain during the outage).
