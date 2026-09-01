---
name: sct-alignment-by-advisor-report
description: Run the Stevens Creek Toyota (SCT, dealer ST/876) Alignment-by-Advisor report from the LIVE Tekion OpenAPI — counting BOTH dedicated alignment opcodes (ALIGN/OKAL) AND alignments bundled inside a TEK service-menu op. Produces the Joe-approved 2-page Toyota-red scorecard (page 1 advisor ranking PNG, page 2 RO-level chip detail PDF) and hands to Stacey to DRAFT in Joe's inbox. Supports full-month (last month) or closed month-to-date windows. This is THE canonical AMG alignment-report FORMAT Joe reuses a lot going forward.
triggers:
  - sct alignment report
  - alignment by advisor sct
  - stevens creek alignment report
  - sct alignment month to date
  - daily alignment report
---

# SCT Alignment-by-Advisor Report (LIVE OpenAPI)

Counts alignments SCT sold in a period, broken down by service advisor, capturing:
- **Dedicated** alignment opcodes sold on an RO: `ALIGN`, `OKAL`, `ALIGN00BRA`.
- **Bundled** alignments performed inside a TEK service-menu op (any `TEK*` opcode
  whose operation story contains "align").

Joe approved this exact report + format on 2026-07-01 ("Alignment report is
perfect!") and said the FORMAT will be reused a lot across stores. The generic
per-store version is skill `tekion-alignment-by-advisor-report`; THIS skill is the
SCT-specific, proven pipeline with the frozen SCT opcode set + scripts.

## Scripts (built, proven)
- **Scan:** `/home/itadmin/tekion-reports/sct_align_full_june.py` — the full-month
  scanner (edit MS0/MS1 window at top for a different month). Two-tier, rate-limit-safe.
- **MTD scan:** `/home/itadmin/tekion-reports/sct_align_mtd.py` — closed month-to-date
  (1st of current month → end of today, Pacific). Same architecture; window auto-computed.
  **STALE SAME-DAY INDEX TRAP (hit 2026-07-10):** the scan caches
  `data/sct-mtd-<YYYY-MM-DD>-closed-index.json` keyed by DATE only. If anything ran the
  scan earlier the SAME day (e.g. a 9:31am probe), the 7pm run reuses that morning index
  and silently misses every RO closed since (observed 1,354 vs 1,461 ROs → 128 vs 141
  alignments — wrong report, exit 0, failed=[]). Before the nightly scan, check the index
  file's mtime; if it exists and is hours old, `mv` it to a `.bak` and re-run. The
  align-scan checkpoint still resumes, so only the NEW candidates fan out (~30 ROs, fast).
  A "loaded cached index: N ROs" log line at 7pm is the tell — always question it.
- **Render:** `/home/itadmin/tekion-reports/render_sct_align_full_june.py` — reads the
  self-contained by-advisor JSON, emits the 2-page scorecard. (A generalized
  `render_sct_align.py` reads any `sct-*-align-by-advisor*.json` + a period label.)
- Interpreter: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`. Data dir:
  `/home/itadmin/tekion-reports/data/`.

## Scan architecture (why it's built this way — DO NOT simplify)
- **Window + status:** filter `closedTime` BTW [start, end-of-today] + `status IN
  CLOSED,INVOICED`. NEVER `modifiedTime` (overcounts). Pacific tz (-07:00).
- **Two-tier, rate-limit-safe:** Pass 1 enumerates all closed ROs, capturing per-RO
  the FREE opcode `tags` (`{field:"OPCODE", value:<code>}`) + `assignee.advisor.id`.
  Pass 2 fans out jobs→operations ONLY on CANDIDATES = ROs whose opcode tags include a
  dedicated ALIGN code OR any `TEK*` code (a bundled alignment can hide inside any menu).
  Full June: 5,382 closed → 1,169 candidates. This ~5x reduction keeps the run under
  the app-wide `OVERALL_RATELIMIT`.
- **DEALER_QUOTA exhaustion — PARTIAL/deep-endpoint variant (hit 2026-08-01):** a THIRD
  quota type. Signature: `/repair-orders:search` and `/repair-orders/{id}/jobs` return 200,
  but `/jobs/{id}/operations` 429s with `Limit exhausted for type : DEALER_QUOTA.` — so the
  skill's standard quota probe (search pageSize=1) returns 200 and LIES. The scan builds the
  index fine, then hangs silently in the fan-out retry/backoff loop forever (no checkpoint
  file ever appears — checkpoint only writes every 20 done ROs). Tells: >15 min with index
  built but NO align-scan.json checkpoint; the `sct-closed/opened-quota-recovery` cron logs
  show `OPS_429`. Diagnose with a probe on the OPS endpoint, not search:
  `O.call('GET','/repair-orders/<rid>/jobs/<jid>/operations')`. Both backoff guards in
  sct_align_mtd.py now also match "DEALER_QUOTA" (patched 2026-08-01). Playbook: kill the
  hung scan, arm the dated self-heal pair (`selfheal_sct_align_20260801.sh` probes the OPS
  endpoint, not search) + handoff watcher; the handoff script now bakes on-disk byte sizes
  into the Stacey build ask. Outage observed 19:00 → past 21:15 PDT with no recovery.
  **DEALER_QUOTA can persist >22h + the sync-all hog + expired-watcher re-arm (2026-08-02):**
  the same outage was STILL 429 at 5 PM the next day. Three lessons:
  1. **Hunt the hog FIRST:** the dealer-detail nightly `sync:all` (cron 23:00,
     `cron-sct-sync.sh` → `npm run sync:all` → tsx) had been running **17 hours**, stuck
     retrying SCT against the 429 wall — it grabs any refill instantly. Diagnose:
     `pgrep -af "sync-all|cron-sct-sync|tsx --conditions"` + `ps -o lstart=` on the flock
     pid (a start time from last night = stuck). Fix: kill the WHOLE tree (flock, .sh, npm,
     tsx, node pids) and confirm `/tmp/dealerdetail-sct-sync.lock` is gone. Do this before
     re-arming anything.
  2. **The 21h self-heal DEADLINE expires mid-outage:** an outage starting ~7 PM outlives a
     watcher armed at ~8:53 PM. Re-arm with fresh DATED copies — the sed date-swap works:
     `sed -e 's/2026-08-01/2026-08-02/g; s/20260801/20260802/g' selfheal_sct_align_20260801.sh
     > selfheal_sct_align_20260802.sh` (LOG/LOCK lines carry dates so both rename cleanly),
     `bash -n` both, chmod +x in its own foreground call, kill the old watcher pair, launch
     each new one via terminal(background=true, /usr/bin/bash explicit).
  3. **Month rollover during an outage:** when recovery lands after the 1st, the MTD scan
     produces a tiny new-month report. The prior month's FINAL data (through the 31st) is
     already on disk (`sct-mtd-<mm>-31-align-by-advisor.json`) — offer Joe a July-final
     render+draft that needs ZERO API quota while waiting.
  If still 429 at the next nightly refill, escalate to Joe: multi-day DEALER_QUOTA
  non-reset is a Tekion-side problem (raise quota / investigate reset).
  **Confirmed recurrence 2026-08-03 (7pm nightly, 3rd/4th consecutive day):** OPS probe
  still 429 DEALER_QUOTA at 19:22 PDT (search+jobs 200, /operations 429 — same signature).
  No sync:all hog and no quota_recovery/backfill runner was active this time (checked
  `pgrep -af "sync-all|cron-sct-sync|tsx --conditions"` and
  `pgrep -af "quota_recovery|bt_seed_watcher|sct_closed_backfill"` — both empty), so the
  non-reset is NOT being caused by a local competing consumer this round — points more at
  a Tekion-side quota bucket that simply isn't refilling daily. Armed fresh dated pair
  `selfheal_sct_align_20260803.sh` + `selfheal_sct_align_handoff_watch_20260803.sh` (probe
  RO/job ids swapped to a fresh 2026-08-03 candidate: RO 6a710a6bcb86dd4c535a2836 / job
  6a710afbcb86dd4c535a9e8f). This is now a MULTI-DAY unresolved outage (8/1→8/2→8/3) —
  worth escalating to Joe directly as a Tekion support ticket rather than re-arming
  nightly forever.
  **Confirmed recurrence 2026-08-04 (7pm nightly, 4th consecutive day, still 429 at
  next-day 7pm):** OPS probe (same RO/job pair `6a727c3d84f7f40f9a42f396` /
  `6a727e1f84f7f40f9a43c9be` reused from the 8/3 probe, confirmed still returns 200 on
  search/jobs) still 429 DEALER_QUOTA at 19:04 PDT. Re-checked for a local competing
  consumer again (`sync-all|cron-sct-sync|tsx --conditions` and
  `quota_recovery|bt_seed_watcher|sct_closed_backfill|sct_align_mtd|selfheal_sct_align`)
  — both empty, confirming (2nd time in a row) this is NOT a local hog; the Tekion-side
  DEALER_QUOTA bucket for SCT is simply not resetting daily. Armed fresh dated pair
  `selfheal_sct_align_20260804.sh` + `selfheal_sct_align_handoff_watch_20260804.sh` via
  the standard `sed -e 's/2026-08-03/2026-08-04/g; s/20260803/20260804/g' <old>.sh >
  <new>.sh` date-swap (LOG/LOCK lines carry dates so both rename cleanly) — reused the
  SAME probe RO/job ids as 8/3 since they still validate (200 on jobs, 429 only on
  operations); no need to hunt a fresh candidate every day if the old probe pair still
  round-trips through search/jobs. `bash -n` both before chmod, chmod in its own
  foreground call, launched each via terminal(background=true, /usr/bin/bash explicit).
  No prior-outage watchers were still alive to kill (8/3 pair had already hit its 21h/22h
  TIMEOUT and exited cleanly per its own log). At month rollover (this outage started
  right at 8/1) there is no partial-month fallback to render meanwhile — unlike the
  7/31→8/1 case, there was no "prior month final" data to offer since the July report had
  already shipped. This is now a 4-DAY continuous unresolved outage (8/1→8/2→8/3→8/4) —
  each nightly run should keep re-arming the self-heal pair (it costs nothing and will
  catch a mid-outage recovery) but should ALSO reiterate the Tekion-side escalation in
  its report every time, rather than treating it as routine. Recommend Joe open a formal
  Tekion support ticket if this persists past day 4-5, since local self-heal cannot fix a
  server-side quota bucket that never refills.
  **Confirmed continuing 8/5 and 8/6 (days 5 and 6, still 429 both nights):** same OPS
  probe signature (search/jobs 200, `/operations` 429 DEALER_QUOTA) held straight through
  — the 8/5 self-heal watcher logged a 429 every ~10 min for its full run with no recovery
  (never hit "quota restored"), and the fresh 8/6 probe at 19:01 PDT was still 429. No
  local competing consumer found either night (checked the same process list both times).
  Reused the SAME validated probe RO/job pair unchanged since 8/3 (still round-trips 200 on
  search/jobs) — don't bother hunting a new candidate as long as the old one still validates.
  **This is now a 6-CONSECUTIVE-DAY unresolved outage (8/1→8/6) with zero August MTD reports
  shipped** — at this length, stop treating "keep re-arming nightly" as sufficient; the
  report to Joe should explicitly recommend a formal Tekion support ticket rather than
  soft-pedaling it as routine self-heal.
  **Confirmed continuing 8/7 (day 7, still 429):** same signature (search/jobs 200,
  `/operations` 429 DEALER_QUOTA) at 19:01 PDT, cross-checked against the independent
  `sct-closed-quota-recovery` job's own probes logged 18:03-18:54 the same evening — also
  all 429. No local competing consumer found (checked
  `sync-all|cron-sct-sync|tsx --conditions` and
  `quota_recovery|bt_seed_watcher|sct_closed_backfill|sct_align_mtd|selfheal_sct_align` —
  both empty). Reused the standard sed date-swap
  (`sed -e 's/2026-08-06/2026-08-07/g; s/20260806/20260807/g' <old>.sh > <new>.sh`) for
  BOTH the probe script and its handoff-watch pair, `bash -n` both, chmod in its own
  foreground call, launched each via terminal(background=true, /usr/bin/bash explicit) —
  confirmed alive via the log's "watcher started" line within 5s. Before arming, asked
  Stacey a terse read-only Gmail search ("subject substring 'SCT Alignment' in Drafts
  and Sent, last 10 days") to confirm the last thing that actually shipped: July
  full-month report, Sent 2026-08-02 — zero August MTD reports have gone out. **7
  CONSECUTIVE DAYS (8/1-8/7) is well past routine self-heal territory** — every nightly
  report in this window should explicitly recommend Joe open a formal Tekion support
  ticket, not just re-arm and move on.
  **When the current scan is blocked, confirm what's already in Drafts before assuming
  nothing shipped:** ask Stacey a terse read-only Gmail search for a SUBSTRING (not exact
  subject match, per the exact-subject false-zero trap above) like "SCT Alignment" to find
  the most recent draft already sitting in Joe's Drafts (e.g. the July MTD-final report
  from before the outage began) — useful context to include in the blocked-night report
  so Joe knows the last successful data point even while August is stuck.
  **Confirmed continuing 8/8 and 8/9 (days 8 and 9, still 429):** the 8/8 self-heal watcher
  ran its full 21h deadline probing every ~10 min (124 log lines, all 429) and hit
  "TIMEOUT — quota never restored" at 8/9 16:05 PDT with zero recovery. Fresh 8/9 probe at
  19:01 PDT (same validated RO/job pair, unchanged since 8/3) also 429. No local competing
  consumer either night (checked the standard process list). Re-armed the standard dated
  pair via the sed date-swap, `bash -n` + chmod + terminal(background=true) launch,
  confirmed alive via pgrep + log "watcher started" line — same recipe as prior days, no
  changes needed. Stacey Gmail check (read-only, "SCT Alignment" substring, Drafts+Sent,
  last 10 days) confirmed the last actually-SENT report is July Full Month (sent Aug 2,
  to Joe) and the July MTD-through-7/31 draft is still sitting unsent in Drafts — zero
  August reports (draft or sent) exist as of day 9. **9 CONSECUTIVE DAYS (8/1-8/9)** —
  this is well past the point where "keep re-arming nightly" should be reported as
  routine; explicitly recommend a formal Tekion support ticket in every blocked-night
  report at this point, not just on first crossing day 4-5.
  **Confirmed continuing 8/10 (day 10, still 429):** 19:01 PDT probe on the same validated
  RO/job pair (unchanged since 8/3) — search/jobs 200, `/operations` 429 DEALER_QUOTA,
  identical signature to every prior day. No local competing consumer
  (`sync-all|cron-sct-sync|tsx --conditions` and
  `quota_recovery|bt_seed_watcher|sct_closed_backfill|sct_align_mtd|selfheal_sct_align` both
  empty — the 8/9 watcher pair had already exited cleanly at its own TIMEOUT, nothing to
  kill). Re-armed the standard dated pair via the sed date-swap
  (`sed -e 's/2026-08-09/2026-08-10/g; s/20260809/20260810/g' <old>.sh > <new>.sh`),
  `bash -n` both, chmod in its own foreground call, launched each via
  terminal(background=true, /usr/bin/bash explicit), confirmed alive via pgrep + the log's
  "watcher started" line within 5s. Stacey Gmail check (read-only, "SCT Alignment"
  substring, Drafts+Sent, last 10 days) reconfirmed: last SENT = July Full Month (Aug 2),
  last DRAFT = July MTD-through-7/31 (still unsent) — zero August reports (draft or sent)
  as of day 10. **10 CONSECUTIVE DAYS (8/1-8/10) with zero August MTD reports shipped** —
  every nightly report in this window must explicitly and prominently recommend Joe open
  a formal Tekion support ticket for the SCT DEALER_QUOTA bucket; this is no longer
  routine self-heal territory by any measure.
  **OUTAGE RESOLVED 2026-08-11 (day 11, first clean run after 10 straight 429 nights):**
  the standard OPS probe (`/repair-orders/{rid}/jobs/{jid}/operations` on the same
  validated RO/job pair reused since 8/3) returned a clean 200 at 19:01 PDT. Ran the MTD
  scan immediately — 1,403 closed ROs, 405 candidates, 0 failed, completed in a few
  minutes (no rate-limit backoff triggered at all). First successful August MTD report
  shipped: 132 alignments (118 dedicated + 14 bundled), 132 ROs, 16 advisors. Lesson: the
  quota DOES eventually self-heal on the Tekion side without any local fix — always probe
  fresh each night before assuming the outage continues; don't skip straight to
  "re-arm and escalate" without a live check. No self-heal watcher was needed this run.
  **Confirmed stable 2026-08-12 (2nd consecutive clean night post-outage):** OPS probe
  200 immediately, no self-heal needed. Full run clean: 1,658 closed ROs, 513 candidates,
  0 failed, ~19 min. 154 alignments (137 dedicated + 17 bundled), 154 ROs, 16 advisors,
  top Cristian Gonzalez (25). Stacey's build ask timed out (exit 124) on the first try as
  usual — the standard fix (sleep 60s, then a single subject-anchored verify ask) resolved
  it cleanly: DRAFTS_COUNT=1, SENT=no, PDF part non-zero (303,528B for a 233,121B file,
  within normal encoding variance), HTML part 171,532B comfortably above the PNG*4/3
  floor. First-try clean draft, no rebuild needed. The DEALER_QUOTA outage looks resolved
  for good at this point — no further escalation language needed unless it recurs.
   Confirmed again 2026-08-13 (3rd consecutive clean night): no quota issues at all —
  index built 1,903 closed ROs, 596 candidates, 0 failed, ~23 min scan (steady ~80
  ROs/3min pace, checkpoint mtime advancing throughout — no backoff triggered). 165
  alignments (148 dedicated + 17 bundled), 165 ROs, 16 advisors, top Cristian Gonzalez
  (25). Stacey's build ask did NOT time out this time — completed in 114s on the first
  try with sizes baked into the build ask (per the 07-22 prevention note), full
  verification in her own reply (HTML 127,110B >= PNG*4/3=126,483; PDF part exactly
  238,779B matching the file). A short `sleep 15` (not the usual 60s) before the
  subject-anchored verify ask was enough — it answered in 44s with DRAFTS_COUNT=1,
  correct TO, SENT_FOLDER_COUNT=0. Confirms the pipeline is now reliably stable
  post-outage; a Stacey build timeout is no longer "usual", just occasional.
  **Confirmed again 2026-08-14 (4th consecutive clean night, quota fully healthy):**
  index built 2,145 closed ROs, 682 candidates, 0 failed, ~25 min scan (19:02→19:27,
  no backoff triggered). 190 alignments (168 dedicated + 22 bundled), 190 ROs, 16
  advisors, top Cristian Gonzalez (26). Stacey's build completed clean on the first
  ask (38s) with sizes baked in per 07-22 prevention. BUT the note-6 dedupe trap fired
  anyway — a PARTS-list verify ask surfaced **3 draft UIDs** with that subject (59/67/72,
  PDF parts 303,528B → 326,752B → 344,454B, growing each revision) even though only ONE
  build ask was ever sent — Stacey's internal retry/revision process silently creates
  extra draft copies without a distinct build request each time. Size math confirmed
  the newest (UID 72, largest PDF) was the good one: HTML part 175,878B >=
  PNG*4/3=127,743B; PDF part 344,454B is +2.6% over PDF*4/3=335,617B (normal encoding
  variance). **Effective dedupe technique:** don't just say "delete duplicates" —
  give her the EXACT UIDs to keep vs delete ("Keep ONLY UID 72, delete UID 59 and UID
  67") from a PARTS-list ask that already enumerated them; this resolved cleanly in one
  ask (59.9s) with a one-line confirm (DRAFTS_COUNT=1). Final verify showed
  PDF_PART_BYTES=251,713 exactly matching the on-disk PDF file size — a clean, exact
  byte-count match is the strongest possible confirmation, stronger than the ~4/3
  encoded-size heuristic. Lesson: even on a fast, non-timing-out build night, ALWAYS
  run the PARTS-list verify (not just a generic DRAFTS_COUNT ask) — it's the only ask
  that reveals multiple UIDs so you can dedupe by exact UID instead of a vague
  "delete the old ones" request.
  **Confirmed again 2026-08-17 (7th consecutive clean night, quota fully healthy) —
  UID INSTABILITY across sequential verify asks:** scan clean (2,618 closed, 869
  candidates, 0 failed, ~34 min). 247 alignments (224 dedicated + 23 bundled), 247
  ROs, 16 advisors, top Cristian Gonzalez (30). Stacey's build completed clean on the
  FIRST ask (115s) with sizes baked in. Verify step 1 (subject-anchored DRAFTS_COUNT/
  TO/SENT_FOLDER_COUNT) came back clean instantly: 1 | kstapp@sctoyota.com | 0. Verify
  step 2 (combined PARTS/RAW_SIZE ask) timed out (124) as usual; per note 11's 07-27
  pattern, degraded to the terse two-line form ("TO=? RAW_SIZE=?") after a 60s pause —
  but this answer cited **"UID 88"**, while the original build confirmation had cited
  **"UID 42368"** — two different UID numbers for what should be the same single
  draft. Rather than assume a duplicate was created, ran ONE more explicit ask: "List
  all drafts with subject substring X dated today, reply UID=<uid> SIZE=<bytes> per
  draft, then DRAFTS_COUNT=<n>" — this came back with a THIRD UID (42251) and
  DRAFTS_COUNT=1, plus a clarifying note that 4 drafts total match the subject
  substring but only 1 is dated today (others are from different nights, per the
  8/16 multi-night-match note). **Lesson: Stacey's reported UID numbers are NOT
  stable/reliable across separate asks, even referring to the same single draft in
  the same conversation turn window** — don't panic-dedupe on a UID mismatch across
  asks. The authoritative signal is a DATE-ANCHORED DRAFTS_COUNT (not the UID value
  itself); if that count is 1, there is one draft, regardless of which UID number
  she quotes in different replies. Only trust UID values for dedupe INSTRUCTIONS
  within the SAME ask/reply pair (per the 8/14 "keep UID X delete UID Y" pattern),
  never across separate asks.
  **Confirmed again 2026-08-18 (8th consecutive clean night) — SENT_FOLDER_COUNT>0 is
  NOT a send-trap alarm once Joe starts sending prior drafts:** pre-flight OPS probe 200.
  Index 2,786 closed ROs, 932 candidates, 0 failed, ~29 min (19:01→19:30). 264 alignments
  (239 dedicated + 25 bundled), 264 ROs, 16 advisors, top Cristian Gonzalez (31). Stacey's
  build clean on the FIRST ask (163s) with paths + on-disk sizes baked in; her own reply
  gave HTML part 176,412B >= PNG*4/3=129,825B and PDF part 288,540B = EXACT on-disk size.
  The subject-anchored verify returned `DRAFTS_COUNT=1 | TO=kstapp@sctoyota.com |
  SENT_FOLDER_COUNT=3` — the 3 are PRIOR NIGHTS' reports Joe reviewed and sent himself in
  the morning (the whole point of draft-only), NOT evidence Stacey sent anything. Do NOT
  panic on a nonzero Sent count now that the nightly has been running for weeks. Correct
  tiebreaker = a TODAY-scoped one-liner: "In Sent Mail, how many with subject substring
  'SCT Alignment' were sent TODAY? Reply: SENT_TODAY=<n>" → came back 0. (The richer
  "list every Sent match with subject+date" ask timed out exit 124; per note 11, a 60s
  pause then the ultra-terse single-number form answered fine. Keep re-asks to ONE
  question with ONE number.)
  **Confirmed again 2026-08-19 (9th consecutive clean night, quota fully healthy):**
  pre-flight OPS probe (same validated RO/job pair, unchanged since 8/3) returned 200 —
  keep doing this probe even deep into a healthy streak, it costs one call. Index 3,046
  closed ROs, 1,008 candidates, 0 failed, ~38 min scan (19:01→19:39, no backoff). 287
  alignments (256 dedicated + 31 bundled), 287 ROs, 16 advisors, top Cristian Gonzalez
  (33) — note Jaime Sanchez and Artist Battle tied at 30, so Cristian's usual #1 spot is
  narrowing. Stacey's build clean on the FIRST ask (67s) with paths + on-disk sizes baked
  in; her own reply gave HTML part 176,942B and PDF part 405,746B. Standard two-ask verify
  both answered on the first try with only a short sleep (15s then 10s, not 60s):
  `DRAFTS_COUNT=1 | TO=kstapp@sctoyota.com | SENT_FOLDER_COUNT=0`, then PARTS
  `RAW_SIZE=591,957 | text/html=179,240 | application/pdf=411,016` — HTML >= PNG*4/3
  (130,233) confirms inline PNG, PDF part +2.6% over PDF*4/3 (400,476) is the normal
  CRLF-wrap variance, and RAW_SIZE ≈ html+pdf parts cross-checks. Note her reply strips
  underscores (`DRAFTSCOUNT`, `PDFPART_BYTES`) — same answer, don't re-ask. Also note the
  part sizes she reports in the BUILD confirmation vs the later PARTS ask differ slightly
  (176,942 vs 179,240 html; 405,746 vs 411,016 pdf) — both pass the lower-bound math;
  small discrepancies between her two reports of the same part are NOT a duplicate-draft
  signal (the date-anchored DRAFTS_COUNT=1 is authoritative, per the 8/17 UID-instability
  note).
  **Confirmed again 2026-08-20 (10th consecutive clean night) — FLAT-DAY / STORE
  POSTING-LAG false alarm:** OPS probe 200. Index 3,065 closed ROs, 1,008 candidates,
  0 failed, ~42 min (19:01→19:43). Result 287 alignments (256 ded + 31 bundled), 287
  ROs, 16 advisors — **byte-for-byte the same candidate count (1,008) and the same
  total (287) as 8/19**, which looks exactly like the stale-same-day-index trap. It was
  NOT. Diagnosis recipe when today's MTD numbers don't move:
  1. Confirm the index is FRESH, not a cached reuse — compare the `window` end
     timestamp in `sct-mtd-<today>-closed-index.json` vs yesterday's (must advance one
     day: 1787209199999 → 1787295599999) and diff the RO id sets
     (`new in 8/20: 19, dropped: 0`). A reused index would have an IDENTICAL window.
  2. Then confirm at the API level with a single-day closed count per day rather than
     trusting the MTD delta: closed 8/18=167, 8/19=261, **8/20=19**. Only 19 ROs closed
     store-side all day (cashiering/posting lag), and none of the 19 were alignment
     candidates → new candidates today = 0 → totals legitimately unchanged.
  So identical day-over-day totals can be REAL. Always run the two checks above before
  suspecting a stale index or a broken scan; conversely a matching `window` end
  timestamp is the definitive tell that you DID hit the stale-index trap.
  Also note: `sct-mtd-latest-align-by-advisor.json` is a COPY, not a symlink — a
  `realpath` comparison against the dated file will (correctly) return False. Don't
  treat that as a stale-pointer bug; verify by reading its `period_label`/`totals`
  instead.
  Stacey's build clean on the FIRST ask (70s) with paths + on-disk sizes baked in
  (HTML part 131,086 >= PNG*4/3=130,319; PDF part exactly 300,357B = on-disk size).
  Standard two-ask verify, short sleeps (15s then 10s), both first-try:
  `DRAFTS_COUNT=1 | TO=kstapp@sctoyota.com | SENT_FOLDER_COUNT=0`, then
  `RAW_SIZE=592,097 | text/html=179,384 | application/pdf=411,016` (+2.6% CRLF variance,
  RAW_SIZE ≈ html+pdf). Underscore-stripped keys again — same answer, don't re-ask.
  **Confirmed again 2026-08-21 (11th consecutive clean night) — TIGHT HTML-part pass is
  still a PASS:** OPS probe 200 (same validated RO/job pair, unchanged since 8/3). Index
  3,089 closed ROs, 1,012 candidates, 0 failed, ~37 min (19:01→19:38, no backoff).
  Window end 1787381999999 advanced one day from 8/20's 1787295599999 — the definitive
  not-a-stale-index check. 290 alignments (259 dedicated + 31 bundled), 290 ROs, 16
  advisors, top Cristian Gonzalez (33). Stacey's build clean on the FIRST ask (52s) with
  paths + on-disk sizes baked in. Two-ask verify, short sleeps (15s then 10s), both
  first-try: `DRAFTS_COUNT=1 | TO=kstapp@sctoyota.com | SENT_FOLDER_COUNT=0`, then
  `RAW_SIZE=594,374 | text/plain=434 text/html=131,618 application/pdf=301,484`. Note the
  HTML part cleared the PNG*4/3 floor (131,060) by only **558 bytes** — a far tighter pass
  than the usual ~45KB headroom nights where Joe's heavy HTML signature inflates it. Per
  note 13 a tight pass IS a pass (her build sometimes omits the heavy signature); do NOT
  rebuild over thin headroom when the PDF part is an exact on-disk byte match (301,484)
  and DRAFTS_COUNT=1. Also: RAW_SIZE (594,374) exceeding html + pdf*4/3 (533,597) is
  normal header/encoding overhead — only a RAW_SIZE *below* that sum is a red flag.
  Underscore-stripped keys again (`DRAFTSCOUNT`, `SENTFOLDER_COUNT`) — same answer.
  **Confirmed again 2026-08-22 (12th consecutive clean night) — SECOND flat-day, and a
  TRUE ZERO-CLOSE day:** OPS probe 200. Index 3,089 closed ROs, 1,012 candidates, 0 failed,
  ~37 min (19:01→19:38). Totals 290 alignments (259 ded + 31 bundled), 290 ROs, 16 advisors,
  top Cristian Gonzalez (33) — **byte-identical to 8/21 in every figure, and the index file
  was even the same byte size (425,567)**, which looks alarming. Ran the note-20 flat-day
  recipe and it cleared: the `window` end advanced one day (1787381999999 → 1787468399999,
  so NOT a cached index), but the RO id-set diff was `new: 0, dropped: 0` — unusual, since
  8/20's flat day still had 19 new ROs. Per-day API closed counts explained it: 8/19=261,
  8/20=19, 8/21=24, **8/22=0**. A Saturday with literally zero ROs closed store-side means
  the MTD set cannot change at all, so identical index size + identical totals are correct.
  Recipe refinement: `new in index = 0` alone is NOT proof of a stale index — pair it with
  the window-end check (definitive stale tell) and the single-day closed count; if that
  count is 0, an unchanged report is the right answer. Also note the per-day count helper
  must send `values` (not `value`) as STRING lists in the search filter — a `value`/int
  form returns HTTP 500 with no totalCount and will mislead you into thinking the API is
  broken; paginate and count results rather than trusting a `meta.totalCount` field (it
  isn't returned). Stacey's build clean on the FIRST ask (93s) with paths + on-disk sizes
  baked in. Two-ask verify, short sleeps (15s then 10s), both first-try:
  `DRAFTS_COUNT=1 | TO=kstapp@sctoyota.com | SENT_FOLDER_COUNT=0`, then
  `RAW_SIZE=594,777 | text/plain=608 text/html=180,502 application/pdf=412,560` — HTML part
  clears PNG*4/3 (131,174) with the usual heavy-signature headroom, PDF part +2.6% over
  PDF*4/3 (401,979) is the normal CRLF variance, RAW_SIZE ≈ html+pdf parts. Underscore-
  stripped keys again.
  **Confirmed again 2026-08-23 (13th consecutive clean night) — THIRD flat-day, near-zero
  close day, cleared by the note-20/22 recipe:** OPS probe 200 (same validated RO/job pair,
  unchanged since 8/3); no same-day index existed pre-run (checked mtime first per the stale-
  index trap). Index 3,091 closed ROs, 1,012 candidates, 0 failed, ~38 min (19:01→19:39).
  Totals 290 alignments (259 ded + 31 bundled), 290 ROs, 16 advisors, top Cristian Gonzalez
  (33) — **identical totals to BOTH 8/21 and 8/22** (three flat nights in a row). Cleared via
  the standard recipe: window end advanced 1787468399999 → 1787554799999 (NOT a cached index),
  id-set diff `new: 2, dropped: 0`, and per-day API closed counts 8/20=19, 8/21=24, 8/22=0,
  **8/23=2** — a Sunday with only 2 ROs closed store-side, neither an alignment candidate, so
  unchanged totals are correct. Note the index FILE SIZE grew slightly (425,567 → 425,823)
  which is a cheap extra confirmation the index is fresh even when totals don't move. Also
  note the leaderboard tightened further: Jaime Sanchez 31, Chris Mai 30, Artist Battle 30 —
  Cristian's lead is now 2. Stacey's build clean on the FIRST ask (163s) with paths + on-disk
  sizes baked in; her reply gave HTML part 132,033B and PDF part 301,487B (exact on-disk
  match). Two-ask verify, short sleeps (15s then 10s), both first-try:
  `DRAFTS_COUNT=1 | TO=kstapp@sctoyota.com | SENT_FOLDER_COUNT=0`, then
  `RAW_SIZE=595,032 | text/plain=630 text/html=180,678 application/pdf=412,564` — HTML clears
  PNG*4/3 (131,308) with heavy-signature headroom, PDF part +2.6% CRLF variance over
  PDF*4/3 (401,983), RAW_SIZE ≈ html+pdf. Underscore-stripped keys again. Note her BUILD
  confirmation reported the PDF part as the exact decoded file size (301,487) while the later
  PARTS ask reported the encoded size (412,564) — per note 9/8 BOTH forms are valid passes;
  the discrepancy between her two reports of the same part is not a duplicate signal.
  **Confirmed again 2026-08-24 (14th consecutive clean night) — VOLUME RESUMED + a NEW
  "TO=<person name>" verify false alarm:** OPS probe 200 (same validated RO/job pair,
  unchanged since 8/3); no same-day index existed pre-run. Index 3,320 closed ROs (up 229
  from 8/23's 3,091 — the three-day flat spell ended, Monday catch-up posting), 1,079
  candidates, 0 failed, ~35 min (19:01→19:36). Window end advanced 1787554799999 →
  1787641199999 and index file grew 425,823 → 458,053 B — both fresh-index confirmations.
  317 alignments (285 dedicated + 32 bundled), 317 ROs, 16 advisors. **Leaderboard is now a
  THREE-WAY TIE at #1** — Jaime Sanchez, Chris Mai, Cristian Gonzalez all 33 (Cristian's
  long-running solo #1 finally gone; Artist Battle 30 close behind). When the top spot is
  tied, phrase the email summary as "a three-way tie between X, Y and Z with N each" rather
  than arbitrarily picking one — Joe's report reads as a ranking. Stacey's build clean on
  the FIRST ask (81s) with paths + on-disk sizes baked in; her reply gave HTML part 176,347B
  >= PNG*4/3=129,751B and PDF part 427,654B (+1.3% over PDF*4/3=422,100 — normal CRLF
  variance).
  **NEW TRAP — the subject-anchored verify can answer `TO=<a PERSON NAME>` (the From/account
  identity), not the recipient address:** tonight's clean verify returned
  `DRAFTSCOUNT=1 | TO=Joe Castelino | SENTFOLDER_COUNT=0`. "Joe Castelino" is the mailbox
  OWNER, not the To: header — it directly contradicted the build confirmation's
  `TO=kstapp@sctoyota.com`. Do NOT rebuild or panic-dedupe on this. Tiebreaker = one
  ultra-terse read-only ask for the RAW HEADER: "print its raw To: header line exactly as
  stored. Reply ONE line: TO_HEADER=<exact To: header value>" → came back
  `TO_HEADER=kstapp@sctoyota.com`. Lesson: when the verify's TO field looks like a human
  name rather than an email address, she's read the account/From identity; ask for
  `TO_HEADER` explicitly. (Same family as the note-15 un-anchored garble and note-17 UID
  instability — her field labels are not trustworthy, the raw header is.)
  Also note: her first Drafts search MISSED the draft entirely and she self-corrected —
  "himalaya uses ISO dates (2026-08-24) not text dates (Aug 24)". A zero/miss on a
  dated-today search that she then retries is a search-syntax artifact, not a missing
  draft; let her self-correct before re-asking. Short sleeps sufficed throughout (15s
  then 10s), no timeouts at all this run.
  **Confirmed again 2026-08-25 (15th consecutive clean night) — NEW TRAP: PARTS-reported
  PDF size can equal a PRIOR NIGHT'S file size:** OPS probe 200 (same validated RO/job pair,
  unchanged since 8/3); no same-day index pre-run. Index 3,514 closed ROs (up 194), 1,079+
  candidates, 0 failed, ~43 min (19:01→19:44). Window end advanced 1787641199999 →
  1787727599999 and index grew 458,053 → 484,759 B — both fresh-index confirmations; id diff
  new: 194, dropped: 0. 325 alignments (293 dedicated + 32 bundled), 325 ROs, 16 advisors.
  **Two-way tie at #1: Jaime Sanchez and Cristian Gonzalez, 34 each** (Chris Mai / Artist
  Battle 33) — phrase ties as ties per the 8/24 note. Stacey's build clean on the FIRST ask
  (102s) with paths + on-disk sizes baked in.
  **The trap:** the PARTS verify returned `application/pdf:316575` — which was NOT today's
  on-disk PDF (320,623) but was an EXACT match for the PREVIOUS night's (8/24) PDF file size,
  which looks exactly like she attached the wrong/stale file. She did not. The note-14 decode
  tiebreaker settled it in one 27s ask — extend it to also request the FILENAME, which is the
  strongest single signal: "PDF_FILENAME=<exact attachment filename> | PDF_DECODED_BYTES=<n>"
  → `SCT-Alignment-By-Advisor-MTD-2026-08-25.pdf | 320623`, i.e. correct file, exact byte
  match. Lesson: a PARTS PDF size matching a PRIOR night's file size is a coincidental
  misreport, not a stale attachment — ALWAYS resolve with filename+decoded-bytes before
  rebuilding, since the filename carries the date and removes all ambiguity. Also note the
  HTML part passed the PNG*4/3 floor by only **117 bytes** (130,540 vs 130,423) — even
  tighter than the 8/21 558-byte pass; a tight pass is still a PASS (note 13).
  Two-ask verify with short sleeps (15s then 10s), both first-try:
  `DRAFTS_COUNT=1 | TO=kstapp@sctoyota.com | SENT_FOLDER_COUNT=0`. Underscore-stripped keys
  again. Also: her PARTS list included zero-size structural parts
  (`multipart/mixed:0, multipart/alternative:0`) — those are container parts, NOT the
  note-13 zero-byte-PDF trap; only a zero-size `application/pdf` part is a failure.
  **Confirmed again 2026-08-26 (16th consecutive clean night) — NEW TRAP: `DRAFTS_COUNT=2`
  from a LOOSE "dated today" match is a FALSE duplicate alarm:** OPS probe 200 (same validated
  RO/job pair, unchanged since 8/3); no same-day index pre-run. Index 3,751 closed ROs (up 237),
  1,248 candidates, 0 failed, ~55 min (19:01→19:56 — longest of the month, late-month window
  ballooning as expected). Window end advanced 1787727599999 → 1787813999999 and index grew
  484,759 → 515,615 B (both fresh-index confirmations). 333 alignments (300 dedicated + 33
  bundled), 333 ROs, 16 advisors. **Three-way tie at #1 again: Jaime Sanchez, Chris Mai,
  Cristian Gonzalez, 35 each** (Artist Battle 33) — phrase as a tie per the 8/24 note.
  Stacey's build clean on the FIRST ask (78s) with paths + on-disk sizes baked in; HTML part
  130,060B cleared PNG*4/3 (129,304) by only **756 bytes** (tight pass = PASS, note 13) and
  PDF part 324,005B was an EXACT on-disk match.
  **The trap:** the terse dated-today ask returned `DRAFTS_COUNT=2`, which looks exactly like
  the note-6 duplication norm — but there was only ONE draft for tonight. Two follow-ups timed
  out (exit 124) before the resolution; the ask that settled it definitively was a **date-free
  subject-substring enumeration**: "Gmail Drafts, subject substring 'SCT Alignment Sales by
  Advisor'. Reply one line per match: SUBJECT=<full subject> DATE=<date>" → returned 14 matches,
  one per night (8/14 through 8/26 plus the July MTD leftover), each with a DISTINCT through-date
  in the subject and its own date. Only one said "(through 8/26)". Lesson: Stacey's "dated today"
  filter is unreliable and can pull in the adjacent night's draft, inflating DRAFTS_COUNT by one.
  **Before deduping on a count of 2, ALWAYS run the date-free SUBJECT+DATE enumeration and check
  the through-date in each subject** — the through-date is the authoritative per-night
  discriminator (stronger than DRAFTS_COUNT, stronger than UIDs per note 17). Deleting on a bare
  count of 2 here would have destroyed the previous night's draft. Also note the count-versus-
  enumeration disagreement is the same family as notes 12/15/17: trust the enumeration, not the
  aggregate. Final verify: `TO_HEADER=Kevin Stapp <kstapp@sctoyota.com>` (raw-header form per
  note 8/24) and `SENT_TODAY=0`. Timeout pattern held to note 11 — 60s pause then a ONE-number
  ask answered every time.
  **Confirmed again 2026-08-27 (17th consecutive clean night) — PUT THE THROUGH-DATE IN THE
  VERIFY SUBSTRING and the note-26 DRAFTS_COUNT=2 trap never fires:** OPS probe 200 (same
  validated RO/job pair, unchanged since 8/3); no same-day index pre-run; no competing
  consumer. Index 3,975 closed ROs (up 224 from 8/26's 3,751), 0 failed, ~49 min
  (19:01→19:50). Window end advanced 1787813999999 → 1787900399999 and index grew
  515,615 → 544,982 B (both fresh-index confirmations). 345 alignments (312 dedicated + 33
  bundled), 345 ROs, 16 advisors. **Two-way tie at #1: Jaime Sanchez and Chris Mai, 36 each**
  (Cristian Gonzalez 35 — he has now slipped off the top spot entirely after a month of
  leading); phrase ties as ties per the 8/24 note.
  **Refinement that avoids the 8/26 false-duplicate entirely:** anchor the verify substring
  with the FULL subject INCLUDING the through-date — `'SCT Alignment Sales by Advisor -
  August MTD (through 8/27)'` — rather than the generic `'SCT Alignment Sales by Advisor -
  August MTD'`. The through-date is the authoritative per-night discriminator (note 26), so
  baking it into the substring makes DRAFTS_COUNT inherently per-night: returned a clean
  `DRAFTS_COUNT=1` on the first ask with zero enumeration follow-up needed, where the
  date-free form would have matched ~14 nights. Note the parens/dashes did NOT break the
  search here because it was explicitly framed as a SUBSTRING match ("substring match, not
  exact") — the note-11 exact-subject false zero is about EXACT matching, not punctuation
  per se. Also fold `TO_HEADER` (note 8/24) and `SENT_TODAY` (note 8/18) into that same
  first ask instead of `TO`/`SENT_FOLDER_COUNT` — both preempt their own false alarms in
  one round-trip: `DRAFTSCOUNT=1 | TOHEADER=kstapp@sctoyota.com | SENT_TODAY=0`.
  **Recommended verify ask #1 going forward:** subject substring WITH through-date →
  `DRAFTS_COUNT=<n> | TO_HEADER=<exact To: header> | SENT_TODAY=<n>`.
  Stacey's build clean on the FIRST ask (125s) with paths + on-disk sizes baked in. PARTS
  ask (with PDF_FILENAME folded in per the 8/25 note) answered first-try after a 10s sleep:
  `RAW_SIZE=633,032 | text/plain:430, text/html:131,922, application/pdf:329,436 |
  PDF_FILENAME=SCT-Alignment-By-Advisor-MTD-2026-08-27.pdf`. HTML part cleared PNG*4/3
  (131,145) by only **777 bytes** (third tight pass of the month — a tight pass is a PASS,
  note 13), PDF part was an EXACT on-disk match, and the filename carried today's date
  (strongest possible attachment confirmation). Her BUILD confirmation had reported the HTML
  part as 178,305 vs the PARTS ask's 131,922 — the familiar two-reports-of-the-same-part
  discrepancy (notes 8/9/8-23), both pass, not a duplicate signal. Short sleeps throughout
  (15s then 10s), no timeouts. Underscore-stripped keys again.
  **Confirmed again 2026-08-28 (18th consecutive clean night) — the note-27 through-date
  substring anchor is NOT enough on its own; the ENUMERATION is:** OPS probe 200 (same
  validated RO/job pair, unchanged since 8/3); no same-day index pre-run; no competing
  consumer. Index 4,214 closed ROs (up 239 from 8/27's 3,975), 1,389 candidates, 0 failed,
  ~51 min (19:01→19:52). Window end advanced 1787900399999 → 1787986799999 and index grew
  544,982 → 579,593 B (both fresh-index confirmations); id diff new: 239, dropped: 0.
  361 alignments (327 dedicated + 34 bundled), 361 ROs, 16 advisors. **Chris Mai is now
  SOLO #1 with 40** (Jaime Sanchez 38; Artist Battle and Cristian Gonzalez tied 35) — the
  multi-way tie at the top has broken.
  **Trap refinement:** the note-27 recipe (bake the through-date into the verify substring)
  did NOT prevent the false count this time — the ask used the full
  `'SCT Alignment Sales by Advisor - August MTD (through 8/28)'` substring and STILL came
  back `DRAFTS_COUNT=15`, i.e. she matched every August night despite the date being in
  the substring. So the through-date anchor helps but is not reliable; **the date-free
  SUBJECT+DATE enumeration (note 26) is the only trustworthy per-night discriminator.**
  It resolved in 30s: 16 matches listed, each with a DISTINCT through-date, exactly ONE
  reading "(through 8/28)". Never dedupe on a raw DRAFTS_COUNT — always enumerate first.
  Also note that enumeration incidentally reveals Joe has 15 August drafts still sitting
  unsent in Drafts (8/14 → 8/28) plus the July MTD leftover; that's his review backlog,
  not a pipeline fault.
  Stacey's build completed on the FIRST ask (119s) with paths + on-disk sizes baked in,
  though her transcript showed several internal self-corrections (typo'd addheader, a
  missed regex, "syntax mangling") before succeeding — internal retries do NOT imply
  duplicate drafts (enumeration proved 1). Her build reply: HTML part 177,575B, PDF part
  337,054B (exact on-disk). Final PARTS ask (162s, no timeout):
  `RAW_SIZE=642,755 | text/plain:385 text/html:131,451 application/pdf:337,054 |
  PDF_FILENAME=SCT-Alignment-By-Advisor-MTD-2026-08-28.pdf` — HTML cleared PNG*4/3
  (130,731) by only **720 bytes** (fourth tight pass of the month, still a PASS per note
  13), PDF part an exact on-disk match, filename carrying today's date. `SENT_TODAY=0`,
  `TO_HEADER=kstapp@sctoyota.com`. Note again her build reply vs PARTS reply disagreed on
  the HTML part size (177,575 vs 131,451) — the familiar two-reports-of-the-same-part
  discrepancy, both pass, not a duplicate signal.
  **Confirmed again 2026-08-29 (19th consecutive clean night) — NEW TRAP: MISSPELLED
  ATTACHMENT FILENAME (content perfect, name wrong):** OPS probe 200 (same validated RO/job
  pair, unchanged since 8/3); no same-day index pre-run; no competing consumer. Index 4,240
  closed ROs (up only 26 from 8/28's 4,214 — light Saturday), 1,393 candidates, 0 failed,
  ~53 min (19:01→19:54). Window end advanced 1787986799999 → 1788073199999 and index grew
  579,593 → 583,458 B (both fresh-index confirmations); id diff new: 26, dropped: 0.
  365 alignments (331 dedicated + 34 bundled), 365 ROs, 16 advisors. **Chris Mai extends his
  solo #1 to 43** (Jaime Sanchez 39; Artist Battle and Cristian Gonzalez tied 35).
  **The new trap:** Stacey's build was clean on the FIRST ask (60s) and every size check
  passed — but the PDF ATTACHMENT FILENAME came back
  `SCT-A**ll**ignment-By-Advisor-MTD-2026-08-29.pdf` (double L). Confirmed real, not a reply
  typo, by re-asking for `PDF_DECODED_BYTES` + `FILENAME_EXACT` in one line: bytes were an
  exact on-disk match (338,883) while the filename still read "Allignment". So the note-25
  filename check is not only an anti-stale-attachment signal — **it also catches cosmetic
  misspellings in the name Kevin actually sees when he opens the mail.** Always read the
  filename character-by-character, don't skim it; "Alignment" vs "Allignment" is easy to miss.
  Fix recipe (worked in ONE 90s ask, no duplicates): tell her to imap.append() ONE fresh
  draft identical to the current '(through 8/29)' one but with the correct filename, then
  DELETE the misspelled one — and **explicitly scope-fence the other nights**: "there are 16
  other SCT Alignment drafts (through 8/14 to 8/28) plus a July one, leave every one of them
  alone, only the '(through 8/29)' one is in scope." Without that fence a delete instruction
  risks her trimming Joe's review backlog. Post-fix enumeration returned TOTAL_MATCHES=17
  (unchanged from before the fix) with exactly one "(through 8/29)" — proving the old copy
  was replaced, not added, and no prior night was touched. Final parts:
  `RAW_SIZE=645,926 | text/plain=530 text/html=180,554 application/pdf=463,736 |
  PDF_FILENAME=SCT-Alignment-By-Advisor-MTD-2026-08-29.pdf | TO_HEADER=kstapp@sctoyota.com |
  SENT_TODAY=0` — HTML clears PNG*4/3 (131,224) with heavy-signature headroom, PDF part
  +2.6% CRLF variance over PDF*4/3 (451,844). Note her build-confirmation HTML part
  (131,943, a 719-byte tight pass) vs the PARTS ask (180,554) disagreed again — the familiar
  two-reports-of-the-same-part discrepancy, both pass. Underscore-stripped keys again.
  **Recommended final verify ask going forward:** fold `PDF_FILENAME` into the PARTS ask
  every night (RAW_SIZE | PARTS | PDF_FILENAME | TO_HEADER | SENT_TODAY) — one round-trip
  that catches stale attachments, misspelled filenames, wrong recipients and accidental
  sends at once.
  **Confirmed again 2026-08-30 (20th consecutive clean night, final full day of August):**
  OPS probe 200 (same validated RO/job pair, unchanged since 8/3); no same-day index pre-run;
  no competing consumer. Index 4,286 closed ROs (up 46 from 8/29's 4,240 — light Sunday),
  1,409 candidates, 0 failed, ~53 min (19:01→19:54). Window end advanced 1788073199999 →
  1788159599999 and index grew 583,458 → 589,909 B (both fresh-index confirmations); id diff
  new: 46, dropped: 0. 376 alignments (340 dedicated + 36 bundled), 376 ROs, 16 advisors.
  **Chris Mai solo #1 with 45** (Jaime Sanchez 42, Cristian Gonzalez 36, Artist Battle 35).
  Stacey's build clean on the FIRST ask (89s) with paths + on-disk sizes baked in: HTML part
  132,155B cleared PNG*4/3 (131,398) by only **757 bytes** (another tight pass = PASS, note 13),
  PDF part 345,219B an EXACT on-disk match.
  **Verify sequencing that worked best (use this order going forward):** (1) run the date-free
  SUBJECT+DATE enumeration FIRST rather than any DRAFTS_COUNT ask — it returned 18 matches, one
  per night 8/14→8/30 plus the July leftover, with exactly ONE "(through 8/30)", proving
  no-duplicate in a single 58s round-trip and completely sidestepping the note-26/note-28
  false-count trap (no DRAFTS_COUNT ask was needed at all tonight). (2) Then the combined
  5-field final ask — which TIMED OUT (exit 124) as usual when it bundles RAW_SIZE+PARTS+
  PDF_FILENAME+TO_HEADER+SENT_TODAY. Per note 11, a 60s pause then **two two-field asks**
  answered cleanly: `PDF_FILENAME | PDF_DECODED_BYTES` → correct spelling
  `SCT-Alignment-By-Advisor-MTD-2026-08-30.pdf` (checked character-by-character for the
  note-29 "Allignment" trap) with decoded bytes 345,219 = exact on-disk; then
  `TO_HEADER | SENT_TODAY` → `kstapp@sctoyota.com | 0`. **Two-field asks are the reliable
  granularity** — five fields times out, one field works but wastes round-trips.
  Underscore-stripped keys again throughout.
  **Confirmed again 2026-08-16 (6th consecutive clean night, quota fully healthy):**
  pre-flight OPS probe (same validated RO/job pair) returned 200. Index built 2,364
  closed ROs, 771 candidates, 0 failed, ~30 min scan (19:01→19:31, no backoff
  triggered). 221 alignments (199 dedicated + 22 bundled), 221 ROs, 16 advisors, top
  Cristian Gonzalez (28). Stacey's build completed clean on the FIRST ask (~138s)
  with file path + on-disk byte sizes baked in. Verify used the standard two-ask
  minimal set: subject-substring-anchored DRAFTS_COUNT/TO/SENT_FOLDER_COUNT (clean:
  1/kstapp@sctoyota.com/0) then a PARTS ask — PDF part 266,726B exact byte match to
  file; HTML part 128,131B >= PNG*4/3=127,280B. Note: the PARTS ask reported "3
  drafts match that substring" — these were 3 DIFFERENT NIGHTS' drafts (8/14, 8/15,
  8/16, all with distinct through-dates in the subject), not duplicates of the same
  night; the earlier DRAFTS_COUNT=1 (dated-today filter) already confirmed only one
  draft for tonight specifically. Don't confuse a multi-night substring match with
  same-night duplication — check the through-date in each match before assuming a
  dedupe is needed.
  **Confirmed again 2026-08-15 (5th consecutive clean night, quota fully healthy,
  no dedupe needed):** pre-flight OPS probe (same validated RO/job pair) returned 200
  before launching — good habit to keep even on a healthy streak. Index built 2,272
  closed ROs, 749 candidates, 0 failed, ~28 min scan (19:01→19:29, no backoff
  triggered). 206 alignments (184 dedicated + 22 bundled), 206 ROs, 16 advisors, top
  Cristian Gonzalez (26). Stacey's build completed clean on the FIRST ask (~122s) with
  file paths + on-disk byte sizes baked in per 07-22 prevention — no rebuild needed.
  Skipped the generic 5-field verify per note 15 and went straight to a
  subject-substring-anchored ask ("DRAFTS_COUNT=1 | TO=kstapp@sctoyota.com |
  SENT_FOLDER_COUNT=0") — clean, single draft, no duplicate-UID trap this time (unlike
  8/14). Final PARTS check: HTML part 129,442B >= PNG*4/3=128,704B (inline PNG
  confirmed); PDF part 259,684B is an EXACT byte-for-byte match to the on-disk PDF file
  size (strongest possible confirmation per note 14). Two-ask verify (subject-anchored
  count/recipient, then PARTS/RAW_SIZE) is now reliably sufficient — no need to run the
  older combined 5-field ask at all on a healthy night.
- **OVERALL_QUOTA exhaustion (hit 2026-07-07):** distinct from OVERALL_RATELIMIT — this is
  the store's DAILY API quota being fully spent (other pipelines, e.g. a TOL backfill loop +
  caliber-ops scrapers, can burn it). EVERY call 429s
  (`Limit exhausted for type : OVERALL_QUOTA`) for HOURS (observed 20:12 PDT → past 05:35
  next morning). No amount of in-run backoff fixes it; the nightly report cannot ship on
  time. Playbook: patch backoffs to also match "OVERALL_QUOTA", then deploy the self-heal
  pair `selfheal_sct_align_20260707.sh` (probe every 10 min → on 200 run scan+render) +
  `selfheal_sct_align_handoff_watch.sh` (waits for "render exit=0 — DONE" in the selfheal
  log → runs `selfheal_sct_align_handoff.py` which verifies the JSON and asks Stacey for the
  DRAFT-ONLY Kevin email with all trap language baked in). Logs in
  `data/sct-align-selfheal-*.log` / `data/sct-align-handoff-*.log`. Both scripts have
  flock guards + deadlines — adjust LOG/LOCK/DEADLINE lines when reusing.
  **Reuse notes (2026-07-08, second consecutive quota night):**
  - `selfheal_sct_align_handoff.py` is DATE-AGNOSTIC (reads `sct-mtd-latest-align-by-advisor.json`,
    globs newest PNG/PDF, derives subject from period_label) — reuse untouched. Only the two .sh
    wrappers need new dated copies with fresh LOG/LOCK paths.
  - **Fast diagnosis:** don't wait on a silent scan. If the background scan shows ZERO output after
    a couple minutes, DO NOT kill it yet — probe quota in a SEPARATE call first:
    `O.call('POST','/repair-orders:search',{filters:[status IN CLOSED],pageSize:1})` — a 429 body
    with `OVERALL_QUOTA` confirms exhaustion in seconds; a 200 means the scan is fine, just silent.
    (2026-07-11: even WITH `python3.11 -u`, the Hermes process log showed ZERO lines for the entire
    ~13-min run — all output appeared only at exit. `-u` does NOT guarantee live output in the
    process pipe. HEALTHY-SCAN tells while the pipe is silent: probe returns 200, AND the data files
    are moving — `data/sct-mtd-<date>-closed-index.json` appears after pass 1 and the checkpoint
    `data/sct-mtd-<date>-align-scan.json` mtime advances every ~20 ROs. Check mtimes before assuming
    a dead scan; killing a healthy run wastes the checkpoint pacing.)
  - **Launch trap:** Hermes rejects shell background wrappers (setsid/nohup/&) AND aborts the whole
    combined command — so a `chmod +x && setsid ...` line leaves the scripts non-executable (exit 126
    on the next try). chmod in its own foreground call, then launch each watcher with
    terminal(background=true). Verify both alive via the log's "watcher started" line + pgrep count.
  -  **Quota can stay dead >24h:** the 2026-07-08am self-heal probed 05:35→18:42 (13h, all 429) and
  TIMED OUT — the through-7/7 draft never shipped. Other queued recovery pipelines (BC/TOL/BT
  `quota_recovery_runner.sh`, caliber-ops) burn the bucket the moment it refills. If a self-heal
  times out, ESCALATE the quota-hog problem to Joe rather than just re-arming watchers — two
  consecutive missed nightly drafts means the systemic consumer needs to be found/paced or the
  Tekion limit raised. When quota restores after midnight, the MTD scan window auto-extends to the
  new "today" — acceptable; the subject/period label self-adjusts.
  **PRIORITIZE the nightly over the quota hogs (2026-07-09, THIRD consecutive quota night —
  outage continuous since 7/07 14:12, ~53h):** re-arming a self-heal alone loses the refill race —
  the queued backfill runners grab the bucket first. Fix: at self-heal launch, **SIGSTOP the
  competing consumers** (`pgrep -af "quota_recovery|bt_seed_watcher"` → `kill -STOP <pids>`;
  a runner holding `/tmp/tekion-quota-recovery.lock` also freezes anything flock-waiting behind
  it, e.g. `sct_closed_backfill_runner.sh` — good). Then bake `trap resume_paused EXIT` into the
  self-heal .sh (`kill -CONT` each paused pid, logged) so they resume automatically no matter how
  the scan exits — never leave processes stopped. Set the probe deadline LONG (21h) to cover a
  mid-day refill. STILL escalate the systemic issue to Joe in the same report (options: pace the
  backfill queue / drop stale backfill days / ask Tekion to raise OVERALL_QUOTA) — the pause trick
  is triage, not the fix.
- **THE 429 TRAP (hit 2026-07-01):** `sct_menu_sales_api.call()` returns a **STRING**
  body on any non-200 (e.g. `{"message":"Limit exhausted ... OVERALL_RATELIMIT"}`), NOT
  a dict. Any `.get()` on it throws `'str' object has no attribute 'get'` and the scan
  dies. The `_get()` helper MUST guard `isinstance(body, dict)` and, on a string body
  containing `OVERALL_RATELIMIT`, back off HARD (`60*(att+1)`s). Regular 429/0/5xx →
  `12*(att+1)`s. Inter-RO pacing `time.sleep(0.5)`. Checkpoint every 20 ROs so a mid-run
  failure resumes (`data/sct-<period>-align-scan.json`), plus a serial retry pass for the
  failed set, and `failed[]` in the output so truncation can't hide.
- **Classify each op:** DEDICATED if opcode in {ALIGN,OKAL,ALIGN00BRA}; BUNDLED if
  opcode starts `TEK` AND story (`" ".join(corrections[].text)` + opcodeDescription,
  lowercased) contains "align".
- **Advisor:** `assignee.advisor.id` is FREE on the search result (no fan-out) → resolve
  via `O.user_name(aid)` (public OpenAPI `/users/{id}`). No browser needed.
- **Output JSON is SELF-CONTAINED:** `rows[]` each `{advisor, dedicated, bundled, total,
  ros, detail[]}` where each detail = `{ro, opcode, kind}`; plus `totals` + `chip_total`.
  VERIFY `chip_total == totals.total` (sum of chips == total alignments) before shipping.

## Render + verify
Renderer = Toyota-red (#EB0A1E) header with the real Toyota logo (`logo_0.png`), 2 pages:
- **Page 1** (PNG, inline in email): 4 KPI cards (Total Alignments / Unique ROs / Advisors
  / Daily Pace) + ranked advisor table (Dedicated, Bundled, Total, ROs, red bar) + TOTAL row.
- **Page 2** (PDF only): RO-level chips per advisor — red chip = dedicated, blue = bundled.
  Per-advisor header count line uses `r['total']` labeled "N ROs" (matches page-1 bar total).
- PNG = page-1 only; PDF = full 2-page. ALWAYS `vision_analyze` the PNG and confirm the
  TOTAL row matches the KPI total before shipping. (Small dataset PNGs read fine full-page;
  for a very tall table crop the top band and 2x-upscale like the menu-sales skill.)

## Verified result (June 2026 full month, 2026-07-01)
516 alignments (469 dedicated + 47 bundled) across 510 ROs, 19 advisors. Jon Vu #1 (110),
Alex Anderson (50), William Dominguez & Cristian Gonzalez (39). chip_total == total == 516,
0 failed. Joe called it "perfect."

## Email via Stacey — DRAFT by default
Files land in `/home/itadmin/tekion-reports/data/`:
`SCT-Alignment-By-Advisor-<period>.png` + `.pdf`. Hand to Stacey via
`timeout 170 ~/bin/ask-agent stacey "..."`. Format = the joe-email-jay-report base64
inline-PNG layout: greeting / summary line with the total BOLD / **PNG inline IN THE MIDDLE**
/ "Sent from Tekion Open API — live data" / Joe's HTML signature. Attach the PDF by full path.

Recipients (task-spec wins over defaults):
- **Daily MTD report → TO Kevin Stapp (kstapp@sctoyota.com), greeting "Kevin,"** (Joe's
  standing instruction 2026-07-01: nightly 7pm MTD-closed alignment report to Kevin).
- A one-off "drafted for Joe to review" → TO jcastelino@americanmotorscorp.com, "Joe,".

### ⚠️ STACEY DRAFT-ONLY TRAP (hit HARD 2026-07-01 — read before every handoff)
Joe asked for a DRAFT; Stacey's rebuild/retry loop tripped her SMTP/X-GM-RAW **send** path
and SENT 7 copies, the newest addressed to Kevin via her hardcoded "SCT report → Kevin"
default — instead of leaving a draft. To DRAFT-ONLY safely:
1. Give an EXPLICIT hard stop: "Create the draft via imap.append() to Drafts ONLY. DO NOT
   call any send/SMTP/X-GM-RAW path. DO NOT send." State the exact TO + greeting and tell
   her to override any hardcoded recipient default.
2. Her FIRST build often MISSES the inline PNG (`INLINE_PNG=no`) even when the PDF attaches
   — explicitly demand a base64 data-URI `<img>` inline in the MIDDLE of the body (NOT CID —
   CID shows broken in Gmail draft view).
3. Do NOT ask her to "rebuild" in a way that re-fires her send pipeline. If a build is wrong,
   tell her to create ONE fresh draft via imap.append() and delete the bad one — still no send.
4. Verify with a TERSE one-line read-only ask (verbose multi-field asks silently time out →
   empty): `TO=<addr> | INLINE_PNG=<y/n> | PDF=<y/n> | IN_DRAFTS=<y/n> | SENT=<y/n>`.
   An empty reply is a timeout, NOT proof of failure — re-ask the same question shorter.
   This applies to ACTION asks too (hit 2026-07-04): a delete-duplicates ask returned
   exit 124/empty but HAD completed — confirm with a fresh read-only count, don't re-fire
   the action blindly.
5. **NO EMOJI in the ask-agent message** (hit 2026-07-04): characters like ⚠️ contain
   Unicode variation selectors and trip the terminal security scanner
   (`tirith:variation_selector`), blocking the command for approval — fatal in a headless
   cron run. Use plain text like "HARD STOP:" instead.
6. **Check DRAFT_COUNT** (hit 2026-07-04): her fix-the-PNG rebuild leaves the old bad
   draft(s) behind — 4 drafts piled up. After the fresh draft verifies good, ask her
   (read-only count first) and have her DELETE duplicates, keeping only the newest good
   one. Final state must be DRAFT_COUNT=1 | SENT=no. (2026-07-05: even a single clean
   build produced DRAFT_COUNT=2; 2026-07-14: a single clean first-try build produced
   DRAFT_COUNT=3 — duplication is the NORM, not the exception. ALWAYS count + dedupe
   even when everything verified good on the first ask.)
7. **INLINE_PNG false-negative** (hit 2026-07-05): a generic "PNG=<y/n>" ask can come
   back `PNG=n` even when the draft is CORRECT — she checks MIME *attachments*, and a
   base64 data-URI `<img>` lives in the HTML body, not as an attachment. Before
   rebuilding anything, verify with the precise body check:
   "Does the HTML body contain an <img> with data:image/png;base64? Reply:
   DATAURI_IMG=<y/n>". Only rebuild if DATAURI_IMG=n. This avoids destroying a good
   draft over a shallow read.
8. **DATAURI check can false-negative EVEN on the precise raw-MIME ask** (hit
   2026-07-06): after a rebuild whose own confirmation said DATAURI_IMG=y, a
   follow-up "fetch raw MIME, does html contain 'data:image/png;base64'" ask still
   came back false. Definitive tiebreaker = SIZE MATH, which needs no substring
   check at all: ask read-only "Reply one line: RAW_SIZE=<RFC822.SIZE> |
   HTML_SIZE=<bytes of text/html part>".   base64 inflates ~4/3, so
   HTML_SIZE ≈ PNG_bytes * 4/3 (+ a few KB of text) proves the inline image is
   embedded (e.g. 84,756-byte PNG → ~113,008 b64 vs HTML_SIZE 113,603 — match).
   **Treat it as a LOWER BOUND, not an equality** (2026-07-12): Joe's HTML
   signature can add ~48KB of extra HTML (96,338-byte PNG → expected ~128,451
   b64, actual HTML part 176,638 — still a GOOD draft). Pass condition:
   HTML_SIZE >= PNG_bytes*4/3; only a few-KB HTML part means the PNG is missing.
   PDF part likewise runs ~2.5% over PDF_bytes*4/3 from base64 CRLF line-wrapping
   (239,206-byte PDF → 327,338 part — normal).
   RAW_SIZE ≈ HTML_SIZE + PDF_bytes*4/3 cross-checks the attachment. If HTML_SIZE
   is only a few KB, the PNG is genuinely missing — rebuild then. Trust the math
   over her y/n substring answers; never rebuild a draft the math says is good.
9. **Best size-verify phrasing = per-part list** (2026-07-10): a bare
   "HTML_SIZE=<bytes>" ask once returned 595 on a draft whose HTML part was actually
   122,705 bytes. The reliable ask: "reply one line: RAW_SIZE=<RFC822.SIZE> |
   PARTS=<each MIME part content-type and size in bytes>" — e.g.
   `PARTS=text/plain=398 text/html=122705 application/pdf=226903` proves inline PNG
   (html ≈ PNG*4/3) AND the exact PDF byte size in one shot.
   NOTE (2026-07-13): PARTS sizes may come back as DECODED bytes — a clean run reported
   application/pdf=249548, exactly the raw PDF file size (not the ~4/3-inflated encoded
   size note 8 predicts). Don't false-alarm on that: a PDF part equal to the file's
   byte size is a PASS. Cross-check with RAW_SIZE ≈ HTML_part + PDF_bytes*4/3 (observed
   478,162 ≈ 130,058 + 332,731 — consistent). The HTML-part lower-bound test
   (HTML_SIZE >= PNG_bytes*4/3) is unaffected.
10. **Telegram detour** (2026-07-10): a read-only ask can come back "I sent the
   summary to your Telegram" instead of answering — the bridge gets nothing. Add
   "reply in THIS chat as plain text, do not message Telegram" to verification asks.
11. **One combined verify ask works best** (2026-07-15): merge notes 4/6/9 into a
   SINGLE read-only ask — "Reply one line: TO=<addr> | IN_DRAFTS=<y/n> | SENT=<y/n> |
   DRAFT_COUNT=<n with this subject> | RAW_SIZE=<RFC822.SIZE> | PARTS=<each MIME part
   content-type and size in bytes>". Returned everything cleanly in one round-trip;
   size math (HTML part 177,507 >= 97,980*4/3; PDF part ~+1.4% over PDF*4/3) verified
   the inline PNG + attachment without any y/n substring answers. That run was also a
   clean first-try DRAFT_COUNT=1 — rare but possible; still always check the count.
   (2026-07-17: the ultra-short re-ask form "PARTS=?" can come back as just a part
   COUNT, e.g. `PARTS=3`, not the per-part type=size list. Don't re-ask endlessly —
   RAW_SIZE alone still verifies: RAW_SIZE ≈ HTML-with-inline-PNG (~PNG*4/3 + sig)
   + PDF*4/3.   Observed 552,379 ≈ ~174K + ~378K for a 97,845 B PNG + 283,334 B PDF —
   pass. Also that night: the full note-11 combined ask timed out (exit 124) but the
   shortened one-line form answered instantly — keep the re-ask TERSE.)
   (2026-07-27: the combined ask timed out TWICE — even a moderately shortened form.
   The pattern that worked: two ultra-terse asks, each ONE line — first
   "TO=? RAW_SIZE=?" (answered instantly), then the note-12 folder search
   "SENT_FOLDER_COUNT=? DRAFTS_COUNT=?". Skipped PARTS entirely; verified via
   RAW_SIZE >= PNG*4/3 + PDF*4/3 (682,124 vs 139.6K+476.0K for a 104,691 B PNG +
   356,988 B PDF) + DRAFTS_COUNT=1/SENT_FOLDER_COUNT=0. When combined asks keep
   timing out, degrade straight to this two-ask minimal set — it is sufficient.
   Confirmed again 2026-07-28: skipped the combined ask entirely, went straight to
   the two-ask minimal set — both answered instantly, clean first-try DRAFT_COUNT=1.
   Note her reply may strip underscores ("SENTFOLDERCOUNT=0") — same answer.
   **EXACT-SUBJECT SEARCH FALSE ZERO (2026-07-31):** the folder-search ask with the
   EXACT full subject ('SCT Alignment Sales by Advisor - July MTD (through 7/31)')
   returned DRAFTS_COUNT=0 even though a prior ask had just found the draft (TO +
   RAW_SIZE answered fine). Punctuation/encoding in the subject (dashes, parens)
   can break her exact-match search. Do NOT rebuild on a zero — re-ask with a
   SUBSTRING: "Search subject substring 'SCT Alignment Sales by Advisor' (not
   exact match), only messages dated today" → came back DRAFTS_COUNT=1,
   SENT_FOLDER_COUNT=0. A zero count contradicting an earlier successful fetch is
   a search-syntax problem, not a missing draft.
   2026-07-29: two-ask minimal set clean again (first-try DRAFTS_COUNT=1, SENT=0) —
   this is now the DEFAULT verify path; don't bother with the combined ask. Also:
   (2026-07-31: even the terse two-ask forms timed out THREE times in a row right
   after the build ask — Stacey was likely still busy. A `sleep 60` before the next
   re-ask got an instant clean answer. On consecutive timeouts, pause ~60s instead
   of hammering.)
   baking file paths + on-disk byte sizes into the initial build ask (note 13
   prevention) again produced a clean one-shot draft. 2026-07-30: third consecutive
   clean first-try night with the same recipe (sizes baked into build ask + two-ask
   verify) — the pipeline is stable; treat any deviation as anomalous and re-read
   the trap notes.)

12. **SENT=y / DRAFT_COUNT FALSE ALARM in the combined ask** (hit 2026-07-23): the
   note-11 combined verify returned `SENT=y | DRAFT_COUNT=7` on a clean first-try
   build — BOTH wrong. Size math in the same reply was perfect (HTML 139,506 >=
   PNG*4/3; PDF part ~+2.6% over PDF*4/3). Tiebreaker before panicking/rebuilding:
   one terse read-only ask — "Search [Gmail]/Sent Mail for that exact subject — how
   many? Search [Gmail]/Drafts — how many? Reply: SENT_FOLDER_COUNT=<n> |
   DRAFTS_COUNT=<n>". Came back 0 | 1 → draft was fine, nothing sent, no dedupe
   needed. Her SENT flag can reflect the \\Seen/session state, and DRAFT_COUNT can
   count the whole Drafts folder, not the subject. Trust folder searches + size math
   over flag answers.
13. **ZERO-BYTE PDF PART** (hit 2026-07-21): her first build can attach the PDF as an
   EMPTY part — combined verify returned `application/pdf:0B` (and RAW_SIZE ~275K, far
   below HTML + PDF*4/3) while her own confirmation claimed the PDF was attached. The
   PARTS list is the only thing that catches this — always check the PDF part size is
   nonzero and ≈ the on-disk PDF byte size (decoded, per note 9) or ~4/3 of it. Fix ask:
   ONE fresh imap.append() draft, explicitly "read and base64-attach the PDF file bytes
   from <path> (<N> bytes on disk — verify the part is non-zero)", then delete the bad
   draft. That fix ask TIMED OUT (exit 124) but HAD completed — per note 4, re-verify
   read-only (DRAFT_COUNT went 1→2, new draft PDF_PART_BYTES=321889 exact file size)
   before re-firing, then have her delete the older 0-byte-PDF draft. Final
   DRAFT_COUNT=1 | SENT=n. Also seen that night: an image/jpeg part alongside a
   healthy-sized HTML part — the data-URI PNG lives in the HTML (size math passed);
   don't treat an extra image part as a failure.
   **PREVENTION (2026-07-22, clean first-try run):** bake the fix language into the
   INITIAL build ask — state both file paths WITH their on-disk byte sizes and say
   "read and base64-attach the actual file bytes ... verify the PDF MIME part is
   NON-ZERO and matches the file size". Night after the 0-byte trap, this produced a
   clean DRAFT_COUNT=1 with PDF part = exact on-disk size on the first ask (confirmed
   again 2026-07-25: clean first-try, DRAFT_COUNT=1, PDF part exactly file size,
   HTML part 133,546 >= PNG*4/3=132,828 — the bake-sizes-into-build-ask prevention
   is reliably producing clean one-shot drafts). Also note:
   the HTML-part lower-bound test can pass with only ~1KB headroom
   (135,136 vs PNG*4/3=134,349) when her build omits the heavy HTML signature — a
   tight pass is still a PASS.

15. **UN-ANCHORED short verify ask can return GARBLED/CROSS-CONTAMINATED data from
   OTHER stores' pending drafts** (hit 2026-08-11): a generic first-shot verify
   ("Reply ONE line: TO=? | INLINE_PNG=? | PDF=? | IN_DRAFTS=? | SENT=?" with no
   subject anchor) came back nonsense mixing unrelated stores:
   `TO=TOL | INLINEPNG=? | INDRAFTS=0 | SENT=SCT+BC (TOL missing)` — Stacey appears to
   pull from whatever draft/task context is freshest in her working memory when the ask
   doesn't pin down WHICH draft, especially if she has other stores' report drafts
   pending around the same time. Do not treat this as evidence of a failed/missing
   draft. Fix: ALWAYS anchor the verify ask with the specific subject SUBSTRING (per
   the exact-subject false-zero trap, note 11's 07-31 entry) — e.g. "Search Gmail
   Drafts for subject substring 'SCT Alignment Sales by Advisor - August MTD', dated
   today. Reply: DRAFTS_COUNT=<n> | TO=<address of newest match> |
   SENT_FOLDER_COUNT=<n>". This came back clean (DRAFTS_COUNT=1, TO=kstapp@sctoyota.com,
   SENT_FOLDER_COUNT=0) immediately after the garbled generic ask — same draft, same
   minute, opposite answer. A follow-up subject-anchored PARTS/RAW_SIZE ask then
   confirmed the inline PNG and PDF cleanly (HTML 125,348B >= PNG*4/3; PDF part exactly
   221,808B matching the file). Lesson: skip the bare 5-field generic ask entirely on
   the first verify attempt — go straight to a subject-substring-anchored ask.

14. **PDF part as application/octet-stream with AMBIGUOUS size + DECODE tiebreaker**
   (2026-07-24): the combined verify listed the PDF part as
   `application/octet-stream:387722` — content-type NOT application/pdf (don't
   false-alarm on that), and the size matched NEITHER the decoded file (344,616)
   NOR ~4/3 encoded (~459K). Same reply also had DRAFT_COUNT=8 (note-12 whole-folder
   false alarm; folder search returned SENT_FOLDER_COUNT=0 | DRAFTS_COUNT=1 — fine).
   When part sizes are ambiguous, the DEFINITIVE check is a terse read-only ask:
   "decode the PDF attachment part of the newest matching draft and give decoded
   byte count. Reply: PDF_DECODED_BYTES=<n>" — came back exactly the on-disk file
   size (344,616). Decoded-bytes-equals-file-size beats all size-math heuristics;
   use it whenever PARTS numbers don't reconcile. (The 3-question follow-up ask
   timed out exit 124; splitting into two one-line asks answered instantly — keep
   re-asks to ONE question each.)

## Cron (LIVE)
Job `25ec117cfe72` "SCT Alignment MTD Closed — nightly 7pm draft to Kevin", schedule
`0 19 * * *` (7pm Pacific), skills=[sct-alignment-by-advisor-report, agent-to-agent-bridge],
deliver=origin (status back to the Slack thread). It runs `sct_align_mtd.py` (background,
notify_on_complete), renders via `render_sct_align.py`, vision-verifies, then hands to Stacey
as a **DRAFT ONLY to Kevin (kstapp@sctoyota.com), greeting "Kevin,"** in Joe's Gmail Drafts —
Joe reviews + sends in the morning. Reset at month rollover is automatic (the MTD scan
computes 1st-of-month → today, so nothing to reset). Scan is paced — early-month it runs
~15-25 min, but LATE-MONTH the MTD window balloons (2026-07-25: 3,941 closed ROs, 1,252
candidates → ~47 min, draft ~7:50pm; 2026-07-27: 1,330 candidates → ~58 min; 2026-07-28:
2026-07-28: 4,488 closed, 1,409 candidates → ~61 min; 2026-07-29: 1,468 candidates → ~58 min;
2026-07-30: 4,914 closed, 1,539 candidates → ~55 min, clean). A 30-65 min
silent scan late in the month is NORMAL —
check checkpoint mtime (advances every ~20 ROs) before assuming it's stuck. Established
2026-07-01 on Joe's instruction.

To flip it to AUTO-SEND to Kevin later: update the cron prompt to have Stacey SEND (SMTP
template-send) instead of draft-only, and drop the DRAFT-ONLY hard-stop language.

## STALE BACKGROUND-NOTIFICATION REPLAY AFTER THE DAILY RESET (2026-08-28)
The daily ~4 AM session reset can RE-DELIVER the previous night's
`Background process ... completed (exit code 0)` message for `sct_align_mtd.py` into the
fresh morning session, making it look like a scan just finished and needs rendering +
a Stacey handoff. It does not. **Before acting on any align-scan completion notice,
check the clock and the file mtimes:**
`ls -la --time-style='+%m-%d %H:%M' data/ | grep -E 'sct-mtd-<date>|SCT-Alignment'`.
If the by-advisor JSON + PNG/PDF are already stamped ~19:50 the PRIOR evening, the run
already shipped — do NOTHING. Re-running rebuilds the whole index and burns OpenAPI
quota for identical data. Cross-check this skill's own dated confirmation notes too: if
the night in question is already written up here with matching totals, it's a replay.
**Recurred 2026-08-29 (~04:04 AM reset)** — the 8/27 run's completion message
(`TOTALS {'dedicated': 312, 'bundled': 33, 'total': 345}`) was re-delivered TWO days later,
so the replayed notice is not necessarily from the immediately-preceding night. The totals
line in the replayed message is the fastest discriminator: match it against this skill's
dated notes (8/27 = 345 / 312 + 33) — if it's already written up, it shipped. Correct
response is a one-line "stale replay, nothing to do" plus the evidence (file mtimes,
Stacey's verified `DRAFTS_COUNT=1 | TO_HEADER=... | SENT_TODAY=0`); do NOT re-render, do
NOT re-ask Stacey (a second handoff would create a duplicate draft for that night).

## COMPANION REPORT: Alignment + BG MENU SALES (built 2026-08-31, Joe's ask)
Joe asked for "total alignment sales with the BG menus." SCT has NO BG-branded alignment
opcode — BG at SCT = the BG Products chemical/fluid service line (17 opcodes seen in Aug:
BGCF, BGBFX, BGTF, BGCVTF, BGCFX, BGRDIFF, BGTC, BGATFX, BGFDIFF, BGAC, BGPSX, BGBAT,
BG208, BGETH, BGTBINJ, BGFINJ, BGMAF). So "alignment sales WITH the BG menus" = the
alignment report PLUS the BG service line, in DOLLARS not just units, with the
cross-sell attach rate (ROs carrying both).
- **Scan:** `sct_align_bg_scan.py` — REUSES that day's `sct-mtd-<tag>-closed-index.json`
  (zero extra index calls; set `TAG=YYYY-MM-DD`). Candidate set = ALIGN ∪ BG ∪ TEK.
  Captures `labor.saleAmount` + summed operation `parts saleAmount` (BOTH CENTS) per line.
  Checkpoint `data/sct-alignbg-<tag>-scan.json`, resumable, `_get()` has the mandatory
  dict-guard + OVERALL_RATELIMIT/OVERALL_QUOTA/DEALER_QUOTA hard-backoff.
- **Render:** `render_sct_align_bg.py` → 3 pages: p1 advisor ranking (align units/$, BG
  units/$, attach ROs, combined $), p2 BG product mix ranked by revenue, p3 RO-level chips
  (red=dedicated, blue=TEK-bundled, green=BG) each stamped with its dollar amount.
  Output stem `SCT-Alignment-BG-Sales-By-Advisor-<date>.{png,pdf}`.
- **NEVER run it concurrently with `sct_align_mtd.py`** — same rate-limit bucket; a
  collision breaks Kevin's nightly. `pgrep -af sct_align_mtd` must be empty first.
- Operations endpoint returns `data.roOperations` (NOT `data.operations`), and
  `O.call()` returns a `(status, body)` TUPLE — both bite immediately if you copy the
  jobs-endpoint shape. Parts are a LINK: `/repair-orders/{rid}/jobs/{jid}/operations/{oid}/parts`
  → `data.parts[].saleAmount`, one extra call per BG line.
- Aug 2026 reference scale: 5,094 closed ROs → 275 with a BG opcode, 200 of those carry
  NO align/TEK op (invisible to the alignment scan), 64 ROs sold BOTH.

## BUG FOUND + FIXED 2026-08-31 — ALIGN00**R**BA vs ALIGN00**B**RA
`ALIGN_OPC` had `ALIGN00BRA`, but the opcode SCT actually uses is **`ALIGN00RBA`** (R and
B transposed). That code appears 107 times across the July+August indexes and **ZERO**
`ALIGN00BRA` ever existed — so every one of those alignments was silently uncounted, and
in August 5 of them weren't even candidates (no ALIGN/OKAL/TEK op on the RO, so the
fan-out never looked at them). Patched all four scanners to accept BOTH spellings:
`align_scan.py`, `align_scan_june.py`, `sct_align_full_june.py`, `sct_align_mtd.py`.
Effect is small (~5/month at SCT) but it means historical alignment totals in prior
reports are LOW by the ALIGN00RBA count for that month. Lesson: derive the opcode set
from the live index (`collections.Counter` over `r['opc']`) rather than trusting a
hardcoded literal — a transposed character produces a silent zero, not an error.

## Pitfalls recap
- Opcode set is SCT-specific (ALIGN/OKAL/ALIGN00RBA — note the R-B order). Other stores differ — see
  `tekion-alignment-by-advisor-report` + `tol-alignment-by-advisor-report`.
- The `_get()` dict-guard + OVERALL_RATELIMIT hard-backoff is MANDATORY — without it the
  scan dies on a string error body.
- chip_total must equal totals.total. failed[] must be empty (or re-run — it resumes).
- DRAFT-ONLY means DRAFT-ONLY: lock Stacey's send path per the trap above.
