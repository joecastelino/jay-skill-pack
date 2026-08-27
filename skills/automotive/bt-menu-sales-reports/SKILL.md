---
name: bt-menu-sales-reports
description: >
  Run the Blackstone Toyota (BT, dealer 1249) Menu Sales scorecards — Daily
  Opened, Daily Closed, and Closed Month-To-Date — from the LIVE Tekion
  OpenAPI. The 4th sibling of the SCT/Kevin, BC/Ruben, and TOL/Sean pipelines.
  Use for any "BT menu report", "Blackstone Toyota menu sales", or Tony Garcia
  menu-sales report request. (Menu REBUILD work is a different skill —
  bt-tony-menu-rebuild.)
triggers:
  - blackstone toyota menu sales
  - BT menu report
  - BT closed MTD
  - tony menu sales report
---

# BT (Blackstone Toyota) Menu Sales Reports

Built 2026-07-08 by cloning the TOL pipeline (see `tol-menu-sales-reports` —
read that skill for ALL shared mechanics: 429 playbooks, $0 validation,
--seed behavior, Stacey draft traps). This file covers only what is
BT-specific.

## Store facts
- **Dealer ID = 1249**, cfg key `bt` = `americanmotorscorporation_1249_0`.
- **Menu opcode set = `data/bst-menu-opcodes.json` = 213 SERVICE_MENU+ACTIVE
  opcodes** (TEK mileage×tier family + `5KTEST`). Derived 2026-07-02 via the
  standard :9223 XHR-capture method. Standard definition:
  `opcodeType==SERVICE_MENU && status==ACTIVE` — NOT SCT's 316 list.
- **Slack delivery = BT menu thread `slack:C0B8EPN76GJ:1783013683.414359`**
  (Joe designated 7/2).
- Email recipient CONFIRMED (Joe 2026-07-28): Tony Garcia,
  agarcia@blackstonetoyota.com — greeting **"Tony,"**. CLOSED MTD is auto-SENT
  (not drafted) daily at 6 AM by cron job `7d023e4565a0` (runs the dated daily
  append for YESTERDAY, renders, Stacey sends to Tony CC Joe; status posts to
  the BT menu Slack thread C0BGTDR158S:1783876504.495759). Ad-hoc requests from
  Joe still default to DRAFT to his inbox unless he says send.
- Naming trap: opcode file is `bst-…` (Blackstone Toyota), scripts are `bt_…`.
  Don't confuse with `bc-…` (Blackstone Chevy, dealer 1251).

