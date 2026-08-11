---
name: sct-menu-sales-closed-mtd-scorecard
description: >
  Run the SCT (Stevens Creek Toyota) Menu Sales CLOSED Month-To-Date scorecard
  pipeline from the LIVE Tekion OpenAPI (incremental design) and email the PDF
  to Joe via Stacey. This is the daily 6 PM companion to the noon/5pm "Opened"
  report (see sct-menu-sales-api-scorecard). Covers the incremental
  master-file design, the ongoing DEALER_QUOTA outage caveat, and the
  ask-agent send-confirmation timeout workaround.
triggers:
  - sct menu sales closed
  - closed mtd scorecard
  - menu sales closed report
trigger: SCT menu sales closed, closed MTD, daily closed performance report, sct_menu_sales_closed_mtd
---

# SCT Menu Sales CLOSED MTD Scorecard (LIVE source, incremental)

Daily 6 PM cron companion to the Opened report (`sct-menu-sales-api-scorecard`
skill — load that too for the :9223 browser auth-check procedure, which is
shared). This one totals CLOSED/INVOICED ROs for the current month
month-to-date, using an incremental per-month master cache so the whole month
is never re-scanned in one run (that exhausts the OpenAPI rate limit).

Interpreter: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`
Work dir: `/home/itadmin/tekion-reports`

## Files

- `sct_menu_sales_closed_mtd.py` — the incremental scanner (reuses
  `sct_menu_sales_api.py` as `O` for opcode list / RO scan / advisor
  resolution).
- `data/sct-menu-closed-mtd-MASTER-<YYYY-MM>.json` — persistent per-month
  cache, keyed `"ro|opcode"`. Auto-created on month rollover.
- `data/sct-menu-sales-closed-<YYYY-MM-DD>.json` — RB-schema MTD snapshot the
  renderer consumes (rewritten every run from the master).
- `render_scorecard.py` — same renderer as Opened; auto-detects "closed" in
  the `report` field and titles it "Menu Sales — Closed Performance Report
  (Month-To-Date)".

## Steps

1. Browser auth check on :9223 (see `sct-menu-sales-api-scorecard` /
   `persistent-browser-server` skills) — needed only for advisor-name
   resolution fallback.
2. `cd /home/itadmin/tekion-reports && python3.11 sct_menu_sales_closed_mtd.py`
   — scans **today only** (~100-150 closed ROs), prefilters to ROs carrying a
   TEK menu opcode tag (free on the search response, no fan-out needed), then
   fans out jobs/operations calls only for those candidates, merges into the
   month master, and re-emits the dated RB-schema file.
   - **Never pass `--seed`** in a daily run — that's the one-time paced full-month
     backfill and will burn the rate limit.
   - Watch stderr `[sct-api]` lines for `429` / `Limit exhausted`. If hit, STOP,
     wait 8 min, retry ONCE.
3. Render: `python3.11 render_scorecard.py data/sct-menu-sales-closed-<today>.json`
   → PNG + PDF.
4. Vision-verify the PNG (title, 4 KPIs, real advisor names not UUIDs, no
   NaN/cut-off). **An empty table with "No menu sales recorded yet for this
   period" is a VALID render** — don't treat it as a renderer bug.
5. Email via Stacey: draft first (recipient jcastelino@americanmotorscorp.com,
   subject `Menu Sales — Closed MTD Performance Report — SCT <m/d/yy>`,
   attach PDF by full path, body = MTD totals + row_count from the JSON's
   `.totals`/`.row_count`), then a SECOND message telling her to **send** that
   specific draft (disambiguate by subject text + today's date, not a bare
   draft ID — draft IDs from her first reply are internal and she may not
   recognize them back).
6. Verify send with a short status-check message ("is '<subject>' to that
   addr in Sent now?"). **The send-instruction call to `ask-agent stacey` can
   return exit_code 124 (timeout) even though the send actually succeeded in
   the background** — don't treat a timeout as failure. Always follow up with
   a separate lightweight status-check call; it will report the real Sent
   state (verified 2026-08-08: two consecutive 150s timeouts on the send
   command, but the status-check confirmed the email was sent and starred in
   Sent Mail at the expected timestamp).

## Pitfall: the scanner does NOT always auto-write `quota_outage_note` — verify manually

**Verified 2026-08-10 (day 10 of the outage):** `sct_menu_sales_closed_mtd.py` printed a
clean `exit 0` with `"✓ all candidate ROs scanned (no truncation)"` and the emitted RB JSON
had NO `quota_outage_note` field at all — even though the outage was still very much active
and 7 genuine TEK-tag candidates existed that day. The "no truncation" message only reflects
`_LAST_FAILED` being empty, which happens because `scan_ro_safe`'s retry loop treats sustained
429s as exhausted-but-still-technically-completed for that RO in some code paths — it does NOT
reliably surface the outage into the JSON on every run. **Don't trust the JSON's absence of
`quota_outage_note` as proof the outage has cleared.** Before treating a 0-menu day as real
(especially during a known multi-day outage window), independently probe 2-3 of today's
TEK-tag candidate ROs directly:

```python
import sys; sys.path.insert(0, "/home/itadmin/tekion-reports")
import sct_menu_sales_api as O, sct_menu_sales_closed_mtd as C
import json
from datetime import date, datetime, timedelta
asof = date.today()
ms0 = int(datetime.combine(asof, datetime.min.time()).timestamp()*1000)
ms1 = int((datetime.combine(asof, datetime.min.time())+timedelta(days=1)).timestamp()*1000)
maint = {r["opcode"] for r in json.loads(O.OPCODE_LIST.read_text())}
ros = C.search_closed(ms0, ms1)
candidates = [ro for ro in ros if C._tek_opcodes(ro, maint)]
for ro in candidates[:3]:
    rid = ro["documentId"]
    stj, jobs = O.call("GET", f"/repair-orders/{rid}/jobs")
    if stj == 200:
        j0 = jobs["data"]["jobs"][0]["id"]
        sto, ops = O.call("GET", f"/repair-orders/{rid}/jobs/{j0}/operations")
        print(ro["documentNumber"], "operations status:", sto, str(ops)[:150])
