---
name: tekion-pipeline-operations
description: Audit, diagnose, and repair the Tekion scraper pipeline including OTP fetching, session reuse, lock starvation, and Puppeteer navigation timeouts.
triggers:
  - scraper pipeline broken
  - tekion pipeline audit
  - otp fetch failing
version: 2.0.0
tags: [tekion, puppeteer, scraper, pipeline, dms]
---

# Tekion Pipeline Operations

Audit and repair the Tekion DMS scraper pipeline at `/home/itadmin/caliber-ops/`.

## ⛔ Caliber dollars CANNOT migrate to the OpenAPI (verified 2026-06-22) — read before "use the API instead"

Joe's standing goal is to move everything off browser scrapers onto the Tekion
OpenAPI. **This works for VI/The Goods but is BLOCKED for the Caliber RO-dollars
pipeline.** The Caliber dashboard's gross/net/GP come from Tekion **Sales Orders**
— the wholesale **parts/sublet tickets** Caliber's body shops run through AMG
stores (shopName = "Caliber - Fresno", "Caliber - Madera", etc.). The scraper reads
them off the **Parts → Sales Order** screen (`page.goto(.../parts/sales-order)`),
NOT the service Repair Order screen.

There is **NO Sales Order / parts-invoice / counter-sales endpoint in our OpenAPI
scope.** Confirmed exhaustively:
- `repair-orders:search` join FAILS: our OpsTrax `invoiceNumber` (6-digit, e.g.
  `198672`) and 10-digit RO#s do NOT exist as RO `documentNumber`; `repair-orders/
  {id}/ro-invoices` returns `invoiceNumber: null` on every record.
- Probed `/sales-orders:search`, `/parts-sales-orders:search`, `/parts-invoices:search`,
  `/counter-sales:search`, `/service-invoices:search`, `/invoices:search` → **all 404**.
- Audited all 266 downloaded APC specs (`~/dealerdetail/specs/apis/`): the only
  parts-adjacent endpoints are `parts-inventory:search` (stock on-hand only) and
  `pricing-quotes:calculate-pricing` (a calculator). `cashiering` = online-payment
  SETTINGS only. None carry sold SO dollars.

**Conclusion:** Keep the (now-stabilized) scraper for Caliber dollars until Tekion
grants a Sales-Order/parts-invoice data scope. Add that ask to the scope request
(`~/dealer-detail/docs/tekion-api-scope-request.txt`). Don't re-attempt the API
migration for Caliber dollars without that grant — it's a guaranteed dead end.
**VI / The Goods IS API-ready** (`vehicle-inventory:search` + 53 specs) — migrate
that one freely.

## Architecture

```
cron-pipeline.sh (every 15 min)
  ├── Step 1: OpsTrax scrape (run-scraper.ts)
  ├── Step 2: Turso sync (migrate-to-turso.ts)
  ├── Step 3: Tekion scrape — 6 dealerships sequentially (tekion-scraper.ts)
  └── Step 4: Final Turso sync

cron-tekion.sh (1 AM nightly)
  └── 60-day backfill — all stores, re-scrapes historical invoices

