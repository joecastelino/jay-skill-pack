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
  - negative on-hand
  - ghost bin
  - cdk migration bin
  - 5005
  - phantom bin balance
  - why is on hand negative
  - auto replenishment not working
  - bin consolidation
  - physical inventory missed
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

## DAILY DIFF TRIAGE RULES (verified on live run 2026-07-23)

When diffing 5000-section snapshots, classify each qty change by the part's bin topology
BEFORE flagging it as a missed transfer:
- **`multipleBinNumbers: []` on the generate hit = the 5000s bin IS the part's ONLY (and
  therefore Primary) bin** → a qty DROP there is a normal sale relieving its own primary.
  No transfer needed, don't flag. (E.g. 08887-02809 grease lives only in 5006.) This is the
  fast roster-level version of the "11 SCT parts have a 5000s bin as PRIMARY" exception.
- **⚠️ BUT a POPULATED `multipleBinNumbers` does NOT prove the 5000s bin is non-primary
  (verified 2026-07-28):** 87139-YZZ93 dropped 45→29 in bin 5007 with
  `multipleBinNumbers=['2422','4111','TXM']` — yet 5007 WAS its Primary (Part Details showed
  "5007 … Primary Bin"), so the drop was a normal sale, NOT a missed transfer. The generate
  hit never says WHICH bin is primary. Before flagging any 5000s qty DROP as needing a
  5000s→2420 transfer, confirm primacy via the part's rendered Bin Details (headless
  Playwright + storage_state, read `document.body.innerText` slice at `lastIndexOf('Bin
  Details')` — the primary bin row carries the literal text "Primary Bin").
- **Qty INCREASE on a NON-primary 5000s bin = someone posted a redistribution/transfer INTO
  it** (sales can't touch non-primary). Usually an intentional back-counter restock or a
  per-sale transfer landing — flag as "verify matches shelf", not as an alarm. (2026-07-28:
  17801-F0020 5006 10→11, Primary 2417 confirmed separately.)
- Qty change on a bin that HAS other bins (esp. one that includes 2420/24xx) = non-primary
  move → someone posted a redistribution/adjustment, or it's drift. Flag for verification.
- **A negative that DEEPENS on a non-primary bin (e.g. -7→-8) = smoking gun** — a bin-level
  decrement happened without stock; always flag loudly.
- **⚠️ A SPECIAL-PURPOSE bin (TXM/SOLD/SP-ORD/RETURNSHELF) can itself BE a part's Primary
  Bin (verified 2026-08-05)** — don't assume "special bin = always ignore, always non-primary."
  Example: 87139-YZZ09 had Primary=TXM (qty 0) and non-primary 5007 (a watched 5000-section
  bin) deepening -15→-17. This is STILL the smoking-gun case above (deepening negative on a
  non-primary bin) — flag it — but it is NOT a standard "5000s→2420 front/back-counter drift"
  (the Primary isn't a front-counter bin like 2420/24xx, it's a process bin), so report it as
  "verify/investigate — atypical Primary" rather than "needs 5000s→2420 transfer." Always
  confirm via rendered Bin Details which bin is actually Primary before writing the flag
  reason — don't infer it from bin number or class alone.
- **⚠️ A 5000s BIN CAN BE PRIMARY WHILE ITS COMPANION (non-tracked) BIN GOES NEGATIVE
  SIMULTANEOUSLY (verified 2026-08-11, SCT 17801-F4010)** — when the snapshot diff shows a
  5000s bin qty DROP and that bin's own Bin Details confirms it IS Primary (looks like a clean
  normal sale, matching the "multipleBinNumbers empty/is-primary → normal sale" rule), don't
  stop there if a companion bin exists in `multipleBinNumbers`. Case: bin 5006 (Primary) dropped
  4→2 — looked like an ordinary 2-unit sale — but live Bin Details showed the OTHER bin (2418,
  not itself in the tracked 5000-section roster so the diff never surfaces it on its own) had
  gone from a positive/zero balance to **-2** in the same window, and Total Inventory Qty net
  landed at 0 (not the 2 you'd expect from a simple primary decrement). The companion bin's
  negative is invisible to the snapshot diff (only 5000-section bins are snapshotted) — it only
  surfaces when you pull live Bin Details on a flagged part. **Rule: any time a 5000s bin's OWN
  qty change is being explained away as "it's Primary, normal sale," still open the part's live
  Bin Details and check whether a companion/non-tracked bin flipped negative in step — if so,
  flag it as a genuine anomaly (possible mis-attributed transfer or drift), not a clean sale.**
- **MULTI-DAY ESCALATION — track a smoking-gun negative across runs, don't re-flag it as
  fresh each day.** 87139-YZZ09 (bin 5007, Primary=TXM) has been deepening for 3+ consecutive
  daily runs and counting: -15→-17 (2026-08-05), -17→-18 (2026-08-06), -18→-19 (2026-08-07),
  with zero corrective adjustment posted in between. Before writing the day's flag, check the
  PREVIOUS 1-2 snapshot files for the same (bin, partNumber) trend, not just yesterday vs today.
  If it's been open 2+ days with no fix, escalate the report language ("day N of continuing
  drift — recommend Joe/Ronald look directly" instead of a fresh-sounding "-18→-19 ⚠️") so it
  doesn't get lost as noise in a daily list.
- **17801-F4010 (bin 5006/companion 2418) is a RECURRING companion-bin-negative case, not a
  one-off** — first documented 2026-08-11 (5006 Primary dropped 4→2, companion 2418 flipped to
  -2), and the SAME exact pattern recurred 2026-08-14 (5006 Primary 6→4, companion 2418 still
  at -2, Total Inventory Qty=2 not 4). Since 2418 isn't a tracked 5000-section bin, its negative
  never shows in the snapshot diff on its own — you only catch it by pulling live Bin Details on
  this specific part whenever 5006 changes. Treat this part like the MULTI-DAY ESCALATION rule
  above: check its live Bin Details EVERY run regardless of whether 5006's diff alone looks like
  a clean sale, and note recurrence count in the report rather than describing it as new each time.
- **NEW MULTI-DAY ESCALATION TRACKED (2026-08-15): 31532 (LOW VISCOSITY FULL SYN. ATF), bin
  5001, Primary = SP-ORD (qty 0), non-primary companions 2615 (qty 0) and 5001 itself.** Flat
  at -20 for the entire month of July into early Aug, then deepened -20→-25 on 2026-08-14, and
  -25→-29 on 2026-08-15 — 2 consecutive days of deepening after a long flat period. Same
  pattern class as 87139-YZZ09/17801-F4010/04500-1: check this part's full multi-day history
  on every future run (not just yesterday-vs-today) and report it as "day N of continuing
  drift," not a fresh-sounding delta. NOTE the Primary here is SP-ORD, not a front-counter bin
  like 2420/24xx — this is NOT a 5000s→front-counter transfer case, it's a standalone
  escalating negative needing direct investigation, same framing as 04500-1.
- **NEW MULTI-DAY ESCALATION TRACKED (2026-08-17): 87139-42040 (ELEMENT, AIR REFINER), bin
  5005, Primary = 2424 (qty 0), companion = 5005 only.** Steadily deepening for 2+ weeks:
  -8 flat 8/3–8/10 → -9 (8/11–8/13) → -10 (8/14–8/16) → -11 (8/17). Same pattern class as
  87139-YZZ09/17801-F4010/31532/04500-1 — check this part's full multi-day history every
  future run (not just yesterday-vs-today) and report as "day N of continuing drift."
- **STANDALONE SINGLE-BIN NEGATIVE = a DIFFERENT case from the back-counter transfer scenario
  — don't apply transfer logic, but DO keep escalating it (verified 2026-08-13, SCT
  04500-1/PLUG&GASKET, bin 5005).** When `multipleBinNumbers: []` AND the bin has no companion
  at all (the part lives in exactly ONE bin, period — not "empty list but IS primary with
  other listed bins", genuinely single-bin), a qty DROP into deeper negative is NOT a normal
  sale relieving primary stock (there's no positive stock to relieve — it's already negative)
  and it's NOT a 5000s→2420 back-counter/front-counter split issue (nothing to transfer, no
  second bin exists). This is a THIRD, separate finding: a receiving/consumption tracking gap
  on that one part. Still check its full history across all available snapshots (not just
  yesterday) — 04500-1 was found to have deepened steadily for 6+ weeks (-69 on 2026-07-04 →
  -111 on 2026-08-13, worsening almost every run) with zero correction. Report it explicitly
  as "outside the 5000s-transfer scope, standalone negative, N weeks open, recommend direct
  investigation" — don't fold it into the transfer-needed bucket and don't drop it just
  because no transfer applies.
