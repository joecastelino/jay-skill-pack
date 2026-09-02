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

## Step 0 (DO THIS FIRST): local fleet probe beats the portal for "which store"

Before touching APC at all, run the 30-second local probe — it answers the
single most important question (one store vs app-wide) without any browser:
```bash
cd /home/itadmin/tekion-reports
/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11 -u _fleet_quota_probe_20260902.py
```
Walks all 7 dealers search → jobs → operations, 8s pacing, one line per store.
**Signature: search 200 + jobs 200 + operations 429 DEALER_QUOTA on exactly one
store = per-dealer 30-day ceiling.** If every store 429s on *search*, it's
`OVERALL_QUOTA` — different problem, different fix.

Then quantify WHO spent it from the dealer-detail DB (no portal needed):
```sql
SELECT s.abbreviation, SUM(r."apiCallCount"), COUNT(*)
FROM "SyncRun" r JOIN "Store" s ON s.id = r."storeId"
WHERE r."startedAt" > now() - interval '30 days'
GROUP BY s.abbreviation ORDER BY 2 DESC;
```
(Column is `abbreviation` not `abbrev`; RO count is `rosFetched`. No `psql` on
this box — run via `npx tsx` + Prisma `$queryRawUnsafe` from `apps/web`.)
Measured 2026-09-02: BC 107,602 · BST 88,991 · ARSJ 16,241 · SCVW 13,012 ·
TOL 8,932 · SCT 6,412 · VWC 2,522. **The blocked store was SCT — the LOWEST
dealer-detail spender.** So a big sync total does NOT identify the culprit;
the blocked store's quota was drained by its own many small consumers plus dead
recovery watchers. Only escalate to the APC Transaction Dashboard once these two
local checks disagree with each other or you need per-endpoint attribution.

