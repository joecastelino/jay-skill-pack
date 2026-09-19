# TOL Menu Sales — archived per-run logs (Aug 2026)

Moved out of SKILL.md 2026-08-30 to stay under the 100KB skill limit.
Historical detail only; the canonical procedures live in SKILL.md.

## (8/22 8:05PM, Closed MTD) Clean one-shot, zero exit-124s across ALL 4 calls
Hand-off returned in 78s (no timeout), draft correct FIRST TRY. Verification asks all FIRST try
with "use raw IMAP, NOT the Gmail API" leading: subject-list 32s, MIME part-listing 128s (parts-only
wording per the 8/22-noon lesson — no bolded-total request), Sent-check 52s. MIME clean:
text/plain + text/html + image/png Content-ID=<scorecard> + application/pdf. No dedupe needed.
BOGUS-UID VARIANT recurred yet again: save confirmation said "#42591", subject-list said 63, and
the part-listing ask replied "UID 42591 (UID 63 was wrong; found by subject)" — the
`UID N (subject "<exact>") ... if that UID is wrong, find it by that exact subject instead`
wording keeps self-healing this. Sent-check = 2 hits, both old June 1-29 em-dash emails (token
trap, item 5b), no leak. Drafts stack tiny (6 TOL total): 08/21 + 08/22 Opened & Closed, plus the
perennial 08/02 em-dash pair (UIDs 19/20) — still flag-don't-delete.
Data: 143 closed ROs scanned, 2 prefilter hits, 28 MTD rows / $7,101.35; closed-append ran
FOREGROUND in ~12s (foreground-with-generous-timeout pattern confirmed again).

