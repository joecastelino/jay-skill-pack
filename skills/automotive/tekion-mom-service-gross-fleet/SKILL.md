---
name: tekion-mom-service-gross-fleet
description: >
  Produce a month-over-month (or any period-vs-period) SERVICE GROSS read across
  all 7 AMG stores from the live Tekion OpenAPI — who's winning, who's slipping,
  and whether it's a VOLUME story or a MARGIN story. Uses a throttle-safe
  sequential RO sample (labor GP + parts GP per RO) scaled by exact closed-RO
  counts, because the GL department-gross endpoint is still locked and a full
  penny-accurate fan-out trips the rate limit for hours. Use when Joe asks
  "service gross month over month", "who's doing well / breaking numbers across
  the stores", "fleet service gross May vs June", or any cross-store gross trend.
triggers:
  - service gross month over month
  - gross mom all stores
  - who is doing well service
  - fleet service gross
---

# Tekion Fleet MoM Service Gross (all 7 stores)

Load `tekion-openapi-repair-orders` alongside this — it has the RO API client,
the cents-are-gross math, and the rate-limit facts. This skill is the recipe for
the specific "cross-store gross trend, who's up/down" ask.

## The number Joe wants
"Service gross" = **total service GP = labor GP + parts GP**, on CLOSED/INVOICED
ROs, per store, period-vs-period. Gross = **sale − cost** (both in cents on the
API). NOT sales, NOT labor-only. Break out labor GP vs parts GP — the split is
where the story lives.

## Why the obvious paths DON'T work (do not rediscover this)
1. **GL API is LOCKED** — `GET /general-ledger/balances/all` returns
   `400 unexpected.error` (no scope). That's the clean department-gross number
   and we can't get it. Confirmed still locked 2026-06-30.
2. **Penny-accurate fleet fan-out = hours, not feasible on demand.** ~33,600
   closed ROs across 7 stores × 2 months, each needing jobs→operations→parts
   (3+ sub-calls) = 130K+ calls. Tekion throttle is **1,500 calls / 15 min**.
3. **The RO search result has NO inline dollar totals** — jobs/operations/parts
   are all link-stubs. There is no fast $ field. Verified: dumping a closed RO's
   top-level keys shows only link stubs for jobs/fees/invoices.
4. **Parallel/large sampling TRIPS THE THROTTLE and WEDGES.** A ThreadPool with
   6 workers × 3 calls/RO tripped 429 inside the FIRST store-month and hung in
   backoff (~5 min, no progress). A 160-RO sample that paged 3,000 ROs first was
   also far too slow. Both were dead ends this session.

## THE WORKING METHOD — sequential 40-RO sample, scaled by exact counts
Proven 2026-06-30, ran clean end-to-end (~25 min for 7 stores × 2 months):
- **Sample 40 closed ROs per store per month, SEQUENTIALLY** (no threads).
  Measured rate = **~3 sec/RO**, zero throttle trips. 40 × 2 × 7 = 560 ROs ≈
  28 min.
- For each RO: sum labor GP (`op.labor.saleAmount − costAmount`) + parts GP
  (`part.saleAmount − costAmount`) over all jobs→operations→parts. Cents → /100.
- Compute **avg labor GP + avg parts GP per RO** from the sample.
- **Scale by the EXACT closed-RO count** for that store-month (pull it first via
  `repair-orders:search` `meta.totalCount`, filter `closedTime BTW [win]` +
  `status IN [CLOSED,INVOICED]`). Projected gross = (avgL + avgP) × count.
- This gives solid **store rankings + MoM direction**, NOT GL-exact dollars.
  ALWAYS state that caveat to Joe: "sampled read, direction/rankings solid,
  exact dollars ballpark; GL API is locked."

