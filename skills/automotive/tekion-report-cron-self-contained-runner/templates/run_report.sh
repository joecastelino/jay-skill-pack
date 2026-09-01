#!/usr/bin/bash
# TEMPLATE — self-contained Tekion report runner: scan -> render -> EMAIL, one process.
#
# Copy to /home/itadmin/tekion-reports/run_<report>.sh and replace the CONFIG block.
# Launch ONLY as:
#   terminal(background=true, notify_on_complete=true,
#            command="/usr/bin/bash /home/itadmin/tekion-reports/run_<report>.sh")
# Then post one status line and STOP. Never poll with process(action='wait').
#
# WHY: an agent turn loop cannot keep a 1-2hr job alive. On 2026-09-01 a babysat
# SCT Align+BG scan finished with perfect data on disk, but the agent hit its
# iteration ceiling on 180s wait timeouts and the render+email never ran. Cron
# reported last_status=ok. Joe got nothing. This script survives the agent dying.
#
# Pitfalls baked in:
#  - explicit /usr/bin/bash (bare `bash` can get reinterpreted under dash on launch)
#  - `bash -n` this file before the first real launch
#  - no `declare -A` (breaks under the launch wrapper) — use a case statement
set -u

# ---------------- CONFIG ----------------
NAME=myreport                                   # short slug: log/lock naming
PY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11
R=/home/itadmin/tekion-reports
D=$R/data
SCAN=$R/${NAME}_scan.py                         # must print the output JSON path as its LAST stdout line
RENDER=$R/render_${NAME}.py                     # takes <json>, writes PNG+PDF, prints their paths
EMAIL=$R/${NAME}_email.py                       # takes <json> <png> <pdf>, sends via jay_mail.send_report
STEM="My-Report-By-Advisor"                     # output filename stem used by RENDER
# Serialize against any higher-priority job sharing the rate-limit bucket.
# e.g. CONFLICT="sct_align_mtd"  (Kevin's 7 PM nightly has priority) — "" to disable.
CONFLICT=""
# ---------------------------------------

LOG=$D/_${NAME}_run.log
LOCK=/tmp/${NAME}.lock

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "[$(date '+%F %T')] already running (lock $LOCK held), exiting" >>"$LOG"; exit 0
fi

say(){ echo "[$(date '+%F %T')] $*" >>"$LOG"; }
say "=== START ${NAME} args=$* ==="

# --- Preflight: wait out a conflicting higher-priority scan (max ~2h) ---
if [ -n "$CONFLICT" ]; then
  waited=0
  while pgrep -f "$CONFLICT" >/dev/null 2>&1; do
    if [ "$waited" -ge 7200 ]; then say "FATAL $CONFLICT still running after 2h, aborting"; exit 1; fi
    say "waiting on conflicting job $CONFLICT (${waited}s)"; sleep 300; waited=$((waited+300))
  done
  say "preflight clear (no $CONFLICT)"
fi

cd "$R" || { say "FATAL cannot cd $R"; exit 1; }

# --- Stage 1: SCAN (the long one) ---
SRC=$("$PY" "$SCAN" "$@" 2>>"$LOG" | tail -1)
say "scan finished, output=$SRC"
if [ ! -f "$SRC" ]; then say "FATAL scan produced no usable JSON (got '$SRC')"; exit 1; fi

# --- Stage 2: RENDER ---
"$PY" "$RENDER" "$SRC" >>"$LOG" 2>&1 || { say "FATAL render failed"; exit 1; }
PNG=$(ls -t "$D"/${STEM}-*.png 2>/dev/null | head -1)
PDF=${PNG%.png}.pdf
if [ ! -s "$PNG" ] || [ ! -s "$PDF" ]; then say "FATAL missing/empty PNG or PDF ($PNG / $PDF)"; exit 1; fi
say "render ok png=$PNG ($(stat -c%s "$PNG")B) pdf=$PDF ($(stat -c%s "$PDF")B)"

# --- Stage 3: EMAIL (jay_mail.send_report raises unless delivery is confirmed) ---
if "$PY" "$EMAIL" "$SRC" "$PNG" "$PDF" >>"$LOG" 2>&1; then
  say "=== EMAIL DELIVERED — ${NAME} COMPLETE ==="
else
  say "=== FATAL email failed — data IS on disk at $SRC; use the recovery drill (render+email only, do NOT re-scan) ==="
  exit 1
fi
