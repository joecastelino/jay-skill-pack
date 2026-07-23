---
name: tekion-apc-docs-scraper
description: Log into the Tekion APC partner portal (apc.tekioncloud.com) and download the full OpenAPI 3.1 specs for every REST API endpoint and every webhook event. Single continuous Playwright session (APC sessions don't persist). Use when building/maintaining the DealerDetail Fixed Ops app or any tool that needs the authoritative Tekion API/webhook schemas.
triggers:
  - download tekion api specs
  - apc portal docs
  - tekion openapi specification
  - tekion webhook schema
---

# Tekion APC Docs / Spec Scraper

Pulls the authoritative OpenAPI 3.1 JSON specs from the Tekion APC partner portal.
Two doc trees: **REST APIs** (`/apis`, 20 sections, 270 endpoints as of the
2026-07-10 Enterprise Tier 1 upgrade) and **Webhooks** (`/webhooks`, Deals +
**Repair Order** + Vehicle Inventory — RO webhooks ro.created/ro.status.updated/
ro.invoice.status.updated/ro.job.created were ADDED with Enterprise Tier 1).
After any plan/app-version upgrade, run the full audit — see skill
`tekion-api-upgrade-audit` (rescrape + catalog diff + live scope probes).

## Critical facts (all verified 2026-06-15)
- **Account: `jcastelino@americanmotorscorp.com`** (the AMC email — the DMS
  `scvolkswagen.com` email does NOT work here) + DMS password `<TEKION_PASSWORD>`
  + 6-digit email OTP.
- **OTP email subject: "Your Login OTP is Here"** (different from the DMS
  "Tekion-Login OTP"). Read via himalaya `[Gmail]/All Mail`.
- **Session does NOT persist** — `storage_state` lands you back at /user/login.
  Do login + ALL scraping in ONE continuous Playwright run.
- **Headless chromium shell binary is missing** on this box. Launch the HEADED
  chromium under xvfb instead:
  - exec: `/home/itadmin/.hermes/profiles/jay/home/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome`
  - wrapper: `HOME=/home/itadmin xvfb-run -a python3 <script>`
  - himalaya is on PATH at `/home/itadmin/.local/bin`

## Login flow (exact)
1. Email field is `input#WORK_EMAIL` (type=text, NOT type=email) → `fill` it →
   click the **Next** button (`get_by_role("button", name="Next", exact=True)`).
2. Two-step: `wait_for_selector("input[type=password]")` → fill → click **Login**.
3. OTP = six `input[type=tel]` boxes: click box[0], then
   `page.keyboard.type(code, delay=120)` (auto-advances) → click **Verify**.
4. Post-verify `page.url` may still read /user/login but you ARE in. Just
   `page.goto()` the docs URL in the same session.
5. Use `wait_until="domcontentloaded"` (NOT networkidle — the SPA never idles).

## Docs navigation
- REST index: `/app/docs/versions/4.0.0/apis` — 20 sections in the left nav.
- Webhooks: `/app/docs/versions/4.0.0/webhooks/<event>` — SEPARATE top-level tree.
- The nav uses router **divs, not `<a>` tags** → expand a section by clicking its
  name with `get_by_text(name, exact=True)`. Endpoint names are the nav lines
  between the section header and the next section header.
- Each endpoint/event page has a **"Download Specification"** button →
  `page.expect_download()` captures the OpenAPI 3.1 JSON. Use a context with
  `accept_downloads=True`.

## Ready-to-run scripts
- `~/dealerdetail/specs/apc_full_spec_downloader.py` — walks all 20 REST sections,
  downloads every endpoint spec → `~/dealerdetail/specs/apis/<section>__<endpoint>.json`,
  writes `api_catalog.json` (section→endpoints).
- `~/dealerdetail/specs/apc_webhook_spec_downloader.py` — same for webhook events →
  `~/dealerdetail/specs/webhooks/`, writes `webhook_catalog.json`.
- `~/tekion-reports/apc_docs_scraper.py` / `apc_webhooks_scraper.py` — lighter
  index-only scrapers (no per-endpoint download).

These are long runs (266 specs ≈ 11 min). Run in the background with
`notify_on_complete=true` and `watch_patterns=["DONE","No OTP","Traceback"]`.

## Verification
After a run: every file should be valid JSON with `openapi`/`paths`/`components`
keys (not a <500-byte empty shell). `api_catalog.json` should show 20 sections.
High-value sections for Fixed Ops: Repair Order (42), Vehicle Inventory (54),
Deals (70), General Ledger Data, Service Appointments, Parts Inventory.

## API-upgrade audit workflow (verified 2026-07-10)
When Joe says "we upgraded the API, what's available now?", do BOTH a docs diff and a live scope probe:

1. **Archive baseline, re-scrape, diff.**
   ```
   cd ~/dealerdetail/specs
   mv apis apis_baseline_YYYYMMDD; cp api_catalog.json api_catalog_baseline.json
   mkdir -p apis && HOME=/home/itadmin xvfb-run -a python3 apc_full_spec_downloader.py
   ```
   Then diff endpoint sets per section between `api_catalog_baseline.json` and the new
   `api_catalog.json` (set difference on `endpoints` lists). 2026-07-10 diff: Repair Order
   42→49 (added recommendations, internal-notes, ro-warranty-claims, clock-entries),
   Deals 70→67, Service Appointments swapped one endpoint.

2. **Live scope probe** — docs presence ≠ granted. Probe one representative READ endpoint
   per section against prod with the real token (`~/tekion-api/tekion_client.py`,
   `cfg=load_config(); tok=get_token(cfg)`). Get the real paths from the spec files
   (`paths` key), don't guess — guessed paths give 404s that look like denials.

3. **Interpret status codes:**
   - `200` or `400` (param complaint like "searchText is required") = **GRANTED** — 400 means
     you reached the handler with bad params.
   - `403 "The app version 0.0.0-pilot-X installed in the dealer does not support this API
     version"` = **NOT GRANTED — installed app version too old**. This blocks per-dealer even
     when the endpoint exists in docs; verified identical at all 7 stores. Fix = ask Joe/Tekion
     to bump the installed app version.
   - `403 "Missing or invalid context headers"` = **YOUR BUG, not scope**: the `dealer_id`
     header must be the FULL string `americanmotorscorporation_<num>_0` (from
     `~/tekion-api/config.json` `dealers` map), NOT a bare number like `876`. Bare number
     produces this misleading 403 on every endpoint.

4. **Response shape for repair-orders:search**: rows are at `out['data']['results']` and the
   RO id field is `documentId` (there is no top-level `id`; `repairOrderNumber` can be null).

State as of 2026-07-10: GRANTED = Customer, Deals, Employee/Users, GL Data, Parts Inventory,
Repair Order, Service Appointments, Vehicle Inventory. GL specifics: `/general-ledger/balances/all`
needs startDate+endDate (epoch ms); `/differential` ALSO needs `clientCurrentTime` +
`refreshWindowTime` or it 400s `unexpected.error`. GL amounts are DOLLARS (not cents, unlike RO $).

## Plan Details page (Enterprise Tier 1, verified 2026-07-10)
- `https://apc.tekioncloud.com/app` redirects to `/app/plan-details` — THE page showing
  the actual entitlements: Product Suite tabs = Dealer Level APIs / Partner Level APIs /
  Feeds / Historical Extracts / Webhooks. No other portal sections exist (guides/usage/
  analytics/feeds URLs all 404; portal = plan-details + docs only).
- Enterprise Tier 1 actuals (differ from the marketing sheet): overall quota
  **2,000,000/30d**, throttle **7,500/15min**, 200 installations. PER-ENDPOINT quota +
  throttle table with ~304 entitled dealer-level APIs (each has own limits, e.g.
  Search-type APIs 200K/30d @ 200/15min).
- The Dealer Level APIs table is VIRTUALIZED — page.inner_text only sees ~25 rows.
  Harvest by accumulating inner_text lines while scrolling every scrollable div
  (scrollTop += 400, loop until 20 stagnant iterations). Saved dumps:
  `~/dealerdetail/specs/plan-details/*.txt`.
- Feeds tab: GL Data Premium = HOURLY; Deals/Parts Inv/Vehicle Inv Standard+Premium = Daily.
  Historical Extracts: Deals 20-year lookback. Webhooks tab lists all 24 subscribed-able
  events (5 Deals + 4 Repair Order + 15 Vehicle Inventory).
- Plan entitles APIs the installed dealer app version may still 403 on
  ("app version 0.0.0-pilot-2.0.0 does not support") — entitlement ≠ installation.
  Notable entitled-but-blocked: RO recommendations/internal-notes/warranty-claims/
  clock-entries, Update Repair Order Status, Create a GL Posting, Credit Application APIs.

## Related
- After scraping webhook schemas, the natural next step is subscribing to them —
  see the `webhook-subscriptions` skill for the Hermes webhook receiver side.
- For LIVE data (not docs/schemas) use the OpenAPI client — see
  `tekion-openapi-repair-orders` (token-based, no browser, colon-action endpoints).
- Specs land in the DealerDetail project: `~/dealerdetail/specs/` (REST + webhooks
  + `api_catalog.json`/`webhook_catalog.json` + README). The app repo is
  `~/dealer-detail` (github.com/oalsadoon-vw/dealer-detail, public).

## User Guide (found 2026-07-10)
Lives at `/app/user-guide/api` (NOT linked obviously; direct URL works when logged in). 10 sections in left nav: Getting Started, Testing Playground, Feeds, Historical Extracts, Partner Level APIs, Pilot And Release Process, My Configurations, Webhooks, Apps, Custom Apps. Section slugs differ from nav labels (Webhooks→`/user-guide/webhook` singular, Feeds→`/user-guide/outbound-feeds`) — navigate by CLICKING the nav text (MouseEvent dispatch), not by guessing URLs, then wait ~5s (SPA lag: reading innerText too fast captures the PRIOR page). Full scrape saved at `/home/itadmin/dealerdetail/specs/user-guide/*.txt`; scraper `/tmp/ug_scrape.py` pattern (clicks each nav item, waits, dumps innerText).

Key operational facts from the guide: token generation capped at 20/15min; sandbox base `https://api-sandbox.tekioncloud.com/openapi` with dealer `techmotors_4_0`; webhook auth = HMAC-SHA256 of payload vs secret, compare `X-Hub-Signature-256` header; webhook/SFTP source IPs to whitelist: 52.42.159.151, 35.85.110.130, 35.163.78.152; historical extracts limited to once/month/dealer; exit-pilot = kebab → Request Release → approval → Publish App.

## Pitfalls
- Don't use `sed` to edit the scripts — use the patch tool (whitespace-sensitive React selectors).
- If "Download Specification" click 404s the slug, expand the section on the index
  page and click the endpoint name instead of navigating by URL.
- OTP races: count baseline "Your Login OTP" emails BEFORE submitting password,
  then wait for the count to increase before reading the code.
- **DEFAULT-EXPANDED SECTION TRAP (hit 2026-06-15, AGAIN 2026-07-10):** the FIRST section in a tree is
  often already expanded on page load. A generic "click section name to expand" loop
  will then *collapse* it → the parser sees 0 events/endpoints and silently skips it.
  On the Webhooks tree, **Deals** is expanded by default; the main run logged
  `[+] Deals: 0 events` and only got Vehicle Inventory. 2026-07-10 variant: the walker
  saved the Deal Created page as `deals__repair-order.json` when a NEW "Repair Order"
  section appeared — it mis-associates section headers with the wrong content. Fix: don't blindly toggle the
  first section. Either (a) check whether its child rows are already visible before
  clicking, or (b) hard-code the known event names and click each one directly
  (see `~/dealerdetail/specs/apc_deals_webhook_fixup.py` — the 5 Deals events:
  Deal Created, Deal Delivery Date Promised, Deal Status Updated, Deal Vehicle
  Delivered, Deal Vehicle Delivery Reported). For any NEW section, verify against
  raw nav text (`page.inner_text("body")`) first, then use a targeted per-event script.
- **Chrome exec path is under the PROFILE home**, not bare `~/.cache`:
  `~/.hermes/profiles/jay/home/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome`.
  Launching from `/home/itadmin/.cache/...` fails "executable doesn't exist" — two
  wasted launches before this was caught. Verify the file exists before launching.
- **Diagnose unknown form fields by dumping inputs**, don't guess selectors. The login
  email field is `input#WORK_EMAIL type=text` — `input[type=email]` 30s-timeouts.
  `page.query_selector_all("input")` + print type/name/id/placeholder reveals the truth fast.
- Known webhook totals for cross-check: **24 total = 5 Deals + 4 Repair Order + 15 Vehicle
  Inventory** (Enterprise Tier 1, 2026-07-10; Standard plan had 22 = 5 + 17, no RO).
  If a run reports fewer, a section was collapsed/skipped — re-run the fixup for it.
