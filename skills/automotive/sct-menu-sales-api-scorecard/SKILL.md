---
name: sct-menu-sales-api-scorecard
description: >
  Run the SCT (Stevens Creek Toyota) Menu Sales same-day scorecard pipeline from
  the LIVE Tekion OpenAPI source (NOT Report Builder) and email the PDF to Joe
  via Stacey. Pulls today's ROs straight from the API, filters to the frozen 316
  TEK* maintenance opcodes, resolves advisor names via the persistent browser
  session on :9223, renders a light-format PNG+PDF scorecard, vision-verifies,
  and emails. Use for the daily Menu Sales Opened Performance Report cron.
triggers:
  - sct menu sales scorecard
  - menu sales daily report
  - sct menu sales api
trigger: SCT menu sales, menu sales scorecard, daily opened performance report, sct_menu_sales_api, live OpenAPI menu sales
---

# SCT Menu Sales API Scorecard (LIVE source)

The CURRENT production pipeline for the daily "Menu Sales — Daily Opened
Performance Report — SCT". Source is the **LIVE Tekion OpenAPI**, so numbers are
as-of run time (no Report Builder lag). The legacy Report-Builder DOM scraper
(`sct_menu_sales.py`, skill `tekion-report-builder-scraper`) is **deprecated** —
do not use unless explicitly asked for a cross-check.

Proven 2026-06-15 (8 menus, labor $1,725.50 / parts $801.86 / total $2,527.36).

## Pipeline (4 steps + 2 verifications)

All scripts use this interpreter: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`
Data dir (REAL path): `/home/itadmin/tekion-reports/data/`
`<today>` = today's ISO date, e.g. `2026-06-15`.

1. **Scrape LIVE data**
   `cd /home/itadmin/tekion-reports && <py> sct_menu_sales_api.py`
   - Pulls today's ROs from Tekion OpenAPI (Stevens Creek Toyota).
   - Filters to the frozen **316 TEK\* maintenance opcodes**.
   - Resolves advisor names via persistent browser session on **:9223**
     (RO→appointment join; cached in `data/sct-advisor-cache.json`).
   - Writes TWO files:
     - `data/sct-menu-sales-api-<today>.json`
     - `data/sct-menu-sales-opened-<today>.json`  ← Report-Builder schema, this
       is what the renderer + the email summary totals come from.
   - Watch stderr `[sct-api]` lines. **0 records is VALID** (slow day) — still send.

2. **Render**
   `cd /home/itadmin/tekion-reports && <py> render_scorecard.py`
   → `data/SCT-Menu-Sales-Scorecard-<today>.png` and `.pdf` (approved LIGHT format).

3. **Vision-verify the PNG** (`vision_analyze` on the .png):
   - KPIs present: Opcode Labor Gross (SUM), Opcode Parts Gross (SUM),
     Total Menu Gross, Menus Sold.
   - Advisor names are real human names, **NOT UUIDs / long hex**.
   - No NaN / undefined / null / spurious $0.00.

   ⚠️ **VISION OCR MISREADS THE SMALL KPI DIGITS ON THE FULL-PAGE PNG (hit
   2026-06-19, expect every run).** The rendered PNG is very tall (~6427px;
   the closed MTD one) and the 4 KPI boxes sit in only the top ~5%. Running
   `vision_analyze` on the WHOLE image returns CONFIDENTLY WRONG numbers — on
   6/19 it read `$49,967.78 / $19,488.59 / $69,456.37 / 349` when the JSON/render
   truly said `$48,467.78 / $18,488.95 / $66,956.73 / 160`. The title +
   advisor-names check still works full-page (those are large text), but DO NOT
   trust full-page OCR of the dollar figures.
   → The JSON totals are authoritative; vision is only a sanity check. To get a
     RELIABLE KPI read, crop the top band and upscale 2x first, then vision that:
     ```python
     from PIL import Image
     im=Image.open('data/SCT-Menu-Sales-Closed-Scorecard-<today>.png')
     w,h=im.size
     top=im.crop((0,0,w,460))                      # ~460px = title + 4 KPI boxes
     top=top.resize((top.width*2,top.height*2),Image.LANCZOS)
     top.save('/tmp/kpi_band.png')
     ```
     `vision_analyze('/tmp/kpi_band.png', ...)` then reads every digit correctly
     and matched the JSON exactly on 6/19. If the cropped-band read matches the
     JSON, verification passes — a full-page mismatch is an OCR artifact, not a
     data bug. (460px works for the closed MTD layout; widen the crop height if a
     future layout pushes the KPI boxes lower.)

   ⚠️ **THE FULL-PAGE PNG CAN EXCEED THE VISION API'S 8000px DIMENSION LIMIT —
   the title/advisor-names full-page check then 400s outright (hit 2026-06-29).**
   On 6/29 the closed MTD PNG was 1226×**8739px** (228 menus → very tall table).
   `vision_analyze` on the WHOLE png returned HTTP 400 `"At least one of the image
   dimensions exceed max allowed size: 8000 pixels"` (both Bedrock + Google
   providers). So you CANNOT do the title/names check full-page on a tall MTD
   render either. → Do BOTH verification reads on crops:
   (a) top band (0,0,w,460) ×2 upscale → KPIs + title (already covered above);
   (b) a MIDDLE table band, e.g. `im.crop((0,2000,w,3200))` → advisor names are
   real humans + no NaN/null/cut-off. The JSON advisor Counter (real names, zero
   digit/UUID keys) is the authoritative names check; the cropped vision read is
   just the visual sanity confirm. Note: a legit **negative labor_gross**
   (e.g. -$34.66, a comped/discounted line) and **TEK opcode truncation with "…"**
   in a table cell are NORMAL real-data artifacts, NOT errors — do not flag them.

4. **Email via Stacey** (see the Stacey section — it is the fiddly part).

5. **Final summary**: totals, menu count, top advisor (highest labor+parts),
   whether email was sent. Live data → numbers are as-of run time.

## Totals come from the opened-JSON
Read `data/sct-menu-sales-opened-<today>.json`:
`.totals.labor_gross`, `.totals.parts_gross` (total menu gross = their sum),
`.row_count` = menus sold. Top advisor = row with max (labor_gross + parts_gross).

## Advisor name resolution depends on :9223 being UP and AUTHENTICATED

### ⭐ UPGRADE (2026-06-19): closed pipeline now uses PUBLIC /users/{id} — NO browser
The closed MTD pipeline (`sct_menu_sales_closed_mtd.py`) no longer needs the
`:9223` browser for advisor names. `sct_menu_sales_api.py` `user_name(uid)` was
patched to call the PUBLIC OpenAPI `GET /openapi/v4.0.0/users/{id}` FIRST
(`_user_name_openapi()`, uses the same HEADERS as the RO scrape), falling back to
the internal `:9223` browser path only if the public call fails. The public scope
was enabled 2026-06-18 and resolves BOTH numeric ids ("59","61","74") and UUIDs.
`resolve_advisors()` in the closed script was simplified to just call
`O.user_name(aid)` — the old `_load_lookups()` + `resolve_advisors_via_browser()`
path is RETIRED because it read the stale `sct-advisor-cache.json` which mislabeled
real advisors. So for the CLOSED report you can skip the whole session-restore
dance below; only fall back to it if the public API ever 403s again.

✅ **CONFIRMED FOR THE OPENED PIPELINE TOO (2026-06-20):** `sct_menu_sales_api.py`'s
own `user_name()` calls the public `/users/{id}` first, so the daily OPENED scrape
ALSO resolves every advisor to a real name even when :9223 is sitting on
`/login` (`t_token:false`). On 6/20 the :9223 probe showed unauthenticated, yet
all 7 advisors (Artist Battle, Chris Mai, Edgardo Oliver, Jon Vu, Michael Robert
Costa) resolved cleanly with NO session restore. So an unauthenticated :9223 is
no longer a blocker for the Opened report — do NOT spend time restoring the
session unless advisor names actually come back as digits/UUIDs after a scrape.

⚠️ **`advisor-name-cache.json` (the file `user_name()` writes/reads, `_CACHE_FILE`)
can hold UUID-as-name entries** — i.e. a value that IS the raw UUID because an old
run failed to resolve it. These show up as hex on the report. Clean them by
re-resolving via the public API:
```python
import json,sys,time; sys.path.insert(0,"/home/itadmin/tekion-reports")
import sct_menu_sales_api as O
p="/home/itadmin/tekion-reports/data/advisor-name-cache.json"; c=json.load(open(p))
for k,v in list(c.items()):
    if len(str(v))>18 and '-' in str(v):           # value is still a UUID
        n=O._user_name_openapi(k); time.sleep(0.3)
        if n: c[k]=n
json.dump(c,open(p,"w"),indent=0)
```
Verified 2026-06-19: the 3 SCT UUIDs once mislabeled "Any Service Advisor" are
real advisors — ee31e3e9…=Angel Gutierrez, bfb756e2…=Michael Robert Costa,
f3fabb57…=Juan Jose Perez. There is NO genuine "Unassigned" bucket on closed ROs;
a None advisor id is a true no-advisor RO (rare). Joe rejects "Unassigned" rows.

### Legacy browser path (fallback only — interim, not production)
If the public API ever 403s, restore the session into :9223 and use the internal
`/api/userservice/u/apc/users/{id}` path as before:
Connection refused` (or `advisor lookup failed for <id>`), the session on :9223
is down or unauthenticated, and some advisors fall back to **numeric/UUID IDs**.
0 records is fine; UUID advisors are NOT — fix and re-scrape:

1. Health check: `curl -s -m5 http://localhost:9223/health` → exit 7 = down.
2. Restart + RESTORE the Tekion session into :9223 (the persistent context is
   unauthenticated after a restart). Follow skill **persistent-browser-server**,
   section "Restoring an authenticated Tekion session into :9223".
   ⚠️ CAVEAT (2026-06-18): this restore reliably re-authenticates the SPA *page*
   (cookie-based), but does NOT reliably make the **internal `/api/`** advisor
   lookup work — `login.py`'s partner `t_token` is rejected by `/api/` with 500
   "Token doesn't exist or is invalid" (see the boxed warning in the Unassigned
   section above). If advisor resolution still returns numeric/UUID ids after a
   restore, the internal token is the blocker — only a fresh INTERACTIVE OTP
   login at dealer 876 fixes it; for a same-day report, recover via
   createdBy/modifiedBy + cache and ship rather than chasing the token.
   - `fuser -k 9223/tcp`; copy `server.js` to the profile-home copy; start with
     `cd /home/itadmin/.hermes/profiles/jay/home/persistent-browser && xvfb-run -a node server.js` (background).
   - Refresh session: `cd /home/itadmin/tekion-auth && <py> login.py` (does a
     fresh OTP login; exit 0 + `LOGGED_IN`). Writes
     `/home/itadmin/caliber-ops/scripts/.tekion-storage-state.json` (5 cookies +
     21 localStorage keys for the tekioncloud origin).
   - Inject cookies via `POST /cookies`, then localStorage **one key at a time**
     via `/eval` (`localStorage.setItem(<json name>,<json value>)`) — all-at-once
     → HTTP 413.
   - Navigate `/home`; verify URL stays on `/home` (not `/login`) AND
     `t_token`, `__user_id`, `currentActiveRoleId`, `currentActiveSiteId` all exist.
3. Re-run `sct_menu_sales_api.py` — UUIDs now resolve to real names.

If :9223 truly can't be restored, the task says: still send, but NOTE the
fallback in the summary. Prefer fixing it — the recovery above is reliable.

Note: "Any Service Advisor" / "Unassigned" is a VALID advisor label, not an
error — don't treat it as a failed resolution.

### "Unassigned" / "Any Service Advisor" rows — root cause + DO-NOT-DO (2026-06-17)

When a menu row shows **"Unassigned"** it is NOT a scraper guess and NOT a bug.
Source: line ~248 reads `ro.assignee.advisor.id` off the live RO; line ~298-300
resolves it, falling back to the literal string `"Unassigned"` only when the id
is absent/None, OR the id maps to a generic placeholder. There is NO code path
that defaults a no-advisor RO to any specific real person — and it MUST stay
that way (Joe explicitly warned: never force "Unassigned" → one advisor).

