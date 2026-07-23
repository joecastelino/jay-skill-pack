---
name: bc-menu-sales-reports
description: >
  Run the Blackstone Chevrolet & Cadillac (BC, a GM store, dealer 1251) Menu
  Sales scorecards — Daily Closed (2x/day) and Closed Month-To-Date (1x/day) —
  from the LIVE Tekion OpenAPI, and have Stacey DRAFT them to Ruben Estrada
  (Restrada@blackstonegm.com). This is the GM-store sibling of the SCT/Kevin
  pipeline (sct-menu-sales-api-scorecard). Use for any "BC menu report",
  "Blackstone Chevy/Cadillac menu sales", or Ruben report request.
trigger: BC menu sales, Blackstone Chevrolet Cadillac menu report, Ruben menu report, BC daily closed, BC closed MTD, blackstonegm report
---

# BC (Blackstone Chevrolet & Cadillac) Menu Sales Reports

GM-store sibling of `sct-menu-sales-api-scorecard`. Same architecture, different
dealer + opcode set + branding + recipient. **Stacey DRAFTS; she does not send
unless Joe says so.** Recipient = **Ruben Estrada <Restrada@blackstonegm.com>**.

## The opcode-mapping divergence (CRITICAL — differs from SCT)
The SCT principle is "a menu = the frozen set of interval-menu opcodes." At SCT
those were tagged serviceType **"Maintenance Service"**. At **BC that is WRONG** —
BC's "Maintenance Service" serviceType (`629607f6857aba0007201fc6`) holds only 18
à-la-carte `INDIVIDUAL_SERVICE` opcodes (brake fluid exchange, battery service…),
NOT menus. **BC's menu packages are tagged serviceType "Service Menu"
(`65530c2bd0e3ef410082b54f`).** The correct BC menu set =
**`opcodeType == "SERVICE_MENU"` AND `status == "ACTIVE"`** = **212 opcodes**,
all `TEK*`-prefixed mileage-interval packages (10K–110K+ mi × 4 tiers
BNM/BSM/PSM/VNM × 53 intervals). Frozen to
`/home/itadmin/tekion-reports/data/bc-menu-opcodes.json`.
Always re-derive per store from the data — never assume SCT's serviceType.

## How the opcode set was derived (re-run to refresh)
Cross-dealer read works from the `:9223` session even while it's on dealer 876 —
just override the headers `dealerId:"1251"` + `tek-siteId:"-1_1251"`:
1. `GET /api/service-module/u/opcode/serviceTypes` → find BC "Service Menu" id.
2. `POST /api/service-module/u/opcode/search` body
   `{pageInfo:{start:N,rows:50},searchText:"",sort:[{order:"DESC",field:"createdTime"}],filters:[],nextPageToken:null,searchFields:["OPCODE","DESCRIPTION","CONSUMER_SCHEDULING_NAME"]}`.
   **Records are in `data.hits`; `data.count` = total.** Page by incrementing
   `pageInfo.start` by 50 until `hits` empty / got==count (~24 pages for 1196).
3. Freeze `opcodeType==SERVICE_MENU && status==ACTIVE` → 212 rows, schema
   `{opcode,category,status,opcodeType,desc,serviceTypeIds,id}`.

## Dealer
BC = `cfg["dealers"]["bc"]` = `americanmotorscorporation_1251_0` (dealerId 1251,
siteId `-1_1251`).

## Scripts (in /home/itadmin/tekion-reports/)
Interpreter: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`
- `bc_menu_sales_api.py` — base module (copy of SCT's, dealer→bc, opcode list→
  bc-menu-opcodes.json, advisor browser-fallback dealerId→1251, BC labels/files).
- `bc_menu_sales_closed_mtd.py` — imports `bc_menu_sales_api as O`. Modes:
  - `--seed` : one-time paced full-month backfill → master
    `bc-menu-closed-mtd-MASTER-<YYYY-MM>.json`, emits MTD RB file
    `bc-menu-sales-closed-<date>.json`.
  - (default) : today-only closed append to master + re-emit MTD file.
  - `--daily-only` : **emit STANDALONE Daily Closed** `bc-menu-sales-daily-<date>.json`,
    does NOT touch the MTD master. ← use for the twice-daily Daily Closed report.
- `render_scorecard_bc.py <json>` — BC branding (typographic BLACKSTONE /
  CHEVROLET·CADILLAC header, GM-blue `#0b4a8f`, dealer+title from JSON). Detects
  report type: "daily"→Daily Closed title, "closed"→MTD title, else Opened.
  Output stems `BC-Menu-Sales-Daily-Scorecard-*` / `BC-Menu-Sales-Closed-Scorecard-*`.

