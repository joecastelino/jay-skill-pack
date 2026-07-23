---
name: tekion-vi-api-migration
description: Migrate the Vehicle Inventory ("The Goods") browser scraper to the Tekion OpenAPI (vehicle-inventory:search) producing per-store JSON that byte-matches the legacy schema. Covers field mapping, the SOLD-pending rule, Pacific-tz dates, rate-limit discipline, and the Don coordination/cutover handoff.
triggers:
  - migrate vi scraper to api
  - the goods api migration
  - vehicle inventory openapi
  - replace browser vi scraper
version: 1.3.0
tags: [tekion, openapi, vehicle-inventory, the-goods, migration, don]
---

# Tekion VI → OpenAPI Migration ("The Goods")

Replace the fragile 2 AM browser VI scraper with a Tekion OpenAPI pull. **Don
(don-ready) OWNS The Goods dashboard** — coordinate with him via the bridge, match
his output schema exactly, and get his sign-off on a TEST file before any cutover.

Deliverable script: `/home/itadmin/tekion-scraper/scripts/vi-api-pull.py`
(this already exists post-2026-06-22 build — patch it, don't rebuild).

## Ground truth first: read the legacy output, don't assume
The Goods reads per-store files at `~/the-goods/data/<code>.json` (code ∈
ar,bc,bt,st,sv,tl,vc), a JSON **array** of objects with EXACTLY these 18 keys,
all **string** values:
```
stock, vin, year, make, model, trim, mileage, price, cost, ro, age,
received, status, subType, ymm, url, roClosed
```
- Files are `<code>.json`, NOT `*-slim.json` (the cron/skill naming was stale).
- **Recon-stage data is SEPARATE** (`recon-maps.json` / `*-recon-map.json`, a
  different kanban scrape). DO NOT touch it during a VI migration unless Don says so.
- Read `~/the-goods/data/sv.json` (smallest, ~80 recs) as the formatting contract:
  comma-thousands no `$` no decimals, date `"Feb 15 2021"`, status title-case
  (`Stocked In`), `age` = day-count string, en-dash `\u2013` and `-` both appear.

## The API
`POST /openapi/v4.0.0/vehicle-inventory:search`, headers via tekion_client
(`get_token`, `cfg["dealers"][code]`, `app_id`). Body `{"pageSize":50}` (max 50).
**Pagination:** next page via `{"paginationToken": meta["nextFetchKey"]}` — the
token field is `nextFetchKey` (NOT nextPageToken); putting `fetchKey` in the body
re-serves page 1. Response: `out["data"]["results"]` (or bare list — handle both).

### Field mapping (verified live, SV)
- `stock` = `stockID`; `vin` = `vin`; `year/make/model` = `vehicleSpecification.{year,make,model}`
- `trim` = `vehicleSpecification.trimDetails.trimCode`
- `mileage` = `odometerReading.value` (comma-formatted)
- `price` = `pricingDetails.price[type==RETAIL_PRICE].amount` (CENTS/100, round, commas, no `$`; `"-"` if 0)
- `cost` = sub-fetch `/vehicle-inventory/{id}/pricing-details/cost`: use `GL_BALANCE` if non-zero else `INVOICE_PRICE` (cents/100). `"-"` if unavailable.
- `ro` = count of NON-CLOSED ROs from sub-fetch `/vehicle-inventory/{id}/repair-orders`; en-dash `\u2013` if none open. `roClosed` = count of CLOSED ROs (string).
- `received` = `receivedTime` (fallback `stockedInTime`) → `"Feb 15 2021"`
- `age` = whole days from received to now, string
- `ymm` = `"{year} {make} {model}"`; `subType` = `"Used Cars"`; `url` = `https://app.tekioncloud.com/vi/vehicle/` + `id`
- Keep only `stockType == "USED"` (the legacy "Used Cars" board).

### ⭐ Dates MUST be Pacific (America/Los_Angeles), not UTC
The legacy scraper read the UI date, which is dealer-local. Using `time.gmtime`
(UTC) shifts ~5% of `received` values by one day across the midnight-UTC boundary.
Use `zoneinfo.ZoneInfo("America/Los_Angeles")` for BOTH `received` formatting and
`age` (compute as Pacific calendar-day diff). This eliminated all 4 `received`
mismatches in the SV test and is strictly *more* correct than the old scraper.

### ⭐ The SOLD-pending rule — discovered through trial and error
A unit can be marked `SOLD` in Tekion but still be physically on the lot (sold,
not yet delivered) — Don WANTS these on his board (deal can fall through, takes up
space). But there's also no delivery flag in the API. Hard-won findings:
1. **`STOCKED_IN + ON_HOLD` only is too narrow** — it drops sold-undelivered units
   (e.g. VX19530 dropped from the SV test; Don flagged it as a 404-day rot unit).
2. **Filtering SOLD by `receivedTime`/age is WRONG** — age = days on lot, not days
   since sold. A unit can sit 405 days then sell today; an age<45 filter misses it.
3. **The correct signal is `modifiedTime`** = when the record flipped to SOLD.
   VX19530's modifiedTime = today (sold today); genuinely-delivered SOLD ghosts have
   modifiedTime ~733 days ago. So: **include SOLD units only if
   `modifiedTime` within `SOLD_AGE_MAX` days.** Display status `"Sold Pending"`
   (Don badges it), and add a `soldSince` key (= `_fmt_date(modifiedTime)`) ONLY on
   SOLD rows so non-sold records keep the exact 18-key schema.
   - Add `soldSince` in `transform` guarded by `if status_raw == "SOLD"`.
4. **`SOLD_AGE_MAX = 14`, NOT 45 (Don's final rule call 2026-06-22).** A
   sold-pending unit's only job on his board is recon urgency (get it cleaned/
   photographed/frontline before the deal unwinds). Past 2 weeks it's a stuck/dead
   finance deal — not his board's problem — and a wider window pads the board with
   "zombie" units (SV at 45d = 110 board vs 81 at 14d ≈ legacy 80 baseline). When
   asked, give Don the cumulative count by window (7/14/21/30/45) so he picks; he
   chose 14. VX19530-type same-day sales survive any window.

### ⭐⭐ THE BIGGEST TRAP: never put SOLD in the SAME status:IN filter (BC/BT/TL=0 bug)
This bug is INVISIBLE on a single-store (SV) test and only surfaced when validating
ALL 7 stores — BC/BT/TL came back with **0 USED vehicles**, ST showed 98 vs 528.
Root cause: a `status IN [STOCKED_IN, ON_HOLD, SOLD]` filter makes the API return
the dealer's **ENTIRE historical sales archive** (Blackstone Chevy = **48,044
records**). Pagination wades through tens of thousands of ancient delivered/NEW
cars and never reaches the live stocked-in units before the page cap → empty board.

