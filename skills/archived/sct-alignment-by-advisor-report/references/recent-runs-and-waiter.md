# Recent runs + the main-nightly waiter pattern

## 2026-09-15 — clean run, 16th of September

- Pre-flight OPS probe (same validated RO/job pair, unchanged since 8/3): **200**. Keep doing
  this probe even deep into a healthy streak — it costs one call.
  (Note: `search` with a malformed/partial query can return **400** — that is NOT a quota
  signal. Only the `/operations` endpoint status matters for the DEALER_QUOTA check.)
- No same-day index pre-run; no competing consumer (both standard pgrep sweeps empty).
- Scan 19:01→19:25 (~24 min, no backoff), 0 failed.
- **208 alignments (190 dedicated + 18 bundled), 208 ROs, 16 advisors, daily pace 13.9.**
- Top advisor **Jason Sulon solo #1 with 23** (Cristian Gonzalez 18, Artist Battle 17,
  Brian Keat & Jaime Sanchez 16, Juan Jose Perez 15).
- NO escalation needed — the September DEALER_QUOTA outage is fully resolved (9/10-9/15 all
  clean, no self-heal armed).

### Stacey verify (notes 30/31 recipe, all first-try, short sleeps 15/10/10/10s, zero timeouts)

1. Date-free SUBJECT+DATE enumeration → 26 total matches, **exactly ONE "(through 9/15)"** →
   no duplicate, no dedupe.
2. `PDF_FILENAME=SCT-Alignment-By-Advisor-MTD-2026-09-15.pdf` (correct one-L spelling) |
   `PDF_DECODED_BYTES=256386` = **exact on-disk match**.
3. `TO_HEADER=kstapp@sctoyota.com | SENT_TODAY=0`.
4. PARTS: `text/html:176134` cleared PNG*4/3 (95,990*4/3=127,987) with heavy-signature
   headroom; `application/pdf:350844` = usual +2.6% CRLF variance over PDF*4/3 (341,848);
   RAW_SIZE 528,686 ≈ html+pdf. Container parts (`multipart/mixed:100`,
   `multipart/alternative:100`) are structural, NOT the zero-byte-PDF trap.
- Build ask was clean on the FIRST ask (93s). On-disk sizes: PNG 95,990 / PDF 256,386.

## 2026-09-16 — clean run, zero traps, zero escalations

- Pre-flight OPS probe **200** (quota healthy; September DEALER_QUOTA outage fully resolved,
  no self-heal armed). No same-day index pre-run; no competing consumer.
- Scan 19:01→19:29 (~27 min, no backoff), **0 failed**.
- **233 alignments (213 dedicated + 20 bundled), 233 ROs, 16 advisors, daily pace 14.6.**
- Top advisor **Jason Sulon solo #1 with 27** (Robin Porter / Juan Jose Perez / Cristian
  Gonzalez 20, Artist Battle 18).
- **PROBE HELPER NAMING GOTCHA:** the module-level entry point in `sct_menu_sales_api` is
  `call(method, path, payload=None)`; `sct_align_mtd.py` imports the module as `O`, so its
  internal calls read `O.call(...)` — but from a standalone `python3 -c` snippet you must do
  `import sct_menu_sales_api as O; O.call('GET', '/repair-orders/<rid>/jobs/<jid>/operations')`.
  There is no `O.O`. First attempt tonight failed with
  `module 'sct_menu_sales_api' has no attribute 'O'`.
- Waiter pattern (per "DON'T BABYSIT THE MAIN NIGHTLY" below) worked perfectly: scan bg +
  `wait_render_<mmdd>.sh` bg, waited only on the waiter, render fired automatically at scan
  exit (exit=0). No manual render step needed.

### Stacey verify (notes 30/31 recipe, all first-try, short sleeps 15/10/10/10s, zero timeouts)