## (8/23 12:05PM, Opened) Clean one-shot on a genuine $0 day; only part-listing needed a retry
Hand-off returned in 58s (no exit-124), draft UID 42593 correct FIRST TRY, no dedupe needed
(no prior draft with today's exact subject). Subject-list returned FIRST try (63s) with
"use raw IMAP, NOT the Gmail API" leading. MIME part-listing 124'd once at 234s even with the
parts-only wording that worked 8/22 — a sleep-45 + STRIPPED-FURTHER re-ask (dropped the
"If that UID is wrong..." clause and the "One raw IMAP fetch only" phrasing down to
"Raw IMAP only... One fetch: [Gmail]/Drafts, subject \"<exact>\"") returned in 22s with clean
parts (multipart/related > alternative(text/plain+text/html) + image/png Content-ID=scorecard
+ application/pdf). So when parts-only still 124s, drop the UID entirely and search by subject
only. Sent-check FIRST try (102s) = 4 hits, all old em-dash-era sends (06/30-07/03), zero today
= no leak. Data: 58 opened ROs scanned, 0 menus / $0.00 — genuine zero per the $0-validation
rule (healthy RO count, plausible for a Sunday noon pull). Drafts stack tiny (4): 08/21, 08/22,
08/23 hyphen-subject Opened drafts plus the perennial 08/02 em-dash one (UID 41547).

## (8/23 8:05PM, Opened) TEXTBOOK CLEAN RUN — zero exit-124s, genuine $0 day, TRUE dedupe
Second genuine $0 day in a row (noon was also $0). EOD pull scanned **74 opened ROs**, 0 menus,
$0.00 — healthy RO count for a Sunday, so a real zero per the $0-validation rule; rendered and
drafted honestly. Hand-off returned in **134s** (no timeout), draft correct FIRST TRY with TRUE
dedupe — she found and deleted the noon draft (UID 64) on her own before building. All 3
verification asks returned FIRST try with "use raw IMAP, NOT the Gmail API" leading the ask:
subject-list 85s, MIME part-listing 66s (parts-only wording per the 8/22-noon lesson), Sent-check
50s. MIME clean: multipart/mixed > related > alternative(text/plain+text/html) + image/png
Content-ID=<scorecard> 43,800B + application/pdf 29,217B.
BOGUS-UID VARIANT recurred AGAIN (now near-universal): her save confirmation said "himalaya 42601
(IMAP UID 67)" and the subject-list ALSO showed `67 | ...`, but the part-listing ask replied
"UID 67 was wrong — correct IMAP UID is 42601" and listed the right MIME. The standing wording
`UID N (subject "<exact>") ... if that UID is wrong, find it by that exact subject instead`
self-heals this every time — keep it.
Sent-check via the SHORT subject stem = 4 hits, all old em-dash-era sends (06/30-07/03), zero
today = no leak; \Draft-flag follow-up skipped per the 8/17 note. Drafts stack tiny (4): 08/21,
08/22, 08/23 hyphen-subject Opened drafts plus the perennial 08/02 em-dash one (UID 20).

## (8/24 12:05PM, Opened) TEXTBOOK CLEAN RUN — 3rd consecutive genuine $0 day
Zero exit-124s, zero corrections, CORRECT UID reported (no bogus-ID self-correction needed).
Hand-off returned in 106s, draft 42629 (IMAP UID 69) correct FIRST TRY: multipart/mixed >
related > alternative(text/plain+text/html) + image/png Content-ID=<scorecard> 43,903B +
application/pdf 29,216B. No dedupe needed. All 3 verification asks returned FIRST try and
FAST with "use raw IMAP, NOT the Gmail API" leading + parts-only part-listing wording:
subject-list 24s, MIME part-listing 21s, Sent-check 24s.
DATA: 83 opened ROs scanned, 0 menus / $0.00 — THIRD straight $0 day (8/23 noon, 8/23 EOD,
8/24 noon). Verified genuine via the opcode sanity scan: 12 TEK ops present but ALL were
numeric-suffix opcodes (TEK09030103 / TEK09040104 / TEK09050103 / TEK09070103), zero overlap
with the 212 TEK<mileage><tier> menu set. Prefix histogram was the classic real-$0 shape
(SUR 68, INV 68, FLO 68, TPS 64, MPV 58, CON 36, TXM 23, LOF 16). A multi-day $0 streak is
NOT by itself evidence of a pipeline bug — run the sanity scan and report honestly.
SANITY-SCAN PROBE GOTCHA (cost 2 wasted iterations): do NOT hand-roll the RO/jobs/operations
traversal from guessed field names. The correct shapes are `ro["documentId"]`,
`jobs["data"]["jobs"]`, `ops["data"]["roOperations"]` — a generic
`out.get("data", out.get("content", []))` returns a dict and yields either a `TypeError:
unhashable type: 'slice'` or an all-`HTTP***`-prefix histogram (silent false negative that
looks like the API is broken). Reuse the script's own `O.fetch_ros(ms0, ms1)` helper (which
also carries the 429 backoff) and copy `scan_ro`'s exact key path from
`sed -n '250,300p' tol_menu_sales_api.py` before writing any probe.
Drafts stack tiny (5): 08/21-08/24 hyphen-subject Opened drafts plus the perennial 08/02
em-dash one (UID 20) — single copy, not a true duplicate, still flag-don't-delete.

## (8/24 8:05PM, Opened) Clean run — 4th consecutive genuine $0 day
Zero exit-124s, correct UID, TRUE dedupe, MIME clean. 129 opened ROs, 0 menus / $0.00.
Sanity scan confirmed genuine (16 TEK ops, all numeric-suffix, zero menu-set overlap).

## (8/25 12:05PM, Opened) Clean run — 5th consecutive genuine $0 day
Zero exit-124s. Bogus-UID variant recurred (reported 42661, subject-list said 76; part-listing
self-healed off the exact subject). 105 opened ROs, 0 menus / $0.00; sanity scan genuine.
SANITY-SCAN PROBE RECIPE (reuse verbatim): build `_probe_<date>.py` that does
`import tol_menu_sales_api as O`, `O.fetch_ros(ms0, ms1)`, then per RO
`O.call("GET", f"/repair-orders/{rid}/jobs")` -> `jobs["data"]["jobs"]` ->
`O.call("GET", f"/repair-orders/{rid}/jobs/{j['id']}/operations")` -> `ops["data"]["roOperations"]`.
Cap at ~60 ROs (full 105 exceeds the execute_code 300s budget; 60 took 149s).