**Two separate conditions both surface as "Unassigned":**
1. `assignee.advisor.id` is genuinely None → no advisor on the RO header.
2. The id IS present but is a SHARED generic placeholder that the cache maps to
   "Any Service Advisor" (e.g. SCT placeholders `ee31e3e9-bba5-4868-8ead-a2464c95eab1`,
   `bfb756e2-d856-45b6-961d-7a5162f12d12`, `f3fabb57-5935-46a7-8f16-97e201b63e30`).
   This means the RO was CHECKED IN under "Any Service Advisor" in Tekion, not
   assigned to a real writer. It is a service-writing/check-in process gap, NOT
   a scraper problem. The fix is in Tekion (reassign the RO), not in code.

**DO NOT** map a placeholder/"Any Service Advisor" UUID to a real advisor name
in `sct-advisor-cache.json` — those UUIDs are SHARED across many ROs, so doing
so would falsely credit EVERY placeholder RO to that one person. This is the
exact failure mode Joe called out.

**How to diagnose which RO + recover the intended advisor (proven 2026-06-17):**
- The opened-schema/api JSON has `advisor_id` and `ro_docid` set to None AFTER
  the strip (lines 296-297), so re-fetch from the LIVE source to inspect.
  Easiest: `import sct_menu_sales_api as S; ros = S.fetch_ros(ms0, ms1)` then
  find the RO by `documentNumber` and print `ro["assignee"]`. (Use the module's
  own `fetch_ros` — building the OpenAPI request by hand 401'd; the tekion_client
  token alone isn't enough, the scraper's `call()` adds the right headers.)
- Real advisor roster (numeric + UUID → name) lives in these files under
  `/home/itadmin/tekion-reports/data/`: `sct-employees.json` (has empNo + active
  flag), `sct-emp-byid.json`, `employees-full.json`, `employee-lookup.json`,
  `sct-empno-lookup.json`. grep them for a last name to get the person's REAL
  unique id(s). (Note: a real advisor can have MORE THAN ONE id, e.g. Juan Jose
  Perez = both `60497b32-...` and `cee75066-...`.) If a real RO carries one of
  those real ids it already resolves correctly — no cache edit needed.
- Pitfall: internal user-search endpoints `/api/userservice/u/apc/users/search`
  (500) and `?searchText=` (404) do NOT work; only the single-user GET
  `/api/userservice/u/apc/users/{id}` works, and the local roster JSON files are
  faster and avoid burning the OpenAPI rate limit.

#### ⚠️ THE INTERNAL `/api/` ENDPOINT IS NOT REACHABLE AFTER A login.py REFRESH (hard-won 2026-06-18)

**Do NOT burn 20+ tool calls trying to resolve advisor names via the internal
`/api/userservice/u/apc/users/{id}` endpoint after refreshing the session with
`login.py`.** It WILL return HTTP 500 `{"message":"Token doesn't exist or is
invalid"}` on EVERY call — even a self-lookup, even cookie-only (no token
header). Root cause, confirmed by decoding the JWT + reading the `tcookie`:

- `login.py` mints an **OpenAPI/partner-flow `t_token`** (JWT `iss=LoginService`,
  claims = jti/iat/sub/iss/userId/email/exp — NO dealerId/aud/scope). The
  internal app `/api/` rejects this token format outright.
- The internal API is authenticated by the **interactive web-login** session
  (its own httpOnly `tekion-api-token` cookie + a token the SPA mints on real
  login). `login.py`'s `storage_state` injection **clobbers** the :9223
  localStorage `t_token` with the partner token, and the previously-valid
  interactive session has usually already expired server-side. The SPA may STILL
  render "Welcome back, Joe!" from cached state — that is a FALSE POSITIVE; the
  internal session is dead.
- Passing the right userId DOES matter but is NOT enough: the real internal
  userId is in `document.cookie` → `tcookie` JSON (`userId`/`original-userid`,
  e.g. `8cc203af-...`), NOT the email string in `__user_id`. Even with the
  correct userId + all tcookie-derived headers, the partner token still 500s.

**What this means in practice:** the memory note "Tekion advisor id→name works via
the internal app endpoint through the :9223 session (verified 2026-06-15)" is
only true while a genuine *interactive* login is live. After a `login.py`-only
refresh you CANNOT resolve placeholder-advisor names programmatically. The ONLY
reliable recovery is a fresh **interactive OTP login driven through the :9223 UI
at the target dealer (876)** so the SPA mints its own valid internal token —
which is heavy and needs the OTP flow. For a same-day report, do NOT block on it.

**Decision rule for the "Unassigned" 13-RO case (2026-06-18):** placeholder
"Any Service Advisor" ROs are walk-in/express check-ins with genuinely NO real
advisor in the OpenAPI data — the name lives ONLY in the internal app. When the
internal API is unreachable, recover what you can WITHOUT it and ship:
- Check each placeholder RO's `createdByUserId` / `modifiedByUserId` — these
  sometimes hold a REAL numeric id that IS in `sct-advisor-cache.json`
  (e.g. RO 568953 createdBy=`73`=Shaun Kamal). Credit those.
- Numeric advisor ids like `74`/`69` that aren't cached stay as
  "Advisor #<id>" — do NOT guess. The roster files (`sct-employees.json` etc.)
  do NOT map these short numeric assignee ids (verified: only 11 of 1,200 records
  even have a UUID, and none match the cache UUIDs — the roster is USELESS for
  short-id resolution).
- Label the rest "Unassigned (express/walk-in)" — accurate, matches Tekion.
- The store/RO TOTALS are unaffected; only the per-advisor bucketing of those
  rows is. Ship the report, flag the count + offer the interactive-login route.

## CRITICAL: OpenAPI rate limit (429) silently truncates record count

The Tekion OpenAPI enforces an account-wide `OVERALL_RATELIMIT`. Each full
scrape makes MANY calls (RO search + per-RO jobs + per-job operations + parts +
vehicle). Running the scraper 3-4 times in quick succession EXHAUSTS the limit.
When that happens, `scan_ro` gets 429 on per-RO `/jobs` calls and silently
returns `[]` for those ROs (see `if stj != 200: return out`) — so the menu count
comes back ARTIFICIALLY LOW (e.g. 8 → 3) with NO error printed. The `[sct-api]`
log looks clean. This is a data-integrity trap.

Rules:
- Do NOT re-run the scraper repeatedly to "double check". One clean run is
  authoritative. Each extra run risks corrupting the next via 429.
- If you must re-scrape (e.g. to fix UUID advisors), do the session-restore
  FIRST, then run the scraper exactly ONCE.
- If the record count drops between runs, suspect rate limiting, NOT a live
  change. Verify with a single probe: POST `/repair-orders:search` →
  429 with `"Limit exhausted ... OVERALL_RATELIMIT"` confirms it.
- Recovery: STOP all API calls and WAIT for the rolling window to reset. On
  2026-06-16 it took ~8 minutes. Poll the search endpoint at 60s intervals (not
  faster — polling also consumes the limit) until it returns 200, then do ONE
  clean scrape.
- ⚠️ **THIRD 429 TYPE — `DEALER_QUOTA` (hit 2026-08-01, 5 PM Opened run):**
- ⚠️ **THIRD 429 TYPE — `DEALER_QUOTA` (first hit 2026-08-01, 5 PM Opened run;
  STILL LIVE as of 2026-08-07 5 PM PDT — a full week, no self-resolution):**
  message `"Limit exhausted for type : DEALER_QUOTA."` — a PER-DEALER quota,
  distinct from OVERALL_RATELIMIT/OVERALL_QUOTA. Signature every time: the
  `repair-orders:search` and `/jobs` endpoints return **200 fine**, but the
  deeper per-RO endpoints (`/operations`, `/parts`) 429 continuously. Because
  search+jobs work, the scraper LOOKS healthy and writes a
  **plausible-but-false 0-menu file (`complete: true`!)** even when real
  TEK-candidate ROs exist. Rules:
  - A 0-menu result with >0 TEK-tag candidates in the search results =
    QUOTA-TRUNCATED, NOT a slow day. Verify with the free tags prefilter
    (search results carry OPCODE tags at no fan-out cost, `ro["tags"]` where
    `field=="OPCODE"`) before trusting 0. Then confirm with ONE deep probe:
    search → `/jobs` → `O.call('GET', jobs['data']['jobs'][0]['operations']['link'])`
    — 429 DEALER_QUOTA on that call = confirmed outage, not a bug.
  - Likely drain source: the DealerDetail sync-all pipeline (fetches 1000s of
    ROs per store, incl. 2900+ at SCT nightly at 23:00, plus a */30 heal-backfill
    cron) shares the dealer quota. A documented "kill nightly sync" containment
    plan (written 8/3) did NOT reliably self-execute/hold — outages recurred
    8/3, 8/7 and beyond despite it, so don't assume a past containment note
    means the issue is fixed; re-verify live every time.
  - **RECOVERY-WATCHER FALSE POSITIVE (hit repeatedly):** a watcher that probes
    only `repair-orders:search` + `/jobs` WILL fire "window clear" while
    `/operations` is STILL 429ing — search/jobs recover first. Any recovery
    probe MUST test the DEEPEST endpoint the scrape needs (the `/operations`
    link), and the post-recovery scrape output must be sanity-checked:
    `record_count == 0` while the tags prefilter shows TEK candidates ⇒ still
    truncated, re-queue, do not trust `complete:true`.
  - **Watcher process-management:** killing a flock-guarded watcher can leave
    its in-flight `sleep` child holding the lock fd — relaunch then falsely
    exits "already running". Diagnose with `fuser -v /tmp/<lock>`, kill that
    PID, confirm `fuser` empty, relaunch. Before launching a NEW dated watcher,
    always `pgrep -af wait_ops_then_scrape` (or the dated variant) + check its
    elapsed time — if one is already alive and within its deadline, do NOT
    relaunch a duplicate; just read its log tail for the latest probe result.
  - **Do not render/email a false zero.** Every outage day: flag the JSON
    `complete:false` + note, do NOT run render_scorecard.py, do NOT email —
    report the outage with last-known-good data (labeled by its as-of date)
    instead. Reusable one-shot watcher pattern: flock-guarded bash loop, poll
    the deep `/operations` link every 10 min, on first 200 run the real
    scraper + renderer once and touch a dated marker file.
  - **Outage timeline (for context on how long this can run):** started 8/1
    5:01 PM PDT, confirmed still active through at least 8/7 5:00 PM PDT
    (7 calendar days, ~10+ separate cron runs lost). Last known-good SCT
    Opened data throughout: 7/31/26, 5 menus, $1,490.98 labor / $454.33 parts
    = $1,945.31 total. If a DEALER_QUOTA outage spans 2+ days, escalate to
    Joe for a Tekion quota review/support ticket — polling alone will not
    fix it, and passive containment notes have not held in practice.
  - **Ad-hoc verification probe script gotchas (avoid burning calls re-learning
    these):** `sct_menu_sales_api.OPCODE_LIST` is a JSON list of DICTS
    (`{"opcode": "TEK...", ...}`), not bare strings — build the maint set with
    `{d['opcode'] for d in json.loads(O.OPCODE_LIST.read_text())}`, not
    `set(json.loads(...))` (TypeError: unhashable dict). RO records from
    `fetch_ros` have no `id` key — the real id is `ro['documentId']`.
    `ro['jobs']['link']` and each job's `operations['link']` are already FULL
    paths (`/repair-orders/...`) — pass them to `O.call('GET', link)` as-is;
    prefixing `/openapi/v4.0.0` again produces a doubled-path 404.