- **SAME-DAY LIVE EDIT ATTRIBUTION** — if Jay executed a live Edit-Part redistribution on a
  part earlier the same day (see FIX PATHS / LIVE EDIT-PART REDISTRIBUTION MECHANICS above),
  a diff on that exact part in the SAME day's watchdog run is very likely a residual/expected
  effect of that edit, not new organic drift. Cross-check the day's redistribution log
  (`sct-bin-redistribution-log.csv`) for the part number before reporting the diff as an
  unexplained change — note it as "expected residual of today's redistribution," not a fresh
  flag needing action. Example: 17801-0P100 5005 8→7 the same day as its live Edit-Part
  consolidate/split (2026-08-07).
- **FAST TELL for a companion-bin negative: compare the 5000s bin's own qty against "Total
  Inventory Qty" in the rendered Bin Details (verified 2026-08-18).** You don't have to eyeball
  every bin row — if the tracked bin shows e.g. 6 but Total Inventory Qty reads 4, the missing 2
  is sitting NEGATIVE in a companion bin that the snapshot diff cannot see. Conversely when they
  agree (or the sum of visible rows reconciles cleanly, e.g. 87139-YZZ93: 5007=21 + 4111=30 +
  TXM/2422=0 → Total 51 ✓), the change is a clean ordinary movement and needs no flag. Make this
  the first check on every part you open, before reasoning about which bin is Primary.
