---
name: tekion-deferred-by-advisor-daily
description: Build the "work deferred/declined per DAY, broken down by service advisor" report for any AMG Tekion store — advisor ranking + trailing-day trend + per-advisor RO-level detail pages (PNG/PDF/CSV). Zero OpenAPI quota.
triggers:
  - deferred by advisor
  - declined work per day by advisor
  - daily deferred report
  - deferred work daily
---

# Deferred Work by Advisor — Daily

## Scripts
- Pull:   `/home/itadmin/tekion-reports/deferred_by_advisor_daily.py <STORE> <YYYY-MM-DD> [TREND_DAYS]`
- Render: `/home/itadmin/tekion-reports/render_deferred_by_advisor.py data/<store>-deferred-by-advisor-<date>.json`
- Outputs: `data/<STORE>-Deferred-By-Advisor-<date>.{png,pdf,csv}` (PNG = page 1 only; PDF = page 1 + one page per advisor with RO-level detail — Joe's standing preference for advisor reports).

## Data source
Internal `POST /api/service-module/u/reporting/recommendation/search`, `RO_RECOMMENDATIONS`,
`status IN [DEFERRED]`, `roClosedTime BTW [dayStart, dayEnd]` in **Pacific**.
Headers from `/tmp/tekion_rec_headers.json` (see `tekion-declined-deferred-services-report` for the
passive XHR-hook re-capture). Store switch = swap `dealerId` + `tek-siteId: -1_<id>` only.
$ are **CENTS** → /100. Offset pagination is fine at day granularity (<10K rows).

### STEP ZERO-A: FASTEST 401 fix — read the token straight out of localStorage (verified 2026-08-25)
**Skip the XHR hook entirely.** The only header that actually expires is `tekion-api-token`;
everything else in `/tmp/tekion_rec_headers.json` is static. Pull the live token from the
authenticated `:9223` browser and merge it in — ~10 seconds, no hook, no SPA driving:

```python
tok = "".join(ev(f"(localStorage.t_token||'').slice({i},{i+200})") for i in range(0,536,200))
h = json.load(open("/tmp/tekion_rec_headers.json"))
h["tekion-api-token"] = tok
json.dump(h, open("/tmp/tekion_rec_headers.json","w"), indent=1)
```
`t_token` is ~536 chars and `/eval` truncates long strings — slice it in 200-char chunks and
verify `len(tok)` matches what `localStorage.t_token.length` reported.

**TRAP that costs a wasted cycle:** do NOT also overwrite `userId`/`roleId` from localStorage.
`localStorage.__user_id` is the **email string** (`"jcastelino@scvolkswagen.com"`) and
`currentActiveRoleId` is a *different* role id than the one the recommendation endpoint wants.
Writing those in produces a fresh 401 that looks like the token pull failed. Keep the static values:
`userId`/`original-userid` = `8cc203af-a87e-4fd7-8090-745a0ffa2339`,
`roleId` = `656e21e547e83861236c5e0c`. Also note the token works regardless of which dealer
`:9223` is currently sitting on (it was on TL/1092 while pulling BC/1251 data fine) — the script
sets `dealerId`/`tek-siteId` itself, so **no dealer switch is needed** for this report.

**Check `/pages` FIRST if `/eval` behaves oddly.** On 2026-08-25 `:9223` had 4 tabs (a ServiceNow
KB tab + two `/login?redirectTo=` orphans); the bound page was a valid authenticated Tekion coupon
page, so the token read worked — but a hook armed via `/eval` got **wiped by a `history.pushState`
soft-nav** (`typeof window.__cap === 'undefined'` afterward) and `window.dispatchEvent(new Event('focus'))`
captured **zero** calls. That's the tell to abandon hooking and just read `t_token`.

### STEP ZERO-B (legacy XHR-hook path): the header file WILL be 401-stale between runs
Symptom: `deferred_by_advisor_daily.py` prints `retry 1..5 HTTP Error 401` then
`RuntimeError: failed`. This is expected any time the Tekion session has refreshed —
it is NOT a broken script. Re-capture headers BEFORE debugging anything else:
1. `:9223` health/url/dealer check (`/eval` `{"js": "..."}`, key is `js`).
   Note `curl http://127.0.0.1:9223/status` does not exist and will HANG the terminal tool — use
   `/health`, `/url`, `/eval` from `execute_code` + urllib, never curl in a shell.
2. Arm the XHR hook (override open/setRequestHeader/send, stash `{u,h}` for any `/api/` with >3 headers).
3. **Trigger a refetch.** Two paths that work:
   - **`history.pushState` soft-nav to `/ro/opcode/list` + `PopStateEvent`** — worked 2026-08-23,
     caught 5 `/api/` calls in ~8s from an idle Parts page. (Contradicts the 2026-08-20 note that
     soft-nav caught zero — try it FIRST, it's the cheapest.)
   - If soft-nav catches nothing, click a real refetch button (Opcode List → `Reset`).
   Any captured header set works — the auth headers are identical across `/api/` endpoints;
   the script overwrites `dealerId`/`tek-siteId` per store anyway.
   **Token extraction gotcha:** `tekion-api-token` is ~536 chars and the `/eval` endpoint
   truncates long strings — pull it in 4000-char slices (`.slice(i,i+4000)`) and reassemble,
   or `JSON.stringify(h)` will hand you a truncated `"eyJhbG...rQUw"` ellipsis form that silently
   still 401s. Verify `len(token)` matches what `h['tekion-api-token'].length` reported.
4. Merge over the old file, re-run the pull. Whole recovery ≈ 90s.

## CRITICAL: the index lags ~1 day
The deferred-services index rebuilds nightly (~11:45 PM). **Today always returns 0 at all 7 stores**
(verified 2026-08-18: today=0 everywhere, yesterday=SCT 97 / BC 46 / BT 289 / SV 19 / TL 125 / AR 4 / VC 28).
Also **Sundays are legitimately 0** (stores closed) — a 0 day is not a bug.
So "today's" report = run for **yesterday**; any daily cron must be scheduled for the morning AFTER.
Filtering on `createdTime`/`modifiedTime`/`lastDeferredTime` does NOT dodge the lag — same 0.

## Advisor names
`primaryAdvisorId` (UUID) → merge caches in `data/`: `advisor-name-cache.json` (fleet, 67 ids),
plus `bc-/bt-/sct-/tol-advisor-cache.json`. Unknown → resolve via OpenAPI
`GET /openapi/v4.0.0/users/{id}` with `dealer_id=americanmotorscorporation_<id>_0`.
**Gotcha:** `r["data"]` is sometimes a LIST — use `r["data"][0] if isinstance(list)`.
Name at `userNameDetails.completeNames[DISPLAY_NAME]`. Write new ids back to `advisor-name-cache.json`.
Note some ids resolve to non-advisor personas (e.g. BC `8c0d2da8…` = Dale Alexander, INVENTORY_MANAGER)
— they still carry deferred lines as RO primary advisor; keep them but don't assume they're writers.

## Reference run (BC / 1251, Mon 8/17/2026)
46 declined lines · 20 ROs · $23,179.47 · 21 Critical. Michael Reyes #1 ($6,233).

## Reference run (BC / 1251, Sat 8/22/2026)
17 declined lines · 8 ROs · $12,984.56 · 5 Critical. Juan Ramirez #1 (9 lines / 4 ROs / $5,278.70),
Houa Moua $4,635.63 (1 RO), Jacob Debussey $2,690.00, Dimetri Reynoso $380.23.
Fri 8/21 was the trailing-7 peak at $44,347 / 51 lines. Dimetri Reynoso = BC advisor not in the
8/19 roster list below — the BC writer set changes; don't hardcode it.

## Reference run (BC / 1251, Wed 8/19/2026)
25 declined lines · 16 ROs · $21,658.61 · 6 Critical. Juan Ramirez #1 ($6,793.43).
Trailing-7 peak was Fri 8/14 at $54,931.33 — daily volume swings hard, so a low day is
not evidence of a pull failure. Always sanity-check the day against the trend panel.
BC advisor set as of 8/2026: Juan Ramirez, Erik Mercado, Houa Moua, Jacob Debussey,
Michael Reyes, Jeremia Navarro (+ Dale Alexander, non-advisor, see below).

## Non-advisor personas in the ranking
BC `8c0d2da8…` = **Dale Alexander, INVENTORY_MANAGER** — recurs as RO primary advisor with
$0-priced lines. He is NOT a writer. The scripts keep him (he legitimately holds the RO), but
**call it out explicitly when presenting to Joe** and offer to filter non-advisor personas —
an unexplained $0.00 row at the bottom of an advisor ranking reads as a bug.

## Email delivery (via Stacey)
Route report emails through Stacey (email-agent) on the bridge — never Jay's direct SMTP.
Store manager recipients: BC → **Ruben Estrada `Restrada@blackstonegm.com`**, greeting "Ruben,";
SCT → Kevin Stapp `kstapp@sctoyota.com`; TL → Sean Preston `spreston@tol-av.com` (greeting "Sean,");
BT → Tony Garcia `agarcia@blackstonetoyota.com`.
Subject pattern: `<STORE> Deferred Work by Advisor — <Weekday MM/DD/YYYY>`.
Body = summary line (bold $ total / lines / ROs / Critical count) → advisor table with TOTAL row →
note that the PDF has a page per advisor for follow-up calls. Scorecard PNG **inline as a CID
attachment** — `multipart/related` + `image/png` part with `Content-ID: <scorecard>` and
`<img src="cid:scorecard">`. **NEVER a `data:` URI** — Gmail blocks those and the image renders
broken (Joe reported exactly this on the 8/19 draft; the PNG bytes were perfect, the delivery
mechanism was wrong). Spell the whole MIME tree out in the ask to Stacey and state explicitly
"the string data:image must NOT appear in the HTML". Verify afterwards: `'data:image' in html`
is False, `'cid:scorecard' in html` is True, and an `image/png` part has Content-ID set.
Tell: correct CID body is ~3-4KB of HTML; a data-URI body is ~180KB.
PDF + CSV attached, Joe's HTML signature.
Note Stacey strips underscores out of the reply token line (`CIDPNG=y`, `INDRAFTS=y`) — that's
her formatting, not a failed field. Also she labels the CSV `application/csv`, not `text/csv`
— still byte-identical, don't flag it.
DRAFT-ONLY asks: give Stacey a hard stop ("imap.append to Drafts ONLY, no send/SMTP/X-GM-RAW path").
Then verify independently with `jay-gmail-draft-verification` — confirm labels are `\Draft` only,
Sent Mail = 0 hits, attachments byte-identical to source files, and the PNG is a real data-URI not a CID stub.

## Cron (LIVE as of 2026-08-25)
Job `d0bfeeef5851` — **"BC Deferred Work by Advisor — 6AM draft to Ruben"**, `0 6 * * *`,
runs for **yesterday** (index lag), draft-only to Ruben Cc Joe, delivers to the BC/GM Slack
thread. Sundays return 0 → job reports `[SILENT]` and creates no email.
Joe asked for 6 AM (he's up by 4) — not the 7:30 AM originally proposed below.

## Pitfalls
- **"I don't see the draft" usually means it's STALE, not missing.** This report has no cron
  (as of 8/2026) so it only exists for whatever day it was last hand-run. Gmail sorts Drafts by
  creation date, so a days-old draft sits ~13 rows down under the menu-sales drafts and Joe
  reads that as absent. Don't argue from the Gmail UI — prove it with raw IMAP (UID, `\Draft`
  label only, 0 hits in Sent), then **immediately build a fresh one for the latest business day**
  rather than just confirming the old one exists. Offer to trash the superseded draft.
- **Un-cron'd one-off reports go stale silently.** If a report is built as a one-off, say so and
  offer to wire the cron in the same turn. Proposed schedule for this one: daily 7:30 AM,
  previous business day (index lags ~1 day), BC → draft to Ruben Cc Joe, delivered to the
  BC/GM Slack thread `C0BR7FHMF17:1787111034.827789`. Sunday = 0 (store closed), skip or note it.
- **Stale test drafts accumulate.** Each test run leaves a dated draft in `[Gmail]/Drafts`
  (e.g. "BC Deferred Work by Advisor - Monday 08/17/2026" UID 42447 from the 8/18 run).
  After verifying a new draft, list Drafts and offer Joe the cleanup of prior-day copies —
  don't silently trash them.
- `pdfinfo`/`pdftoppm` are NOT installed — QA extra PDF pages by re-rendering the HTML in Playwright
  and screenshotting a single `.page` div, then `vision_analyze`.
- Store brand colors/labels live in the `BRAND` dict of the renderer — add new stores there.