- ⚠️ **TWO DISTINCT 429 TYPES — read the `message` (learned 2026-07-08):**
  `OVERALL_RATELIMIT` = rolling ~15-min window, resets in ~8-15 min → the
  poll-until-200 recovery above works. `OVERALL_QUOTA` = **org-wide daily
  quota**, shared across ALL pipelines (Caliber invoice scrape, TOL backfill,
  BC/SCT menu jobs). On 2026-07-08 it stayed exhausted **12+ hours** and did
  NOT reset overnight — the outage ran ~37 hrs across two full business days
  (7/8 5:35 AM → 7/9 6:17 PM+), costing noon/5PM/6PM crons on both days.
  Polling is futile once it's clearly org-wide daily quota, not a rolling
  window — confirm via 2-3 paced probes ~10 min apart, cross-check sibling
  logs (`data/tol-closed-backfill-*.log`, `~/caliber-ops/logs/tekion-nightly.log`,
  `data/sct-align-selfheal-<date>.log`) for corroborating 429s, then GIVE UP
  and report with last known-good — do not burn hours polling a daily quota.
  `fetch_ros`'s retry loop (429 → sleep 185 → continue) does NOT distinguish
  QUOTA from RATELIMIT and will loop forever with buffered/invisible output on
  a quota day — probe the type yourself with one search call and kill the
  scraper if it's OVERALL_QUOTA rather than waiting on it.
  The "0 records is VALID — still send" rule applies ONLY to a clean scrape
  that genuinely found 0 menus. A quota outage produces no usable data file —
  that's a failure, not a slow day: do not render, do not email; report the
  outage with last known-good labeled by its as-of date. After an outage,
  the closed-MTD daily append scans TODAY only — append each missed date
  first via the positional date arg before running today's default append,
  or missed days silently drop from the MTD total.
  Do NOT render/email stale master data as today's report. After the outage,
  the daily append scans TODAY only — **append each missed date first** via the
  positional date arg (`sct_menu_sales_closed_mtd.py 2026-07-07`) before
  running today's default append, or the missed day silently drops from MTD.
  (2026-07-08 outage FINAL: quota stayed exhausted the ENTIRE day — 429 from
  5:35 AM through at least 6:25 PM; noon Opened, 5 PM Opened, AND 6 PM Closed
  crons all lost. 7/7 evening was ALSO missed (no closed file for 07-07). So
  the 07-09 closed run must append BOTH `2026-07-07` and `2026-07-08` via
  positional-date runs before the default today-append. Quick check for missed
  days: `ls data/sct-menu-sales-closed-2026-07-*.json` — any calendar-day gap
  since the 1st needs a positional append.)
  **2026-07-09 UPDATE: the OVERALL_QUOTA outage did NOT reset overnight** — 429
  continuously from 7/8 5:35 AM through at least 7/9 12:12 PM (30+ hrs). The 16h
  quota-recovery watcher timed out (`quota-recovery-2026-07-08.log`: "TIMEOUT 16h
  — quota never restored"). So OVERALL_QUOTA is NOT a simple daily reset — either
  the org's quota allocation changed or another consumer drains it instantly at
  reset. If a second consecutive day 429s, flag that a Tekion support ticket /
  API quota review is likely needed; do not burn hours polling.
  **2026-07-09 5 PM UPDATE: still 429 OVERALL_QUOTA at 17:01 PDT** — the outage
  now spans the ENTIRE second day (7/8 5:35 AM → 7/9 5 PM+, ~36 hrs continuous;
  `quota-recovery2-2026-07-09.log` shows 429 on every 30-min probe all day).
  7/9 noon + 5 PM Opened crons AND presumably the 6 PM Closed cron all lost.
  Days now needing positional closed-append when quota returns: 2026-07-07,
  2026-07-08, 2026-07-09. A Tekion support ticket / org API quota review is
  DEFINITELY needed — escalate to Joe; polling is futile.
  **2026-07-09 6 PM FINAL: still 429 OVERALL_QUOTA at 18:17 PDT** — the 6 PM
  Closed cron ALSO lost on 7/9. Outage now ~37 hrs continuous across two full
  business days. Closed-append backlog when quota returns: **2026-07-07,
  2026-07-08, 2026-07-09** (positional-date runs, oldest first, THEN the
  current-day default append).
  **2026-07-10 ~12:16 PM: QUOTA RESTORED** — probe returned 200 and the noon
  Opened run completed cleanly (8 menus, no 429). Total outage ≈ 2026-07-08
  5:35 AM → sometime before 2026-07-10 noon. The 7/10 6 PM Closed cron still
  owes the positional appends for 07-07/07-08/07-09 before today's default. Last known-good closed MTD = 7/6 6:01 PM:
  34 menus, $11,873.73 labor / $4,305.20 parts = $16,178.93 total. Token from `tekion_client.get_token(cfg)`; endpoint
  `cfg["base_url"]/openapi/v4.0.0/repair-orders:search` with body
  `{"filters":[{"field":"creationTime","operator":"BTW","values":[str(ms0),str(ms1)]}],"pageSize":50}`.

**Clean opened-report 429 recovery (proven 2026-06-29 — textbook):** a `wait-then-scrape`
bash wrapper is the cleanest one-shot. Run it BACKGROUND (notify_on_complete + watch
`["window clear","gave up","sct-api"]`). The poller's probe can just call
`O.fetch_ros(ms0, ms1)` in a try/except (200 → break; "429" in str(e) → sleep 60, retry).
IMPORTANT: `fetch_ros` is a READ that BURNS the limit but does NOT write any files —
only the full `sct_menu_sales_api.py` run writes the two JSON files. So after a 200 probe
the wrapper must still invoke `sct_menu_sales_api.py` once; the probe alone produces no
output files. PROOF the authoritative scrape ran (not just the probe): both
`data/sct-menu-sales-api-<today>.json` and `data/sct-menu-sales-opened-<today>.json` exist
with a fresh `pulled_at`, `complete: true`, and `row_count == expected_records`. The
background process buffers stdout (the `echo "poll N"` lines may never flush mid-run) —
do NOT rely on log output to know it finished; check for the freshly-written data files
instead, then KILL the still-sleeping wrapper once the files are present. On 6/29 the
account-wide window was already exhausted on the very FIRST scrape attempt (429 immediately,
NOT from my own re-runs — a prior unrelated job had drained it); the wrapper cleared it on
an early poll and produced a clean 6-record pull, all advisors resolved to real names via the
public API. The render PNG was only ~900px tall (small dataset), so full-page vision OCR read
the KPI digits CORRECTLY — the cropped-band step is only mandatory for the tall (~6427px) MTD
layout, but running both costs nothing. Send was a textbook happy path: draft 39115 → SMTP
template-send → Sent copy verified TO=jcastelino@americanmotorscorp.com, TOTAL matched, no
wrong-recipient/blank-figure trap.

## CLOSED Month-To-Date variant — the SCALE rate-limit trap (2026-06-17)

A "Closed MTD" report (Joe wants daily 6 PM, status finalized, month-to-date
incl. today) is NOT the same shape as the daily Opened report and CANNOT be
built by the same brute-force scan. Script: `sct_menu_sales_closed_mtd.py`
(imports `sct_menu_sales_api as O` and reuses scan_ro/advisor/render wholesale;
only the RO search filter + output labels differ).

What "closed" means in the API: RO `status` field values observed are
`CLOSED, INVOICED, READY_FOR_INVOICE, HOLD, UNASSIGNED, IN_PROGRESS`. Finalized
/ booked dollars = `status IN ["CLOSED","INVOICED"]`. The search DOES accept a
`{"field":"status","operator":"IN","values":[...]}` filter alongside a time
`BTW` filter (verified 200 OK).

**THE TRAP — do not repeat:** Month-to-date at SCT = ~2,698 closed ROs. scan_ro
makes several calls PER RO (jobs→operations→parts→vehicle), so one MTD pass =
THOUSANDS of calls → **guaranteed 429 OVERALL_RATELIMIT exhaustion mid-scan.**
The older ROs then silently return `[]` (the `if stj != 200: return out` trap),
so the result is TRUNCATED: e.g. a test returned 19 menus but ALL clustered on
the last 3 days (Jun 15-17), nothing from Jun 1-14. The `[sct-api]` log looked
clean. **A full-month re-scan every run will always fail this way.**

Also: do NOT filter the window on `modifiedTime` (last-touched) — it is the
wrong field for "closed in period". Need the real invoice/close timestamp
(likely in `ro["invoices"][]`; inspect a CLOSED/INVOICED RO to confirm — but do
it AFTER the rate-limit window resets, ~8-10 min, or you re-trigger 429).

### ✅ WINDOW FIELD RESOLVED — use `closedTime` (verified 2026-06-19)
The `repair-orders:search` filter DOES accept `closedTime` and `invoicedTime` as
window fields (alongside `status IN [CLOSED,INVOICED]`). Counts for the SAME 24h
window prove why `modifiedTime` was wrong:
- `closedTime`   → 152 ROs  (TRUE "closed in period" — USE THIS)
- `invoicedTime` → 222 ROs  (valid if counting revenue at invoice instead)
- `modifiedTime` → 263 ROs  (last-touched — OVERCOUNTS; includes ROs closed days
                              ago but edited today. This is what the old pipeline
                              used → inflated/noisy counts.)
`sct_menu_sales_closed_mtd.py`'s `search_closed(ms0, ms1, field="closedTime")`
now defaults to `closedTime` (both seed + daily call sites).

**GOTCHA — the search RESULT does NOT echo closedTime/invoicedTime back.** Both
fields are `null` in every result record even though the FILTER works correctly.
So you can FILTER membership by close-date, but you can only DISPLAY/BUCKET rows
by `creationTime` (when the RO was opened). Don't try to group the report by
close-day — that data isn't in the search payload.

**After changing the window field you MUST re-seed the month master** — the old
master was built on `modifiedTime` so it has the wrong row set (rows that closed
in May but were modified in June, and missing rows that closed in June but were
modified later). `rm data/sct-menu-closed-mtd-MASTER-<YYYY-MM>.json` (back it up
first), then `sct_menu_sales_closed_mtd.py --seed`. June 1-19 = 2,807 closed ROs,
47 paced batches (60/batch, 20s rest), ~16-20 min, no 429.

**Correct architecture — incremental daily cache (NOT brute-force MTD):**
Each 6 PM run scans ONLY that day's newly-closed ROs (~100-150, safe), then
APPENDS to a running month-to-date JSON. Report shows full MTD totals assembled
incrementally. Reset the accumulator at month rollover. Optionally seed the
already-elapsed part of the current month with ONE carefully PACED backfill
(sleeps between RO scans) — never an unthrottled full-month sweep.

Confirm with Joe before cron: (1) closed = CLOSED+INVOICED vs strict CLOSED,
(2) seed this month's history or accumulate forward only.

## Session restore on 2026-06-16 — navigation gotcha

`/health` returning `{"status":"ok"}` only means the NODE SERVER is up, NOT that
Tekion is authenticated. ALWAYS probe the real auth state:
`curl -X POST :9223/eval -d '{"js":"(()=>JSON.stringify({url:location.href,t_token:!!localStorage.getItem(\"t_token\")}))()"}'`.
If url is `/login?redirectTo=...` or `t_token` is false → session is dead; do the
full restore (login.py → inject cookies → inject localStorage one-at-a-time).

Navigation gotchas hit during restore:
- After a FAILED goto, the page sits on `chrome-error://chromewebdata/` where
  localStorage access throws `SecurityError: Access is denied`. You MUST be on a
  real tekioncloud page before setting localStorage.
- `/home` and `/` can return `net::ERR_FAILED` while the session is only
  partially seeded, but `/login` reliably returns HTTP 200. So: inject cookies →
  navigate to `/login` (gives a valid tekioncloud origin) → set all 21
  localStorage keys one-at-a-time → THEN the app auto-redirects `/login`→`/home`
  once `t_token` is present. Confirm by re-reading `location.href` (shows
  `/home`) and doing a test fetch to
  `/api/userservice/u/apc/users/<id>` (HTTP 200 + a real name = authenticated).
- Other domains (google.com) loading fine while tekioncloud ERR_FAILs is NORMAL
  mid-restore — not a network outage; it clears once localStorage is seeded.

## Emailing — STACEY OWNS THE EMAIL. NEVER SEND IT YOURSELF. (2026-06-17)

**HARD RULE learned the hard way (Joe was frustrated):** Jay's job is ONLY to
produce the data files (JSON + PNG + PDF in `/home/itadmin/tekion-reports/data/`).
**Stacey composes and sends the email.** Do NOT bypass her and send via himalaya
directly — it WILL fail and look broken:
- Piping a hand-built `.eml` with himalaya `<#part type=... filename=...>` MIME
  markup through `himalaya message send` does **NOT render** — the message
  arrives as a broken `<#part type=application/octet-stream>` blob with the
  literal `<#!part...>` markup as plain text, **no inline image, no real
  attachments.** That markup syntax only works in himalaya's *template/compose*
  flow, not on a literal piped send.
- Stacey's `joe-email-jay-report` skill uses **base64 data-URI inline PNG**,
  which is the ONLY approach that survives Gmail's pipeline and renders the
  picture inline. That pipeline lives in HER profile; Jay does not have it.

**The EXACT format Joe wants** (his approved reference = his own Opened-report
email, e.g. himalaya msg 72839 sent 2:38pm 2026-06-17). Layout, top to bottom:
```
Kevin,

Attached is [today's SCT Menu Sales daily opened report | the SCT Menu Sales
closed month-to-date report (<window>)].
N menus, $LABOR labor / $PARTS parts = *$TOTAL total*.   <- total is BOLD

[scorecard PNG INLINE — IN THE MIDDLE of the body]

Sent from Tekion Open API — live data
<Joe signature / AMG logo>
```
The non-negotiable: **picture INLINE, IN THE MIDDLE** (after the summary line,
before the "Sent from Tekion Open API" footer). Subject lines are approved as-is
— do not reword them.

**Email recipients — DIFFERS BY REPORT TYPE — but ALWAYS obey the task spec's
explicit recipient over these defaults:**
- **Opened** (daily noon/5pm) → TO **Kevin Stapp <kstapp@sctoyota.com>**; a
  "validation send" goes TO Joe but the BODY still greets "Kevin," so Joe sees
  exactly what Kevin will get.

  ⚠️ **STACEY HARDCODES OPENED → KEVIN IN HER SMTP TEMPLATE-SEND, OVERRIDING THE
  DRAFT'S RECIPIENT (hit 2026-06-20).** When a cron task explicitly says to email
  the OPENED report TO Joe (jcastelino@americanmotorscorp.com) — e.g. an Opened
  report requested as Joe's copy — Stacey's "joe-email-jay-report" SMTP path
  STILL defaults the Opened report TO kstapp@sctoyota.com, even though the draft
  you had her build (38579) was correctly addressed to Joe. The first Sent copy
  landed at Kevin; her summary even said "sent to Kevin" while claiming success.
  → After ANY Opened send where the spec wants Joe, the read-only Sent verify
    MUST check the **TO: header**, not just subject+total. Ask literally:
    `TO=<recipient>` / `TOTAL=<body total>`. If TO is Kevin, re-ask her to send
    a copy with `TO=jcastelino@americanmotorscorp.com ONLY` and greet "Joe,".
  → She then gave TWO false-positive "Sent to Joe @ 12:07/12:09" replies while a
    recipient-scoped Sent search returned `TOJOE=NO`. Do NOT trust her "Sent to
    Joe" word — confirm with a recipient-counting read-only query:
    `JOECOPIES=<count of Sent copies whose TO header contains jcastelino@...>`.
    Only declare success when JOECOPIES≥1. (On 6/20 the forced re-send finally
    landed; the retry loop left 3 identical correct copies to Joe — duplicated
    but correct, not worth recalling.)
- **Closed MTD** (daily 6pm) → TO **Joe, jcastelino@americanmotorscorp.com**, and
  the body greets **"Joe,"**. This is CORRECT and intentional — the closed MTD is
  Joe's internal companion report, NOT the customer-facing Opened report.
  ⚠️ Stacey will PROACTIVELY FLAG "this went only to Joe, not Kevin like the
  Opened report" (she did on 6/19). That flag is a false alarm for the closed
  report — do NOT "correct" it by forwarding to Kevin. Recipient comes from the
  cron task spec; closed = Joe, opened = Kevin.
  ⚠️⚠️ **HARDCODE-TO-KEVIN TRAP ALSO HITS THE CLOSED REPORT (hit 2026-06-23).**
  Even with a draft correctly addressed to Joe (38778), Stacey's SMTP
  template-send put the FIRST Sent copy (msg 9685) to **kstapp@sctoyota.com** and
  her reply literally said "sent to Kevin" while claiming success. The body TOTAL
  was correct ($78,988.77) but the TO was wrong. → After the closed send, the
  read-only Sent verify MUST extract the **TO header** (not just subject+total):
  `TO=<recipient> | TOTAL=<body total> | TS=<ts>`. If TO=Kevin, re-ask her to
  SEND a fresh copy `TO=jcastelino@americanmotorscorp.com ONLY, greet 'Joe,',
  override any hardcoded Kevin default`. On 6/23 the forced re-send landed
  correctly to Joe @ 18:10 (verified TO=jcastelino...). Do NOT trust her "sent to
  Joe" word — confirm with a terse `TO=<recipient> TS=<ts>` read of the NEWEST
  Sent copy (a verbose multi-field verify silently timed out → empty; the terse
  one-liner returned cleanly on first try). The first wrong-recipient copy to
  Kevin is a harmless leftover — not worth recalling.

**Whose template:** `joe-email-jay-report` at
`/home/itadmin/.hermes/profiles/email-agent/skills/joe-email-jay-report/SKILL.md`
is the canonical, working one (base64 data-URI). The older
`sct-menu-sales-report-email` / `jay-tekion-report-email` skills used
CID/multipart-related which Gmail strips on IMAP drafts — deprecated.

Stacey reads from `/home/itadmin/tekion-reports/data/`:
- Opened: `sct-menu-sales-opened-<date>.json` + `SCT-Menu-Sales-Scorecard-<date>.png/.pdf`
- Closed: `sct-menu-sales-closed-<date>.json` + `SCT-Menu-Sales-Closed-Scorecard-<date>.png/.pdf`
JSON she expects: `.totals.labor_gross`, `.totals.parts_gross`, `.row_count`.

### Mechanics of asking Stacey — KNOWN PAINFUL, follow exactly

Stacey is the email agent: `timeout 150 ~/bin/ask-agent stacey "<message>"`.
She DRAFTS by default. Subject: `Menu Sales — Daily Opened Performance Report —
SCT <m/d/yy>`. Recipient: `jcastelino@americanmotorscorp.com`. Attach the PDF by
**full path**. Body = 1-2 sentences with labor gross, parts gross, total, menu
count from the opened-JSON totals. Tell her to include "Joe's standard email
signature (she knows it)".

PITFALLS (all hit on 2026-06-15):
- **ask-agent send calls frequently TIME OUT at 150s (exit 124)** even though
  work may still be ongoing. A timeout is NOT proof of failure or success.
  → After ANY send attempt, run a SHORT separate verification call:
    `timeout 130 ~/bin/ask-agent stacey "Is '<subject>' to <addr> in the Sent
    folder now? Reply Sent + timestamp, or NotSent."`
- **Two-step send**: after she confirms the draft, send a SECOND message telling
  her to SEND that specific draft. Do not assume the draft auto-sends.
- **Draft-ID collisions**: a draft ID (e.g. 38333) can collide with an INBOX
  message ID. Telling her "send draft <ID>" can make her grab the wrong item.
  → ALWAYS disambiguate by SUBJECT, e.g. "send the 'Menu Sales … SCT 6/15/26'
    draft (the 6/15 one, NOT 6/14)", not just the bare ID.
- Her raw himalaya draft-send is unreliable; she falls back to "template send".
- Don't accept a Sent confirmation whose date/subject is YESTERDAY's report —
  verify the timestamp/subject matches TODAY before declaring success.
- **FALSE-POSITIVE "Sent" — the worst trap (hit 2026-06-18).** Stacey can reply
  a confident "✅ Sent — <timestamp>" while the message is STILL just a draft.
  On 6/18 she said "Sent 12:09:41 PM" but a follow-up showed it sitting in
  Drafts (IDs 38510/38511) — the IMAP raw draft-send had silently not delivered.
  Her own "Sent + timestamp" reply is NOT proof. NEVER declare success on her
  word alone.
  → ALWAYS verify by forcing a SENT-FOLDER search, not a Drafts check:
    `timeout 150 ~/bin/ask-agent stacey "Search ONLY [Gmail]/Sent Mail for
    subject '<subject>'. Does a SENT copy exist there with timestamp? Separately
    say whether draft <ID> still exists. If NO Sent copy, SEND it now (Gmail
    X-GM-RAW / SMTP template-send), delete the leftover draft, confirm."`
  → The reliable delivery path is her **SMTP template-send** (which DID land a
    real copy in [Gmail]/Sent Mail on 6/18, msg 9564). The IMAP draft-send is
    the one that lies. If the first "send draft" produces a false Sent, just
    re-ask her to rebuild + SMTP-send and delete the duplicate draft.
- **NEW FALSE-SENT VARIANT — \"exported in /tmp\" artifact (hit 2026-07-11).**\n  Stacey's IMAP draft-send can land a Sent copy that is a BROKEN ARTIFACT:\n  blank subject, body literally `Message <draftID> successfully exported in\n  /tmp!`, no report text, no PDF — while she replies \"Sent 12:20 PM\" and\n  deletes the draft. Her ask-agent verify then times out (exit 124) or returns\n  garbled noise (`тихо` spam + NOTSENT). FASTEST verify: skip her entirely and\n  read Sent Mail YOURSELF with himalaya (read-only, safe):\n  `himalaya envelope list -f \"[Gmail]/Sent Mail\" -s 5` then\n  `himalaya message read <id> -f \"[Gmail]/Sent Mail\"` — check TO, subject,\n  body dollar figures, and the `<#part type=application/pdf ...>` attachment.\n  (Reading via himalaya is fine; only SENDING via himalaya is forbidden.)\n  Recovery: re-ask her to REBUILD from scratch + SMTP template-send; on 7/11\n  that landed correctly on the first retry (verified via himalaya read).\n- **GREETING-ONLY leak variant (hit 2026-07-14 closed run).** Stacey's SMTP\n  template-send delivered a CORRECT closed email (TO=Joe, right subject, right\n  literal dollar figures, real inline PNG + real PDF attachment — md5 matched\n  source) but the body greeted \"Kevin,\" from the opened template, despite the\n  draft instructions saying greet 'Joe,'. Decision rule: if recipient + numbers\n  + attachments are all verified correct, do NOT re-send just to fix the\n  greeting — a duplicate email is worse than the cosmetic name. Note it in the\n  summary. Cheap md5 verify of the real attachment:\n  `himalaya attachment download <id> -f \"[Gmail]/Sent Mail\"` (drops files at the\n  /tmp paths named in the part markup) then `md5sum` against the source PDF/PNG.\n- **OPENED-WORDING + RENAMED-FILENAME leak variant (hit 2026-07-18 closed run).**
  SMTP template-send delivered a CORRECT closed email (TO=Joe, greet 'Joe,',
  right subject, exact literal dollar figures, real multipart MIME with PNG+PDF
  attachments) but the body sentence said \"today's SCT Menu Sales daily opened
  report\" and the attachments were RENAMED without \"Closed\"
  (SCT-Menu-Sales-Scorecard-<date>.pdf). The renamed PDF's md5 MATCHED the real
  Closed scorecard source — content was right, filename cosmetic. Decision rule
  (same as the 7/14 greeting leak): recipient + numbers + verified-correct
  attachment content ⇒ do NOT re-send; note it in the summary. ALWAYS md5 the
  the downloaded attachment against BOTH the Closed and Opened source PDFs to prove\n  which one actually went out. ⚠️ md5-verify pitfall (hit 2026-07-20): if a file\n  with the attachment's name ALREADY exists in /tmp (e.g. Stacey's own build\n  artifact from 17:05), `himalaya attachment download` writes `<name>_1.pdf`\n  instead of overwriting — md5'ing the same-named /tmp file checks the STALE\n  artifact, not the Sent attachment. Find the fresh file with\n  `find /tmp -newermt \"<send-time>\" -name '*.pdf'` and md5 THAT.
  which one actually went out.
