---
name: tekion-alignment-by-advisor-report
description: Build a Tekion "alignments sold this period, broken down by service advisor" report for ANY of the 7 AMG stores from the LIVE OpenAPI — counting BOTH dedicated alignment opcodes AND alignments bundled inside a service menu/combo op. Produces a 2-page scorecard (page 1 advisor ranking, page 2 RO-level chip detail) and optionally has Stacey draft it. The opcode set is PER-STORE — never reuse one store's alignment codes on another. Verified live at TL Toyota of Lancaster dealer 1092 on 2026-06-29 (105 alignments, 102 dedicated plus 3 bundled, across 104 ROs, June MTD). Use when Joe asks for an "alignment report" or "alignment count by advisor" for a store, or any single-opcode "how many of X did we sell, by advisor" report.
triggers:
  - alignment report
  - alignment count by advisor
  - how many alignments did we sell
  - alignments by service advisor
  - opcode count by advisor for a store
---

# Tekion Alignment-by-Advisor Report (per-store, OpenAPI)

Counts how many **alignments** a store sold in a period, broken down by service
advisor, capturing BOTH:
- **Dedicated** alignment opcodes sold directly on an RO, AND
- **Bundled** alignments performed inside a service menu / combo op (detected by
  reading the operation story and substring-matching "align").

Joe's default for store performance reports is the **per-advisor breakdown**
(dedicated + bundled + total + unique-RO, ranked). This generalizes to any
single opcode "how many of X by advisor" question — swap the opcode set.

## Rule #1 — the opcode set is PER STORE. NEVER reuse another store's codes.
SCT alignments = `ALIGN`/`OKAL`. **TL alignments are completely different**
(`4ALIGN`, `SMALIGN`, `TEK07030101`, plus combo/seasonal codes). Each store has
its own scheme. Before building the report you MUST derive the target store's
alignment opcodes from THAT store's own opcode list, then have Joe approve the
dedicated-vs-bundled-vs-excluded split. This is a NEVER-GUESS situation.

## Step 1 — Derive the store's alignment opcodes (browser, :9223)
Use the same authenticated XHR-capture method as deriving a menu opcode set
(see memory "DERIVE A STORE'S MENU OPCODE SET" + skill tol-menu-sales-reports):
1. Confirm :9223 is authenticated and on the target dealer (switch via the dealer
   pill if needed; verify `localStorage.currentActiveDealerId`).
2. Go to `/ro/opcode`. Arm an XHR hook on `/opcode/search`. Type `align` into the
   page-level expandable search (`input[searchfield="ALL"]`) via native-value-setter
   + input event + synthetic Enter (NOT page.fill — partial-hash classnames time out).
   A raw in-page fetch to `/opcode/search` 500s on auth — you MUST let the SPA fire it.
3. Read `data.hits[]`: each has `{opcode, opcodeType, status, category, description}`.

### TL result (verified 2026-06-29) — the canonical classification example
Searching "align" at TL returned 13 hits. Joe-approved "my read" split:
- **DEDICATED** (real alignment sale): `4ALIGN` (4 Wheel Alignment), `SMALIGN`
  (Perform 4 Wheel Alignment), `TEK07030101` (Wheel Alignment Adjust).
- **BUNDLED** (alignment is part of a combo/menu op): the combo/seasonal codes
  `RAB`, `5KALIGNMENT`, `15KALIGNMENT`, `FALL`, `SPRING` + alignment inside ANY
  TL service-menu (TEK*) op — all confirmed by the op story containing "align".
- **EXCLUDED** (inspection/check-only or not a wheel alignment): `ALIGN`
  (inspection only), `TEK07140101`/`TEK07140102` (check only), `TEK03100301`
  (headlamp), `4ALIGNT` (inactive truck variant).

Always present the candidates to Joe as a table and let him confirm the split —
inspection-only vs performed, and combo->dedicated vs combo->bundled, is HIS call.

