---
name: tekion-report-cron-self-contained-runner
description: Build any long-running (>20 min) Tekion report cron as a self-contained shell runner (scan -> render -> email in ONE flock'd process) instead of an agent-babysat background job. Use when creating a new report cron, when a report "ran but Joe got no email", or when a cron's data landed on disk but the render/email tail never executed. Includes the recovery drill for orphaned scan JSON.
triggers:
  - report ran but no email
  - cron finished but nothing shipped
  - new tekion report cron
  - scan completed but report never sent
  - report cron died mid-run
  - orphaned scan json
---

# Long-Running Tekion Report Crons: Self-Contained Runner Pattern

## THE FAILURE THIS PREVENTS (real, cost Joe a morning)

**2026-09-01, SCT Alignment + BG report, first run of cron `733827598a50`:**
The cron launched `sct_align_bg_scan.py` with `terminal(background=true)` and then sat in
`process(action='wait')` loops waiting for it. The scan ran **2 hours** and finished
PERFECTLY at 23:19 — 5,094 closed ROs, 1,798 candidates, 0 failures, correct totals
written to `data/sct-alignbg-2026-08-31-by-advisor.json`.

**The render and email never ran.** Every 180-second `wait` timeout burned one agent
iteration; the session hit its ceiling and ended while the scan was still going. The tail
of the job — render, vision-verify, email — was simply never reached.

Joe woke up to nothing and asked *"were you able to finish this report?"* The data had been
sitting complete on disk for **7 hours**. Nothing errored. Nothing alerted. `last_status`
on the cron said **`ok`**.

**Why this is insidious:** the scan succeeding is what kills you. A crash would leave a
traceback. This leaves a perfect data file and a silent, statusless nothing.

## THE RULE

> **An agent turn loop must never be the thing that keeps a long job alive.**
> Anything over ~20 minutes goes in a shell script that runs scan → render → email as ONE
> process. Launch it, post one status line, and STOP. Do not poll.

If the agent session dies one millisecond after launch, the email must still go out.

## PATTERN — the runner

Reference implementation: `/home/itadmin/tekion-reports/run_sct_alignbg.sh`
Template: `templates/run_report.sh` in this skill.

Key properties (all mandatory):
1. **One process, three stages.** scan → render → email chained with `&&`/guards in shell,
   never orchestrated across agent turns.
2. **`flock` guard** on its own lock (`/tmp/<report>.lock`, fd 9, `flock -n` → exit 0 if
   already running). Prevents a retry/overlap from double-emailing.
3. **Its own log** at `data/_<report>_run.log`, every stage timestamped, so a post-mortem
   needs zero agent context.
4. **Fail loudly per stage** — if the scan produces no JSON path, `exit 1` and say so in
   the log. Don't let a missing file silently reach the emailer.
5. **Email via `jay_mail.send_report`** (SMTP + CID inline PNG). No Stacey handoff — that
   removes an entire class of traps (the SCT alignment skill has ~29 documented Stacey
   verification traps; a direct-send report inherits none of them).

### Launch it like this
```
terminal(background=true, notify_on_complete=true,
         command="/usr/bin/bash /home/itadmin/tekion-reports/run_<report>.sh")
```
Then post ONE line ("launched, ~60 min, will report on completion") and end the turn.
`notify_on_complete` surfaces the result — polling adds nothing but iteration burn.

**Pitfall:** use explicit `/usr/bin/bash`, never bare `bash` — the background launch
wrapper can reinterpret plain `bash script.sh` under dash and blow up on `$(...)`.
Always `bash -n script.sh` before first launch.

## RECOVERY DRILL — scan JSON on disk but no email went out

This is the exact situation you'll walk into the morning after. **Do NOT re-scan** — it
burns OpenAPI quota (and per-dealer DEALER_QUOTA) for data you already have, and can take
hours. Render + email the existing file. Takes ~30 seconds.

```bash
cd /home/itadmin/tekion-reports
PY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11
ls -lt data/ | head            # find the orphaned by-advisor JSON + its tag
$PY render_<report>.py data/<report>-<tag>-by-advisor.json
$PY <report>_email.py data/<report>-<tag>-by-advisor.json \
     data/<Stem>-<tag>.png data/<Stem>-<tag>.pdf
```

Then `vision_analyze` the PNG before/after — confirm branding + that the TOTAL row matches
the KPI cards (logo trap: `logo_0.png` AND `logo_st.png` are BOTH Stevens Creek Toyota;
correct only for SCT).

**Triage order when Joe says "did the report go out?":**
1. `ls -lt <data dir>` — is there a scan JSON / PNG / PDF, and what's the mtime?
2. If JSON exists but no PNG/PDF → died before render. Recovery drill above.
3. If all three exist but no email → died before send. Run just the emailer.
4. Only if NO scan JSON exists do you re-run the scan.
5. Read the cron's session transcript to confirm the failure mode (see below) — a
   `last_status: ok` cron that shipped nothing is the signature of this bug.

### Reading the cron transcript for the tell
```python
import json
d = json.load(open("/home/itadmin/.hermes/profiles/jay/sessions/session_cron_<job>_<ts>.json"))
for m in d["messages"][-12:]:
    print(m.get("role"), str(m.get("content"))[:300])
```
Signature: a trailing run of `{"status": "timeout", ..., "Waited 180s, process still
running"}` tool results with empty assistant messages between them, and no final summary.
That's the iteration ceiling, not a scan failure.

## WRITING THE CRON PROMPT

The prompt itself must forbid babysitting, or a future run will reinvent it. Include:
- The one-command launch, verbatim.
- **"After launching, post a one-line status and STOP. Do not poll in wait loops."**
- A one-sentence statement of why (the 2026-09-01 incident) — future-you needs the reason,
  not just the rule, or it gets "optimized" away.
- The recovery-mode block, verbatim, so a re-run never re-scans.
- Any preflight serialization (e.g. `pgrep -af sct_align_mtd` must be empty — Kevin's 7 PM
  nightly owns the rate-limit bucket and has priority).

## WHERE THIS APPLIES

Any AMG report whose scan exceeds ~20 min. Late-month MTD windows balloon badly — SCT
alignment runs 15-25 min early month and **63 min** on the 31st. Candidates: SCT
alignment/align+BG, SCT & BC & TOL & BT menu sales closed MTD, BC deferred-by-advisor,
part-sales ledger bisection scans, AMG WIP engine pulls, fleet advisor-gross scans.

**Audit trigger:** if a report cron's prompt contains `process(action='wait')`,
"wait for it to finish", or launches a scan and then continues doing work in the same
agent session — it has this bug latent. Convert it.

## RELATED

- `sct-alignment-by-advisor-report` — the SCT-specific instance (its "AGENT-BABYSAT SCAN
  DIED" section has the Aug-2026 figures of record + exact recovery commands).
- `tekion-pipeline-operations` — documents a sibling anti-pattern: proliferating dated
  one-off `selfheal_*_YYYYMMDD.sh` watchers instead of one durable guarded runner. Same
  root disease (agent-orchestrated recovery in place of infrastructure); that one drained
  SCT's DEALER_QUOTA for days.
- Memory note: "NEVER AGENT-BABYSIT A LONG SCAN".
