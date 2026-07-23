---
name: tekion-tek-opcode-part-replace
description: >
  Swap a wrong factory part on a FACTORY "TEK"-prefixed Tekion opcode (e.g.
  TEK04020101 "Cabin Air Filter Remove and Replace") to the correct part, using
  the "Replace Part Number" action inside Opcode Management → Overrides → Parts →
  Modify System Parts. This is the fix-surface for FACTORY TEK opcodes used in a
  service menu (NOT custom/BG opcodes — those use tekion-included-service-parts-override).
  Covers the exact, painfully-learned order of operations (Identifier + Job BEFORE
  the part number), the 16th-row trick, the Replace-Part-Number modal, the
  validation-error trap, and the re-quote verification. Verified live at SCT
  (dealer 876) 2026-06-25: 87139-06030 → 87139-YZZ81, quote $1,937.12 → $1,929.12.
  Use when Joe says a maintenance-menu line pulls the wrong factory part and the
  opcode starts with "TEK".
category: automotive
tags: [tekion, opcode, parts, override, service-menu, factory-opcode, part-replace, browser]
---

# Tekion — TEK Factory-Opcode Part Replace

## When to use this skill
A Tekion **service-menu line** (e.g. the 120K maintenance package) pulls the
**WRONG factory part** for a vehicle, and the opcode behind that line is a
**FACTORY "TEK"-prefixed opcode** (starts with `TEK`, e.g. `TEK04020101`).
Goal: replace the wrong part number with the correct one so every vehicle that
takes that opcode gets the right part.

### Fix-surface decision (CRITICAL — Joe drills this)
The fix location depends on the **opcode TYPE**:
- **FACTORY "TEK" opcode** (e.g. `TEK04020101`) → **OPCODE MANAGEMENT**
  (`/ro/opcode/edit/<OPCODE>` → Overrides → Parts → Modify System Parts).
  **← THIS SKILL.**
- **CUSTOM / BG opcode** used in a menu (e.g. `BGCVTF`) → **Service Menu Setups →
  Included Services → Edit Service → Overrides → Parts.** Use
  `tekion-included-service-parts-override` instead.

If you don't yet know which opcode drives the menu line, discover it via the
**Quotes portal ONLY** (see `tekion-quotes-menu-price-diagnosis` /
`tekion-sitemap`): toggle "Add Menu Services as separate operations" ON+Save →
build a quote → read per-op opcodes in the RIGHT detail panel. Do NOT guess.

## Prerequisites
- Persistent browser logged into Tekion at the correct dealer (see
  `persistent-browser-server`, port 9223). All steps below use the `:9223`
  HTTP endpoints: `/eval` (POST `{js}` → `.result`), `/click` (POST
  `{selector}`; tag elements with a `data-jay` attr first), `/type` (POST
  `{selector,text}`), `/screenshot` (GET → JSON `.screenshot` base64).
- Know the **old (wrong) part number**, the **new (correct) part number**, and
  the **opcode** (TEKxxxxx). Confirm on-hand for both (the wrong part is usually
  a superseded/low-stock number; the new one is the current part with stock).

## The method (verified end-to-end)

### 0. Open the opcode editor on the OVERRIDES tab
- Navigate: `location.href='https://app.tekioncloud.com/ro/opcode/edit/<OPCODE>'`
  (a fresh load also discards any unsaved stray rows from a prior attempt).
