---
name: tol-menu-sales-reports
description: Run the Toyota of Lancaster (TOL/TL, dealer 1092) Menu Sales scorecards — Daily Opened and Closed Month-To-Date — from the LIVE Tekion OpenAPI, and have Stacey DRAFT them to Sean Preston (spreston@tol-av.com). The Toyota-store sibling of the SCT/Kevin (sct-menu-sales-api-scorecard) and BC/Ruben (bc-menu-sales-reports) pipelines. Use for any "TOL/TL/Toyota of Lancaster menu report" or "Sean Preston report" request.
triggers:
  - toyota of lancaster menu sales
  - TOL menu report
  - TL menu sales
  - Sean Preston report
  - lancaster opened closed menu
---

# Toyota of Lancaster (TOL/TL) Menu Sales Reports

The TL (Toyota of Lancaster) menu-sales pipeline. Sibling of `sct-menu-sales-api-scorecard`
(SCT/Kevin) and `bc-menu-sales-reports` (BC/Ruben). **Load `agent-to-agent-bridge` too**
(Stacey drafts the email). All scripts live in `/home/itadmin/tekion-reports/`.

## Store facts (memorize)
- **Dealer ID = 1092**, siteId `-1_1092`, cfg key `tl` = `americanmotorscorporation_1092_0`.
- **Recipient = Sean Preston, spreston@tol-av.com.** GREETING = **"Sean,"** — NOT "Preston".
  (The `s` in `spreston` is his first initial; do not guess the first name from the address.)
- Store hours: open till 8 PM.
- **Menu opcode set = `data/tl-menu-opcodes.json` = 212 SERVICE_MENU opcodes**
  (53 mileage intervals 5K–200K × 4 tiers BNM/BSM/PSM/VNM). This is the BC-standard
  definition (`opcodeType==SERVICE_MENU && status==ACTIVE`), NOT SCT's looser 316
  "Maintenance Service" list. See `DERIVE A STORE'S MENU OPCODE SET` in memory for how it
  was built (drive the app's own opcode search via :9223 + XHR hook, scroll-paginate).

## Files (the pipeline — already built, prefix is `tol_` not `tl_`)
- `tol_menu_sales_api.py` — **OPENED** report. Default run = today's ROs by creationTime.
  Writes `data/tol-menu-sales-opened-<date>.json`.
  **MUST point `OPCODE_LIST` at `data/tl-menu-opcodes.json`** (was wrongly set to SCT's
  `sct-tek-maintenance-opcodes.json` — fixed 2026-06-29).
- `tol_menu_sales_closed_mtd.py` — **CLOSED MTD**. Modes:
  - `--seed` = full-month backfill (paced, scans every closed RO in the month, prefilters
    to those carrying a TEK menu opcode, fans out only those). **Run this ONCE per month**
    to build the master, or any time the master looks under-populated.
  - default (no flag) = daily-append to MTD master + re-emit MTD JSON.
  - `--daily-only` = standalone daily closed (no MTD).
  Master file = `data/tol-menu-closed-mtd-MASTER-<YYYY-MM>.json`.
  Closed JSON = `data/tol-menu-sales-closed-<date>.json`.
- `render_menu_sales_paged_tol.py <date> [closed]` — renders Toyota-red (#EB0A1E) 2-page
  layout: page-1 advisor-ranking PNG, full multi-page PDF. Output stems:
  - opened: `TOL-Menu-Sales-Scorecard-<date>.{png,pdf}`
  - closed: `TOL-Menu-Sales-Closed-Scorecard-<date>-Paged.{png,pdf}`
  (uses its own headless Playwright — independent of the :9223 session.)

Python interpreter for all of these: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`.

## Run sequence

### Opened (daily)
```sh
cd /home/itadmin/tekion-reports
PY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11
$PY tol_menu_sales_api.py
$PY render_menu_sales_paged_tol.py $(date +%F)
```

### Closed MTD (daily, after seeding the month once)
```sh
$PY tol_menu_sales_closed_mtd.py            # default = daily append + re-emit MTD
$PY render_menu_sales_paged_tol.py $(date +%F) closed
```

### Seed the closed master (first run of a month, or if master is sparse)
```sh
# Back up first, then reseed clean:
cd /home/itadmin/tekion-reports/data
cp tol-menu-closed-mtd-MASTER-$(date +%Y-%m).json{,.bak} 2>/dev/null
rm -f tol-menu-closed-mtd-MASTER-$(date +%Y-%m).json
cd /home/itadmin/tekion-reports
$PY tol_menu_sales_closed_mtd.py --seed     # paced; run as background w/ notify_on_complete
```

## Verify before handing to Stacey
`vision_analyze` each PNG: confirm store = "Toyota of Lancaster", correct period, KPI
totals (menus/labor/parts/total) match between the KPI cards and the table totals,
advisor ranking is sensible, no rendering errors.

## Hand-off to Stacey (DRAFT only)
Use `~/bin/ask-agent stacey "..."`. One message with: recipient `spreston@tol-av.com`,
greeting **"Sean,"**, store "Toyota of Lancaster", the numbers, inline-PNG path, attach-PDF
path, and **"leave as DRAFTS — do not send."** Same Kevin/SCT layout: greeting / summary
with bold total / scorecard PNG inline / "Sent from Tekion Open API — live data" / Joe's
HTML signature. Subjects:
- `TOL Menu Sales — Opened (MM/DD/YYYY)`
- `TOL Menu Sales — Closed MTD (Month D–D, YYYY)`

### VERIFY Stacey's draft after hand-off (learned 2026-07-04, 8PM run)
Stacey's drafts can silently come out wrong — always run a follow-up READ-ONLY ask
(\"list drafts with subject X, take no action, do NOT send\") and check:\n
1. **Inline PNG can be dropped.** Her first EOD attempt saved the draft with the PDF
   attached but NO inline image in the body. If missing, ask her to rebuild the draft
   with the PNG embedded inline (keep PDF attachment).
2. **Stale duplicate drafts.** The noon Opened run leaves a draft with the IDENTICAL
   subject. The 8PM EOD run must have Stacey DELETE the superseded noon draft so
   exactly ONE draft with that subject remains — otherwise Joe may send the stale one.
3. **False-negative on inline-image check.** Stacey's plain draft listing may report
   \"Inline image: No\" even when the image IS there — she embeds via a hosted Imgur
   `<img src=\"https://i.imgur.com/...\">` tag (not a cid: attachment), which her
   text-part scan misses. To truly verify, ask her to inspect the RAW HTML body and
   quote the `<img>` src. Presence of the img tag = good.
4. Also have her confirm Sent folder shows 0 matches for the subject.
   (8/06 EOD) If the Sent-check ask times out 3x in a row (even with the tersest
   single-API-call wording) and never returns an answer, it's acceptable to STOP
   retrying and proceed without it — PROVIDED the hand-off message never asked
   Stacey to send anything (draft-only instruction). Note the skipped check in
   the report to Joe rather than burning more retry cycles; risk is negligible
   since no send action was ever issued. (Draft-list-by-subject and MIME
   part-listing checks are higher priority and should still be completed first —
   that run they returned clean: draft-list in one try listing all 7 stacked
   drafts with id|subject pairs, MIME part-listing on the 3rd terser retry.)
5. **Sent-count FALSE POSITIVE #2 (7/14 EOD):** Stacey answered \"Sent: 1\" with today's
   exact subject, To spreston, internalDate = the DRAFT's save time (8:05 PM) — she was
   inspecting the DRAFT, not a sent mail. Resolve with ONE decisive read-only ask:
   `search 'in:sent subject:(TOL Menu Sales Opened)', list exact Subject + labelIds +
   internalDate for each`. Real sends carry labelIds ['SENT']; the draft won't appear.
   If no result matches today's exact subject, there is no leak.
5b. **Sent-count FALSE POSITIVE (7/12):** Gmail subject search is TOKEN-based, not
   exact-match — a Sent query for `TOL Menu Sales — Closed MTD (July 1-12, 2026)`
   returned \"1\" that was actually the OLD June 1-29 email sent 6/30. A nonzero Sent
   count is NOT proof of a leak: follow up with a read-only ask to fetch the match's
   EXACT subject + sent date and compare. Only an exact-subject, today-dated hit
   means the draft was sent.

### DRAFT-CLEANUP COLLATERAL DAMAGE (2026-08-28)
Deleting a stale duplicate draft "by UID N" is RISKY: Gmail Drafts resists IMAP delete so
Stacey falls back to `himalaya message move`, and **himalaya IDs != IMAP UIDs**. On 8/28
she moved a wrong ID first, sweeping a legit SCT report + ~30 inbox items into Trash.
Fix: have her resolve the himalaya ID by matching SUBJECT in a Drafts listing; ALWAYS
follow with a read-only "what moved to Trash in the last 15 min (subject + From)" ask and
restore casualties via "move ID X back to INBOX". Em dashes break her IMAP search strings,
so a delete may be reported failed when it actually worked — re-verify without the dash.

### COMPETING SEND CRONs in Stacey's own profile (discovered 2026-07-05 noon)
The email-agent (Stacey) profile has its OWN cron jobs `TOL Menu Sales - 12:05 PM
(Opened Only)` and `TOL Menu Sales - 8:05 PM (Opened & Closed)` (file
`/home/itadmin/.hermes/profiles/email-agent/cron/jobs.json`) that generate the report
independently and **SEND directly to Sean via SMTP** (subject style: `Menu Sales — Daily
Opened Performance Report — TOL 7/5/26`, CC Joe). So a Sent-folder hit at ~12:06 PM with
that other subject is Stacey's cron, NOT a leak of Jay's draft. When verifying "0 in
Sent", match on the EXACT `TOL Menu Sales — Opened (MM/DD/YYYY)` subject. Joe should be
told about the duplication (Jay drafts + Stacey auto-sends = Sean can get two versions).

### Stacey draft-quality traps (2026-07-05 noon run)
1. She may save the draft with the WRONG subject (her own template `Menu Sales — Daily
   Opened Performance Report — TOL M/D/YY`) — verify and have her rename to the exact
   requested subject.
2. She may set the inline img src to a LOCAL path (`/tmp/...png`) that won't render for
   the recipient, or write `cid:scorecard` in the HTML but OMIT the image/png MIME part.
   Verify the raw MIME: need an `image/png` part with `Content-ID: <scorecard>` (or a
   hosted https img src). If missing, ask her to rebuild multipart/related with the CID
   part and re-verify.
3. Her read-only checks are flaky: she may reply "Drafts: 0" right after saving (search\n   lag / wrong subject), or say "sent results to Telegram" instead of answering inline —\n   instruct "print answers IN YOUR REPLY TEXT" and re-ask briefly on timeout (exit 124).\n   (7/26 EOD) The Telegram deflection recurred TWICE ("I have sent the results") even\n   with "reply in your text only" in the ask. Wording that finally worked: "IMPORTANT:\n   print the answer as plain text IN THIS REPLY, do not send it anywhere else" as the\n   FIRST sentence, plus an explicit output format ("'Sent: N' then per hit one line\n   'Subject | internalDate'. Nothing else."). Lead with the print-inline demand, not\n   trail with it. Expect 2-3 x exit-124/deflection cycles per verification question;\n   keep the sleep 30-60 retry cadence.
4. (7/11) Multi-part verification asks (4 questions: draft count + raw MIME + attachment
   + Sent count in ONE message) time out repeatedly (exit 124). SPLIT verification into
   tiny single-question asks: "one word yes/no, single Gmail API call, no other tools" —
   those return fast and reliably. Ask draft-exists first, then img src, then the
   png-MIME-part yes/no, then Sent count. Budget a `sleep 30-60` between retries.
5. (7/11) The cid trap RECURRED even though she REPORTED "PNG embedding: cid (embedded
   inline using cid:scorecard)" — the HTML had `cid:scorecard` but NO image/png MIME
   part. Never trust her save-confirmation on embedding; always run the explicit
   yes/no "does the raw MIME contain an image/png part with Content-ID scorecard"
   check. Effective fix instruction: "delete that draft and rebuild as
   multipart/related with an actual image/png part (Content-ID: <scorecard>,
   Content-Disposition: inline) base64-encoded from <png path>" — she rebuilt with
   Python's MIME builders and it verified clean (1 draft, PNG part yes, PDF yes,
   Sent 0).
