---
name: tekion-bin-replenishment-picklist
description: Build and run the Tekion Bin Replenishment Pick List for multi-bin parts warehouses (pilot SCT). Detects parts where the Primary Bin is running low while overflow bins hold real stock, produces a daily warehouse-walk pick list, and (phase 2) auto-keys the system-side bin adjustment via Tekion's new Adjust Bin by Part / QOH bin adjustment features. Load whenever Joe mentions bin replenishment, sell-by-bin, primary bin stockouts, or moving stock between bins.
---

# Tekion Bin Replenishment Pick List

## Background (why this exists)
Tekion sells ONLY from a part's single **Primary Bin** (KB0012192/KB0022520/KB0026315). Jay's research got escalated to a Tekion co-founder (2026-07-02); verdict: Tekion will **NOT** build sell-by-bin. Instead they enabled two features (**live 2026-07-04**):
- **Quantity on hand bin adjustments**
- **Adjust Bin by Part**

These allow MANUAL stock moves between bins. Sales still only pull from Primary. So the operational answer is: **never let the Primary run dry while overflow bins hold stock** — a detection + replenishment loop Jay automates.

Side benefit: reduces negative-OH sales (a chunk of those happen when Primary shows 0 while stock sits in overflow and the part gets billed anyway).

## Agreed design (Joe-approved defaults, easy to change)
- **Pilot store: SCT (dealer 876)**, multi-bin parts only (~5,345 per Multiple Bin Report)
- **Trigger:** Primary bin qty < **7 days supply** (velocity-based via the bulk velocity API — see memory entry "BULK VELOCITY API"), or Primary = 0 for slow movers
- **Move qty:** top Primary up to **~30 days supply**, capped at overflow available
- **Output:** morning pick list emailed via Stacey, sorted by overflow bin location for one efficient warehouse pass. Columns: Part# · Description · From Bin → Primary Bin · Qty to Move

## Phase 1 — Detection (read-only, works on any Tekion)
1. **Per-bin quantities are NOT in the public OpenAPI** (parts-inventory:search returns only total onHandQty) and the Source Code export lists bin NAMES but not per-bin qty.
2. Read path to crack: **Edit Part → Bin Details** panel fires an internal XHR (same class as the velocity/salehistory XHRs under /api/wms/parts/u/inventory/...). Harvest at scale via in-page fetch() or XHR hook in the :9223 authenticated browser (see "BULK VELOCITY API" memory entry for the exact hook + pushState technique).
3. Join per-bin data with monthly velocity (POST /api/wms/parts/u/inventory/utility/salehistory/groupByMonth) to compute day-supply thresholds.
4. **CRITICAL FILTER: exclude ghost/dead CDK bins** (e.g. bin 5005 — frozen negatives, no shelf, zero transactions; see ghost-bin skill/report). Without this filter the pick list emits nonsense like "move -16 spark plugs from 5005". Only legit overflow bins with positive real qty qualify as a move source.
5. Test part for validation: spark plug **90080-91180** (Tekion ID `M_TMNA_9008091180`) at SCT — detail page `/parts/inventory/part/view/M_TMNA_9008091180/details`, Bin Details under Edit Part.

## Phase 2 — System-side adjustment (needs the 2026-07-04 features)
1. Once live, map the click-path + backing XHR of **Adjust Bin by Part** and **QOH bin adjustment** screens (likely under Parts → Warehouse Management, near the existing Bin Change by Part/by Bin).
2. Automation rule (Joe agreed): auto-key the system adjustment **only AFTER a human confirms the physical move** — system must always match shelf, never adjust ahead of the physical move.

## Distinct from the ghost-bin report
- Ghost-bin report (done) = one-time CLEANUP of phantom negatives stranded in dead CDK bins — nothing to physically move.
- This pick list = ONGOING replenishment of real stock from legit overflow bins into Primary. Same per-bin plumbing, different job; ghost bins are a filter here, not the subject.

## Pitfalls
- Don't promise full automation until the Bin Details per-bin-qty XHR is confirmed harvestable at scale.
- React Query caches panel data — use fresh partIds or direct in-page fetch (see velocity API entry).
- Tekion "automatic bin transfers" setting = SUPERSESSION only (Parts Settings → Auto-Replacement → Bins), NOT sale-time picking — don't confuse it with this project.