## Run sequence
**Daily Closed** (noon + 5pm):
```
cd /home/itadmin/tekion-reports
<py> bc_menu_sales_closed_mtd.py --daily-only          # → bc-menu-sales-daily-<today>.json
<py> render_scorecard_bc.py data/bc-menu-sales-daily-<today>.json
```
**Closed MTD** (once daily): first of month `--seed`, thereafter default append:
```
<py> bc_menu_sales_closed_mtd.py        # appends today, re-emits MTD; --seed to rebuild month
<py> render_scorecard_bc.py data/bc-menu-sales-closed-<today>.json
```

## ☠️ PARALLEL STACEY AUTO-SEND PIPELINE EXISTS (discovered 2026-07-09)
Stacey (email-agent) runs her OWN BC cron jobs (noon Opened, 5:05pm Opened, 7pm
Closed) with skill `email/bc-menu-sales-report-email` that AUTO-SENDS via SMTP
to Ruben + CC Art Markarian + Joe — no drafting. During the 7/8–7/9 quota
outage her skill instructed her to SYNTHESIZE a $0 empty JSON and send a $0
"placeholder" report — Ruben got "0 menus, $0" emails and Joe flagged "GM open
service menus are wrong." That skill clause was patched 2026-07-09 (never
synthesize; skip + notify Joe only). If BC numbers ever look wrong at the
recipient end, CHECK STACEY'S PIPELINE FIRST — her jobs write to the same
data/bc-menu-sales-opened-<date>.json paths and can overwrite/pollute with
synthetic zeros (quarantine dir: data/quarantine-synthetic/). Jay's own noon/5pm
Daily Closed + 6:15pm MTD cron jobs are separate and draft-only.

## Quota exhaustion (429 OVERALL_QUOTA) — hit 2026-07-08, ~12h outage
`repair-orders:search` can return
`429 ... "Limit exhausted for type : OVERALL_QUOTA"` — this is an **ORG-WIDE
OpenAPI daily quota**, not per-dealer and not transient rate-limiting. Backoff
does NOT help; on 7/8 it stayed exhausted 11+ hours (burned overnight by the
Caliber invoice scrape + TOL backfill retries). Playbook:
1. Confirm it's org-wide, not you: check sibling pipeline logs —
   `tail data/tol-closed-backfill-*.log` (429 probe watcher) and
   `~/caliber-ops/logs/tekion-nightly.log`. If they're 429-ing too, stop.
2. Try a few PACED attempts (~10 min apart, max ~1h total), then GIVE UP and
   report the failure. Do not hammer — you're competing with the same quota.
3. Do NOT render/draft stale master data as today's report. Report last
   known-good MTD numbers from the master (labeled as-of date) for reference.
4. **Missed-day catch-up is MANDATORY**: the default append scans TODAY only,
   so a skipped day silently drops from the MTD master. The script takes an
   optional positional date: `bc_menu_sales_closed_mtd.py 2026-07-07` appends
   that day's closed ROs. After an outage, append EACH missed date FIRST (one
   run per date, oldest first), then run today's default append, then render + draft.
5. Confirmed recurrence 2026-07-08 PM: quota still exhausted 12:30–13:40 PT
   (6 paced attempts, all 429; TOL probe watcher 429 in parallel). Playbook held:
   no stale draft, reported last-good MTD, flagged 2 owed catch-up dates.
6. STILL exhausted at the 5pm run 2026-07-08 (attempts 17:10–17:54 PT, 5 total,
   all 429; TOL probe 429 through 17:31+). Full-day outage — quota likely resets
   at Tekion's daily boundary (midnight UTC ≈ 5pm PT was NOT the reset). Owed
   catch-ups as of 7/8 EOD: 07/07 and 07/08 (master asof 2026-07-06).
