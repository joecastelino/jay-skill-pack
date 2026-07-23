---
name: tol-menu-sales-reports
description: Run the Toyota of Lancaster (TOL/TL, dealer 1092) Menu Sales scorecards — Daily Opened and Closed Month-To-Date — from the LIVE Tekion OpenAPI, and have Stacey DRAFT them to Sean Preston (spreston@tol-av.com). The Toyota-store sibling of the SCT/Kevin (sct-menu-sales-api-scorecard) and BC/Ruben (bc-menu-sales-reports) pipelines. Use for any "TOL/TL/Toyota of Lancaster menu report" or "Sean Preston report" request.
triggers:
  - toyota of lancaster menu sales
  - TOL menu report
  - TL menu sales
  - Sean Preston report
  - lancaster opened closed menu
---

# Toyota of Lancaster (TOL/TL) Menu Sales Reports

The TL (Toyota of Lancaster) menu-sales pipeline. Sibling of `sct-menu-sales-api-scorecard`
(SCT/Kevin) and `bc-menu-sales-reports` (BC/Ruben). **Load `agent-to-agent-bridge` too**
(Stacey drafts the email). All scripts live in `/home/itadmin/tekion-reports/`.

## Store facts (memorize)
- **Dealer ID = 1092**, siteId `-1_1092`, cfg key `tl` = `americanmotorscorporation_1092_0`.
- **Recipient = Sean Preston, spreston@tol-av.com.** GREETING = **"Sean,"** — NOT "Preston".
  (The `s` in `spreston` is his first initial; do not guess the first name from the address.)
