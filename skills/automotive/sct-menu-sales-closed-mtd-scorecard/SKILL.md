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
  - closed mtd
  - daily closed performance report
  - sct_menu_sales_closed_mtd
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
   ⚠️ **Output lands in `data/`, NOT the work-dir root.** The task spec implies
   `/home/itadmin/tekion-reports/SCT-Menu-Sales-Closed-Scorecard-<today>.pdf`,
   but the renderer actually writes
   `/home/itadmin/tekion-reports/data/SCT-Menu-Sales-Closed-Scorecard-<today>.{png,pdf}`
   (it echoes both full paths on stdout — just read them from there). An `ls` on
   the root path returns "No such file or directory"; that is not a render
   failure. Always attach the `data/` path in the Stacey ask.
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
   - ⚠️ **Verified 2026-08-22: asking her to "build the message with a real MIME
     library" is NOT strong enough on its own** — that phrasing was used in the
     original draft ask AND the rebuild ask, and the message STILL went out
     `MIME=MARKUP-ONLY | PDF=NO`. What fixed it first try was instructing the
     *mechanism* explicitly: **"Do it by WRITING AND RUNNING A PYTHON SCRIPT
     that uses email.mime (MIMEMultipart('mixed') + MIMEMultipart('alternative')
     + MIMEApplication for the PDF with Content-Disposition attachment header)
     and sends via smtplib SMTP. Do NOT use the himalaya `<#part>` template
     syntax — that is what broke it."** Naming himalaya's `<#part>` syntax as
     the thing to avoid is the key ingredient. Also ask her to **confirm the
     actual attachment size in bytes**, then cross-check it against
     `ls -la` on the PDF (150,092 B matched exactly) — a byte-exact match is
     the cheapest hard proof the real file went out.
   - ✅ **Verified 2026-08-23: putting the explicit "WRITE AND RUN A PYTHON SCRIPT
     using email.mime … do NOT use the himalaya `<#part>` syntax" instruction in
     the ORIGINAL draft ask (not just as a rebuild retry) produced a correct
     `MIME=REAL-multipart` on the first attempt** — no rebuild cycle needed, and
     Stacey volunteered the byte counts unprompted (PDF 150,092 / PNG 883,652,
     both matching `ls -la`). Make that instruction part of the standard draft
     ask every run; it turns a 2-3 call recovery loop into one clean call.
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
   - ⚠️ **Verified 2026-08-24: THREE consecutive `ask-agent stacey` calls returned
     empty output (exit 0) — the draft ask, the send ask, and the first verify ask.**
     Long multi-line asks appear to be what stalls her. The fix that restored
     responsiveness immediately: **shorten the ask drastically.** A terse
     `"READ-ONLY. Last 5 Sent messages, newest first: TS | TO | SUBJ. One line
     each."` returned a clean formatted list first try, and a one-line Drafts
     probe (`"Any draft created today whose subject mentions 'Closed MTD'?
     Reply: DRAFT=<id and subject, or NONE>"`) surfaced the draft ID. Then the
     send-by-explicit-ID ask (draft ID + the WRITE-AND-RUN-A-PYTHON-SCRIPT
     email.mime/smtplib instruction, ~6 lines) worked first try and returned
     `SENT=18:12 | BYTES=152087` — byte-exact vs `ls -la`. **Sequence to use when
     asks go silent: terse Sent list → terse Drafts probe → send by draft ID.**
     Don't keep re-issuing the long ask; it just burns 150s timeouts.
   - ⚠️ **Verified 2026-08-25: the escalation ladder that finally worked was
     TERSENESS, in three steps.** Send ask #1 (long, with full MIME
     instructions) returned a confident `SENT=6:07 PM | BYTES=153,328` —
     byte-exact and totally false (Sent newest was 17:08, draft still EXISTS
     created 18:04). Send ask #2 (long re-send ask restating TO/subject/paths/
     body) returned **empty output, exit 0** — also did nothing. Send ask #3 was
     a single line — **`"Send draft 42670 via smtplib now. Reply: OK or
     ERROR=<msg>"`** — and worked first try. Byte-exactness of a reported figure
     is NOT evidence of a real send; only a Sent-folder read is. When a send ask
     fails once, do NOT retry with more detail — retry with LESS. The draft is
     already fully built at that point, so the one-liner has everything it needs.
   - ✅ **Verified 2026-08-26 — BEST-KNOWN FLOW: skip the draft stage entirely and
     write the body to a FILE.** The long draft ask (inline multi-line BODY:, ATTACH:,
     INLINE:, plus MIME instructions) returned **empty output exit 0**, and the terse
     Drafts probe confirmed `DRAFT=NONE` — nothing was created. What worked **first
     try** was collapsing draft+send into ONE short ask with the body passed by path:
     1. `write_file` the body (greeting + figures + Joe's signature) to
        `data/closed_mtd_body_<today>.txt`.
     2. One ~6-line ask:
        ```
        Write and run a python script (email.mime + smtplib, NOT himalaya <#part>) that SENDS now:
        TO jcastelino@americanmotorscorp.com
        SUBJ: <subject>
        BODY file: <path to .txt>
        ATTACH: <full PDF path>
        Reply: OK BYTES=<pdf size> or ERROR=<msg>
        ```
        Returned `OK BYTES=154593` (byte-exact vs `ls -la`), and the Sent-folder read
        confirmed a real 18:06 send with `MIME=REAL-multipart`, PDF attached.
     Moving the prose body out of the ask is what keeps it short enough not to stall
     her. Prefer this over draft→send-by-ID; it's 1 call instead of 3-4.
     ✅ **Re-confirmed 2026-08-27: same body-file + one short send ask worked first try**
     (`OK BYTES=155444`, byte-exact; Sent showed 18:03, `MIME=REAL-multipart`, PDF
     attached). Three calls total for the whole email stage (send, Sent list, MIME check).
     This is now the default flow — do not build a draft first. Still run
     both verifies (subject-agnostic Sent list, then the MIME one-liner) — `OK BYTES=`
     is still not proof on its own.
   - ⚠️ **A literal `SENT=<HH:MM>` reply from the send ask can be FALSE.**
     Verified 2026-08-21: the send instruction for draft 42577 returned a crisp
     `SENT=18:05`, but an unfiltered Sent listing showed the newest message was
     17:07 and `DRAFT42577=EXISTS created 18:03` — it had never left Drafts.
     A re-send ask then returned **empty output (exit 0)** and *that* one
     actually worked (Sent showed 18:03, MIME=REAL-multipart, PDF attached).
     So the send ask's reply text is uninformative in BOTH directions: a
     confident `SENT=` can be a hallucination, and silence can be success.
     Only an actual Sent-folder read settles it.
   - ⚠️ **Best tie-breaker is a SUBJECT-AGNOSTIC Sent listing**, not a subject
     search (which the em-dash breaks, see above) and not a `Closed MTD`
     fragment search (which returned a false `NONE-IN-SENT` on 2026-08-21 even
     though the message was there). This phrasing is the reliable one:
     ```
     READ-ONLY, send nothing. Do NOT filter by subject. List the last 8
     messages in Sent, newest first: TS=<YYYY-MM-DD HH:MM> | TO=<addr> |
     SUBJ=<subject> | ATT=<attachment filenames or NONE>.
     Final line: DRAFT<id>=<EXISTS created HH:MM / GONE>
     ```
     Comparing the newest Sent timestamp against the draft's creation time
     tells you unambiguously whether the send happened.
   - ⚠️ **`ATT=NONE` in that list view is meaningless** — it shows NONE for
     every row including messages verified to carry a real PDF. Her tabular
     view doesn't surface attachments (she'll also note it doesn't surface
     `TO`). Never conclude the PDF is missing from a list-view `ATT=NONE`;
     confirm attachments only via the raw-MIME one-liner check.
   - Also note `DRAFTS=20+` on the broad verify is just her whole Drafts folder
     (Stacey accumulates many unrelated drafts), NOT copies of this report —
     scope any draft count to an ASCII subject fragment before acting on it.
   - Leave the broken first copy in Sent — Joe gets two emails, one good; a
     duplicate is far better than a recall attempt. Note it in the summary.