```
If `/jobs` returns 200 but `/operations` returns 429 with `"Limit exhausted ... DEALER_QUOTA"`,
the 0-menu figure is outage-caused, not real. **Manually patch the emitted RB JSON** (the file
`data/sct-menu-sales-closed-<today>.json`) to add a `quota_outage_note` field describing the
probe result (candidate RO numbers, confirmed 429s, outage start date/day count) — the renderer
ignores unknown fields so this is safe, and it gives Stacey's email draft the caveat text to
include. Do this BEFORE drafting the email, not after — the caveat belongs in the body every
day the outage persists, and the render itself will still legitimately show "No menu sales
recorded yet for this period" (that's a cosmetically valid render — the outage caveat has to
come from the email body / JSON note, not the chart).

## Pitfall: DEALER_QUOTA outage can silently zero out real data

**Verified ongoing 2026-08-01 through at least 2026-08-08:** the Tekion
OpenAPI `/operations` endpoint (used for the deep RO scan) can 429 with
`"Limit exhausted for type : DEALER_QUOTA"` while `/repair-orders:search` and
`/jobs` return clean 200s. This means:
- The script completes with exit 0 and prints "✓ all candidate ROs scanned
  (no truncation)" — **looks like a clean success**.
- But the prefilter step finds genuine TEK-opcode candidate ROs, and the
  fan-out to `/operations` silently 429s on all of them, so the MTD master
  ends up with **0 records for the entire outage window** even though real
  menu sales almost certainly exist.
- **How to tell a real zero from an outage zero:** check the emitted RB JSON
  for a `quota_outage_note` field (some daily runs during the 2026-08 outage
  wrote this note explicitly). If absent but the master's row_count has been
  stuck at 0 for multiple consecutive days while `search_closed` reports
  dozens of closed ROs and a nonzero TEK-tag prefilter count, suspect the
  outage is still active — check stderr from the run for `429`/`DEALER_QUOTA`
  even if the exit code is 0 (the retry/backoff loop can mask it in the final
  summary).
- **Always flag this caveat in the email body** if the master has been
  showing 0 across multiple days that plausibly have real sales — don't just
  report "$0.00, 0 menus" as if it were a genuine slow month. Recommend
  escalating a multi-day DEALER_QUOTA outage to Tekion support / Walter II.

## Relationship to the Opened report skill

Share the :9223 browser-auth-check procedure and the Stacey draft→send→verify
email flow with `sct-menu-sales-api-scorecard` (the Opened report). The two
reports run back-to-back (noon/5pm Opened, 6pm Closed) and both land in
Stacey's Sent folder — when verifying, make sure you're checking the correct
one by exact subject match (they'll be adjacent in Sent, "right after" each
other).