- Store hours: open till 8 PM.
- **Menu opcode set = `data/tl-menu-opcodes.json` = 212 SERVICE_MENU opcodes**
  (53 mileage intervals 5K–200K × 4 tiers BNM/BSM/PSM/VNM). This is the BC-standard
  definition (`opcodeType==SERVICE_MENU && status==ACTIVE`), NOT SCT's looser 316
  "Maintenance Service" list. See `DERIVE A STORE'S MENU OPCODE SET` in memory for how it
  was built (drive the app's own opcode search via :9223 + XHR hook, scroll-paginate).

## Files (the pipeline — already built, prefix is `tol_` not `tl_`)
- `tol_menu_sales_api.py` — **OPENED** report. Default run = today's ROs by creationTime.
  Writes `data/tol-menu-sales-opened-<date>.json`.
  **MUST point `OPCODE_LIST` at `data/tl-menu-opcodes.json`** (was wrongly set to SCT's
  `sct-tek-maintenance-opcodes.json` — fixed 2026-06-29).
- `tol_menu_sales_closed_mtd.py` — **CLOSED MTD**. Modes:
  - `--seed` = full-month backfill (paced, scans every closed RO in the month, prefilters
    to those carrying a TEK menu opcode, fans out only those). **Run this ONCE per month**
    to build the master, or any time the master looks under-populated.
  - default (no flag) = daily-append to MTD master + re-emit MTD JSON.
  - `--daily-only` = standalone daily closed (no MTD).
  Master file = `data/tol-menu-closed-mtd-MASTER-<YYYY-MM>.json`.
  Closed JSON = `data/tol-menu-sales-closed-<date>.json`.
- `render_menu_sales_paged_tol.py <date> [closed]` — renders Toyota-red (#EB0A1E) 2-page
  layout: page-1 advisor-ranking PNG, full multi-page PDF. Output stems:
  - opened: `TOL-Menu-Sales-Scorecard-<date>.{png,pdf}`
  - closed: `TOL-Menu-Sales-Closed-Scorecard-<date>-Paged.{png,pdf}`
  (uses its own headless Playwright — independent of the :9223 session.)

Python interpreter for all of these: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`.

## Run sequence

### Opened (daily)
```sh
cd /home/itadmin/tekion-reports
PY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11
$PY tol_menu_sales_api.py
$PY render_menu_sales_paged_tol.py $(date +%F)
```

### Closed MTD (daily, after seeding the month once)
```sh
$PY tol_menu_sales_closed_mtd.py            # default = daily append + re-emit MTD
$PY render_menu_sales_paged_tol.py $(date +%F) closed
```

### Seed the closed master (first run of a month, or if master is sparse)
```sh
# Back up first, then reseed clean:
cd /home/itadmin/tekion-reports/data
cp tol-menu-closed-mtd-MASTER-$(date +%Y-%m).json{,.bak} 2>/dev/null
rm -f tol-menu-closed-mtd-MASTER-$(date +%Y-%m).json
cd /home/itadmin/tekion-reports
$PY tol_menu_sales_closed_mtd.py --seed     # paced; run as background w/ notify_on_complete
```

## Verify before handing to Stacey
`vision_analyze` each PNG: confirm store = "Toyota of Lancaster", correct period, KPI
totals (menus/labor/parts/total) match between the KPI cards and the table totals,
advisor ranking is sensible, no rendering errors.

## Hand-off to Stacey (DRAFT only)
Use `~/bin/ask-agent stacey "..."`. One message with: recipient `spreston@tol-av.com`,
greeting **"Sean,"**, store "Toyota of Lancaster", the numbers, inline-PNG path, attach-PDF
path, and **"leave as DRAFTS — do not send."** Same Kevin/SCT layout: greeting / summary
with bold total / scorecard PNG inline / "Sent from Tekion Open API — live data" / Joe's
HTML signature. Subjects:
- `TOL Menu Sales — Opened (MM/DD/YYYY)`
- `TOL Menu Sales — Closed MTD (Month D–D, YYYY)`

### VERIFY Stacey's draft after hand-off (learned 2026-07-04, 8PM run)
Stacey's drafts can silently come out wrong — always run a follow-up READ-ONLY ask
(\"list drafts with subject X, take no action, do NOT send\") and check:\n
1. **Inline PNG can be dropped.** Her first EOD attempt saved the draft with the PDF
   attached but NO inline image in the body. If missing, ask her to rebuild the draft
   with the PNG embedded inline (keep PDF attachment).
2. **Stale duplicate drafts.** The noon Opened run leaves a draft with the IDENTICAL
   subject. The 8PM EOD run must have Stacey DELETE the superseded noon draft so
   exactly ONE draft with that subject remains — otherwise Joe may send the stale one.
3. **False-negative on inline-image check.** Stacey's plain draft listing may report
   \"Inline image: No\" even when the image IS there — she embeds via a hosted Imgur
   `<img src=\"https://i.imgur.com/...\">` tag (not a cid: attachment), which her
   text-part scan misses. To truly verify, ask her to inspect the RAW HTML body and
   quote the `<img>` src. Presence of the img tag = good.
4. Also have her confirm Sent folder shows 0 matches for the subject.
5. **Sent-count FALSE POSITIVE #2 (7/14 EOD):** Stacey answered \"Sent: 1\" with today's
   exact subject, To spreston, internalDate = the DRAFT's save time (8:05 PM) — she was
   inspecting the DRAFT, not a sent mail. Resolve with ONE decisive read-only ask:
   `search 'in:sent subject:(TOL Menu Sales Opened)', list exact Subject + labelIds +
   internalDate for each`. Real sends carry labelIds ['SENT']; the draft won't appear.
   If no result matches today's exact subject, there is no leak.
5b. **Sent-count FALSE POSITIVE (7/12):** Gmail subject search is TOKEN-based, not
   exact-match — a Sent query for `TOL Menu Sales — Closed MTD (July 1-12, 2026)`
   returned \"1\" that was actually the OLD June 1-29 email sent 6/30. A nonzero Sent
   count is NOT proof of a leak: follow up with a read-only ask to fetch the match's
   EXACT subject + sent date and compare. Only an exact-subject, today-dated hit
   means the draft was sent.

### COMPETING SEND CRONs in Stacey's own profile (discovered 2026-07-05 noon)
The email-agent (Stacey) profile has its OWN cron jobs `TOL Menu Sales - 12:05 PM
(Opened Only)` and `TOL Menu Sales - 8:05 PM (Opened & Closed)` (file
`/home/itadmin/.hermes/profiles/email-agent/cron/jobs.json`) that generate the report
independently and **SEND directly to Sean via SMTP** (subject style: `Menu Sales — Daily
Opened Performance Report — TOL 7/5/26`, CC Joe). So a Sent-folder hit at ~12:06 PM with
that other subject is Stacey's cron, NOT a leak of Jay's draft. When verifying "0 in
Sent", match on the EXACT `TOL Menu Sales — Opened (MM/DD/YYYY)` subject. Joe should be
told about the duplication (Jay drafts + Stacey auto-sends = Sean can get two versions).

### Stacey draft-quality traps (2026-07-05 noon run)
1. She may save the draft with the WRONG subject (her own template `Menu Sales — Daily
   Opened Performance Report — TOL M/D/YY`) — verify and have her rename to the exact
   requested subject.
2. She may set the inline img src to a LOCAL path (`/tmp/...png`) that won't render for
   the recipient, or write `cid:scorecard` in the HTML but OMIT the image/png MIME part.
   Verify the raw MIME: need an `image/png` part with `Content-ID: <scorecard>` (or a
   hosted https img src). If missing, ask her to rebuild multipart/related with the CID
   part and re-verify.
3. Her read-only checks are flaky: she may reply "Drafts: 0" right after saving (search
   lag / wrong subject), or say "sent results to Telegram" instead of answering inline —
   instruct "print answers IN YOUR REPLY TEXT" and re-ask briefly on timeout (exit 124).
4. (7/11) Multi-part verification asks (4 questions: draft count + raw MIME + attachment
   + Sent count in ONE message) time out repeatedly (exit 124). SPLIT verification into
   tiny single-question asks: "one word yes/no, single Gmail API call, no other tools" —
   those return fast and reliably. Ask draft-exists first, then img src, then the
   png-MIME-part yes/no, then Sent count. Budget a `sleep 30-60` between retries.
5. (7/11) The cid trap RECURRED even though she REPORTED "PNG embedding: cid (embedded
   inline using cid:scorecard)" — the HTML had `cid:scorecard` but NO image/png MIME
   part. Never trust her save-confirmation on embedding; always run the explicit
   yes/no "does the raw MIME contain an image/png part with Content-ID scorecard"
   check. Effective fix instruction: "delete that draft and rebuild as
   multipart/related with an actual image/png part (Content-ID: <scorecard>,
   Content-Disposition: inline) base64-encoded from <png path>" — she rebuilt with
   Python's MIME builders and it verified clean (1 draft, PNG part yes, PDF yes,
   Sent 0).
