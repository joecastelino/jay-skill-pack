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

### STEP ZERO-0: TRY THIS FIRST — token from the canonical session file (verified 2026-08-26)
**Cheapest and most reliable 401 fix. Beats STEP ZERO-A because it does not require `:9223` to be
logged in at all.** `login.py` maintains the canonical session file, and its `t_token` is a full
untruncated 536-char string on disk — no `/eval` slicing, no SPA driving, no browser dependency:

```python
import json, shutil
sess = json.load(open("/home/itadmin/caliber-ops/scripts/.tekion-session.json"))
hp = "/tmp/tekion_rec_headers.json"
shutil.copy(hp, hp + ".bak")            # keep a rollback
h = json.load(open(hp))
h["tekion-api-token"] = sess["t_token"] # ONLY this key
json.dump(h, open(hp, "w"), indent=1)
```
Same TRAP as ZERO-A applies: change **only** `tekion-api-token`. Leave `userId`/`original-userid`
= `8cc203af-a87e-4fd7-8090-745a0ffa2339`, `roleId` = `656e21e547e83861236c5e0c`,
`tenantname` = `americanmotorscorporation` untouched; the script sets `dealerId`/`tek-siteId` itself
(the stale file may show a *different* store's dealerId, e.g. 876/SCT — harmless, don't "fix" it).

Sanity-check both tokens by decoding the JWT `exp` before merging — the session file's token is
often FRESHER than the header file's, which is exactly why the pull was 401ing:
```python
import base64, json, time
def exp(t):
    b = t.split(".")[1]; b += "=" * (-len(b) % 4)
    return json.loads(base64.urlsafe_b64decode(b))["exp"] - time.time()   # seconds of headroom
```
Refresh the session file first if needed: `$VPY /home/itadmin/tekion-auth/login.py` (prints
`REUSED` if already alive — ~0.4s, no OTP). `VPY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`.

**When ZERO-A is unavailable (hit 2026-08-26):** `:9223` can be *healthy* (`/health` = ok) yet
fully **logged out** — `/pages` showed a single tab on `https://app.tekioncloud.com/login?redirectTo=...`
and `localStorage.t_token.length` returned **0**, with `t_apmAutnToken` also empty and only
`persist:primary` (71 B, `LoginReducer:{}`) left. There is no token to read, so ZERO-A and the
ZERO-B hook are both dead ends. Do NOT start an OTP re-login for this report — the session file
was valid the whole time (token exp ~29 days out). Total recovery via ZERO-0: ~30s, zero OTP.
Order of attack: **ZERO-0 → ZERO-A → ZERO-B (hook)**.

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
**Working recipe (verified 2026-08-29, resolved `3fd74487-…` → Louie Vallejo Jr in ~1 min):**
```python
import sys; sys.path.insert(0, "/home/itadmin/tekion-api")   # NOT /home/itadmin/tekion-reports
import tekion_client as tc
cfg = tc.load_config()
r = tc.api_get(cfg, f"/openapi/v4.0.0/users/{uid}", "americanmotorscorporation_1251_0", {})
d = r["data"]; d = d[0] if isinstance(d, list) else d
name    = d["userNameDetails"]["completeNames"][0]["value"]        # completeNames is a LIST of
persona = d["userRoleDetails"]["primaryRole"]["persona"]           # {nameType,value} dicts
```
Two traps: `completeNames` is a **list of dicts**, not a dict keyed by DISPLAY_NAME —
`.get("DISPLAY_NAME")` returns None. And persona is at `userRoleDetails.primaryRole.persona`;
there is no top-level `personas`/`roles` key. After writing the cache, **re-run the pull** (not just
the renderer) — the name is baked in at pull time.
Note some ids resolve to non-advisor personas (e.g. BC `8c0d2da8…` = Dale Alexander, INVENTORY_MANAGER)
— they still carry deferred lines as RO primary advisor; keep them but don't assume they're writers.

## Reference run (BC / 1251, Mon 8/31/2026) — RECORD DAY
**90 declined lines · 45 ROs · $101,725.62 · 27 Critical** — ~2.8x the prior trailing-7 peak
(Fri 8/28 $36,868.51) and the largest BC deferred day observed. Dimetri Reynoso #1 $26,059.10
(10 lines / 4 ROs, incl. RO 99614 at $11,219.79 + $6,583.95), Juan Ramirez $21,535.75,
Michael Reyes $14,605.62 (RO 81379 single line $13,426.49 — biggest line of the day),
Humberto Dominguez $10,336.98, Dale Alexander $10,241.69 (21 lines / **18 of the 27 Criticals**),
Jeremia Navarro $6,725.00, Houa Moua $3,733.98, Louie Vallejo Jr $3,218.13,
Jacob Debussey $2,845.03, Erik Mercado $2,249.14, **Phillip Stafford $175.20 (NEW id
`16f190a9-55bc-4833-b1b5-162cff16fbe3` = SERVICE_MANAGER)**. Draft UID 42906. PDF = 12 pages.
Notes: (1) STEP ZERO-0 fixed the 401 in ~30s — header token had 28 days of headroom yet still
401'd, so **headroom is NOT a validity test**; a token can be unexpired and still rejected.
Just merge the session-file token whenever the pull 401s, don't reason about `exp`.
(2) BC now has THREE non-writer personas in the ranking (Dale Alexander INVENTORY_MANAGER,
Louie Vallejo Jr SERVICE_MANAGER, Phillip Stafford SERVICE_MANAGER) — call all three out.
(3) Top-3 line amounts all carry severity `CAUTION`, not CRITICAL — the Critical count is
concentrated in Dale Alexander's low-dollar lines, so don't equate Critical with big dollars.