⚠️ **APC session expires and needs a fresh OTP login.** On 2026-09-02 `:9224`
navigated straight to `/user/login?redirectTo=...` — the "session persists across
days" note is not reliable. Budget for the OTP flow, which is another reason to
exhaust the local checks above first. Also: the persistent-browser-apc server has
**no `/goto` endpoint** — it's `POST /navigate` (plus `/eval /click /type /press
/mouse /cookies /console` and `GET /health /url /screenshot /snapshot`). Verify
with `grep -oE "app\.(get|post)\('/[a-z-]+'" server.js`.

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

## CONFIRMED ROOT CAUSE PATTERN: self-inflicted watcher pile-up (verified 2026-08-05)

The suspect flagged in the first investigation turned out to be the actual cause.
**A prolonged single-store DEALER_QUOTA outage that "won't clear" is very likely
YOUR OWN recovery watchers, not a Tekion-side problem** — especially if the outage
spans multiple context-compaction/session boundaries. What happened:

- Across several sessions (spanning Aug 1 → Aug 5), THREE separate SCT quota-recovery
  watchers got launched at different times to self-heal different reports (Opened
  Menu Sales, Closed MTD, Alignment-by-advisor), each with its own probe-then-scan
  loop. Each new session that hit the SCT outage launched ANOTHER watcher without
  realizing the earlier ones were still alive — because after context compaction,
  the assistant's summary doesn't always carry forward "there are already N
  background watchers running against this store."
- The Transaction Dashboard raw text showed the smoking gun: a repeating 6-call
  burst (`Search Repair Order x4 (200) → Get Jobs (200) → Get Operations (429)`)
  firing every ~10-15 minutes, non-stop, for the entire ~20-hour outage — plus a
  SEPARATE lone `Get Operations → 429` every ~10 min from a third watcher. That
  volume (700-1000+ calls over the outage window, ALL hitting the one exhausted
  bucket) is very plausibly why the bucket never got a clean window to refill if
  429 responses still count against the request/quota counter (common behavior).
- **Fix**: kill ALL recovery watchers touching that dealer, confirm process list is
  clean, THEN wait and do a single manual probe later — don't relaunch a watcher
  immediately. If it clears once left alone, that confirms self-inflicted; if it's
  still 429 after a genuinely quiet window, THEN it's a real Tekion-side issue worth
  escalating to support.

### MANDATORY: watcher census BEFORE root-causing any "quota won't clear" ticket

Before concluding a store-specific 429 outage needs a support ticket, always run a
full census for pre-existing self-built recovery infrastructure targeting that
dealer — don't trust your own memory/context summary, they get lost across
compaction:

```bash
ps aux | grep -iE "sct|<storecode>|<dealerid>" | grep -v grep   # live watcher processes
ps aux | grep -E "wait_ops|watcher|selfheal|quota_guard" | grep -v grep
crontab -l | grep -v '^#'                                       # cron-launched watchers
ls -la /tmp/*quota*.lock /tmp/*recovery*.lock /tmp/*selfheal*.lock 2>/dev/null
find /home/itadmin/tekion-reports -iname "*selfheal*" -o -iname "*watcher*"
```
Kill every hit before doing anything else. A stray watcher from 1-4 days ago
(`selfheal_sct_align_20260804.sh` in the verified case) is exactly the kind of thing
that survives silently because it has no notify_on_complete and its parent session
is long gone.

## `api-metrics/search` requires ambient app headers — cold fetch() calls 401

Attempted to bypass the filter-UI entirely by calling
`POST /api/apc-core/u/vendor/api-metrics/search` directly via in-page `fetch()`
with a hand-built JSON body (filters/sortList/rows/searchText/includeFields) — this
consistently returned `401 {"message":"Missing Mandatory Headers!"}` even from
inside the authenticated page context. Captured (via XHR/fetch hook on the app's
OWN calls) the actual headers the app's axios-equivalent attaches automatically:
`tekion-api-token`, `tenantId`, `userId`, `workspaceId`, `originalTenantId`,
`originalUserId` (plus Sentry trace/baggage headers, non-functional). These are NOT
regular cookies — they're injected by an interceptor a bare in-page `fetch()` does
NOT get for free, same "bare fetch fails auth" pattern documented for the DMS app
proper in the `persistent-browser-server` skill. **Do not waste time hand-building
the request body and calling fetch cold — it will 401 regardless of how correct the
body shape is.**

### What actually works: drive the app's own search, then read the DOM

Instead of fighting the filter-panel multi-select dropdowns (painful, see section
above) or hand-calling the API (401s), the fastest reliable method is:
1. Click the **"Search on Request ID"** text box (a real, simple `<input>`, easy to
   target reliably) and press a key + Enter — ANY keystroke triggers the app to
   refire its own `fetch()` (with correct headers) against `api-metrics/search`,
   which you can observe via an XHR/fetch hook if you want the raw JSON, OR:
2. Just clear the search box (Backspace + Enter) to restore the full unfiltered
   result set, then `document.body.innerText` — the rendered table rows already
   contain API Endpoint, HTTP Status, Request Time, Dealer, App Name as plain text,
   sorted Request Time DESC. This answered "which store, which endpoint, what
   status, how often" in a single innerText read with ZERO filter-UI interaction.
3. Confirmed request-body shape (for reference, in case a future session wants to
   retry the direct-API route via the DMS app's own already-authenticated context
   rather than APC's separate auth):
   ```json
   {"filters":[{"field":"requestTime","filterType":"BTW","values":[msStart,msEnd]}],
    "sortList":[{"field":"requestTime","order":"DESC"}],
    "rows":200,"searchText":"","countRequired":true,
    "includeFields":["traceId","statusCode","requestTime","apcMethod","responseCaptured",
     "id","vendorId","externalDealerSiteId","appKey","apiName","apcPath","responseTime",
     "apiVersion","tekionOemId","tekionProgramId","testCall","tier","vendorUserId","vendorWorkspaceId"]}
   ```
   Dealer filter field is presumably `externalDealerSiteId` (matches the dealer
   string shown elsewhere, e.g. `americanmotorscorporation_876_0`) but this was
   never confirmed to work standalone — every direct-body attempt 401'd regardless
   of field names tried.

## Status log
- 2026-08-05: Confirmed via Transaction Dashboard raw text (no filters needed) that
  SCT-only was throwing 429 DEALER_QUOTA on `GET .../jobs/{id}/operations` while
  every other visible row (all 7 dealers, Search Repair Order / Get Jobs) was 200.
- 2026-08-05 (same day, follow-up): Root-caused it further — the repeating 6-call
  burst pattern in the dashboard log was traced to THREE of Jay's own forgotten SCT
  recovery watchers (two from same-day sessions, one running unnoticed since Aug 4)
  polling every 10-15 min. Killed all three; confirmed dashboard log volume was
  self-inflicted, not Tekion-side. `api-metrics/search` direct-fetch approach 401'd
  (missing ambient auth headers) — DOM-text-read-after-simple-search-box-interaction
  is the reliable method going forward, not hand-calling the API.