7. STILL exhausted at the 6:26pm MTD run 2026-07-08 (6 paced attempts
   18:29–19:34 PT, all 429; TOL probe 429 through 19:07+). So midnight UTC
   (5pm PT) is definitively NOT the reset boundary. Next likely reset: Tekion's
   own daily window (possibly midnight PT/ET). First run on 7/9 must append
   07/07 then 07/08 (positional-date runs, oldest first) before today's append.
8. STILL exhausted at the noon Daily Closed run 2026-07-09 (6 paced probes
   12:19–13:10 PT, all 429). >36h continuous outage — this is NOT a daily-reset
   quota anymore; likely the org quota was re-exhausted immediately at reset by
   another consumer, or Tekion changed/zeroed the org allotment. If a 3rd
   consecutive day 429s, escalate to Joe that the OpenAPI org quota itself needs
   investigation (which app/consumer is burning it, or ask Tekion to raise it).
   Owed catch-ups as of 7/9 noon: 07/07, 07/08, 07/09 (master asof 2026-07-06).
9. STILL exhausted at the 5pm Daily Closed run 2026-07-09 (5 paced attempts
   17:12-18:04 PT, all 429). That makes 3 CONSECUTIVE DAYS (7/7 eve? -> 7/8 full
   day -> 7/9 full day) = the escalation threshold from point 8 is MET. Escalated
   to Joe: the Tekion OpenAPI ORG quota itself needs investigation — identify
   which app/consumer burns it at reset, or ask Tekion to raise the allotment.
   Owed catch-ups as of 7/9 EOD: 07/07, 07/08, 07/09 (master asof 2026-07-06).
10. STILL exhausted at the 6:15pm MTD run 2026-07-09 (6 paced attempts
   18:20-19:26 PT, all 429 on the 07/07 catch-up append). Zero successful BC
   pulls on 7/9 — full third consecutive day. Escalation to Joe already fired
   at the 5pm run; no re-escalation needed same evening. No draft made (no
   stale data). Owed catch-ups unchanged: 07/07, 07/08, 07/09
   (master asof 2026-07-06, 20 menus $9,112.98).
11. RESOLVED 2026-07-10 AM: quota restored (Joe said "the API was fixed" —
   coincides with the Enterprise Tier 1 upgrade, org quota 100K→1M/30d). All 3
   owed catch-up dates appended per step 4 (07/07 +2, 07/08 +6, 07/09 +6 menus),
   then today's append → MTD whole again (34 menus $10,791.47 as of 7/10).
   The catch-up-oldest-first playbook worked exactly as written.