6. (7/13) PREVENTION beats repair: put the full MIME spec in the ORIGINAL hand-off
   message — "MUST be embedded as multipart/related with an actual image/png MIME
   part (Content-ID: <scorecard>, Content-Disposition: inline, base64 from that
   file) referenced by <img src='cid:scorecard'>. Do NOT use a local file path as
   img src, and do not write cid:scorecard without the actual PNG MIME part." With
   that wording the 7/13 EOD draft came out clean FIRST TIME (raw-MIME yes, PDF
   yes, Sent 0) — no rebuild cycle needed. Also bundle the delete-superseded-noon-
   draft instruction into the same initial ask ("if an earlier draft with this
   exact subject exists, DELETE it so exactly ONE remains") — she handles save +
   dedupe in one shot and reports both. Verification asks may still 124 twice
   before answering — keep the sleep 30-60 retry pattern; terse single-question
   asks eventually return.
6b. (7/15 EOD) The 7/13 prevention wording is NOT sufficient by itself: with the full
   MIME spec + dedupe instruction in the original ask, Stacey still saved TWO
   malformed drafts (text/plain only — no HTML, no PNG, no PDF) with the correct
   subject, while replying \"Draft saved: yes / duplicate: n/a (none found)\". Her
   save-confirmation and her dedupe claim are both untrustworthy. ALWAYS run the
   part-listing verification (item 7) — it caught both problems in one ask (count=2,
   parts=text/plain only). Fix that worked in one shot: \"DELETE BOTH drafts (IDs X,
   Y), build exactly ONE new draft with email.mime as multipart/related ...\" —
   rebuild verified clean (1 draft; text/html + image/png cid=scorecard +
   application/pdf). Note: her rebuilt drafts may include an extra image/jpeg part
   (Content-ID <amglogos>, amg-dealer-logos.jpg) — that's Joe's signature logo,
   normal, don't flag it. RECURRED 7/17 EOD: full MIME spec in the initial ask,
   she replied "inline PNG scorecard via a proper CID reference, per your exact
   specifications" — yet part-listing showed text/plain body only + PNG/PDF as
   plain attachments (Content-ID None, /tmp/ filenames). Her confident wording
   proves nothing; the delete-and-rebuild-with-email.mime instruction fixed it
   in one shot again. Part-listing verification is MANDATORY every run.
   Verification ask may 124 once — sleep 40 and re-ask terser ("single Gmail
   API call, no other tools"); that returned fast.
7. (7/14 EOD) FALSE-NEGATIVE on the terse yes/no MIME probe: the single-question
   "one word yes/no — does the raw MIME contain an image/png part with Content-ID
   scorecard?" ask answered "no" TWICE, including once on a rebuild that was
   provably GOOD. The reliable verifier is the PART-LISTING ask instead:
   "list every MIME part of the draft (mimeType, Content-ID, filename), one line
   per part, terse". A good draft lists: multipart/related / text/html /
   image/png Content-ID=<scorecard> / application-pdf-or-octet-stream with the
   .pdf filename. Trust the part listing over the yes/no probe — a bare "no" may
   trigger a needless delete-and-rebuild cycle. (Also: PDF attachments often show
   mimeType=application/octet-stream with the .pdf filename — that's fine, don't
   flag it.)
7b. (7/18 EOD) Dedupe claim FALSE again even when the MIME comes out clean: with the
   full prevention wording, the draft structure was perfect FIRST TIME (multipart/
   related, png cid, pdf — no rebuild needed), but she replied \"duplicate: none
   found\" while the noon draft with the identical subject still existed (part-
   listing ask returned count=2). The part-listing verification's COUNT is what
   catches this — treat count>1 as mandatory-fix. One-shot fix that worked: \"KEEP
   the latest draft (id X, the good one), DELETE the other older draft with that
   subject\" → she reported deleted id + remaining count 1. So: MIME quality and
   dedupe are INDEPENDENT failure modes; a clean structure does not mean dedupe
   happened.
