---
name: tekion-ghost-bin-negative-onhand
description: >
  Diagnose a part showing NEGATIVE total on-hand in Tekion that stems from a CDK-migration
  "ghost bin" (a location-less legacy bin like 5005 / 5000 / 5001 / 5004 / RC1 / RC2 carried
  over at CDK→Tekion cutover ~4 yrs ago). The negative lives ONLY on the bin record, has ZERO
  transactions, is invisible to physical inventory (out of count scope), and poisons the
  auto-replenishment math (OH+OnOrder stays under reorder point → perpetual over-ordering).
  Distinct from a real stock-out. Use when Joe says "this part shows -11 on hand / negative
  on hand / auto replenishment isn't working" AND the negative traces to a non-primary bin.
  Sibling of tekion-parts-autoorder-diagnosis (that one = velocity/BRP/BSL/Min stock-outs;
  THIS one = phantom bin balances). WRITE-SIDE FIX PATHS NOW LIVE (2026-07-03): Edit-Part
  redistribution (zero GL) vs bin-level OH adjustment — see FIX PATHS section. Case-B $
  adjustments still require Joe's explicit go.
triggers:
  - negative on hand
  - part shows -11 on hand
  - auto replenishment isnt working
  - ghost bin / legacy bin / CDK bin 5005
  - where did the negative come from
  - bin 5005 negative
trigger: negative on-hand, ghost bin, CDK migration bin, 5005, phantom bin balance, why is on hand negative, auto replenishment not working, bin consolidation, physical inventory missed
---

# Tekion Ghost-Bin Negative On-Hand Diagnosis

> **READ FIRST:** the canonical, fuller parts-replenishment skill is
> **`tekion-parts-autoorder-diagnosis`** — it already contains the deep ghost/phantom-bin
> diagnosis ("PHANTOM/ORPHAN BIN", "PHYSICAL-INVENTORY CROSS-CHECK", "Auto-replenishment is NOT
> broken when On Order is firing"). Load THAT for the diagnostic logic. Load THIS skill for the
> **live :9223 pull mechanics** (the exact endpoints, the `/eval` `js` bug, dealer-switch, the
> screenshot exhibit) and the **vendor-letter** workflow that the canonical skill doesn't cover.

When a part shows a **negative TOTAL on-hand** and "auto-replenishment seems broken," there are
two very different root causes. Don't conflate them:

| Symptom | Root cause | Skill |
|---|---|---|
| Shelf at 0 / kept stocking out, Min set but never recovers | velocity / BSL round-down / negative-OH backfill / Min-Max | `tekion-parts-autoorder-diagnosis` |
| **Total OH negative, but a NON-PRIMARY bin holds the negative** | **CDK-migration ghost bin** | both (diagnosis there, live-pull + letter here) |

## The signature of a ghost-bin negative (what makes it THIS case)

1. **Part Details → Bin Details** shows two (or more) bins: a real **Primary Bin** with a sane
   positive qty (e.g. 2420 = +5), and a **second bin with no Shelf / no Drawer ("- | -")**
   carrying a NEGATIVE qty (e.g. 5005 = -16). Net = the negative total you were handed.
2. The ghost bin number is a **legacy CDK bin**: commonly **5005, 5000, 5001, 5004, RC1, RC2,
   3307, 3505, 2509** at SCT. They have no physical shelf — they're location-less containers
   created at the CDK→Tekion cutover (~late 2022 / "4 years ago").
3. **The ghost bin has ZERO transactions.** In the part's activity log, every PO Received / SO
   Filled / RO Filled posts to the PRIMARY bin only. Tekion auto-extracts from the primary bin;
   the counter cannot choose a bin. So the ghost bin's balance is FROZEN — no sale drains it, no
   receipt rebuilds it. (Confirmed live: spark plug 90080-91180, 5005 = 0 of 1,175 transactions.)
4. **Auto-replenishment is NOT broken.** Stocking Details shows Status=Active, Manual Order=No,
   On Order > 0. It IS firing — it's just doing the right thing off a poisoned number:
   `OH(-11) + OnOrder(30) = 19 < ReorderPoint(25)` → it keeps ordering. Clean the ghost (+16)
   and OH→+5, (5+30)=35 > 25, over-ordering stops. **The fix is a bin consolidation, NOT a
   stocking-param change.**

## ROOT-CAUSE SETTING — why the ghost bin got ATTACHED (KB-confirmed 2026-06-29)

The ghost bin isn't random leftover — Tekion actively MOVES an old part's bin onto its successor
on supersession/auto-replacement. ONE setting controls it:

> **Parts Settings → Auto-Replacement section → Bins option** = radio:
> - **\"Transfer the bin from the old part\"** ← when a part supersedes/auto-replaces, the OLD part's
>   bin is copied onto the NEW part (THIS is how a location-less legacy bin like 5005 gets attached
>   to the successor, carrying its frozen negative).
> - **\"Manually select the bin\"** ← STOPS the auto-transfer; flip to this + Save.

This single radio resolves ALL of: \"why does the system keep changing/moving my parts into different
bins\", \"stop supersession bin change\", \"disable/stop automatic bin transfers\" (KB0016963,
KB0017544, KB0022577, KB0024963, KB0026315 — all five point here). Confirmed live: spark plug
**90080-91180** superseded to **-91184**; Tekion transferred old bin **5005** (no shelf/drawer,
frozen **-16**) onto the new part → **-11** total OH at SCT. KB PDFs + text at
`/home/itadmin/tekion-kb/pdfs/` and `/home/itadmin/tekion-kb/text/` (auto-ingested into GBrain).

## MULTI-BIN IS POSSIBLE — \"Sell by Bin\" feature (the big find, KB0010624, 2026-06-29)