## Files (in /home/itadmin/tekion-reports/, prefix `bt_`)
Interpreter: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`
- `bt_menu_sales_api.py` — OPENED (default run = today by creationTime) →
  `data/bt-menu-sales-opened-<date>.json` (+ `-api-` companion with
  `ro_count_scanned`).
- `bt_menu_sales_closed_mtd.py` — CLOSED. `--seed` = full-month backfill
  (paced), default = daily append to `data/bt-menu-closed-mtd-MASTER-<YYYY-MM>.json`,
  `--daily-only` = standalone daily closed, positional `YYYY-MM-DD` = dated
  catch-up for a missed day.
- `render_menu_sales_paged_bt.py <date> [closed]` — Toyota-red 2-page render,
  stems `BT-Menu-Sales-Scorecard-<date>` / `BT-Menu-Sales-Closed-Scorecard-<date>-Paged`.
- `bt_seed_watcher.sh` — flock-guarded (/tmp/bt-seed-watcher.lock) quota\n  watcher: waits for any `quota_guard.sh` reservation loop to exit, then\n  probes `/home/itadmin/dealer-detail/scripts/tekion-quota-probe.py`\n  (14h deadline); on 200 it runs `--seed` then renders. Log\n  `data/bt-seed-watcher-<date>.log`.\n  **MUST run from the system CRONTAB (every 15 min), NOT as a session\n  background process** — the Hermes session reaper SIGTERMs background\n  terminal children on session recycle (exit 143; killed the watcher twice\n  on 7/9 before the crontab move). Pattern: cron every 15 min + flock (only\n  one instance) + a DONE marker file that permanently no-ops the job once\n  the seed succeeds. Remove the cron line after delivery.

## How the clone was built (repeat for SV/AR/VC when asked)
`sed` the TOL sources (`tol_menu_sales_api.py`, `tol_menu_sales_closed_mtd.py`,
`render_menu_sales_paged_tol.py`):
dealer string `americanmotorscorporation_1092_0`→`_1249_0`, opcode list path,
`tol-`→`bt-` file stems, `[tol-api]`→`[bt-api]`, titles/dealer name, import
line in the MTD script, output stems in the renderer. **PITFALLS hit:**
1. A first grep pass MISSES the browser-fallback constants — also replace
   `tol-advisor-cache/emp-byid/user-lookup.json` and BOTH internal-API
   `"dealerId":"1092"` literals (two occurrences). Verify with
   `grep -c "1092\|tol-" bt_menu_sales_api.py` == 0.
2. If the live TOL script is renamed `*.py.paused` by a quota-crisis guard,
   clone from the `.paused` copy — same content.
3. `python3 -m py_compile` all three before first run.

## First run / seeding
BT has NO master yet as of 2026-07-08 — there are no last-known-good MTD
numbers to fall back on during an outage until the first `--seed` completes.
The 7/8 request landed during the multi-day OVERALL_QUOTA exhaustion +
an active `quota_guard.sh` window reserved for SCT; correct move was: build
pipeline, queue `bt_seed_watcher.sh` as a background job with
notify_on_complete, tell Joe honestly (no stale/zero draft), deliver to the
BT Slack thread when it lands.\n\n## Daily SEND cron (6 AM job `7d023e4565a0`) — bridge call tool choice matters (learned 2026-08-18)
The daily CLOSED MTD auto-SEND (not draft) to Tony Garcia CC Joe uses the manual
`env -u HERMES_HOME ... hermes chat -q "<msg>"` bridge pattern (per
`agent-to-agent-bridge`), NOT `~/bin/ask-agent` (may be wiped by home resets).
**Don't run that bridge call through `execute_code`'s `terminal()` helper** — its
own ~5-minute internal cap can kill the whole script (status "timeout") before
the subprocess even returns, even though the underlying `hermes chat -q` call
itself would have finished in under 2 minutes. Use the **top-level `terminal`
tool with `background=true, notify_on_complete=true`**, writing stdout to a log
file, then `process(action='wait')` (auto-clamped to ~180s, fine — poll again if
needed) and `read_file` the log. That pattern worked cleanly both for the
send-hand-off (~102s) and the verify-only Sent-check ask (~78s), zero timeouts.

Confirmed 2026-08-18 (first live SEND-only run, no draft step): Stacey's
`joe-email-mime-signature` skill auto-loads and builds the correct
multipart/mixed > multipart/related > multipart/alternative(text/plain+html) +
image/png(Content-ID=scorecard,inline) + application/pdf structure and actually
SENDS via SMTP first try — no rebuild cycle needed for a send (unlike the
TOL/BC draft pipelines' frequent MIME-rebuild traps). Verification via a single
terse read-only ask (`in:sent subject:(BT Menu Sales Closed MTD)`) returned
fast with the standard **token-match trap**: 4 hits total, 3 were prior weeks'
sends (Aug 1-8, July 1-30, July 1-28) plus today's exact match — always compare
the FULL exact subject/date, don't treat a multi-hit count as a red flag. Her
first himalaya invocation errored (`himalaya search ... --folder Sent` — wrong
subcommand) and she self-corrected to `himalaya envelope list -f "[Gmail]/Sent
Mail" -s 50 '...'` plus a raw imaplib cross-check; this is a normal self-healing
retry, not a failure to flag (same spirit as the TOL em-dash IMAP-search hiccup).

### BEST PATTERN for the bridge call: write a .sh wrapper with a quoted heredoc (2026-08-21)
Cleanest way to fire BOTH the send hand-off and the verification ask, avoiding every
known quoting pitfall (`&` false-positive block, literal parens breaking bash, `$`/
backtick expansion, em-dashes, multi-line):