- **CORRECT-BODY / NO-REAL-ATTACHMENT variant (hit 2026-07-21 opened run) —\n  the sneakiest one: TO+subject+body-numbers ALL CORRECT, so a terse\n  TO+TOTAL verify PASSES, yet the Sent copy is a SINGLE plain-text part with\n  the `<#part type=application/pdf ...>` markup as literal text — no real PDF,\n  no inline PNG.** Trigger: the \"send draft <ID>\" ask returned EMPTY output\n  (exit 0), then the draft-send path delivered the broken copy at 12:06.\n  → EVERY send verify must include the MIME check, even when TO/numbers look\n  right: `himalaya message export <id> -f \"[Gmail]/Sent Mail\" --full | grep -iE\n  \"content-type|content-disposition\"` — a real send shows `multipart/mixed` +\n  `Content-Disposition: attachment; filename=...`; if the grep returns ONLY the\n  literal `<#part ...>` line (no multipart headers), it's broken. Recovery:\n  re-ask REBUILD from scratch + SMTP template-send (landed first retry 12:10,\n  verified multipart + md5-matched PDF). The broken copy is a harmless leftover.\n- **WRONG-BODY draft-send variant (hit 2026-07-12 closed run).** Stacey's first
  draft+send produced a Sent copy (10959) whose BODY was the wrong TEMPLATE
  entirely — greeted \"Kevin,\", said \"daily opened report\", and both PNG+PDF were
  literal `<#part ...>` markup pointing at /tmp (nothing attached) — even though
  the DRAFT instructions explicitly said closed report / greet Joe / real paths,
  and her reply claimed success with the right numbers. The himalaya read-only
  Sent check caught it immediately. Recovery = re-ask her to REBUILD from scratch
  + SMTP template-send (worked first retry, msg 10961). VERIFY the greeting +
  \"closed month-to-date\" wording + real MIME attachment
  (`himalaya message export <id> -f \"[Gmail]/Sent Mail\" --full | grep -iE
  \"content-type|filename\"` → expect multipart/mixed + Content-Disposition:
  attachment with the real PDF filename). Note: `[Inline PNG]` in the plain-text
  part is NORMAL (the HTML alternative has the base64 image), and himalaya read
  shows real attachments as `<#part>` too — the export/grep MIME check is what
  distinguishes a real attachment from markup-as-text.