**Fix = TWO SEPARATE server-side queries, merged + deduped by id:**
1. `[{"field":"status","operator":"IN","values":["STOCKED_IN","ON_HOLD"]}]` — the
   live on-lot inventory (BC ≈ 490 records, small + fast).
2. `[{"field":"status","operator":"IN","values":["SOLD"]},
      {"field":"modifiedTime","operator":"GTE","values":[str(now_ms - SOLD_AGE_MAX*86_400_000)]}]`
   — SOLD **pre-filtered SERVER-SIDE by modifiedTime** so you pull ~350 recent-sold,
   NOT 48k. The `modifiedTime GTE` filter IS respected by the search endpoint
   (verified: returned ages 0–11 days). Then keep `stockType=="USED"` on the merge.

Refactor: a generic `_page_search(cfg, tok, dealer_id, filters)` helper that
paginates any filter set; `fetch_used_inventory` calls it twice (live + sold-window)
and merges `{v["id"]: v}`. The old `SEARCH_STATUSES` constant becomes unused —
leave it or delete it, but do NOT use it as a single combined filter.

**LESSON: always validate ALL 7 stores before cutover, never just SV.** High-volume
stores (BC 48k, ST 528 used) expose pagination/archive bugs that the small SV store
(80 units) cannot. A clean single-store test is necessary but NOT sufficient.