1. `write_file` a throwaway script, e.g. `/home/itadmin/tekion-reports/_bt_send_<date>.sh`:
   ```sh
   #!/bin/bash
   REAL=/home/itadmin
   read -r -d '' MSG <<'EOF'
   ...full multi-line message, ANY punctuation, zero escaping needed...
   EOF
   timeout 300 env -u HERMES_HOME -u HERMES_SESSION_KEY HOME=$REAL \
     HERMES_HOME=$REAL/.hermes/profiles/email-agent \
     $REAL/.hermes/hermes-agent/venv/bin/hermes chat -q "$MSG"
   echo "EXIT=$?"
   ```
   The **quoted** heredoc delimiter (`<<'EOF'`) is what makes the body literal.
2. Run it via top-level `terminal(background=true, notify_on_complete=true)` redirecting
   to a log, then `process(action='wait', timeout=180)` + `read_file` the log.
   (`read -r -d '' MSG` returns exit 1 at EOF — harmless, don't `set -e`.)

This beats both the `execute_code`+`subprocess.run(argv-list)` approach (5-min internal
cap risk) and inlining the message in a top-level `terminal` string (scanner/bash traps).
8/21 run: send returned in ~60s, verification in ~43s, zero timeouts, zero corrections.
Log-reading tip: the hermes banner is ~60 lines of ASCII art — read the log via
`execute_code` and slice from `Initializing agent` to keep context small.

### DUPLICATE SEND from a false "SMTP connection dropped" retry (2026-08-22) — NEW, IMPORTANT
On the 8/22 run (Aug 1-21 report) Stacey's first `execute_code` SMTP attempt returned an
error, she announced "SMTP connection dropped. Retrying - Gmail sometimes rejects on first
attempt for large MIME messages," and re-sent. **The first attempt had ALREADY delivered.**
Tony + Joe received TWO identical emails (Sent Mail UIDs 8484/8485, distinct Message-IDs,
06:03:56 and 06:04:46 PDT, 50s apart). The error was on the Python side AFTER the SMTP
`sendmail` succeeded, not a real delivery failure. Unlike the draft pipelines, a duplicate
SEND cannot be cleaned up — the recipient already has both.
MITIGATION for future runs: add to the hand-off message a line like
"If your first SMTP attempt raises an error, DO NOT immediately re-send — first check
[Gmail]/Sent Mail for a message with this exact subject sent in the last 2 minutes; only
re-send if there is none."
DETECTION: the Sent-check verification returning TWO hits with TODAY'S EXACT subject (not
the usual old-date token-match hits) is the tell. Confirm with a follow-up raw-IMAP ask for
UID + Message-ID + Date-to-the-second per hit; two distinct Message-IDs = real duplicate.
Report it to Joe rather than trying to fix it.
CONFIRMED FIXED 2026-08-23: adding the explicit "CRITICAL - DO NOT DOUBLE SEND: if your
first SMTP attempt raises an error, DO NOT immediately re-send; first check
[Gmail]/Sent Mail for this exact subject sent in the last 2 minutes" paragraph to the
hand-off message produced a clean single send (one SMTP attempt, no error, no retry).
Keep that paragraph in every hand-off. The 8/22 duplicate pair (Aug 1-21, 06:03:56 +
06:04:46) still shows in Sent-folder listings forever — when verifying, expect to see it
and don't mistake it for a NEW duplicate; only two hits carrying TODAY'S exact date range
indicate a fresh double-send.