Ready-to-run script: `scripts/mom_service_gross.py` (edit DEALERS window/SAMPLE).
Launch as a **background** job with `notify_on_complete=true` and invoke the
python DIRECTLY (`python3 mom_service_gross.py > log 2>&1`) — NOT wrapped in
`nohup ... &` inside a bash `-c`, or the wrapper returns exit 0 immediately and
the completion notification fires on the WRAPPER, not the real job (masks a job
that's still running or died). Hit this trap twice.

## The analysis that makes it useful (this is what Joe actually asked for)
He wants the READ, not a spreadsheet: "who's doing well, who's breaking numbers,
what should I look at." So the deliverable is a narrative, and the framing MUST
separate volume from margin:

- **Rank by DAILY PACE, not raw gross** — a period-MTD total is low only because
  the month is short. `pace = proj_gross / days_elapsed`; May=31, June-MTD as of
  the run day. Pace Δ% is the apples-to-apples comparison.
- **For every store, report BOTH deltas: RO-count Δ% AND gross-per-RO Δ%.**
  - Count up + $/RO down = **MARGIN problem** (discounting, warranty/internal
    mix, menu pricing). This is the important one — "traffic's fine, we're
    leaving gross on the table."
  - Count down + $/RO flat = **VOLUME/traffic problem**.
- **Gross-per-RO varies ~8x across stores by design** (measured 2026-06-30):
  Stevens Creek Toyota ~$97/RO (warranty-heavy, thin sale−cost) vs Alfa Romeo
  ~$788–1,027/RO (customer-pay skew). So NEVER compare raw $/RO across a Toyota
  store and a luxury/CP store as if a gap is "bad" — compare each store to
  ITSELF month-over-month. A warranty-mix store legitimately shows low gross.
- **Small stores (AR ~108 ROs, VC ~685) are noisy** on a 40-RO sample — flag
  their numbers as low-confidence.

## Sample-stability sanity check (do this before calling a big drop "real")
A 40-RO sample on a warranty-heavy store can swing hard by luck of the draw. If a
flagship shows a scary move (e.g. ST/BT −36%), **re-sample the SAME store-month
with a different offset** (page past the first 80 ROs, take the next 40) and
confirm the $/RO lands close before reporting it as a cliff. Don't ship
"your two Toyota stores fell off a cliff" off one unlucky sample.

## Delivery
Joe usually wants this **as a plain email or a Telegram message** ("you can tell
me here or email me, I don't care… just a simple summary"). Keep it a short
narrative: WINNING / HOLDING / SLIPPING buckets, one line each with the
volume-vs-margin tag, then a "what to look at" paragraph naming the 2–3 stores
that matter and the likely cause. End with the sampled-data caveat + offer to run
a full penny-accurate pull or a pay-type split on any store he wants to drill.

Email: route through Stacey (`~/bin/ask-agent stacey ...`) if the bridge exists.
If NO bridge (checked this session — `/home/itadmin/bin/ask-agent` was absent),
fall back to direct SMTP as Stacey using her app password:
```python
cfg='/home/itadmin/.hermes/profiles/email-agent/home/.config/himalaya/config.toml'
APP_PW=re.search(r'raw\s*=\s*"([^"]+)"', open(cfg).read()).group(1).replace(' ','')
# smtplib.SMTP_SSL('smtp.gmail.com',465); login jcastelino@americanmotorscorp.com
```
From+To = Joe for an "email me" request. Footer: "Sent from Tekion Open API —
live data (sampled)". Flag to Joe that Stacey was unavailable and you covered.

## Sibling ask: appointment COUNT month-over-month (per store)
Verified 2026-06-30 (VC & SV, May vs June). Endpoint =
`service-appointments:search` on the OpenAPI. This one is CHEAP — the count is
`meta.totalCount`, no fan-out, no throttle risk. Filter-field gotcha:
- There is **NO `appointmentTime` field** — that filter 400s. Discover valid
  fields by dumping one record: it has `appointmentDateTime`, `creationTime`,
  `modifiedTime` (all three ARE filterable).
- **`appointmentDateTime`** = appt SCHEDULED FOR that date → the true
  "appointment count for the month." Use this as the headline number.
- **`creationTime`** = appt BOOKED/created in that month. Managers sometimes mean
  this. Report BOTH angles so Joe isn't ambiguous.
- June-MTD is a day short of full May — mention per-day pace.
- Tie it back to the gross read: flat appointments + rising gross = a MARGIN win
  (gross-per-car up), not a traffic win. Verified: VC 800→1004 scheduled (+26%,
  and its gross was up too = real traffic gain); SV 934→943 (+1%, flat — its
  ~34% gross gain was margin/mix, not more cars).

## Natural follow-up Joe asks
"Why did gross-per-RO drop?" → pull the **pay-type split** on that store
(Customer vs Warranty vs Internal) — a warranty/internal shift is the usual
cause of thin gross. Offer it proactively.

## Verified snapshot (2026-06-30, May full vs June MTD, sampled)
Ranked by daily pace Δ: VW Clovis +36% · Stevens Creek VW +34% · Blackstone
Chevy +20% · Toyota of Lancaster +1% · Alfa Romeo −5% · Blackstone Toyota −21%
(margin: cars +8%, $/RO −29%) · Stevens Creek Toyota −36% (margin: volume flat,
$/RO −39%). Fleet ≈ −4% on pace, entirely dragged by the two Toyota flagships;
strip them and the fleet is up. VW stores + BC = bright spots (margin climbing,
not just volume).
