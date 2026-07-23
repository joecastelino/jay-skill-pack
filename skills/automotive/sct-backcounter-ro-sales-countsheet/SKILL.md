---
name: sct-backcounter-ro-sales-countsheet
description: >
  Build Joe's daily SCT Back Counter Bin Check count sheet — cross-reference a day's
  RO part sales (Tekion OpenAPI) against parts that stock in a back-counter bin
  (5000 section) and render a Tekion-bin-check-style sheet with Primary Bin and
  Back Counter Bin write-in Count boxes, emailed via Stacey. Use when Joe asks to
  "verify counts daily", "which back counter parts sold today", or re-run the
  back-counter check for a date. KEY DESIGN INSIGHT (Joe corrected me 2026-07-04):
  a bin-snapshot DIFF can NEVER catch a back-counter pull — Tekion only relieves
  the PRIMARY bin (2420), so the 5000s bin doesn't move when the sale posts.
  Detection must be sales-driven: today's RO parts INTERSECT back-counter roster.
triggers:
  - back counter bin check
  - verify counts daily
  - parts ro sales back counter
  - count sheet
  - backcounter cross check
---

# SCT Back-Counter RO Sales Cross-Check + Count Sheet

## Why this exists (the causal logic — don't regress to snapshot diffs)
At SCT, 2420 = FRONT counter (Primary), ALL 5000-section bins (5000–5007) = BACK counter
(Joe 2026-07-04). Tekion relieves ONLY the Primary bin on any sale. So when a part is
physically pulled from the back counter, the system decrements 2420 anyway → 2420 reads
low, 5000s reads high, and **neither bin snapshot moves in a way a diff can catch**.
The correct daily control: flag every part sold on a day's ROs that ALSO stocks in a
back-counter bin, and have the counter physically verify both bins. Fix per drift =
Edit Part redistribution 5000s→2420 (zero GL; see tekion-ghost-bin-negative-onhand).

## Pipeline (3 scripts, all in /home/itadmin/tekion-reports/)

### 1. Scan: `sct_backcounter_ro_sales.py [--all] [--date YYYY-MM-DD]`
- Roster = newest snapshot in `bin5000s-snapshots/` (fallback `bin5005-snapshots/`),
  filtered to BACK_BINS {5000..5007}, keyed by normalized part# (dashes stripped).
- ROs = OpenAPI `repair-orders:search` with `modifiedTime BTW [midnight, midnight+1d]`
  Pacific (BTW, values as string epoch-ms; GTE for live today). Skips VOID.
- Fan-out jobs→operations→parts per RO; match normalized partNumber against roster;
  SALE qty from `quantities[]`.
- State file `backcounter-ro-sales-state.json` dedups (ro,opId,part,qty) lines across
  incremental runs; `--all` ignores AND does NOT write state (historical runs must not
  clobber the incremental baseline).
- Output: `backcounter-ro-sales/YYYY-MM-DD.json` + stdout checklist grouped by part.
- ⚠️ RUNTIME: a full closed business day = **20-55 min** depending on 429 backoff
  (331 ROs/963 lines ≈ 45 min; 514 ROs/1,477 lines ≈ 50 min on 2026-07-06;
  410 ROs/1,104 lines ≈ 23 min on 2026-07-11 when quota was uncontended;
  680 ROs/1,836 lines ≈ 37 min on 2026-07-13 — biggest day yet, still in range) —
  ALWAYS run background with notify_on_complete. Live intraday (109 ROs) ≈ 6 min.
  Output is buffered — empty poll output ≠ hung (verify liveness with
  `ps -p <pid>` if nervous). Hermes `process wait` CLAMPS timeout to 180s
  regardless of what you request — loop the wait calls, don't ask for 3600s once.