- **A qty INCREASE on a 5000s bin that IS Primary is a restock, not a sale — but still open the
  part** (2026-08-18, 17801-F4010 5006 2→6, recurrence #3 of the companion case): the increase
  itself is benign, yet the stale companion negative (2418 = −2) was still sitting there
  uncorrected from prior runs. Report the recurrence count and the unresolved companion, not the
  increase.
- **STATUS UPDATE 2026-09-01 — THE 8/31 CORRECTIONS HELD; QUIETEST RUN ON RECORD (1 diff / 174 rows).**
  Both 8/31 corrections are STABLE one day later: **87139-YZZ83** 5007 held **+50** (TXM Primary 0 +
  **4119**=85 + 5007=50 → Total 135 ✓ — note 4119 drew down 100→85, ordinary sales off a non-tracked
  bin, Primary is TXM at 0 so nothing relieved there); **87139-YZZ09** 5007 held **+10** (TXM Primary
  10 + 4107=2 + 5007=10 → Total 22 ✓). **17801-F4010 CONFIRMED RESOLVED (2nd clean day)** — 5006
  Primary=1 + 2417=1 → Total 2 ✓, no companion negative anywhere; the case that ran 14 recurrences
  8/11–8/30 is closed. Stop opening it every run unless it reappears in a diff. Negatives held at
  **24** with the identical per-bin mix as 8/31 (5005:11, 5007:5, 5000:2, 5004:2, 5006:2, 5001:1,
  5002:1). Still open/flat: **04500-1** −29 (4th flat day, single-bin 5005 IS Primary, outside
  transfer scope, On Order 1), **87139-42040** −12 (**13th** flat day, Primary 2424), **31532** −58
  (7th flat day in the bin, BUT SP-ORD Primary drew 24→**21** and Total Inventory Qty slid −34→**−37**
  — the bin-vs-Total divergence is still widening even though the diff shows nothing; this is the one
  item that keeps moving). ONLY diff in 174 rows: 87139-YZZ93 5007 32→25 (Primary; +4111=30 → Total
  55 ✓ benign high-churn). 66/174 with 24h activity. Session state: :9223 was on
  **`/login?redirectTo=/home`** (single tab, 13h-old storage-state) → `login.py --force` clean FIRST
  TRY (~30s, LOGGED_IN) → cookies added:5 → `localStorage.clear()` → **21/21** keys verified →
  `/navigate /home` welcome:true on BC/1251 → dealer pill x1130,y32 → SCT leaf x1074,y344 → 876 in ONE
  poll. 7/7 bins tagged+clicked first try via "500" filter + `data-jaybin`, zero scrolling, **Apply at
  x314,y689**, 4 pages clean.
- **STATUS UPDATE 2026-08-31 — BIGGEST CORRECTION DAY EVER RECORDED: bin 5007's two deepest
  negatives BOTH cleared, and the 17801-F4010 companion case RESOLVED after 20 days.**
  **87139-YZZ83** (5007): **−93 → +50** (+143 swing) — was the single deepest negative on the board;
  live Bin Details now reconciles clean (TXM Primary 0 + **4119**=100 + 5007=50 → Total 150 ✓).
  NOTE its companion roster CHANGED from `['2422','TXM','4115']` to `['TXM','4119']` — a bin
  re-map accompanied the correction, so don't diff companions blindly. **87139-YZZ09** (5007,
  Primary=TXM): **−22 → +10** (+32) after **23 consecutive flat days** — TXM Primary now 10,
  4107=2, 5007=10, Total 22 ✓. Both were tracked multi-day escalations; both are now positive and
  reconcile. **17801-F4010 (recurrence #14 → RESOLVED):** 5006 4→1 and the stale companion **2418
  = −2 is GONE** — the part now lists bins 5006 (Primary, 1) + **2417** (1), Total 2 ✓. The
  companion negative that sat unmoved since 8/11 was corrected AND the companion bin itself changed
  2418→2417. Stop treating this as an open recurrence unless 2418/2417 goes negative again.
  Still open/flat: **04500-1** −29 (2nd flat day, single-bin 5005 IS Primary, still outside transfer
  scope), **31532** −58 (6th flat day; SP-ORD Primary 28→**24**, Total Inventory Qty **−34** —
  bin-vs-Total divergence persists), **87139-42040** −12 (12th flat day, Primary 2424=0).
  Negatives dropped **26 → 24** — first change in the count after 13 identical days; per-bin mix
  now 5005:11, **5007:5** (was 7), 5000:2, 5004:2, 5006:2, 5001:1, 5002:1. 5007 now owns only 2 of
  the 6 deepest (00475-1BF03 −69, 17801-YZZ10 −51) instead of 4 — the scoped-Bin-Spot-Check
  recommendation for 5007 is partially actioned but NOT complete. Benign diffs: 87139-YZZ93 5007
  41→32 (Primary, +4111=30 → Total 62 ✓); 17801-21040 5005 1→0 (Primary 2419=11 → Total 11 ✓).
  **LESSON: when a tracked escalation CORRECTS, verify via live Bin Details before celebrating —
  the generate hit's unsigned magnitude makes a −93→+50 flip look identical to a −93→−50 deepening.**
  Session state: :9223 alive/authenticated, single tab on `/dse-v2/appointments/scheduler/month`,
  parked on **BC/1251** — recovery was just `/navigate /home` (welcome:true, NO login.py) → dealer
  pill x1130,y32 → SCT leaf x1074,y344 → 876 in ONE 4s poll (~15s). 7/7 bins tagged+clicked first
  try via "500" filter + `data-jaybin`, zero scrolling, Apply at x306,y689, Next at x865,y686,
  4 pages clean, 5 diffs / 174 rows, 65/174 with 24h activity.
- **STATUS UPDATE 2026-08-30 — WHOLE BOARD FLAT; 04500-1 regression finally PAUSED.** **04500-1**
  (5005, single-bin, 5005 IS Primary) held at **−29** — first non-worsening day after 5 straight
  deepening days post-8/25 correction; report as "paused, still −29, not fixed." **31532** (5001)
  FLAT at −58 for a 5th day, but SP-ORD Primary dropped **28 → 24** (another sale off Primary) →
  Total Inventory Qty **−34**. Bin-vs-Total divergence persists. **17801-F4010 recurrence #14** —
  5006 flat at 4 (Primary), companion 2418 STILL −2, Total **2** vs bin 4; unmoved **20 days**
  since 8/11, and again NO diff on 5006 (4th silent-diff catch — the bin-vs-Total tell was the
  only signal). Flat: 87139-42040 −12 (11th flat day), 87139-YZZ09 −22 (day 23 flat). ONLY ONE
  diff in 174 rows: 87139-YZZ93 5007 53→41 reconciled clean (41 Primary + 4111=30 + TXM/2422=0 →
  Total 71 ✓). Negatives held at **26 for a 13th consecutive day** with the IDENTICAL per-bin mix
  (5000:2, 5001:1, 5002:1, 5004:2, 5005:11, 5006:2, 5007:7); 5007 still owns 4 of the 6 deepest.
  Session state: :9223 was on **`/login?redirectTo=/home`** (single tab, 13h-old storage-state) →
  `login.py --force` succeeded FIRST TRY (~35s, LOGGED_IN) → cookies added:5 → `localStorage.clear()`
  → **21/21** keys verified → `/navigate /home` welcome:true on BC/1251 → dealer pill x1130,y32 →
  SCT leaf x1074,y344 → 876 in ONE 4s poll. Restore ~60s, zero retries. 7/7 bins tagged+clicked
  first try via "500" filter + `data-jaybin`, zero scrolling, Apply at x306,y689, Next at x865,y686,
  4 pages clean, 57/174 with 24h activity.
- **STATUS UPDATE 2026-08-29 — 04500-1 REGRESSION DAY 5 (uninterrupted).** **04500-1** (5005, single-bin,
  5005 IS Primary): −28 → **−29**. Five consecutive deepening days since the 8/25 +97 correction
  (−23 → −26 → −27 → −28 → −29) — the correction has now been fully invalidated as a fix; frame as
  "regression day 5, off-book consumption never stopped, recommend direct human investigation."
  **31532** (5001) FLAT at −58 for a 4th day; SP-ORD Primary held at 28 (no refill/sale today), Total
  Inventory Qty **−30**. **17801-F4010 recurrence #13** — 5006 flat at 4 (Primary), companion 2418 STILL
  −2, Total Inventory Qty **2** vs bin 4; unmoved **19 days** since 8/11 (NO diff on 5006 today — the
  bin-vs-Total tell was the only catch, 3rd silent-diff catch; keep opening this part every run).
  Flat: 87139-42040 −12 (10th flat day), 87139-YZZ09 −22 (day 22 flat). 87139-YZZ93 5007 24→**53** (big
  restock, largest single-day jump in the tracked window) reconciled clean (53 Primary + 4111=30 +
  TXM/2422=0 → Total 83 ✓). Negatives held at **26 for a 12th consecutive day** with the IDENTICAL
  per-bin mix every single day (5000:2, 5001:1, 5002:1, 5004:2, 5005:11, 5006:2, 5007:7) — 5007 still
  owns 4 of the 6 deepest (−235 combined). Session state: :9223 was on **`/login?redirectTo=/home`**
  (dealer null, 21 keys) with a 13-hour-old storage-state → `login.py --force` succeeded FIRST TRY
  (~40s, LOGGED_IN) → cookies added:5 → **21/21** keys length-verified → `/navigate /home` welcome:true
  on BC/1251 → dealer pill x1130,y32 → SCT leaf x1074,y344 → 876 in ONE 4s poll. Whole restore ~70s,
  zero retries. 7/7 bins tagged+clicked first try via "500" filter + `data-jaybin`, zero scrolling,
  Apply at x306,y689, Next at x880,y686, 4 pages clean, 2 diffs / 174 rows, 61/174 with 24h activity.
  **NEW TIP: clear localStorage before injecting** (`localStorage.clear()` after `/navigate /login`) —
  the dead session left 21 stale keys behind; clearing first guarantees the 21/21 verify is meaningful.
- **STATUS UPDATE 2026-08-28 — 04500-1 REGRESSION DAY 4; 31532 Primary REFILLED again.**
  **04500-1** (5005, single-bin, 5005 IS Primary): −27 → **−28**. Four consecutive deepening days since
  the 8/25 +97 correction (−23 → −26 → −27 → −28). The correction demonstrably did not hold; frame as
  "regression day 4, underlying off-book consumption never stopped." On Order = 1. **31532** (5001) FLAT
  at −58 for a 3rd day, but its SP-ORD Primary went **28 → 32** (refilled again after yesterday's sale);
  Total Inventory Qty **−26**. The bin-vs-Total divergence persists — stock keeps cycling through SP-ORD
  while the −58 in 5001 is never touched. **17801-F4010 recurrence #12** — 5006 dropped 6→4 (sale off its
  own Primary), companion 2418 STILL −2, Total Inventory Qty **2** vs bin 4; unmoved **18 days** since
  8/11. Flat: 87139-42040 −12 (9th flat day), 87139-YZZ09 −22 (day 21 flat). 87139-YZZ93 5007 36→24
  reconciled clean (24 Primary + 4111=30 → Total 54 ✓). Negatives held at **26 for an 11th consecutive
  day** with the IDENTICAL per-bin mix every single day (5000:2, 5001:1, 5002:1, 5004:2, 5005:11, 5006:2,
  5007:7) — 5007 still owns 4 of the 6 deepest (−235 combined). Session state: :9223 alive/authenticated
  but bound to a **ServiceNow KB tab** (`tekion.service-now.com/sp/en?id=index`, single tab) and parked on
  **BC/1251** — recovery was simply `/navigate /home` (welcome:true, no `/pages/select` needed since only
  one tab existed, no login.py) → dealer pill x1130,y32 → SCT leaf x1074,y344 → 876 in ONE 4s poll (~15s
  total). 7/7 bins tagged+clicked first try via "500" filter + `data-jaybin`, zero scrolling, Apply at
  x306,y689, Next at x880,y686, 4 pages clean, 3 diffs / 174 rows, 54/174 with 24h activity.
- **STATUS UPDATE 2026-08-27 — 04500-1 REGRESSION IS NOW THE HEADLINE (3rd straight day post-correction).**
  **04500-1** (5005, single-bin, 5005 IS Primary): −26 → **−27**. Timeline: −120 (8/24) → +97 correction
  landed 8/25 (−23) → −26 (8/26) → −27 (8/27). Three consecutive deepening days immediately after the
  first correction in 7 weeks — the fix was cosmetic, the underlying off-book consumption never stopped.
  Frame this as "correction failed to hold," not "improving." **31532** (5001) FLAT at −58 (2nd flat day)
  but its SP-ORD Primary dropped **32 → 28** (a sale off Primary) while 5001 stayed −58; Total Inventory
  Qty now **−30**. The bin-vs-Total divergence noted 8/26 persists — someone is selling off the received
  SP-ORD stock while the 5001 negative sits untouched. **17801-F4010 recurrence #11** — 5006 flat at 6
  (Primary), companion 2418 STILL −2, Total Inventory Qty=**4** vs bin 6; unmoved **17 days** since 8/11
  and again NO diff on 5006 (bin-vs-Total tell only). Flat: 87139-42040 −12 (8th flat day), 87139-YZZ09
  −22 (day 20 flat). 87139-YZZ93 5007 42→36 reconciled clean (36 Primary + 4111=30 → Total 66 ✓).
  Negatives held at **26 for a 10th consecutive day** with an IDENTICAL per-bin mix every single day
  (5000:2, 5001:1, 5002:1, 5004:2, 5005:11, 5006:2, 5007:7) — 5007 still owns 4 of the 6 deepest (−235
  combined). Session state: :9223 alive/authenticated, single clean tab on `/service/settings/ro-settings`,
  parked on **TL/1092** — recovery was `/navigate /home` (welcome:true, no login.py) → dealer pill
  x1130,y32 → SCT leaf x1074,y344 → 876 in ONE 4s poll (~15s total). 7/7 bins tagged+clicked first try via
  "500" filter + `data-jaybin`, zero scrolling, Apply at x306,y689, 4 pages clean, 2 diffs / 174 rows,
  67/174 with 24h activity.
- **STATUS UPDATE 2026-08-26 — TWO ESCALATIONS RESUMED DEEPENING + a NEW wrinkle on 31532.**
  **04500-1 (5005, single-bin, 5005 IS Primary) RESUMED: −23 → −26** — only ONE day after the +97
  correction landed on 8/25. The correction did NOT fix the underlying process; the part is
  consuming/receiving off-book again immediately. Report as "corrected 8/25, already regressing."
  **31532 (5001) RESUMED after 7 flat days: −56 → −58** — AND its Primary changed character: SP-ORD
  went from qty **0** (its state for the whole prior escalation) to **32**, so Total Inventory Qty is
  now **−26** rather than equal to the bin (−58). Someone received 32 into the SP-ORD Primary while
  the 5001 negative kept growing — the receipt masks the total but does not touch the bin. Watch for
  the bin-vs-Total divergence here now (it previously matched). **17801-F4010 recurrence #10** — 5006
  rose 4→6 (restock off its own Primary), companion 2418 STILL −2, Total Inventory Qty=**4** vs bin 6;
  unmoved 16 days since 8/11. Flat: 87139-42040 −12 (7th flat), 87139-YZZ09 −22 (day 19 flat).
  87139-YZZ93 5007 32→42 reconciled clean (42+30=72 ✓, Primary=5007). Negatives held at **26 for a
  9th consecutive day**; bin mix 5005=11 rows, 5007=7 and still owns 4 of the 6 deepest. Session
  state: :9223 alive/authenticated, bound to a stale `/ro/opcode/edit/UCRBRAKE` tab + 1 extra tab,
  parked on **BC/1251** — recovery was `/pages/close` index 1 → `/navigate /home` (welcome:true, no
  login.py) → dealer pill x1130,y32 → SCT leaf x1095,y344 → 876 in ONE 4s poll (~15s total). 7/7 bins
  tagged+clicked first try via "500" filter + `data-jaybin`, zero scrolling, 4 pages clean, 5 diffs
  out of 174 rows, 73/174 with 24h activity.
- **STATUS UPDATE 2026-08-25 — FIRST REAL CORRECTION IN 7+ WEEKS:** **04500-1 (PLUG&GASKET, bin 5005)
  jumped −120 → −23, a +97 correction** — someone finally posted an adjustment on the longest-running
  standalone negative (open since 7/04 at −69, worsened to −120 by 8/24). NOT fully resolved (still −23),
  so keep tracking, but report the improvement as the headline rather than re-flagging it as drift. This
  is the first evidence that daily escalation language actually got actioned — when a tracked escalation
  IMPROVES, lead with it and note the delta + remaining balance. Other escalations flat: 31532 −56 (7th
  flat day), 87139-42040 −12 (6th flat), 87139-YZZ09 −22 (day 18 flat). **17801-F4010 recurrence #9** —
  5006 rose 2→4 (restock off its own Primary) but companion 2418 STILL −2 and Total Inventory Qty=**2**
  vs bin 4; unmoved 15 days since 8/11. 87139-YZZ93 5007 34→32 reconciled clean (32+30=62 ✓, Primary=5007).
  77144-04010 5001 0→1 benign (5001 IS Primary, RC1=0, Total 1 ✓). Negatives held at **26 for an 8th
  consecutive day** (composition improved though — 04500-1 no longer in the top 4); bin mix 5005=11 rows,
  5007=7 and still owns 4 of the 6 deepest. Session state: :9223 alive/authenticated but bound to an
  `about:blank` tab with 3 stale tabs (2 on `/login`, 1 ServiceNow KB) and parked on **TL/1092** — fix was
  `/pages/close` the 3 stale tabs → `/navigate /home` (welcome:true, no login.py needed) → dealer pill
  x1130,y32 → SCT leaf x1095,y346 → 876 in ONE 4s poll. Total recovery ~20s. 7/7 bins tagged+clicked first
  try via the "500" filter + `data-jaybin` tagging, zero scrolling, 4 pages paginated clean.
- **STATUS UPDATE 2026-08-24:** 2 diffs / 174 rows and **ALL FIVE tracked escalations FLAT** — 31532 −56
  (6th flat day), 04500-1 −120 (flat after 8/23's resume), 87139-42040 −12 (5th flat), 87139-YZZ09 −22
  (day 17). **17801-F4010 recurrence #8** — 5006=2 (Primary) vs Total Inventory Qty=**0**, companion 2418
  still −2, unmoved 14 days since 8/11; AGAIN no diff on 5006, only the bin-vs-Total tell caught it (2nd
  consecutive silent-diff catch — this part MUST be opened every run regardless of diff). Both diffs benign:
  08887-02919 FC GREASE 5006 3→4 restock (5006 IS Primary, sole bin, Total 4 ✓); 87139-YZZ93 5007 42→34
  reconciled clean (34+30=64 ✓, Primary=5007). Negatives held at **26 for a 7th consecutive day**; bin mix
  5005=11 rows, 5007=7 and still owns 4 of the 6 deepest. Session state: :9223 alive/authenticated but
  parked on VC/1891 `/parts/sales-order` — NO login.py needed, just `/navigate /home` → dealer pill
  x1130,y32 → SCT leaf x1095,y287 → 876 (~25s). **NEW PITFALL: the checkbox-tagging `/eval` can return
  HTTP 500 if it uses a broad `document.querySelectorAll('*')` + spread/arrow-heavy payload** — rewrite it
  as a plain `function(){}` with a NARROW selector
  (`[class*="binNodeLabel"],[class*="customCheckBoxTreeNodeDiv"] span/div`) and it succeeds instantly. 7/7
  bins tagged+clicked first try, no scrolling.
- **STATUS UPDATE 2026-08-23:** 2 diffs / 174 rows. **04500-1 RESUMED deepening −119→−120 after 3 flat
  days** (7+ weeks open, standalone single-bin, `multipleBinNumbers: []`, 5005 IS its Primary — outside
  transfer scope). 31532 flat −56 (**5th** flat day), 87139-42040 flat −12 (4th), 87139-YZZ09 flat −22
  (day 16). **17801-F4010 recurrence #7** — 5006=2 (Primary) vs Total Inventory Qty=**0**, companion 2418
  still −2, unmoved since 8/11 (13 days); again NO diff on 5006 itself, only the bin-vs-Total tell caught
  it. 87139-YZZ93 5007 46→42 reconciled clean (42+30=72 ✓, Primary=5007). Negatives held at **26 for a 6th
  consecutive day**; bin mix 5005=11 rows, 5007=7 and still owns 4 of the 6 deepest. Session state this
  run: :9223 was on `/login` with a 24h-old storage-state → `login.py --force` (clean first try, LOGGED_IN)
  → cookies added:5 → **22/22** keys length-verified → `/navigate /home` welcome:true on BC/1251 → dealer
  pill x1130,y32 → SCT leaf x1074,y346 → 876. Whole restore ~90s, zero retries. The `data-jaybin` tagging +
  "Search Bin Names"=500 filter selected all 7 bins first try with no scrolling.
- **STATUS UPDATE 2026-08-22:** Quietest run to date — **ONE diff out of 174 rows**, and ALL FIVE tracked
  escalations flat again: 31532 −56 (4th flat day), 04500-1 −119 (3rd flat), 87139-42040 −12 (3rd flat),
  87139-YZZ09 −22 (day 15 flat), 17801-F4010 recurrence **#6** (5006=2 vs Total Inventory Qty=**0**,
  companion 2418 still −2 and unmoved since 8/11 — the bin-vs-Total tell fired with NO diff on 5006 at
  all, so keep opening this part every run even on silent days). 87139-YZZ93 5007 21→46 reconciled clean
  (46+30=76 ✓, Primary confirmed = 5007). Negatives held at 26 for a **5th** consecutive day; 5005=11 rows,
  5007=7 rows and still owns 4 of the 6 deepest (−235 units combined across YZZ83/00475-1BF03/17801-YZZ10/
  YZZ09). When the whole board goes flat multiple days running, LEAD with that as the finding and note the
  streak length — and keep re-stating the two standing recommendations (scoped Bin Spot Check on 5007; the
  2-unit 17801-F4010/2418 fix) with their AGE, since an aging unactioned recommendation is the real signal.
- **STATUS UPDATE 2026-08-21:** ALL FIVE tracked escalations FLAT — 31532 −56 (3rd flat day, acceleration
  confirmed broken), 04500-1 −119 (2nd flat day, first pause in ~7 weeks), 87139-42040 −12 (2nd flat),
  87139-YZZ09 −22 (day 14 flat), 17801-F4010 companion 2418 still −2 (recurrence #5: bin 5006=2 vs Total
  Inventory Qty=0 — the bin-vs-Total tell fired again). 87139-YZZ93 5007 29→21 reconciled clean (21+30=51 ✓).
  Negatives held at 26 for a 4th consecutive day; 5005=11 rows, 5007=7 rows and still owns 4 of the 6
  deepest. Only 2 diffs out of 174 rows. When every tracked item goes flat in the same run, SAY SO as the
  headline finding — a first-quiet-day-in-weeks is itself signal, not an empty report.
- **STATUS UPDATE 2026-08-20:** 31532 **BROKE ITS ACCELERATION — flat at −56** (first non-worsening
  day after 6 straight); 04500-1 −117→**−119**; 87139-42040 −11→**−12** (resumed after 3 flat days);
  87139-YZZ09 **flat −22 for 13 days**; 17801-F4010 5006 unchanged at 4 but companion 2418 STILL −2
  (Total 2 vs bin 4 — the bin-vs-Total tell still fires even with no diff, so open it every run even
  when the diff is silent); 87139-YZZ93 5007 41→29 reconciled clean (29+30=59 ✓, benign churn).
  Negatives held at 26 for a 3rd consecutive day; 5005 = 11 rows, 5007 = 7 rows and still owns 4 of
  the 6 deepest. Only 3 diffs total out of 174 rows — a very quiet day is normal, don't hunt for more.
- **STATUS OF TRACKED MULTI-DAY ESCALATIONS (as of 2026-08-19) — read before re-deriving history:**
  - **31532** (5001, Primary=SP-ORD qty 0, companion 2615 qty 0): −20 flat July→8/13 → −25
    (8/14) → −29 (8/15–8/17) → −43 (8/18) → **−56 (8/19, −13 more)**. Day 6 and STILL
    ACCELERATING — −36 units in 6 days after ~6 weeks flat, with 8/18+8/19 alone = −27. Total
    Inventory Qty == the bin (−56); On Order = 0, stocking ACTIVE. Not a transfer case (Primary
    is a process bin). This is the fastest-deteriorating item on the board — escalate hard and
    recommend direct human investigation, it is outrunning the daily report.
  - **04500-1** (5005, single-bin, 5005 IS Primary): −69 (7/04) → −105 (8/03) → −114 (8/17) →
    −116 (8/18) → **−117 (8/19)**. 7+ weeks open, standalone negative, outside transfer scope.
  - **17801-F4010** (5006 Primary, companion 2418): recurrences 8/11, 8/14, 8/18, **8/19 (#4)**.
    2418 stuck at −2 across ALL FOUR; Total Inventory Qty keeps reading 2 less than bin 5006
    (8/19: 5006=4, Total=2). The 5006 qty itself oscillates 2↔6 (sales + restocks off Primary),
    which is why only the bin-vs-Total tell catches it — never the 5006 delta alone.
  - **87139-YZZ09** (5007, Primary=TXM): deepened −14→−22 through 8/08, then **flat at −22 for 12
    consecutive days** (8/08–8/19). Stable but never corrected — report as "open, not worsening"
    rather than re-flagging as fresh drift.
  - **87139-42040** (5005, Primary=2424): −8 → −11 over two weeks, **flat at −11 since 8/17**.
  - **87139-YZZ93** (5007 IS Primary, companions 4111/2422/TXM) is a KNOWN HIGH-CHURN part, not
    an escalation: it swings hard almost daily (8/06→8/19: 27,17,8,2,0,27,50,36,25,52,47,32,21,41)
    from ordinary sales off Primary plus restocks. Every check so far reconciles cleanly
    (8/19: 5007=41 + 4111=30 + TXM/2422=0 → Total 71 ✓). Still open it each run (the bin-vs-Total
    tell is cheap), but expect a benign result and don't write it up as drift.
  When a tracked part goes FLAT, say so explicitly ("open N days, not worsening") — a silent
  omission reads as "fixed," and re-flagging it as new drift is noise.
- **Also surface the standing-negative TOP LIST and its bin concentration each run** — 26
  negatives across the section on BOTH 2026-08-18 and 2026-08-19, and bin **5007 held 4 of the 6
  deepest on both days** (87139-YZZ83 −93, 00475-1BF03 −69, 17801-YZZ10 −51, 87139-YZZ09 −22),
  with bin 5005 carrying the most ROWS (11 of 26, incl. 04500-1 at −117). The 5007 concentration
  is now a CONFIRMED PERSISTENT pattern, not a one-day snapshot artifact — a single bin owning
  most of the deep negatives is itself the finding (suggests a whole-shelf process problem, not
  per-part drift) and is worth recommending as a scoped Bin Spot Check target. The daily
  yesterday-vs-today diff will NEVER reveal it because those rows are flat — you must compute the
  negative roster + per-bin counts fresh from the current snapshot every run, independent of the
  diff. Cheap to do: one pass over the saved snapshot, sort ascending by onHandQuantity, and
  `Counter(bin)` the negatives.
- 65-70/175 parts having lastTransactionTime in 24h is NORMAL on a busy day — the 24h-activity
  list is a reminder roster (sales relieve Primary only), not an alarm list. Only qty
  changes/new negatives are alarms.

**SNAPSHOT FORMAT DRIFT — bin5000s-snapshots has TWO different JSON shapes across dates
(hit 2026-08-10, cost a diff-script crash):** older snapshot files store each bin as a
**LIST** of row objects (`{"5005": [{...}, {...}]}`); newer ones store each bin as a
**DICT keyed by partNumber** (`{"5005": {"04500-1": {...}, ...}}`). A diff script that
assumes one shape will throw `AttributeError: 'list' object has no attribute 'get'` (or the
reverse) depending on which day it hits. FIX: when loading ANY prior-day snapshot for
diffing, normalize first —
```python
raw = json.load(open(path))
normalized = {}
for b, v in raw.items():
    normalized[b] = {r["partNumber"]: r for r in v} if isinstance(v, list) else v
```
Always write NEW snapshots in the dict-keyed-by-partNumber shape (easier to diff), but
always normalize on READ since old files won't be back-converted.

Session-recovery note (2026-07-23): finding :9223 parked on an unexpected page (e.g.
`/core/user-setup/edit/...`) on dealer 1251 does NOT mean the session is dead — just
`/navigate /home`, confirm "Welcome back" + no Username, then dealer-pill switch to 876.
Do NOT preemptively run login.py; also never run login.py inside an execute_code script —
it can block on OTP polling and blow the 300s sandbox timeout. If needed, run it via
terminal() with its own timeout or background=true.

**`login.py --check` is a FILE-EXISTENCE check, NOT a server-side liveness probe (verified
2026-08-14)** — it returns `{"file_ok": true, "detail": "137986B all-keys"}` just from reading
the saved storage-state file's size/key-completeness. This is DIFFERENT from plain `login.py`
(no flags), which does an actual server probe and prints `ALIVE`/`REUSED`/`LOGGED_IN`. A
`--check` pass does NOT mean the saved session will authenticate — in this run the file was
`file_ok:true` yet a full cookie+21-key inject into :9223 still bounced to the login form
(stale token from the prior day). Don't waste a cycle trusting `--check`; either attempt one
real injection and verify (`/navigate /home` → check for "Welcome back"/no "Username"), or if
you already know the file is >1 day old, skip straight to `login.py --force`.

**`login.py --force` can fail/crash 1-2 times before succeeding — loop it, don't treat one
failure as a blocker (verified 2026-08-14):** attempt 1 printed `FAIL: no fresh token after
verify` (OTP/verify race); attempt 2 crashed outright with
`subprocess.TimeoutExpired: himalaya message read ... timed out after 20 seconds` (OTP email
fetch via himalaya stalled); attempt 3 succeeded cleanly (`fresh OTP received` →
`t_token exp in 129 min` → `LOGGED_IN`) in ~35s. Always run via `terminal(timeout=280)`, NEVER
inside execute_code (blocks on OTP polling, blows the 300s sandbox cap). Retry up to 3x on
FAIL/crash before escalating as a real blocker.

**Daily watchdog cron run, verified clean end-to-end 2026-08-08:** when :9223 was fully
dropped to `/login` (no salvageable session), `terminal(command="python3 login.py --force",
timeout=280)` (NOT execute_code — login.py blocks on OTP polling) got a fresh OTP + LOGGED_IN
in ~35s, then the standard cookie+21-key injection via execute_code + urllib landed
authenticated on BC/1251 ("Welcome back, Joe!"), then dealer-pill switch (x1130,y32 → popover
→ filter `dealerInfoItem_itemName` → 'Stevens Creek Toyota' leaf, that day at x1074,y346) →
verified `currentActiveDealerId==='876'`. Total time from dead session to authenticated SCT
context: ~2 minutes. The 7-bin multi-select-then-Apply-then-paginate flow (scrollIntoView each
leaf → walk-up to checkbox → /mouse click → verify `.checked` → after all 7, confirm
`querySelectorAll('input[type=checkbox]:checked').length===7` → click Apply → poll
`window.__xhr` for new `binReport/generate` entries by index, not substring match) worked
exactly as documented with zero retries needed.

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

**⚠️ RUN STANDALONE PLAYWRIGHT SCRIPTS FROM A CLEAN CWD — module shadowing will kill the import
(cost 3 wasted runs, 2026-08-22).** An ad-hoc Bin-Details script failed with
`AttributeError: module 'inspect' has no attribute 'FrameInfo'` deep inside
`playwright/_impl/_connection.py`. Cause: **`/tmp/inspect.py` exists and shadows the stdlib `inspect`
module** when cwd is `/tmp` (Python puts cwd first on `sys.path`). Running from
`/home/itadmin/tekion-reports` failed differently — some module in that directory executes on import
and dumped a whole BC Menu Sales JSON to stdout before the same traceback. Diagnose with
`python3 -c "import inspect; print(inspect.__file__)"` — if it prints anything other than the
stdlib path, your cwd is poisoned. **FIX: run from a scratch dir with no .py files**, e.g.
`mkdir -p /home/itadmin/tmp-jay && cp script.py /home/itadmin/tmp-jay/ && cd /home/itadmin/tmp-jay
&& python3 script.py`. The committed `bin5000s_daily_pull.py` is unaffected (it runs fine from
`/home/itadmin/tekion-reports`) — this bites only ad-hoc scripts written to /tmp.

**⚠️ PORTING SKILL SNIPPETS TO STANDALONE PYTHON: `page.evaluate("document.body.innerText")`
returns a PYTHON str, not a JS string.** The skill's Bin-Details recipe is written as in-browser JS
(`t.lastIndexOf('Bin Details')`), and copying it verbatim into a Playwright Python script throws
`AttributeError: 'str' object has no attribute 'lastIndexOf'`. Use `t.rfind("Bin Details")`. Same
class of bug for `indexOf`→`.find()`. Only keep `.lastIndexOf()` inside a `/eval` `js` payload.

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
1b. **USE THE "Search Bin Names" FILTER BOX FIRST (verified 2026-08-11) — huge shortcut, skip
   raw checkbox enumeration.** The bin selector panel has a text input
   `input[placeholder='Search Bin Names']` above the 400+-row checkbox list. `/type` a substring
   (e.g. `"500"`) into it and the list instantly narrows to just the matching bin numbers (e.g.
   typing "500" at SCT returned only `3500, 4500, 5000, 5001, 5002, 5004, 5005, 5006, 5007` — 9
   rows instead of 403). Read the filtered list via `document.body.innerText` (cheap) instead of
   dumping every checkbox's bounding rect (`querySelectorAll('input[type=checkbox]')` over the
   full unfiltered list returns 300+ entries and floods the response — avoid unless you've
   already filtered). After filtering, find each target bin's leaf + walk-up checkbox exactly as
   below — same mechanics, just against a tiny already-narrowed DOM.
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
   **SCROLL BECOMES UNNECESSARY when you use the "Search Bin Names" filter first (verified
   2026-08-17, all 7 SCT 5000-section bins in one pass):** after typing "500" into the filter
   box, the narrowed list (9 rows: 3500, 4500, 5000-5007) renders ENTIRELY within the visible
   panel (leaf y-coords ~382–621, no scrolling needed) — just enumerate all target leaves in
   one `/eval`, walk each up to its checkbox, and `/mouse`-click all 7 back-to-back with no
   `scrollIntoView` calls at all. Verify `document.querySelectorAll('input[type=checkbox]:checked').length===7`
   before Apply. This is faster than the scroll-per-leaf loop above — use it whenever the
   filter narrows the list enough that every target fits on-screen.
   **TAG EACH CHECKBOX WITH A `data-jaybin` ATTRIBUTE during enumeration (verified 2026-08-18,
   7/7 bins first try, zero retries).** Instead of collecting coords once and replaying them
   blind, in the SAME enumeration `/eval` do `cb.setAttribute('data-jaybin', binNumber)` on each
   walked-up checkbox. Then the click loop per bin is: re-read the live rect via
   `document.querySelector('[data-jaybin="5005"]').getBoundingClientRect()` → `/mouse` it →
   verify `document.querySelector('[data-jaybin="5005"]').checked === true` by the SAME selector.
   Why this is better than the coord-list approach: coords go stale the instant the list
   re-renders (checking one box can reflow the panel), and a stale coord silently checks the
   WRONG bin — the exact failure the "walk up to the checkbox" rule already warns about. The tag
   survives re-render, so every read/click/verify targets a provably identical element. Also skip
   any bin whose tagged checkbox already reads `checked` (idempotent re-runs). Full loop for 7
   bins took ~4s.
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

**FIRST LIVE JAY-EXECUTED REDISTRIBUTION — VERIFIED WORKING PROCEDURE (2026-08-07, SCT
17801-0P100, Joe confirmed each step live):** Joe wants a TWO-STEP redistribution, not a
direct one-shot split — (1) consolidate ALL qty into Primary first (intermediate save), THEN
(2) split out to match Joe's physical count (second save). This gives a clean checkpoint and
matches how Joe/Ronald did it by hand. Exact click-path via :9223 execute_code:

1. Navigate to `/parts/inventory/part/view/M_TMNA_<PARTNUM_no_dashes>/details`, confirm
   right dealer (`localStorage.currentActiveDealerId`) and right part in body text.
2. Read current Bin Details via `/eval` innerText slice from 2nd occurrence of 'Bin Details'
   (1st occurrence is the left-nav tab label, 2nd is the actual section header).
3. Click **Edit Part** button (`/eval` filter `innerText.trim()==='Edit Part' && tagName==='BUTTON'`
   → get rect center → `/mouse` click). Page re-renders with editable bin rows.
4. Find the 3 Qty `<input>` fields: filter `document.querySelectorAll('input')` to visible
   ones, the bin-row Qty inputs are the ones whose value matches the current per-bin qty and
   sit near y-coords of each bin row (~40px below that bin's label). Tag them with
   `setAttribute('data-jay','qty-<binname>')` for reliable `/type` targeting (index order is
   stable per page: e.g. idx 22=first bin's qty, 27=second, 32=third — but ALWAYS re-verify by
   value/position after any remount, indices shift).
5. **Step 1 (consolidate):** `/type` each tagged input — Primary bin = current TOTAL, all
   others = 0. Verify via `/eval` reading each input's `.value` AND the "Additional qty. to be
   adjusted" / "Total Inventory Qty" text (should read 0 and unchanged-total respectively).
   Screenshot + vision_analyze as a visual double-check before saving.
6. Click **Save** button (`/eval` filter `innerText.trim()==='Save' && tagName==='BUTTON'` →
   `/mouse` click). Page returns to view mode (Edit Part button reappears).
7. **VERIFY WITH TRUE REMOUNT** (per the SAVE-VERIFY TRAP lesson elsewhere in this skill) —
   `/navigate` to `/home` THEN back to the part URL, wait ~7s, re-read Bin Details. Re-reading
   the same DOM without a hard nav can show stale/unsaved values as if persisted.
8. **Step 2 (final split):** repeat steps 3-7 — click Edit Part again (page remounted, must
   re-find + re-tag inputs), `/type` the final target split (per Joe's physical count), verify
   total unchanged, screenshot+vision confirm, Save, verify with true remount again.
9. Log the move to `/home/itadmin/tekion-reports/sct-bin-redistribution-log.csv`
   (date, store, part, before/after per-bin split, method, confirmed_by, notes) — this is the
   ONLY audit trail since Case-A redistribution posts zero GL/ledger entry in Tekion itself.

Gotchas hit this run: (a) numbers can DRIFT between when a part is first flagged and when you
actually execute — always re-pull live Bin Details immediately before editing, don't trust an
earlier snapshot from the same conversation; (b) `browser_navigate`/other generic browser_*
tools open a SEPARATE unauthenticated context — do NOT use them for :9223 workflows, stick to
execute_code + the :9223 HTTP API (`/eval`, `/mouse`, `/type`, `/screenshot`) throughout.
**Confirmed 2026-08-12: `browser_vision` is ALSO one of these "other generic browser_* tools"**
— calling it to sanity-check the :9223 page (e.g. "is the bin selector visible?") returned a
convincing but FALSE "completely blank white page, no content" analysis, because it screenshots
its own separate stale/unauthenticated context, not :9223. This can wrongly suggest the :9223
session died. Never use `browser_vision`/`browser_snapshot`/`browser_click`/etc. to inspect
:9223 state — always `GET /screenshot` from the :9223 API, base64-decode to a real PNG file,
then `vision_analyze` THAT file if you want AI-vision confirmation of what :9223 is rendering.

## LIVE EDIT-PART REDISTRIBUTION MECHANICS (first live execution, verified 2026-08-07)

Joe's WORKFLOW PREFERENCE, stated explicitly (17801-0P100 case): do NOT jump straight from
the current (wrong) split to the target (physical-count) split in one Save. **ALWAYS
consolidate everything into the Primary bin FIRST (one Save), THEN redistribute out to the
target split (a second Save).** i.e. two edits, not one:
- Step 1: Primary = Total Inventory Qty, all other bins = 0. Save. Verify Total unchanged.
- Step 2: Primary / other bins = the actual physical-count split. Save. Verify Total unchanged.
This gives a clean "everything's accounted for in one place" checkpoint before splitting it
back out, and matches how Joe/Ronald did the manual 91180 fix. Always re-verify Total
Inventory Qty stayed constant after EACH save, not just at the end.

Click-path via :9223 (persistent-browser-server), on the part's `/details` page with the
correct dealer already active:
1. Confirm current state is unchanged since last read (re-slice `body.innerText` from
   `indexOf('Bin Details')` a SECOND time — the string appears twice, once in the left-nav
   list and once as the section header; use the second occurrence for the actual table).
2. Vision-locate + click **"Edit Part"** (bottom-right of the page, NOT a pencil icon in the
   header) via `/mouse` on its bounding-rect center. Screenshot afterward and vision-verify
   the Bin Details rows became editable ("Type here" placeholders appear in Shelf/Drawer, Qty
   cells become plain text inputs) before proceeding — don't assume the click worked.
3. **Enumerate ALL visible `<input>` elements** via `/eval` (`querySelectorAll('input')` with
   `offsetParent!==null`, dumping type/value/placeholder/x/y for each). The per-bin Qty inputs
   are typically at fixed relative indices once other inputs are counted (verified case: index
   22/27/32 for a 3-bin part, i.e. every 5th input starting from the first bin's Qty field —
   radio(primary) + name + shelf + drawer + qty per row). **Don't hardcode the index across
   parts** — re-enumerate per part since Stocking Details field count varies.
4. **Tag the exact 3 (or N) qty inputs with a `data-jay="qty-<binNumber>"` attribute** via
   `/eval` (`inputs[i].setAttribute('data-jay','qty-2418')` etc.) — this gives a stable
   selector for `/type` that survives re-reads. Verify each tag landed
   (`querySelector('[data-jay="qty-2418"]')` should return truthy) before typing.
5. `/type` each tagged input with its target value (`{"selector":"[data-jay='qty-2418']",
   "text":"9"}`), small `sleep(0.5)` between each, then re-read all three `.value`s to confirm
   they landed as typed (React state can silently reject a bad value).
6. **Verify Total Inventory Qty BEFORE saving** — re-slice `innerText` from
   `indexOf('Additional qty')` (this label sits right above Total Inventory Qty) and confirm
   the total is unchanged and "Additional qty. to be adjusted" reads 0. Also take a screenshot
   and `vision_analyze` it as a second confirmation layer (catches a mis-tagged input that a
   text-only check might miss) before clicking Save.
7. **Find Save** via `/eval` filtering `innerText.trim()==='Save'` + `offsetParent!==null` +
   tag is BUTTON or SPAN (there are usually 2 matching nodes — button + its inner span, same
   coords); click either via `/mouse` on the bounding-rect center.
8. STOP and get Joe's explicit go before the actual Save click on a first-ever live edit —
   narrate the exact before/after numbers and wait for confirmation, per the standing
   never-guess/confirm-before-live-write rule.

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