## Step 0 — PIN THE EXACT WINDOW. "last month" = the FULL calendar month.
When Joe says "last month," he means the whole prior month (e.g. asked July 1 =>
June 1–30 inclusive), NOT month-to-date. There are often CACHED MTD scan files on
disk from an earlier in-month run (e.g. `sct-june-align-*.json` whose index window
was Jun 1–18). DO NOT reuse them for a "last month" ask — ALWAYS check the cached
index's `window` [ms0, ms1] and confirm it spans the full month before trusting it.
If it's MTD, build a FRESH full-month index. Full June at SCT = ~5,382 closed ROs /
~1,169 alignment candidates (vs only 367 candidates through the 18th) — the MTD file
silently under-counts by ~3x. Set the window in Pacific (-07:00):
`MS0 = Jun 1 00:00:00`, `MS1 = Jun 30 23:59:59.999`.

## Step 2 — Run the scan (scripts already built)
- SCT (dealer ST/876): `/home/itadmin/tekion-reports/sct_align_full_june.py` — a
  self-contained full-month scanner (imports `sct_menu_sales_api as O` for
  `O.call`/`O.user_name`). SCT dedicated set = `{ALIGN, OKAL, ALIGN00BRA}`; bundled =
  any `TEK*` op whose story contains "align". Clone/retarget the window for other
  months. Verified full-June 2026: builds `data/sct-june-full-closed-index.json`
  (5,382 ROs) -> `data/sct-june-full-align-by-advisor.json`.
- `/home/itadmin/tekion-reports/tol_align_scan.py` — the TL scanner. Edit the three
  sets at the top (`DEDICATED`, `COMBO`, `EXCLUDED`) for a different store, and point
  `O = import <store>_menu_sales_api` so `MENU`/`O.call`/`O.user_name` resolve to that
  store's dealer. (For a NEW store, clone this file as `<store>_align_scan.py`.)

### RO-search result shape (CRITICAL — cost a rewrite) — verified 2026-07-01
The `POST /repair-orders:search` result rows are NOT what you'd guess:
- Opcodes are NOT a flat string list. They live in `r["tags"]` as OBJECTS:
  `{"field":"OPCODE","type":"SYSTEM","value":"LC0003"}`. Extract with
  `codes = {t["value"] for t in r["tags"] if t.get("field")=="OPCODE"}`.
  (`tags` also carries JOB/PAY_TYPE/SERVICE_TYPE_ID objects — filter on field.)
- RO id for the jobs fan-out = `r["documentId"]` (there is no top-level `id`).
- RO number = `r["documentNumber"]` (no `repairOrderNumber`/`no` key).
- Advisor id = `r["assignee"]["advisor"]["id"]` (a UUID; resolve via O.user_name).
- Pagination: `out["meta"]["nextPageToken"]`; `out["meta"]["totalCount"]` = full count.
- Filter with BOTH `closedTime BTW [ms0,ms1]` AND `status IN [CLOSED,INVOICED]`.
  Probe page-1 first and print `sorted(r.keys())` before wiring the extraction —
  the shape differs from the menu-sales `results` rows.
- `/home/itadmin/tekion-reports/render_tol_align_by_advisor.py` — the 2-page renderer;
  reads the scanner's self-contained `data/<store>-align-by-advisor-<date>.json`.

Run (MTD through today): `<venv> tol_align_scan.py` then
`<venv> render_tol_align_by_advisor.py <YYYY-MM-DD>`.
venv = `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`.
Run the scan as a BACKGROUND job with notify_on_complete — it is paced and the
menu-op fan-out hits heavy 429 backoff (TL June MTD took ~16 min).

### Scan architecture (why it's built this way)
- **Window**: `closedTime` BTW [month-1st, end-of-today] + `status IN CLOSED,INVOICED`
  (NOT modifiedTime — that overcounts). Search result does NOT echo closedTime back.