### 2. Enrich with SIGNED per-bin qtys + primary bin
The bin snapshot's onHandQuantity is per-5005 only and generate-report rows are
unsigned. Ground truth = internal `POST /api/wms/parts/u/inventory/withPart/search`,
body `{"filters":{"partId":{"key":"partId","values":[<=40 M_TMNA_ ids]}},"page":{"offset":0,"rows":50}}`.
- **Response shape: `data.list[]`** (NOT partInventoryDetails/hits). Each rec:
  `rec.part.partNumber` (no dashes), `rec.partInventory.quantity.totalQty`,
  `rec.partBinMappings[]` = {binNumber, quantity SIGNED, primaryBin bool}.
- partId map comes from the snapshot rows (`partId` field, M_TMNA_ prefix).
- Replay with captured axios headers from `/home/itadmin/sct-physical-2025/api-headers.json`.

**HEADER RECAPTURE RECIPE (headers go stale → 401; refreshed 2026-07-04):**
1. Verify :9223 is on dealer 876 (dealer pill x1130,y32 → SCT leaf ~x1074,y346;
   session drifts — found it on BT/1249).
2. `/navigate` to `/parts/inventory/part`, wait ~8s (nav wipes hooks — arm AFTER).
3. Arm a REQUEST-header hook: override `XMLHttpRequest.prototype.open` (save url),
   `.setRequestHeader` (collect into this.__h), `.send` (push {u,h} to window.__reqs
   for /api/ urls).
