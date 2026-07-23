---
name: tekion-api-upgrade-audit
description: Audit what changed after a Tekion APC API plan/scope/app-version upgrade — rescrape specs, diff the catalog, live-probe every section for scope (read AND write) safely without touching production data. Use whenever Joe says the API was upgraded, a new tier was purchased, premium docs were authorized, or the installed app version was bumped.
triggers:
  - tekion api upgrade what's available
  - api scope audit
  - did the tekion upgrade unlock anything
  - probe tekion write access
---

# Tekion API Upgrade Audit

The full procedure for answering "we upgraded the API — what can you do now?"
Verified end-to-end 2026-07-10 (Enterprise Tier 1 upgrade).

## Step 1 — Rescrape the APC spec catalog (background, ~10 min)

```bash
cd /home/itadmin/dealerdetail/specs
mv apis apis_baseline_YYYYMMDD          # archive old specs
cp api_catalog.json api_catalog_baseline.json
mkdir -p apis
HOME=/home/itadmin xvfb-run -a python3 apc_full_spec_downloader.py
```
Run as `terminal(background=true, notify_on_complete=true, watch_patterns=["No OTP","Traceback"])`.
Login/OTP mechanics = skill `tekion-apc-docs-scraper` (AMC email, "Your Login OTP is Here").

## Step 2 — Diff the catalog

```python
old = json.load(open('api_catalog_baseline.json'))
new = json.load(open('api_catalog.json'))
# each section = {'endpoints': [names]}; diff set(old)-set(new) per section
```
2026-07-10 result: Repair Order 42→49 (added recommendations, internal-notes,
ro-warranty-claims, clock-entries), Deals 70→67 (external-deal endpoints removed).

## Step 3 — Live scope probe (the critical part)

Probe ONE representative READ endpoint per section against SCT with the prod token
(`/home/itadmin/tekion-api/tekion_client.py`, cfg dealers).

**PITFALL #1 (cost 15 min):** `dealer_id` header MUST be the full
`americanmotorscorporation_876_0` string from config.json `dealers`, NOT the bare
number. Bare `876` → misleading `403 "Missing or invalid context headers"` on
EVERYTHING, which looks exactly like scope denial.

**PITFALL #2:** don't guess paths — extract the real path per section from the fresh
spec files (`for p, ops in spec['paths'].items()`). A guessed path 404s
("No matching handler") which tells you nothing about scope.