- **Em-dash in subject breaks IMAP ASCII encoding.** The approved subject has a
  real "—" (U+2014). Stacey's IMAP search/send chokes on it ("em dash tripped
  IMAP's ASCII encoder"); she recovers via Gmail's X-GM-RAW. Expect this detour
  — it's not a failure, just slower. Disambiguate drafts by the m/d date too.
- **Duplicate drafts are common** (two identical drafts at the same minute, e.g.
  38510 + 38511). Tell her to SEND one and DELETE the other so only one copy
  goes out. Confirm "zero matching drafts" in the final verification.
- **Duplicate SENT copies happen too (hit 2026-06-19), not just duplicate
  drafts.** When the first "send draft" ask-agent call returns EMPTY output
  (exit 0, no text — a silent timeout), the work often DID proceed. Do NOT re-ask
  her to "send" again blindly — a retry can fire a SECOND real send. On 6/19 two
  empty-output send asks resulted in TWO real sent copies in [Gmail]/Sent Mail
  (12:06 + 12:07, both with the PDF) PLUS two leftover drafts (38557 + 38559).
  Recipient gets two identical (correct) emails — annoying but not wrong; not
  worth recalling. PREVENTION: after an empty/timeout send ask, do a READ-ONLY
  Sent-folder verify FIRST ("is it in Sent? reply Sent <ts> or NotSent") before
  ever re-issuing a send. Only re-send if verify says NotSent.
  ✅ BEST PATTERN (proven 2026-07-29): after a timed-out (exit 124) send ask,\n  first poll himalaya Sent yourself (~60-150s total); if no copy appears,\n  collapse verify+recovery into ONE conditional ask: \"Verify first: is there a\n  Sent copy of '<subject>'? I see none in [Gmail]/Sent Mail. If NOT sent:\n  REBUILD from scratch and SMTP template-send NOW. <full spec: TO/greeting/\n  literal-numbers sentence/closed-MTD wording/PNG+PDF paths/footer>. Delete any\n  leftover draft <ID>. Reply one line: SENT <ts> TO <recipient>, or NOTSENT.\"\n  This makes Stacey do the Sent check herself before acting, closing the\n  duplicate-send window between a separate verify call and a separate re-send\n  call — on 7/29 it landed correctly on the first retry (verified multipart\n  MIME, md5-matched PDF, 0 leftover drafts). Include the FULL rebuild spec in\n  that ask so a NOTSENT outcome needs no follow-up message.\n  CONFIRMED BOTH WAYS 2026-07-13: a timed-out (exit 124) send ask was a GENUINE\n  non-send — himalaya Sent-list showed nothing after 2.5 min of waiting, and the\n  terse read-only verify returned NOTSENT; ONE explicit SMTP re-send then landed\n  cleanly (msg 11040, no duplicates, 0 leftover drafts). So a timeout is truly\n  indeterminate: verify FIRST, then act on NOTSENT — the loop works in both the\n  \"actually sent\" (6/19) and \"actually not sent\" (7/13) cases. Waiting/polling\n  himalaya Sent yourself for ~2-3 min before asking Stacey is a cheap first check.
- **STALE earlier-send collision — verify Sent-copy CONTENTS, not just existence (hit 2026-06-19, 5 PM run).** When a Sent-folder search for today's subject returns copies, do NOT assume they're yours — an EARLIER run the same day (e.g. a noon Opened run, or a validation send TO Joe vs the real send TO Kevin) can leave Sent copies with DIFFERENT numbers and/or a different recipient. On 6/19 the 12:06/12:07 Sent copies were a noon run (7 menus / $5,915.30, to Kevin) while the 5 PM run's correct data (10 menus / $5,234.94, to Joe) was still only a DRAFT. A bare \"2 copies in Sent\" check would have falsely concluded \"already sent\" and skipped the real send. → After a timed-out send, the read-only Sent verify must check the BODY NUMBERS + RECIPIENT of each Sent copy against today's totals, not just that *a* copy with the subject exists. Only conclude \"already sent\" if a Sent copy matches BOTH today's exact totals AND the intended recipient. Otherwise the draft still needs sending.\n  RE-CONFIRMED 2026-06-22 (same-recipient stale-copy trap): an earlier NOON Opened send to Joe (total $1,625.84) sat in Sent while the 5 PM run draft (38623, total $2,384.81 / 8 menus) was still UNSENT. A terse 'is it in Sent? SENT/NOTSENT' replied 'SENT 12:03' — TRUE for the STALE noon copy, which would have falsely ended the task. The stale copy had the SAME recipient AND subject AND date, differing ONLY in TOTAL. The catch: a follow-up read-only ask for TS+TO+TOTAL of the MOST-RECENT Sent copy returned TOTAL=$1,625.84 != today $2,384.81, proving the real send had NOT happened. Recipient-match alone is NOT enough when multiple same-day runs exist; the verify MUST extract the body TOTAL and compare to the opened-JSON total, then re-ask Stacey to SEND the specific newer draft ID with the EXPECTED total stated. A final TS+TO+TOTAL read confirmed $2,384.81 to Joe.\n- **Leftover drafts can be MULTIPLE and must be deleted one round at a time.**
  After a send, ask her to delete the leftover draft; she may then report ANOTHER
  same-subject draft (the second send's leftover). Loop: delete → re-ask
  "how many drafts with subject '<subj>' remain? reply just the number" until 0.
  A short bare-number verification call ("reply just the number") is the most
  reliable final confirmation — it survives the 150s timeout where verbose asks
  return empty.
- **BLANK DOLLAR FIGURES IN THE SENT BODY — verify the NUMBERS, not just TO+TS (hit 2026-06-26 closed run).**
  Stacey's SMTP template-send can deliver a real Sent copy with the correct
  recipient/subject/timestamp AND the correct menu COUNT, but with all three
  DOLLAR figures rendered BLANK — body reads literally
  `"204 menus,  labor /  parts =  total."`. Root cause: the `*$83,963.78 total*`
  markdown/variable substitution silently dropped the digits in her SMTP path.
  The TO/TS/subject verify passed clean (TO=Joe, TS=today) — only a SEPARATE
  body-numbers read caught it. → After the closed send, the read-only Sent verify
  MUST extract the body DOLLAR figures, not just TO+TS:
  `Reply one line: TO=<recipient> | NUMS=<exact $ figures in body, or BLANK> | TS=<ts>`.
  If NUMS=BLANK, re-ask her to REBUILD + re-SEND with the numbers as PLAIN
  LITERAL TEXT typed verbatim (no markdown asterisks, no variables), e.g.
  `'204 menus, $60,609.41 labor / $23,354.37 parts = $83,963.78 total.'`. On 6/26
  the literal-text rebuild landed correctly @ 6:07pm with all three figures
  present. The first blank-figure copy is a harmless leftover. NOTE: a `MATCH/MISMATCH`
  body check is more reliable than the bare `NUMS=` template when probing — on
  6/26 her first total-check returned `MISMATCH=204 menus, labor / parts = total`
  which immediately exposed the blanks.
- **VERIFY queries must be ONE terse line, not a multi-field template (re-hit
  2026-06-20 closed run).** A read-only Sent-folder verify asking her to fill a
  structured template (`TO=<..> | TS=<..> | TOTAL=<..> | DRAFTSLEFT=<..>`)
  silently timed out → EMPTY output TWICE in a row. The SAME check rephrased as a
  single terse instruction — `"Reply only: SENT <timestamp> TO <recipient>, or
  NOTSENT."` — returned cleanly (`SENT 2026-06-20 18:07-07:00 TO Joe Castelino`)
  on the first try. So when a verbose/multi-field ask-agent verify returns empty,
  do NOT assume failure and do NOT re-send — just re-ask the SAME read-only
  question collapsed to one short sentence with a fixed minimal answer format.
  (The closed 6/20 send itself was clean: draft 38587→Joe, SMTP template-send,
  Sent copy confirmed 6:07pm PDT, draft trashed, no dup — textbook happy path.)

## CLOSED Month-To-Date variant — NOW RELIABLE VIA API (FIXED 2026-06-19, supersedes the "use Report Builder" conclusion)

✅ **The API CAN count a full month of closed menus reliably — once you add the
OPCODE-tags PREFILTER + per-RO retry + failure tracking. The prefilter was the
missing piece.** The earlier "API IS UNRELIABLE → use Report Builder" verdict was
correct ONLY for the naive full-fan-out design; do NOT default to Report Builder
anymore.

### The original failure (2026-06-17, kept for context)
The first `sct_menu_sales_closed_mtd.py` (`--seed` paced backfill) fanned out
jobs→operations→parts on ALL ~2,800 closed ROs. Same month returned a DIFFERENT
total each run (28 / 35 / 17 menus). ROOT CAUSE: per-RO calls fail a random
subset every run (429 AND raw `URLError [Errno 104] Connection reset`); `scan_ro`
swallows non-200 as `[]`, so menus silently drop. The clean batch log was a LIE —
batch-done ≠ scan-complete. Re-hit 2026-06-19: a re-seed returned **15 menus
clustered on just 3 days** (6/6, 6/7, 6/18), nothing across the other 16 — the
unmistakable truncation signature (real data is spread across all days).

### THE FIX — two-tier scan (`scan_records` rewritten 2026-06-19)
1. **PREFILTER on the FREE `OPCODE` tags.** Every `repair-orders:search` result
   carries `ro["tags"]` with `field=="OPCODE"` entries — NO fan-out needed to read
   them. Only ROs whose OPCODE tags intersect the 316 TEK* set get a
   jobs/operations scan. At SCT this is ~150-200 of ~2,800 closed ROs = a ~13x
   call reduction, which keeps the whole MTD scan under the 1,500/15min limit.
   ```python
   def _tek_opcodes(ro, maint):
       return {t.get("value") for t in (ro.get("tags") or [])
               if t.get("field")=="OPCODE"} & maint
   candidates = [ro for ro in ros if _tek_opcodes(ro, maint)]
   ```
2. **`scan_ro_safe(ro, maint)` — retry + tell failure from empty.** `O.scan_ro`
   returns `[]` for BOTH "no menu" and a swallowed non-200, so probe the `/jobs`
   call yourself first: 200 → run scan_ro, return `(recs, True)`; 429/0(reset)/5xx
   → backoff `min(25*(n+1),90)`s and retry (≤6); genuine 404 → `([], True)`;
   exhausted → `([], False)` so the caller knows to re-scan. Returns `(records, ok)`.
3. **Failure tracking + second pass.** Collect every `ok=False` RO, retry them
   serially (≤8 attempts, 2s spacing) in a second pass, then expose any still-failed
   docNumbers via module-level `_LAST_FAILED`. `main()` prints
   `✓ all candidate ROs scanned (no truncation)` or
   `⚠️ N candidate ROs unscanned (possible undercount): [...]`. **Truncation can
   no longer hide** — that printed line is the trust signal.

### Advisor names — public API, NOT browser (see the ⭐ UPGRADE section above)
`resolve_advisors()` now just calls `O.user_name(aid)` (public `/users/{id}`
primary). Drop the `_load_lookups()`/`resolve_advisors_via_browser()` path. Clean
any UUID-as-name entries in `advisor-name-cache.json` first (one-liner above).

### Window field — `closedTime` (see the ✅ WINDOW FIELD RESOLVED section above)
`search_closed(ms0, ms1, field="closedTime")`. After changing it, RE-SEED the
month master (the old one was built on `modifiedTime`).

### Operating sequence for a clean MTD seed (proven 2026-06-19)
1. Probe `repair-orders:search` once; if 429, POLL at 60s until 200 (faster polling
   also burns the limit). A prior bad seed can leave you rate-limited ~8-15 min.
2. `cp` then `rm` the old `data/sct-menu-closed-mtd-MASTER-<YYYY-MM>.json`.
3. Run `sct_menu_sales_closed_mtd.py --seed` as a BACKGROUND process
   (notify_on_complete + watch `["prefilter:","WARNING:","SEED COMPLETE"]`) — the
   wait+scan exceeds the foreground/execute_code limits. A `wait-then-seed` bash
   wrapper (poll for 200, rm master, run --seed) is the cleanest one-shot.
4. Trust the result ONLY if it prints `✓ all candidate ROs scanned`. If it prints
   `⚠️ N unscanned`, just re-run --seed once more — the failed set re-scans.
5. Daily (non-seed) runs scan only today's closed candidates (~100-150 → ~20 after
   prefilter) and append to the master — fast and safe.