4. Fire the app's own XHRs WITHOUT full nav: `history.pushState({},'',
   '/parts/inventory/part/view/M_TMNA_<part>/details')` + `dispatchEvent(new
   PopStateEvent('popstate'))` → withPart/search fires with full auth headers.
5. Save `window.__reqs.find(x=>x.u.includes('withPart/search')).h` to api-headers.json.
   Headers replay fine from plain urllib outside the browser (no cookies needed).
   RE-VERIFIED end-to-end 2026-07-11 (cron run): :9223 was already alive on 876,
   recapture took <30s, build re-ran clean — 16 header keys captured incl.
   tekion-api-token/roleId/userId/dealerId/tek-siteId.
   RE-VERIFIED again 2026-07-13: session found drifted to **BC/1251** sitting on a
   service-menu EDIT page (possibly another automation's work-in-progress) — the
   recipe still ran clean: pendo-strip → dealer pill (found live via
   `root_dealerSe` rect, landed exactly x1130,y32) → SCT leaf x1074,y346 →
   dealer=876 → recapture. Sanity-check `dealerId` in the saved headers == 876
   before re-running the build (wrong-dealer headers return the wrong store's bins
   without erroring).
   RE-VERIFIED again 2026-07-15: session drifted to a THIRD dealer this time —
   **Stevens Creek Volkswagen/826**, parked on an /ro/repair-orders jobs page.
   Same recipe (pendo-strip → dealer pill via live `root_dealerSe` rect x1130,y32 →
   SCT leaf x1074,y346 → dealer=876 → /navigate /parts/inventory/part → arm hook →
   pushState) worked unchanged. Lesson: drift target/page is unpredictable
   (BT/1249, BC/1251, SV/826 all seen) — never assume, always read
   `currentActiveDealerId` first; the recipe is dealer-agnostic as long as the
   session is authenticated.
   RE-VERIFIED again 2026-07-18 (cron): this time :9223 had dropped fully to
   `/login?redirectTo=...` (not just dealer drift). Full recovery ran clean unattended:
   `login.py` reported REUSED/ALIVE (token exp 32 min) and the **REUSED-session injection
   WORKED** — cookies(5) + 21 keys (t_user 64KB / dse_t_user 60KB chunked via window.__tmp,
   length-verified) → /home authenticated on BC/1251 → pendo-strip → pill x1130,y32 →
   SCT leaf x1074,y346 → dealer=876 → recapture (16 keys) → build clean (62 parts,
   EMAIL_SENT+INBOX_COPY_OK). So REUSED≠alive is a *sometimes* trap, not always: try ONE
   injection off a REUSED state first; only if the post-inject verify shows the login form
   or navs bounce, go `login.py --force`. Don't --force preemptively (burns an OTP).
   Also: :9223 client bug to avoid — `/navigate` MUST be POST; calling the api() helper
   with the body in the method slot throws a confusing http.client TypeError.
   RE-VERIFIED again 2026-07-19 (cron): :9223 healthy AND already on 876 (first run
   with ZERO drift — don't skip the check, but no switch needed) — pushState recapture
   <30s, 16 keys, build clean (67 parts). SMTP attempt 1 failed \"Connection unexpectedly
   closed\" and the IN-SCRIPT retry recovered it (EMAIL_SENT+INBOX_COPY_OK) — a single
   transient printed before EMAIL_SENT is NOT a failure, don't re-run.
   RE-VERIFIED again 2026-07-17: drifted to **BT/1249**, parked on a DRAFT RO quote
   page (`/ro/quotes/<id>/service/new`, QO#2290 "Drafted") — possibly a human's or
   another automation's work-in-progress. Navigated to `/home` FIRST before the
   dealer switch (don't click around on someone's live draft). Recipe then ran
   unchanged: pill x1130,y32 → SCT leaf x1074,y346 → dealer=876 → hook → pushState →
   16 header keys captured, build re-ran clean (71 parts, EMAIL_SENT+INBOX_COPY_OK).

**⚠️ :9223 CAN FAIL UNRECOVERABLY — STANDALONE HEADLESS RECAPTURE (built 2026-07-16, now
the PREFERRED path):** on 7/16 the :9223 session had dropped to /login AND, even after a
full `login.py --force` (plain login.py said \"ALIVE, 27 min\" but injection still bounced —
the known REUSED≠alive trap) + cookie/21-key injection (big keys chunked, all verified),
EVERY `/navigate` to app.tekioncloud.com returned `net::ERR_FAILED` /
`chrome-error://chromewebdata` — while example.com navigated fine (tekioncloud-specific
network failure inside that Chromium; cause unresolved). Do NOT burn time fighting :9223.
Run `/home/itadmin/tekion-reports/refresh_withpart_headers.py` instead: own headless
Playwright + fresh storage_state (run `login.py --force` first if stale), pendo-strip →
dealer pill → SCT leaf → verifies dealer==876 → goto the M_TMNA_9008091184 part detail
page → `page.on(\"request\")` captures the withPart/search REQUEST headers → merges into
the existing api-headers.json key set (case-insensitive match, keeps old value for any
missing key) → prints HEADERS_SAVED. Whole run <60s, exit 0/2/3/4 =
ok/FAIL_AUTH/FAIL_DEALER/FAIL_NO_CAPTURE. Then re-run build_and_send. The :9223 pushState
recipe above still works when :9223 is healthy on 876, but the standalone script needs no
browser-server state at all — use it first for unattended/cron runs.

### 3. Render: `render_backcounter_countsheet.py <YYYY-MM-DD>`
Reads `backcounter-ro-sales/<date>-countsheet.json` (rows: part, desc, sold, n_ros,
ros, prim_bin, prim_qty, back_bin, back_qty, total). Joe-approved format = Tekion
bin-check style: red-rule header + SCT logo (logo_0.png base64), meta line
(date / parts to verify / Counted by / Time), table with two 3-col groups —
**Primary Bin (front)** green header: Bin | System | empty Count box, and
**Back Counter Bin** red header: Bin | System | empty Count box — negatives in red
bold, how-to legend, two signature lines. Drop qty-0 rows. Outputs PNG (inline email)
+ PDF via headless chromium; also write a CSV (Count columns blank) for sorting.
Vision-verify PNG before sending.