6. (7/13) PREVENTION beats repair: put the full MIME spec in the ORIGINAL hand-off
   message — "MUST be embedded as multipart/related with an actual image/png MIME
   part (Content-ID: <scorecard>, Content-Disposition: inline, base64 from that
   file) referenced by <img src='cid:scorecard'>. Do NOT use a local file path as
   img src, and do not write cid:scorecard without the actual PNG MIME part." With
   that wording the 7/13 EOD draft came out clean FIRST TIME (raw-MIME yes, PDF
   yes, Sent 0) — no rebuild cycle needed. Also bundle the delete-superseded-noon-
   draft instruction into the same initial ask ("if an earlier draft with this
   exact subject exists, DELETE it so exactly ONE remains") — she handles save +
   dedupe in one shot and reports both. Verification asks may still 124 twice
   before answering — keep the sleep 30-60 retry pattern; terse single-question
   asks eventually return.
6b. (7/15 EOD) The 7/13 prevention wording is NOT sufficient by itself: with the full
   MIME spec + dedupe instruction in the original ask, Stacey still saved TWO
   malformed drafts (text/plain only — no HTML, no PNG, no PDF) with the correct
   subject, while replying \"Draft saved: yes / duplicate: n/a (none found)\". Her
   save-confirmation and her dedupe claim are both untrustworthy. ALWAYS run the
   part-listing verification (item 7) — it caught both problems in one ask (count=2,
   parts=text/plain only). Fix that worked in one shot: \"DELETE BOTH drafts (IDs X,
   Y), build exactly ONE new draft with email.mime as multipart/related ...\" —
   rebuild verified clean (1 draft; text/html + image/png cid=scorecard +
   application/pdf). Note: her rebuilt drafts may include an extra image/jpeg part
   (Content-ID <amglogos>, amg-dealer-logos.jpg) — that's Joe's signature logo,
   normal, don't flag it. RECURRED 7/17 EOD: full MIME spec in the initial ask,
   she replied "inline PNG scorecard via a proper CID reference, per your exact
   specifications" — yet part-listing showed text/plain body only + PNG/PDF as
   plain attachments (Content-ID None, /tmp/ filenames). Her confident wording
   proves nothing; the delete-and-rebuild-with-email.mime instruction fixed it
   in one shot again. Part-listing verification is MANDATORY every run.
   Verification ask may 124 once — sleep 40 and re-ask terser ("single Gmail
   API call, no other tools"); that returned fast.
7. (7/14 EOD) FALSE-NEGATIVE on the terse yes/no MIME probe: the single-question
   "one word yes/no — does the raw MIME contain an image/png part with Content-ID
   scorecard?" ask answered "no" TWICE, including once on a rebuild that was
   provably GOOD. The reliable verifier is the PART-LISTING ask instead:
   "list every MIME part of the draft (mimeType, Content-ID, filename), one line
   per part, terse". A good draft lists: multipart/related / text/html /
   image/png Content-ID=<scorecard> / application-pdf-or-octet-stream with the
   .pdf filename. Trust the part listing over the yes/no probe — a bare "no" may
   trigger a needless delete-and-rebuild cycle. (Also: PDF attachments often show
   mimeType=application/octet-stream with the .pdf filename — that's fine, don't
   flag it.)
7b. (7/18 EOD) Dedupe claim FALSE again even when the MIME comes out clean: with the
   full prevention wording, the draft structure was perfect FIRST TIME (multipart/
   related, png cid, pdf — no rebuild needed), but she replied \"duplicate: none
   found\" while the noon draft with the identical subject still existed (part-
   listing ask returned count=2). The part-listing verification's COUNT is what
   catches this — treat count>1 as mandatory-fix. One-shot fix that worked: \"KEEP
   the latest draft (id X, the good one), DELETE the other older draft with that
   subject\" → she reported deleted id + remaining count 1. So: MIME quality and
   dedupe are INDEPENDENT failure modes; a clean structure does not mean dedupe\n   happened. (7/25 EOD) Same trap inside the REBUILD ask: her \"old draft deleted:\n   yes\" in a delete-and-rebuild reply was FALSE — part-listing showed both the\n   malformed 41188 and the good rebuild 41189 still present. The explicit\n   \"KEEP id X / DELETE id Y\" follow-up fixed it in one shot; re-verify count=1\n   after ANY delete claim, including ones bundled into a rebuild.\n   (7/26 EOD) First fully-clean run on record: the full prevention wording (MIME spec\n   + bundled dedupe instruction in ONE initial ask) produced a correct draft (html +\n   png cid + pdf) AND a TRUE dedupe (noon draft actually deleted, part-listing\n   count=1) in one shot — no rebuild, no fix cycle. So the one-shot CAN work; the\n   part-listing verification remains mandatory regardless, since 7/15/7/17/7/18/7/25\n   show the same wording failing silently. (7/27 EOD) SECOND consecutive clean\n   one-shot with the same wording (draft 41227: html + png cid=scorecard + pdf,\n   count=1). Verification ask 124'd once; sleep 45 + terser re-ask returned fast.\n   Sent check that run returned 'Sent: 2' — both were the OLD June 1-29 emails\n   (token-match trap, see item 5b), not a leak. Also 7/27:\n   the part-listing verification ask timed out (exit 124) THREE times even with the\n   print-inline demand as the FIRST sentence; the 4th, tersest variant (\"one\n   drafts.list + drafts.get call ... reply only ...\") returned instantly. Budget\n   3-4 retry cycles (sleep 45/60/90) for verification asks; the action ask itself\n   returned fine on the first try. (7/28 EOD) THIRD consecutive clean one-shot:\n   draft 41270 (html + png cid=scorecard + pdf), TRUE dedupe (noon draft deleted,\n   count=1), and BOTH verification asks (part-listing, Sent check) returned FIRST\n   try with zero 124s. Sent check gave 14 token-match hits, all old (6/30-7/7),
   none with today's exact subject = no leak. (7/30 noon) Another clean one-shot
   with the prevention wording (draft 41325: html + png cid=scorecard + pdf,
   count=1, true dedupe). Part-listing ask returned FIRST try; Sent check 124'd
   once, sleep-45 terse re-ask returned 4 hits all old (6/30-7/03), no leak. Same night the CLOSED MTD draft
   (41271) was ALSO a clean one-shot (html + png cid + pdf, count=1), both\n   verification asks first try; Sent check = 2 hits, both the old June 1-29\n   emails (token trap), no leak. (7/30 EOD) Another clean one-shot (draft 41370:\n   html + png cid=scorecard + pdf, true dedupe of noon draft). BOTH verification\n   asks returned FIRST try, zero 124s. Sent check = 14 hits all old (6/30-7/6),\n   no leak. (7/31 noon) Another clean one-shot (draft 41425: html + png\n   cid=scorecard + pdf, count=1, no prior duplicate). BOTH verification asks\n   returned FIRST try, zero 124s. Sent check = 4 hits, all old (6/30-7/03),\n   no leak. Part-listing count was 4 but only one had today's exact subject —\n   the others were 07/28+07/29 unsent Opened drafts (Joe hasn't cleared them)\n   plus an unrelated weekly summary; token-count trap applies to Opened too\n   when prior days' drafts linger.