**Interpret status codes:**
| Code | Meaning |
|---|---|
| 200 | granted, working |
| 400 / 422 (validation msg) | **GRANTED** — request reached the handler, params wrong |
| 500 on fake ID | **GRANTED** — handler choked on nonexistent id; scope open |
| 403 "Missing or invalid context headers" | your headers are wrong (see pitfall #1) |
| 403 "The app version X does not support this API version" | endpoint exists but the dealer-installed APP VERSION blocks it — needs Tekion-side bump, not a plan issue |
| 404 "No matching handler" | wrong path guess — retry with spec path |

## Step 4 — Probe WRITE access safely

Use a nonexistent 24-hex id `'000000000000000000000000'` in path params + empty `{}`
body. This can only fail validation — it can never create/modify real data.
400/404/500 = write scope GRANTED; 403 = blocked. Verified write domains 2026-07-10:
RO (create, jobs, operations, parts), Customers (create/update), Vehicle Inventory
(full CRUD incl cost/pricing/media/bulk upsert), Deals (full CRUD).

## Step 5 — Rescrape webhooks tree

`apc_webhook_spec_downloader.py` has the **default-expanded-section trap in a NEW
form**: Deals is expanded on load, so the generic walker toggles it and also
mis-associates the first collapsed section — 2026-07-10 it saved the Deal Created
page as `deals__repair-order.json` (wrong). Fix: write a one-off targeted script
that (a) clicks the new section name once to expand, (b) clicks each event by exact
name, (c) `page.expect_download()` on "Download Specification". Delete the bogus
file. Verify totals: **24 events = 5 Deals + 4 Repair Order + 15 Vehicle Inventory**
(as of Enterprise Tier 1; Standard had 22 = 5+17... note VI went 17→15 in count but
scraper saved 17 files incl legacy — trust the nav listing).

New RO webhook events (specs at ~/dealerdetail/specs/webhooks/repair-order__*.json):
`ro.created`, `ro.status.updated`, `ro.invoice.status.updated`, `ro.job.created`.
Payload = meta{eventType,eventTime,dealerId} + data{id,link} — fetch details via API.

## Step 6 — Spot-verify the headline unlock with REAL data

For GL (the 2026-07-10 win):
```
GET /openapi/v4.0.0/general-ledger/balances/all?startDate=<ms>&endDate=<ms>   # both required, epoch millis
→ data.glBalancePerGlAccount = {acct: [{month,year,openingBalance,closingBalance,netActivityForMonth,count}]}
# NOTE: GL amounts are DOLLARS, not cents (unlike RO amounts!)
GET .../balances/differential  # ALSO requires clientCurrentTime + refreshWindowTime, else 400 unexpected.error
```

## Step 7 — Report to Joe

Table of granted vs denied sections, what each unlock means practically, and the
concrete ask for Tekion (e.g. "bump app version off 0.0.0-pilot-2.0.0 to unlock the
new RO endpoints"). State the write-back rule: no writes without explicit go per
use case + dry-run report first.

## Step 8 — If endpoints 403 with the app-version message: check the APP in the APC portal (verified 2026-07-10)

The fix for `403 "The app version 0.0.0-pilot-X does not support this API version"` lives in
the APC portal, NOT in any config. Where to look:

1. **Navigation**: after APC login you land on `/app/plan-details`. The app manager is behind
   the **9-dot grid icon (top-left, ≈x22,y32)** → tile **"My Applications"** →
   `/app/my-applications/list`. Guessed routes (`/app/apps`, `/app/my-apps`) 404.
2. The list shows the smoking gun columns: **Status** (ours: "Pilot In Progress"),
   **Published Version** ("-" = never published past pilot), **Current Version**
   (`0.0.0-pilot-2.0.0`). A plan upgrade does NOT bump the installed app version — the app
   must be UPDATED/republished, plan change alone changes quotas/permissions only.
3. Click the app name → edit wizard `/app/my-applications/edit-application/<app_id>`
   (our app_id = `4ec8bf78-9322-4c25-ae1e-34f73d6eeb50`). 4 steps: General Info /
   Contact Info / Product Suite / Data Permission. "View App History" (top-right) opens a
   drawer with the full current-version snapshot (180 APIs, data permissions, pilot details).
4. **"Products Removed" modal trap**: after a plan change, advancing to the Product Suite
   step pops *"The access for following product(s) has been removed due to changes in your
   plan. Please remove these products and update your application to proceed."* with
   [Cancel] / [Remove & Update]. Tekion BLOCKS any app update until you accept the removal
   (2026-07-10: `Get Transactions By Deal Id` was dropped by Enterprise Tier 1).
   **STOP AND ASK JOE before clicking Remove & Update** — unclear whether pushing an app
   update triggers a new review/pilot cycle that could disrupt the live install all
   pipelines depend on. There IS a "Save As Draft" button as a likely safe staging path.
5. Wizard quirks: the modal/drawer state makes the step navigation bounce — clicking the
   step-3 label can land you back on step 2. Verify which step rendered by body text
   ("Business contact" = step 2, "Manage APIs" = step 3), don't trust the click. New APIs
   (e.g. the 8 new RO endpoints) get added via the **"Manage APIs" button** on step 3.

### APC browser automation note
APC sessions can't be saved, and mid-flight script crashes force full OTP re-logins. Better:
clone the persistent-browser-server onto **port 9224** with its own profile dir
(`/home/itadmin/persistent-browser-apc/`, symlink node_modules, sed PORT, and ADD
`executablePath: '<profile-home>/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome'`
— the stock server.js lacks it and the context never initializes). Then drive login
interactively: `/type` email → click "Next" → `/type` password → **`/mouse` on the Login
button center** (text `/click` reported success but didn't fire React) → wait for a NEW
"Your Login OTP" email (track newest himalaya envelope ID, not count) → `/mouse` first
`input[type=tel]` → `/press` each digit → `/mouse` Verify. Session then survives across
turns for the whole portal investigation.

## Step 8 — If sections still 403 "app version does not support": UPDATE THE APP (verified 2026-07-10)

Plan upgrade alone does NOT clear the pilot-app 403s — the installed APP must be
updated. In APC: 9-dot grid (22,32) → **My Applications** tile → click the app row
→ 4-step edit wizard. Procedure that worked:
1. A **"Products Removed"** modal may gate everything (plan dropped an API — 2026-07-10:
   "Get Transactions By Deal Id"). Click **Remove & Update** to clear it.
2. Step 3 Product Suite → **Manage APIs** → click the header **select-all checkbox**
   (it covers the FULL virtualized list, not just rendered rows; went 180→265 APIs)
   → Save (modal's own Save, bottom-right).
3. Webhooks/Feeds/Historical Extracts tabs say "configure credentials in My
   Configuration app" — separate setup, skip for a version bump.
4. Step 4 Data Permission: new permission groups appear (Appointment, Cashiering,
   Communications, Support...). Tick every ENABLED unchecked Read/Write box and fill
   every empty Reason (submit blocks/rejects on empties). The grid is VIRTUALIZED —
   scroll the inner scroller in ~250px steps and re-scan; rows also sit below the
   720px viewport fold, so clicks on stale coords silently miss (verify checked
   state after each click).
5. **Request App Update** → confirm modal **Yes, Request**. Status flips to
   "App Pending Approval", version `<old>-next`. Requires Tekion approval.
6. **Live pipelines are UNAFFECTED while pending** — sanity-probe a granted endpoint
   (repair-orders:search) right after; old version keeps serving.
7. After approval: re-probe the blocked sections; check whether dealers need an
   install-version bump too.

Reusable authenticated APC browser: persistent server on **:9224**
(/home/itadmin/persistent-browser-apc/, own browser-data, executablePath must be the
profile-home chromium-1223 path or context never initializes). Login via /type +
Next, /mouse-click Login (React ignores /click text on this form), OTP = wait for a
NEWER "Your Login OTP" email id than baseline, /mouse first tel box, /press each digit.

## Infrastructure follow-up (webhooks/feeds/extracts)
- Webhooks + Feeds + Historical Extracts require OUR infrastructure first: public HTTPS webhook receiver URL + SFTP server, both with Tekion source IPs whitelisted (52.42.159.151, 35.85.110.130, 35.163.78.152).
- AMG infra contact = Omar Alsadoon (oalsadoon@scvolkswagen.com). 2026-07-10: Stacey drafted the request email into Joe's Drafts (not sent) asking for (1) HTTPS webhook endpoint/subdomain + firewall allow, (2) SFTP host/port/creds + drop directory. Port 22 preferred (non-standard ports need extra Tekion-side whitelisting).
- Once infra exists: configure destination URL + secret (≥8 chars) in APC "My Configurations", run built-in Test Delivery (webhooks) / Test Connection (SFTP), then add event bundles to the app. Verify HMAC-SHA256 of payload vs X-Hub-Signature-256 header; return 200 fast, process async.
- User guide lives at /app/user-guide/api (10 sections, scraped to /home/itadmin/dealerdetail/specs/user-guide/*.txt). Key limits: token generation 20/15min (always use cached bearer via tekion_client); sandbox = api-sandbox.tekioncloud.com dealer techmotors_4_0 (same app creds — dry-run ALL write-back there first); historical extracts limited once/month/dealer; exit-pilot = approved app update → kebab "Request Release" → approval → "Publish App".

## Status log
- 2026-07-10 1:19PM: App update SUBMITTED ("American Motors API" → "App Pending Approval", version 0.0.0-pilot-2.0.0-next; 265 dealer-level APIs, read+write on all enabled permission groups, plan-dropped "Get Transactions By Deal Id" removed). Joe is calling Tekion HIMSELF to expedite approval — do NOT poll. When Joe says approved: re-probe the 8 new RO endpoints + Cashiering/CRM Leads+Appointments/F&I/Pricing Quotes/Support at all 7 stores (pilot-403 should clear), then verify dealer install version bumped. Live pipelines keep working on the old version while pending. Webhooks/Feeds/Historical Extracts NOT added (require credentials in APC "My Configuration" app first — separate task).

## Pitfalls recap
- Bare-number dealer_id = fake 403 on everything.
- 500 ≠ denied; on a fake id it usually means granted.
- App-version 403 is uniform across all 7 stores — testing other dealers won't help.
- Deals `pageSize` param rejected on /customers (uses different param names per
  section — read each spec's parameters).
- Webhook scraper's generic section walker is untrustworthy for NEW sections —
  always verify against the raw nav text (`page.inner_text("body")`) first.