## ⚠️⚠️ Rate limits: TWO separate buckets — the #1 trap (cost both dev AND prod)
### Why every vehicle costs 2 extra calls (structural, unavoidable)
In the search result, `pricingDetails.costs` and `repairOrders` are **LINKS, not
inline data** (`{"link": "/vehicle-inventory/{id}/repair-orders"}`). Verified live
2026-06-23. There is NO inline cost/RO and NO bulk endpoint — so `cost`, `ro`,
`roClosed` REQUIRE one GET each per vehicle. A full store = search-pages +
~2 sub-fetches × N vehicles (≈190 calls for an 80-unit store, ≈830 for BC's 414).
Do NOT waste time hunting for a way to avoid the sub-fetches; it doesn't exist.

### Two buckets, two behaviors — know which 429 you hit (read the error body)
- **`DEALER_RATELIMIT`** — per-dealer 1,500 calls / 15 min. Recovers fast; a single
  store rarely trips it. Short backoff (25/50/75/100s) is fine.
- **`OVERALL_RATELIMIT`** — **app-wide across ALL dealers** (shared app_id quota).
  This is what kills an all-7-store run: AR(183)+BC(414)+BT(358) ≈ 955 vehicles ×
  ~3 calls ≈ 2,800 calls in minutes → `429 OVERALL_RATELIMIT` on store 4 (ST).
  Short backoff CANNOT save you — the whole shared 15-min window must drain.
  `err_body` literally says `"Limit exhausted for type : OVERALL_RATELIMIT"`.
- **`OVERALL_QUOTA`** — a THIRD, worse bucket (seen 2026-07-07→07-10): app-wide
  **long-horizon quota** (monthly/rolling), NOT a 15-min window. When exhausted,
  EVERY OpenAPI call 429s (`"Limit exhausted for type : OVERALL_QUOTA"`) for
  **days** — no backoff or cooldown helps. Correct response: stop all pulls,
  set up a cheap restoration probe, and re-run everything once it clears.
  Probe: `/home/itadmin/tekion-reports/quota_ping_once.py` (venv python3.11) —
  prints `STATUS=200` + exits 0 when restored, exits 1 while blocked. After
  restoration, one full 7-store `cron-vi-api.sh` run completes clean (~30 min)
  and the 1:30 AM DealerDetail `sync:all` backfills RO data automatically.
  Verified live: the 2026-07-07 OVERALL_QUOTA outage cleared ~2026-07-11 03:19
  (≈4 days); the probe→re-run→backfill workflow executed clean on first try.
  Remember to REMOVE the temporary quota-watch cron job after restoration —
  and remove it IMMEDIATELY, not \"later\": if the watch job is RECURRING (hourly),
  every subsequent fire after restoration re-runs the full 7-store pull again.
  Verified 2026-07-11: watch fired at 12:15/1:17/2:47/3:17 PM = 4 redundant pulls
  ≈ 11k calls burned on day 1 of restored quota. It fired AGAIN at 7:24 PM (5th
  redundant pull, right after a clean 6:16 PM run) and AGAIN at 01:24 AM 07-12
  (6th redundant pull, 1 hour after a clean 00:23 AM run — the agent tailed the
  log only AFTER starting the pull, too late), AGAIN at 07:49 AM 07-12 (7th
  redundant pull, when the log already showed a clean 06:20 AM run — same
  tail-after-start mistake),  AND AGAIN at 08:49 AM 07-12 (8th redundant pull,
  one hour after the clean 07:48 AM run — the agent probed quota then launched
  the pull immediately WITHOUT ever tailing the log first), AND AGAIN at 10:18 AM
  07-12 (9th redundant pull, one hour after the clean 09:17 AM run — same
  probe-then-launch-immediately mistake; the watch prompt's explicit \"re-run the
  VI pull\" instruction does NOT override the check-the-log-first rule), AND AGAIN at 1:16 PM 07-12 (10th redundant pull,
  ~1 hour after a clean 12:14 PM run — agent probed quota → launched pull →
  only THEN tailed the log, which plainly showed the 12:14 ✓ complete; ~2,800
  more calls burned. AND AGAIN at 3:13 PM 07-12 (11th redundant pull, 90 min
  after a clean 13:44 run — identical probe→launch→tail-too-late sequence;
  the agent never loaded this skill before acting. If a cron prompt mentions
  quota_ping_once.py or cron-vi-api.sh, LOAD THIS SKILL FIRST. Also: a prompt
  saying \"do NOT CREATE cron jobs\" does NOT forbid REMOVING the watch job —
  remove it yourself, don't just report that someone should). The correct order is a single 3-command sequence BEFORE
  any pull: probe → `tail vi-api.log` → IF current-day block shows 7 `wrote` +
  `✓ complete`, report "already ran clean, skipping" and STOP) because
  the job was still installed— the watch prompt itself says "re-run the VI pull", so every fire
  after restoration burns ~2,800 calls unless the AGENT checks the log first. The watch prompt should ideally
  make the pull conditional on the log NOT already showing a clean same-day run.
  ⭐ **Before re-running the pull after restoration, tail `logs/vi-api.log` first**
  — the regular 2 AM (or morning) cron may have ALREADY completed a clean run once
  quota cleared (it did on 2026-07-11: 9:14 AM run succeeded before the 10:16 watch
  job fired). If the current-day block shows 7 `wrote` lines + `✓ complete`, skip
  the re-run entirely — a redundant 7-store pull burns ~2,800 calls of the freshly
  restored quota for nothing. Ordering matters: `tail log` → *decide* → maybe pull.\n  ⭐ **If YOU are the agent running the watch job and quota is restored, REMOVE the\n  watch job YOURSELF in the same session** via `cronjob(action='list')` →\n  `cronjob(action='remove', job_id=...)` (unless the prompt forbids cron changes) —\n  merely \"noting that Joe/Jay should remove it\" has let it fire 7+ redundant times.

### The fix shipped 2026-06-23 (in vi-api-pull.py — keep it)
1. **Bucket-aware backoff** in `_request`: detect `"OVERALL_RATELIMIT" in err_body`;
   if OVERALL sleep `180*(attempt+1)` (180/360/540/720s, max_retries=6) so one
   nightly run rides through a drained window; else DEALER → 25/50/75/100s.
2. **`INTER_STORE_COOLDOWN = 90`s** — `main()` sleeps 90s between stores so the
   shared OVERALL bucket refills. The nightly cron has all night; PACING beats
   blasting + 429 storms.
3. **Per-store error isolation** — wrap `pull_store` per store in try/except, append
   to a `failed = []` list, print `!! stores that FAILED and need a re-run: [...]`.
   One store's 429 must NOT abort the other 6 (the old run lost ST/SV/TL/VC).

### Dev discipline (still applies)
- Do NOT iterate filter logic by re-running the full store live. Pull raw search
  results ONCE, save to JSON, test transform/filter logic against the cache offline.
- A 429 can leave a partial/corrupt output file — DELETE it and re-run clean.
- When a run dies mid-way, RE-RUN ONLY THE STORES THAT DIDN'T COMPLETE (check file
  mtimes — stale files from the previous buggy run look done but aren't). Don't
  re-blast all 7 into an already-hot bucket.
- Even inspection/probe calls count against OVERALL — after a crash, wait ~5 min
  for the bucket to drain BEFORE the re-run, or you just 429 again immediately.

## Validation (do this, then hand to Don)
1. Run for ONE store to a TEST suffix so you never clobber prod:
   `python3 vi-api-pull.py --store sv --suffix apitest` → writes `sv-apitest.json`.
2. Diff vs current `sv.json` by `stock`/`vin`. Expect: **all 17 stable fields exact
   match**; only `age` differs (it's a live recompute — correct, off-by-1 same-day,
   and can be >1 when the old browser value was stale, which is an upgrade not a bug).
3. Confirm the SOLD-pending units are present (e.g. VX19530), tagged `Sold Pending`,
   carry `soldSince`, and that NO ancient delivered ghosts (modifiedTime 700+d) leak in.
4. **Send the test file to Don via the bridge** for an independent diff + sign-off:
   `timeout 160 ~/bin/ask-agent don-ready "<self-contained: paths, your diff summary,
   ask APPROVED or list off fields>"`. He WILL catch dropped units (he caught VX19530)
   — treat his catches as blocking. Loop him before cutover on any filter decision.

## Cutover (only after Don's APPROVED on the full set) — DONE 2026-06-23
1. Run all 7 stores to real `<code>.json` (no suffix). `vi-api-pull.py` with no
   `--suffix` writes prod files directly — that IS the cutover data.
2. Write a NEW cron wrapper `cron-vi-api.sh` (don't reuse the browser one):
   - It calls `python3 vi-api-pull.py` (no suffix) → logs to `logs/vi-api.log`.
   - ⭐ **It does NOT need the `/tmp/caliber-pipeline.lock`.** The browser scraper
     held that lock because it shared the Tekion **browser login/OTP** with
     caliber-ops (concurrent logins invalidate each other's session). The API pull
     uses independent **OpenAPI tokens** — zero session collision — so drop the
     caliber lock entirely. Keep only its own `/tmp/tekion-vi.lock` (prevent two VI
     pulls overlapping → rate-limit safety). This is a real simplification, not laziness.
3. Swap the crontab line (keep 2 AM timing) from `cron-vi-scraper.sh` →
   `cron-vi-api.sh`. **SEE THE CRONTAB-WIPE PITFALL BELOW — do NOT use sed pipe.**
4. Verify plumbing without a full pull: `python3 -c "import ast; ast.parse(...)"`,
   `bash -n cron-vi-api.sh`, `timeout 15 python3 vi-api-pull.py --help` (must rc=0
   fast). Do NOT smoke-test with a real `--store` run into a hot bucket.
5. Leave recon maps on their own scrape.
6. Retire (don't delete) `cron-vi-scraper.sh` — leave the legacy reference in the
   crontab comment in case of rollback.

### ⚠️⚠️ CRONTAB-WIPE PITFALL — this nearly destroyed all 8 cron jobs 2026-06-23
**NEVER** edit the crontab with `crontab -l | sed '...' | crontab -`. The new cron
line contains a `#` (the `# legacy=...` comment) AND the URL/paths, which collide
with sed's `s###` delimiter and ALSO break `s#...#` alternates. When sed errors, it
prints to stderr and pipes **EMPTY** stdout into `crontab -` → the entire crontab is
**silently wiped** (no error from crontab; `crontab -l` then returns nothing). I lost
all 8 jobs and had to recover.

**Safe procedure (use this every time):**
```bash
# 1. ALWAYS back up first
crontab -l > /tmp/crontab.bak.$(date +%s)
# 2. Edit via python: read backup -> string-replace -> write temp -> install temp file
python3 - <<'PY'
lines = open("/tmp/crontab.bak.<ts>").read().splitlines()   # use the GOOD backup
new = "0 2 * * * /home/itadmin/tekion-scraper/scripts/cron-vi-api.sh >> .../vi-api.log 2>&1 # ..."
out, hits = [], 0
for ln in lines:
    if "cron-vi-scraper.sh" in ln:          # match on UNIQUE substring, not whole line
        out.append(new); hits += 1
    else:
        out.append(ln)
assert hits == 1, f"expected 1 match, got {hits}"
open("/tmp/ct_final.txt","w").write("\n".join(out)+"\n")
PY
crontab /tmp/ct_final.txt     # install from a FILE, never from a pipe
crontab -l                    # VERIFY all jobs still present
```
- Match on a **unique substring** (`cron-vi-scraper.sh`), NOT the literal full line —
  whitespace around `2>&1` differs from what you think and an exact-string `assert`
  will fail (it did, twice).
- If `crontab -l` ever returns empty after an edit, you wiped it — recover from the
  most recent NON-empty `/tmp/crontab.bak.*` (check sizes; the post-wipe backup is 0 bytes).
- The execute_code sandbox runs as a different user context — `crontab -l` there may
  not see the real crontab. Do crontab edits in the **terminal**, not execute_code.

## Pitfalls recap
- Jay's `~` != `/home/itadmin` — use absolute paths for shared assets (the-goods, tekion-api).
- `~/tekion-scraper` has no git repo — back up the script (`.bak`) instead of committing there.
- Don't trust a `*-apitest.json` that has a wildly off record count — it's a
  429-corrupted, stale-filter, or archive-trap artifact; delete and re-run clean.
  Sanity baselines (USED board, clean run 2026-07-11): AR 173, BC 419, BT 393,
  ST 663, SV 98, TL 307, VC 103. Counts drift over weeks — order-of-magnitude is
  what matters; BC/BT/TL must be NON-ZERO (a 0 means the SOLD-archive pagination
  trap above — you combined the filters).
- `SOLD_AGE_MAX = 14` (Don's call). modifiedTime filter value is **epoch ms as a
  STRING**: `str(int(now_ms - SOLD_AGE_MAX*86_400_000))`.
- **`logs/vi-api.log` is CUMULATIVE** — `grep -i failed vi-api.log` returns stale
  `FAILED`/`!! stores that FAILED` lines from PRIOR runs and makes a clean run look
  broken. Always scope to the current run first:
  `awk '/Cron Start: <timestamp-of-this-run>/,0' logs/vi-api.log | grep -iE "FAILED|wrote|complete"`.
  A clean run shows 7 `wrote N records` lines + `✓ VI API pull complete` and NO
  FAILED lines *within that block*.
- Full 7-store run takes ~30 min (90s inter-store cooldown × 7 + sub-fetches).
  Hermes `process wait` clamps to 180s per call — poll the log tail between waits
  instead of trusting a single wait to block until completion.
