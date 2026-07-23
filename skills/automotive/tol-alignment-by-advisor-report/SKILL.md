---
name: tol-alignment-by-advisor-report
description: Run the Toyota of Lancaster (TL/TOL, Tekion dealer 1092) ALIGNMENT count report, month-to-date, broken down by service advisor (dedicated + bundled + unique ROs, ranked). Produces a 2-page Toyota-red scorecard (page-1 PNG + full PDF) and is drafted to Sean Preston by Stacey. Use when Joe asks for "the Lancaster/TOL alignment report" or to schedule it.
triggers:
  - tol alignment report
  - lancaster alignment report
  - toyota of lancaster alignments by advisor
  - run the TL alignment count
---

# TOL Alignment-by-Advisor Report (MTD)

Counts how many **alignments** were sold at Toyota of Lancaster in the current
month, split into **dedicated** (a standalone alignment opcode) and **bundled**
(an alignment performed inside a service-menu / combo op), then ranks by service
advisor. Mirrors the SCT alignment methodology but with **TL's own opcode
scheme** (TL opcodes differ from SCT — never reuse SCT's ALIGN/OKAL).

## TL alignment opcode scheme (Joe-approved 2026-06-29, "Jay's read")
- **DEDICATED** (count as an alignment sale):
  `4ALIGN` (4 Wheel Alignment), `SMALIGN` (Perform 4 Wheel Alignment),
  `TEK07030101` (Wheel Alignment Adjust).
  (Note: in June only `4ALIGN` actually sold; the other two are valid but unused
  that month — keep them in the set for future months.)
- **BUNDLED** (alignment inside a multi-service op): the combo/seasonal codes
  `RAB`, `5KALIGNMENT`, `15KALIGNMENT`, `FALL`, `SPRING`, **plus** any TL
  SERVICE_MENU / TEK* menu opcode whose operation **story** contains "align".
- **EXCLUDED** (inspection / check-only / not a wheel alignment): `ALIGN`
  (inspection only), `TEK07140101`, `TEK07140102` (check only), `TEK03100301`
  (headlamp), `4ALIGNT` (inactive).

These are hard-coded in `tol_align_scan.py` (DEDICATED / COMBO / EXCLUDED sets).
The bundled-menu match uses the frozen TL menu set `data/tl-menu-opcodes.json`
(212 SERVICE_MENU opcodes — see skill `tekion menu-opcode derivation` / the
TL menu-sales pipeline).

## Run it
```sh
cd /home/itadmin/tekion-reports
PY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11
# 1. scan (MTD through today; or pass YYYY-MM-DD as-of). PACED — run in background.
$PY tol_align_scan.py            # writes data/tol-align-by-advisor-<today>.json
# 2. render the 2-page scorecard (page-1 PNG + full PDF)
$PY render_tol_align_by_advisor.py <today>
#   -> data/TOL-Alignment-By-Advisor-<today>.{png,pdf}
```
- The scan is RATE-LIMIT PACED (18s between batches, 429 backoff). For June it
  enumerated ~3,800 closed ROs, prefiltered to ~183 candidates, ~6-18 min wall
  time depending on the shared OpenAPI ratelimit. **Run as a background job with
  notify_on_complete**; do NOT block a foreground terminal.
- Coverage is verified: the scan does a retry pass and prints
  "all candidate ROs scanned (no truncation)" or a WARNING with unscanned RO #s.

## How the scan works (two-tier, rate-limit-safe)
1. `search_closed(ms0, ms1, field="closedTime")` — all CLOSED/INVOICED ROs with
   `closedTime` in [month-1st .. end-of-as-of-day]. (Use closedTime, NOT
   modifiedTime — modifiedTime overcounts.)
2. Prefilter on the FREE OPCODE `tags` array (no fan-out): keep ROs carrying a
   dedicated align opcode OR a combo code OR any TL menu opcode.
3. Fan out jobs -> operations only on candidates; classify each op as dedicated /
   bundled / excluded. Bundled detection reads the op **story**
   (`operation.corrections[].text` + opcodeDescription) and substring-matches
   "align".
4. `assignee.advisor.id` is FREE on the RO search result — resolve names via
   `O.user_name(aid)` (public OpenAPI /users/{id}). No browser needed.

## Output JSON schema (data/tol-align-by-advisor-<date>.json)
`{report, dealer, window, totals:{dedicated,bundled,total,unique_ros,advisors},
advisors:[{advisor,dedicated,bundled,total,unique_ros,detail:[{ro,opcode,kind}]}]}`
— ranked by total desc. The renderer consumes this single file directly.

## Render output
- **Page 1** = summary scorecard (KPI cards Total/Unique ROs/Advisors/Daily Pace
  + ranked advisor table with red bars). PNG = page-1 ONLY (inline email image).
- **Page 2** = RO-level detail: per-advisor chip blocks, red chip = dedicated,
  blue chip = bundled (labeled "(menu)"). PDF = full 2-page (email attachment).
- Toyota-red (#EB0A1E) branding, typographic header "TOYOTA OF LANCASTER"
  (no logo image — matches the TOL menu-sales reports). Address 43301 12th St W,
  Lancaster CA 93534.

## Email (via Stacey, draft-only unless told to send)
Recipient = **Sean Preston, spreston@tol-av.com**, greeting "Sean,". Same format
Stacey uses for the TOL menu-sales reports (greeting / summary w/ bold total /
PNG inline / "Sent from Tekion Open API — live data" / Joe's HTML signature).
Subject e.g. "TOL Alignment Sales by Advisor — June MTD (6/1-6/29)". Hand off via
`~/bin/ask-agent stacey "..."` with the PNG (inline) + PDF (attach) absolute
paths. DEFAULT = leave as a DRAFT in Joe's Gmail Drafts, DO NOT SEND, unless Joe
explicitly approves auto-send.

## "The month" ambiguity (esp. on the 1st)
When Joe asks for "the alignment report for the month" and today is early in a new
month (e.g. July 1), "the month" almost always means the **just-completed prior
month** (the new month has ~no data). Default to the full prior month
(pass its last day as the as-of arg, e.g. `2026-06-30`), state that assumption in
the reply, and offer to rerun for MTD if that's not what they meant. (clarify tool
may be unavailable in Slack threads — pick the sensible default and note it.)

## Pitfalls
- **Transient OpenAPI read timeout on the FIRST `/repair-orders:search`**
  (`TimeoutError: The read operation timed out` in the traceback, EXIT=1) is a
  known intermittent hiccup on the shared API, NOT a code bug. Recovery: sanity-
  check the API/token with a 1-row probe —
  `python3.11 -c "import tol_menu_sales_api as O; print(O.call('POST','/repair-orders:search',{'filter':{'dealerId':'1092'},'pageSize':1})[0])"`
  (expect `200`), then just rerun the scan. It usually succeeds on the 2nd try.
- Launch the background scan with **`/usr/bin/bash`** (not bare `bash`) or invoke
  the python interpreter directly; the login-shell wrapper otherwise dumps the
  Ubuntu MOTD into the log and can obscure the real EXIT code.
- TL opcodes are NOT SCT's — always use the TL set above. Joe rejects wrong
  opcode assumptions instantly.
- Run the scan in background; foreground will time out on 429 backoff.
- The launcher wrapper shell can linger as a defunct/`RUNNING` match after the
  python child exits — verify by tailing the log for "all candidate ROs scanned"
  and the printed totals, not just `pgrep`.
- Files: `tol_align_scan.py`, `render_tol_align_by_advisor.py` in
  /home/itadmin/tekion-reports. Interpreter
  /home/itadmin/.hermes/hermes-agent/venv/bin/python3.11.
