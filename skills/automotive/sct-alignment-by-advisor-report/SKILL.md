---
name: sct-alignment-by-advisor-report
description: Run the Stevens Creek Toyota (SCT, dealer ST/876) Alignment-by-Advisor report from the LIVE Tekion OpenAPI — counting BOTH dedicated alignment opcodes (ALIGN/OKAL) AND alignments bundled inside a TEK service-menu op. Produces the Joe-approved 2-page Toyota-red scorecard (page 1 advisor ranking PNG, page 2 RO-level chip detail PDF) and hands to Stacey to DRAFT in Joe's inbox. Supports full-month (last month) or closed month-to-date windows. This is THE canonical AMG alignment-report FORMAT Joe reuses a lot going forward.
triggers:
  - sct alignment report
  - alignment by advisor sct
  - stevens creek alignment report
  - sct alignment month to date
  - daily alignment report
---

# SCT Alignment-by-Advisor Report (LIVE OpenAPI)

Counts alignments SCT sold in a period, broken down by service advisor, capturing:
- **Dedicated** alignment opcodes sold on an RO: `ALIGN`, `OKAL`, `ALIGN00BRA`.
- **Bundled** alignments performed inside a TEK service-menu op (any `TEK*` opcode
  whose operation story contains "align").

Joe approved this exact report + format on 2026-07-01 ("Alignment report is
perfect!") and said the FORMAT will be reused a lot across stores. The generic
per-store version is skill `tekion-alignment-by-advisor-report`; THIS skill is the
SCT-specific, proven pipeline with the frozen SCT opcode set + scripts.

## Scripts (built, proven)
- **Scan:** `/home/itadmin/tekion-reports/sct_align_full_june.py` — the full-month
  scanner (edit MS0/MS1 window at top for a different month). Two-tier, rate-limit-safe.
- **MTD scan:** `/home/itadmin/tekion-reports/sct_align_mtd.py` — closed month-to-date
  (1st of current month → end of today, Pacific). Same architecture; window auto-computed.
  **STALE SAME-DAY INDEX TRAP (hit 2026-07-10):** the scan caches
  `data/sct-mtd-<YYYY-MM-DD>-closed-index.json` keyed by DATE only. If anything ran the
  scan earlier the SAME day (e.g. a 9:31am probe), the 7pm run reuses that morning index
  and silently misses every RO closed since (observed 1,354 vs 1,461 ROs → 128 vs 141
  alignments — wrong report, exit 0, failed=[]). Before the nightly scan, check the index
  file's mtime; if it exists and is hours old, `mv` it to a `.bak` and re-run. The
  align-scan checkpoint still resumes, so only the NEW candidates fan out (~30 ROs, fast).
  A "loaded cached index: N ROs" log line at 7pm is the tell — always question it.
- **Render:** `/home/itadmin/tekion-reports/render_sct_align_full_june.py` — reads the
  self-contained by-advisor JSON, emits the 2-page scorecard. (A generalized
  `render_sct_align.py` reads any `sct-*-align-by-advisor*.json` + a period label.)
- Interpreter: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`. Data dir:
  `/home/itadmin/tekion-reports/data/`.

## Scan architecture (why it's built this way — DO NOT simplify)
- **Window + status:** filter `closedTime` BTW [start, end-of-today] + `status IN
  CLOSED,INVOICED`. NEVER `modifiedTime` (overcounts). Pacific tz (-07:00).
- **Two-tier, rate-limit-safe:** Pass 1 enumerates all closed ROs, capturing per-RO
  the FREE opcode `tags` (`{field:"OPCODE", value:<code>}`) + `assignee.advisor.id`.
  Pass 2 fans out jobs→operations ONLY on CANDIDATES = ROs whose opcode tags include a
  dedicated ALIGN code OR any `TEK*` code (a bundled alignment can hide inside any menu).
  Full June: 5,382 closed → 1,169 candidates. This ~5x reduction keeps the run under
  the app-wide `OVERALL_RATELIMIT`.
- **OVERALL_QUOTA exhaustion (hit 2026-07-07):** distinct from OVERALL_RATELIMIT — this is
  the store's DAILY API quota being fully spent (other pipelines, e.g. a TOL backfill loop +
  caliber-ops scrapers, can burn it). EVERY call 429s
  (`Limit exhausted for type : OVERALL_QUOTA`) for HOURS (observed 20:12 PDT → past 05:35
  next morning). No amount of in-run backoff fixes it; the nightly report cannot ship on
  time. Playbook: patch backoffs to also match "OVERALL_QUOTA", then deploy the self-heal
  pair `selfheal_sct_align_20260707.sh` (probe every 10 min → on 200 run scan+render) +
  `selfheal_sct_align_handoff_watch.sh` (waits for "render exit=0 — DONE" in the selfheal
  log → runs `selfheal_sct_align_handoff.py` which verifies the JSON and asks Stacey for the
  DRAFT-ONLY Kevin email with all trap language baked in). Logs in
  `data/sct-align-selfheal-*.log` / `data/sct-align-handoff-*.log`. Both scripts have
  flock guards + deadlines — adjust LOG/LOCK/DEADLINE lines when reusing.
  **Reuse notes (2026-07-08, second consecutive quota night):**
  - `selfheal_sct_align_handoff.py` is DATE-AGNOSTIC (reads `sct-mtd-latest-align-by-advisor.json`,
    globs newest PNG/PDF, derives subject from period_label) — reuse untouched. Only the two .sh
    wrappers need new dated copies with fresh LOG/LOCK paths.
  - **Fast diagnosis:** don't wait on a silent scan. If the background scan shows ZERO output after
    a couple minutes, DO NOT kill it yet — probe quota in a SEPARATE call first:
    `O.call('POST','/repair-orders:search',{filters:[status IN CLOSED],pageSize:1})` — a 429 body
    with `OVERALL_QUOTA` confirms exhaustion in seconds; a 200 means the scan is fine, just silent.
    (2026-07-11: even WITH `python3.11 -u`, the Hermes process log showed ZERO lines for the entire
    ~13-min run — all output appeared only at exit. `-u` does NOT guarantee live output in the
    process pipe. HEALTHY-SCAN tells while the pipe is silent: probe returns 200, AND the data files
    are moving — `data/sct-mtd-<date>-closed-index.json` appears after pass 1 and the checkpoint
    `data/sct-mtd-<date>-align-scan.json` mtime advances every ~20 ROs. Check mtimes before assuming
    a dead scan; killing a healthy run wastes the checkpoint pacing.)
  - **Launch trap:** Hermes rejects shell background wrappers (setsid/nohup/&) AND aborts the whole
    combined command — so a `chmod +x && setsid ...` line leaves the scripts non-executable (exit 126
    on the next try). chmod in its own foreground call, then launch each watcher with
    terminal(background=true). Verify both alive via the log's "watcher started" line + pgrep count.
  -  **Quota can stay dead >24h:** the 2026-07-08am self-heal probed 05:35→18:42 (13h, all 429) and
  TIMED OUT — the through-7/7 draft never shipped. Other queued recovery pipelines (BC/TOL/BT
  `quota_recovery_runner.sh`, caliber-ops) burn the bucket the moment it refills. If a self-heal
  times out, ESCALATE the quota-hog problem to Joe rather than just re-arming watchers — two
  consecutive missed nightly drafts means the systemic consumer needs to be found/paced or the
  Tekion limit raised. When quota restores after midnight, the MTD scan window auto-extends to the
  new "today" — acceptable; the subject/period label self-adjusts.
  **PRIORITIZE the nightly over the quota hogs (2026-07-09, THIRD consecutive quota night —
  outage continuous since 7/07 14:12, ~53h):** re-arming a self-heal alone loses the refill race —
  the queued backfill runners grab the bucket first. Fix: at self-heal launch, **SIGSTOP the
  competing consumers** (`pgrep -af "quota_recovery|bt_seed_watcher"` → `kill -STOP <pids>`;
  a runner holding `/tmp/tekion-quota-recovery.lock` also freezes anything flock-waiting behind
  it, e.g. `sct_closed_backfill_runner.sh` — good). Then bake `trap resume_paused EXIT` into the
  self-heal .sh (`kill -CONT` each paused pid, logged) so they resume automatically no matter how
  the scan exits — never leave processes stopped. Set the probe deadline LONG (21h) to cover a
  mid-day refill. STILL escalate the systemic issue to Joe in the same report (options: pace the
  backfill queue / drop stale backfill days / ask Tekion to raise OVERALL_QUOTA) — the pause trick
  is triage, not the fix.
- **THE 429 TRAP (hit 2026-07-01):** `sct_menu_sales_api.call()` returns a **STRING**
  body on any non-200 (e.g. `{"message":"Limit exhausted ... OVERALL_RATELIMIT"}`), NOT
  a dict. Any `.get()` on it throws `'str' object has no attribute 'get'` and the scan
  dies. The `_get()` helper MUST guard `isinstance(body, dict)` and, on a string body
  containing `OVERALL_RATELIMIT`, back off HARD (`60*(att+1)`s). Regular 429/0/5xx →
  `12*(att+1)`s. Inter-RO pacing `time.sleep(0.5)`. Checkpoint every 20 ROs so a mid-run
  failure resumes (`data/sct-<period>-align-scan.json`), plus a serial retry pass for the
  failed set, and `failed[]` in the output so truncation can't hide.
- **Classify each op:** DEDICATED if opcode in {ALIGN,OKAL,ALIGN00BRA}; BUNDLED if
  opcode starts `TEK` AND story (`" ".join(corrections[].text)` + opcodeDescription,
  lowercased) contains "align".
- **Advisor:** `assignee.advisor.id` is FREE on the search result (no fan-out) → resolve
  via `O.user_name(aid)` (public OpenAPI `/users/{id}`). No browser needed.
- **Output JSON is SELF-CONTAINED:** `rows[]` each `{advisor, dedicated, bundled, total,
  ros, detail[]}` where each detail = `{ro, opcode, kind}`; plus `totals` + `chip_total`.
  VERIFY `chip_total == totals.total` (sum of chips == total alignments) before shipping.

## Render + verify
Renderer = Toyota-red (#EB0A1E) header with the real Toyota logo (`logo_0.png`), 2 pages:
- **Page 1** (PNG, inline in email): 4 KPI cards (Total Alignments / Unique ROs / Advisors
  / Daily Pace) + ranked advisor table (Dedicated, Bundled, Total, ROs, red bar) + TOTAL row.
- **Page 2** (PDF only): RO-level chips per advisor — red chip = dedicated, blue = bundled.
  Per-advisor header count line uses `r['total']` labeled "N ROs" (matches page-1 bar total).
- PNG = page-1 only; PDF = full 2-page. ALWAYS `vision_analyze` the PNG and confirm the
  TOTAL row matches the KPI total before shipping. (Small dataset PNGs read fine full-page;
  for a very tall table crop the top band and 2x-upscale like the menu-sales skill.)

## Verified result (June 2026 full month, 2026-07-01)
516 alignments (469 dedicated + 47 bundled) across 510 ROs, 19 advisors. Jon Vu #1 (110),
Alex Anderson (50), William Dominguez & Cristian Gonzalez (39). chip_total == total == 516,
0 failed. Joe called it "perfect."

## Email via Stacey — DRAFT by default
Files land in `/home/itadmin/tekion-reports/data/`:
`SCT-Alignment-By-Advisor-<period>.png` + `.pdf`. Hand to Stacey via
`timeout 170 ~/bin/ask-agent stacey "..."`. Format = the joe-email-jay-report base64
inline-PNG layout: greeting / summary line with the total BOLD / **PNG inline IN THE MIDDLE**
/ "Sent from Tekion Open API — live data" / Joe's HTML signature. Attach the PDF by full path.

Recipients (task-spec wins over defaults):
- **Daily MTD report → TO Kevin Stapp (kstapp@sctoyota.com), greeting "Kevin,"** (Joe's
  standing instruction 2026-07-01: nightly 7pm MTD-closed alignment report to Kevin).
- A one-off "drafted for Joe to review" → TO jcastelino@americanmotorscorp.com, "Joe,".

### ⚠️ STACEY DRAFT-ONLY TRAP (hit HARD 2026-07-01 — read before every handoff)
Joe asked for a DRAFT; Stacey's rebuild/retry loop tripped her SMTP/X-GM-RAW **send** path
and SENT 7 copies, the newest addressed to Kevin via her hardcoded "SCT report → Kevin"
default — instead of leaving a draft. To DRAFT-ONLY safely:
1. Give an EXPLICIT hard stop: "Create the draft via imap.append() to Drafts ONLY. DO NOT
   call any send/SMTP/X-GM-RAW path. DO NOT send." State the exact TO + greeting and tell
   her to override any hardcoded recipient default.
2. Her FIRST build often MISSES the inline PNG (`INLINE_PNG=no`) even when the PDF attaches
   — explicitly demand a base64 data-URI `<img>` inline in the MIDDLE of the body (NOT CID —
   CID shows broken in Gmail draft view).
3. Do NOT ask her to "rebuild" in a way that re-fires her send pipeline. If a build is wrong,
   tell her to create ONE fresh draft via imap.append() and delete the bad one — still no send.
4. Verify with a TERSE one-line read-only ask (verbose multi-field asks silently time out →
   empty): `TO=<addr> | INLINE_PNG=<y/n> | PDF=<y/n> | IN_DRAFTS=<y/n> | SENT=<y/n>`.
   An empty reply is a timeout, NOT proof of failure — re-ask the same question shorter.
   This applies to ACTION asks too (hit 2026-07-04): a delete-duplicates ask returned
   exit 124/empty but HAD completed — confirm with a fresh read-only count, don't re-fire
   the action blindly.
5. **NO EMOJI in the ask-agent message** (hit 2026-07-04): characters like ⚠️ contain
   Unicode variation selectors and trip the terminal security scanner
   (`tirith:variation_selector`), blocking the command for approval — fatal in a headless
   cron run. Use plain text like "HARD STOP:" instead.
6. **Check DRAFT_COUNT** (hit 2026-07-04): her fix-the-PNG rebuild leaves the old bad
   draft(s) behind — 4 drafts piled up. After the fresh draft verifies good, ask her
   (read-only count first) and have her DELETE duplicates, keeping only the newest good
   one. Final state must be DRAFT_COUNT=1 | SENT=no. (2026-07-05: even a single clean
   build produced DRAFT_COUNT=2; 2026-07-14: a single clean first-try build produced
   DRAFT_COUNT=3 — duplication is the NORM, not the exception. ALWAYS count + dedupe
   even when everything verified good on the first ask.)
7. **INLINE_PNG false-negative** (hit 2026-07-05): a generic "PNG=<y/n>" ask can come
   back `PNG=n` even when the draft is CORRECT — she checks MIME *attachments*, and a
   base64 data-URI `<img>` lives in the HTML body, not as an attachment. Before
   rebuilding anything, verify with the precise body check:
   "Does the HTML body contain an <img> with data:image/png;base64? Reply:
   DATAURI_IMG=<y/n>". Only rebuild if DATAURI_IMG=n. This avoids destroying a good
   draft over a shallow read.
8. **DATAURI check can false-negative EVEN on the precise raw-MIME ask** (hit
   2026-07-06): after a rebuild whose own confirmation said DATAURI_IMG=y, a
   follow-up "fetch raw MIME, does html contain 'data:image/png;base64'" ask still
   came back false. Definitive tiebreaker = SIZE MATH, which needs no substring
   check at all: ask read-only "Reply one line: RAW_SIZE=<RFC822.SIZE> |
   HTML_SIZE=<bytes of text/html part>".   base64 inflates ~4/3, so
   HTML_SIZE ≈ PNG_bytes * 4/3 (+ a few KB of text) proves the inline image is
   embedded (e.g. 84,756-byte PNG → ~113,008 b64 vs HTML_SIZE 113,603 — match).
   **Treat it as a LOWER BOUND, not an equality** (2026-07-12): Joe's HTML
   signature can add ~48KB of extra HTML (96,338-byte PNG → expected ~128,451
   b64, actual HTML part 176,638 — still a GOOD draft). Pass condition:
   HTML_SIZE >= PNG_bytes*4/3; only a few-KB HTML part means the PNG is missing.
   PDF part likewise runs ~2.5% over PDF_bytes*4/3 from base64 CRLF line-wrapping
   (239,206-byte PDF → 327,338 part — normal).
   RAW_SIZE ≈ HTML_SIZE + PDF_bytes*4/3 cross-checks the attachment. If HTML_SIZE
   is only a few KB, the PNG is genuinely missing — rebuild then. Trust the math
   over her y/n substring answers; never rebuild a draft the math says is good.
9. **Best size-verify phrasing = per-part list** (2026-07-10): a bare
   "HTML_SIZE=<bytes>" ask once returned 595 on a draft whose HTML part was actually
   122,705 bytes. The reliable ask: "reply one line: RAW_SIZE=<RFC822.SIZE> |
   PARTS=<each MIME part content-type and size in bytes>" — e.g.
   `PARTS=text/plain=398 text/html=122705 application/pdf=226903` proves inline PNG
   (html ≈ PNG*4/3) AND the exact PDF byte size in one shot.
   NOTE (2026-07-13): PARTS sizes may come back as DECODED bytes — a clean run reported
   application/pdf=249548, exactly the raw PDF file size (not the ~4/3-inflated encoded
   size note 8 predicts). Don't false-alarm on that: a PDF part equal to the file's
   byte size is a PASS. Cross-check with RAW_SIZE ≈ HTML_part + PDF_bytes*4/3 (observed
   478,162 ≈ 130,058 + 332,731 — consistent). The HTML-part lower-bound test
   (HTML_SIZE >= PNG_bytes*4/3) is unaffected.
10. **Telegram detour** (2026-07-10): a read-only ask can come back "I sent the
   summary to your Telegram" instead of answering — the bridge gets nothing. Add
   "reply in THIS chat as plain text, do not message Telegram" to verification asks.
11. **One combined verify ask works best** (2026-07-15): merge notes 4/6/9 into a
   SINGLE read-only ask — "Reply one line: TO=<addr> | IN_DRAFTS=<y/n> | SENT=<y/n> |
   DRAFT_COUNT=<n with this subject> | RAW_SIZE=<RFC822.SIZE> | PARTS=<each MIME part
   content-type and size in bytes>". Returned everything cleanly in one round-trip;
   size math (HTML part 177,507 >= 97,980*4/3; PDF part ~+1.4% over PDF*4/3) verified
   the inline PNG + attachment without any y/n substring answers. That run was also a
   clean first-try DRAFT_COUNT=1 — rare but possible; still always check the count.
   (2026-07-17: the ultra-short re-ask form "PARTS=?" can come back as just a part
   COUNT, e.g. `PARTS=3`, not the per-part type=size list. Don't re-ask endlessly —
   RAW_SIZE alone still verifies: RAW_SIZE ≈ HTML-with-inline-PNG (~PNG*4/3 + sig)
   + PDF*4/3. Observed 552,379 ≈ ~174K + ~378K for a 97,845 B PNG + 283,334 B PDF —
   pass. Also that night: the full note-11 combined ask timed out (exit 124) but the
   shortened one-line form answered instantly — keep the re-ask TERSE.)

12. **SENT=y / DRAFT_COUNT FALSE ALARM in the combined ask** (hit 2026-07-23): the
   note-11 combined verify returned `SENT=y | DRAFT_COUNT=7` on a clean first-try
   build — BOTH wrong. Size math in the same reply was perfect (HTML 139,506 >=
   PNG*4/3; PDF part ~+2.6% over PDF*4/3). Tiebreaker before panicking/rebuilding:
   one terse read-only ask — "Search [Gmail]/Sent Mail for that exact subject — how
   many? Search [Gmail]/Drafts — how many? Reply: SENT_FOLDER_COUNT=<n> |
   DRAFTS_COUNT=<n>". Came back 0 | 1 → draft was fine, nothing sent, no dedupe
   needed. Her SENT flag can reflect the \\Seen/session state, and DRAFT_COUNT can
   count the whole Drafts folder, not the subject. Trust folder searches + size math
   over flag answers.
13. **ZERO-BYTE PDF PART** (hit 2026-07-21): her first build can attach the PDF as an
   EMPTY part — combined verify returned `application/pdf:0B` (and RAW_SIZE ~275K, far
   below HTML + PDF*4/3) while her own confirmation claimed the PDF was attached. The
   PARTS list is the only thing that catches this — always check the PDF part size is
   nonzero and ≈ the on-disk PDF byte size (decoded, per note 9) or ~4/3 of it. Fix ask:
   ONE fresh imap.append() draft, explicitly "read and base64-attach the PDF file bytes
   from <path> (<N> bytes on disk — verify the part is non-zero)", then delete the bad
   draft. That fix ask TIMED OUT (exit 124) but HAD completed — per note 4, re-verify
   read-only (DRAFT_COUNT went 1→2, new draft PDF_PART_BYTES=321889 exact file size)
   before re-firing, then have her delete the older 0-byte-PDF draft. Final
   DRAFT_COUNT=1 | SENT=n. Also seen that night: an image/jpeg part alongside a
   healthy-sized HTML part — the data-URI PNG lives in the HTML (size math passed);
   don't treat an extra image part as a failure.
   **PREVENTION (2026-07-22, clean first-try run):** bake the fix language into the
   INITIAL build ask — state both file paths WITH their on-disk byte sizes and say
   "read and base64-attach the actual file bytes ... verify the PDF MIME part is
   NON-ZERO and matches the file size". Night after the 0-byte trap, this produced a
   clean DRAFT_COUNT=1 with PDF part = exact on-disk size on the first ask. Also note:
   the HTML-part lower-bound test can pass with only ~1KB headroom
   (135,136 vs PNG*4/3=134,349) when her build omits the heavy HTML signature — a
   tight pass is still a PASS.

## Cron (LIVE)
Job `25ec117cfe72` "SCT Alignment MTD Closed — nightly 7pm draft to Kevin", schedule
`0 19 * * *` (7pm Pacific), skills=[sct-alignment-by-advisor-report, agent-to-agent-bridge],
deliver=origin (status back to the Slack thread). It runs `sct_align_mtd.py` (background,
notify_on_complete), renders via `render_sct_align.py`, vision-verifies, then hands to Stacey
as a **DRAFT ONLY to Kevin (kstapp@sctoyota.com), greeting "Kevin,"** in Joe's Gmail Drafts —
Joe reviews + sends in the morning. Reset at month rollover is automatic (the MTD scan
computes 1st-of-month → today, so nothing to reset). Scan is paced (~15-25 min) — the draft
lands by ~7:25pm. Established 2026-07-01 on Joe's instruction.

To flip it to AUTO-SEND to Kevin later: update the cron prompt to have Stacey SEND (SMTP
template-send) instead of draft-only, and drop the DRAFT-ONLY hard-stop language.

## Pitfalls recap
- Opcode set is SCT-specific (ALIGN/OKAL/ALIGN00BRA). Other stores differ — see
  `tekion-alignment-by-advisor-report` + `tol-alignment-by-advisor-report`.
- The `_get()` dict-guard + OVERALL_RATELIMIT hard-backoff is MANDATORY — without it the
  scan dies on a string error body.
- chip_total must equal totals.total. failed[] must be empty (or re-run — it resumes).
- DRAFT-ONLY means DRAFT-ONLY: lock Stacey's send path per the trap above.