Tekion's DEFAULT is single-bin selling (a part relieves stock only from its **Primary Bin**).
BUT **KB0010624 \"HOW TO: Move On Hand Inventory Between Bins\"** ends with the key note:
> *\"Sell by bin feature must be activated. Found in Parts Settings.\"*

So a part CAN carry on-hand across **multiple bins with per-bin qty and sell from a specific bin**
— but ONLY when the **Sell by Bin** feature is turned on in **Parts Settings**. This is the real
unlock for Joe's back-counter goal (selling/stocking bin 5005 as a genuine second sell location,
not just flipping which single bin is Primary).

Procedure to split on-hand across bins (with Sell by Bin ON): Parts → Parts & Inventory → search
part → Part Details → scroll to **Bin Details** → type the desired **qty for EACH bin** (per-bin
quantities must sum to the part's Total Inventory Qty) → click **Save As**.

⚠️ NEVER-GUESS GAPS before flipping it live (tell Joe, don't assume): (a) exact label/location of
the Sell-by-Bin toggle inside Parts Settings; (b) store-level vs enterprise-level; (c) blast radius
(fleet-wide vs per-part); (d) how PO receiving then asks which bin. Distilled in
`/home/itadmin/tekion-kb/distilled/tekion-bin-management-multibin.md`.

Physical Inventory (Parts app, ARC) has two flavors:
- **Bin Spot Check** (targeted; phases: Setup → Counting → Reconciliation). At Setup, choose
  **\"Create Bin Spot Check By → Bin\"** to scope-count a SPECIFIC bin (e.g. 5005), and tick
  **\"Include parts with 0 bin quantity from the default bin\"** to pull parts regardless of stocking
  status. A spot check scoped to the ghost bin will COUNT it and log the +16 variance — this is the
  lever to catch a ghost the standard count misses.
- **Full Physical Inventory** (Setup → Counting → Reconciliation, then reconcile vs Accounting GL).

GAP CLOSED 2026-06-29 — I now have all 3 canonical Bin Spot Check phase KBs (KB0011053 Setup,
KB0011058 Counting, KB0011059 Reconciliation). Full distilled text at
`/home/itadmin/tekion-kb/text/KB001105[3,8,9]_*.txt` + distilled page
`/home/itadmin/tekion-kb/distilled/tekion-physical-inventory-bin-spot-check.md`.

**EXACT click-path to POST the variance that zeroes the -16 out of bin 5005:**
1. **Setup** (KB0011053): Physical Inventory app → **Create Inventory → Create Bin Spot Check** →
   name it → **Create Bin Spot Check By = Bin** → **Select Bins** = the ghost bin (5005) → check
   **\"Include parts with 0 bin quantity from the default bin\"** → pick warehouse/brand → optionally
   add **Other Bins** as a count-sheet column → **Calculate** → review summary → **Start Inventory**
   → tick \"I agree…\" → **Proceed** (enters Counting).
2. **Counting** (KB0011058): open the in-progress spot check → **Download Count Sheet** → physically
   count 5005 → select the sheet, **input physical count** (for a dead ghost, that's the true qty,
   often 0) → green check when complete; **Mark all counts as 0** if the bin is empty → **Show
   Variance** to preview On-Hand vs Physical → when done **Mark as Complete** (confirm popup) →
   **Proceed to Reconciliation**.
3. **Reconciliation** (KB0011059 — THE COMMIT): open the spot check → review **Net / Positive /
   Negative Variance** quick views + Total Variance (by Bin or Part) → optionally **Re-Open Counts**
   (max 2x) → when satisfied click **Make Adjustments**. This is the ONE-CLICK \"Automatic On Hand
   adjustments\" commit — it auto-creates ALL on-hand adjustments, refreshes, and shows the final
   results + any exceptions in the **Summary** phase. The result lands in the **On Hand Adjustment**
   application. ⚠️ \"Make Adjustments\" is the irreversible write — verify variances FIRST.
Permissions: Physical Inventory Edit + Show/Download Variance in Count Sheet.

Still nice-to-have (not blocking): \"PARTS APP: Auto Supersession Replacement Setups\" KB.

**ALTERNATIVE to clear an EMPTY ghost bin (KB0017730 \"Delete the Unallocated Bins\"):** once the
ghost bin's qty is zeroed, you can DELETE it: Warehouse Management → open the bin's location →
Assign Location (if unallocated) → confirm bin has 0 parts → trash icon at end of the bin row →
Save. **A bin can only be deleted when it holds NO parts** — so zero it (Bin Change or spot-check
adjustment) FIRST, then delete.

## ⚠️ SUPERSEDED FIX PHILOSOPHY (Joe, 2026-07-03) — DUAL-BIN STRATEGY, DO NOT DELETE BINS

Joe REVERSED the "zero + delete ghost bins" end-state: at SCT, **ALL 5000-SECTION BINS
(5000–5007) = BACK COUNTER shelves (Joe confirmed 2026-07-04 — not just 5005) and 2420 =
FRONT COUNTER (Primary)** — these bins are intentional and STAY. Do NOT propose bin
deletion or "every non-primary bin = 0" anymore. The operating model instead:

- Tekion still only relieves the **Primary** bin on any sale, so every back-counter physical
  pull silently corrupts both bins (2420 reads low, 5005 reads high). Nobody erred — system design.
- **Fix per occurrence** = transfer the sold qty **5005 → 2420** via Edit Part → Bin Details
  redistribution. When the TOTAL is unchanged this posts **ZERO GL, no adjustment record, no
  audit-log entry** (Hemant/Tekion PM confirmed; verified live: no ledger row appeared).
  Because it's trail-less, keep an own CSV log of redistributions.
- **Bin-level On Hand Adjustments went LIVE for all AMG stores 2026-07-03** (Hemant enabled).
  These DO post to GL and appear in the Transactions ledger as `Adjustment Increment/Decrement`
  with a Bin column (On Hand Adjustment app, /parts). Use ONLY when the total is wrong.
  Lesson from the live fix (91180, adj #36365-69): it took Joe+Ronald 5 adjustments to land the
  split — ALWAYS compute the exact target per-bin numbers FIRST and post once.
- Triage rule: **split wrong / total right → Edit Part redistribution (zero GL). Total wrong →
  bin-level OH adjustment (GL).**
- **Daily watchdog exists**: cron `d372a20d2889` "SCT Back Counter (5000-section) Daily Bin Check" 8PM — pulls the
  5000-section Bin Report (method below), snapshots to
  `/home/itadmin/tekion-reports/bin5000s-snapshots/YYYY-MM-DD.json`, diffs vs prior day, flags
  ⚠️ **KNOWN LIMITATION (Joe identified 2026-07-04): a snapshot DIFF cannot catch a back-counter
  pull** — Tekion relieves only the Primary bin, so the 5000s bin doesn't move on the sale. The
  CORRECT detection = cross-reference the day's RO part sales against the back-counter roster —
  see skill `sct-backcounter-ro-sales-countsheet` (scan + signed-bin enrich + Tekion-style count
  sheet with Primary/Back write-in boxes, emailed via Stacey). The snapshot still matters as the
  ROSTER source + catches adjustments/transfers/new negatives.
  parts with last-24h transactions ("transfer sold qty 5005→2420?") + NEW negatives (missed
  transfer smoking gun) to Slack. Baseline seeded 2026-07-03.
- **AGREED FULL-SCOPE MONITORING DESIGN (2026-07-03, Joe signed off):** since
  only Primary sells, the Multiple Bin Report catches everything — scan ALL multi-bin parts
  daily, then per-bin CLASS decides what alerts: back-counter bins → alert on CHANGES (sale
  needing transfer, new negative); legacy bins → alert on ANY qty ≠ 0 (should never regrow);
  special bins (SOLD/TXM/SP-ORD/RETURNSHELF) → suppressed; ANY negative anywhere → always
  alert. **SCT CLASSIFICATION (Joe, 2026-07-04): ALL 5000-section bins (5000–5007) = BACK
  COUNTER.** RC1/RC2/3307/3505/2509 remain presumed LEGACY (not yet re-confirmed post-ruling);
  other stores' back-counter lists still TBD from Joe. The watchdog cron (d372a20d2889, 8PM
  daily — moved from 6AM per Joe 2026-07-04) was expanded
  2026-07-04 to cover the whole 5000 section (snapshots at
  `/home/itadmin/tekion-reports/bin5000s-snapshots/YYYY-MM-DD.json`, keyed by bin; legacy
  5005-only baselines live in `bin5005-snapshots/`).

## :9223 CONTENTION FALLBACK — headless standalone pull (verified 2026-07-12)

If :9223 is being actively driven by ANOTHER session (symptom: your /navigate lands on
bin-reports but 1-2 calls later location.href has flipped back to a different page/dealer —
e.g. a BC service-menu edit page — someone else's automation owns the browser), do NOT fight
over it. Use the standalone headless script
`/home/itadmin/tekion-reports/bin5000s_daily_pull.py` — own Playwright + storage_state,
switches dealer to 876, selects all 5000-section bins via `[data-test-id*="customCheckBoxTreeNodeDiv"]`
rows (scrollIntoView → checkbox rect → mouse.click → verify checked), clicks Apply, captures
binReport/generate via `page.on("response")`, paginates by Next, saves the daily snapshot.
Runs clean end-to-end in ~90s. Since 2026-07-13 the script strips Pendo overlays
(`document.querySelectorAll('[id*="pendo"],[class*="pendo"]').forEach(e=>e.remove())`) before
clicking the dealer pill — a pendo-backdrop was intercepting the click and failing the dealer
switch (FAIL_DEALER). TWO MORE PITFALLS baked into it:
- **`time.sleep()` does NOT pump Playwright sync-API events** — `page.on("response")`
  callbacks only fire during a Playwright call. Waiting with time.sleep made the generate
  XHR invisible (looked like it never fired; the table rendered fine in the screenshot).
  Always wait with `page.wait_for_timeout(ms)`.
- Match pagination on the COUNT of generate captures, not len(all captures) — messaging/
  clock-poll XHRs land constantly and fake a "new page arrived" signal.
Note: a part's Primary is NOT always 2420 (e.g. 17801-77050's primary = **2419**).

## LIVE BIN REPORT PULL via :9223 (the reusable scrape, verified 2026-07-03)

Endpoint captured: **POST `/api/wms/u/warehouse/binReport/generate`** — response
`{data:{count, hits:[...]}}`, hits have `partNumber, description, onHandQuantity (SIGNED here,
unlike the UI magnitude claim below — trust the JSON), cost, listPrice, sourceCodeName,
stockingStatus, monthNoSale, ytdSaleQty, onOrderQTY, onHoldQTY, multipleBins,
multipleBinNumbers[] (the OTHER bins), lastTransactionTime (ms epoch)`. 50 rows/page.

Procedure (page = /parts/warehouse-management/bin-reports, must be on right dealer — session
DRIFTS between turns, verify `currentActiveDealerId` first):
1. Arm XHR hook AFTER navigation (nav wipes hooks): override `XMLHttpRequest.prototype.open/send`,
   push `{u,r:responseText}` for URLs containing `/api/` into `window.__xhr`.
2. Select the bin: find the visible leaf element with innerText exactly '5005'
   (`parts_customBinSelectionField_binNodeLabel...`), **walk UP its parents to find the row's
   `input[type=checkbox]`** and /mouse-click THAT (clicking the label text alone selected a
   WRONG bin — 2601 — on first try; verify with
   `document.querySelectorAll('input[type=checkbox]:checked')` before Apply).
   **MULTI-BIN SELECT WORKS in one pass (verified 2026-07-05, 7 bins):** loop per bin —
   `leaf.scrollIntoView({block:'center'})` (leaves sit ~y=14550, WAY offscreen; scroll is
   mandatory), sleep ~0.5s, re-read the checkbox rect FRESH after each scroll (all boxes land
   ~x122,y445 post-scroll), /mouse-click, verify `cb.checked===true` before moving on. Then ONE
   Apply → ONE combined generate XHR covering all selected bins (each hit carries `binNumber`,
   so rows split cleanly per bin). No need for one-bin-at-a-time loops in the UI path — that
   caution applies only to the headless API-replay harvest (server 500s under load).
3. Click the visible **Apply** button → report loads, XHR captured.
4. Pagination: "Showing 1-50 out of N"; scrolling `.rt-tbody` does NOTHING (not infinite scroll)
   — click the visible **'Next'** text element at the bottom (~x794,y686) and capture page 2's
   fresh binReport/generate XHR. Merge + dedup by partNumber.
   Robust loop (verified 2026-07-05, 5 pages): record `window.__xhr.length` BEFORE clicking
   Next, then poll ~1s for a new entry whose FULL `u` contains 'binReport/generate' with index
   ≥ that length; take the LAST match. Repeat until merged hits == `data.count`.
   ⚠️ When listing `window.__xhr` to find the page-2 capture, match 'binReport/generate' against
   the FULL `x.u`, not a sliced substring — the generate URL is only ~66 chars, so e.g.
   `u.slice(60,120)` returns just "nerate" and the filter silently finds nothing even though the
   XHR is already captured (cost an iteration 2026-07-04). Also: the page-2 XHR often lands in
   `__xhr` immediately on click; list ALL entries with `{i,u,len}` and pick the LAST generate.
   Watchdog cron note: since 2026-07-05 the DAILY 5000s snapshot covers ALL section bins
   (5000-5002, 5004-5007 exist at SCT; 5003 absent) via one multi-select Apply; ~224 parts,
   5 pages.
5. Extract big responses in ≤15000-char slices via `/eval` `window.__xhr[i].r.slice(a,b)`.

Ghost Bin 2.0 deliverable pattern (Joe liked): multi-tab xlsx — Summary / Negative (fix first) /
Positive (verify shelf) / Zero (stale), ranked by extended $, red/green fills, "Other Bins" column;
send via Stacey with explicit "attach real MIME" instruction. Saved at
`/home/itadmin/tekion-reports/ghost-bin-2.0-sct-5005.xlsx`.

## BULK API HARVEST — quantify ghost bins store-wide (VERIFIED 2026-07-03, the $200K find)

Skip DOM scraping entirely. Three internal APIs (browser-replay w/ captured axios headers)
give the FULL picture. Capture headers once via a headless Playwright run with
`storage_state` + request/response hooks (pattern: `/home/itadmin/sct-physical-2025/harvest_ghost_bins.py`),
save to `api-headers.json`, then replay from plain Python `urllib` — they work OUTSIDE the browser.

**⚠️ SIGN TRAP (cost a wrong first analysis):** `binReport/generate` rows return
`onHandQuantity` as UNSIGNED MAGNITUDE (a -16 bin shows as 16). The SIGNED per-bin truth is
`partBinMappings[].quantity` from withPart/search. Use generate only as a ROSTER of which
parts live in a bin; always re-pull signed quantities per part.

1. **Bin roster** — `POST /api/wms/u/warehouse/binReport/generate`, body =
   `{"tekSearchAndAggregationRequest":{filters:[{"field":"binId","operator":"IN","values":[<binId>]}],
   pageInfo:{start,rows}}, "fields":[...]}`. Also accepts `onHandQuantity` LT filter.
   binId↔number map: capture `/api/wms/u/warehouse/binReport/locationIdBinIds` + `/api/lookup/ids`
   (BINS) from the Bin Reports page load. **Server 500s under load** — query ONE bin at a time,
   rows≤100, sleep 1-2s between pages, retry w/ backoff; save incrementally; run as background job.
2. **Signed per-bin truth (batch)** — `POST /api/wms/parts/u/inventory/withPart/search`, body =
   `{"filters":{"partId":{"key":"partId","values":[...≤40 ids]}},"page":{"offset":0,"rows":50}}`
   (NOTE: different body shape, NOT tekSearchAndAggregationRequest; a bare `searchText` body is
   IGNORED and returns unfiltered junk). Response shape (CORRECTED 2026-07-06 — the earlier
   note was wrong and cost an empty-extraction retry): items are in `data.list[]` (NOT
   data.hits); each item's TOP-LEVEL keys = `{part, partInventory, partBinMappings, bins,
   resolvedPartNumber, ...}` — **`partBinMappings` is a SIBLING of partInventory, NOT nested
   inside it** (reading `partInventory.partBinMappings` returns nothing). Quantities nest at
   `partInventory.quantity.{totalQty, onHandQty, onOrderQty, minimumQty, available}` (a nested
   object, not flat fields). `part.partNumber` is dash-stripped; `partInventory.partNumber`
   also exists. Mapping fields unchanged: {binNumber, quantity **signed**, primaryBin,
   modifiedTime, lastModifiedByUserId}. The saved
   primaryBin, modifiedTime, lastModifiedByUserId}. The saved
   `/home/itadmin/sct-physical-2025/api-headers.json` replay still authenticates (2026-07-05)
   — but returned **401 by 2026-07-08** (headers expire within days). If the replay 401s,
   DON'T re-harvest just to verify one sign: navigate the :9223 browser to the part's
   Part Details page and read Bin Details from the DOM instead
   (`t.lastIndexOf('Bin Details')` slice gives per-bin SIGNED qtys + Total Inventory Qty).
   ~3,150 parts in 45s at batch=40. `partId` accepts BOTH forms: OEM ids (`M_TMNA_...`) and
   raw 32-hex ids (locally-sourced parts like 04500-1 have hex partIds — take partId straight
   from the binReport hit).
2b. **PARTS ACTIVITY LOG (front-vs-back counter split!) — CRACKED 2026-07-06** —
   `POST /api/parts/activity-log/u/search`, body MUST be wrapped in `tekRequest`:
   `{"tekRequest":{"filters":[{"field":"inventoryId","operator":"IN","values":[<invIds ≤20-40>]},
   {"field":"transactionTime","operator":"BTW","values":["<ms0>","<ms1>"]},
   {"field":"refType","operator":"IN","values":["FULFILMENT","SALES_ORDER"]}],
   "pageInfo":{"start":N,"rows":500}}}` → `data.count` + `data.hits[]`. Without the tekRequest
   wrapper = 400 "tekRequest must not be null"; wrapping tekSearchAndAggregationRequest INSIDE
   tekRequest = filters IGNORED (returns 3.1M rows). inventoryId = `partInventory.id` from
   withPart/search. Hit fields: `refType` (**FULFILMENT = RO parts sales/back counter,
   SALES_ORDER = counter sale/front counter**, PURCHASE_ORDER, ADJUSTMENT, MATERIAL_RETURN,
   FULL_INVENTORY, CUSTOMER, MIGRATED), `type` (DELIVER_DIRECT/NEGATIVE_SALE=sale w/ delta<0;
   LOCK delta=+1 + DELIVER_LOCKED delta=-1 pair on locked SOs — count only the negative-delta
   leg or you double/zero-count; RETURN delta>0), `deltaOnHandQty` (SIGNED),
   `refNumber` (= RO# on FULFILMENT, SO# on SALES_ORDER), `binNumber`, `customer.customerName`,
   `soldByName`, `transactionTime`. THIS is how you split a part's movement front vs back
   counter (Glade's flip-the-primary analysis, June 2026: 221 dual-bin parts, 74% of movement
   = RO/back; report script `/home/itadmin/tekion-reports/render_bin_primary_recommendation.py`,
   data build inline — parts map at data/bin-primary-analysis-parts.json).
3. **On Hand Adjustment ledger** — `POST /api/wms/parts/u/adjustment/search`, body =
   `{"sort":[{"field":"createdTime","order":"ASC"}],"filters":[...],"searchText":"<part#>",
   "key":"parts.onHandAdjustmentList","pageInfo":{start,rows}}`. searchText by part number = full
   adjustment history for that part (this dated 91180's -16 to adjustment #1371, 2022-10-12 CDK
   cutover Bin Check Decrease of exactly 16, and proved the June 2025 physical posted only +1 net).
   `createdTime BTW` filter = all adjustments in a window (June 2025 = 7,637). Reason names:
   `/api/parts/proxy/u/settings/adjustments/reasons` (Bin Check ±, Physical Inventory Adj ±,
   Part Replacement ±, PDC ship, Part Returned). Resolve `userId` via OpenAPI
   `sct_menu_sales_api.user_name()` (works for numeric ids + UUIDs).
   OHA page route = `/parts/onhand-adjustment` (NOT /parts/on-hand-adjustment — that renders blank).

Analysis split that matters to Joe: NEGATIVE bin balances = phantom, understate book value
(found money if store shows short); POSITIVE balances in legacy bins nobody counts = book value
possibly not on any shelf (makes a shortage WORSE — the bigger exposure: SCT 2026-07-03 =
-$32.5K phantom negatives vs +$200K positives, RC1+RC2 alone $151K). Report both directions.
SCT secondary-bin set verified: 5000-5007 (= BACK COUNTER per Joe 2026-07-04, NOT legacy),
RC1, RC2, 3307, 3505, 2509, SOLD (+ SP-ORD, RTN have
negatives too) — when sizing "stranded legacy $", EXCLUDE the 5000 section (that stock is real
back-counter shelf, not phantom). Deliverable = multi-tab xlsx via Stacey (smtplib MIME, never himalaya template).

## Why physical inventory does NOT fix it (the key insight Joe cared about)

A physical inventory only **reconciles bins it actually counts**, and the count typically reconciles
the **primary / active bin**, not migrated legacy bins. If the primary (2420 = +5) matches the
system, the part shows **NO variance** and never appears on the **Final Parts Exception Report** —
*by design*, not by error. The −16 in the ghost bin was simply **never in scope**. A negative
shelf qty is physically impossible, so a count that REACHED the ghost bin would log a +16 variance;
its ABSENCE from the exception report is the proof the bin was out of scope. (This is the honest
framing for any letter to the inventory vendor — see below.)

### VENDOR-CONFIRMED mechanism (Kevin Lopez / Dealers Inventory Service, 2026-06-29)

The decisive answer came from the inventory vendor himself, and it REFINES the above: the crew DOES
count every bin (their count sheet prints a line per bin Tekion shows), BUT **Tekion's post-back
reconciles to the PART TOTAL only — it does NOT write the corrected per-bin counts back to the
individual bins.** So even when the crew physically counts the ghost bin and submits a real number
for it, Tekion discards the bin-level detail and only trues-up the part total. Result: the total can
end up correct while the **bin SPLIT stays broken** (negative frozen in the ghost bin, offset by an
inflated primary), and the part shows no variance **when its TOTAL matched at count time**. So the
honest conclusion is **NOBODY made an error** — it's a Tekion bin-level reconciliation limitation.
The only thing that fixes the split is a deliberate manual Bin Change / consolidation (the count
structurally cannot), OR a Bin Spot Check scoped BY BIN to the ghost (see CATCH mechanism). When
confirming this with Joe, also watch the TOTAL gap: if system net (e.g. -11) ≠ his physical total
(e.g. 13), then \"just shift the ghost into primary\" preserves the WRONG total — truing-up to physical
DOES change the total (+24 in that case), which is a different operation than a pure redistribution.

### 2025 SCT PHYSICAL — the hard numbers + the OPEN "expected 4" question (Kevin email 2026-07-04)

Kevin's 2025 FINAL physical detail for 90080-91180: bin 2420 counted 36 vs system-expected 46
(-10); bin 5005 counted 9 vs **system-expected 4** (+5); STOCKINGSHELF handwrite +6; **net posted
+1**, post-count OH = 51. Adjustment ledger CONFIRMS: June 2025 physical posted **+1 on 91180 and
+13 on 91184**, reason "Physical Inventory Adj." Kevin also confirmed he does NOT have per-bin
post-back counts (consistent with the total-only mechanism above).

**⚠️ OPEN QUESTION (pending Kevin's answer, Joe asked directly):** the count sheet's "expected 4"
for 5005 matches NO reconstructable ledger state — the ledger shows 5005 at **-16 at count time**
(frozen since CDK-cutover adj #1371, Oct 2022). Working hypothesis: the vendor's count-file export
got the MAGNITUDE without the SIGN (same unsigned quirk as binReport/generate). Consequence: the
variance was computed against the wrong baseline → the physical **under-corrected the part by ~20
units** while netting a clean-looking +1 that never hit the exception report — the count *laundered*
the ghost rather than missing it. When diffing any vendor count file, always compare expected qtys
against SIGNED partBinMappings, and check whether negatives were systematically masked.

Certified 2025 recap dollars (STEVENS CREEK TOYOTA 2025 PRELIMINARY pdf): **$1,589,445.07
computer / $2,000,372.62 combined**, including line "LESS TEKION UPDATE EXCEPTIONS: **-$50,924.70**"
(unexplained — worth a line-item review; may touch these same bin anomalies).

**Shortage framing Joe asked for (2026-07-04 audit):** phantom NEGATIVE bin balances = found value
(reduce an apparent shortage; SCT = 173 rows, -1,096 units, **-$32,561.78**; 73 parts net-negative
total = -$9,922.56). Stranded POSITIVES in uncounted legacy bins = the REAL exposure (**+$200,084.83**,
RC1+RC2 alone $151K); net legacy-bin distortion **+$172,871.67**. But the recovery from cleaning
negatives only materializes if reconciliation runs against SIGNED bin balances — a masked count
takes the shortage hit AND forfeits the offset. Full workbook:
`/home/itadmin/sct-physical-2025/` outputs, emailed to Joe via Stacey 2026-07-04.

Post-cleanup state after Joe+Ron's 2026-07-03 fix: 91180 = 28 total (2420=23, 5005=+5),
91184 = 35 total (2420=25, 5005=+10) — positive 5005 residue is intentional under the dual-bin
strategy but will keep confusing counts until transferred on sale.

## Live diagnosis procedure (read-only, via persistent browser :9223)

Prereq: authenticated :9223 session on the right dealer (e.g. SCT/876). If the context dropped to
/login, restore it (see PITFALLS — login + storage_state + dealer switch). Load `tekion-sitemap`
and `persistent-browser-server` first.

1. **Open the part.** Navigate to
   `https://app.tekioncloud.com/parts/inventory/part/view/M_TMNA_<PARTNUM_no_dashes>/details`
   (Toyota OEM prefix `M_TMNA_`, strip dashes; e.g. 90080-91180 → `M_TMNA_9008091180`).
   **The URL also accepts the raw partId directly** (verified 2026-07-08) — e.g.
   `/parts/inventory/part/view/67b7524aabcd5b725ef3773b/details` — which is the ONLY way in
   for locally-sourced parts (BG products like 31532, 04500-1) that have hex partIds and no
   OEM id. Take `partId` straight from the binReport/generate hit.
   Wait ~7s for the SPA to boot. Confirm the body shows the part name + correct store.

2. **Read Bin Details from the rendered DOM** (the authoritative source for the per-bin qty —
   it is NOT in a report, it's on the bin record):
   ```python
   # /eval — note the param key is "js" (NOT "expression"!)
   post("/eval", {"js": "(()=>{const t=document.body.innerText;const s=t.indexOf('Stocking Details');return t.slice(s, s+1500);})()"})
   ```
   This returns Stocking Details (Source Code, Status, Manual Order, Total OH, On Order, BRP/BSL,
   Min/Max, Last Purchase/Sale) AND the Bin Details table (each bin + Shelf/Drawer/Qty + Total).

3. **Prove the ghost bin has zero transactions** (the activity-log API). The part's
   `inventoryId` is on the inventory record. Endpoint:
   `POST /api/parts/activity-log/u/search` with body filtering `inventoryId IN [...]`, page rows
   2000. Because a bare in-page `fetch()` is REJECTED ("Token doesn't exist or is invalid" — the
   app's axios interceptor adds auth headers a raw fetch lacks), capture it by installing an XHR
   hook and letting the app's own React Query fire it, OR re-use the previously-pulled ledger.
   Tally `binNumber`: the ghost bin should be 0; primary bin holds all activity.

4. **Show it's systemic (not a one-off)** with the **Bin Reports** screen:
   `https://app.tekioncloud.com/parts/warehouse-management/bin-reports` → filter Custom = the ghost
   bin number (e.g. 5005) → it lists EVERY part stranded in that one dead bin (Total Bin Qty shown
   POSITIVE here = magnitude; the Part Details view applies the sign and shows it negative — same
   number). One filter immediately reveals multiple parts → confirms fleet-wide scope.
   Sidebar "Available Bins (Shelf|Drawer)" with "- | -" = location-less ghost confirmed.

5. **(Optional) Multiple Bin Report** (Parts → Reports) lists every part holding >1 bin — at SCT
   ~5,345 parts carry legacy CDK bins. Use to size total dollar distortion for a cleanup worklist.

## Screenshot exhibit (for a vendor letter / proof)

The cleanest single exhibit is **Part Details → Bin Details** showing the NEGATIVE (e.g. 5005 = -16),
because it visibly shows the impossible negative. To capture it:
- Click the left-sidebar "Bin Details" anchor (a `.ant-tabs-tab` ~x184; find it via
  `[...document.querySelectorAll('*')].filter(e=>e.innerText.trim()==='Bin Details' && e.offsetParent && rect.x>0 && rect.x<400)`)
  then `/mouse` click it to scroll-jump the section into view (a plain scrollIntoView on the header
  often lands above the table).
- `GET /screenshot` returns JSON `{screenshot: <base64>}` — base64-decode to PNG.
- ALWAYS vision-verify the -NN is legible before handing it over.

## The vendor letter (if Joe wants to question the physical inventory)

Frame as GENUINE inquiry, NOT accusation — Joe explicitly wanted "help me understand how it was
handled," not a challenge. Three questions: (1) SCOPE — do you reconcile ALL bins or only the
primary/active bin; are legacy/secondary bins in scope? (2) NEGATIVE BALANCES — how does your
process handle a negative on-hand in a bin (flag / adjust / leave)? (3) THIS CASE — part shows -16
in bin 5005 yet no variance on the exception report; how was this bin handled? Route the DRAFT
through Stacey (agent-to-agent-bridge), do NOT send direct. Addressee for SCT's vendor: Kevin Lopez,
Dealers Inventory Service, 8959 "B" Chapman Ave, Garden Grove CA 92841, 714-537-2312. Sign as Joe
Castelino, VP Fixed Ops. NB: the report has the firm's mailing address/phone but NOT Kevin's email —
ask Joe for the email or send as a printed/PDF letter.

## FIX PATHS — WRITE ACCESS IS LIVE (updated 2026-07-03, supersedes "read-only" framing below)

Tekion PM Hemant Agarwal enabled **bin-level On Hand Adjustments for ALL AMG stores** on
2026-07-03 (On Hand Adjustment app under /parts, Create Adjustment form: part / bin / qty /
reason / notes / unit+total cost). Verified live: Joe + Ronald E Rice posted bin-level
adjustments #36365–36369 on spark plug 90080-91180 the same morning. There are now TWO fix
paths — choose by whether the TOTAL is right:

| Case | Symptom | Tool | GL impact |
|---|---|---|---|
| **A — split wrong, total right** | ghost bin ± qty offset by primary; total matches shelf | **Edit Part → redistribute qty across bins** (Hemant's alternative) | **NONE** — no adjustment record, no ledger row, no audit log |
| **B — total wrong** | system total ≠ physical count | **bin-level On Hand Adjustment** (or Bin Spot Check → Make Adjustments) | Yes — posts Adjustment Increment/Decrement rows + $ |

Verified mechanics of Case A (Edit Part redistribution): per-bin qtys must sum to Total
Inventory Qty; saving changes the SPLIT with **zero transactions, zero audit-log entry, zero
GL**. Because it leaves NO paper trail, keep an own CSV log (part, before/after per bin) for
every redistribution.

Verified mechanics of Case B (bin-level OH adjustment): each posts a ledger row
"Adjustment Increment/Decrement" with adjustment number, bin, qty, $ at unit cost, user.
**The Before/After Qty column in the Transactions ledger tracks the running PART TOTAL, not
the bin balance** — don't misread a bin adjustment's After Qty as the bin's new qty.
A messy manual session (91180 took FIVE adjustments by two people to land at the intended
split) is the argument for computing the exact target split FIRST, then posting once.

**END-STATE RULE (REVISED by Joe 2026-07-03, supersedes "all non-primary = 0"):** the rule
depends on the BIN CLASS, which only Joe can assign (data can't distinguish a real back
shelf from a dead CDK bin):
- **BACK-COUNTER bins (SCT = the ENTIRE 5000 section, bins 5000–5007; Joe 2026-07-04)** —
  legitimately hold POSITIVE qty matching the
  physical back shelf. 91180 at 2420=23 / 5005=5 (total 28) is Joe's INTENTIONAL correct
  state, not a stray. Do NOT zero these. Manage via the per-sale transfer workflow (below).
- **LEGACY/ghost bins (RC1, RC2, old CDK bins…)** — must end at EXACTLY 0, then may be
  deleted (KB0017730). Any qty ≠ 0 regrowing here = alert.
- **SPECIAL-PURPOSE bins (SOLD, TXM, SP-ORD, RETURNSHELF)** — process bins, leave alone.
Positive qty in a NON-back-counter secondary bin is still harmful (unsellable + pads
replenishment total so the sellable shelf sinks below Min before reorder fires).

**THE DUAL-BIN DRIFT + TRANSFER WORKFLOW (Joe's key op question, confirmed correct):**
back counter physically pulls from 5005 but Tekion decrements 2420 (only Primary relieves)
→ every back-counter sale makes 2420 read low and 5005 read high. Manual fix per
occurrence: Edit Part → Bin Details → move the sold qty **5005 → 2420** (total unchanged,
zero GL). The daily watchdog is the CATCH mechanism.

**Standard per-part recipe (legacy-bin cleanup):** (1) count the primary shelf; (2) if
total matches → Edit Part, all qty to primary, legacy bins = 0 (Case A, free); (3) if
total wrong → bin-level OH adjustment for the difference (Case B); (4) once 0, legacy bin
may be deleted (Warehouse Mgmt, KB0017730 — back-counter bins are NEVER deleted);
(5) prevention: Parts Settings → Auto-Replacement → Bins = "Manually select the bin".
Post Case-B batches early in the month (GL noise settles before close); Jay may execute
Case-A redistributions with Joe's go per BATCH, but still never posts a Case-B $ adjustment
without explicit per-change go.

**AUTHORIZATION REAFFIRMED (Joe 2026-07-05, "I don't want you to do it. Just so I know."):**
Jay confirmed capability but must NOT touch bin quantities autonomously. Two caveats stated
to Joe: (1) Jay has NEVER executed an Edit-Part redistribution live (Joe+Ronald did 91180 by
hand) — the first must be a single part with Joe watching before any batching. (2) **AUTO-
TRANSFER BLIND SPOT:** RO data shows what SOLD, not which counter it was PULLED from — a
front-counter sale of a dual-bin part needs NO transfer, so auto-transferring every back-bin
part sale would corrupt splits in the other direction. Auto-transfer is only safe when the
back bin is the only real stock, or with human shelf confirmation (the count sheet). Also
note: 11 SCT parts have a 5000s bin as their PRIMARY — those back bins DO relieve on sale
(exception to "only 2420 relieves").

## PITFALL — wrong part / wrong dealer reads (cost a wrong report 2026-07-03)

- Supersession pairs look near-identical (90080-9118**0** vs 9118**4**). Confirm the exact
  part number with Joe before reporting bin states — I reported the successor's bins when Joe
  had adjusted the predecessor.
- The :9223 session DRIFTS DEALERS between turns (found sitting on BT/1249; same part number
  showed BT's record: bin SP-ORD, qty 0). **Always check `localStorage.currentActiveDealerId`
  AND the store name in the page header before reading part data**, and switch via the dealer
  pill if wrong. A part URL loads fine under the wrong dealer with no error.

## The fix — (LEGACY section, see SUPERSEDED FIX PHILOSOPHY above; bin deletion is OFF the table per Joe 2026-07-03)

Bin consolidation: zero/merge the ghost bin balance into the primary bin so the phantom negative is
removed and true OH = primary qty. The correct counter procedure for locally-sourced parts going
forward is a true in-and-out (receive +qty FIRST, then sell −qty, net 0) so OH never goes negative
(see tekion-parts-autoorder-diagnosis negative-OH backfill trap). To CATCH the ghost, run a Bin
Spot Check scoped By Bin = the ghost bin number (see "CATCH mechanism" above). PREVENT recurrence:
flip Parts Settings → Auto-Replacement → Bins to "Manually select the bin" so future supersessions
don't re-attach a dead bin (see "ROOT-CAUSE SETTING" above). The exact reconcile/variance-post
click-path lives in the Bin Spot Check Counting + Reconciliation KB articles I don't yet have —
stop and flag rather than guess the post step.

## PITFALLS (hard-won this session)

- **`/eval` param is `js`, NOT `expression`.** Wrong key → HTTP 400. (Cost a full restore attempt.)
- **Dealer switch ≠ setting `currentActiveDealerId` in localStorage.** That key resets on nav.
  Switch via the UI: click the dealer pill (`.root_dealerSe...` ~x1100,y20) → popover → `/mouse`
  click the "Stevens Creek Toyota" leaf (`root_dealerInfoItem_itemName` ~x1074,y346). Default
  dealer after login is Blackstone Chevrolet (BC, 1251) — you MUST switch to 876 for SCT parts.
- **A bare in-page `fetch()` to `/api/...` returns "Token doesn't exist or is invalid"** even when
  the page is authenticated — the app's axios interceptor adds headers a raw fetch lacks. Use an
  XHR hook + let the app fire its own request, or read previously-captured data.
- **Session restore into :9223 after it dropped to /login:** run `tekion-auth/login.py` (writes
  `.tekion-storage-state.json`), then POST cookies to `/cookies`, navigate to `/login` (need an
  origin), set all ~21 localStorage keys one-by-one via `/eval {"js": ...}`, then navigate into the
  app. It will land authenticated on BC — switch dealer via UI as above.
  RE-VERIFIED END-TO-END 2026-07-04 (cron run): token was 227 min expired → any /mouse click on
  the dealer pill bounced the SPA to `/login?redirectTo=...`. Full recovery = `login.py` (fresh
  OTP, LOGGED_IN) → inject cookies+21 keys → `/navigate /home` → lands on BC/1251 authenticated →
  dealer pill x1130,y32 → SCT leaf (filter `root_dealerInfoItem`, includes 'Stevens Creek Toyota',
  NOT 'Volkswagen', take LAST visible match ≈x1074,y287) → dealer=876. Whole flow is safe to run
  unattended inside a cron job.
  ⚠️ **REUSED ≠ alive (verified 2026-07-11):** plain `login.py` can report "token exp in 59 min →
  ALIVE — reusing" yet the injected cookies+keys STILL bounce every nav to `/login` (server-side
  rejected). Don't loop retrying injection — if the first inject lands on the login form, go
  straight to `login.py --force` (fresh OTP), re-inject, and it works. login.py's liveness probe
  can pass on a session Tekion has already invalidated.
- **Bin Report Qty is shown POSITIVE (magnitude); Part Details Bin Details applies the sign.** Same
  number — don't think they contradict. The -16 on Part Details is the stronger exhibit.
- **Don't blame auto-replenishment.** It's working. The cause is the phantom bin. Saying "this
  stemmed from replenishment issues" in a vendor letter invites the rebuttal "then it's your system."
- **Physical inventory "missing" it may not be an error** — DISPROVEN for the 2025 SCT count:
  the crew DID count 5005 (found 9), but the variance ran against a masked/unsigned expected qty
  ("expected 4" vs ledger -16) and Tekion posted total-only. See the "2025 SCT PHYSICAL" section —
  the count launders ghosts, it doesn't skip them.
- **Read-only.** Never post a bin/inventory adjustment without Joe's explicit go. Joe/Glade post.
