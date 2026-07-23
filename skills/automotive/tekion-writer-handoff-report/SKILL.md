---
name: tekion-writer-handoff-report
description: Build a Tekion "repair orders that closed under a DIFFERENT service writer than they were opened/created with" report for any AMG store from the LIVE OpenAPI. Produces RO#, dollar total, opened-by writer, closed-by writer, date opened, date closed. Use when Joe asks for a service-writer handoff / reassignment audit ("ROs that started with one writer and ended with another", "who opened vs who closed", writer-change report).
triggers:
  - service writer handoff report
  - ro closed with different writer
  - writer reassignment audit
  - who opened vs who closed the ro
  - repair orders that changed service advisor
  - advisor change over report
  - advisor changeover report
---

# Tekion Service-Writer Handoff Report (LIVE OpenAPI)

Finds repair orders CLOSED in a period where the **creating user** (opened-with)
differs from the **final service advisor** (closed-with). Verified SCT June 2026:
341 of 5,381 June-closed ROs had a writer change. Built 2026-07-01 on Joe's ask.

## Data model — the hard-won facts (DO NOT re-derive by guessing)
The public OpenAPI gives exactly TWO writer signals per RO, both FREE on the
`repair-orders:search` result row (no fan-out):
- **Opened-with** = `createdByUserId.id` — the user who physically CREATED the RO.
- **Closed-with** = `assignee.advisor.id` — the service advisor assigned at close.

There is **NO advisor-reassignment audit trail** in the public API. Confirmed by
probing: `/repair-orders/{id}/history`, `/audit`, and `/activity` ALL return 404.
So "opened-with vs closed-with" = created-by vs final-advisor is the ONLY handoff
signal available. When they differ, the RO was created by one person and closed
under a different advisor.

⚠️ **NUANCE TO FLAG TO JOE (not a guess — a real caveat):** `createdByUserId` is
*whoever created the RO*, which at some stores is a GREETER / CHECK-IN / BDC person,
NOT a service writer. At SCT the #1 "opened-with" name was **Jasmine Perez (86 ROs)**
— if she is a check-in person, those are normal check-in→writer flow, not true
writer-to-writer handoffs. Resolve the top creators and TELL Joe which look like
check-in staff vs writers; offer to exclude check-in names for a pure writer-to-writer
view, but DEFAULT to keeping everyone in with a note and let Joe decide.

## Dollar figure — `/ro-invoices`, sum invoiceAmount across pay types
`GET /repair-orders/{id}/ro-invoices` → `data.roInvoices[]`, each with `payType`
(CUSTOMER_PAY / WARRANTY / INTERNAL) and `invoiceAmount`. **Total RO $ = sum of
invoiceAmount across all pay types, THEN DIVIDE BY 100.**

🚨 **CRITICAL — `invoiceAmount` IS IN CENTS (integer).** ALL Tekion OpenAPI dollar
fields (invoiceAmount, labor.saleAmount/costAmount, parts saleAmount/costAmount) are
integer CENTS — always `/100`. This bit the 2026-07-01 SCT run HARD: raw sum produced
a **$22,615,080 total / $1.5M single RO** (e.g. RO 567022 warranty `1561543`). After
`/100` it reconciled to the correct **$226,150.80 total / $15,615.43 top RO**.
SYMPTOM YOU MUST RECOGNIZE: any per-RO figure in the hundreds-of-thousands or a store
total in the millions = you forgot `/100`. `sct_menu_sales_api.scan_ro` already `/100`s
its amounts — mirror that. (Note: an older version of this skill wrongly said "RO 571821
= $2,500" — that raw 250000 is actually $2,500... only IF already-cents; the safe rule
is ALWAYS `/100`, no exceptions.)

`invoiceNumber` is always null and `closedTime` on the invoice is 0 — do NOT rely
on those. This is ONE call per RO (no deep jobs/operations fan-out needed for $).

## Dates — creationTime (open) + modifiedTime (close proxy)
- **Date opened** = RO `creationTime` (also on the search row as `ct`).
- **Date closed** = RO `modifiedTime` from `GET /repair-orders/{id}`. The search
  result and detail both return `closedTime` as NULL even though it is filterable
  server-side. For a RO with `status` CLOSED/INVOICED, `modifiedTime` = the close
  timestamp (verified RO 571821: created 6/30 15:38, modified 6/30 18:00, CLOSED —
  modified IS the close). Accurate to the day. Don't chase a true closedTime field;
  it isn't returned.

