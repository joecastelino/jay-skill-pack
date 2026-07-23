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
- Email recipient TBD (likely Tony Garcia, agarcia@blackstonetoyota.com —
  BT Service Manager — but Joe has NOT confirmed; ask before drafting).
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
BT Slack thread when it lands.\n\n## OVERALL_QUOTA reset behavior (observed 7/8–7/9 outage)\nNOT a fixed midnight reset. Behaves like a rolling ~24h+ bucket tied to when\nthe calls were burned; the 7/8 outage ran **29+ hours** with continuous 429s.\nRecovered capacity can be instantly re-drained by queued crons (11PM\ndealer-detail sync, 2AM VI pull), making it look continuously dead.\nIf dead >24h, escalate: ticket to Tekion asking the actual OVERALL_QUOTA\nlimit, reset schedule, and a raise — it's one org-wide bucket shared by all\n7 stores' pipelines and AMG has co-founder-level contact from the bin\nescalation. Never blind-retry; probe-gate everything.