8. (7/13 EOD) NEW trap: she can nail the inline-PNG cid embedding but DROP the
   PDF attachment entirely, even with both files spelled out in the initial ask.
   Always include "does the draft have an application/pdf attachment?" as one of
   the split yes/no verification asks. Fix instruction that worked: "DELETE that
   draft and rebuild ... PLUS an application/pdf attachment from <pdf path>, use
   Python's email.mime builders" — rebuilt clean in one shot (1 draft, png part
   yes, pdf yes, Sent 0).

## Pitfalls (hard-won 2026-06-29)
1. **OPCODE_LIST trap.** The old `tol_menu_sales_api.py` shipped pointing at SCT's 316-list.
   All 212 TL menus ARE a subset of SCT's 316 (so it never MISSED a menu) but the looser
   list can over-count à-la-carte INDIVIDUAL_SERVICE ops. Always confirm `OPCODE_LIST =
   data/tl-menu-opcodes.json`.
2. **Closed master not seeded.** A fresh/never-seeded master only holds the days the daily
   ran (e.g. 2 rows = $227 for "the month") — wildly understated. If the MTD total looks
   too small, `--seed` the month. Verified June 1–29: 83 menus / $14,290.97.
3. **Greeting name.** It's **Sean**, not Preston. Guessing the first name off the email
   address (`spreston`) is wrong — `s` is the first initial.
4. **--seed is slow & buffered.** stdout block-buffers to the log file; the bash wrapper
   may go defunct (`Zs`) while the python child keeps running. Verify with
   `pgrep -f "tol_menu_sales_closed_mtd.py --seed"`, not the wrapper PID. Run it as a
   background job with `notify_on_complete`.