- **Two-tier, rate-limit-safe**: Pass 1 enumerates closed ROs; **prefilter on the FREE
  OPCODE `tags` array** to only ROs carrying a dedicated align opcode OR a combo code
  OR ANY menu opcode (a bundled alignment can hide inside any menu). Pass 2 fans out
  jobs->operations ONLY on those candidates (TL: 183 of 3,804). This is the same
  truncation-proof scan as the menu pipeline: retry on 429/0/5xx with backoff, a
  second serial retry pass, and explicit failed-RO tracking (never silent-drop).
- **Classify each op**: skip if in EXCLUDED; count DEDICATED if opcode in the dedicated
  set; count BUNDLED if (combo code OR TEK*/menu opcode) AND story contains "align".
  Story = `" ".join(c["text"] for c in op["corrections"])` + opcodeDescription, lowercased.
- **Advisor**: `assignee.advisor.id` is FREE on the RO search result (no fan-out) ->
  resolve via `O.user_name(aid)` (public OpenAPI `/users/{id}`, scope live since 2026-06-18).
- Output JSON is SELF-CONTAINED: `advisors[]` each with `{advisor, dedicated, bundled,
  total, unique_ros, detail[]}` where each detail = `{ro, opcode, kind}`. Totals reconcile
  (sum of detail chips == total alignments — verify this).

