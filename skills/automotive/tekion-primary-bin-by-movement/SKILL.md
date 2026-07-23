---
name: tekion-primary-bin-by-movement
description: Recommend which bin should be a part's PRIMARY bin based on where the movement actually happens — back counter (RO parts sales) vs front counter (Sales Orders). Glade's alternative to the "zero out every non-primary bin" policy. Use when Joe/Glade asks which counter drives a part's sales or wants primary-bin flip recommendations.
---

# Primary Bin by Majority Movement (Front vs Back Counter)

## Context / policy question
Tekion only relieves inventory from a part's ONE Primary Bin (KB0012192/0022520/0026315). Two competing fixes for dual-bin drift at SCT:
1. **Joe's end-state rule**: every non-primary bin = exactly 0 (zero strays).
2. **Glade's alternative** (this skill): flip the Primary Bin to wherever the MAJORITY of movement occurs.
As of 2026-07-07 Joe has the analysis but has NOT decided which policy wins. SCT convention: bin 2420 = FRONT counter (current primary for most), ALL 5000-section bins = BACK counter.

## Key data discovery (the crux)
The Tekion parts activity/transactions ledger tags EVERY inventory movement with a transaction type:
- **FULFILMENT** = RO parts sale = **back counter**
- **SALES_ORDER** = counter sale = **front counter**

This gives a TRUE per-part front/back split — no approximation or RO cross-referencing needed.

## Method
1. Build the roster of dual-bin parts (parts with qty in both 2420 and a 5000-section bin) — from the Multiple Bin Report / withPart:search partBinMappings (signed per-bin truth; binReport/generate is unsigned magnitudes).
2. For each part, pull last-month ledger rows; sum units by transaction type (FULFILMENT vs SALES_ORDER).
3. Majority rule: if back-counter share > 50% and current primary is the front bin → recommend FLIP (and vice versa). No movement = no basis to flip.
4. Compute impact: units/mo currently relieved from the wrong counter's bin, before vs after flips.
5. Report per part: part#, description, units by counter, share %, current primary, recommended primary, flag any part NEGATIVE in the target bin.

## June 2026 SCT baseline (for comparison on re-runs)
- 221 dual-bin parts: back 9,958 units vs front 3,571 (74% back)
- 97 flip recommendations, 49 keeps, 75 no-movement
- Drift reduction: ~9,877 → ~1,780 wrong-bin units/mo (82%)
- Top flips: 90430-12031 drain plug gasket (90% RO), 90915-YZZN1 oil filter (87% RO), BG/chem line 208RS-C/280/115/7073 (99–100% RO)
- Legit front-counter keeps: 04152-YZZA6, 00289-ATFWS WS fluid, bulk 0W16

## Pitfalls
- **Do NOT flip anything without an Edit-Part bin redistribution FIRST** — the new primary must actually hold the on-hand or it sells negative immediately. Several June flip candidates (87139-YZZ83, 87139-YZZ93) were NEGATIVE in the back bin.
- Edit-Part redistribution leaves NO GL entry / ledger trail — keep your own CSV log (per Hemant-confirmed behavior).
- The minority counter still drifts after a flip — the daily count sheet stays as the catch mechanism for the residual.
- Recommendation-only unless Joe explicitly approves changes; he decides policy (flip vs zero-out).
- Deliver as emailed report (Excel/CSV/PDF), store-by-store style; remember Gmail self-send needs an INBOX imaplib.append (Sent-only otherwise).

## Related skills
- tekion-ghost-bin-negative-onhand (bin APIs, signed quantities, fix paths)
- tekion-parts-sales-orders (front-counter data)
- tekion-customer-pay-ro-count / tekion-openapi-repair-orders (back-counter data)
- sct-backcounter-ro-sales-countsheet (daily count sheet that catches residual drift)