## (8/25 8:05PM, Opened) TEXTBOOK CLEAN RUN — 6th consecutive genuine $0 day
Zero exit-124s across ALL 4 calls, CORRECT UID (78) reported and it worked first try on the
part-listing (no bogus-ID self-correction needed). Hand-off returned in 106s, draft correct
FIRST TRY with TRUE dedupe (she found and deleted the noon draft on her own before building).
MIME clean: multipart/mixed > related > alternative(text/plain+text/html) + image/png
Content-ID=<scorecard> + application/pdf. Verification asks with "use raw IMAP, NOT the Gmail
API" leading + parts-only part-listing wording: subject-list 42s, part-listing 41s, Sent-check
40s. Sent-check = 4 hits, all old em-dash-era sends (06/30-07/03), zero today = no leak.
DATA: 163 opened ROs scanned (busy Monday), 0 menus / $0.00 — SIXTH straight $0 opened day
(8/23 noon through 8/25 EOD). Sanity scan over the first 55 ROs confirmed genuine: 16 TEK ops,
ALL numeric-suffix (TEK09040104 x6, TEK09070103 x3, TEK09030103 x3, TEK09050103 x2,
TEK09010103 x2), ZERO menu-set hits; classic real-$0 prefix histogram (MPV 52, TPS/SUR/INV/FLO
49, TXM 35, LOF 16, CON/UCD 12). KEEP ESCALATING to Joe.
SANITY-SCAN PROBE GOTCHA (new, cost 1 iteration): `data/tl-menu-opcodes.json` is a list of
DICTS, not a list of strings — build the set as `{d["opcode"] for d in json.load(...)}`.
A bare `set(json.load(...))` raises `TypeError: unhashable type: 'dict'`.
Drafts stack tiny (6): 08/21-08/25 hyphen-subject Opened drafts + the perennial 08/02 em-dash
one (UID 20).