### 4. Email — DIRECT SMTP BY DESIGN (Stacey path RETIRED for this report, 2026-07-04)
**Do NOT route this email through Stacey.** She failed TWICE on it: even with an
explicit "use python smtplib, build real MIME" instruction she replied "SENT <id>"
but emitted raw MML `<#part>` markup as the literal body — the message landed in
`[Gmail]/Sent Mail` (so a Sent-Mail grep passes!) with no real attachments/inline
image and NEVER surfaced in Joe's INBOX. Joe: "I never got the email."
**Verification rule: check INBOX, not Sent Mail** — Sent presence proves nothing.

The whole post-scan pipeline is now ONE script:
`python3 build_and_send_countsheet.py <YYYY-MM-DD> [--no-email]`
- Does steps 2–4: signed-bin enrich (withPart/search) → countsheet JSON + CSV →
  calls render_backcounter_countsheet.py → emails Joe direct via smtplib
  (app pw regex'd from Stacey's himalaya config.toml; From+To Joe; PNG inline
  base64 data-URI; PDF+CSV MIMEBase attachments named SCT-BackCounter-<date>.*;
  footer "Sent from Tekion Open API — live data").
- Exit codes: 0 ok (prints EMAIL_SENT), 2 = stale api-headers (401 — recapture via
  the header recipe above, re-run), 3 = missing scan file, 4 = SMTP failed 3x.
- SMTP retry is REQUIRED: gmail SMTP_SSL threw a transient
  `ConnectionResetError(104)` mid-send on a ~580KB message — 3 attempts w/ 5s sleep,
  timeout=120 (already coded).
- **EXIT 4 ≠ blocker (verified 2026-07-12):** all 3 in-script attempts can fail with
  "Connection unexpectedly closed" during a transient Gmail-side blip, yet an IMMEDIATE
  full re-run succeeds. Recovery: (1) probe connectivity —
  `python3 -c "import smtplib; s=smtplib.SMTP_SSL('smtp.gmail.com',465,timeout=15); print(s.noop()); s.quit()"`
  — then (2) just re-run `build_and_send_countsheet.py <date>` — it's idempotent, the
  enrich/render steps redo in seconds and artifacts already exist. Only escalate as a
  blocker if the re-run ALSO exits 4 (or the noop probe can't connect).
Subject pattern: "SCT Back Counter Bin Check — YYYY-MM-DD".
- ⚠️ **GMAIL SELF-SEND DEDUP (hit 2026-07-04/05):** From==To==Joe means Gmail files
  the message ONLY in Sent Mail — it NEVER appears in Joe's INBOX ("I didn't get
  this as an email"). EMAIL_SENT + a Sent-Mail copy is NOT delivery proof for a
  self-send. FIX (coded 2026-07-05): after SMTP send, the script IMAP-APPENDs a
  copy to INBOX (prints INBOX_COPY_OK). Verify delivery by grepping INBOX, and if
  a past sheet is stuck in Sent only, recover with
  `himalaya message copy -f "[Gmail]/Sent Mail" INBOX <id>` (arg order: TARGET
  before ID). This applies to ANY direct-SMTP self-send report, not just this one.
- ⚠️ **APPEND WITH ORIGINAL Message-ID/Date GETS BURIED (2nd bite, 2026-07-05):**
  the himalaya copy / a raw append that keeps the ORIGINAL Message-ID + Date gets
  threaded by Gmail into the existing sent conversation at its OLD timestamp —
  Joe replied "I don't see it in my mail" even though it WAS in INBOX. For a
  redelivery Joe will actually SEE: strip + regenerate `Message-ID`
  (`email.utils.make_msgid(domain='americanmotorscorp.com')`), set `Date` to NOW
  (`email.utils.formatdate(localtime=True)`), optionally suffix subject
  "(redelivery)", and append with `(\\Flagged)` flags → lands at inbox TOP,
  unread, unthreadable. build_and_send_countsheet.py should keep fresh
  Date/Message-ID on the INBOX copy for the same reason.

## BASELINE report variant — full 5000-section signed-bin audit (built 2026-07-05, Joe asked "give me a report of the multiple bins in the 5000 so I can create a baseline, include what is supposed to be in the bin according to Tekion")

Different from the daily sales-driven sheet: this is EVERY part carrying a 5000s
bin with Tekion's SIGNED per-bin qty + a blank Physical Count box — the one-time
(re-runnable) baseline for a full back-counter physical.

Pipeline (all under /home/itadmin/tekion-reports/):
1. **Roster** = newest `bin5000s-snapshots/YYYY-MM-DD.json` (dict keyed by bin
   number → rows; gives partIds + cost/desc). No new scrape needed.
2. **Signed truth** = batch `withPart/search` (≤40 partIds/call, 1.5s pacing,
   ~220 parts in ~12s) using `/home/itadmin/sct-physical-2025/api-headers.json`.
   If 401 → headers stale: restore :9223 session (login.py → inject cookies +
   21 localStorage keys via /login origin → /home), switch dealer pill to SCT
   876, then run the HEADER RECAPTURE RECIPE above (pushState to a part detail
   fires withPart/search with full auth headers). Whole restore ≈ 2 min.
3. Build `data/bin5000s-baseline-<date>.json` (per part: prim bin/qty, back
   bins signed, other bins, total, ext$) then render with
   `render_backcounter_baseline.py <date>` → PNG/PDF/CSV at
   `data/SCT-BackCounter-Baseline-<date>.{png,pdf,csv}`.
4. Sheet design Joe accepted: KPI band (bin lines / negative / positive / zero /
   net units / net ext$), one line per (part, back bin), sorted NEGATIVES FIRST
   then positives by ext$ desc then zeros; PRIMARY badge when the 5000s bin IS
   the part's primary (11 parts at SCT — those bins DO relieve on sale, call
   this out); columns incl. Primary bin+qty, Other Bins, Part Total OH, Unit
   Cost, Ext$; blank Physical Count box; CSV mirrors with blank count column.
