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
echo "$(date '+%F %T') render exit=$?" >> "$LOG"
```

Launch the waiter the same way (`terminal(background=true, notify_on_complete=true)`) and wait
only on it — it exits (code 0) the moment the scan finishes, so one long-gap `wait` gets you a
rendered PNG/PDF with no manual render step.

**Healthy-scan tells while the waiter is silent** (the scan's own stdout is buffered and may
show nothing until exit — do NOT kill it):
- `data/sct-mtd-<date>-closed-index.json` appears after pass 1.
- `data/sct-mtd-<date>-align-scan.json` checkpoint mtime advances every ~20 ROs
  (observed 21,963 → 58,694 B over ~10 min on 9/15).
- The OPS probe returns 200.

The waiter needs no cleanup and is harmless to leave on disk.
