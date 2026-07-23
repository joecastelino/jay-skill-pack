---
name: tekion-physical-inventory
description: Run a Tekion Parts Physical Inventory or Bin Spot Check audit — the full Setup → Counting → Reconciliation → Summary workflow that compares system count vs physical count, surfaces variance, and writes on-hand adjustments. Use when Joe asks about counting parts, bin spot checks, inventory variance, reconciling shelf qty vs Tekion, or "Make Adjustments". Load alongside tekion-sitemap.
---

# Tekion Physical Inventory & Bin Spot Check

The Physical Inventory app runs an inventory audit comparing the **system count (on-hand + on-hold)** against the **actual physical count**, surfaces variance, lets you research/correct, then writes on-hand adjustments. A **Bin Spot Check** is a smaller subset version (a few bins/parts) to catch variance before committing to a full count.

Built from Tekion KBs: KB0025956 (Bin Spot Check), KB0011058 (Counting Phase), KB0012181 (PI Counting), KB0012244 (PI Reconciliation).

## Where it lives
App Grid menu > Apps tab > **Parts** section > **Physical Inventory** app tile.

## Permissions (Roles page > Permissions tab > Parts drop-down > Parts section)
- **Physical Inventory Edit**
- **Show/Download Variance in Count Sheet** (also unlocks the Variance Dashboard during counting)
Parts manager has both by default.

## Phases
- Full Physical Inventory: **Setup → Counting → Reconciliation → Summary** (4)
- Bin Spot Check: **Setup → Counting → Reconciliation** (3)

### 1) Setup (Bin Spot Check)
1. Physical Inventory > **Create Inventory** > **Create Bin Spot Check**, name it.
2. **Part Selection** — by Bin, Source Code, Bin Range, Random, Top Selling, etc.; optionally include 0-qty parts; pick warehouse locations + brands.
3. (Optional) **Add Additional Parts**.
4. Configure **Count Sheet** (sort sequence, extra columns, page breaks).
5. Configure **Variance Sheet** (layout, columns, page breaks).
6. **Calculate** → review summary (bins, sheets, parts, value) → **Start Inventory**.

### 2) Counting
1. Open the in-progress inventory from the list.
2. **Download Count Sheet** → physically count each bin.
3. Select a sheet on the left → input physical counts. Sort pane: **Pending / Partially Filled / Variance**.
4. Green check = sheet complete; red = something missing. Move pages via the next-page box at bottom.
5. Buttons: **Clear All** (re-enter a page), **Mark all counts as 0** (zero the whole sheet), **Add Write-In** (part in bin not on sheet — fields: Part Number, Description, Cost Price [0 ok], List Price [0 ok], Source Code, Brand, Bin Details, Physical Count; check "Add another write-in entry" for multiples; **Save**). View via **Write-In Part List** bottom-left. Write-in CANNOT use a bin/source excluded at setup.
6. **Show Variance** (permission) compares On-Hand vs Physical live; **Download Variance Sheets** for the list.
7. **Variance Dashboard** tabs: Summary, No Variance, Negative Variance, Positive Variance, Total Variance, Uncounted, Write-In. Summary columns = Number of Parts, Percent of Inventory, Count Value (physical × total cost), System Value ((on-hand+on-hold) × total cost), Dollar Variance (Count − System). Each tab except Summary has a **Print** button.
8. All sheets green → **Mark as Complete** (confirm) → **Proceed to Reconciliation**.

### 3) Reconciliation
1. Open the in-progress inventory.
2. Quick Views: **Net Variance** (frozen snapshot of initial health — does NOT update), **Positive Variance**, **Negative Variance** (final $ lands in the On Hand Adjustment app).
3. Variance tabs per-part columns: Part# w/Desc, Bin, Shelf|Drawer, Count Sheet No., Physical Count, System Count, Variance, Total Cost, Variance Amount. Write-ins tagged with Write-in icon. Search by part#/bin; filter by cost >/<; multi-sort (Bin, Part#, Cost, Variance). View Total Variance by Bin or Part.
4. **Re-Open Counts** → back to Counting to fix counts/write-ins. **Limited to 2 total** (system shows remaining).
5. **Download / Print** Reconciliation summary PDF: Summary / Total Variance by Part / Total Variance by Bin (available even after closed).
6. **Make Adjustments** = THE irreversible commit. Creates all on-hand adjustments in real time → opens Summary.

### 4) Summary (full PI)
Reports parts with **exceptions** — on-hand adjustments that did NOT complete.

## Pitfalls
- **Make Adjustments is the commit** — it writes on-hand. Verify all variance in Reconciliation first.
- Only **2 Re-Open Counts** — budget them.
- Net Variance is a frozen initial-health snapshot; true final $ is in the On Hand Adjustment app + manual adjustments outside the physical.
- Write-ins can't land in setup-excluded bins/sources (system blocks with an alert).
- Show Variance + Variance Dashboard are permission-gated (Show/Download Variance in Count Sheet).
- Ties into negative-on-hand work: a physical/spot check is how you reset shelf truth after Negative-OH-Sale events (see tekion-parts-autoorder-diagnosis / tekion-ghost-bin-negative-onhand).

## Cross-references
- tekion-sitemap (nav), tekion-parts-autoorder-diagnosis, tekion-ghost-bin-negative-onhand, tekion-parts-ordering-receiving.