5. **Don't use browser_navigate/browser_vision for the :9223 session** — those open a
   separate UNauthenticated context. Use :9223's own `/eval` + `/screenshot`.

## 429 OVERALL_RATELIMIT on the OPENED script's RO search (fixed 2026-07-02)
`tol_menu_sales_api.py`'s `fetch_ros()` originally raised `RuntimeError: RO search 429`
immediately when the shared OpenAPI OVERALL_RATELIMIT was exhausted (commonly a concurrent
`caliber-ops tekion-scraper.ts --quick` cron for ANY store — e.g. Blackstone Toyota at
noon). Fixed: 8-try backoff loop (30s*(n+1), cap 120s) on the `/repair-orders:search`
call, same pattern as the closed script. If it still fails after 9 tries, check
`ps aux | grep tekion-scraper` and re-run.

**Foreground-timeout trap (hit 2026-07-02, 8PM run — BOTH scripts):** while the
backoff is riding through a concurrent `tekion-scraper.ts --quick --dealership
Toyota of Lancaster` cron (runs at noon AND ~8PM), the opened script can exceed
the 600s foreground terminal cap. The CLOSED daily-append run hit the same 600s
cap on the 8:05 PM 7/02 run **even with NO scraper running** (per-call backoff
inside `search_closed`/`scan_ro_safe` alone can add up). **Just run both scripts
as background jobs by default** for evening runs: `python3.11 -u <script> >
data/<name>.log 2>&1` with `background=true, notify_on_complete=true`, then read
the log. A timed-out foreground attempt may still leave written JSONs — the closed
one can be a valid partial (master written before timeout), but always re-run
clean and verify via the log rather than trusting leftovers (see next section).