## (8/27 12:05PM, Opened) TEXTBOOK CLEAN RUN — best opened day since the $0 streak
Zero exit-124s across ALL 4 ask-agent calls. Hand-off produced a correct draft FIRST TRY, no
dedupe needed (0 prior drafts with today's exact subject). All 3 verification asks returned
FIRST try and fast with "use raw IMAP, NOT the Gmail API" leading + parts-only part-listing
wording. MIME clean: multipart/mixed > related > alternative(text/plain+text/html) +
image/png Content-ID=<scorecard> inline + application/pdf attachment.
BOGUS-UID VARIANT — INVERTED THIS RUN: her save confirmation said "Draft ID 42729", the
subject-list said UID 88, and the part-listing said "UID 88 doesn't exist for that subject.
Actual UID is 42729" and resolved by subject. So the SUBJECT-LIST's UID can be the wrong one,
not just her reported id. Lesson unchanged and reinforced: never trust ANY reported numeric
id — always carry the `UID N (subject "<exact>") ... if that UID is wrong, find it by that
exact subject instead` wording, which self-healed it again.
UNPROMPTED CAVEAT: Stacey volunteered a warning that "CID images typically get stripped in
Gmail draft preview, fallback is Imgur hosted URL." Ignore it — the part-listing proved a real
image/png cid=scorecard part exists. Don't order an Imgur rebuild over her speculative note.
DATA: 105 opened ROs scanned, **3 menus / $647.20** ($433.64 labor + $213.56 parts) — the
strongest opened day since the six-day $0 streak (8/23-8/25) broke on 8/26. Gustavo Alatorre
2 menus/$251.06; 1 menu ($396.14, RO 398946 TEK30000BNM 2025 Camry) landed on the
"Any Service Advisor" placeholder, which the renderer shows as **"Unassigned"** — normal,
that's an unassigned-advisor RO, not a rendering bug. Note again `totals.parts_price`
($452.82) != `parts_gross` ($213.56); scorecard + email use GROSS.
Sent-check = 6 hits, ALL old em-dash-era sends (06/29-07/03), zero today = no leak.
Drafts stack = 15 TOL total (08/21-08/27 Opened & Closed pairs + the perennial 08/02 em-dash
pair UIDs 19/20) — no true dupes.

## (8/26 12:05PM, Opened) TEXTBOOK CLEAN RUN — $0 streak BROKEN at 6 days
Hand-off returned in 189s (no exit-124), draft correct FIRST TRY, no dedupe needed (0 prior
drafts with today's exact subject). All 3 verification asks returned FIRST try and FAST with
"use raw IMAP, NOT the Gmail API" leading + parts-only part-listing wording: subject-list 25s,
MIME part-listing 36s, Sent-check 37s. MIME clean: multipart/mixed > related >
alternative(text/plain+text/html) + image/png Content-ID=<scorecard> + application/pdf.
BOGUS-UID VARIANT recurred mildly: save confirmation said "Draft ID 42695", subject-list said
UID 82; part-listing resolved it by subject and reported UID 42695 with correct MIME. Standing
`UID N (subject "<exact>") ... if that UID is wrong, find it by that exact subject instead`
wording self-heals it again. Sent-check = 4 hits, all old em-dash-era sends (06/30-07/03),
zero today = no leak.
DATA: 103 opened ROs scanned, **1 menu / $114.48** ($55.52 labor + $58.96 parts), advisor
Gustavo Alatorre, RO 398771, TEK50000BNM on a 2025 Camry. This ENDS the six-consecutive-$0
opened-day streak (8/23 noon - 8/25 EOD) — good news to report to Joe alongside the standing
escalation. Note the JSON's `totals.parts_price` ($130.43) differs from `parts_gross` ($58.96);
the scorecard/KPI + email use PARTS GROSS — use gross, not price.
Drafts stack = 13 TOL total (08/21-08/26 Opened & Closed pairs + the perennial 08/02 em-dash
pair UIDs 19/20) — no true dupes.

## (8/26 8:05PM, Opened) Clean draft, TRUE dedupe; only the INITIAL hand-off exit-124'd
Initial hand-off hit exit-124 at 235s — but per the 8/19-EOD lesson, a subject-search right
after showed the draft HAD saved correctly (UID 42714) AND true dedupe had happened (the noon
draft 42695 with the identical subject was gone; exactly one 08/26 hit). NEVER blind re-fire.
All 3 verification asks returned FIRST try and fast with "use raw IMAP, NOT the Gmail API"
leading + parts-only part-listing wording: subject-list 38s, MIME part-listing 44s, Sent-check
44s. MIME clean: multipart/mixed > related > alternative(text/plain+text/html) + image/png
Content-ID=<scorecard> inline + application/pdf attachment. Reported UID matched (no bogus-ID
self-correction needed). Sent-check = 4 hits, all old em-dash-era sends (06/30-07/03), zero
today = no leak.
DATA: 165 opened ROs scanned, **2 menus / $200.25** ($121.45 labor + $78.80 parts), both
Gustavo Alatorre (RO 398771 TEK50000BNM 2025 Camry; RO 398800 TEK10000BNM 2016 Tacoma).
Second consecutive non-zero opened day after the six-day $0 streak — trend is recovering.
JSON QUIRK: `records` array in `tol-menu-sales-opened-<date>.json` can be EMPTY (0) while
`totals` and the companion `tol-menu-sales-api-<date>.json` (`record_count`, per-RO lines in
the run log) carry the real rows — read the per-advisor detail from the API JSON / run log,
not from `opened.records`. Also `totals.parts_price` ($180.02) != `parts_gross` ($78.80);
the scorecard and email use GROSS.
Drafts stack tiny (7): 08/21-08/26 hyphen-subject Opened drafts + the perennial 08/02 em-dash
one (UID 41547).

## (8/27 8:05PM, Closed MTD) TEXTBOOK CLEAN RUN — best closed day of August
Zero exit-124s across ALL 4 ask-agent calls. Draft correct FIRST TRY, no dedupe needed (0 prior
drafts with today's exact subject). All 3 verification asks FIRST try with "use raw IMAP, NOT
the Gmail API" leading + parts-only part-listing wording. MIME clean: multipart/mixed > related
> alternative(text/plain 784B + text/html 1178B) + image/png Content-ID=<scorecard> 103,819B
inline + application/pdf 86,156B; bolded total $8,463.74 confirmed in body.
BOGUS-UID recurred: save confirmation AND subject-list BOTH said UID 92; part-listing replied
"UID 42749 — UID 92 was wrong" and resolved by exact subject. Standing `UID N (subject
"<exact>") ... if that UID is wrong, find it by that exact subject instead` wording self-heals.
Stacey again volunteered the UNPROMPTED "Gmail draft preview doesn't reliably render CID images,
want a hosted-image version?" caveat (same as 8/27 noon) — IGNORE it, the part-listing proved a
real image/png cid part; do NOT order an Imgur rebuild. Sent-check = 2 hits, both old June 1-29
em-dash emails (token trap, item 5b) — no leak.
NEW: her first build attempt hit a bytes-handling bug in her OWN dedupe loop and she
self-recovered inside the SAME ask (reported "no partial state", then saved). Don't re-fire on
a mid-reply error narration if the final line says the draft saved — verify by subject instead.
DATA: 162 closed ROs scanned, 6 prefilter hits, 6 new menu rows -> MTD moved 31 rows /
$7,344.56 to **37 rows / $8,463.74** ($5,742.74 labor + $2,721.00 parts). Today's +$1,119.18 is
the biggest single-day closed add of August and the 2nd consecutive non-zero closed day after
the 8/22-8/25 flat streak — the store-side menu-presentation escalation is easing; tell Joe.
Top advisor Gustavo Alatorre (18 menus, $2,353.65); Michael Hachey 3/$2,096.36. Closed-append
ran FOREGROUND in ~30s. Drafts stack (Closed stem) = 8: Aug 1-21..1-27 + perennial 08/02
em-dash (UID 19) — no true dupes.

## (8/26 8:05PM, Closed MTD) TEXTBOOK CLEAN RUN — zero exit-124s, flat streak BROKEN
Hand-off returned in 216s (no timeout), draft correct FIRST TRY, no dedupe needed (0 prior
drafts with today's exact subject). All 3 verification asks returned FIRST try and FAST with
"use raw IMAP, NOT the Gmail API" leading + parts-only part-listing wording: subject-list 35s,
MIME part-listing 34s, Sent-check 33s. MIME clean: multipart/mixed > related >
alternative(text/plain+text/html) + image/png Content-ID=<scorecard> + image/jpeg <amglogos>
(sig logo, normal) + application/pdf. BOGUS-UID VARIANT recurred: save confirmation AND
subject-list both said UID 86, part-listing replied "UID 86 was wrong — the actual UID is
42715" and listed correct MIME. Sent-check = 2 hits, both the old June 1-29 em-dash emails
(token trap, item 5b) — no leak.
DATA: 170 closed ROs scanned, 3 prefilter hits, 3 new menu rows -> MTD moved 28 rows /
$7,101.35 to **31 rows / $7,344.56** ($5,050.56 labor + $2,294.00 parts). This ENDS the
four-consecutive-zero-delta closed-day streak (8/22-8/25), matching the opened side which
broke its six-day $0 streak on 8/26 noon. Top advisor by gross Michael Hachey (3 menus,
$2,096.36); most menus Gustavo Alatorre (15, $1,944.97). Closed-append ran FOREGROUND in
~25s. Drafts stack (hyphen stem) = 7: Aug 1-21 through 1-26 + the perennial 08/02 em-dash
one (UID 19) — no true dupes.

## (8/25 8:05PM, Closed MTD) TEXTBOOK CLEAN RUN — zero exit-124s, CORRECT UID, 4th zero-delta day
Hand-off returned in 76s (no timeout), draft UID 42674 correct FIRST TRY, and the reported UID
was CORRECT (part-listing found it directly — no bogus-ID self-correction needed). All 3
verification asks returned FIRST try with "use raw IMAP, NOT the Gmail API" leading + parts-only
part-listing wording: subject-list 53s, part-listing 41s, Sent-check 38s. MIME clean:
multipart/mixed > related > alternative(text/plain+text/html) + image/png Content-ID=<scorecard>
99,724B + application/pdf 78,381B. No dedupe needed (0 prior drafts with today's exact subject).
Sent-check = 2 hits, both the old June 1-29 em-dash emails (token trap, item 5b) — no leak.
DATA: 93 closed ROs scanned, 0 prefilter hits, MTD FLAT at 28 rows / $7,101.35 — identical to
8/22, 8/23, 8/24. That is FOUR consecutive zero-delta closed days on top of SIX consecutive $0
opened days (8/23 noon - 8/25 EOD). Keep escalating to Joe as a store-side menu-presentation
problem; pipeline is healthy (RO counts 93-215/day, opcode sanity scans clean).
Closed-append ran FOREGROUND in ~10s. Drafts stack (hyphen stem) = 6: Aug 1-21 through 1-25 +
the perennial 08/02 em-dash one (UID 41546) — no true dupes.

## (8/24 8:05PM, Closed MTD) Clean one-shot, zero exit-124s; ZERO-DELTA day
Hand-off returned in 103s (no timeout), draft correct FIRST TRY, no dedupe needed. All 3
verification asks returned FIRST try with "use raw IMAP, NOT the Gmail API" leading and the
parts-only part-listing wording: subject-list 29s, MIME part-listing 166s, Sent-check 185s
(both slow but no 124). MIME clean: multipart/mixed > related > alternative(text/plain +
text/html) + image/png Content-ID=<scorecard> + application/pdf.
BOGUS-UID VARIANT recurred yet again: save confirmation AND subject-list both said UID 74,
part-listing replied "UID 74 was wrong — found it at UID 42648" and listed correct MIME.
Sent-check = 6 hits, ALL old em-dash-era sends (06/29-07/03), zero today = no leak.
Drafts stack (hyphen stem) = 5: Aug 1-21, 1-22, 1-23, 1-24 + the perennial 08/02 em-dash
one (UID 19) — no true dupes.
DATA: 215 closed ROs scanned (busy day), 0 prefilter hits, so MTD stayed FLAT at 28 rows /
$7,101.35 — identical to 8/22 and 8/23. That's now THREE consecutive zero-delta closed days
alongside FOUR consecutive $0 opened days (8/23 noon through 8/24 EOD) — the combination is
worth flagging to Joe as a probable store-side menu-presentation/process problem, not a
pipeline bug (RO counts are healthy and the opcode sanity scan came back clean 8/24 noon).
Closed-append ran FOREGROUND in ~15s.

## (8/23 8:05PM, Closed MTD) TEXTBOOK CLEAN RUN — zero exit-124s across all 4 calls
Hand-off returned in 161s (no timeout), draft correct FIRST TRY, no dedupe needed. All 3
verification asks returned FIRST try with "use raw IMAP, NOT the Gmail API" leading and the
parts-only part-listing wording: subject-list 27s, MIME part-listing 37s, Sent-check 58s.
MIME clean: multipart/mixed > related > alternative(text/plain+text/html) + image/png
Content-ID=<scorecard> + application/pdf. BOGUS-UID VARIANT recurred (now essentially every
run): save confirmation AND subject-list both said UID 68, part-listing replied "found at IMAP
UID 42602, not UID 68" and listed correct MIME — the standing `UID N (subject "<exact>") ...
if that UID is wrong, find it by that exact subject instead` wording self-heals it every time.
Sent-check = 2 hits, both the old June 1-29 em-dash emails (token trap, item 5b), no leak.
Drafts stack (hyphen stem) = 4: Aug 1-21, 1-22, 1-23 plus the perennial 08/02 em-dash one
(UID 19) — no true dupes. DATA NOTE: Sunday close day — 29 closed ROs scanned, 0 prefilter
hits, so MTD stayed flat at 28 rows / $7,101.35 (identical to 8/22). Zero-delta days are
normal on Sundays; state it explicitly in the email body so Sean isn't confused by an
unchanged total. Closed-append ran FOREGROUND in ~10s.

## (8/21 8:05PM, Closed MTD) Clean one-shot, zero exit-124s; bogus-ID variant recurred
Draft correct first try; all 3 verification asks first try with "use raw IMAP, NOT the Gmail
API" leading. MIME clean (text/plain + text/html + image/png cid=scorecard + application/pdf);
bolded total $6,645.14 confirmed — keep asking her to quote the bolded total, it's a free
content check. Bogus-ID recurred (her reported id and the subject-list id were both himalaya
numbering, not IMAP UIDs) and self-healed off the exact subject. Sent-check = 2 old June
em-dash hits (token trap, item 5b), no leak. Data: 117 closed ROs, 2 hits, 26 rows/$6,645.14;
closed-append ran FOREGROUND in ~8s.

## (8/20 8:05PM, Closed MTD) Clean one-shot; hyphen-subject hid OLD em-dash drafts from search
Draft correct first try; all 3 verification asks first try with "use raw IMAP, NOT the Gmail
API" leading. Wrinkle: a literal-hyphen subject search only matched hyphen-era drafts — old
em-dash drafts didn't surface. Harmless (dedupe only cares about TODAY's exact subject), but
don't read a small count as "Joe cleared the backlog"; search the short stem "TOL Menu Sales
Closed" for the true stack size. Bogus-UID variant recurred and self-healed via the
`UID N (subject "<exact>") ... if that UID is wrong, find it by that exact subject` wording.



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