## Advisor/user name resolution
`O.user_name(uid)` (public `/users/{id}`, works for numeric ids AND UUIDs). All 23
distinct users on the SCT mismatch set resolved to real human names.

## Build sequence (scripts in /home/itadmin/tekion-reports/)
Interpreter: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`. Import
`sct_menu_sales_api as O` for `O.call` + `O.user_name`.

**PREFERRED reference impl: `sct_writer_handoff_july.py`** — fully SELF-CONTAINED
(builds its own index via closedTime BTW + status IN CLOSED,INVOICED, resolves
names, fans out). Copy it and edit MS0/MS1 + the file-name constants for a new
period/store. The older `sct_writer_handoff_june.py` DEPENDS on a pre-built
`sct-june-writer-index.json` that gets cleaned up — don't reuse it directly.
The `_call` helper also handles `OVERALL_QUOTA` (not just OVERALL_RATELIMIT).
Runtime calibration: July 2026 MTD (14 days, ~215 mismatches) ran end-to-end in
~4 min. May 2026 FULL month (5,355 closed ROs indexed, 322 mismatches) ran ~7 min
as a background process. Renderer for a new period = `sed` the period strings +
json/output file names in render_writer_handoff.py (see render_writer_handoff_july.py;
full-month variant = sct_writer_handoff_may.py + render_writer_handoff_may.py —
fixed MS1 = first ms of the NEXT month instead of now()).

⚠️ "Do the same thing for <month>" TRAP (2026-07-15): Joe's follow-up asks like
"can you do the same thing for May?" arrive in FRESH sessions with no context —
I guessed the most-recent report (TXM open-times) and burned a full scan before
he corrected me to THIS report ("the advisor change over report you built for SCT").
When "the same thing" is ambiguous across recent reports, name the report you think
he means in one line BEFORE launching a heavy scan, or ask. Cheap confirmation beats
a wasted 10-min API scan.

⚠️ execute_code + read_file CACHE QUIRK: inside execute_code, hermes_tools
read_file can return the literal string "File unchanged since last read..." instead
of content (if the file was already read this conversation) — string-transforming
that output writes a broken file. For copy-and-edit of an existing script, use
plain `sed` in terminal or write the new file directly with write_file.
1. **Enumerate + capture writer fields (no fan-out).** Page through
   `repair-orders:search` with `closedTime BTW [ms0,ms1]` + `status IN CLOSED,INVOICED`,
   capturing per RO `{no:documentNumber, id:documentId, cb:createdByUserId.id,
   adv:assignee.advisor.id, ct:creationTime}` → `data/<store>-<period>-writer-index.json`.
   (Note: closedTime works fine as a server-side FILTER even though it comes back null
   in the payload.)
2. **Filter mismatches:** `cb and adv and cb != adv`. Resolve distinct users to names
   once → `data/<store>-<period>-writer-names.json`.
3. **Fan out ONLY the mismatch set:** per RO fetch `/ro-invoices` ($ total) +
   `/repair-orders/{id}` (modifiedTime = close). Checkpoint every 25. 341 ROs × 2
   calls ≈ 5-8 min, well under the rate limit at 0.2s pacing.
   Reference impl: `sct_writer_handoff_june.py` (edit window/store for reuse).
4. Sort rows by $ desc; emit `{count, total_dollars, rows[]}` where each row =
   `{ro, total, opened_by, closed_by, date_opened, date_closed}`.

## Rate-limit safety (same trap as every other Tekion scan)
`O.call` returns a STRING body on non-200. Use a `_get()` helper that guards
`isinstance(body, dict)` and, on a string body containing `OVERALL_RATELIMIT`,
backs off `60*(att+1)`s (regular 429/5xx → `12*(att+1)`s). Without this the scan
dies with `'str' object has no attribute 'get'`.

## Render + email
Render a table (RO# | $ | Opened By | Closed By | Date Opened | Date Closed),
sorted by $ desc, with a summary line (count + total $). Toyota-red header like the
alignment report. Reference impl: `render_writer_handoff.py` — outputs a summary PNG
(KPIs + top handoff pairs + top receivers), a full-table PDF, AND a **CSV**. Joe likes
the CSV for data reports he'll sort/filter — always include it for this report.

Email via Stacey. Verified 2026-07-01 SEND flow (Joe said "email it to me" = SEND, not
draft): give Stacey ONE explicit instruction with hard rules — TO=Joe ONLY
(jcastelino@americanmotorscorp.com), do NOT use any hardcoded Kevin/SCT-report default,
do NOT cc, send exactly ONCE (no retry/rebuild loop), embed the PNG as base64 data-URI
INLINE (not CID), attach BOTH the PDF and the CSV, Joe's HTML signature. Then VERIFY via
a read-only Sent-folder check (time | TO | subject | HAS_PDF | HAS_CSV) — Stacey's own
"SENT=yes" line is not sufficient (she over-reports).

🚨 GMAIL SELF-SEND DEDUP (bit Joe 2026-07-15): when From==To==Joe, Gmail files the
message ONLY under Sent Mail — it never appears in his Inbox view. Even IMAP-appending
a copy to INBOX is NOT enough if it keeps the original (older) Date header / \Seen flag:
Gmail sorts it below the fold and Joe reports "I don't see it". RELIABLE FIX: append a
FRESH message to INBOX via imaplib with a CURRENT Date header, UNREAD (do not set \Seen),
subject suffixed "(resend)" — it lands unread at the top of the inbox. Verify with an
IMAP INBOX search for the resend subject, not Sent Mail. For a DRAFT-ONLY ask instead, obey
the DRAFT-ONLY TRAP in skill `sct-alignment-by-advisor-report`.
Side effect (seen 2026-07-16 May-report send): SMTP delivery + the INBOX-copy append can
BOTH land in the inbox = two copies. Harmless; tell Joe to delete one rather than trying
to dedupe. Verified May 2026 full-month result for comparison baselines: **322 handoff ROs
of 5,355 closed, $160,186.83** (vs June: 341 / $226,150.80) — top pairs Jasmine Perez→
Carlos Garcia (102), Jasmine Perez→Michael Parayo (43), Adam Esquivel→Carlos Garcia (41).

## Sort order (Joe's preference, 2026-07-02)
Joe wants the full RO table + CSV **grouped by CLOSING advisor (A–Z)** with a
per-advisor subtotal header row (N ROs · $X), ROs sorted by $ desc within each
advisor — NOT globally ranked by $. renderer already does this.

## Draft-building — do it YOURSELF via imaplib (2026-07-02)
Stacey's draft build produced an `<img>` with NO src attribute (broken image in
Gmail) even after explicit data-URI instructions. Reliable path: build the MIME
yourself with python imaplib/email using himalaya's creds
(~/.config/himalaya/config.toml), `M.append('"[Gmail]/Drafts"', '(\\Draft)', ...)`.
Gotchas: (1) inline PNG = `<img src="data:image/png;base64,...">` in the text/html
alternative part; (2) CSV must be `MIMEText(..., 'csv')` → text/csv (MIMEApplication
_subtype='csv' gives application/csv); (3) deleting an old Gmail draft needs
copy-to-'"[Gmail]/Trash"' + \\Deleted + expunge (plain \\Deleted+expunge alone can
leave it resurrected); (4) verify final state byte-level: exactly 1 draft, data-URI
present in HTML, PDF + text/csv attachments, Sent-folder search empty.

## Pitfalls
- NEVER claim a report was "emailed/drafted" from memory — VERIFY in the actual
  mailbox first (search Drafts/Sent/All Mail for the subject). On 2026-07-02 I told
  Joe the handoff report was "already emailed" when the email step never ran; a
  mailbox search proved it. Report delivery status only from a live mailbox check.
- Do NOT claim a true "original service advisor" history exists — it doesn't in the
  public API. Created-by is the proxy; state that plainly to Joe.
- Check whether top "opened-with" names are check-in/greeter staff before calling
  them writer handoffs.
- `invoiceNumber`/invoice `closedTime` are null — don't use them.
