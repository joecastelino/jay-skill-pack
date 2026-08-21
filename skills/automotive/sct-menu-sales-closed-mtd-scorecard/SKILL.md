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
  ⚠️ **The cron task spec hardcodes a stale baseline sentence** (e.g. "the
  current-month master already holds June 1-17 = 28 menus / $10,119.08"). That
  line was written in June and is NEVER updated — by 2026-08-18 the real master
  was `MASTER-2026-08` at 68 menus / $31,300.21. Ignore the spec's baseline
  entirely; read the actual current-month master at the start of the run to get
  the true pre-run figure, and mention the discrepancy in the final summary so
  Joe knows the spec text is stale, not the data.
- `data/sct-menu-sales-closed-<YYYY-MM-DD>.json` — RB-schema MTD snapshot the
  renderer consumes (rewritten every run from the master).
- `render_scorecard.py` — same renderer as Opened; auto-detects "closed" in
  the `report` field and titles it "Menu Sales — Closed Performance Report
  (Month-To-Date)".

## Steps

1. Browser auth check on :9223 (see `sct-menu-sales-api-scorecard` /
   `persistent-browser-server` skills) — needed only for advisor-name
   resolution fallback.
   ⚠️ **A dead :9223 is NOT a blocker for this report — do not spend calls
   restoring it.** The task spec's step 1 says to restore the session, but the
   closed pipeline resolves advisor names via the PUBLIC OpenAPI `/users/{id}`
   (see the ⭐ UPGRADE section in `sct-menu-sales-api-scorecard`). Verified
   again 2026-08-18: `curl :9223/health` returned **exit 7 (connection
   refused, server not even running)** and all 15 advisors still resolved to
   real human names with zero UUIDs. Only restore if advisor names actually
   come back as digits/UUIDs AFTER the scan — check the emitted JSON, don't
   pre-emptively fix the browser.
   Quick post-scan names check (authoritative, cheaper than vision):
   ```python
   import json, re
   from collections import Counter
   d = json.load(open("data/sct-menu-sales-closed-<today>.json"))
   adv = Counter(r["advisor"] for r in d["rows"])
   bad = [a for a in adv if str(a).isdigit() or re.fullmatch(r'[0-9a-fA-F\-]{6,}', str(a))]
   print(bad, adv.most_common())
   ```
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
   - **Pitfall (verified 2026-08-15): `vision_analyze` OCR is noisy on this dense
     table and gives DIFFERENT wrong details on repeated calls against the same
     PNG** — e.g. across 3 calls on the same image it read the dealer name as
     both "Stevens Creek Toyota" (correct) and "Stevens Creek Chrysler Jeep
     Dodge" (wrong/hallucinated), and per-advisor menu counts/totals drifted
     between calls (Jaime Sanchez read as 6 vs 8 menus, Cristian Gonzalez 6 vs
     7, etc.) even though the KPI header totals ($ labor/parts/total, menu
     count) stayed consistently correct across all calls. **Treat vision_analyze
     as a structural check only** (title text present + says Closed/MTD, 4 KPI
     cards present, advisor names look like human names not hex/UUIDs, no
     NaN/null/cut-off) — do NOT trust its transcribed per-advisor numbers or
     dealer name as ground truth. Cross-check any numeric claims against the
     source JSON's `.totals`/`.row_count`/`.rows` directly in Python instead of
     relying on what vision reports back.
5. Email via Stacey: draft first (recipient jcastelino@americanmotorscorp.com,
   subject `Menu Sales — Closed MTD Performance Report — SCT <m/d/yy>`,
   attach PDF by full path, body = MTD totals + row_count from the JSON's
   `.totals`/`.row_count`), then a SECOND message telling her to **send** that
   specific draft (disambiguate by subject text + today's date, not a bare
   draft ID — draft IDs from her first reply are internal and she may not
   recognize them back).
6. Verify send with a short status-check message ("is '<subject>' to that
   addr in Sent now?"). **The send-instruction call to `ask-agent stacey` can
   return exit_code 124 (timeout) with EITHER outcome underneath** — sometimes
   the send actually succeeded in the background (verified 2026-08-08: two
   consecutive 150s timeouts, but status-check confirmed sent/starred), and
   sometimes it did NOT (verified 2026-08-12: single 124 timeout on the send
   instruction, but the follow-up status-check found the draft still sitting
   in Drafts, unsent). **Never infer success OR failure from the exit code —
   the timeout is uninformative either way.** Always follow up with a
   lightweight status-check call to get the real Sent-folder state. If the
   status-check reports it's still in Drafts, Stacey's status reply will
   often surface the internal draft ID (e.g. "Drafts | 42208") — send ONE
   more explicit instruction referencing that draft ID directly ("send draft
   42208 now — that's the '<subject>' email") rather than repeating the
   generic subject-only send instruction, then verify Sent again.

7. **MANDATORY second verify: the MIME/attachment check. A passing
   TO/TS/TOTAL verify does NOT prove the PDF actually went out.**
   Re-confirmed on the CLOSED report 2026-08-18 (previously only logged for
   the Opened run 2026-07-21, so this trap hits BOTH reports): the send ask
   returned empty output (exit 0, silent timeout), the read-only verify came
   back a clean `SENT 18:05 TO Joe Castelino TOTAL $35,040.89` — correct
   recipient, correct subject, correct literal figures — yet the Sent copy was
   a single plain-text part with the `<#part type=application/pdf ...>` markup
   as literal text. **No real attachment, no inline PNG.** Recipient+numbers
   passing is exactly what makes this one sneaky; never stop at that verify.
   - Jay cannot read Sent via himalaya (IMAP AUTHENTICATIONFAILED in Jay's
     profile), so the MIME check must be a terse one-line ask to Stacey. This
     exact phrasing worked first try:
     ```
     READ-ONLY, send nothing. For that Sent copy of '<subject fragment>'
     (<HH:MM> today): 1) exact TO email address, 2) is the MIME real multipart
     with a Content-Disposition attachment filename (not literal <#part>
     markup as text)?, 3) how many drafts with that subject remain?
     Reply one line: TO=<addr> | MIME=<REAL-multipart filename=... or
     MARKUP-ONLY> | DRAFTS=<number>
     ```
   - On `MIME=MARKUP-ONLY`, recovery that landed correctly on the FIRST retry:
     tell her to **REBUILD FROM SCRATCH** (never edit/reuse the broken one) and
     explicitly instruct the transport — *"Build the message with a real MIME
     library (multipart/mixed + multipart/alternative) and send over SMTP"* —
     plus restate TO / greeting / literal figures / real PDF path / inline PNG
     path in the same ask so no follow-up is needed. Naming the MIME structure
     explicitly is what makes it stick; a generic "use SMTP template-send"
     re-ask is weaker.
   - **`DRAFTS=1` in the verify line does NOT mean the send failed.** Verified
     2026-08-19: send ask returned empty (exit 0), verify came back
     `SENT=18:05 | MIME=<png filename> | DRAFTS=1` — the remaining draft was a
     **leftover copy of the message that had already gone out** (same ID 42521,
     created 18:03, two minutes before the 18:05 send), not an unsent message.
     Don't re-send on a nonzero DRAFTS count; ask one disambiguating question
     (`DRAFT=<leftover-copy or UNSENT>`) first, or you'll double-mail Joe.
   - Also note the verify's `MIME=` field may echo only the **inline PNG**
     filename even when the PDF attachment is present — that alone is not proof
     the PDF is missing. Ask specifically:
     `PDF=<YES filename/NO> | TOTAL=<dollar figure in body> | DRAFT=<leftover-copy or UNSENT>`
     (this exact one-liner worked first try on 2026-08-19 and settled both
     ambiguities in a single call).
   - Then do a final read-only confirm scoped to the NEW message UID:
     `TO=<addr> | TS=<ts> | PDF=<YES filename / NO> | TOTAL=<$>`.
   - ⚠️ **The em-dash in the subject causes FALSE "GENUINELY-UNSENT" verdicts.**
     Verified 2026-08-20: verify #1 returned a clean
     `TO=jcastelino@... | TS=18:08 | PDF=YES SCT-...-2026-08-20.pdf | TOTAL=$42,841.05`,
     but a follow-up asking her to count messages matching the *exact* subject
     string `'Closed MTD Performance Report — SCT 8/20/26'` came back
     `SCOPED_DRAFTS=0 | SENT_COPIES=0 | VERDICT=GENUINELY-UNSENT` — flatly
     contradicting the first check, on a message that HAD in fact gone out.
     Her subject matcher does not reliably match the `—` (U+2014) em-dash, so
     an exact-subject scoped search silently returns zero hits. **Never re-send
     on a lone `SENT_COPIES=0` / `GENUINELY-UNSENT` answer** — that is how you
     double-mail Joe. Tie-break with a punctuation-insensitive query, which
     resolved it first try:
     ```
     READ-ONLY, send nothing. Ignore subject punctuation/em-dashes. Search
     Sent for ANY message sent TODAY to <addr> whose subject mentions
     'Closed MTD'. List each as: SENT | TS=<HH:MM> | SUBJ=<subject> |
     PDF=<attachment filename or NONE>. If none, reply exactly: NONE-IN-SENT
     ```
     Rule of thumb: always phrase Sent-folder verifies with a short ASCII-only
     subject fragment (`Closed MTD`) rather than the full em-dashed subject.
   - Also note `DRAFTS=20+` on the broad verify is just her whole Drafts folder
     (Stacey accumulates many unrelated drafts), NOT copies of this report —
     scope any draft count to an ASCII subject fragment before acting on it.
   - Leave the broken first copy in Sent — Joe gets two emails, one good; a
     duplicate is far better than a recall attempt. Note it in the summary.

## Reading the master / RB files in an inspection script (schema gotchas)

- The **master** is a dict `{"month","records","updated","asof"}` where
  `records` is itself a **dict keyed `"ro|opcode"`** — NOT a list. Iterating
  the top-level object yields the four key STRINGS and blows up with
  `AttributeError: 'str' object has no attribute 'get'`. Use
  `rows = list(json.load(open(master))["records"].values())`.
- The emitted **RB file** uses `rows` (a list) plus `.totals` /`.row_count` —
  different shape from the master. `.totals` has `labor_gross`, `parts_gross`,
  `labor_price`, `parts_price`; total menu gross = labor_gross + parts_gross
  (it is NOT a stored field).
- **`row["date"]` is the RO's CREATION date, not its close date** (documented
  upstream: the search response returns `closedTime`/`invoicedTime` as null, so
  rows can only be bucketed by `creationTime`). So filtering
  `[r for r in rows if r["date"] == "<today>"]` legitimately returns **0 rows
  even on a day that added 10 new menus** — those ROs were opened days earlier
  and merely closed today. Do NOT treat that as a scan failure. To report
  today's delta, diff the master row_count/totals before vs. after the run, or
  read the scanner's own stdout (`master now holds N MTD menu rows`).

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