DON'T re-run the seed repeatedly to "double-check" — each extra full run risks
429 corrupting the next. One clean run with `✓ all candidate ROs scanned` is
authoritative.

### POST-SEED GOTCHA — leaked numeric advisor ids (hit live 2026-06-19)
A heavy seed can exhaust the rate limit at the VERY END, so the last handful of
`/users/{id}` advisor lookups 429 and **leak raw numeric ids (e.g. 61/68/55) into
the master as the advisor name** — even though the scan itself is 100% complete.
The render would then show "61" instead of "Jon Vu". Symptom: a render or a quick
`Counter(r["advisor"])` shows pure-digit or UUID advisor values. FIX (window is
clear by now): re-resolve each leaked id via `O._user_name_openapi(uid)`, patch
every master row where `advisor==id`, persist the id→name into
`data/advisor-name-cache.json`, then **RE-EMIT the RB file** (`C.emit_rb(master,
asof)`) so the renderer picks up the corrected names. (2026-06-19: 61→Jon Vu,
68→William Dominguez, 55→Jason Sulon — patched 32 rows.) Verify zero digit/UUID
advisors remain before rendering. Final June 1-19 closed = **152 menus /
$63,732.99**, 17 real advisors, 0 Unassigned.

### MONTH ROLLOVER — the master is PER-MONTH; MTD resets on the 1st (verified 2026-07-01)
The master file is `data/sct-menu-closed-mtd-MASTER-<YYYY-MM>.json` — keyed to the
CALENDAR MONTH. On the 1st of a new month `sct_menu_sales_closed_mtd.py` creates a
FRESH master for the new `<YYYY-MM>` and starts accumulating from zero. This is
correct and intended: "month-to-date" resets at month rollover.
- **A cron task spec's baseline note (e.g. "master already holds June 1-17 = 28
  menus / $10,119.08") is STALE the instant the month rolls** — it refers to the
  PRIOR month's master and does NOT carry into the new month. Do NOT try to
  "restore" or merge the prior month's total; the new month legitimately starts at
  the first closed menu of day 1. On 2026-07-01 the correct MTD was just that day's
  7 menus / $3,494.51, NOT June's numbers.
- On the 1st, more than one run can happen (e.g. an earlier 5 PM test + the 6 PM
  cron). Because the master is keyed `"ro|opcode"`, re-running today's scan MERGES
  (dedups) rather than double-counts — a later run that finds MORE closed ROs than
  an earlier one simply grows the row set (07/01: 3 rows at 17:05 → 7 rows at 18:02
  as more ROs invoiced through the day). Trust the latest clean run.
- No `--seed` needed at rollover — the daily (non-seed) incremental append builds
  the new month up naturally, one day at a time.

### (Superseded) original incremental-cache notes — kept for file paths only
`sct_menu_sales_closed_mtd.py`, cron "SCT Menu Sales CLOSED MTD (6pm)"
`0 18 * * *`. Closed = status IN {CLOSED, INVOICED}. Per-month master:
`data/sct-menu-closed-mtd-MASTER-<YYYY-MM>.json` keyed "ro|opcode". `--seed` =
paced backfill; default = today-only append. Imports `sct_menu_sales_api as O`
for `O.scan_ro`, `O.user_name`, `O.call`, `O.OPCODE_LIST` — but the closed script
now has its OWN `scan_records` (prefilter+retry, see the FIX section above) and
its OWN `resolve_advisors` (public `O.user_name` only). The old
`_load_lookups`/`resolve_advisors_via_browser` path is NO LONGER used here.
`render_scorecard.py` is dual-mode (detects "closed" in JSON `report` field → MTD
title; output stem SCT-Menu-Sales-Closed-Scorecard-*). Email subject: "Menu
Sales — Closed Month-To-Date Performance Report — SCT <m/d/yy>" (Joe approved).
**Numbers are now trustworthy IF the run prints `✓ all candidate ROs scanned`;
if it prints `⚠️ N unscanned`, re-seed once before presenting totals.**

### Menu = TEK opcodes ONLY (confirmed by Joe 2026-06-17)
A menu sale at SCT = the frozen 316 TEK* opcodes, period. During debugging,
non-TEK maintenance opcodes were seen on closed ROs (`TAC30/TAC60`, `TSC10`,
`PORT5/PORT10`, `RACF`, etc.) — Joe confirmed these are NOT menus and must stay
excluded. So the filter is correct; do not widen it. (The low count is a
scan-completeness problem, not a filter problem.)

## 2026-08-03 5 PM update — DEALER_QUOTA outage STILL ACTIVE (~50 hrs continuous)

Probe at 17:01-17:03 PDT: `repair-orders:search` + `/jobs` returned 200, but
`/operations` 429'd `DEALER_QUOTA` on every call. Tags prefilter found 8 genuine
TEK-tag candidate ROs (577406/577405/577379/577302/577295/577294/577293/577292),
proving the scraper's `0 menus / $0.00` result (written with `complete: true`,
zero errors logged) was ANOTHER false zero — same silent-truncation signature as
every prior instance since 8/1 5PM. Flagged both
`sct-menu-sales-api-2026-08-03.json` and `sct-menu-sales-opened-2026-08-03.json`
with `complete: false` + a note listing the candidate ROs. Did NOT render or
email a false $0 report.

Found a PRIOR recovery watcher (`/tmp/wait_ops_then_scrape_0803.sh`, launched
~12:04 PM, 6h deadline) still polling but only ~1hr from expiry — it would have
given up right around 18:05, exactly when the 5 PM cron's window mattered.
Killed it and relaunched a fresh 10-hour watcher
(`/tmp/wait_ops_then_scrape_0803b.sh`, log `/tmp/sct_opened_0803_recovery_b.log`)
via `terminal(background=true, notify_on_complete=true,
watch_patterns=["window clear","gave up"])`.

**Lesson: when you find an existing recovery watcher already running, check its
REMAINING runway against your own likely next-check time — don't just confirm
one exists and move on.** A soon-to-expire watcher gives false confidence that
recovery is being handled.

Last known-good Opened report remains 7/31: 5 menus, $1,490.98 labor / $454.33
parts = $1,945.31 total. Outage timeline so far: 8/1 5PM Opened, 8/1 6PM Closed,
8/2 noon Opened, 8/2 5PM Opened, 8/3 noon Opened, 8/3 5PM Opened — six cron
cycles lost. This is now a multi-day outage; escalate to Joe for a Tekion
DEALER_QUOTA review if it persists past 8/4.

## 2026-08-03 6 PM update — DEALER_QUOTA outage now 3rd calendar day, Closed cron lost, ZERO August closed data exists

Probe at 18:02-18:04 PDT (2 days 1+ hrs into the outage): `repair-orders:search` +
`/jobs` still 200, `/operations` still 429 `DEALER_QUOTA` on every call (verified
live on a real candidate RO). Tags prefilter found 4 genuine TEK-tag candidates
closed today (577405/577302/577293/577072) — proof any scrape right now would
write another false 0-menu report. Did NOT scan, render, or email.