### (8/25 run, for Sat 8/24) DO-NOT-DOUBLE-SEND paragraph WORKED AS DESIGNED on a REAL SMTP failure
First live case where the SMTP error was a GENUINE non-delivery (unlike 8/22). Stacey's first
attempt raised "connection unexpectedly closed"; per the CRITICAL paragraph she did NOT blind
re-send — she ran two IMAP Sent-Mail checks (noting herself that "subject has parens - might mess
with IMAP search" and retrying broader), confirmed no Aug-25 message existed, THEN resent. Result:
exactly ONE email in Sent (Message-ID <178766310350...>, 06:05:03 PDT). Verification returned 5
hits, four prior sends (Jul 1-28, Jul 1-30, Aug 1-8, Aug 1-18) + today's exact match — the usual
token-match trap. LESSON: the paragraph is doing real work in BOTH directions (blocked a false
retry 8/23, permitted a correct retry 8/25); keep it verbatim. Also note the 8/22 duplicate pair
did NOT appear in this listing again — its presence/absence remains non-signal.
Hand-off ran 2m54s, verification 2m25s, zero timeouts with the .sh-wrapper + quoted-heredoc pattern.

### (8/26 run, for Mon 8/25) TEXTBOOK CLEAN — close lag fully recovered
After the 8/22 (closedTime=3) and 8/23 (closedTime=0) close-lag days, 8/25 came back fully
normal: **106 closed ROs**, 8 prefilter hits, 8 new menu rows, `all candidate ROs scanned`.
MTD jumped 241 rows/$58,056.84 -> **270 rows / $69,653.28** ($51,339.35 labor + $18,313.93
parts). Note the big MTD delta includes the store finally closing the backlogged 8/22-8/24
invoiced ROs, not just 8/25 activity (8/25-dated rows alone = 4 menus / $322.01) — worth
stating both numbers in the email body so Tony isn't confused by the jump.
The .sh-wrapper + quoted-heredoc + DO-NOT-DOUBLE-SEND paragraph produced a one-attempt send
in **89s** (zero SMTP errors); IMAP Sent-check returned in **44s** first try, 6 hits, exactly
one carrying today's subject (Aug 1-25) — the other 5 all prior sends (Jul 1-28, Jul 1-30,
Aug 1-8, Aug 1-18, Aug 1-24), the usual token-match trap. The 8/22 duplicate pair did NOT
appear again (confirms its presence/absence is non-signal).
MASTER JSON SHAPE (for ad-hoc per-day math): `records` is a **dict** keyed `"<ro>|<opcode>"`,
not a list — `json.load(...)["records"].values()`, each row has `date` as `MM/DD/YY`,
`labor_gross`, `parts_gross`, `total_gross`, `advisor`. A bare `recs[0]` raises KeyError.

### (8/27 run, for Tue 8/26) TEXTBOOK CLEAN — biggest single-day add of the month
200 closed ROs, 19 prefilter hits, 19 new menu rows, `all candidate ROs scanned`. MTD moved
270 rows/$69,653.28 -> **289 rows / $76,813.08** ($56,350.27 labor + $20,462.81 parts).
8/26-dated rows alone = 15 menus / $4,105.19 (the rest of the +$7,159.80 delta is the store
closing older invoiced ROs) — state both numbers in the body like the 8/26 run.
.sh-wrapper + quoted-heredoc + DO-NOT-DOUBLE-SEND paragraph: one-attempt send in **101s**,
zero SMTP errors; Stacey pre-checked Sent Mail for a same-day duplicate BEFORE sending on her
own initiative (the CRITICAL paragraph is now producing a proactive pre-send dup check, not
just a post-error one — good). IMAP Sent-check returned in **32s** first try, 7 hits, exactly
one carrying today's subject (Aug 1-26); other 6 all prior sends (Jul 1-28, Jul 1-30, Aug 1-8,
Aug 1-18, Aug 1-24, Aug 1-25) — usual token-match trap. 8/22 duplicate pair absent again.