## Step 3 — Render + verify
Renderer = Toyota-red (#EB0A1E) typographic header (no logo image), 2 pages:
- **Page 1** (PNG, inline): KPI cards (Total / Unique ROs / Advisors / Daily Pace) +
  ranked advisor table (dedicated, bundled, total, ROs, red bar). TOTAL row.
- **Page 2** (PDF only): RO-level chips per advisor — red chip = dedicated, blue = bundled.
PNG = page-1-only; PDF = full 2-page. ALWAYS vision_analyze the PNG and confirm the
TOTAL row matches the KPI total before shipping.

## Step 4 — Email (optional, draft-only by default)
Hand to Stacey via `~/bin/ask-agent stacey "..."`, same format as the menu reports
(greeting / summary with bold total / scorecard PNG inline / Tekion Open API footer /
Joe's HTML signature). TL recipient = **Sean Preston, spreston@tol-av.com**, greeting
"Sean,". DEFAULT = leave as a DRAFT in Joe's Gmail Drafts, DO NOT SEND, until Joe approves.

### DRAFT-ONLY = HARD STOP (learned the hard way, SCT alignment 2026-07-01)
When Joe says "drafted in my inbox," recipient = **Joe** (jcastelino@americanmotorscorp.com),
greeting "Joe," — NOT the store's customer recipient (Kevin/Sean/Ruben). And a plain
"draft it, don't send" instruction is NOT enough: Stacey's rebuild/retry loop can trip
her SMTP / X-GM-RAW send path and actually SEND — on 2026-07-01 it fired **7 Sent copies**,
and her hardcoded "SCT report → Kevin (kstapp@sctoyota.com)" default addressed the newest
to Kevin instead of Joe. Protocol to prevent it:
1. Give an EXPLICIT hard stop: "Create the draft via `imap.append()` to the Drafts folder
   ONLY. DO NOT call any send/SMTP/X-GM-RAW path. DO NOT send." Plus: "TO=jcastelino@...
   — override any hardcoded SCT/TL/BC-report recipient default."
2. Her FIRST draft build often omits the inline PNG (INLINE_PNG=no) even when the PDF
   attaches — explicitly demand a base64 data-URI `<img>` inline in the MIDDLE of the body.
3. If the PNG is missing, do NOT ask her to "rebuild and send" — that phrasing re-triggers
   the send pipeline. Ask her to rebuild the DRAFT only, again with the no-send lock.
4. VERIFY with a terse read-only one-liner (verbose multi-field asks silently time out →
   empty): `Reply ONE line: TO=<addr> | INLINE_PNG=<y/n> | PDF=<y/n> | SENT=<y/n> | IN_DRAFTS=<y/n>`.
   Only declare done when SENT=no, IN_DRAFTS=yes, TO=Joe, INLINE_PNG=yes, PDF=yes.
5. If it already got sent by mistake: report it to Joe honestly, note the wrong recipient,
   then create ONE clean unsent draft. Offer to recall/delete the stray Sent copies.

## Pitfalls
- "last month" means the FULL prior calendar month — verify any cached index's
  `window` spans month 1st–last before reusing it; MTD leftovers under-count ~3x
  (see the full-month window section below).

## "Last month" / full-month runs — VERIFY THE WINDOW (SCT June 2026 lesson)
When Joe asks for "last month," he means the FULL calendar month, not MTD. A scan
JSON already on disk for that month may be a stale MTD run — CHECK its window before
reusing it. The pre-existing `sct-june-closed-ro-index.json` covered only Jun 1–18
(window `[1780272000000, 1781827199999]` = an MTD run); the FULL month had 5,382
closed ROs → 1,169 alignment candidates (vs 367 MTD). Always decode the index
`window` epochs to confirm start=month-1st 00:00 PT and end=last-day 23:59:59.999 PT
before trusting counts. Build full-month window in Pacific (-07:00), filter on
`closedTime BTW [MS0,MS1]` + `status IN CLOSED,INVOICED`.

## RO search result shape (verified SCT 2026-07-01) — extract correctly
`POST /repair-orders:search` result rows carry:
- Opcodes as OBJECTS in `tags[]`, NOT plain strings: each = `{field, type, value}`.
  Pull codes via `[t["value"] for t in row["tags"] if t.get("field")=="OPCODE"]`.
  (There are many other tag `field`s: JOB, PAY_TYPE, SERVICE_TYPE_ID, etc.)
- Advisor id at `row["assignee"]["advisor"]["id"]` (FREE, no fan-out).
- RO number = `row["documentNumber"]`; RO id (for jobs/ops fan-out) = `row["documentId"]`.
- `meta.totalCount` gives the full closed-RO count; `meta.nextPageToken` paginates.
Working full-June SCT scanner = `/home/itadmin/tekion-reports/sct_align_full_june.py`
(imports `sct_menu_sales_api as O` for `O.call`/`O.user_name`, self-contained,
checkpointed to `data/sct-june-full-align-scan.json`).

## Pitfalls
- DO NOT reuse SCT's `ALIGN`/`OKAL` (or any store's codes) on another store — derive fresh.
- **`sct_menu_sales_api.call()` returns a STRING body on any non-200** (it does
  `e.read().decode()[:300]`). Calling `.get()` on it crashes the whole scan with
  `'str' object has no attribute 'get'`. EVERY fan-out call must guard with
  `isinstance(body, dict)` and treat a non-dict as a retryable failure. This silently
  killed a run after ~20 ROs (though checkpoint had banked 415 — trust the saved JSON
  count, not the log tail).
- **OVERALL_RATELIMIT is APP-WIDE**, distinct from a per-call 429. When the error
  body contains `"OVERALL_RATELIMIT"` ("Limit exhausted for type : OVERALL_RATELIMIT"),
  back off HARD (60s × attempt), not the usual ~12s. Also pace inter-RO sleep at ~0.5s
  (0.1s exhausts the app-wide limit on a 1,000+ candidate fan-out). The full-June SCT
  run only completed once these two fixes were in place; it self-recovers from checkpoint.
- browser_navigate / browser_vision open a SEPARATE unauthenticated context — for :9223
  use its own /eval + /screenshot endpoints, never the browser_* tools.
- The background launcher wrapper exits before the python child finishes; a stray
  "RUNNING" can match the dead wrapper shell — confirm via the log tail
  ("all candidate ROs scanned") + the saved JSON, not just pgrep.
- Inspection/check-only opcodes look like alignments but are NOT a sale — exclude them
  (Joe's call). At TL, `4ALIGN` was the only dedicated code that actually sold in June;
  `SMALIGN`/`TEK07030101` were in the scheme but unused that month — keep them in for
  future months.