7c-count-crossstore. (8/05 EOD) SENT-CHECK FALSE POSITIVE CAN BE A DIFFERENT STORE:
   a query like `in:sent Closed MTD August` returned "Sent: 3", which looked alarming,
   but all 3 hits were **BT** (Blackstone Toyota) sent emails ("BT Menu Sales - Closed
   MTD (August 1-2/3/4, 2026)") — a sibling pipeline that auto-sends, not a TOL leak.
   The token-match trap isn't limited to old same-store dates (5b/7c-count) — a broad
   "Closed MTD" query matches ACROSS STORES too, since BT/BC/SCT/TOL all share that
   phrase. Always get the exact Subject text for each Sent hit before concluding a
   leak; a nonzero count alone (even several) proves nothing. Scope the query tighter
   next time (`in:sent TOL Closed MTD August 1-5`) to cut down on cross-store noise.
7c-count. (7/29 EOD) DEDUPE-COUNT TOKEN TRAP: the part-listing ask's draft count is a\n   TOKEN search, so for the Closed MTD report (whose subject changes daily:\n   \"July 1-28\" vs \"July 1-29\") it matches ALL prior days' unsent drafts — 7/29\n   returned \"Count: 7\" for a perfectly clean run. Count>1 is only a real dupe if\n   two drafts share TODAY'S EXACT subject: follow up with \"list each hit's EXACT\n   full Subject + draft id, one per line\" and compare before ordering any delete.\n   (Opened reports don't have this problem when noon drafts get deleted same day.)\n   Also: unsent Closed-MTD drafts accumulate day over day — mention the stack to\n   Joe in the report so he can clear superseded ones; do NOT auto-delete prior\n   days' drafts, they have different subjects and are his to discard.

7g. (8/08 noon) OPENED drafts ALSO accumulate long-term, contradicting the "Opened
   reports don't have this problem when noon drafts get deleted same day" note above
   — that's only true if the EOD run actually happens and dedupes THAT day's noon
   draft. A drafts.list on `in:draft TOL Menu Sales Opened` this run showed 10
   stacked drafts going back to 07/31 (one per day, mostly), PLUS a genuine
   duplicate pair with the IDENTICAL subject from 08/02 (ids 41542 and 41547, both
   "TOL Menu Sales — Opened (08/02/2026)") that was apparently never cleaned up.
   Verifying TODAY's exact-subject draft is still sufficient for the immediate
   task, but don't assume old Opened drafts self-clean — periodically flag the
   stack size to Joe like the Closed-MTD stack, and if you spot an old
   exact-subject duplicate in passing, mention it rather than silently
   auto-deleting someone else's day's draft.\n   4th consecutive clean one-shot with the prevention wording (draft 41315: html +\n   png cid + pdf). Verification ask 124'd twice; third, tersest variant returned.\n7c. (7/28 noon) Rebuild-ask reply can be RUNAWAY GIBBERISH (thousands of repeated\n   \"producing\" tokens + random LaTeX) yet the rebuild itself SUCCEEDED — draft 41233\n   was saved correctly and the malformed one deleted. Treat garbage output like a\n   timeout: don't re-fire the action; verify read-only first. Also that run: a terse\n   subject-scoped drafts.list returned \"Drafts: 0\" (false negative, em-dash/token\n   search quirk) right after the rebuild; a broader `in:draft TOL Menu Sales` search\n   found it fine. Prefer the broad search + exact-subject match, then drafts.get by\n   id for the part listing.\n7d. (8/02 EOD) BOGUS DRAFT ID in her save confirmation: she replied \"Draft ID: 29\"
   but drafts.get(29) returned an UNRELATED draft (BT HyperCare, different recipient).
   Never verify by her reported id — verify by SUBJECT: broad `in:draft TOL` listing
   (id | exact subject per line), confirm exactly one hit with today's exact subject,
   then part-list THAT one. Same run also recurred the 6b trap (PNG/PDF as plain
   attachments, Content-ID None, /tmp filenames, despite full MIME spec in the
   initial ask) — delete-and-rebuild fixed it one shot.
7d-confirm. (8/04 EOD) BOGUS DRAFT ID recurred a THIRD time: she replied "Draft ID
   41635" but drafts.get(41635) returned an totally unrelated draft (a VW of
   Clovis Used Car Recon .docx). This is now a RELIABLE, expected failure mode —
   don't bother querying by her reported id at all. Always verify via: (1) a
   drafts.list search on the exact subject text (e.g. "in:draft TOL Menu Sales
   Closed MTD"), which lists id | exact-Subject pairs, (2) pick the id whose
   Subject matches today's exactly, (3) drafts.get THAT id for the part listing.
   Worked cleanly in one pass this run: found 6 stacked drafts (July 1-31 through
   today, one per day, no true duplicates since each day's subject is unique),
   the correct one's MIME came back perfect first try (multipart/mixed >
   multipart/related > multipart/alternative(text/plain+text/html) + image/png
   Content-ID=scorecard + application/pdf) — no rebuild needed.
7f. (8/04 EOD) Clean one-shot MIME (html + png cid=scorecard + pdf) but count=2
   again (noon 41614 + tonight 41634) despite bundling the dedupe instruction in
   the initial ask -- same as 7b/7d/7e pattern. Fixed with the standard explicit
   KEEP-id/DELETE-id follow-up, verified count=1 after. Sent-check that run had
   14 token-match hits, all old dates (6/30-7/6), zero labelIds=['SENT'] and zero
   exact-subject-today matches -- no leak. Keep treating count>1 as routine, not
   alarming; the KEEP/DELETE follow-up resolves it reliably every time so far.
7e. (8/02) The compact 4-line raw-MIME probe (\"html/img-src/png-cid/pdf yes-no\")
   can answer `pdf: no` FALSELY when the PDF part is application/octet-stream.
   Before ordering a rebuild over a pdf:no, follow up with: \"yes/no — does ANY
   part regardless of mimeType have a filename ending in .pdf?\" (answered yes).
8. (7/13 EOD) NEW trap: she can nail the inline-PNG cid embedding but DROP the
   PDF attachment entirely, even with both files spelled out in the initial ask.
   Always include "does the draft have an application/pdf attachment?" as one of
   the split yes/no verification asks. Fix instruction that worked: "DELETE that
   draft and rebuild ... PLUS an application/pdf attachment from <pdf path>, use
   Python's email.mime builders" — rebuilt clean in one shot (1 draft, png part
   yes, pdf yes, Sent 0).

## Pitfalls (hard-won 2026-06-29)
1. **OPCODE_LIST trap.** The old `tol_menu_sales_api.py` shipped pointing at SCT's 316-list.
   All 212 TL menus ARE a subset of SCT's 316 (so it never MISSED a menu) but the looser
   list can over-count à-la-carte INDIVIDUAL_SERVICE ops. Always confirm `OPCODE_LIST =
   data/tl-menu-opcodes.json`.
2. **Closed master not seeded.** A fresh/never-seeded master only holds the days the daily
   ran (e.g. 2 rows = $227 for "the month") — wildly understated. If the MTD total looks
   too small, `--seed` the month. Verified June 1–29: 83 menus / $14,290.97.
3. **Greeting name.** It's **Sean**, not Preston. Guessing the first name off the email
   address (`spreston`) is wrong — `s` is the first initial.
4. **--seed is slow & buffered.** stdout block-buffers to the log file; the bash wrapper
   may go defunct (`Zs`) while the python child keeps running. Verify with
   `pgrep -f "tol_menu_sales_closed_mtd.py --seed"`, not the wrapper PID. Run it as a
   background job with `notify_on_complete`.
5. **Don't use browser_navigate/browser_vision for the :9223 session** — those open a
   separate UNauthenticated context. Use :9223's own `/eval` + `/screenshot`.

## 429 OVERALL_RATELIMIT on the OPENED script's RO search (fixed 2026-07-02)
`tol_menu_sales_api.py`'s `fetch_ros()` originally raised `RuntimeError: RO search 429`
immediately when the shared OpenAPI OVERALL_RATELIMIT was exhausted (commonly a concurrent
`caliber-ops tekion-scraper.ts --quick` cron for ANY store — e.g. Blackstone Toyota at
noon). Fixed: 8-try backoff loop (30s*(n+1), cap 120s) on the `/repair-orders:search`
call, same pattern as the closed script. If it still fails after 9 tries, check
`ps aux | grep tekion-scraper` and re-run.

**Foreground-timeout trap (hit 2026-07-02, 8PM run — BOTH scripts):** while the
backoff is riding through a concurrent `tekion-scraper.ts --quick --dealership
Toyota of Lancaster` cron (runs at noon AND ~8PM), the opened script can exceed
the 600s foreground terminal cap. The CLOSED daily-append run hit the same 600s
cap on the 8:05 PM 7/02 run **even with NO scraper running** (per-call backoff
inside `search_closed`/`scan_ro_safe` alone can add up). **Just run both scripts
as background jobs by default** for evening runs: `python3.11 -u <script> >
data/<name>.log 2>&1` with `background=true, notify_on_complete=true`, then read
the log. A timed-out foreground attempt may still leave written JSONs — the closed
one can be a valid partial (master written before timeout), but always re-run
clean and verify via the log rather than trusting leftovers (see next section).

**Validating a $0 opened JSON:** before rendering/drafting, check `ro_count_scanned`
in the companion `data/tol-menu-sales-api-<date>.json`. A healthy end-of-day pull on
a busy day scans ~150+ ROs (7/02 = 161); a holiday still scans a substantial count
(7/04 = 75 — that's a healthy pull, not starvation). If it shows 0 ROs scanned, the run was
starved by the rate limit — re-run, don't report $0 from it. `menus: 0` with a
plausible ro_count_scanned is a genuine zero-menu day.

## Uncaught socket TimeoutError ≠ 429 (learned 2026-07-22 noon)
The opened script can also die with a raw `TimeoutError: The read operation timed
out` (traceback through `urllib` → `ssl.py`, raised from the ThreadPool `ex.map`
fan-out on `/jobs/{id}/operations`). This is NOT a 429 — the backoff loops only
catch HTTP 429s, so a plain socket read-timeout (server slow under load from a
concurrent `tekion-scraper.ts --quick` cron, typically the noon Blackstone Toyota
run) crashes the whole run after the RO search already succeeded. Fix: just
`sleep 60` and re-run the script clean — second attempt completed in seconds
(7/22: 87 ROs, clean). No code change needed unless it recurs repeatedly; if it
does, wrap the per-op `call()` in the same retry pattern for `TimeoutError`.

## HTTP 500 `internal.service.failure` / code 3001 — Tekion-side outage (2026-08-19 8:05PM)
NEW failure mode, distinct from every 429 variant below. `/repair-orders:search` returns
`500 {"id":"internal.service.failure","detail":"Internal server error","code":"3001"}`.
Key facts learned that run:
- The script's 8-try backoff DOES cover 5xx (`st >= 500` branch in `search_closed`), so a
  crash with `RuntimeError: closed RO search 500` means it already burned 8 retries over
  ~10 min. Each failed run therefore takes ~11-12 min of wall clock — do NOT keep
  re-running the full script to test recovery. Use a tiny probe script instead.
- **It is ACCOUNT/PLATFORM-wide, not store- or filter-specific.** Verified by probing:
  closedTime / invoicedTime / creationTime, with and without a status filter, today and
  yesterday windows — all 500. And BT / BC / SCT modules (different dealer IDs, same
  OpenAPI creds) ALSO returned 500. So don't waste time varying the filter or blaming
  the TOL pipeline.
- It can start MID-EVENING with no warning: the 20:02 Opened run that same day succeeded
  cleanly (165 ROs scanned, 7 menu records) and the 500s began by ~20:20.
- Diagnostic probe pattern (fast, ~1s per call — reuse it):
  ```py
  import sys; sys.path.insert(0,"/home/itadmin/tekion-reports")
  import tol_menu_sales_api as O           # or bt_/bc_/sct_menu_sales_api
  st,out = O.call("POST","/repair-orders:search",
      {"filters":[{"field":"creationTime","operator":"BTW","values":[ms0,ms1]}],"pageSize":5})
  ```
  Saved as `_probe2.py` (TOL) / `_probe3.py` (cross-store) in `/home/itadmin/tekion-reports`.
- **Do NOT draft a report on stale/partial data.** Same policy as OVERALL_QUOTA: report the
  outage honestly to Joe, skip the Stacey hand-off entirely (no PNG/PDF exists to attach —
  the render step also can't run without a fresh closed JSON), and leave a backfill watcher.
- Recovery watcher used: `backfill_tol_closed_20260819.sh` (flock
  `/tmp/tekion-tol-backfill-20260819.lock`, log `data/tol-closed-backfill-<date>.log`) —
  probes every 15 min for 12h, and on the first 200 runs
  `tol_menu_sales_closed_mtd.py <date>` (dated positional backfill, merges into the month
  master) then `render_menu_sales_paged_tol.py <date> closed`. Copy/adapt it by date rather
  than writing a new one. CHECK ITS LOG on the next run before doing anything else.

### 500-outage RESOLVED 2026-08-20 03:13 AM — but the backfill result is SUSPECT
`backfill_tol_closed_20260819.sh` logged `probe=500` every ~15 min from 21:01 8/19 until
`probe=200` at **03:13:38 8/20** (~7h outage), then ran the dated backfill + render, rc=0,
`QUEUE DONE`. BUT it recorded `closed/invoiced ROs today: 0` for 8/19 — which by this
skill's own $0-validation rule is a STARVED run on a business day, not a genuine zero.
Corroborating evidence it's bogus: the BT pipeline (dealer 1249, same creds) probed clean
at 06:02 8/20 and pulled **141 closed ROs for 8/19**. Likely the API was only partially
recovered at 03:13 (search returns 200 but empty result sets). ACTION for the next TOL
run: re-run `tol_menu_sales_closed_mtd.py 2026-08-19` to backfill the real 8/19 closed
data before trusting the August master (it currently shows 15 MTD rows / $4,691.57,
unchanged from 8/18 — i.e. 8/19 contributed nothing). LESSON: a watcher's `rc=0` +
`QUEUE DONE` is NOT validation — always apply the ro_count_scanned / "closed ROs today"
sanity check to a watcher's backfill output, and cross-check a sibling store if a
recovery-window pull comes back suspiciously empty.

### 8/19 CLOSED BACKFILL RESOLVED (2026-08-20 noon run)
Per the ACTION note above, re-ran `tol_menu_sales_closed_mtd.py 2026-08-19` this run —
the suspect watcher result WAS bogus. Clean re-run pulled **178 closed ROs for 8/19**
(watcher had logged 0), prefilter 5 of 178 carried TEK menu opcodes, 5 new menu rows.
August master went 15 rows / $4,691.57 -> **20 rows / $5,554.64** ($3,865.73 labor +
$1,688.91 parts), `✓ all candidate ROs scanned (no truncation)`. CONFIRMS the lesson:
a recovery-window pull returning 0 on a business day is starvation, not a real zero —
always re-run the dated backfill once the API is fully healthy, and never trust a
watcher's `rc=0`/`QUEUE DONE` as validation. The 500 outage is fully over (this run's
opened pull scanned 93 ROs with zero 429s/500s).

## 429 OVERALL_QUOTA ≠ OVERALL_RATELIMIT (learned 2026-07-07)
Two distinct 429 messages:
- `Limit exhausted for type : OVERALL_RATELIMIT` — short rolling window; the 8-try
  backoff rides through it. Usually a concurrent tekion-scraper cron.
- `Limit exhausted for type : OVERALL_QUOTA` — the account's DAILY quota is gone.
  NO amount of backoff/waiting helps intra-day (verified 7/07: exhausted 14:12 →
  still 429 at 19:38+, probes every 2–5 min all day). Cause was a big ad-hoc scan
  (TOL tire Q2 quarter-ledger) earlier that day. When you see OVERALL_QUOTA:
  don't burn the session polling — report the outage honestly, skip the draft
  (never draft stale/zero data), and let the next scheduled run (or next day)
  retry. Also check for sibling watchers already queued (`wait_then_scrape2.sh`,
  `quota_probe_long.py` etc.) so you don't stack more probes on the dead quota.
  RECOVERY for a quota-killed CLOSED daily run: `tol_menu_sales_closed_mtd.py`
  accepts a positional date arg (`$PY tol_menu_sales_closed_mtd.py 2026-07-07`)
  that scans ONLY that day's closed ROs and merges into the month master — so a
  missed day can be backfilled later without a full --seed. Pattern used 7/07:
  leave a flock-guarded watcher (`backfill_tol_closed_<date>.sh`, probe every
  15 min, 14h deadline) as a background job that runs the dated backfill once
  the probe returns 200. Check `data/tol-closed-backfill-<date>.log` next run.
  NEW 7/08: OVERALL_QUOTA does NOT necessarily reset at midnight — the 7/07 14:12\n  exhaustion was STILL 429 through 12:30 PM 7/08 (22+ hours, probes every ~10 min all\n  night and morning). The 7/07 closed-backfill watcher hit its 14h deadline and gave\n  up (`GAVE_UP`/`TIMEOUT` in its log). Treat OVERALL_QUOTA as a possibly multi-day\n  outage: skip the run, report, and make sure MISSED closed days get dated backfills\n  (`tol_menu_sales_closed_mtd.py <date>`) once a probe finally returns 200.\n  UPDATE 7/08 8PM: the 7/07 14:12 OVERALL_QUOTA exhaustion was STILL 429 at 20:01 PM\n  7/08 — 30+ hours. Assume multi-day. A single sequential recovery runner\n  (`quota_recovery_runner.sh`, log `data/quota-recovery-<date>.log`, lock\n  `/tmp/tekion-quota-recovery.lock`) now replaces per-job watchers: it probes every\n  20 min via `dealer-detail/scripts/tekion-quota-probe.py` and on 200 runs queued\n  backfills ONE AT A TIME with cooldowns (avoids thundering-herd re-exhaustion).\n  Preferred pattern for a NEW missed day: do NOT add another probing watcher —\n  chain off the runner instead (watch its log for `QUEUE DONE`, cooldown, then run\n  your dated backfills). Example: `backfill_tol_20260708.sh` (log\n  `data/tol-backfill-2026-07-08.log`) waits for QUEUE DONE then runs\n  `tol_menu_sales_api.py 2026-07-08` (opened takes a positional date arg too) +\n  render + closed dated append + closed render. NOTE: an opened backfill run the\n  NEXT day still queries by creationTime for the given date, so the data is\n  correct, but the draft is late — tell Joe rather than auto-drafting stale-dated\n  email without context.\n  UPDATE 7/09 noon: STILL 429 at 12:15 PM 7/09 — ~46 hours since the 7/07 14:12\n  exhaustion. `quota_recovery_runner.sh` hit its 16h TIMEOUT at 12:03 PM 7/09 without\n  ever seeing a 200; the 7/08 TOL watcher also died. Replaced with\n  `quota_recovery_runner2.sh` (36h deadline, 30-min probes, expanded queue: BC closed\n  7/07, TOL closed 7/07+7/08+7/09, TOL opened 7/08+7/09 with renders, BT seed, SCT\n  align; log `data/quota-recovery2-<date>.log`, same flock). Escalate to Joe: this\n  smells like the account's quota allocation itself, not a normal daily reset —\n  may need Tekion support / APC portal check on the API key's quota tier.\n  UPDATE 7/09 8PM: STILL 429 at 20:04 PM 7/09 — ~54 hours since 7/07 14:12. runner2\n  (started 12:15 PM 7/09, 36h deadline → ~12:15 AM 7/11) probing every 30 min, never\n  seen a 200. TOL opened+closed 7/09 are in its queue, so EOD 7/09 gets backfilled\n  automatically on recovery — no need for a new watcher. 8PM run skipped pull+draft.\n  Related: on quota-crisis days another session may rename scripts to `*.py.paused`
  (plus a `quota_guard.sh` pkill loop, log `guard.log`) to reserve the window for
  one store's scrape. Check `ls *.paused` + `guard.log` mtimes before running;
  restore with `cp tol_menu_sales_api.py.paused tol_menu_sales_api.py` once the
  guard loop is no longer running.
  RESOLUTION 7/10-7/11: the 7/07 quota outage finally cleared — `quota_recovery2`
  log shows `QUEUE DONE` at 10:30 AM 7/10, and the 7/11 noon opened run pulled
  live with zero 429s (91 ROs scanned). Lingering `*.py.paused` files are HARMLESS
  if the active script also exists and is identical (`ls -la` both; same size/date
  = already restored, no action needed). Check the active file, not just the
  presence of `.paused`.

## 429 OVERALL_RATELIMIT on the initial closed search (fixed 2026-07-01)
The `search_closed()` in `tol_menu_sales_closed_mtd.py` originally had NO retry on
the FIRST `/repair-orders:search` call — it raised `RuntimeError: closed RO search
429` immediately if the shared OpenAPI OVERALL_RATELIMIT was exhausted (commonly by a
concurrent `caliber-ops` `tekion-scraper.ts --quick --dealership Toyota of Lancaster`
running at the same time on cron). Fixed: wrapped that call in an 8-try backoff loop
(30s*(n+1), cap 120s) mirroring `scan_ro_safe`. If you still see the raise, another
job may be hammering the API — check `ps aux | grep tekion-scraper` and just re-run;
the backoff now rides through it. Do NOT keep waiting/re-launching manually.

## Verifying a $0 / zero-menu result is REAL (not a bug)
Opened runs legitimately come back **0 menus / $0.00** on quiet days (verified
6/29, 6/30, 7/01/2026 all $0). Before treating $0 as a failure, confirm it's real:
- The 212-opcode menu set is ALL TEK-mileage opcodes (`TEK<mileage><tier>`, e.g.
  `TEK100000BNM`, tiers BNM/BSM/PSM/VNM). The matcher needs `opcode in menu_set`
  AND `labor.saleAmount > 0`.
- Quick sanity scan of today's opened ROs: pull `/repair-orders:search` by
  `creationTime BTW`, then for each RO GET `/jobs` then
  `/jobs/{id}/operations`, collect opcode prefixes. On a real $0 day you'll see
  lots of `TPS/SUR/INV/FLO/MPV/TXM/LOF/POR/CON` ops and only a handful of generic
  `TEK` ops that are NOT the mileage-menu ones (no overlap with the 212 list).
- If instead you see `TEK<mileage><tier>` opcodes WITH labor>0 that the report
  missed, THEN it's a real bug (check OPCODE_LIST path / matching).
- pitfall gotcha: in an inline `python3 -c` avoid bare `&` (e.g. `a & b` set
  intersection) — the shell backgrounds it. Use `a.intersection(b)` or a heredoc.
Still render + draft the $0 scorecard; the render handles empty tables cleanly
(TOTAL row only, KPIs $0.00). Frame Stacey's summary honestly: "No menu packages
were written on opened ROs today — total menu gross $0.00 across 0 menus."

**Validating a $0 CLOSED MTD:** the closed script's log tells you directly whether
$0 is real. A healthy zero looks like (7/02 example):
`closed/invoiced ROs today: 68` → `prefilter: 0 of 68 closed ROs carry a TEK menu
opcode` → stdout `✓ all candidate ROs scanned (no truncation)`. Nonzero ROs scanned
+ zero prefilter hits + no-truncation line = genuine zero-menu MTD; render and
draft it honestly. `closed/invoiced ROs today: 0` on a business day = starved run,
re-run it. New-month note: on the 1st (or first run of a month) the script
auto-creates a fresh `MASTER-<YYYY-MM>.json` with empty records — a tiny (~97 byte)
master early in the month is normal, NOT the "unseeded master" pitfall.

## Em-dash breaks Stacey's ASCII IMAP/himalaya search (learned 2026-08-07 8:05PM run)
When Gmail API token is expired and Stacey falls back to raw imaplib/himalaya, a
literal em-dash (—) in the subject ("TOL Menu Sales — Closed MTD ...") can break her
first search attempt ("Em dash tripped up ASCII IMAP" / "broke the IMAP search") —
she self-corrects by retrying with an ASCII substring and succeeds on the 2nd try.
This is a normal, self-healing hiccup, not a failure to flag. It also explains why a
single hand-off ask can end up doing several internal save/search attempts.

## Large "duplicates deleted" claim — verify, don't panic (2026-08-07 8:05PM run)
Stacey reported "Old duplicates deleted: 8" on a single hand-off (vs the usual 0-1).
This is likely inflated by retry attempts from the em-dash search bug above (each
failed/retried search+save cycle can re-trigger a delete pass), not 8 genuine other
drafts being wiped. ALWAYS follow up with the standard subject-search verification
(`in:draft TOL Menu Sales Closed MTD`) — that run it correctly showed exactly 2
drafts remained: the current day's (Aug 1-7) and one legitimate prior-day draft
(Aug 1-2) with a different subject, confirming nothing improperly deleted. Never
skip the verification just because the deleted-count sounds alarming or reassuring
— check the actual remaining subjects either way.

## Google OAuth token expiry mid-verification (learned 2026-08-07 EOD)
A Sent-folder verification ask can hit an EXPIRED Google OAuth token — Stacey will try
Gmail API, fail, try a profile-specific token, fail again, then surface a manual OAuth
consent URL asking Jay/Joe to click through a browser flow. Don't do that in a headless
cron run. Instead just re-ask her the same verification question but explicitly say
"use himalaya instead" (her IMAP/SMTP fallback) — she completes the Sent-folder check
himalaya can't do the drafts.get part-listing (that needs the Gmail API for MIME internals),
but it works for basic
Sent-folder subject searches. (8/07 EOD: draft 41881 was a fully clean one-shot —
correct subject, greeting "Sean,", MIME clean (html + png cid=scorecard inline 58KB +
pdf attachment 48KB), count=1 no dedupe needed, and the himalaya-fallback Sent check
verifying by exact subject text rather than trusting any reported id (per the existing\n"bogus draft ID" pitfalls).

CORRECTION (8/08 EOD): the "himalaya can't do part-listing" claim above is WRONG — when
the Gmail API token was expired again, Stacey successfully fetched the FULL MIME part
listing (multipart/mixed > multipart/related > multipart/alternative(text/plain +
text/html) + image/png Content-ID=scorecard,filename + application/pdf,filename) via
raw IMAP against `[Gmail]/Drafts` (UID-based) and explicitly noted "fetched via IMAP
... Gmail API token is expired ... Same MIME structure regardless." So during an OAuth
outage, still ask her the part-listing question — she falls back to raw IMAP UID fetch
and gets equivalent MIME detail; don't skip it as "can't check." Only real limitation:
her own himalaya-numbered IDs are NOT the same as IMAP UIDs, so a self-reported numeric
draft id during a token outage may not match what Gmail-side tools show — keep
verifying by exact subject text rather than trusting any reported id (per the existing
"bogus draft ID" pitfalls).

(8/09 noon) OUTAGE CONFIRMED MULTI-DAY + REFRESH TOKEN FULLY REVOKED: the token that
expired 8/07 was STILL dead 8/09 noon — but this time Stacey explicitly said the
REFRESH token is also invalid/revoked, requiring a full browser OAuth consent flow
(not just an expired-access-token auto-refresh). Don't offer to "kick off OAuth" in a
headless cron run — that needs Joe in a browser; just fall back to himalaya and move on.
Also note: API access can be INCONSISTENT WITHIN ONE RUN — the same run's drafts.list
and drafts.get (part-listing) calls succeeded fine via Gmail API (returned instantly,
correct MIME), but a LATER in:sent search on the same draft failed with "token expired,
refresh invalid." Don't assume one successful Gmail-API call means the token is healthy
for the rest of the run — if a later verification call stalls/fails, just retry that
specific ask with "use himalaya instead" rather than concluding the whole session is
broken. The himalaya Sent-folder search still works fine and is sufficient to prove no
leak (0 matches for today's exact subject + comparison against the actual last-sent TOL
email's date confirms the search executed for real, not a silent no-op).

(8/17 8:05PM) OAUTH OUTAGE STILL DEAD 10 DAYS LATER — DEFAULT TO IMAP FOR ALL VERIFICATION
ASKS: the Gmail refresh token first reported revoked 8/07 was STILL dead on 8/17 (10 days).
This run burned ~10 minutes: an unspecified-method MIME part-listing ask timed out
(exit 124) THREE times in a row (~170-220s each) before explicitly adding "use
himalaya/raw IMAP, not Gmail API" to the ask, which then returned correct results in
48s on the very next try. A separate unspecified-method Sent-check ask, in contrast,
came back FAST with an explicit "Gmail OAuth token is dead (invalid_grant)" message
rather than timing out — so failure mode is inconsistent (sometimes silent timeout,
sometimes fast explicit error) but the underlying cause is the same dead token.
LESSON: given the outage has now persisted 10+ days, stop trying unspecified-method
verification asks first. Lead EVERY verification ask (draft-list, MIME part-listing,
Sent-check, Draft-flag-check) with "use himalaya/raw IMAP, not Gmail API" by default —
don't wait for a timeout or an explicit invalid_grant error to discover this. This
saves 2-3 wasted retry cycles (roughly 8-10 minutes) per run. Re-test occasionally
(drop the IMAP instruction once) to see if the token has finally been re-authorized;
until then, IMAP-first is the efficient default. That run: draft-list-by-subject (no
IMAP instruction) actually DID return fine via Gmail API on the first try (19 stacked
Opened drafts, one clean hit for today's exact subject, 08/02 true-dup pair 41542/41547
still unresolved) — so Gmail API isn't uniformly broken, just unreliable enough that
IMAP-first is the safer default for the slower/heavier calls (MIME listing, Sent-check).
The final \Draft-flag-in-Drafts confirmation timed out once even with IMAP specified and
was skipped after one attempt (acceptable per policy since no send action was ever
requested) — Sent-check=0 plus the subject-search confirming exactly one draft was
judged sufficient proof of no leak.

(8/09 noon) CLEAN ONE-SHOT, NO REBUILD NEEDED: draft 41903 (subject exactly right,
greeting "Sean,", multipart/related with image/png Content-ID=scorecard inline + a
real application/pdf attachment) came out correct on the FIRST hand-off with no
MIME-rebuild or dedupe-fix cycle — the full-spec prevention wording continues to work
most of the time; the part-listing + dedupe-count verification asks are still mandatory
but this run needed zero corrective follow-ups. First ask-agent call still hit the
~200s exit-124 timeout as usual (expected, not a failure) — verification follow-ups
after a sleep 15-45 all returned on the first or second try.

(8/09 noon) Drafts stack observation: 11 unsent "TOL Menu Sales — Opened" drafts now
span 07/31 through 08/09, including the still-unresolved 08/02 true duplicate pair
(41542/41547) noted in 7g — it has NOT been cleaned up across multiple runs. Continue
to only flag it to Joe, don't auto-delete another day's draft.

(8/09 EOD, Closed MTD) Another fully clean one-shot, and NOTABLY zero exit-124 timeouts
across all 3 ask-agent calls this run (initial draft build ~132s, subject-dedupe check
~55s, MIME part-listing ~94s, Sent-check ~146s) — contradicts the usual expectation that
the first hand-off call times out. Don't assume a timeout is required before treating a
run as normal; just retry if one happens, and don't be surprised when none do. Also: the
August master (tol-menu-closed-mtd-MASTER-2026-08.json) was already present/seeded going
into this run, so no --seed was needed — confirms new-month auto-seeding is reliable.
Sent-check cross-store false positive recurred again exactly per 7c-count-crossstore:
closest Sent-folder hits were "BT Menu Sales - Closed MTD" (different store, auto-sent
sibling pipeline) and old June "TOL Menu Sales — Closed MTD" emails — zero exact-subject-
today matches, no leak. Draft-list-by-subject search cleanly enumerated all 4 stacked
Closed-MTD drafts (Aug 1-2, 1-7, 1-8, 1-9) with correct id|subject pairs on the first try
— her self-reported "Draft ID: 41923" happened to be correct this time too, but keep
verifying independently via subject search + drafts.get per the standing bogus-ID pitfall
rather than trusting the reported id. (Duplicate OAuth/IMAP-fallback paragraph removed here
— see the CORRECTION (8/08 EOD) section above for the canonical version.)

(8/11 EOD) Another fully clean one-shot on a genuine $0 opened day (170 ROs scanned, 0
menus — real zero). Draft 42177 correct first try (multipart/related > alternative
(text/plain+html) + image/png Content-ID=scorecard + application/pdf), noon-draft
dedupe worked automatically without a separate follow-up (Stacey self-detected and
deleted noon draft 42163 before building), and all 3 verification asks (subject-search,
part-listing, Sent-check) returned on the FIRST try with zero exit-124s. Sent-check
confirmed via the labelIds/IMAP-folder-location follow-up baked into the ask itself
(no false-positive this time — clean "Sent: 0" plus \\Draft flag proof).

(8/10 EOD) Clean one-shot on a genuine $0 opened day (111 ROs scanned, 0 menus — real\nzero, not starvation). Draft 42091/UID64 came out correct first try (html + png\ncid=scorecard + pdf octet-stream), dedupe worked (exactly 1 draft w/ today's exact\nsubject after auto-delete of an old same-date draft). Sent-check false positive\nRECURRED exactly per item 5 (\"Sent: 1\" with today's exact subject, timestamp matching\nthe draft save time to the minute) — resolved with the labelIds/IMAP-folder-location\nfollow-up (message only in [Gmail]/Drafts and All Mail with empty X-GM-LABELS, zero\nhits in [Gmail]/Sent Mail = DRAFT-ONLY, confirmed not sent). This labelIds/folder-\nlocation check is now the reliable go-to whenever the plain Sent-count query returns\na same-day exact-subject hit — don't stop at "Sent: N", always follow up asking\nwhether the message is actually inside Sent Mail vs Drafts/All Mail only.\n\n(8/11 8:05PM, Closed MTD) NEW Sent-check failure mode: totally UNRELATED message returned
as the "hit". A Sent-folder search for the exact subject came back "0 in Sent Mail, 1 in
All Mail" with a UID/date/from that looked plausible at a glance, but a follow-up identity
check revealed the "hit" was a completely different, unrelated email (a Nov-2025 "Fwd:
Factory Warranty schedule" forward from a different sender) that shared none of the search
terms — not a same-subject-different-date match (5b) or cross-store match (7c-count-
crossstore), just a bogus/garbled search result. Don't trust ANY Sent-check hit at face
value, even one with a seemingly relevant subject line in the summary table — always
follow up asking her to quote the hit's actual identifying fields (From/Subject/Message-ID)
before concluding anything was sent. THE DEFINITIVE reassurance in this situation is a
DIRECT check of the Drafts folder: search `[Gmail]/Drafts` for the exact subject, confirm
the message UID still exists there WITH the `\Draft` flag intact. If the draft is still
sitting in Drafts with `\Draft` set, it was never sent, regardless of what a noisy Sent-
folder query returns. Prefer this direct Drafts-recheck over chasing an ambiguous Sent-
folder anomaly through more rounds of Q&A.

(8/12 8:05PM) IDs in the draft-list search output are IMAP UIDs, not bogus — distinct
from the "bogus draft ID" pitfall (7d/7d-confirm) which is about a SELF-REPORTED save-
confirmation id pointing to an unrelated draft. Here, a subject-search list came back
as `id | exact Subject` (e.g. `64 | TOL Menu Sales — Opened (08/12/2026)`, `67 | ...`
same subject) — two real dupes (noon 1:47PM save + EOD 8:05PM save). Feeding those exact
numbers back into a follow-up "KEEP id 67, DELETE id 64" ask worked correctly — Stacey
confirmed they're IMAP UIDs (her own himalaya numbering differs) and deleted the right
one via raw IMAP (himalaya `move` only touches INBOX, so she used raw IMAP delete/expunge
instead). Note the UID can shift after an expunge (67 became 66) — that's normal Gmail
IMAP renumbering, not a sign anything went wrong; re-verify by exact subject text after
any delete, not by the old numeric id. This run was otherwise a clean one-shot: correct
subject/greeting, MIME verified (html + png cid=scorecard + pdf) on BOTH the noon and EOD
drafts before dedupe, Sent-check came back a clean 0 with direct \Draft-flag confirmation
on the surviving message — no rebuild cycle needed, only the standard KEEP/DELETE dedupe.

(8/12 8:05PM, Closed MTD) FULLY CLEAN ONE-SHOT, NEW PREVENTIVE TACTIC: sent the hand-off
subject to Stacey using a plain hyphen ("TOL Menu Sales - Closed MTD (August 1-12, 2026)")
instead of an em-dash, specifically to preempt the known "em-dash breaks IMAP/himalaya
search" bug (8/07 note above). Draft came out correct first try (multipart/related >
alternative(text/plain+html) + image/png Content-ID=scorecard inline + application/pdf),
subject-search/part-listing/Sent-check all returned FIRST try with zero exit-124s (part-
listing took ~150s but didn't time out). No dedupe needed — no prior draft existed with
that exact subject (7 stacked Closed-MTD drafts total, Aug 1-2 through 1-12, each a
different date range/subject, none duplicated). Sent-check used the definitive "\Draft
flag still intact in [Gmail]/Drafts" method (per 8/11 8:05PM note) rather than trusting a
plain Sent-count number — 0 hits in Sent, UID present in Drafts with \Draft flag. Gmail
API token was revoked (invalid_grant) again this run; Stacey silently fell back to IMAP
for the verification part-listing (not just Sent-check) with full MIME fidelity.
TRADEOFF: using a hyphen instead of em-dash means today's draft subject doesn't visually
match the em-dash style of adjacent days' drafts in the stack — cosmetic only, doesn't
affect matching/verification since all checks are exact-string based anyway. Recommend
defaulting to hyphen-instead-of-em-dash in ALL future hand-off subjects for this pipeline
(and its BC/SCT/BT siblings) as a standing preventive measure, not just a fallback.

(8/13 8:05PM, Opened) Confirmed the hyphen-instead-of-em-dash tactic (previously only tested on
Closed MTD, 8/12) also works cleanly for the OPENED report subject: sent hand-off subject as
"TOL Menu Sales - Opened (08/13/2026)" (plain hyphen). Fully clean one-shot — draft 42213 (himalaya
id; underlying IMAP UID 68) came out correct first try: multipart/mixed > related > alternative
(text/plain+html) + image/png Content-ID=scorecard inline + image/jpeg Content-ID=amglogos (Joe's
sig logo, normal) + application/pdf attachment. No dedupe needed (today's exact subject had no
prior draft, even though the stack has 15 prior Opened drafts back to 07/31, plus the still-
unresolved 08/02 true-duplicate pair 41542/41547 — left untouched per standing policy). Sent-check
clean: 0 hits in Sent Mail, \Draft flag confirmed intact via IMAP on the surviving message. Timing
pattern matched prior runs: initial hand-off call hit the expected ~170s exit-124 (action still
completed); first two terse verification re-asks also hit exit-124 (himalaya timeout inside her own
tool call, self-reported "himalaya timed out, going straight to raw IMAP by subject"); third,
tersest retry (single search call, explicit "reply only" format) returned clean each time. Budget
2-3 retries per verification question as standard, not just for MIME/dedupe checks — draft-listing
itself can also need it. Recommend defaulting to hyphen (not em-dash) in ALL future hand-off
subjects for both Opened and Closed MTD going forward — two consecutive clean runs now (Closed MTD
8/12, Opened 8/13).

(8/13 8:05PM, Closed MTD) FULLY CLEAN ONE-SHOT AFTER ONE RE-FIRE: the initial hand-off call hit
the ~170s exit-124 timeout with the draft NOT actually saved yet (verified: a subject-search
right after found zero drafts with today's exact subject) — this differs from most prior runs
where the timed-out call had actually completed. Re-fired the SAME hand-off message once (adding
"there is NO existing draft yet, no dedupe needed") and it completed cleanly in ~98s: draft UID
42219, subject exact match, greeting "Sean,", MIME clean (multipart/mixed > related >
alternative(text/plain+html) + image/png Content-ID=scorecard,filename + application/pdf,filename),
Sent-check 0, \Draft flag confirmed intact. Lesson: after an exit-124 on the INITIAL action ask,
don't assume completion — always verify via subject-search before deciding whether to re-fire or
just move to verification. If the draft isn't there, it's safe to just re-send the same hand-off
message once (Stacey's dedupe/no-duplicate-found logic handles it fine either way).

## Combining Sent-check + Draft-flag-check into ONE ask can time out (2026-08-15 8:05PM)
A single verification ask that bundled BOTH "search Sent Mail for exact subject" AND "confirm
the draft still has the \Draft flag in [Gmail]/Drafts" hit the ~170s exit-124 timeout. Splitting
it into two separate terse single-question asks (sleep ~45s between them) returned cleanly and
fast (Sent: 0 in ~69s, Draft flag: yes in ~34s). Keep the Sent-count check and the \Draft-flag
confirmation as TWO separate asks, not one combined ask — this is a specific case of the general
"split verification into tiny single-question asks" guidance (item 4 above), now confirmed for
this exact pairing. That run overall was a fully clean one-shot: no MIME rebuild needed (html +
png cid=scorecard + pdf attachment correct first try), dedupe handled automatically by Stacey
without a separate follow-up instruction (1 noon duplicate, UID 72, found and deleted on her own),
subject-search/MIME-listing verification asks both returned first try, only the combined Sent+flag
ask needed the split-and-retry.

## \Draft-flag confirmation timeout — 1 try is enough if Sent-check already returned 0 (2026-08-17 8:05PM)
When the Sent-folder check already came back clean (`Sent: 0`) on its own terse ask, a
SEPARATE follow-up "\Draft flag still intact?" confirmation timing out (exit 124) does NOT
need the full 3x-retry treatment from item 4 above — one timeout is sufficient to stop and
report the draft as confirmed-not-sent. Sent=0 for the exact subject is already strong proof
nothing went out; the \Draft-flag check is a nice-to-have belt-and-suspenders, not the primary
evidence. That run (8/17 EOD) was otherwise a fully clean one-shot: initial hand-off hit the
usual ~200s exit-124 (draft still saved fine), and subject-search (72.89s), MIME part-listing
(34.85s — multipart/mixed > related > alternative(text/plain+html) + image/png CID=scorecard +
application/pdf), and Sent-check (31.25s) all returned FIRST try with correct results, zero
dedupe needed (only one draft existed with today's exact subject).

## (8/18 8:05PM, Opened) Clean one-shot; only the Sent-check needed a retry
Hyphen-subject tactic held again ("TOL Menu Sales - Opened (08/18/2026)"). Initial hand-off
returned in 82s with NO exit-124 (draft 42441 correct first try: multipart/mixed > related >
alternative(text/plain+html) + image/png Content-ID=scorecard + application/pdf), and TRUE
dedupe — she found and deleted the noon draft on her own, subject-search confirmed exactly one
hit for today. Subject-search (29s) and MIME part-listing (29s) both returned FIRST try with
"use raw IMAP, not Gmail API" specified up front (per the 8/17 IMAP-first default — it keeps
working). ONLY the Sent-check timed out (exit 124 at 206s) when the subject filter included the
full parenthesised date; a sleep-45 + terser re-ask with the subject truncated to just
"TOL Menu Sales - Opened" (no date/parens) returned in 32s. TIP: parenthesised date strings in
an IMAP subject search seem to be the expensive/fragile part — search the short subject stem and
compare exact subjects in the returned list instead. Sent: 4 hits, all old (06/30-07/03), zero
matching today = no leak. Opened draft stack down to 6 (Aug 13-18); the old 08/02 true-duplicate
pair (41542/41547) is gone from the listing, so Joe appears to have cleared the older backlog.

## (8/18 8:05PM, Closed MTD) Fully clean one-shot, zero exit-124s across ALL 4 calls
Hyphen-subject tactic + full MIME prevention spec + bundled dedupe instruction in ONE initial
ask = draft 42442 correct first try (multipart/mixed > related > alternative(text/plain+html) +
image/png Content-ID=<scorecard> + application/pdf). Hand-off returned in 113s (no timeout);
subject-search 23s, MIME part-listing 40s, Sent-check 50s — ALL first try, all with "use raw
IMAP, NOT the Gmail API" specified up front (IMAP-first default from 8/17 continues to pay off).
No dedupe needed (7 stacked Closed-MTD drafts Aug 1-12 through 1-18, each a unique date range,
zero true dupes). Sent-check = 2 hits, both the old June 1-29 emails (token trap, item 5b) — no
leak; \Draft-flag follow-up skipped as unnecessary per the 8/17 note since Sent had zero
exact-subject-today matches. Data note: closed-append ran foreground in ~10s (96 closed ROs,
2 prefilter hits, 15 MTD rows / $4,691.57) — confirms the foreground-with-generous-timeout
pattern below.

## (8/19 12:05PM, Opened) Initial hand-off exit-124 with draft NOT saved — re-fire worked
Repeat of the 8/13 Closed-MTD pattern: the first hand-off ask hit exit-124 at ~203s and the
draft was genuinely NOT saved (subject-search right after returned 6 drafts, all 08/13-08/18,
none for today). Re-fired the SAME message once with "there is NO existing draft yet, no
dedupe needed" added — completed in 55s, clean first-try MIME (multipart/mixed > related >
alternative(text/plain+html) + image/png Content-ID=<scorecard> + application/pdf). ALWAYS
verify by subject-search after an exit-124 before deciding to re-fire; do not assume the
timed-out call completed. All three verification asks returned FIRST try with "use raw IMAP,
NOT the Gmail API" leading the ask (subject-list 30s, part-listing 19s, Sent-check 47s) —
IMAP-first default (8/17) keeps paying off. Sent-check = 4 hits, all old em-dash-era emails
(06/30-07/03), zero today = no leak. Opened draft stack now 7 (08/13-08/19), no true dupes.

## (8/19 8:05PM, Opened) Initial hand-off exit-124 but draft DID save — verify before re-firing
Opposite outcome to the 8/19 noon run: the initial hand-off ask hit exit-124 at 230s, but a
subject-search right after showed the draft (42525) HAD been saved correctly and TRUE dedupe had
already happened (the noon draft with the identical subject was gone; exactly 7 drafts, one per
day 08/13-08/19, all unique subjects). MIME was clean first try (multipart/related >
alternative(text/plain+html) + image/png Content-ID=scorecard + application/pdf). So exit-124 on
the initial ask means NOTHING either way — always subject-search first, never blind re-fire.
All 3 verification asks returned FIRST try with "use raw IMAP, NOT the Gmail API" leading the ask
(subject-list 60s, part-listing 28s, Sent-check 48s). Sent-check via the SHORT subject stem
("TOL Menu Sales - Opened", no date/parens, per the 8/18 tip) returned 4 hits, all old em-dash-era
sends (06/30-07/03), zero today = no leak. Hyphen-instead-of-em-dash subject tactic held again.

## (8/20-8/21, Opened) FOUR consecutive clean runs — condensed
8/20 noon, 8/20 EOD, 8/21 noon, 8/21 EOD were all clean one-shots: draft correct FIRST TRY,
MIME clean (multipart/mixed > related > alternative(text/plain+html) + image/png
Content-ID=<scorecard> + application/pdf), all verification asks first try with "use raw
IMAP, NOT the Gmail API" leading (14-117s each). Sent-checks = 4-6 hits, ALL old em-dash-era
sends (06/29-07/03), zero today = no leak. Lessons distilled from these four:
- BOGUS-UID recurs in a VARIANT where even the SUBJECT-LIST ids are her himalaya numbering,
  not real IMAP UIDs (8/20 EOD: listed 97, real 42550; 8/21 EOD: reported 42580, real 57).
  Always phrase the part-listing ask as `UID N (subject "<exact>") ... if that UID is wrong,
  find it by that exact subject instead` — it self-heals every time.
- Ask her to QUOTE THE BOLDED TOTAL in the part-listing reply: free body-content check.
- Her own "cid:scorecard byte search missed" self-note is a NORMAL false negative (the HTML
  part is content-transfer-encoded); the part-listing is what settles it.
- The 08/02 em-dash draft keeps appearing/disappearing depending on whether the search stem
  uses a hyphen or em-dash. Usually ONE copy = not a true dupe. Flag, never auto-delete.
- Run verification asks via `execute_code` + `subprocess.run([...])` with an argv LIST (never
  a shell string) — sidesteps every quoting/paren/`&` pitfall.
## (8/22 12:05PM, Opened) Clean one-shot; only the MIME part-listing needed retries
Hand-off returned in 128s (no exit-124), draft UID 59 (himalaya id 42583) correct FIRST TRY:
multipart/mixed > related > alternative(text/plain+html) + image/png Content-ID=<scorecard>
+ application/pdf, bold total $456.21. No dedupe needed. Subject-list returned FIRST try (54s)
with "use raw IMAP, NOT the Gmail API" leading; Sent-check FIRST try (123s) = 6 hits all old
em-dash-era sends (06/29-07/03), zero today = no leak.
ONLY the MIME part-listing needed a retry: the first version asked for parts AND a quoted
bolded total AND a "if that UID is wrong find it by subject" fallback in ONE ask -> exit-124
at 200s. Sleep 45 + a stripped-down re-ask ("One raw IMAP fetch only... List its MIME parts,
one line each: mimeType | Content-ID | filename. Reply only with those lines.") returned clean
at 231s. LESSON: don't bundle the bolded-total quote request into the part-listing ask — that
free-content-check tip (8/21) makes the ask heavy enough to time out. Ask parts-only.
Drafts stack is tiny (3 TOL Opened drafts: 08/21, 08/22, plus the perennial 08/02 em-dash one
UID 20 which has reappeared again — still not a true duplicate, still flag-don't-delete).

## (8/22 8:05PM, Opened) Clean one-shot, zero exit-124s; parts-only part-listing ask confirmed
Hand-off returned in 79s (no timeout), draft correct FIRST TRY with TRUE dedupe (noon draft
deleted on her own). All 3 verification asks returned FIRST try with "use raw IMAP, NOT the
Gmail API" leading: subject-list 25s, MIME part-listing 146s, Sent-check 27s. The 8/22-noon
lesson held — asking for MIME PARTS ONLY (no bolded-total quote, no extra fallback clauses
beyond the one-line "if that UID is wrong find it by subject") returned cleanly with no 124.
BOGUS-UID VARIANT recurred: her save confirmation AND the subject-list both said UID 62, but
part-listing replied "UID 62 not found. Actual draft is UID 42590" and listed correct MIME
(multipart/mixed > related > alternative(text/plain+text/html) + image/png Content-ID=scorecard
+ application/pdf). Sent-check = 4 hits, all old em-dash-era sends (06/30-07/03), zero today =
no leak. Drafts stack tiny (3): 08/21, 08/22, plus the perennial 08/02 em-dash draft UID 20 —
still not a true duplicate, still flag-don't-delete.

## ARCHIVED RUN LOGS (8/20–8/27) — see `references/run-log-archive-aug2026.md`
Older per-run entries (8/22–8/26 Opened, 8/20–8/27 Closed MTD) moved there to keep
SKILL.md under its size limit. Consensus of those runs: the full prevention wording
produces a clean one-shot draft the large majority of the time; verification asks are
still mandatory; the $0 opened streak ran 8/23–8/25 (6 half-day slots) and broke 8/26.

## (9/02 8:05PM, Closed MTD) TEXTBOOK CLEAN RUN — zero exit-124s, all 4 asks first try
Closed append foreground clean in seconds (0 scrapers): 132 closed ROs, prefilter 0 of 132
carried a TEK menu opcode, master unchanged at **2 MTD rows / $163.74** ($110.75 labor +
$52.99 parts), `✓ all candidate ROs scanned (no truncation)` — a 0-new-rows day with 132 ROs
scanned is healthy, not starvation. Hand-off RC=0 FIRST TRY (86s); draft correct FIRST TRY at
IMAP UID 120, no dedupe needed. All 3 verification asks FIRST try, IMAP-first: subject-list
77s (Count: 6 — Aug 1-28/1-29 em-dash, Aug 1-30/1-31, Sept 1-1, Sept 1-2; no true dupes),
part-probe 63s using the Closed-MTD exact-subject disambiguation form (UID 120 echoed; PNG
58,433 / PDF 49,115 = EXACT on-disk decoded bytes; bolded total $163.74 = JSON), Sent-check
34s (Sent: 2, both old June 1-29 emails = token trap 5b, no leak). BOGUS-UID note: her save
confirmation said UID 43065 (himalaya numbering) vs real IMAP UID 120 — subject-list settled
it, standard quirk. MTD leaders: Hachey 1/$108.64 (66.4%), Alatorre 1/$55.10 (33.6%).
Flag to Joe: 5 prior unsent Closed-MTD drafts still stacked (Aug 1-28 through Sept 1-1).

## (9/02 8:05PM, Opened) TEXTBOOK CLEAN RUN — genuine $0 day, zero exit-124s, all 4 asks first try
Both scripts foreground clean in seconds (0 scrapers). 160 opened ROs scanned, **0 menus /
$0.00** — GENUINE zero (`complete: true`, `expected_records: 0`, rows empty, `records` key
ABSENT). Second consecutive $0 slot today (noon was 87 ROs / 0). Hand-off RC=0 FIRST TRY in
95s; draft correct FIRST TRY at IMAP UID 119 with TRUE dedupe (noon draft UID 117 deleted;
subject-list confirmed exactly one 09/02 hit). All 3 verification asks FIRST try with
"use raw IMAP, NOT the Gmail API" leading: subject-list 31s (Count: 14, stack 08/21-09/02 +
em-dash 08/02 UID 19 + 08/28 UID 91, no true dupes), part-probe 94s (png yes 43,487 / pdf yes
28,990 = EXACT decoded on-disk bytes; her "UID fetched: 43064" is the himalaya-numbering
quirk — byte-size cross-check settles it), Sent-check 33s (4 hits, all old em-dash-era
06/30-07/03, zero today = no leak).
PATH NOTE: `~/bin/ask-agent` only resolves under Jay's profile HOME
(/home/itadmin/.hermes/profiles/jay/home/bin/ask-agent) — /home/itadmin/bin/ask-agent does
NOT exist. In execute_code/subprocess use the absolute profile path.
Flag to Joe: 13 unsent Opened drafts still stacked (08/21-09/02).

## (9/02 12:05PM, Opened) CLEAN RUN — genuine $0 day; one part-probe 124
Both scripts foreground clean (87 ROs scanned, 0 menus — GENUINE zero: `complete: true`,
`expected_records: 0`, rows+records both empty). NOTE: `tol_menu_sales_api.py.paused` present
but ACTIVE file identical (same md5, Jul 2 date) = already restored, harmless, per the 7/10-11
note. Hand-off RC=0 FIRST TRY in 135s; draft correct FIRST TRY at UID 43037, no dedupe needed.
Subject-list FIRST try (120s, Count: 14 — Opened stack 08/21-09/02 + perennial 08/02 em-dash
41547 + 08/28 em-dash 42814; no true dupes). The 3-line UID-first part probe hit exit-124 once;
sleep 45 + the bare parts-only form ("One raw IMAP fetch only... List its MIME parts, one line
each") returned in 82s: text/plain+text/html + image/png CID=<scorecard> + application/pdf.
LISTING QUIRK: her flat listing showed multipart/mixed > multipart/alternative with NO
multipart/related line, though her save confirmation claimed related was present — treated as
listing flattening, not a defect (png CID + pdf present = pass; don't rebuild over this).
Sent-check FIRST try (70s, short stem) = 4 hits all old em-dash-era (06/30-07/03), zero today =
no leak. Flag to Joe: 13 unsent Opened drafts stacked (08/21-09/02).

## (9/01 8:05PM, Closed MTD) FIRST CLOSED RUN OF SEPTEMBER — new-month auto-seed CONFIRMED clean
No `--seed` needed and none run: the script auto-created `tol-menu-closed-mtd-MASTER-2026-09.json`
on the 1st exactly as documented. A tiny new master on day 1 is NORMAL, not the unseeded-master
pitfall. Closed append ran FOREGROUND clean in seconds (no scraper contention,
`ps aux | grep -c "[t]ekion-scraper"` = 0).
Hand-off RC=0 FIRST TRY in 159s; draft correct FIRST TRY at IMAP UID 115 (himalaya id 43021),
no dedupe needed (no prior draft with today's exact subject). All 3 verification asks returned
FIRST try with "use raw IMAP, NOT the Gmail API" leading: subject-list 34s, part-probe 105s,
Sent-check 84s. Zero exit-124s across all 4 calls.
PART-PROBE: used the Closed-MTD-specific form from the 8/31 pitfall — NO UID, lead with the
exact subject + explicit "SEPTEMBER 1-1, the newest one - NOT any of the August 1-28/1-29/1-30/
1-31 drafts" disambiguation, and ask her to echo back "(1) the UID you fetched" as line 1.
Returned correct first try (UID 115). The wrong-draft trap did NOT recur — this wording works;
keep leading with it for Closed MTD. Cross-check passed: reported PNG 58,499 / PDF 49,111 =
EXACT on-disk bytes (decoded form), bolded total $163.74 = JSON total.
BOGUS-UID trap did NOT recur (reported 115 == subject-list 115 == part-probe 115).
Sent-check = 6 hits, all old em-dash-era sends (06/29-07/03), zero today = no leak.
DATA: 76 closed ROs scanned, prefilter 2 of 76 carried a TEK menu opcode, 2 rows,
`✓ all candidate ROs scanned (no truncation)`, `complete: true`, `expected_records: 2`.
**2 menus / $163.74** ($110.75 labor + $52.99 parts). Michael Hachey 1/$108.64 (66.4%) —
RO 399480 TEK10000BNM 2024 RAV4, 94,572 mi, opened 08/31, closed today; Gustavo Alatorre
1/$55.10 (33.6%) — RO 399532 TEK35000BNM 2025 RAV4, 31,635 mi (same-day open+close, the same
RO the Opened runs caught). Closed JSON has NO `records` key — read `rows`.
`totals.parts_price` ($100.36) != `parts_gross` ($52.99) — scorecard/email use GROSS.
Closed-MTD drafts stack = 5 (Aug 1-28, 1-29 em-dash; Aug 1-30, 1-31 hyphen; Sept 1-1). No true
dupes — each a unique date range. Flag to Joe: 4 unsent August Closed-MTD drafts still stacked.

## (9/01 8:05PM, Opened) TEXTBOOK CLEAN RUN — zero exit-124s, TRUE dedupe, all 4 asks first try
Both scripts ran FOREGROUND clean in seconds (no scraper contention, `ps aux | grep -c
"[t]ekion-scraper"` = 0). Hand-off RC=0 FIRST TRY in 209s (just inside the 230s timeout);
draft correct FIRST TRY at IMAP UID 114, and TRUE dedupe — she found and deleted the noon
draft UID 111 with the identical subject on her own, subject-list confirmed exactly one
09/01 hit. NOTE: her reply showed a self-correcting rebuild mid-run ("the related wrapper
shows as multipart/alternative instead of multipart/related. Let me fix that and rebuild")
— she caught and fixed her own MIME nesting BEFORE finishing; final structure verified
correct. Treat that as normal self-healing, not a failure.
All 3 verification asks returned FIRST try with "use raw IMAP, NOT the Gmail API" leading +
the 3-line numbered part probe: subject-list 59s, part-probe 105s, Sent-check 33s. Part
sizes DECODED and EXACT on-disk (PNG 50,645 / PDF 45,173); bolded total $55.10 confirmed.
The part-probe reply included a visible self-correction ("regex was too strict — the <b> tag
wraps 'TOTAL MENU GROSS: $55.10'") before answering — harmless. BOGUS-UID trap did NOT recur
(reported 114 == subject-list 114). Sent-check = 4 hits, all old em-dash-era sends
(06/30-07/03), zero today = no leak.
DATA: 180 opened ROs scanned, **1 menu / $55.10** ($29.32 labor + $25.78 parts) — thin but
GENUINE (`complete: true`, `expected_records: 1`, 180 ROs proves no starvation). Gustavo
Alatorre 1/$55.10 (100% share): RO 399532 TEK35000BNM 2025 RAV4, 31,635 mi — the SAME single
RO the noon run caught, i.e. zero additional menus written all afternoon/evening.
`records` empty (0) while `rows` had the entry — the 8/26 quirk STILL RECURS; read `rows`.
`totals.parts_price` ($49.68) != `parts_gross` ($25.78) — scorecard/email use GROSS.
Opened drafts stack = 13 (08/21-09/01 + perennial 08/02 em-dash UID 19; 08/28 UID 91 also
em-dash). No true dupes. Flag to Joe: 12 unsent August Opened drafts still accumulating.

## (9/01 12:05PM, Opened) TEXTBOOK CLEAN RUN — zero exit-124s, all 4 asks first try
First run of September. Hand-off RC=0 FIRST TRY in 122s; draft correct FIRST TRY at IMAP UID 111,
no dedupe needed (0 prior drafts with today's exact subject). All 3 verification asks returned
FIRST try with "use raw IMAP, NOT the Gmail API" leading + the 3-line numbered part probe:
subject-list 32s, part-probe 52s, Sent-check 47s. Part sizes DECODED and EXACT on-disk
(PNG 50,672 / PDF 45,169). BOGUS-UID trap did NOT recur (reported UID 111 == subject-list UID 111).
Sent-check = 4 hits, all old em-dash-era sends (06/30-07/03), zero today = no leak.
NEW-MONTH NOTE: no new-month setup was needed for the OPENED pipeline (that's only a Closed-MTD
concern) — the opened script ran clean on 9/01 with no master/seed involvement.
DATA: 115 opened ROs scanned, **1 menu / $55.10** ($29.32 labor + $25.78 parts) — a thin but
GENUINE day (`complete: true`, `expected_records: 1`). Gustavo Alatorre 1/$55.10 (100% share):
RO 399532 TEK35000BNM 2025 RAV4, 31,635 mi. `records` empty (0) while `rows` had the entry —
the 8/26 quirk STILL RECURS every run; ALWAYS read `rows`, never `records`.
`totals.parts_price` ($49.68) != `parts_gross` ($25.78) — scorecard/email use GROSS.
Opened drafts stack = 13 (08/21-09/01 + perennial 08/02 em-dash UID 19; 08/28 UID 91 also
em-dash). No true dupes. Flag to Joe: 12 unsent August Opened drafts are accumulating.

## (8/31 8:05PM, Closed MTD) NEW HIGH-VALUE PITFALL: part-probe fetched the WRONG draft
Draft itself was a clean one-shot (hand-off RC=0 first try in 98s, himalaya id 42877 / IMAP
UID 109, no dedupe needed). But the MIME part-probe INSPECTED A DIFFERENT DRAFT and reported
plausible-looking-but-WRONG values: PNG 105,010 / PDF 88,443 / bolded total **$8,954.44**.
Those are the exact on-disk sizes and MTD total of the **Aug 1-28** draft — i.e. she matched
an older Closed-MTD draft from the stack instead of today's.
ROOT CAUSE: the standing probe wording `UID N (subject "<exact>") ... if that UID is wrong,
find it by that exact subject instead` is UNSAFE for Closed MTD, because the Drafts stack
holds several near-identical subjects differing only in the end date (August 1-28 / 1-29 /
1-30 / 1-31) and her subject matching is substring/token-ish, so it lands on the wrong one.
(Opened reports don't hit this — their subjects differ by full date.)
**DETECTION (do this every run):** cross-check the reported PNG/PDF byte sizes against the
actual on-disk files (`ls -la data/TOL-Menu-Sales-Closed-Scorecard-<today>-Paged.{png,pdf}`)
AND the bolded total against the JSON total. If either mismatches, she read the wrong draft —
do NOT rebuild the draft, just re-probe. A fast way to confirm which day she actually read:
loop the month's `tol-menu-sales-closed-2026-08-*.json` files printing row_count + total; the
bogus total will match a prior day exactly.
**FIX that worked in one shot:** re-ask with NO UID at all and an explicit disambiguation —
"find the draft whose Subject is EXACTLY `TOL Menu Sales - Closed MTD (August 1-31, 2026)`
(note: August 1-31, the LAST one, not August 1-28 or 1-29 or 1-30. Match the literal string
'August 1-31'.) Fetch THAT message only." Also ask her to echo back "(1) the UID you fetched"
as the first answer line. Returned correct in 58s: UID 109, PNG 105,453 / PDF 93,426 (exact
on-disk), bolded total $10,457.96.
RECOMMENDATION: for Closed MTD, skip the UID-first form entirely — lead the part-probe with
the exact-subject + "not the earlier date ranges" disambiguation from the start.
Subject-list ask returned first try (55s, Count: 4 — Aug 1-28/1-29 em-dash, Aug 1-30/1-31
hyphen; no true dupes). Sent-check first try (63s) = 6 hits, all old em-dash-era sends
(06/29-07/03), zero today = no leak. Zero exit-124s across all 4 asks.
DATA: 286 closed ROs scanned, prefilter 4 of 286 carried a TEK menu opcode, 4 new rows.
Master 44 -> **48 MTD rows / $10,457.96** ($7,101.19 labor + $3,356.77 parts),
`✓ all candidate ROs scanned (no truncation)`. Gustavo Alatorre 24/$3,345.34; Michael Hachey
7/$2,685.16; Eduardo Jimenez 5/$1,152.14; 10 advisors on the board. Today's 4 adds: Alatorre
RO 399398 TEK10000BNM $110.85, 399419 TEK30000BNM $241.41, 399422 TEK10000BNM $118.47;
Hachey RO 399475 TEK10000BNM $127.89. Closed JSON has NO `records` key — read `rows`.
`totals.parts_price` ($7,745.81) != `parts_gross` ($3,356.77) — scorecard/email use GROSS.
Backgrounded the append defensively (a `tekion-scraper --quick --dealership Toyota of
Lancaster` launched at 20:20, same minute) — finished well inside 170s with no backoff.

## (8/31 8:05PM, Opened) TEXTBOOK CLEAN RUN — zero exit-124s, TRUE dedupe, all 4 asks first try
Both scripts ran FOREGROUND clean in seconds (no scraper contention). Hand-off RC=0 FIRST TRY
in 72s; draft correct FIRST TRY, TRUE dedupe (she found+deleted noon draft UID 105 on her own;
subject-list showed exactly one 08/31 hit). All 3 verification asks returned FIRST try with
"use raw IMAP, NOT the Gmail API" leading + the 3-line numbered part probe: subject-list 41s,
part-probe 75s, Sent-check 111s. Part sizes DECODED (PNG 57,557 / PDF 51,397 = exact on-disk).
MILD BOGUS-UID: her save said UID 109, subject-list said UID 108 — the "if that UID is wrong,
find it by that exact subject" wording self-healed it. Sent-check = 4 hits, all old em-dash-era
(06/30-07/03), zero today = no leak.
DATA: 129 opened ROs scanned, **5 menus / $707.26** ($518.10 labor + $189.16 parts) — best
opened day since 8/27. Gustavo Alatorre 3/$470.73 (RO 399398 TEK10000BNM 2023 Highlander;
399419 TEK30000BNM 2024 RAV4; 399422 TEK10000BNM 2018 Tundra 4WD); Michael Hachey 2/$236.53
(RO 399475 TEK10000BNM 2019 RAV4; 399480 TEK10000BNM 2024 RAV4). `records` empty (0) while
`rows` had all 5 — the 8/26 quirk STILL RECURS; ALWAYS read `rows`.
`totals.parts_price` ($399.35) != `parts_gross` ($189.16) — scorecard/email use GROSS.
Opened drafts stack = 12 (08/21-08/31 + perennial 08/02 em-dash UID 19; 08/28 UID 91 also
em-dash). No true dupes.

## (8/31 12:05PM, Opened) TEXTBOOK CLEAN RUN — zero exit-124s, all 4 asks first try
No concurrent scrapers; both scripts ran FOREGROUND clean in seconds. Hand-off RC=0 FIRST TRY
in 87s; draft correct FIRST TRY at IMAP UID 105, no dedupe needed (no prior draft with today's
exact subject). All 3 verification asks returned FIRST try with "use raw IMAP, NOT the Gmail
API" leading + the 3-line numbered part probe: subject-list 38s, part-probe 97s, Sent-check 30s.
Part sizes DECODED (PNG 49,958 / PDF 47,242 = exact on-disk bytes) — 4th consecutive decoded run.
BOGUS-UID trap did NOT recur (reported UID 105 == subject-list UID 105). Sent-check = 6 hits,
all old em-dash-era sends (06/29-07/03), zero today = no leak.
DATA: 87 opened ROs scanned, **3 menus / $479.17** ($344.43 labor + $134.74 parts) — ends the
two-day $0 streak (8/30 noon + EOD both zero). Gustavo Alatorre wrote ALL 3 (single-advisor day):
RO 399398 TEK10000BNM 2023 Highlander $110.85; RO 399419 TEK30000BNM 2024 RAV4 $241.41;
RO 399422 TEK10000BNM 2018 Tundra 4WD $126.91. `records` empty (0) while `rows` had all 3 —
the 8/26 quirk STILL RECURS every run; ALWAYS read `rows`, never `records`.
`totals.parts_price` ($297.99) != `parts_gross` ($134.74) — scorecard/email use GROSS.
Opened drafts stack = 12 (08/21-08/31 + perennial 08/02 em-dash UID 19); note 08/28 (UID 91) is
also an EM-DASH subject now, so the hyphen search stem surfaces 10 hyphen + 2 em-dash. No dupes.

## (8/30 8:05PM, Closed MTD) TEXTBOOK CLEAN RUN — zero exit-124s, all 4 asks first try
Backgrounded the closed daily-append defensively (5 concurrent `tekion-scraper` SVW processes
live) but it finished in well under 170s with no backoff — 163 closed ROs, prefilter 0 of 163
carried a TEK menu opcode (so no new rows today), master holds 44 MTD rows, `✓ all candidate ROs
scanned (no truncation)`. NOTE: a 0-prefilter day still produces a valid MTD report — the master
carries the month's accumulated rows; don't mistake "0 new" for a starved pull (163 ROs scanned
proves health).
Hand-off RC=0 FIRST TRY in 105s; draft correct FIRST TRY at IMAP UID 105 (himalaya id 42839),
no dedupe needed (no prior draft with today's exact subject). All 3 verification asks returned
FIRST try with "use raw IMAP, NOT the Gmail API" leading + the 3-line numbered part probe:
subject-list 36s, part-probe 108s, Sent-check 33s. Part sizes came back DECODED (PNG 105,550 /
PDF 90,818 = exact on-disk bytes) — third consecutive run in decoded form. Bolded total
$9,859.34 confirmed in body. BOGUS-UID trap did NOT recur (reported 42839/UID 105 == subject-list
UID 105). Sent-check = 6 hits, all old em-dash-era sends (06/29-07/03), zero today = no leak.
DATA: 44 menus MTD / **$9,859.34** ($6,664.52 labor + $3,194.82 parts), Aug 1-30 closed-to-date.
Gustavo Alatorre 21/$2,874.61; Michael Hachey 6/$2,557.27; Eduardo Jimenez 5/$1,152.14; 10
advisors on the board. `rows` populated (44), `records` key ABSENT entirely in the closed JSON
(the closed schema uses `rows` + `row_count` + `expected_records`, not `records`) — read `rows`.
TOL drafts stack = 14 (11 Opened 08/21-08/30 + perennial 08/02 em-dash UID 19, plus 3 Closed-MTD:
Aug 1-28, 1-29, 1-30). No true dupes; older Closed-MTD drafts have unique date ranges — leave them.

## (8/30 8:05PM, Opened) TEXTBOOK CLEAN RUN — second $0 day in a row, zero exit-124s
Ran with 5 concurrent `tekion-scraper` processes live; backgrounded the pull defensively but it
finished in <60s with no backoff. Hand-off RC=0 FIRST TRY in 78s, draft correct FIRST TRY at
IMAP UID 104, and TRUE dedupe (noon draft UID 101 actually deleted — subject-list showed exactly
one 08/30 hit). All 3 verification asks returned FIRST try with "use raw IMAP, NOT the Gmail API"
leading + the 3-line numbered part probe: subject-list 40s, part-probe 70s, Sent-check 36s.
Part sizes came back DECODED again (PNG 43,937 / PDF 29,223 = exact on-disk bytes), same as
8/30 noon — the base64-inflated form seen 8/28-8/29 seems to have stopped; either is fine.
BOGUS-UID trap did NOT recur (reported UID 104 == subject-list UID). Sent-check = 4 hits, all
old em-dash-era sends (06/30-07/03), zero today = no leak.
DATA: 79 opened ROs scanned, **0 menus / $0.00** — GENUINE zero (`complete: true`,
`expected_records: 0`, `rows` AND `records` both empty). SECOND consecutive $0 opened day
(noon 8/30 was also 0/61 ROs) — Sunday, low menu volume; not starvation.
Opened drafts stack = 11 (08/21-08/30 + perennial 08/02 em-dash UID 19); 13 TOL drafts total
incl. 2 Closed-MTD. No true dupes.

## (8/30 12:05PM, Opened) TEXTBOOK CLEAN RUN — genuine $0 day, all 4 asks first try
Ran with 5 concurrent `tekion-scraper` processes live; backgrounded the pull defensively
per the 429 section but it finished in ~60s with no backoff. Hand-off RC=0 first try, draft
correct FIRST TRY at IMAP UID 101 (All-Mail APPENDUID 42830), no dedupe needed (0 prior
drafts with today's exact subject). All 3 verification asks returned FIRST try with "use raw
IMAP, NOT the Gmail API" leading + the 3-line numbered part probe. Zero exit-124s anywhere.
NEW: part sizes came back DECODED, not base64-inflated (PNG 44,088 / PDF 29,224 = exact
on-disk bytes), unlike 8/28-8/29. Either form is fine — confirm non-zero, don't flag either.
BOGUS-UID trap did NOT recur (reported UID 101 == subject-list UID).
Sent-check = 6 hits, all old em-dash-era sends (06/29-07/03), zero today = no leak.
DATA: 61 opened ROs scanned, **0 menus / $0.00** — a GENUINE zero (`menus: 0`, `rows` AND
`records` both empty, `complete: true`, `expected_records: 0`). First $0 opened day since
the 8/23-8/25 streak, after four straight non-zero days. On a true-zero day the usual
"`records` empty but `rows` populated" quirk is uninformative — `complete: true` plus a
non-trivial RO scan count is what proves a real zero vs. a starved pull.
Opened drafts stack = 11 (08/21-08/30 + perennial 08/02 em-dash UID 19); 13 TOL drafts total
incl. 2 Closed-MTD. No true dupes; em-dash vs hyphen subjects can't collide.
SKILL MAINTENANCE: SKILL.md hit the 100,000-char skill_manage limit this run. Fixed by
moving the 8/20-8/27 per-run logs into `references/run-log-archive-aug2026.md` (now ~78KB).
When the next size error appears, archive the OLDEST per-run `## (M/DD ...)` sections the
same way — never delete procedure/pitfall sections.

## (8/29 8:05PM, Opened) TEXTBOOK CLEAN RUN — zero exit-124s, TRUE dedupe, all 4 asks first try
Both scripts ran FOREGROUND clean (opened pull ~seconds, render ~seconds) — no backoff, no
scraper contention on a Saturday evening. Hand-off returned RC=0 in 117s; draft correct FIRST
TRY at himalaya ID 42826 / IMAP UID 98, and TRUE dedupe happened (noon draft IMAP UID 95 with
the identical subject actually deleted; subject-list showed Count: 1). All 3 verification asks
returned FIRST try with "use raw IMAP, NOT the Gmail API" leading + the 3-line numbered part
probe: subject-list 104s, part-probe 51s, Sent-check 42s.
MIME clean: image/png CID scorecard 88,580B + .pdf 69,758B (base64-inflated from on-disk
64,730 / 50,975 — expected, don't flag). Bolded total $789.02 confirmed in body.
BOGUS-UID variant recurred (mild): Stacey's save summary said "himalaya ID 42826, IMAP UID 98"
but the subject-list returned 42826 as the UID. Cosmetic — verify by SUBJECT, always.
SENT-CHECK NOTE: broad `subject contains "TOL Menu Sales"` now returns 6 hits (not the 4 seen
in prior runs) — the extra 2 are the same old June/July em-dash-era sends surfaced by the
broader search string. ALL 6 are 06/29-07/03; zero today = no leak. A rising hit count on the
BROAD query is not a regression, just a looser match term.
DATA: 115 opened ROs scanned, **3 menus / $789.02** ($507.76 labor + $281.26 parts).
Mauricio Orellana 1/$413.73 (RO 399209 TEK30000BNM 2020 GR Supra); Gustavo Alatorre 1/$247.40
(RO 399208 TEK30000BNM 2023 Highlander); Michael Hachey 1/$127.89 (RO 399281 TEK10000BNM 2021
Corolla). The first two are the same ROs the noon run caught ($774.85) — Hachey's 399281 is the
afternoon add. `records` empty (0) while `rows` had all 3 — the 8/26 quirk STILL RECURS every
run; ALWAYS read `rows`, never `records`.
`totals.parts_price` ($621.55) != `parts_gross` ($281.26) — scorecard/email use GROSS.

## (8/29 12:05PM, Opened) TEXTBOOK CLEAN RUN — zero exit-124s, all 4 asks first try
Hand-off returned in 69s, draft correct FIRST TRY, no dedupe needed (0 prior drafts with
today's exact subject). All 3 verification asks returned FIRST try with "use raw IMAP, NOT
the Gmail API" leading + the 3-line numbered part probe (per the 8/28 truncation lesson):
subject-list 40s, part-probe 39s, Sent-check 21s. MIME clean: image/png Content-ID
scorecard 57,098B + .pdf 47,766B; bolded total $774.85 confirmed in body.
BOGUS-UID variant recurred (mild): save confirmation said "Draft UID 42819", subject-list
said UID 95 — the standing `UID N (subject "<exact>") ... if that UID is wrong, find it by
that exact subject instead` wording self-healed it. Verify by SUBJECT, always.
Sent-check = 4 hits, all old em-dash-era sends (06/30-07/03), zero today = no leak.
CONFIRMED: the 3-line numbered probe ("(1) png+CID yes/no+size (2) any .pdf filename
yes/no+size (3) bolded total") is now the PREFERRED part-verification form — second
consecutive run where it returned fast with no truncation and no retry.
DATA: 100 opened ROs scanned, **2 menus / $774.85** ($520.80 labor + $254.05 parts).
Mauricio Orellana 1/$527.45 (RO 399209 TEK30000BNM 2020 GR Supra); Gustavo Alatorre
1/$247.40 (RO 399208 TEK30000BNM 2023 Highlander). Fourth consecutive non-zero opened
day after the 8/23-8/25 $0 streak. `records` empty (0) while `rows` had both entries —
the 8/26 quirk now RECURS every run; ALWAYS read `rows`, never `records`.
`totals.parts_price` ($570.87) != `parts_gross` ($254.05) — scorecard/email use GROSS.
Opened drafts stack = 10 (08/21-08/29 + perennial 08/02 em-dash UID 19), no true dupes.

## (8/28 12:05PM, Opened) TEXTBOOK CLEAN RUN — zero exit-124s, CORRECT UID reported
Draft correct FIRST TRY at UID 95; reported UID was CORRECT (bogus-UID trap did NOT recur).
No dedupe needed. Subject-list first try (17 stacked TOL drafts, 08/21-08/28 pairs + the
perennial 08/02 em-dash pair UIDs 19/20).
NEW MINOR TRAP: the full "list EVERY MIME part, one line each: mimeType | Content-ID |
filename | size" wording TRUNCATED mid-reply ("Part 1: multipart/mixed | CID=" then stopped,
RC=0 — a cut-off stream, NOT a timeout). Fix in ONE shot after `sleep 20`: collapse to a
3-line numbered probe — "(1) image/png part w/ Content-ID scorecard? yes/no + byte size
(2) any part w/ filename ending .pdf? yes/no + byte size (3) the bolded total". Returned
"(1) yes, 78748 (2) yes, 66838 (3) $309.54" instantly. PREFER this 3-line form. Sizes are
BASE64-encoded (57,544B PNG -> 78,748; 48,843B PDF -> 66,838) — don't flag vs on-disk sizes.
Sent-check = 4 hits, all old em-dash-era sends (06/30-07/03), zero today = no leak.
DATA: 99 opened ROs, **2 menus / $309.54** ($194.49 labor + $115.05 parts). Gustavo Alatorre
1/$157.68 (RO 399030 TEK10000BNM 2023 Tundra 4WD); Michael Hachey 1/$151.86 (RO 399026
TEK40000BNM 2024 GR Corolla). Third consecutive non-zero opened day after the 8/23-8/25 $0
streak. `records` empty (0) while `rows` had both entries — the 8/26 quirk RECURS; read `rows`.

## (8/27 8:05PM, Opened) TEXTBOOK CLEAN RUN — zero exit-124s, TRUE dedupe first try
Hand-off returned in 220s (no timeout), draft correct FIRST TRY, dedupe TRUE (noon draft
UID 88 actually deleted; subject-list showed exactly one 08/27 hit at UID 42748). All 3
verification asks returned FIRST try and FAST with "use raw IMAP, NOT the Gmail API"
leading + parts-only part-listing wording: subject-list 32s, part-listing 50s, Sent-check
30s. MIME clean: multipart/mixed > related > alternative(text/plain 502B + text/html 812B)
+ image/png Content-ID=<scorecard> 63,910B inline + application/pdf 53,197B; bolded total
$1,159.78 confirmed in body.
BOGUS-UID recurred in MILD form: save confirmation said "UID 91" (she self-explained it as
post-expunge Gmail renumbering) but the real IMAP UID was 42748 — the standing "if that UID
is wrong, find it by that exact subject" wording resolved it silently. Verify by SUBJECT.
Sent-check = 4 hits, all old em-dash-era sends (06/30-07/03), zero today = no leak.
DATA: 171 opened ROs, 6 menus / $1,159.78 ($732.78 labor + $427.00 parts) — best opened day
in weeks. Gustavo Alatorre 4/$515.20, Unassigned 1/$328.88, Mauricio Orellana 1/$315.70.
The 8/26 empty-`records` JSON quirk did NOT recur — `rows` was fully populated (6 rows).
Opened drafts stack = 8 (08/21-08/27 hyphen + perennial 08/02 em-dash UID 41547), no dupes.

## Backgrounding the CLOSED daily-append run — don't over-engineer (learned 2026-08-14 8:05PM)
The default (non-`--seed`) `tol_menu_sales_closed_mtd.py` run is a light daily-append —
it typically finishes in well under a minute (8/14: ~10-15s for 158 closed ROs, 1 new
menu row). Launching it with `terminal(background=true)` AND also appending a literal
`&`/`echo "started with PID $!"` inside the command string is redundant and confusing —
you get two PIDs (the bash wrapper's `$!` and the actual tracked session), and the
top-level `process(action='wait', timeout=300)` call gets silently clamped to the
configured 180s limit and returns immediately with just the launch line, not the result.
Worse pitfall: don't write a custom polling loop in `execute_code` that shells out
`pgrep -af '<script-name>'` repeatedly — each `pgrep -af` invocation matches its OWN
command line (which contains the script name as a search string) and can look like the
job is still "running" indefinitely, and a `time.sleep(15)`-loop burns through the whole
300s `execute_code` timeout doing nothing useful once the real work is already done (log
already shows the final `✓ all candidate ROs scanned (no truncation)` line on the very
first check). **Simpler, faster pattern for this specific script:** just run it in the
foreground with a generous timeout (`terminal(command=..., timeout=180)`, no
background=true needed) — a daily append comfortably finishes inside that window unless
a concurrent scraper/quota fight is happening (see the OVERALL_RATELIMIT/QUOTA sections
above for when background+watch IS warranted, e.g. --seed or a 600s-cap trap). If you do
background it, just poll `process(action='poll')` once or twice a short time apart, or
`process(action='wait', timeout=60)` — don't loop pgrep checks.

## Fully clean one-shot, zero exit-124s across ALL calls (2026-08-14 8:05PM)
Another fully clean run end to end: hand-off (~98s), dedupe subject-search (~45s), MIME
part-listing (~37s), and Sent-check (~36s) ALL returned on the first try with zero
exit-124 timeouts — contradicts the usual expectation that at least the initial
hand-off times out. Draft (id 71 that run) came out correct first try: subject exact
with plain hyphen, greeting "Sean,", multipart/related > alternative(text/plain+html) +
image/png Content-ID=scorecard + application/pdf, no rebuild needed. Dedupe count showed
9 total stacked Closed-MTD drafts (Aug 1-2 through 1-14, one per day) with zero true
duplicates — consistent with the known accumulation pattern (7c-count); don't touch the
older ones. Sent-check used the definitive \Draft-flag-in-Drafts method: 0 exact-subject
hits in Sent, target draft confirmed still in `[Gmail]/Drafts` with `\Draft \Seen` flags.

## Cross-store note
This same pattern (clone the sibling pipeline, derive the store's OWN SERVICE_MENU opcode
set, set dealer ID + recipient) applies to the remaining AMG stores (SV/AR/VC) when Joe
asks for their menu reports. Per-store menu set ≠ SCT's 316 — always derive it.
**BT was cloned from THIS pipeline 2026-07-08** — see `bt-menu-sales-reports` for the
BT specifics and the clone pitfalls (missed `tol-*` cache paths + internal
`"dealerId":"1092"` literals need a second sed pass; verify with a zero-grep).