### Reading the MTD master for last-known-good numbers (during an outage)
`data/bc-menu-closed-mtd-MASTER-<YYYY-MM>.json` schema:
`{month, asof, updated, records}` where **`records` is a DICT keyed
`"<RO>|<opcode>"`** (e.g. `"98099|TEK45000BNM"`), NOT a list. Each value:
`{date:"MM/DD/YY", ro, opcode, year, make, model, mileage, labor_gross,
labor_price, parts_gross, parts_price, job_type, pay_type, advisor, total_gross}`.
Report **customer-facing totals from `labor_price` + `parts_price`** (the
scorecard's labor$/parts$), not the `_gross` fields. Menus count =
`len(records)`; per-advisor / per-day = Counter over `advisor` / `date`.
Always label the numbers with the master's `asof` date.

## Reliability (inherited from SCT pipeline)
- Prefilter on FREE `OPCODE` tags → only ROs carrying a TEK menu opcode get a
  jobs/operations fan-out (BC: ~126 of 1791 closed ROs for the month). Truncation-
  proof: run must print `✓ all candidate ROs scanned`. BC volume is small
  (~90 closed ROs/day) so rate-limit risk is low; still don't re-run to "double check".
- Advisor names resolve via public OpenAPI `/users/{id}` — verified clean for BC
  (Juan Ramirez, Dimetri Reynoso, Erik Mercado, Lindsay Paris, Jeremia Navarro,
  Michael Reyes, Houa Moua, Jacob Debussey, Valentine Nolasco). No UUIDs/numerics.
- Vision-verify: crop the top ~460px band, upscale 2x, then vision (full-page OCR
  misreads the small KPI digits). JSON totals are authoritative.

## Emailing — Stacey DRAFTS to Ruben (do NOT send unless told)
Give Stacey explicit BC-specific instructions or she'll fall back to Kevin/SCT
defaults. Per draft: TO=Ruben Estrada <Restrada@blackstonegm.com>, greeting
"Ruben,", summary line with bold total, **PNG inline base64 in the middle**, PDF
attached, footer "Sent from Tekion Open API — live data", Joe's signature.
Subjects: `Menu Sales — Daily Closed Performance Report — BC m/d/yy` and
`Menu Sales — Closed Month-To-Date Performance Report — BC m/d/yy`.

VERIFY INDEPENDENTLY (Stacey's word is not proof):
- Direct IMAP check via himalaya (PATH=/home/itadmin/.local/bin):
  `himalaya envelope list --folder '[Gmail]/Drafts'` → grep "BC m/d".
  `himalaya message read <id> --folder '[Gmail]/Drafts'` → grep
  `data:image/png;base64` (inline PNG present), `To:` (must be Restrada, NOT Kevin).
  `himalaya envelope list --folder '[Gmail]/Sent Mail' | grep -ic "BC m/d"` must
  be 0 for a draft-only task.
- Known trap: first build often comes back HASPNG=no (Stacey's check misreads, or
  the inline image really dropped) — re-ask her to REBUILD with the base64 PNG
  embedded inline in the middle of the body; then re-verify HASPNG via raw IMAP.

## Daily OPENED report (verified 2026-06-29) — no dedicated script needed
BC has NO separate "opened" script. The base module's DEFAULT run IS the opened
pull (today's ROs by `creationTime`, identical to the SCT base module):
```
cd /home/itadmin/tekion-reports
<py> bc_menu_sales_api.py                                  # → bc-menu-sales-opened-<today>.json (+ -api-)
<py> render_scorecard_bc.py data/bc-menu-sales-opened-<today>.json
```
The renderer auto-titles "Daily Opened Performance Report" because the opened
JSON `report` field contains neither "daily" nor "closed" (the type-detect
fallthrough = Opened). Output stem `BC-Menu-Sales-Scorecard-<today>.png/.pdf`
(NO "Daily"/"Closed" infix — distinct from the closed stems). Verified 6/29:
3 menus, $809.64 labor / $382.52 parts = $1,192.16, advisors Erik Mercado +
Jacob Debussey resolved clean. Recipient for Opened is STILL Ruben (same as the
closed reports) unless Joe says otherwise. Subject:
`Menu Sales — Daily Opened Performance Report — BC m/d/yy`.

## EMAIL VERIFICATION — himalaya CANNOT confirm the inline PNG; Stacey's raw-MIME check is the authority (hit 2026-06-29)
Do NOT trust `himalaya message read <id>` (or `--raw`, or `--no-headers`) to
verify the inline base64 PNG on a draft Stacey built:
- `message read` renders only the DISPLAY body and strips MIME structure, so
  `grep -c "data:image/png;base64"` returns **0 even when the image IS embedded**
  — a FALSE negative that sends you in circles.
- `--raw` returned **0 bytes** on this himalaya version (flag unsupported here).
- himalaya CAN reliably verify: the `To:`/`Subject:` headers, that a PDF
  attachment exists (`attachment download` lists it), and the Sent-folder count
  (`envelope list --folder '[Gmail]/Sent Mail' | grep -ic "<subj key>"` must be 0
  for a draft-only task). Use himalaya ONLY for those.
- For the INLINE-PNG presence, ask **Stacey** to confirm she checked the raw MIME
  herself (she has the working base64 pipeline). Her raw-MIME confirmation is the
  authority; your himalaya grep is not.

### Stacey build/rebuild traps (2026-07-18 run — took 3 passes)
- **She copies formatting instructions LITERALLY**: asking for "a bold total"
  produced body text `= a BOLD total of $1,082.33`. Phrase it as markup from the
  start: give her the exact summary sentence with `<b>$X</b>` inline.
- **Rebuilds mutate headers**: a rebuild flipped From display-name to "Jay" and
  auto-added Cc Art Markarian + Joe (her auto-send pipeline's defaults bleeding
  in). Always specify From `Joe Castelino <jcastelino@americanmotorscorp.com>`
  and "TO Ruben only, NO Cc" explicitly on every rebuild, and himalaya-check the
  From/Cc lines, not just To.
- **Header-only fix requests drop the attachments**: asking her to "just fix
  From/Cc" produced a draft with HASPNG=no AND HASPDF=no. Any rebuild ask must
  restate the FULL build spec (inline base64 PNG path, PDF path, footer, sig).
- **Exit 124 recovery pattern that works**: after an ask-agent timeout, don't
  re-fire the action. Send a terse status probe — `"Reply with just: DONE
  <new-id> or NOT-DONE"` — she answered `DONE 40449` instantly, confirming the
  timed-out rebuild had completed. Then verify the draft contents yourself.
- **PDF attachment CAN be verified via himalaya**: `himalaya attachment
  download <id> --folder '[Gmail]/Drafts'` succeeding proves the PDF is there
  (only the inline PNG needs Stacey's raw-MIME check).

### Rebuild churn leaves DUPLICATE + WRONG-RECIPIENT drafts — clean to exactly ONE
When the first build comes back without the inline PNG and you re-ask Stacey to
rebuild, expect MULTIPLE leftover drafts at the same subject (saw 4: 39046/48/49/50).
**Duplicates also occur on a SINGLE first-build ask with NO rebuild** (2026-07-11:
one request produced drafts 39802 + 39803 one minute apart, subject differing only
em-dash vs hyphen, both to Ruben). So the dedupe pass below is UNCONDITIONAL —
run it after EVERY Stacey build, keep the LATEST draft (her verified HASPNG one),
expunge the rest via `flag add <id> deleted` + `folder expunge`.
Worse: **two of the rebuild drafts leaked recipient `David Fowlkes
<dfowlkes@americancustomers.com>`** instead of Ruben (a cross-contamination in
Stacey's rebuild path). Always, after a rebuild:
1. `himalaya envelope list --folder '[Gmail]/Drafts' | grep -i "BC m/d"` → list ALL.
2. Verify the `To:` on EACH (wrong-recipient leak is common) — delete any not to
   `Restrada@blackstonegm.com`.
3. Ask Stacey to DELETE all but ONE correct Ruben draft and confirm the kept one
   has the inline base64 PNG (her raw-MIME check). End state MUST be exactly 1
   draft to Ruben.
4. Final himalaya verify: exactly 1 BC m/d draft, `To: Ruben`, Sent count = 0.
5. Deleting stale drafts yourself: `himalaya message delete <id>` FAILS on this
   account ("No folder Trash"). Working method: `himalaya flag add <id> deleted
   --folder '[Gmail]/Drafts'` then `himalaya folder expunge '[Gmail]/Drafts'`.
6. Twice-daily cadence note: the 5pm Daily Closed run supersedes the noon draft
   at the same subject — delete the noon leftover so exactly ONE remains. Also
   `grep "BC m/d"` in Sent will match the separate Daily OPENED report; filter
   with `grep "Daily Closed"` before declaring a sent-leak.

## "3 reports" clarification (Joe 2026-06-26)
Joe's "same 3 reports as Kevin" = the SCT cadence (Daily Opened run TWICE: noon +
5pm) + MTD once = 3 runs. For BC he asked specifically for **Daily Closed 2x/day +
Closed MTD 1x/day**. Confirm cadence before cron-scheduling.

## No real BC logo yet
blackstonegm.com sits behind Cloudflare / a lander page — couldn't scrape a logo.
Using a clean typographic header. Drop a real logo PNG into the renderer if Joe
supplies one (replace the `.brand` block with an `<img>` like the SCT renderer).

## First run (2026-06-26, verified)
Daily Closed: 5 menus, $798.94 labor / $458.81 parts = $1,257.75.
Closed MTD (Jun 1–26): 122 menus, $24,023.80 labor / $12,090.19 parts = $36,113.99.
Drafted to Ruben (draft IDs 38930 Daily, 38931 MTD), inline PNG + PDF, SENT=NONE.