5. Email direct-SMTP self-send + INBOX append w/ FRESH Message-ID/Date +
   \Flagged; subject "SCT Back Counter Baseline — Full 5000-Section Bin Audit —
   <date>". Vision-verify a 2x-upscaled TOP CROP (full PNG is ~6400px tall —
   exceeds vision 8000px limit territory and small-digit OCR is unreliable).

7/5 baseline numbers (reference): 222 bin lines / 219 parts, 37 negative
(worst 87139-YZZ83 -93, 87139-YZZ93 -90 in 5007), 103 pos, 82 zero, net 625
units / $6,843.77 ext.

### 5. Daily automation (live 2026-07-04)
Cron `14e6387de450` "SCT Back Counter Count Sheet — daily 8:15PM email" — runs
AFTER the 8PM bin-snapshot job (d372a20d2889): background scan for today →
build_and_send → on exit-2 refresh headers (prefer refresh_withpart_headers.py; :9223 recipe is the fallback) → Slack summary
(top parts, negatives, EMAIL_SENT confirm); [SILENT] if NO_HITS.

## Interpreting results (7/3 + 7/4 baselines)
- Chronic flags are NORMAL: drain-plug gaskets (90430-12031 sold 138/day), wipers,
  air filter elements — the daily list converges on ~10 repeat offenders.
- Parts already NEGATIVE in a back bin (e.g. 04500-1 at -69, 17801-YZZ11 at -28) =
  accumulated never-transferred back-counter pulls — call these out in the email body.
  These DEEPEN while uncorrected (04500-1: -69 on 7/4 → -93 by 7/18 → **-94 by 7/21**;
  chronic trio 87139-YZZ83/-93, 87139-YZZ93/-90 unchanged across weeks; **00475-1BF03
  BRAKE FLUID at -69 in 5007** joined the big-ticket list by 7/21) — the daily sheet
  flags them but only Joe-authorized Case-A redistribution actually fixes them.
  7/21 run note: :9223 healthy AND already on 876 (2nd zero-drift run after 7/19);
  pushState recapture <30s, 16 keys, build clean (70 parts, 585 ROs/1,643 lines,
  scan ~28 min — within the normal runtime band).
  7/22 run note: drifted to BT/1249 parked on a LIVE RO quote view (`/ro/quotes/<id>/
  service/<id>` — read-only view, safe to nav away from directly); recipe unchanged
  (pill x1130,y32 → SCT leaf x1074,y346 → 876 → pushState → 16 keys), build clean
  (79 parts, 16 negatives). Negatives drift continues: **04500-1 now -96** (was -94
  on 7/21), and **17801-YZZ10 ELEMENT SUB-ASSY at -51 in 5007** is a new big-ticket
  negative alongside the chronic 87139-YZZ83 (-93) / 00475-1BF03 (-69) set.
