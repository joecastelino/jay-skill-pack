---
name: amg-wip-monthly-column-fill
description: Fill a month column of Joe's AMG WIP workbook (the monthly fixed-ops tracker, rows=metrics cols=months, one tab per store) with Tekion data — hours sold by pay type, vehicle attendance, ToyotaCare hours, workshop hours, WIP $, ELRs. Includes the quota-free dealer-detail DB method for operation-level hours. Use when Joe says he needs to "finish" or "work on" the AMG WIP sheet for a month.
---

# AMG WIP Monthly Column Fill (Tekion → workbook)

## What this is
Joe's **AMG WIP.xlsx** = the monthly fixed-ops metric tracker (DISTINCT from the payroll-vs-RTH workbook in amg-wip-payroll-vs-rth-analysis). 8 tabs: Stevens Creek Toyota, Stevens Creek Volkswagen, Toyota of Fresno (=BT service), Blackstone Body Shop (=BT body), Volkswagen of Clovis, Fresno GM (=BC), Toyota of Lancaster, Alfa Romeo of San Jose. Rows = metrics, one column per month (header row 1 = datetime dated the **26th**, but Joe confirmed the window is the **CALENDAR month**, 1st→EOM).

- Live copy on Joe's Drive: file id `1esCOBSklptjeR3We9dKG6rcaDEfii6aJ` (an **.xlsx in Drive, NOT a native Sheet** — Sheets API can't write it; download via Drive `files/{id}?alt=media` with Bearer token, or convert to native Sheet for API writes). Local mirror: `/home/itadmin/amg-wip/AMG-WIP-live.xlsx`.
- Jay's Google access: symlink `~/.hermes/profiles/jay/google_token.json → /home/itadmin/.hermes/google_token.json` (Walter's base token, Joe's account, Sheets read/write + drive.readonly). Verify with google-workspace `setup.py --check`.

## SCT tab row map (col A labels; other tabs similar)
r4-10 Hours Sold: CUSTOMER / TXM / TOYOTA CARE / PREPAIRD MAINTENANCE / WARRANTY / PDI / INTERNAL · r13-14 VEHICLE ATTENDANCE: TOYOTA / OTHERS · r18-21 WORKSHOP: TOTAL AVAIL HOURS / TOTAL PROD HOURS / UNAPPLIED · r25-30 LABOR RATES (manual, carry forward) · r32 WIP $ · r35-45 ELR by make×paytype · r49-55 ACCESSORY ELRs · r60-67 TXM COUNT/SALE/COST/GROSS + parts block.

**TELL for an unfilled month:** the new column is an exact COPY of the prior month (every cell identical). Diff col N vs N-1 before assuming it's done.

## Data methods (validated 2026-08-03, SCT July)