**Validating a $0 opened JSON:** before rendering/drafting, check `ro_count_scanned`
in the companion `data/tol-menu-sales-api-<date>.json`. A healthy end-of-day pull on
a busy day scans ~150+ ROs (7/02 = 161); a holiday still scans a substantial count
(7/04 = 75 — that's a healthy pull, not starvation). If it shows 0 ROs scanned, the run was
starved by the rate limit — re-run, don't report $0 from it. `menus: 0` with a
plausible ro_count_scanned is a genuine zero-menu day.

## Uncaught socket TimeoutError ≠ 429 (learned 2026-07-22 noon)
The opened script can also die with a raw `TimeoutError: The read operation timed
out` (traceback through `urllib` → `ssl.py`, raised from the ThreadPool `ex.map`
fan-out on `/jobs/{id}/operations`). This is NOT a 429 — the backoff loops only
catch HTTP 429s, so a plain socket read-timeout (server slow under load from a
concurrent `tekion-scraper.ts --quick` cron, typically the noon Blackstone Toyota
run) crashes the whole run after the RO search already succeeded. Fix: just
`sleep 60` and re-run the script clean — second attempt completed in seconds
(7/22: 87 ROs, clean). No code change needed unless it recurs repeatedly; if it
does, wrap the per-op `call()` in the same retry pattern for `TimeoutError`.

## 429 OVERALL_QUOTA ≠ OVERALL_RATELIMIT (learned 2026-07-07)
Two distinct 429 messages:
- `Limit exhausted for type : OVERALL_RATELIMIT` — short rolling window; the 8-try
  backoff rides through it. Usually a concurrent tekion-scraper cron.
- `Limit exhausted for type : OVERALL_QUOTA` — the account's DAILY quota is gone.
  NO amount of backoff/waiting helps intra-day (verified 7/07: exhausted 14:12 →
  still 429 at 19:38+, probes every 2–5 min all day). Cause was a big ad-hoc scan
  (TOL tire Q2 quarter-ledger) earlier that day. When you see OVERALL_QUOTA:
  don't burn the session polling — report the outage honestly, skip the draft
  (never draft stale/zero data), and let the next scheduled run (or next day)
  retry. Also check for sibling watchers already queued (`wait_then_scrape2.sh`,
  `quota_probe_long.py` etc.) so you don't stack more probes on the dead quota.
  RECOVERY for a quota-killed CLOSED daily run: `tol_menu_sales_closed_mtd.py`
  accepts a positional date arg (`$PY tol_menu_sales_closed_mtd.py 2026-07-07`)
  that scans ONLY that day's closed ROs and merges into the month master — so a
  missed day can be backfilled later without a full --seed. Pattern used 7/07:
  leave a flock-guarded watcher (`backfill_tol_closed_<date>.sh`, probe every
  15 min, 14h deadline) as a background job that runs the dated backfill once
  the probe returns 200. Check `data/tol-closed-backfill-<date>.log` next run.
  NEW 7/08: OVERALL_QUOTA does NOT necessarily reset at midnight — the 7/07 14:12\n  exhaustion was STILL 429 through 12:30 PM 7/08 (22+ hours, probes every ~10 min all\n  night and morning). The 7/07 closed-backfill watcher hit its 14h deadline and gave\n  up (`GAVE_UP`/`TIMEOUT` in its log). Treat OVERALL_QUOTA as a possibly multi-day\n  outage: skip the run, report, and make sure MISSED closed days get dated backfills\n  (`tol_menu_sales_closed_mtd.py <date>`) once a probe finally returns 200.\n  UPDATE 7/08 8PM: the 7/07 14:12 OVERALL_QUOTA exhaustion was STILL 429 at 20:01 PM\n  7/08 — 30+ hours. Assume multi-day. A single sequential recovery runner\n  (`quota_recovery_runner.sh`, log `data/quota-recovery-<date>.log`, lock\n  `/tmp/tekion-quota-recovery.lock`) now replaces per-job watchers: it probes every\n  20 min via `dealer-detail/scripts/tekion-quota-probe.py` and on 200 runs queued\n  backfills ONE AT A TIME with cooldowns (avoids thundering-herd re-exhaustion).\n  Preferred pattern for a NEW missed day: do NOT add another probing watcher —\n  chain off the runner instead (watch its log for `QUEUE DONE`, cooldown, then run\n  your dated backfills). Example: `backfill_tol_20260708.sh` (log\n  `data/tol-backfill-2026-07-08.log`) waits for QUEUE DONE then runs\n  `tol_menu_sales_api.py 2026-07-08` (opened takes a positional date arg too) +\n  render + closed dated append + closed render. NOTE: an opened backfill run the\n  NEXT day still queries by creationTime for the given date, so the data is\n  correct, but the draft is late — tell Joe rather than auto-drafting stale-dated\n  email without context.\n  UPDATE 7/09 noon: STILL 429 at 12:15 PM 7/09 — ~46 hours since the 7/07 14:12\n  exhaustion. `quota_recovery_runner.sh` hit its 16h TIMEOUT at 12:03 PM 7/09 without\n  ever seeing a 200; the 7/08 TOL watcher also died. Replaced with\n  `quota_recovery_runner2.sh` (36h deadline, 30-min probes, expanded queue: BC closed\n  7/07, TOL closed 7/07+7/08+7/09, TOL opened 7/08+7/09 with renders, BT seed, SCT\n  align; log `data/quota-recovery2-<date>.log`, same flock). Escalate to Joe: this\n  smells like the account's quota allocation itself, not a normal daily reset —\n  may need Tekion support / APC portal check on the API key's quota tier.\n  UPDATE 7/09 8PM: STILL 429 at 20:04 PM 7/09 — ~54 hours since 7/07 14:12. runner2\n  (started 12:15 PM 7/09, 36h deadline → ~12:15 AM 7/11) probing every 30 min, never\n  seen a 200. TOL opened+closed 7/09 are in its queue, so EOD 7/09 gets backfilled\n  automatically on recovery — no need for a new watcher. 8PM run skipped pull+draft.\n  Related: on quota-crisis days another session may rename scripts to `*.py.paused`
  (plus a `quota_guard.sh` pkill loop, log `guard.log`) to reserve the window for
  one store's scrape. Check `ls *.paused` + `guard.log` mtimes before running;
  restore with `cp tol_menu_sales_api.py.paused tol_menu_sales_api.py` once the
  guard loop is no longer running.
  RESOLUTION 7/10-7/11: the 7/07 quota outage finally cleared — `quota_recovery2`
  log shows `QUEUE DONE` at 10:30 AM 7/10, and the 7/11 noon opened run pulled
  live with zero 429s (91 ROs scanned). Lingering `*.py.paused` files are HARMLESS
  if the active script also exists and is identical (`ls -la` both; same size/date
  = already restored, no action needed). Check the active file, not just the
  presence of `.paused`.

## 429 OVERALL_RATELIMIT on the initial closed search (fixed 2026-07-01)
The `search_closed()` in `tol_menu_sales_closed_mtd.py` originally had NO retry on
the FIRST `/repair-orders:search` call — it raised `RuntimeError: closed RO search
429` immediately if the shared OpenAPI OVERALL_RATELIMIT was exhausted (commonly by a
concurrent `caliber-ops` `tekion-scraper.ts --quick --dealership Toyota of Lancaster`
running at the same time on cron). Fixed: wrapped that call in an 8-try backoff loop
(30s*(n+1), cap 120s) mirroring `scan_ro_safe`. If you still see the raise, another
job may be hammering the API — check `ps aux | grep tekion-scraper` and just re-run;
the backoff now rides through it. Do NOT keep waiting/re-launching manually.

## Verifying a $0 / zero-menu result is REAL (not a bug)
Opened runs legitimately come back **0 menus / $0.00** on quiet days (verified
6/29, 6/30, 7/01/2026 all $0). Before treating $0 as a failure, confirm it's real:
- The 212-opcode menu set is ALL TEK-mileage opcodes (`TEK<mileage><tier>`, e.g.
  `TEK100000BNM`, tiers BNM/BSM/PSM/VNM). The matcher needs `opcode in menu_set`
  AND `labor.saleAmount > 0`.
- Quick sanity scan of today's opened ROs: pull `/repair-orders:search` by
  `creationTime BTW`, then for each RO GET `/jobs` then
  `/jobs/{id}/operations`, collect opcode prefixes. On a real $0 day you'll see
  lots of `TPS/SUR/INV/FLO/MPV/TXM/LOF/POR/CON` ops and only a handful of generic
  `TEK` ops that are NOT the mileage-menu ones (no overlap with the 212 list).
- If instead you see `TEK<mileage><tier>` opcodes WITH labor>0 that the report
  missed, THEN it's a real bug (check OPCODE_LIST path / matching).
- pitfall gotcha: in an inline `python3 -c` avoid bare `&` (e.g. `a & b` set
  intersection) — the shell backgrounds it. Use `a.intersection(b)` or a heredoc.
Still render + draft the $0 scorecard; the render handles empty tables cleanly
(TOTAL row only, KPIs $0.00). Frame Stacey's summary honestly: "No menu packages
were written on opened ROs today — total menu gross $0.00 across 0 menus."

**Validating a $0 CLOSED MTD:** the closed script's log tells you directly whether
$0 is real. A healthy zero looks like (7/02 example):
`closed/invoiced ROs today: 68` → `prefilter: 0 of 68 closed ROs carry a TEK menu
opcode` → stdout `✓ all candidate ROs scanned (no truncation)`. Nonzero ROs scanned
+ zero prefilter hits + no-truncation line = genuine zero-menu MTD; render and
draft it honestly. `closed/invoiced ROs today: 0` on a business day = starved run,
re-run it. New-month note: on the 1st (or first run of a month) the script
auto-creates a fresh `MASTER-<YYYY-MM>.json` with empty records — a tiny (~97 byte)
master early in the month is normal, NOT the "unseeded master" pitfall.

## Cross-store note
This same pattern (clone the sibling pipeline, derive the store's OWN SERVICE_MENU opcode
set, set dealer ID + recipient) applies to the remaining AMG stores (SV/AR/VC) when Joe
asks for their menu reports. Per-store menu set ≠ SCT's 316 — always derive it.
**BT was cloned from THIS pipeline 2026-07-08** — see `bt-menu-sales-reports` for the
BT specifics and the clone pitfalls (missed `tol-*` cache paths + internal
`"dealerId":"1092"` literals need a second sed pass; verify with a zero-grep).