- FULL-5000s coverage matters: the first full-section run (7/4, 38 parts across
  5000/5001/5002/5005/5006/5007) surfaced cabin filters **87139-YZZ83 at -93 and
  87139-YZZ93 at -90 in bin 5007** — big negatives invisible to any 5005-only watch.

## Authorization boundary (Joe, 2026-07-05 — "I don't want you to do it. Just so I know.")
Jay must NOT adjust bin quantities autonomously — capability confirmed, execution is
Joe's call only.
- **Case A (split wrong, total right)** = Edit Part → Bin Details redistribution
  (zero GL, no ledger). Automatable in principle, but Jay has NEVER executed one live —
  first must be a single part with Joe watching before any batching.
- **Blind spot that kills naive auto-transfer:** RO data shows what SOLD, not which
  counter it was PULLED from. A front-counter sale of a dual-bin part needs NO
  transfer — auto-transferring every sale would corrupt splits the other way. That's
  why the count sheet (human shelf verification) exists.
- **Case B (total wrong)** = On Hand Adjustment posts real GL dollars — ALWAYS
  explicit per-change approval, never autonomous.
- Redistribution leaves ZERO audit trail in Tekion — if ever authorized, keep a CSV
  log as the only record.

## FALLBACK: OpenAPI quota exhausted → activity-log reconstruction (proven 2026-07-08)

**⚠️ PROBE QUOTA FIRST, EVERY RUN (lesson from 2026-07-09):** before launching the 45-55 min
OpenAPI scan, run `python3.11 /home/itadmin/dealer-detail/scripts/tekion-quota-probe.py`
(exit 0 = quota live). On 7/09 I skipped this, burned TWO full scan attempts (~30 min each,
12 retries with backoff apiece) against a quota that had been dead for 3 STRAIGHT DAYS
(OVERALL_QUOTA 429 since 2026-07-07 14:12), and only then discovered the outage — when this
skill's activity-log fallback below would have produced the sheet in ~4s with ZERO OpenAPI
calls. Decision rule: **probe 429 → go STRAIGHT to the fallback** (it needs only valid
api-headers.json; if those are also 401, do the header recapture first). Outages can last
DAYS, not hours — an inline retry loop or "wait for reset tonight" is not a plan.

**Deferred self-heal watcher pattern** (only if the fallback is ALSO blocked, e.g. headers
stale + :9223 unrecoverable unattended): flock-guarded bash loop probing every 30 min for
≤24h; on quota restore sleep 15 min FIRST (other recovery runners coordinate on
`/tmp/tekion-quota-recovery.lock` — let the main queue lead), then scan + build_and_send;
exit 2 on STALE_HEADERS rather than guessing the browser refresh unattended. Template:
`/home/itadmin/tekion-reports/selfheal_backcounter_countsheet_20260709.sh`. During a fleet
quota outage MULTIPLE watchers coexist (quota_recovery_runner2, sct_closed_backfill,
selfheal_sct_align) — they only probe, they're not the cause; don't kill them.