1. Build ask clean on the FIRST ask (133s): `DRAFTSCOUNT=1 | PDFPARTBYTES=363884 | DATAURIIMG=y`.
2. Date-free SUBJECT+DATE enumeration → 21 total matches, **exactly ONE "(through 9/16)"**
   dated today → no duplicate, no dedupe. (The other 20 are Joe's unsent August backlog + the
   July MTD leftover — expected, not a fault.)
3. `PDFFILENAME=SCT-Alignment-By-Advisor-MTD-2026-09-16.pdf` (correct one-L spelling, carries
   today's date) | `PDFDECODED_BYTES=269241` = **exact on-disk match**.
4. `TOHEADER=kstapp@sctoyota.com | SENTTODAY=0`.
5. PARTS: `RAW_SIZE=546413 | multipart/mixed=368436, multipart/alternative=176868,
   text/plain=592, text/html=176276, application/pdf=368436`. HTML part 176,276 cleared
   PNG*4/3 (96,195*4/3=128,260) with the usual heavy-signature headroom; PDF part 368,436 is
   the normal +2.6% CRLF variance over PDF*4/3 (358,988); RAW_SIZE ≈ html+pdf (544,712).
   Container parts are structural, NOT the zero-byte-PDF trap.
- On-disk sizes: PNG 96,195 / PDF 269,241. Her build confirmation's PDF part (363,884) vs the
  PARTS ask's (368,436) differ slightly — the familiar two-reports-of-the-same-part
  discrepancy, both pass, not a duplicate signal.

## 2026-09-17 — clean run, quota healthy, no self-heal needed

- Pre-flight OPS probe on the same validated RO/job pair (unchanged since 8/3): **200** at
  19:01 PDT. No same-day index pre-run (no stale-index trap). A caliber-ops
  `run-scraper.ts` WAS running — left alone per the 8/31 lesson because the OPS probe was
  clean (a competitor only matters when the probe is 429). No `sct_align_mtd` competitor.
- Scan 19:02→19:30 (~28 min, checkpoint mtime advancing throughout, no backoff), **0 failed**.
- **247 alignments (225 dedicated + 22 bundled), 247 ROs, 16 advisors, daily pace 14.5.**
- Top advisor **Jason Sulon solo #1 with 30** (Cristian Gonzalez 22, Juan Jose Perez 21,
  Robin Porter / Artist Battle tied 20). `chip_total == totals.total == 247`, `failed=[]`.
- PNG vision-verified: TOTAL row 225/22/247/247 matches the KPI card, Toyota logo present,
  16 real human names.
- **Launch pattern refinement (best so far):** a single self-contained
  `run_sct_align_nightly_<date>.sh` that does scan→render in ONE flock-guarded background
  process, plus a foreground `tail --pid=<pid> -f /dev/null` with `timeout=590` to block on it.
  Cost ~3 iterations total for a 28-min scan (vs ~10-18 clamped `process wait` calls). The
  waiter renders automatically at scan exit; no manual render step. Preferred going forward.

### Stacey verify (notes 30/31 recipe, all first-try, sleeps only 15/10/10s, zero timeouts)

1. Build ask clean on the FIRST ask (74s) with paths + on-disk sizes baked in:
   `DRAFTUID=43508 | HTMLPARTBYTES=127418 | PDFPART_BYTES=276825`.
   HTML part cleared PNG*4/3 (94,974*4/3=126,632) by only **786 bytes** — a tight pass, still
   a PASS (note 13). PDF part = **exact on-disk match**.
2. Date-free SUBJECT+DATE enumeration FIRST → 10 total matches, **exactly ONE
   "(through 9/17)"** dated today → no duplicate, no dedupe, no DRAFTS_COUNT ask needed.
   (The other 9 are Joe's unsent backlog: 9/16, the August Final CORRECTED, and August
   nightlies 8/25-8/31 — expected, not a fault.)