### 1. Vehicle Attendance (RO count) — live OpenAPI, search-only, quota-cheap
`POST /repair-orders:search` filters: `closedTime BTW [monthStartPT_ms, monthEndPT_ms]` + `status IN CLOSED,INVOICED`, pageSize 200, paginate via `meta.nextPageToken`. NO fan-out → survives even when DEALER_QUOTA is tight (search itself kept working while /jobs fan-out 429'd). Script: `/home/itadmin/tekion-reports/wip_sct_july_attendance.py`. SCT July = 5,199.

**Make split (Joe's canonical filter — VERIFIED EXACT 2026-08-03):** saved filter group **"WIP Attendance - Toyota"** now exists on SCT Advisor Performance (built+saved by Jay via :9223): Pay Type Closed Date / Between / 1st–EOM + Make / In / Toyota, Scion (multi-select "In", NOT is-like). Applying it for July reproduced Joe's number EXACTLY: Total RO Count **5,060** (also Bill Hrs 6,386.37 all-paytype Toyota/Scion). TOYOTA row = that count; OTHERS = Make Not In Toyota/Scion. Save-group mechanics: funnel popover → "Save Filter Group" (top-right) → name input (placeholder "Type Here") + Save span; new group appears in the top singleValue dropdown options. Joe's clock = PAY TYPE CLOSED DATE; RO closedTime differs ~0.3% (DB-derived est was 5,073) — for the sheet use the report/filter-group number. In the DB: `payload->'vehicle'->>'make'` matched case-insensitively against `/toyota|scion/` (casing dirty: "toyota"+"Toyota"). Script: `/home/itadmin/dealer-detail/apps/web/wip_makes.cjs`. PITFALL: live OpenAPI `repair-orders:search` does NOT inline vehicle (link stub only) — make-split live needs per-RO fan-out; use the DB or the saved filter group. For non-Toyota stores confirm the make list per store brand with Joe before first use.

### 2. Hours by pay type / opcode buckets — dealer-detail DB (ZERO Tekion quota) ⭐
**Key discovery:** the dealer-detail Supabase DB (`/home/itadmin/dealer-detail/apps/web`, `RawRepairOrder.payload`) embeds the FULL RO snapshot: `payload.jobs[] = {job:{payType,subPayType,type}, operations:[{operation:{opcode, labor:{billDuration, laborAllowanceDuration, saleAmount, costAmount}}, parts:[...]}]}` plus `payload.vehicle.make`. So operation-level **billed hours = labor.billDuration / 3600** for a whole month with NO API fan-out. Query with a `.cjs` node script via Prisma `$queryRawUnsafe` (no psql installed): join `Store` on abbreviation (SCT/SCVW/BST/BC/TOL/VWC/ARSJ), window on `closeDate` (UTC: month start/end + 07:00 for PT). Working scripts: `apps/web/wip_sct_july_sanity.cjs`, `wip_probe.cjs`.

**Coverage caveat:** DB lags live — SCT July had 4,644 of 5,199 (89%). Report hour numbers as "slightly low" or backfill first (`npm run sync:store -- SCT <days>`, quota-gated).

**Backfill PITFALL (burned 2026-08-03):** `npm run sync:store` needs `.env` loaded — bare invocation prints "Missing required environment variables: DATABASE_URL..." yet still EXITS 0 and ingests NOTHING. Always wrap like the nightly cron: `cd apps/web && set -a && . ./.env && set +a && npm run sync:store -- SCT 35`. Verify ingestion afterward by re-counting the month's ROs (fetchedAt max should be fresh), never trust exit code alone.

### 3. Hours Sold bucket mapping (Joe confirmed 2026-08-03, CORRECTED same day)
The 7 hours rows come from Joe's SAVED FILTER GROUPS on SCT Advisor Performance (load group → set dates → Apply → read Bill Hrs TOTAL).

**⚠️ ONLY ELR IS YTD — EVERYTHING ELSE IS THE TARGET MONTH ONLY (Joe corrected 2026-08-03, same-day reversal of an earlier "needs to be YTD" instruction that turned out to be ELR-specific).** Rule:
- **ELR** (every ELR cell/row, e.g. r35-45 LABOR RATES/ELR block, r49-55 ACCESSORY ELRs) → date range 01/01/<year> → EOM of target month (YTD-to-date average).
- **Everything else** (Hours Sold r4-10, VEHICLE ATTENDANCE r13-14, WIP $, RO counts, parts $, TXM count/sale/cost/gross, workshop hours) → single calendar MONTH window (1st–EOM of the target month only), NOT YTD.
Verified July-only CP (07/01–07/31/2026): **Bill Hrs 2,211.33, ROs 3,177** — this is the correct number for the Hours Sold row. The YTD run (18,486.81/23,619/$174.65) is ONLY valid for the ELR figure ($174.65); do not use the YTD hours/RO-count for the monthly Hours Sold or Attendance rows.

Joe confirmed which groups:
- **CUSTOMER** = `Customer Pay Hours 10/1/2025` — was corrupted (stored Pay Type = **Internal**, stale save); FIXED + re-saved with Joe's approval 2026-08-03 (now Pay Type In Customer Pay). Definition: Pay Type Status In Closed + Opcode **Not In** TAC80–TAC15,TSC1–TSC10 + Pay Type In Customer Pay + Make In Toyota,Scion. (The Internal-corrupted run gave July 1,455.75 ≈ INTERNAL row's magnitude.)
- **WARRANTY** = `Warranty Hours 11/1` ✓ (Joe: correct)
- **TOYOTA CARE** = `TAC/TOYOTACARE REVISED 3/1/25` ✓
- **PREPAID MAINT** = `TSC/Prepaid Hours REVISED 3/1/25` ✓
- **PDI** = `PDI` ✓
- **TXM** = ❌ NOT the `TXM REVISED 9/1` group — Joe: use **"SCP-Toyota Care 2.0" from REPORT BUILDER** (/report-manager custom report; scrape via tekion-report-builder-scraper).
- Attendance = `WIP Attendance - Toyota` group (see above).
SAVED-GROUP PITFALLS: loaded groups carry STALE dates (reset every time) and possibly WRONG edited-then-saved values — read every row (esp. Pay Type) after loading, before Apply. Date calendar: month-grid cells have no onClick — advance RIGHT panel arrow first, then LEFT (left arrow caps adjacent to right panel); details in tekion-standard-reports-performance skill. For YTD: left-panel prev-month arrow (~606,441) back to Jan, click "1" in left panel, click "31" (or EOM) in right panel — range inputs update only after BOTH ends clicked.

**SWITCHING THE SAVED-GROUP DROPDOWN ITSELF (fix, 2026-08-03):** switching the LOADED GROUP (the react-select showing e.g. "Customer Pay Hours 10/1/2025" at the top of the popover) to a different saved group (e.g. "Warranty Hours 11/1") via a raw `/mouse` COORDINATE click on the option row is UNRELIABLE — coordinates drift/mis-hit between renders, and a wrong click can add a stray filter row (e.g. "Bill Hrs Equals") instead of switching groups, leaving the popover in a corrupted "*Edited" state. FIX:\n1. If popover shows "*Edited" or looks corrupted, navigate away (e.g. `/navigate` to `.../home`) and back to the report URL for a clean remount — a same-URL/hash-only reload does NOT reset it.\n2. Open funnel icon via `/mouse` on `.root_filterTrigger_icon` bounding-rect center.\n3. Click the group select control via `/mouse` on `.ant-popover [class*="-control"]` bounding-rect center to open the option listbox.\n4. Query live option elements: `document.querySelectorAll('[id*="option"]')` filtered to `offsetParent` truthy; find target by exact `innerText.trim()` match.\n5. Do NOT click by coordinate. Instead dispatch events directly on that found element in one `/eval` call: `target.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}))`, then `mouseup`, then `target.click()`.\n6. Verify by reading `document.querySelector('.ant-popover').innerText` afterward — confirm group name + a few dependent filter values changed as expected (e.g. Pay Type flipped, Opcode list flipped) BEFORE touching dates or clicking Apply.\nThis mirrors the existing Apply-button dispatch fix below — /mouse coordinate clicks are unreliable on this popover's dynamically-positioned elements in general; prefer find-element-then-dispatch-events for every interactive control inside `.ant-popover`.
**APPLY-CLICK PITFALL (burned 2026-08-03):** clicking Apply via the :9223 `/mouse` endpoint at its coords SILENTLY FAILS on this popover — popover stays open (`*Edited` remains), grid never refreshes, and you'll poll stale totals forever. FIX: dispatch native MouseEvents on the LEAF element via /eval: `[...document.querySelectorAll('.ant-popover *')].filter(e=>e.offsetParent&&e.children.length===0&&e.innerText.trim()==='Apply')` → dispatch mousedown/mouseup/click with bubbles:true. Verify success = popover count drops to 0 AND Total row changes within ~10s. Also: :9223 `/screenshot` is **GET** returning JSON `{"screenshot": "<base64>"}` (POST /screenshot = 404).

### 3b. Bucket mapping via DB (cross-check only — never guess)
RO data exposes only THREE payTypes: CUSTOMER_PAY / WARRANTY / INTERNAL. The sheet splits 7 ways. Observed: TAC15–TAC80 opcodes under CP = TOYOTA CARE row (matches sct-toyotacare-billed-hours-report skill, "not Warranty" rule); TSC* opcodes under CP ≈ prepaid maintenance candidate; TXM* opcodes appear under WARRANTY. **PDI/TXM/PPM bucket definitions must come from Joe's saved Advisor Performance filters — ASK, don't infer.** (Asked 2026-08-03, answer pending — record it here when given.)

### 4. Workshop hours (avail/prod/unapplied)
Tekion Tech Performance report (see tekion-standard-reports-performance skill), flag-date window = calendar month.

### 5. Labor Rates rows
Manual/rare — carry forward prior month unless Joe says changed.

## Sanity-check protocol (Joe asked for this explicitly)
Before filling a whole column: present 3-5 computed cells vs the prior month's values, state coverage caveats, and have Joe verify 1-2 (CP Bill Hrs total + RO Count from his Advisor Performance report for the same window) before running the rest. Joe fills the sheet by hand from numbers posted in Slack — deliver in row order.

## YTD variant — ELR ONLY (verified 2026-08-03, corrected same day)
Joe's rule: **only the ELR figure is YTD**; every other cell (hours, RO counts, attendance, $ totals) uses the single target MONTH. Use this YTD date-range method only when computing an ELR row/cell. Same saved groups, just set Pay Type Closed Date = 01/01/YYYY → end of current month for the ELR read, then re-Apply with 1st–EOM of the target month for the actual Hours Sold number from the same group. Date entry: open funnel → click the START date input in the popover → use `.ant-calendar-prev-month-btn` nav arrow (~606,441) repeatedly until left panel header = "Jan YYYY" → click day 1 in `.ant-calendar-range-left` → click day 31 (end day) in `.ant-calendar-range-right` (right panel will already show the end month). Inputs update to 01/01/2026 / 07/31/2026 and the calendar closes.

**CRITICAL APPLY PITFALL:** the popover's Apply button does NOT respond to /mouse coordinate clicks (popover stays open, grid keeps stale totals — polled 60s with no change). Must dispatch a native MouseEvent on the leaf Apply element via /eval:
```js
const els=[...document.querySelectorAll('.ant-popover *')].filter(e=>e.offsetParent&&e.children.length===0&&e.innerText.trim()==='Apply');
const el=els[els.length-1];const b=el.getBoundingClientRect();
['mousedown','mouseup','click'].forEach(t=>el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,clientX:b.x+b.width/2,clientY:b.y+b.height/2})));
```
Verify success = popover count drops to 0 AND grid Total changes within ~10s. Poll `document.body.innerText` slice after 'Sublet Parts Cost' until the old RO count disappears.

Total-row read order after 'Sublet Parts Cost\nTotal\n': ROcount, [6 $ columns], **BillHrs**, ELR, ... (e.g. YTD CP: `23619 ... 18486.81, 174.65`).

/screenshot endpoint = **GET** returning JSON `{screenshot: <base64>}` — not POST.

**Verified YTD CP (SCT, 01/01–07/31/2026): Bill Hrs 18,486.81, ROs 23,619, ELR $174.65** (July-only was 2,211.33 / 3,177 / $172.63).

## Pitfalls
- OpenAPI RO search results have NO `id` field — use `documentId`; jobs live at `data.jobs`, operations at `data.roOperations` (fan-out path only).
- `get_token(cfg)` requires the cfg arg (`sys.path.insert(0,"/home/itadmin/tekion-api")`).
- 2-4 AM PT = VI pull window; DEALER_QUOTA 429s on fan-out likely. Search-only endpoints still worked.
- Labor $ in CENTS (/100); billDuration in SECONDS (/3600).
- Header dates (26th) are cosmetic — window is calendar month (Joe, 2026-08-03).