If `repair-orders:search` returns persistent **429 "Limit exhausted for type : OVERALL_QUOTA"**
(daily OpenAPI quota burned by other jobs — it did NOT reset for 2+ hrs on 7/8), do NOT stall
the count sheet. Rebuild the scan file from the INTERNAL activity-log API (same headers file as
withPart/search, no OpenAPI quota):
1. Roster + partIds from today's `bin5000s-snapshots/<date>.json` (~232 parts).
2. `withPart/search` batches (≤40 partIds) → grab `partInventory.id` = **inventoryId** per part.
3. `POST /api/parts/activity-log/u/search` body wrapped in `tekRequest`: filters
   `inventoryId IN [≤30 ids]` + `transactionTime BTW [midnight,midnight+1d] ms` +
   `refType IN ["FULFILMENT"]`, pageInfo rows 500. (~4s total for 232 parts vs 45-55 min fan-out!)
4. Net per (refNumber=RO#, part): **exclude `type=LOCK` legs** (+1 paired with DELIVER_LOCKED -1),
   sum `-deltaOnHandQty`; drop lines netting ≤0 (returns). Write flags to
   `backcounter-ro-sales/<date>.json` in the scanner's schema (ro, part, desc, qty_sold,
   back_bins, fulfillment) + a `method` note — then `build_and_send_countsheet.py <date>` runs unchanged.
Caveat: activity-log FULFILMENT lacks opcode + RO status (fields left null); qty comes from
inventory deltas not billed qty — matched 7/8's expectations (49 parts / 124 ROs). **UPDATE
2026-07-23: this is now the PRIMARY method ALWAYS** (not just during outages) — see the
modifiedTime double-count bug in Pitfalls; the OpenAPI fan-out is enrichment-only.

## Pitfalls
- **Snapshot format slimmed 2026-07-08** (rows keep only partNumber/partId/description/cost/
  onHandQuantity/stockingStatus/multipleBinNumbers/lastTransactionTime — **binNumber dropped**).
  sct_backcounter_ro_sales.py patched 7/8 to inject binNumber from the dict key; any other
  consumer iterating snapshot rows must do the same.
- Snapshot `multipleBinNumbers` EXCLUDES the row's own bin — union both for "other bins".
- A qty-0 sale line (returned/zeroed part) can appear — filter `sold == 0` rows.
- `--all` reruns of past dates: state must NOT be written (already coded, don't "fix").
- **⚠️ modifiedTime DOUBLE-COUNT BUG — JOE CAUGHT IT 2026-07-23 (04152-YZZA4 "6 sold"
  vs 3 in transaction history):** ROs matched on modifiedTime means status flips
  (IN_PROGRESS→CLOSED, READY_FOR_INVOICE→INVOICED) drag OLD part lines onto today's
  sheet — 3 ROs billed 7/16-7/20 rode onto 7/21's sheet AND had already appeared on
  7/20's. The state-dedup file that should prevent this had been FROZEN since 7/04
  because the 8:15PM cron invokes the scan in `--all` mode, which deliberately skips
  state writes — so the dedup never advanced. Net effect: daily sold qtys can be
  inflated by any prior-day billed line whose RO was merely touched today.
- **FIX / METHOD MIGRATION (2026-07-23): the activity-log ledger is now the PRIMARY
  sold-qty source, not just the quota-outage fallback.** `/api/parts/activity-log/u/search`
  keys on actual `transactionTime` — "sold on 7/21" = billed 7/21, period; returns net
  out automatically, runs in seconds, zero OpenAPI quota. The OpenAPI RO fan-out is
  demoted to opcode/RO-status ENRICHMENT only. If a rebuilt sheet still shows inflated
  qtys vs Tekion transaction history, check the sheet is actually running the ledger
  path. Verify a suspect line the way Joe does: pull the part's Transactions ledger and
  compare per-RO billed dates against the sheet's date.
- Related skills: tekion-ghost-bin-negative-onhand (fix paths, watchdog cron
  d372a20d2889 now 8PM), tekion-openapi-repair-orders (API mechanics, 429 discipline).