3. `PDFFILENAME=SCT-Alignment-By-Advisor-MTD-2026-09-17.pdf` (correct one-L spelling,
   carries today's date) | `PDFDECODED_BYTES=276825` = **exact on-disk match**.
4. `TOHEADER=Kevin <kstapp@sctoyota.com> | SENTTODAY=0`.
- On-disk sizes: PNG 94,974 / PDF 276,825. Draft-only respected, nothing sent.

## DON'T BABYSIT THE MAIN NIGHTLY — the `tail --pid` waiter + render

The alignbg section already forbids agent-babysat scans (the iteration ceiling silently kills
the render/email tail — see the 2026-09-01 incident). **The MAIN nightly `sct_align_mtd.py`
has the same exposure** and the task prompt's "run background + wait" wording invites it:
`process(action='wait')` is **clamped to 180s**, so a 25-55 min scan costs ~10-18 wait
iterations, and exhausting the turn loop before the Stacey handoff means Joe wakes up to
nothing.

**Reusable fix (used 2026-09-15):** launch the scan as a background process
(`terminal(background=true, notify_on_complete=true)`), then immediately launch a small
background shell that blocks on the scan PID and runs the render itself:

```bash
#!/usr/bin/env bash
# wait_render_<mmdd>.sh
set -u
cd /home/itadmin/tekion-reports
PY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3
SCANPID=<pid from the scan launch>
LOG=data/_wait_render_<mmdd>.log
echo "=== waiter started $(date '+%F %T') on pid $SCANPID ===" >> "$LOG"
tail --pid=$SCANPID -f /dev/null 2>/dev/null    # blocks until the scan exits
echo "$(date '+%F %T') scan pid exited" >> "$LOG"
sleep 3
$PY -u render_sct_align.py >> "$LOG" 2>&1
echo "$(date '+%F %T') render exit=$? ===" >> "$LOG"
```

Launch the waiter the same way (`terminal(background=true, notify_on_complete=true)`) and wait
only on it — it exits (code 0) the moment the scan finishes, so one long-gap `wait` gets you a
rendered PNG/PDF with no manual render step.

**Even better (2026-09-17):** skip the separate waiter and wrap scan→render in ONE
flock-guarded script:

```bash
#!/usr/bin/env bash
# run_sct_align_nightly_<YYYYMMDD>.sh
set -u
cd /home/itadmin/tekion-reports
PY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3
LOG=data/_sct_align_nightly_<YYYYMMDD>.log
exec 9>/tmp/sct-align-nightly-<YYYYMMDD>.lock
flock -n 9 || { echo "already running" >> "$LOG"; exit 1; }
echo "=== runner started $(date '+%F %T') ===" >> "$LOG"
$PY -u sct_align_mtd.py >> "$LOG" 2>&1
RC=$?
echo "$(date '+%F %T') scan exit=$RC" >> "$LOG"
[ $RC -ne 0 ] && { echo "SCAN FAILED rc=$RC"; exit $RC; }
$PY -u render_sct_align.py >> "$LOG" 2>&1
echo "$(date '+%F %T') render exit=$? ===" >> "$LOG"
```

Launch with `terminal(background=true, notify_on_complete=true)`, then block in the foreground
with `tail --pid=<pid> -f /dev/null` at `timeout=590` (re-issue if it returns 124). This costs
~3 iterations for a 28-min scan and cannot be killed by the iteration ceiling.

**Healthy-scan tells while the waiter is silent** (the scan's own stdout is buffered and may
show nothing until exit — do NOT kill it):
- `data/sct-mtd-<date>-closed-index.json` appears after pass 1.
- `data/sct-mtd-<date>-align-scan.json` checkpoint mtime advances every ~20 ROs
  (observed 21,963 → 58,694 B over ~10 min on 9/15; 38,056 → 77,407 B on 9/17).
- The OPS probe returns 200.

The waiter needs no cleanup and is harmless to leave on disk.