- Click the **Overrides** tab (top, next to Default).
- Click **Parts** in the left sub-nav (Labor / Parts / Fees / …).
- **Expand the vehicle row** that covers the target vehicle (e.g. the "Toyota"
  row) by clicking its far-left **caret**. This reveals the
  **"Modify System Parts"** table (the opcode's ~15 native factory parts) plus
  the **"Add Custom Parts"** table above it.

### 1. KNOW THE TWO TABLES (the #1 thing I keep relearning)
- **"Add Custom Parts"** (top of the expanded row): a vehicle-row/custom builder.
  Rows added here have a ⋮ menu with **Delete ONLY** — **NO "Replace Part
  Number"**. **WRONG table for this task.**
- **"Modify System Parts"** (below it, with the "Remove System Parts" toggle):
  the opcode's native part rows. A row here has the full ⋮ menu: **Exclude /
  Replace Part Number / Link Part / Delete**. **THIS is where the replace lives.**

To get a NEW part (the old/wrong one) the "Replace Part Number" option, you must
add it as the **16th row at the BOTTOM of the Modify System Parts table** (after
the 15th native row, e.g. `87139-76020`), using that table's own blank add-row —
**not** the Add Custom Parts field.

### 2. CRITICAL ORDER — Identifier + Job FIRST, THEN the part number
On the blank add-row at the bottom of Modify System Parts, the columns are:
`Identifier (x≈365) | Job (x≈585) | Part Name (x≈805) | Qty | Price`.

**You MUST set Identifier and Job BEFORE typing the part number:**
1. Click the **Identifier** column → pick **"All Identifiers"**.
2. Click the **Job** column → pick **"All Jobs"**.
3. THEN click **Part Name** and type the **FULL** wrong part number (e.g.
   `87139-06030`, **NOT** bare `06030` — bare returns only `Create "..."` + an
   unrelated part). Pick the **real** option (`87139-06030 - ELEMENT, AIR
   REFINER`), **ignore** the `Create "…"` option when you want a REAL part.

**What `Create "..."` actually does (Joe confirmed 2026-07-20):** it creates a
**generic placeholder part** on the opcode — you can name it anything (e.g.
"Transmission Fluid") and set a price, and it does NOT add anything to the
parts master/inventory. Use it deliberately when the opcode should bill a
generic line that Parts swaps for the correct real part at RO time (e.g. a
generic "Transmission Fluid" so the estimate never shows WS fluid on a CVT
vehicle). Pick the real catalog option only when you want the actual part.

**If you type the part number before setting Identifier+Job**, those two stay
empty (placeholders "Add identifiers from" / "Add jobs from here"), the field
gets a **red border**, and the final Save FAILS with the red toast
**"Please correct form errors to proceed."** This was the entire debugging loop —
do it in the right order.

After this the row reads: `All Identifiers | All Jobs | 87139-06030 - ELEMENT | each`.
Do **NOT** touch Quantity or Price (system-driven / price-code-driven).

### 3. Replace Part Number
- Open the **⋮ (icon-overflow)** kebab on the 06030 row → menu shows
  **Exclude / Replace Part Number / Link Part / Delete** → click **"Replace
  Part Number"**.
- Modal opens: **"Replace Part Number of M_TMNA_<oldnumber>"**.
- Click the **"Select Part"** dropdown (a react-select; its input is
  `#react-select-NN-input`, located just below the "Select Part" label) → type
  the **FULL new part number** (e.g. `87139-YZZ81`) → pick the real option
  (`87139-YZZ81 - ELEMENT, AIR REFINER`).
- Click **Save** on the modal (the Save button inside the modal box, ~y434).

### 4. Save the override box
- Click the bottom **Save** button on the override box (≈ x1166, y671).
- Expect green toast **"Opcode updated successfully"**. If you instead get the
  red "Please correct form errors" — go back to step 2 (Identifier/Job empty).

Note: after the replace, the row's displayed part number **still SHOWS the old
number** (e.g. 87139-06030). That is **correct** — "Replace Part Number" maps
old→new underneath and resolves to the new part at quote time. Do not "fix" it.

### 5. VERIFY by re-quoting (mandatory)
Build a fresh quote for the exact VIN + mileage and confirm the corrected part:
1. `/ro/quotes` → **Create Quote** (top-right, ≈ x1110, y80).
2. VIN field "Search VIN #" → type the VIN; it decodes inline (no dropdown click).
3. Odometer field (`input[id*="dometer"]`) → type the mileage (e.g. `120000`).
4. **Continue** (≈ x1166, y673).
5. Right panel **Service Menu** tab → the package tile auto-loads for the
   odometer (e.g. "120K mi Maintenance Package").
6. Click the tile → pick the **tier** (Basic / **Basic +** / Signature). Joe's
   convention: **Basic+ = Value = VNM**. Confirm the package opcode flips
   (e.g. read `TEK120000VNM`, the `V` = Value) before trusting it.
7. **Add To Quote**.
8. Click the menu **service line** (the deepest `span` containing the package
   opcode `TEK120000VNM`, ≈ x95) to navigate into `/service/<id>`.
9. Confirm in the page text: the **new part is present** and the **old part is
   gone**, e.g. `87139YZZ81 - ELEMENT, AIR REFINER 1 each 36 - $21.99` and no
   `87139-06030`. Confirm the menu total dropped by the expected delta.

## Verified case (SCT, dealer 876, 2026-06-25)
- Opcode `TEK04020101` "Cabin Air Filter Remove and Replace".
- Wrong part `87139-06030` (ELEMENT AIR REFINER, on-hand 2, superseded) →
  correct `87139-YZZ81` (ELEMENT AIR REFINER, on-hand 36, $21.99).
- 120K Value menu `TEK120000VNM` on a 2004 Camry (VIN `4T1BE30K34U909096`,
  odometer 120000).
- Result: quote line now pulls **87139-YZZ81**; total **$1,937.12 → $1,929.12**.

## Pitfalls (all hit live)
- **Wrong table:** adding the part in "Add Custom Parts" gives a Delete-only ⋮
  (no Replace). Must be the 16th row in **Modify System Parts**.
- **Wrong order:** part number before Identifier+Job → red "Please correct form
  errors to proceed" on Save. Identifier="All Identifiers", Job="All Jobs" FIRST.
- **Bare suffix:** typing `06030` (not `87139-06030`) won't surface the ELEMENT
  option — only `Create "..."` + an unrelated TRANY FLUID part.
- **Hidden duplicate row builder:** the page renders a HIDDEN copy of the row
  builder at negative-x / off-screen y. Always target the **VISIBLE** control
  (`offsetParent != null && rect.x > 0`).
- **Stale `data-jay` selectors / menu reflow:** Tekion menus render in a portal;
  after each click rows reflow. Re-tag elements right before each `/click`; a
  stale selector causes a silent ~10s `/click` timeout. When a DOM read of a
  popup menu shows only "Delete" but you expect more, **screenshot + vision** —
  the menu item rects can report 0,0 in a transform/portal.
- **`/type` needs `{selector,text}`** (not bare text). Tag the live react-select
  input by its `#react-select-NN-input` id + a `data-jay` attr.
- **Never-guess:** if a field/menu doesn't behave as documented, STOP and ask
  Joe rather than inventing a path — this is live Published config.

## Related skills
- `tekion-included-service-parts-override` — the CUSTOM/BG-opcode counterpart
  (Service Menu Setups → Included Services).
- `tekion-quotes-menu-price-diagnosis` — find which opcode drives a menu line.
- `tekion-opcode-overrides` — general opcode override batch workflow.
- `tekion-sitemap` — nav URLs; `persistent-browser-server` — the :9223 layer.