## Reference run (BC / 1251, Tue 9/1/2026)
32 declined lines · 10 ROs · $21,814.79 · 24 Critical. Dale Alexander #1 $15,354.43 (25 lines / 6 ROs /
**23 of the 24 Criticals**) — the INVENTORY_MANAGER persona again dominating both lines and Criticals.
Then Jacob Debussey $2,317.99, Humberto Dominguez $2,317.84, Juan Ramirez $914.21, Erik Mercado $910.32.
Only 5 advisors, 10 ROs — lowest RO count in the trailing 7 but a normal day (prior day Mon 8/31 was the
$101,725.62 record). Draft UID **43022**. PDF = 6 pages. HTML 4,361 B after Stacey appends the signature.
401 again on first pull; **STEP ZERO-0 fixed it in ~30s** — header token had 28.9 days headroom and still
401'd, session-file token had 29.6 days. Reconfirms: headroom is NOT a validity test, just merge and re-run.
Stacey's DRAFT_UID=43022 was for once the REAL UID (seq no. was 116) — still resolve it yourself.

## Reference run (BC / 1251, Fri 8/28/2026)
31 declined lines · 16 ROs · $36,868.51 · 13 Critical — **trailing-7 peak**, above Mon 8/24's $35,836.63.
Houa Moua #1 $9,380.40, Juan Ramirez $8,169.24, Michael Reyes $4,829.20, Jeremia Navarro $4,435.72,
Humberto Dominguez $4,095.70, Dale Alexander $2,793.11, Jacob Debussey $1,932.49,
Dimetri Reynoso $843.35, **Louie Vallejo Jr $389.30 (NEW id `3fd74487-…`)**. Draft UID 42817. PDF = 10 pages.
New unresolved id resolution worked exactly as documented (see Advisor names) — note the OpenAPI
persona lives at `userRoleDetails.primaryRole.persona`, NOT a top-level `personas` key. Louie Vallejo Jr
= **SERVICE_MANAGER** (secondary role SERVICE_ADVISOR), i.e. a SECOND non-writer persona alongside
Dale Alexander now appearing in the BC ranking — call both out when presenting.

## Reference run (BC / 1251, Tue 8/25/2026)
36 declined lines · 11 ROs · $20,443.83 · **29 Critical (81% — unusually high vs 9/43 on Mon 8/24)**.
Dale Alexander #1 with 75% of the dollars ($15,368.31 / 24 lines / 4 ROs) — the non-advisor
INVENTORY_MANAGER persona topping the ranking, led by RO 101427 (2007 Nissan Frontier, rear diff
seal + axle shaft, Critical, ~$6K). Then Jacob Debussey $3,614.22, Michael Reyes $1,322.09,
Erik Mercado $139.21. Only 4 advisors and 11 ROs — lowest weekday RO count in the trailing 7,
but a legitimate day, not a pull shortfall. Draft UID 42675. PDF = 5 pages (summary + 4 advisor).

## Reference run (BC / 1251, Mon 8/24/2026)
43 declined lines · 22 ROs · $35,836.63 · 9 Critical. Jacob Debussey #1 ($13,731.77 / 2 lines / 2 ROs)
— driven by a single RO 101776 (2016 Corvette, differential carrier assembly, $12,234.84). Then
Erik Mercado $5,226.01, Dimetri Reynoso $5,086.15, Houa Moua $5,076.02, Dale Alexander $3,446.19
(14 lines / 5 ROs — highest line count, non-advisor persona), Jeremia Navarro $1,829.58,
Michael Reyes $1,191.17, Humberto Dominguez $249.74 (new name, not in the 8/19 roster).
Draft UID 42652. Note one big-ticket line can dominate the ranking — lead with it when presenting.

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
- **Stacey's reported `DRAFT_UID` is often a SEQUENCE NUMBER, not the IMAP UID** (2026-08-26):
  she reported `DRAFT_UID=80` for a draft whose real UID was **42675**. The raw fetch response
  makes it obvious: `b'80 (X-GM-LABELS () UID 42675 FLAGS (\Draft))'` — the leading `80` is the
  sequence number, `UID 42675` is the truth. Never quote her number to Joe; always resolve the
  real UID yourself via `X-GM-RAW` subject search and report that. Her other self-report tokens
  (CID_PNG, HTML_BYTES, IN_DRAFTS) have been accurate. Also expect her to mangle underscores in
  token names (`DATAURIIN_HTML`) — formatting only, not a failed field.
- **Report `Critical` from the JSON, not the renderer.** Count `severity == "CRITICAL"` across
  every advisor's `detail` array (keys are `advisor`/`lines`/`ros`/`amt`/`detail`, and
  `advisorId` — NOT `name`/`amount`/`total`; guessing key names yields a row of `None`s).
  Cross-check against the PDF page-1 "FLAGGED CRITICAL" tile — they must match (29 = 29).
- **A draft Joe "can't find" in Gmail is usually STALE, not missing.** (Pre-cron history; since
  2026-08-25 job `d0bfeeef5851` produces one every 6 AM, so a missing draft now means the CRON
  failed — check its log/delivery before hand-running.) Gmail sorts Drafts by
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