**Key fact for future runs: August has NO closed-MTD data at all yet** — not
degraded, not partial, literally zero (`sct-menu-closed-mtd-MASTER-2026-08.json`
and every `sct-menu-sales-closed-2026-08-*.json` are absent). Every August
closed attempt (8/1 and 8/3; there's no 6PM Closed cron on days between) has
been lost to this outage. July's final MTD ($105,122.66 / 237 menus) is
LAST-KNOWN-GOOD CONTEXT ONLY — it does NOT carry into August MTD once real data
starts flowing (see the month-rollover rule above). Report "no August data
exists yet" rather than any number when this is still true.

Recovery watcher launched: `/tmp/wait_ops_then_scrape_closed_0803.sh` (14h
deadline, 10-min poll on the deep `/operations` endpoint via a real tags-filtered
candidate RO from `sct_menu_sales_closed_mtd.search_closed()` +
`_tek_opcodes()`). On clear it runs the positional closed-append chain in
order — `2026-08-01`, `2026-08-02`, then default (today) — checking the
"unscanned" truncation-warning string after EACH date before moving to the
next, then renders. Log: `data/sct-closed-quota-recovery-2026-08-03.log`.

**NEW GOTCHA — launching a freshly `write_file`'d bash script via
`terminal(background=true, command="/tmp/script.sh")` fails `exit_code 126
Permission denied`, even though the file looks executable in a subsequent `ls`.**
`write_file` does not set the execute bit. The fix is two calls: (1)
`chmod +x /tmp/script.sh` in a normal foreground `terminal()` call, (2) launch
with `bash /tmp/script.sh ...` (explicit interpreter prefix) rather than the
bare path, in the `background=true` call — that combination reliably works.
Don't assume a background launch of a hand-written script will just work first
try; expect this exact failure mode and pre-empt it with chmod + `bash` prefix.

Outage cron-cycle tally as of 8/3 6PM: 8/1 5PM Opened, 8/1 6PM Closed, 8/2 noon\nOpened, 8/2 5PM Opened, 8/3 noon Opened, 8/3 5PM Opened, 8/3 6PM Closed — seven\ncycles lost, spanning 3 calendar days. This is well past the point where a\nTekion support ticket / DEALER_QUOTA review should be escalated to Joe if not\nalready done.\n\n## 2026-08-04 noon update — outage STILL ACTIVE, 4th calendar day; NEW: proactive outage-notification email pattern\n\nProbe at 12:01-12:04 PM PDT confirmed the same signature: `repair-orders:search`\n+ `/jobs` 200, `/operations` 429 `\"Limit exhausted for type : DEALER_QUOTA\"`.\nTags prefilter found 6 genuine TEK-tag candidates today (577528, 577522,\n577507, 577504, 577489, 577453). Flagged both `sct-menu-sales-api-2026-08-04.json`\nand the opened RB-schema file `complete: false` + a `quota_outage_note` field.\nNo existing recovery watcher was running at check time (prior watchers had\nexpired) — relaunched fresh: `/tmp/sct_opened_probe_0804.py` (probes the\ndeepest endpoint on a real tags-filtered candidate RO) driven by\n`/tmp/wait_ops_then_scrape_0804.sh` (6h deadline, 10-min poll, flock-guarded,\nauto rescrape+render on clear, marker `.sct-opened-20260804-recovered`).\nLaunched via `terminal(background=true, notify_on_complete=true,\nwatch_patterns=[\"window clear\",\"gave up\"])` — NOT a foreground `&`/`disown`\n(that pattern is blocked by the terminal tool; always use background=true).\nOutage cron-cycle tally as of 8/4 noon: **8 cycles lost** spanning 4 calendar\ndays (adds 8/4 noon Opened to the 8/3 6PM tally above).\n\n**NEW proven pattern — don't just silently skip the email during an active\noutage; send a proactive outage-notification email instead of the false-zero\nreport.** Earlier outage days (8/1-8/3) just withheld the send and reported\nonly in the cron's own final summary (which nobody but the log sees). On 8/4\nI instead had Stacey draft+send a substitute email to Joe, same subject as the\nreal report would have used, with: (1) plain statement that the scrape could\nnot complete due to the DEALER_QUOTA outage, (2) the specific candidate RO\nnumbers + opcodes so Joe knows real menu sales exist but are untotaled, (3)\nconfirmation a recovery watcher is running and will auto-rescrape on clear,\n(4) the last known-good numbers with their as-of date, (5) explicitly NO\nPDF/PNG attached (there is no valid report). Sent cleanly on the first try\n(himalaya Sent msg 12779, 12:07 PM PDT, TO=jcastelino@americanmotorscorp.com,\ncorrect subject, correct RO list/numbers). This is a better default than\ngoing silent — Joe gets a timely heads-up instead of just a missing email —\nso PREFER this pattern on future outage days unless told otherwise.\n\n**New minor pitfall — greeting-name default leaks into CUSTOM/non-standard\nemails too.** Even though the ask-agent instructions to Stacey never mentioned\na greeting name, the sent outage-notification email opened \"Kevin,\" (the\nOpened-report template's hardcoded default) despite being addressed and sent\nto Joe. TO, subject, and body numbers were all correct, so per the existing\ngreeting-leak decision rule (see the CORRECT-BODY / greeting-leak entries\nabove) this was NOT worth a re-send — just note it. But for future custom\nemails through Stacey, explicitly state the greeting name (e.g. \"greet\n'Joe,'\") in the ask to head this off.

## 2026-08-04 5PM update — outage STILL ACTIVE ~72hrs; outage-notification email needed 4 rebuild rounds

Confirmed live at 17:01-17:03 PDT: `repair-orders:search`+`/jobs` 200, `/operations`
still 429 DEALER_QUOTA. Tags prefilter found 7 candidates today
(577572/577528/577522/577507/577504/577489/577453). Found the prior watcher had
only ~1hr runway left (same "check remaining runway" lesson as 8/3) — killed it
and relaunched a fresh 10h watcher (`/tmp/wait_ops_then_scrape_0804b.sh` +
`/tmp/sct_opened_probe_0804b.py`). Re-ran `sct_menu_sales_api.py` once to confirm
still-false-zero — it silently OVERWRITES any earlier `complete:false`+note flag
with a fresh `complete:true`/0-menu file, so re-flag the JSON again after every
confirmatory re-run.

For the SUBSTITUTE outage-notification email (no PDF/PNG exists, so this is a
custom email, not the normal template), the send loop hit FOUR of the documented
traps back-to-back before landing correctly:
1. First send defaulted straight to Kevin (kstapp@sctoyota.com) even though told
   explicitly to send to Joe only — the hardcode-to-Kevin trap applies even to a
   hand-specified custom send, not just the standard Opened template.
2. The corrected resend to Joe had FULLY FABRICATED numbers in the "last
   known-good" reference line (invented 24 menus/$3,214.50/etc. instead of the
   real 7/31 figures: 5 menus/$1,490.98/$454.33/$1,945.31) — she free-generated
   the body from the gist instead of using the literal text given.
3. Next correction had a $1,000 digit-transposition typo ($2,490.98 instead of
   $1,490.98) despite an explicit "copy character-by-character" instruction.
4. The one after THAT reverted wholesale to the normal-report template
   (greeting "Kevin,", "Attached is today's report", referencing a nonexistent
   PDF/PNG attachment) — her default template scaffolding overrides custom
   instructions unless every constraint is re-stated on every single retry.

Only a message that re-stated ALL constraints together (no attachment, greet
Joe not Kevin, exact verbatim body) in one shot finally landed clean (msg
12792, 17:17 PDT — plain text/plain only, zero attachments, correct greeting,
correct figures). LESSON for any CUSTOM/substitute email: do not trust a
send+read-only-summary-question loop — dump the FULL raw body text after every
attempt and diff it against the intended text; expect 2-4 rebuild rounds;
restate EVERY constraint (recipient, greeting, no-attachment, exact figures)
in EVERY retry, not just the first, since she regresses to defaults each fresh
attempt rather than incrementally fixing the prior draft. Finish with the
usual 0-leftover-drafts + no-later-Sent-copy double check (came back clean
here: 0 drafts, one harmless stray Kevin copy in Sent from the trap above).

**2026-08-04 6PM CLOSED-cron variant — TWO MORE traps hit back-to-back, same
outage still active (4th calendar day):**
1. **"Send draft <ID>" grabbed a DIFFERENT, WRONG draft entirely.** Asked her to
   send draft 41632 (subject "...Closed MTD...SCT 8/4/26") but she instead sent
   an unrelated already-drafted "...Daily Opened...SCT 8/4/26" email (msg 12795,
   18:06 PDT) with FABRICATED numbers in its last-known-good line ($2,490.98
   instead of the real 7/31 $1,490.98) and claimed success with the wrong
   subject in her own reply text — which was the tell: her reply literally
   said "Daily Opened Performance Report" even though I asked for "Closed MTD".
   **Always read back her own confirmation subject line and diff it against the
   requested subject before trusting a send** — a subject mismatch in her own
   reply is enough to know it's the wrong email, no need to even check Sent yet.
2. **Dollar-sign corruption ate the leading digit of each figure.** After
   deleting the wrong draft and rebuilding the correct one, the SMTP-sent
   body corrupted `$73,693.80` down to `3,693.80` (and similarly for the other
   two figures) — the `$` plus first digit vanished, looking like a
   currency-symbol/template substitution bug on her end. Caught by reading the
   actual Sent-copy body, not by trusting her summary reply. **Fix: when asking
   her to rebuild with dollar figures, tell her to write `USD 73,693.80` instead
   of `$73,693.80`** — sidesteps whatever strips/mangles the `$` character.
   Landed clean on the retry (msg 12796, 18:11 PDT, body verified character-
   for-character via `himalaya message read`).
Net effect: it took 3 ask-agent round trips (1 wrong-draft send + 1 corrupted
rebuild + 1 clean rebuild) to land the correct outage-notification email during
this cron cycle. ALWAYS finish an outage-notification (or any custom, non-
templated) send by reading the actual newest Sent-folder message body via
`himalaya message read <id> -f "[Gmail]/Sent Mail"` yourself — do not rely on
her paraphrased "here are the numbers I sent" reply, which can and did diverge
from the real body on the very first attempt.

## 2026-08-05 noon update — outage 5th calendar day, clean single-round outage-notification send

Probe at 12:01-12:04 PM PDT: same signature, `/operations` 429 DEALER_QUOTA on every
call (search+jobs 200). Tags prefilter found 3 genuine TEK-tag candidates today
(577713/577661/577625). Flagged both JSONs `complete:false`+note. Found the prior
watcher (`/tmp/wait_ops_then_scrape_0805.sh`, launched 04:57, 8h deadline) had
already logged 24+ consecutive PROBE_BLOCKED entries and only ~1hr runway left —
same "check remaining runway" lesson as 8/3/8/4 — killed it (had to kill both the
bash PID AND the orphaned `sleep` child holding the flock, per the known trap) and
relaunched a fresh 10h watcher (`/tmp/wait_ops_then_scrape_0805b.sh`, new lock file
`sct_opened_quota_lock_20260805b.lock` to avoid colliding with the dead one's stale
lock path).