cron-vi-scraper.sh (2 AM)
  └── Vehicle Inventory scrape → the-goods/data/*-active.json
```

## Common Failure Modes & Fixes

### 1. OTP Fetcher Broken
**Symptom:** Pipeline log shows `Command failed: python google_api.py gmail search "Tekion-Login OTP"`

**Root cause:** `google_api.py` at `/home/itadmin/.hermes/skills/productivity/google-workspace/scripts/google_api.py` requires OAuth2 setup (client_secret.json, auth code from user). If never set up, OTP fetch fails every run.

**Fix:** Replace with himalaya-based IMAP OTP fetcher:
```bash
# The replacement script at /home/itadmin/caliber-ops/scripts/fetch_otp.py
# Uses himalaya with HOME=/home/itadmin to query Gmail via IMAP
# No OAuth needed — uses existing himalaya IMAP config
python3 /home/itadmin/caliber-ops/scripts/fetch_otp.py  # Returns 6-digit OTP
```

The scraper's `getOTPFromEmail()` was patched to call this instead of google_api.py. The replacement:
- Calls `execSync("python3 /home/itadmin/caliber-ops/scripts/fetch_otp.py")` 
- Expects 6-digit OTP on stdout
- Retries 6 times with 5s delay

### 2. Session Reuse Fails — Network Idle Timeout
**Symptom:** Every scraper run re-authenticates despite saved session. Log shows 30s timeouts on session check.

**Root cause:** `loadSession()` uses `page.goto(TEKION_URL, { waitUntil: "networkidle2", timeout: 30000 })`. Tekion's heavy SPA never reaches network idle in 30s → timeout → falls through to full login.

**Fix:** Change to `domcontentloaded` with shorter timeout:
```typescript
// In tekion-scraper.ts loadSession():
await page.goto(TEKION_URL, { waitUntil: "domcontentloaded", timeout: 20000 });
```

Same fix applies to the main `loginToTekion()` function's initial navigation.

### 3. Nightly Backfill Starved (Lock Contention)
**Symptom:** `tekion-nightly.log` shows "Pipeline running, skipping nightly" every night for weeks.

**Root cause:** Both `cron-pipeline.sh` (15-min) and `cron-tekion.sh` (1 AM) use the SAME lock file (`/tmp/caliber-pipeline.lock`) with `flock -n` (non-blocking). Pipeline runs every 15 min → lock always held → nightly never runs.

**Fix:** Change nightly to use blocking flock:
```bash
# In cron-tekion.sh:
# OLD: flock -n 200 || { echo "Pipeline running, skipping nightly"; exit 0; }
# NEW: flock -x 200 || { echo "Failed to acquire lock, skipping nightly"; exit 0; }
```
Blocking `flock -x` waits for pipeline to release lock, then runs.

### 4. Session File Corrupted
**Symptom:** `/home/itadmin/caliber-ops/scripts/.tekion-session.json` is 2 bytes (`{}`). Scraper re-authenticates every run.

**Fix:** After a successful scrape, the scraper saves localStorage keys: `t_token`, `t_user`, `dse_t_user`, `currentActiveIsWorkspace`, `currentActiveWorkspace`. A healthy session file is ~137KB. If empty/corrupt, kill the scraper and re-run — it'll do a full OTP login and save a fresh session.

### 5b. Zombie Scraper Holds Pipeline Lock for Days (MOST IMPACTFUL)
**Symptom:** `pipeline.log` shows "Already running, skipping" on EVERY 15-min run for days/weeks. Dashboard data frozen at some past date. `cron-tekion.sh` nightly log shows cascading `Runtime.callFunctionOn timed out` on every invoice.

**Root cause:** A scraper (usually launched by the 1 AM nightly backfill) hangs on a Puppeteer protocol timeout — the headless chrome (`puppeteer_dev_chrome_profile-*`) never dies and keeps `exec 200>/tmp/caliber-pipeline.lock` held. Since `cron-pipeline.sh` uses `flock -n` (non-blocking), every subsequent 15-min run instantly skips. The lock is released ONLY when the holding process dies — and a hung chrome never does. Confirmed June 2026: a June-12 nightly + June-15 scraper held the lock until June 22 (10 days, zero dashboard data).

**Diagnose:**
```bash
fuser /tmp/caliber-pipeline.lock                 # PIDs holding it
ps aux | grep -E "tekion-scraper|puppeteer_dev_chrome|node_modules/chromium" | grep -v grep
```
Look for processes with a STARTED date days in the past.

**Immediate fix:**
```bash
# Kill the whole zombie tree (the flock wrapper, tsx, node, AND all chrome PIDs).
# DO NOT kill the 718xxx-style ms-playwright chrome — that's the persistent-browser server.
kill -9 <all caliber-ops scraper + node_modules/chromium PIDs>
rm -f /tmp/caliber-pipeline.lock
# Test one store, then run full pipeline:
cd /home/itadmin/caliber-ops && npx tsx scripts/tekion-scraper.ts --quick --dealership "Blackstone Toyota"
```

**Permanent fix (applied June 2026):**
1. `tekion-scraper.ts` launch now sets `protocolTimeout: 60000` so a hung SPA call rejects instead of wedging chrome forever.
2. `cron-pipeline.sh` got a pre-lock watchdog: kills any `caliber-ops/scripts/tekion-scraper.ts` PID or `puppeteer_dev_chrome_profile` chrome older than 3600s BEFORE acquiring the lock.
3. Per-store call wrapped in `timeout -k 30 720` so one bad store can't stall the run.

NOTE: the IMPORTANT gap (e.g. "no data since 6/2") is usually NOT lost data — it's the lock. Once unblocked, `--quick` mode backfills missing invoices automatically. Don't panic about the date; fix the lock and let it catch up.

**Watchdog pgrep-pattern bug (found + fixed 2026-08-05):** the pre-lock watchdog in
`cron-pipeline.sh` used `pgrep -f "caliber-ops/scripts/tekion-scraper.ts"` — but the
ACTUAL process argv (via `npx tsx scripts/tekion-scraper.ts ...`) never contains the
`caliber-ops/` path prefix, only the relative `scripts/tekion-scraper.ts`. So the
watchdog's own pattern never matched and it silently never fired — a wedged SCT
scraper held the pipeline lock for 17+ hours (Aug 4 10:44 AM → Aug 5 3:00 AM) with
zero self-heal, and the 1 AM nightly backfill queued the whole time waiting on the
same lock. Fixed by loosening the pattern to just `pgrep -f "tekion-scraper.ts"`
(both `for PID in $(pgrep -f ...)` loops in the watchdog). **Lesson: always verify a
watchdog's pgrep pattern against the ACTUAL live process argv (`ps -o cmd= -p <pid>`
or `cat /proc/<pid>/cmdline`), not the path you assume the shell will show — path
prefixes get stripped/resolved differently than expected.** After any watchdog
edit, test it against a real running PID before trusting it silently protects the
pipeline.

### 5. Frame Detachment Cascade — FIXED 2026-06-22
**Symptom:** `Attempted to use detached Frame 'F...'` errors. NOT just "after ~100 searches" — once it happens ONCE, **every subsequent invoice in that store silently fails**, so the store reports `Found: 0` (or 0 processed). Confirmed June 2026: BC/SV/VC all showed Found:0 while BT/ST/TL got 42 each, and the run logged **9,158 detached-frame errors**. The error path does NOT write false zeros (it only stamps `tekionScrapedAt`), so the dashboard goes STALE on the affected stores, not zeroed — diagnose by per-store `Found:` counts in the COMPLETE summaries, not by dashboard zeros.

**Root cause:** In `searchInvoice()` Step 6, after extracting SO dollars the scraper called **`await page.goBack()`** to return to the sales-order list. `goBack()` on Tekion's React SPA **destroys/detaches the Puppeteer main-frame handle**; the next `page.evaluate` in the loop throws "detached Frame" and it cascades for the rest of the batch.

**Fix (committed, branch `dev`):**
1. In `searchInvoice()` Step 6, replace `page.goBack()` with a hard nav that rebuilds a fresh attached frame:
```typescript
try {
  await page.goto("https://app.tekioncloud.com/parts/sales-order",
    { waitUntil: "domcontentloaded", timeout: 30000 });
  await sleep(2500);
} catch { try { await page.goBack(); await sleep(3000); } catch {} }
```
2. Add a mid-loop detach probe right after `const data = await searchInvoice(...)` so a single detach can't poison the rest of the store:
```typescript
try { await page.evaluate("1"); }
catch (e: any) {
  if (String(e?.message||"").includes("detached")) {
    await page.goto("https://app.tekioncloud.com/parts/sales-order",
      { waitUntil:"domcontentloaded", timeout:30000 }); await sleep(3000);
  }
}
```
Result: 0 detached-frame errors on the next run (down from 9,158). `--quick` mitigation is no longer needed for this.

NOTE: `tsx` runs the scraper, so the pre-existing tsconfig `TS18028` node_modules lint noise + the `tekion-scraper.ts(709,7)` type error in `clearSearch` are HARMLESS — they predate any edit and don't block execution. Don't chase them.

### 5c. Dashboard Frozen at a Date Despite Scraper "Working" (Turso INSERT gap)
**Symptom:** Dashboard (Glade/Glendale/any store) shows 0 orders or stale data; "Last Scrape" timestamp stuck on an old date (e.g. 6/02). Pipeline log says "✓ OpsTrax OK" and scraper finds hundreds of orders, but `repair-orders`/dashboard never updates.

**Root cause (confirmed June 2026):** The dashboard reads from **Turso** (remote libSQL). The OpsTrax scraper (`scraper.ts`) writes to `process.env.TURSO_DATABASE_URL || "file:dev.db"`. In `cron-pipeline.sh`, the `export $(grep -v '^#' .env.local | xargs)` line was placed AFTER step-1 scrape — so the scraper had NO Turso env and wrote every order to **local file:dev.db only**. Then `migrate-to-turso.ts` runs, but it ONLY UPDATES Tekion-dollar fields on rows that ALREADY exist in Turso (matched by `invoiceNumber|dealership`) — it has **no INSERT path** for brand-new orders. Net result: new OpsTrax orders pile up in dev.db and NEVER reach Turso. Dashboard freezes on the last date Turso was populated. "Not in Turso: 0" in the migrate log is the tell — it silently ignores unmatched new orders.

**Diagnose:**
```bash
cd /home/itadmin/caliber-ops && export $(grep -v '^#' .env.local | xargs)
# Compare local dev.db vs Turso newest order + counts:
npx tsx -e 'import {PrismaClient} from "./src/generated/prisma/client"; import {PrismaLibSql} from "@prisma/adapter-libsql";
const L=new PrismaClient({adapter:new PrismaLibSql({url:"file:dev.db"})});
const T=new PrismaClient({adapter:new PrismaLibSql({url:process.env.TURSO_DATABASE_URL,authToken:process.env.TURSO_AUTH_TOKEN})});
(async()=>{console.log("local:",await L.order.count(),"turso:",await T.order.count());
const ln=await L.order.findMany({orderBy:{submittedAt:"desc"},take:1}); const tn=await T.order.findMany({orderBy:{submittedAt:"desc"},take:1});
console.log("local newest:",ln[0]?.submittedAt,"turso newest:",tn[0]?.submittedAt);await L.$disconnect();await T.$disconnect();})();'
```
If local count >> turso count and local newest is recent but turso newest is old → this bug.

**Permanent fix:** Move the `export $(grep -v '^#' .env.local | xargs)` line ABOVE the step-1 scrape in `cron-pipeline.sh` so the scraper upserts directly to Turso (scraper.ts already does `order.upsert`).

**One-time backfill** of the dev.db→Turso gap: `scripts/sync-all-orders-to-turso.ts` (upserts ALL local orders to Turso, parallel batches of 20, keyed on roNumber+invoiceNumber+dealership). Run: `export $(grep -v '^#' .env.local | xargs) && npx tsx scripts/sync-all-orders-to-turso.ts`. ~8k rows in ~6 min. Verify Turso `after-6/02` count climbs and Glendale range extends to today.

NOTE: "Glade" in chat = **Glade Wilson** (gwilson@stevenscreektoyota.com, Stevens Creek Toyota) OR **Caliber - Glendale** shop — clarify which. Glade Wilson's dashboard 7-day card reads Stevens Creek Toyota orders.

### 6. Exit Code Swallowing
**Symptom:** Pipeline cron shows "✓ Tekion OK" even when scraper fails. Failures are silent.

**Root cause:** In `cron-pipeline.sh`, the Tekion scraper loop uses `if npx tsx ...` but tsx may return 0 even on errors. Also the per-dealer errors are logged but not reflected in exit codes.

**Fix:** Ensure `tekion-scraper.ts` calls `process.exit(1)` on fatal errors (not just `console.error`). The `--quick` mode should also exit non-zero when scraping fails for a store.

### 7. SCT DEALER_QUOTA Multi-Day Outage (distinct bucket from OVERALL_QUOTA)
**Symptom:** Deep RO-operations/per-op fan-out endpoints 429 with `Limit exhausted
for type : DEALER_QUOTA` for a SPECIFIC store (seen: SCT/876), while search/jobs
endpoints on the same store keep working fine. This is a PER-DEALER quota bucket,
separate from the app-wide `OVERALL_QUOTA` documented elsewhere in this skill.
Confirmed 2026-08-01→08-03: outage persisted 35+ hours across TWO nightly refills.

**Repeat root cause:** dealer-detail's own `sync:all` nightly cron and/or ad-hoc
`sync:store SCT <days>` backfills retry-loop against the 429 wall and grab the
quota the INSTANT it refills, re-draining it before any other consumer (incl.
Jay's own report scans) gets a turn. Killed this exact process twice in one
outage before it finally cleared.

**Diagnose/fix:**
```bash
ps aux | grep -E "sync:all|sync:store|dealer-detail" | grep -v grep
# kill any hitting the affected store, THEN re-arm/re-run your own recovery job
```
Always kill competing dealer-detail sync processes BEFORE re-arming a self-heal
watcher for a DEALER_QUOTA-blocked store — otherwise the watcher just starves
again on the next refill.

**Zero-quota fallback:** if the report period's data already landed on disk from
a prior successful scrape (e.g. a full-month report where the last day of the
month was already scraped and cached to JSON), render directly from that cached
JSON instead of waiting on the API. Verified: SCT alignment "July full month"
report rendered entirely from the 7/31 close-data JSON with zero API calls while
the DEALER_QUOTA outage was still active.

**Escalation threshold:** if a DEALER_QUOTA outage survives 2+ nightly refills
without clearing, it's likely stuck on Tekion's side (not just heavy local
usage) — escalate to Joe to ask Tekion support to check/raise the affected
store's dealer quota bucket on the American Motors API app rather than
indefinitely re-arming recovery watchers.

## Codex Computer Use (Future)

Codex with computer use can replace Puppeteer for Tekion automation:
- AI vision understands the UI naturally (no fragile selectors)
- Recovers from unexpected states (frame detach, React portals)
- Natural language opcode updates: "Set BGFINJ to $226 fixed price"

Auth: Use `codex login --device-auth` to link to ChatGPT Pro account (no API credits needed).

## Health Check Commands

```bash
# Check session
python3 /home/itadmin/.hermes/shared/tekion-session.py status

# Check VI data freshness
ls -lt /home/itadmin/the-goods/data/*-active.json | head -7

# Check pipeline log for OTP errors
tail -50 /home/itadmin/caliber-ops/logs/pipeline.log | grep -i "error\|fail\|OTP"

# Check nightly backfill log
tail -20 /home/itadmin/caliber-ops/logs/tekion-nightly.log

# Check if pipeline is running
ls -la /tmp/caliber-pipeline.lock && pgrep -f "tekion-scraper"
```

## Manual Test Scrape

```bash
cd /home/itadmin/caliber-ops
npx tsx scripts/tekion-scraper.ts --quick --dealership "Blackstone Toyota"
```

Use store names (not codes): "Blackstone Toyota", "Stevens Creek Toyota", "Toyota of Lancaster", etc.