## Pitfall: a genuine 0-closed-RO day (validate, don't assume outage)

**Verified 2026-08-22 (Saturday):** the scan printed `closed/invoiced ROs
today: 0` and `prefilter: 0 of 0`, leaving MTD flat. Prior Saturdays were NOT
zero (8/15=137, 8/8=48, 8/1=28 closed ROs), so a Saturday zero is not
self-evidently normal — but it was real, not a quota outage. Cheap way to tell
the difference in ONE call: re-probe `search_closed` for today plus the two
prior days. If adjacent days return healthy counts (8/21=24 ROs, 8/20=19) with
no 429s, the API is fine and today's zero is genuine (invoicing simply hadn't
posted by the 6 PM run). An outage instead shows 429/`DEALER_QUOTA` or zeros
across ALL probed days. **Variant verified 2026-08-29 (Saturday):** a *nonzero* RO count with a zero
prefilter — `closed/invoiced ROs today: 25` but `prefilter: 0 of 25`. Same
validation applies and is equally cheap: adjacent days came back 8/28 = 239
ROs / 5 TEK candidates and 8/27 = 225 / 6, no 429s, so the API was fine and
Saturday simply invoiced 25 non-menu tickets. Note the RO count is itself a
useful signal — 25 vs ~230 on weekdays confirms a light Saturday rather than a
scan that silently failed to page.

Still render + email on a genuine zero — the MTD total
stands — and say so explicitly in the body ("No repair orders were
invoiced/closed today as of the 6 PM run, so MTD is unchanged from yesterday")
so Joe doesn't read the flat number as a broken pipeline.

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