### Verification ask wording that works first try
Lead with `IMPORTANT: print the answer as plain text IN THIS REPLY` AND
`Use himalaya / raw IMAP against "[Gmail]/Sent Mail" (NOT the Gmail API)` — the
IMAP-first default (inherited from the TOL skill's 8/17 lesson) applies here too and
returned in 43s first try on 8/21. Search the SHORT subject stem
(`BT Menu Sales - Closed MTD`, no date/parens — parenthesised dates are the fragile part
of IMAP subject searches). Expect the token-match trap: 8/21 returned `Sent: 5`, four of
which were prior sends (Jul 1-28, Jul 1-30, Aug 1-8, Aug 1-18) plus today's exact match.

### LOW "closed/invoiced ROs today" can be a REAL store-side close lag, not starvation (2026-08-23)
The 8/23 run (for 8/22, a Saturday) logged `closed/invoiced ROs today: 3` — far below the
prior two Saturdays (8/08 = 80, 8/15 = 75) and every weekday (66-263). By the standard
$0-validation rule that looks like a starved run, but a clean re-run reproduced exactly 3,
with zero 429s/500s. A DIRECT API probe settled it: for 8/22, `closedTime` returned
**3** while `invoicedTime` returned **118** and `creationTime` **125** — and 8/20/8/21
returned normal counts on all three fields. So the store simply had not run its accounting
CLOSE on Saturday's invoiced ROs yet; the API was healthy and the data is correct.
`bt_menu_sales_closed_mtd.py:search_closed()` filters on `closedTime` by design (verified
2026-06-19: closedTime is true "closed in period"; modifiedTime overcounts).
DIAGNOSTIC (use this before declaring starvation on ANY low-RO day — ~3s, no full re-run):
```py
import sys, datetime; sys.path.insert(0,"/home/itadmin/tekion-reports")
import bt_menu_sales_api as O
d = datetime.date.fromisoformat("YYYY-MM-DD")
a = int(datetime.datetime(d.year,d.month,d.day,0,0,0).timestamp()*1000)
b = int(datetime.datetime(d.year,d.month,d.day,23,59,59).timestamp()*1000)
for f in ["closedTime","invoicedTime","creationTime"]:
    st,out = O.call("POST","/repair-orders:search",
        {"filters":[{"field":f,"operator":"BTW","values":[a,b]}],"pageSize":1})
    print(f, st, (out.get("meta") or {}).get("totalCount"))
```
Saved as `_bt_probe_0823.py`. DECISION RULE: all three fields 0 / non-200 = real outage,
skip the email. closedTime low but invoicedTime/creationTime normal = genuine close lag,
the MTD total is still valid — **render and send normally**, and note the lag in the
final report so Joe knows the day contributed almost nothing. Also probe an adjacent day
as a control before concluding anything.

### (8/24 run, for Sun 8/23) ZERO closed ROs — confirmed close lag, NOT starvation
Sunday 8/23 logged `closed/invoiced ROs today: 0`. The `_bt_probe_0824.py` 3-field probe
(now saved alongside `_bt_probe_0823.py`) settled it instantly with an adjacent-day control:
8/21 closedTime=150 / invoiced=180 / created=146 (normal), 8/22 closedTime=3 / invoiced=118
/ created=125 (the known 8/22 lag), 8/23 **closedTime=0 / invoicedTime=34 / creationTime=35**
— all HTTP 200. So the store simply hadn't run accounting close on Sunday's 34 invoiced ROs.
Per the DECISION RULE this is a genuine lag: MTD total still valid, render + send normally.
Confirms `closedTime=0` alone is NOT proof of starvation — always probe all three fields plus
a control day BEFORE skipping the email. MTD stayed flat at 241 rows / $58,056.84 (same as
8/22's run); state the zero-delta explicitly in the email body so Tony isn't confused by an
unchanged total (same practice as the TOL Sunday note).
CLEAN SEND: the .sh-wrapper + quoted-heredoc pattern with the DO-NOT-DOUBLE-SEND paragraph
produced a one-attempt send in **47s** (zero SMTP errors, zero retries); the IMAP Sent-check
returned in **26s** first try, 5 hits, exactly one carrying today's subject. NOTE: the 8/22
duplicate pair (Aug 1-21, 06:03:56 + 06:04:46) did NOT appear in this Sent listing even
though the skill predicted it would show forever — don't treat its absence (or presence) as
signal either way; only two hits with TODAY's exact date range mean a fresh double-send.

## OVERALL_QUOTA reset behavior (observed 7/8–7/9 outage)\nNOT a fixed midnight reset. Behaves like a rolling ~24h+ bucket tied to when\nthe calls were burned; the 7/8 outage ran **29+ hours** with continuous 429s.\nRecovered capacity can be instantly re-drained by queued crons (11PM\ndealer-detail sync, 2AM VI pull), making it look continuously dead.\nIf dead >24h, escalate: ticket to Tekion asking the actual OVERALL_QUOTA\nlimit, reset schedule, and a raise — it's one org-wide bucket shared by all\n7 stores' pipelines and AMG has co-founder-level contact from the bin\nescalation. Never blind-retry; probe-gate everything.