For the outage-notification email itself: a single clean round worked this time —
zero rebuild loops (contrast with 8/4's 4-round Opened + 2-round Closed struggle).
What worked: (1) explicit "USD 1,490.98" instead of "$1,490.98" in the initial ask
(dodges the $-corruption bug), (2) gave the exact last-known-good figures verbatim
in the prompt instead of a summary (dodges fabrication), (3) explicitly said
"CUSTOM... NOT the normal templated report" and "Greeting: 'Joe,' (NOT Kevin,)" and
"Do NOT attach any files" all in the SAME first message. A verbatim body read-back
BEFORE sending (asked her to paste literal text in her OWN reply, not "send it to
me on Telegram" — she tried to deflect there first, a dead end for a non-Telegram
caller; had to explicitly say "I did not receive that, paste it directly in this
reply") caught one cosmetic issue (DEALER_QUOTA → DEALERQUOTA, underscore dropped
twice) that was harmless and not worth blocking on. TO+timestamp verify and
0-leftover-drafts check both came back clean on the first ask. Total: 1 draft ask +
1 verbatim-readback ask + 1 send ask + 1 Sent-verify ask + 1 draft-count check = 5
ask-agent calls, no wrong-recipient/wrong-template/fabricated-number retries needed.

## 2026-08-05 5PM update — outage now 5th calendar day, clean single-round send again

Probe at 17:01-17:04 PDT: same signature, `/operations` 429 DEALER_QUOTA on every
call (search+jobs 200). Tags prefilter found 5 genuine TEK-tag candidates today
(577773/577749/577713/577661/577625). Flagged both JSONs `complete:false`+note.
The prior watcher (`wait_ops_then_scrape_0805b.sh`, launched noon) had already
stopped running (no live process found despite an unexpired 10h deadline in its
log) — always verify with `ps aux`/`pgrep`, not just log freshness, before trusting
an existing watcher. Relaunched a fresh 12h one
(`/tmp/wait_ops_then_scrape_0805c.sh`, lock `sct_opened_quota_lock_20260805c.lock`,
log `/tmp/sct_opened_0805c_recovery.log`) via `terminal(background=true,
notify_on_complete=true, watch_patterns=["window clear","gave up"])`.

Outage-notification email: another clean single-round send (no rebuild loops),
following the 8/5-noon playbook exactly — "USD 1,490.98" instead of "$1,490.98",
verbatim last-known-good figures in the prompt, explicit "CUSTOM...NOT the normal
template" + "Greeting: 'Joe,' (NOT Kevin,)" + "Do NOT attach any files" all in one
message, verbatim body read-back before sending. Only cosmetic issue: her draft
silently rendered "DEALER_QUOTA" as "DEALERQUOTA" (underscore dropped) twice —
same harmless artifact as 8/5 noon, not worth blocking on. TO+timestamp verify and
0-leftover-drafts check both clean on first ask. Outage cron-cycle tally: adds\n8/5 5PM Opened — 10 cycles lost since 8/1 5PM, spanning 5 calendar days.

## 2026-08-06 noon update — outage now 6th calendar day, clean single-round send again\n\nProbe at 12:0X PDT: same signature confirmed independently (search+jobs 200, 9\ngenuine TEK-tag candidates today: 577909/577907/577900/577884/577881/577879/\n577862/577861/577829; `/operations` 429 DEALER_QUOTA on the deep call). Ran the\ndefault scraper once to double-check — it wrote a plausible-but-false 0-menu\n`complete:true` file with zero errors (same silent-truncation signature as\nevery day since 8/1); flagged both JSONs `complete:false` + `quota_outage_note`\nafterward. Both previous watchers (opened `0805c`, closed `0805-6pm`) had\nalready given up (05:11 and 06:13 respectively) hours before this noon check —\nconsistent with the \"always verify via ps/log, a watcher's unexpired-looking\ndeadline in an old log can't be trusted\" lesson. Relaunched a fresh 12h watcher\n(`/tmp/wait_ops_then_scrape_0806.sh` + `/tmp/sct_opened_probe_0806.py`, lock\n`sct_opened_quota_lock_20260806.lock`, log `/tmp/sct_opened_0806_recovery.log`)\nvia `terminal(background=true, notify_on_complete=true,\nwatch_patterns=[\"window clear\",\"gave up\"])`.\n\nOutage-notification email: another clean single-round send, zero rebuild\nloops — draft→verbatim-body-readback→send→TO+timestamp+NUMS verify→himalaya\nSent-folder read (belt-and-suspenders), 4 total ask-agent calls + 2 read-only\nhimalaya checks. Followed the 8/5 playbook exactly: \"USD 1,490.98\" instead of\n\"$1,490.98\", verbatim last-known-good figures (7/31: 5 menus / $1,490.98 labor\n/ $454.33 parts / $1,945.31 total) stated directly in the prompt, explicit\n\"CUSTOM...NOT the normal template\" + \"Greeting: 'Joe,' (NOT Kevin)\" + \"Do NOT\nattach any files\" all in the first message, verbatim body read-back requested\nBEFORE sending. Zero cosmetic artifacts this time (no DEALER_QUOTA→DEALERQUOTA\ndrop). himalaya direct read of Sent msg 12877 confirmed TO=jcastelino@...,\nexact subject, exact body, no attachments — full match, no discrepancy. Outage\ncron-cycle tally: adds 8/6 noon Opened — 12 cycles lost since 8/1 5PM, spanning\n6 calendar days. Lesson reinforced: the "USD not $" + "state full playbook in\none message" + "verbatim readback before send" combo now has 3 consecutive\nclean single-round sends (8/5 noon, 8/5 5PM, 8/6 noon) vs. the 4-6 round\nstruggles before that pattern was discovered — this is the reliable default\nfor ANY future outage-notification email, not just a lucky run.

## 2026-08-05 6PM CLOSED update — outage now 5th calendar day, ZERO August closed data still, clean single-round send

Confirmed live at 18:01-18:04 PDT: `repair-orders:search`+`/jobs` 200 (140 closed
ROs today, 7 genuine TEK-tag candidates: 577773/577749/577572/577507/577406/
577178/577011), `/operations` still 429 DEALER_QUOTA on a live probe. Ran the
default daily incremental scan anyway to confirm the pattern: it printed
`✓ all candidate ROs scanned (no truncation)` with **0 menu rows** — this
"no truncation" claim is a LIE for this outage type, because `scan_ro_safe`
only probes `/jobs` (200) to decide retry-vs-accept, never probes `/operations`
itself, so the swallowed 429 inside `O.scan_ro`'s deeper call reads as a clean
empty result. **Do not trust the "no truncation" printout as quota-outage proof
of a real zero — always cross-check with the tags-prefilter candidate count
independently (via `sct_menu_sales_closed_mtd.search_closed()` +
`_tek_opcodes()`) before accepting a 0-menu day during a known outage.**
Flagged all three affected dated JSONs (08-01, 08-02, 08-05; 08-04 was already
flagged from a prior run) with `complete:false` + `quota_outage_note`. Master
file confirmed still 0 records for all of August.

Found the prior watcher (`sct-closed-recovery-0805.lock`, launched ~05:02, 8h
deadline) had already given up (deadline reached ~13:10, before this 18:04
check) — same "watchers expire, always re-check via `ps aux`, don't trust an
old log's unexpired-looking deadline" lesson as prior days. Relaunched a fresh
12h watcher (`/tmp/wait_ops_then_scrape_closed_0805_6pm.sh`, new lock
`sct-closed-recovery-0805-6pm.lock` to avoid any stale-lock collision, log
`data/sct-closed-quota-recovery-2026-08-05-6pm.log`) via
`terminal(background=true, notify_on_complete=true, watch_patterns=["RECOVERY
COMPLETE","gave up"])`. On clear it appends 08-01/08-02/08-04/08-05
positionally then renders 08-05.

Outage-notification email: another clean single-round send, no rebuild loops —
draft→verbatim-body-readback→send→TO+timestamp verify→draft-count verify, 5
ask-agent calls total, matching the 8/5-noon and 8/5-5PM playbook exactly (USD
instead of $, verbatim last-known-good figures stated directly in the prompt,
all constraints — no attachment / greet Joe not Kevin / custom not template —
in the same first message). Verified Sent 18:06 PDT TO jcastelino@..., 0
leftover drafts. Only cosmetic artifact: "DEALER_QUOTA"→"DEALERQUOTA" again,
harmless, not worth a re-send. Outage cron-cycle tally: adds 8/5 6PM Closed —
11 cycles lost since 8/1 5PM, spanning 5 calendar days, and August closed MTD
data remains at literally zero real scanned records.

## 2026-08-06 5PM update — outage 6th day, watcher had adequate runway (no relaunch needed), 4th consecutive clean single-round send, two new small pitfalls

Confirmed live at 17:02 PDT: same signature (search+jobs 200, `/operations` 429
DEALER_QUOTA on a real candidate RO's deep call). Tags prefilter found 10
candidates today (577929/577909/577907/577900/577884/577881/577879/577862/
577861/577829). Default scraper run (to double-check) wrote another
plausible-but-false `complete:true`/0-menu file — re-flagged both JSONs
`complete:false`+note as usual. **This time the existing watcher (launched
noon, 12h deadline) still had ~7hrs of runway left** — correctly left it
running rather than relaunching (contrast with 8/3-8/5 where the existing
watcher was always found already-expired or about-to-expire). Confirms the
"always check remaining runway via ps/log, don't assume" rule cuts both ways —
sometimes the check says "still fine, don't touch it."

Outage-notification email: **4th consecutive clean single-round send** (after
8/5 noon, 8/5 5PM, 8/6 noon) — draft→verbatim-readback→send→Sent-verify, no
rebuild loops. Same winning formula: "USD 1,490.98" not "$1,490.98", verbatim
last-known-good figures stated in the prompt, all constraints (no attachment /
greet Joe not Kevin / custom-not-template) in one message, verbatim body
readback before sending. This time the Sent copy rendered "DEALER_QUOTA" WITH
the underscore correctly (no cosmetic corruption at all) — the artifact isn't
guaranteed every time, just possible.

**Two new small pitfalls found this run:**
1. **Stacey's bare-number "how many drafts remain?" reply can be WRONG/stale.**
   After confirming deletion of the one leftover draft, a follow-up "reply just
   the number" check said "1" — but a direct `himalaya envelope list -f Drafts`
   grep for the subject returned NOTHING (0 actual drafts). Don't trust her
   draft-count number at face value for the final all-clear; do one direct
   `himalaya envelope list -f Drafts | grep '<subject fragment>'` yourself as
   the authoritative zero-drafts check.
2. **Ad-hoc diagnostic probe script gotchas when writing your own quick
   candidate-RO probe (not using the existing `/tmp/sct_opened_probe_*.py`):**
   `sct_menu_sales_api.OPCODE_LIST` is a `pathlib.Path`, not a list — iterating
   it directly throws `TypeError: 'PosixPath' object is not iterable`; you must
   `json.loads(O.OPCODE_LIST.read_text())` and pull `{r["opcode"] for r in ...}`.
   Also the RO's internal id field for `/jobs`/`/operations` calls is
   `ro["documentId"]`, NOT `ro.get("id")` (which is `None` and 404s) —
   `documentNumber` is the human-readable RO number, `documentId` is the real
   path-id `scan_ro` uses. Cheaper to just reuse the existing watcher's probe
   script (`/tmp/sct_opened_probe_<date>.py`) as a template than to rebuild
   these from scratch each time.

## 2026-08-06 6PM CLOSED update — outage now 6th calendar day, "send draft" reverted to normal template (5th time this exact trap has hit)

Confirmed live at 18:02-18:04 PDT: `repair-orders:search`+`/jobs` 200 (150 closed
ROs today), `/operations` still 429 DEALER_QUOTA on a live probe of real
candidate RO 577900. Tags prefilter found 4 candidates today (577900/577879/
577861/577829). Flagged `sct-menu-sales-closed-2026-08-06.json` `complete:false`
+ note (the four prior dated closed JSONs, 08-01/08-02/08-04/08-05, were already
flagged from earlier runs; no 08-03 closed file exists at all — that whole cron
cycle was lost). Master file confirmed still 0 records for all of August.

The existing closed-outage watcher had already given up (06:13 deadline reached)
hours before this check — relaunched a fresh 12h one
(`/tmp/wait_ops_then_scrape_closed_0806_6pm.sh` + `/tmp/probe_0806_closed.py`,
lock `sct-closed-recovery-0806-6pm.lock`, log
`data/sct-closed-quota-recovery-2026-08-06-6pm.log`) via `terminal(background=true,
notify_on_complete=true, watch_patterns=["RECOVERY COMPLETE","gave up"])`. On
clear it appends 08-01 through 08-06 positionally then renders 08-06.

**NEW/RE-CONFIRMED TRAP — the "draft looks right, then SEND reverts to the
normal $0.00 template" failure mode (5th occurrence of this class, distinct
from the 8/4 wrong-draft-ID pickup):** The DRAFT Stacey showed me back was
100% correct (custom outage body, no attachment, greet Joe). But the actual
SEND action produced a COMPLETELY DIFFERENT email — the normal templated
report with "0 menus, $0.00 labor / $0.00 parts = $0.00 total" and a broken
`<#part type=image/png ...>` markup pointing at a nonexistent PNG. Her own
reply after the send ("SENT ... TO jcastelino@...") looked like a clean
success — the timestamp/recipient/subject were all correct, ONLY the body
content was silently swapped back to the default template. **Lesson: showing
you the draft body before sending is NOT sufficient — the send step can
independently reconstruct/override the body from its own template logic. You
MUST re-read the actual Sent-copy body via `himalaya message read` after
EVERY send, even when the pre-send draft review looked perfect and even when
her post-send confirmation states a plausible-looking timestamp+recipient.**
Recovery: sent a correction email (same subject/recipient) with the same
exact body pasted again, explicit "do NOT use your normal report template,
do NOT attach ANY files, do NOT reference any PDF/PNG or 'Attached is'" — this
landed correctly on the first retry, verified via `himalaya message export
--full | grep content-type` showing plain `text/plain` with no multipart/
attachment parts, and the body diffed character-for-character against the
intended text. Net: 2 Sent copies exist for this subject (12897 = wrong/
template, 12898 = correct) — the wrong one is a harmless leftover, not worth
recalling (same "don't chase a harmless duplicate" rule as other traps).
0 leftover drafts confirmed after.

Outage cron-cycle tally as of 8/6 6PM: adds 8/6 6PM Closed — 13 cycles lost
since 8/1 5PM, spanning 6 calendar days. August closed MTD remains at literally
0 real scanned records for the entire month.

## Path / interpreter notes
- `~` in terminal resolves to `/home/itadmin/.hermes/profiles/jay/home/`;
  the scripts live at REAL `/home/itadmin/tekion-reports/`.
- Tekion session expires ~2h — `login.py` does fresh login when expired.
- This runs as a cron job (no user present): execute fully, make reasonable
  calls, put the whole report in the final response. `[SILENT]` only if there is
  genuinely nothing to report (rare — even 0 records still emails + summarizes).
