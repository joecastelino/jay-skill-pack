---
name: tekion-parts-sales-orders
description: Tekion Parts Sales Orders (counter sales) + Parts RO Sales (parts on repair orders) + the full parts PRICING system (hierarchy, price codes, price breaks/formulas, matrices, defaults). Covers /parts/sales-order, P&A vs Fulfillment, cores, prepaid parts, core returns (CM credit memos), and the 5-tier pricing hierarchy where manual override is "king of kings." Load for counter-sale, parts-on-RO, or parts-pricing questions.
---

# Tekion Parts Workflows & Pricing (Sales Orders + RO Sales)

Source: Tekion "Jump Start" webinar, Parts Workflows & Pricing (Emily Shaw, CVA Fixed Ops). Full distillation at `references/workflows-pricing-full.md`.

> **NEVER-GUESS RULE:** On parts-pricing troubleshooting, if you hit something not covered here, STOP and ask Joe — do not invent a plausible answer. He is deeply parts-knowledgeable and rejects wrong root-cause diagnoses instantly.

## Apps & Navigation
- **Sales Order** app — nine-dots launcher → Sales Order (under Parts). The **Parts Sales Order / counter sales** screen. Path = `/parts/sales-order`. **This is the Caliber RO-dollars source** (no OpenAPI endpoint; browser scrape only).
- **Parts RO Sales** app — sell/quote parts against **Repair Orders**.
- **Customer Management** — set customer **default sale type** + **default part pricing** (price code).
- **Settings → Part Settings** — sale types, price codes, core handling, default pricing, price breaks/formulas, custom (matrix) pricing, lost sales, supersession.
- UI: **filter funnel** (save filter groups per counterperson; CLEAR to search by number), **gear** (columns, lockable, per-user), **three-dots/kebab → Settings** (per-user not global), **action bar** (per-line), **bulk actions**, **blue bubbles** = New Request count.

## Sales Order / Counter Sale Workflow (key steps)
1. Sales Order app → **Create** → enter **customer** (Tekion keys to **customer number**, not VIN).
2. Expose advanced/header fields (drop arrow): **Sale Type** (Retail/Wholesale/Internal — configurable, routable to accounting), **Price Code**, **VIN** (informational), **Department**, **Comments**.
3. **Special Orders blue banner** = SORs tied to that customer; select & import, or view on-order.
4. Import options: **Snap-on**, **XL Import (Excel template)**, SRs.
5. Add part (catalog all brands); watch **supersession**; error if part **not added to inventory**.
6. **Cores**: green = waiting on core to come back (not charged); red = core should be in hand → dirty-core inventory on finalize; zeroed in fill+sale = core charged out. Charge behavior set in Part Settings.
7. **Quantity** splits into **fill** (on-hand) + **order** (procure). Set **Priority code**.
8. **Create Sales Order** → SO number + status (partially filled / pending payment).
9. **Action button** (per line): **Mark as prepaid**, **Sell to negative** (reconcile on finalize), supersession. Bulk actions available.
10. **Modify → Invoice** → Create Purchase Order (OEM Special Order / Vendor Order), **Picklist**, Process Return, Transaction history.
11. **Proceed to Cashiering**: Cash / On Delivery(COD) / Other (split, GL account). Show/Print Receipt.

**Core return (after closed):** filter Sell Status = Closed (or search SO#) → select part → **Create Return → action bar → Used Core Return** → return invoice starts with **`CM`** (credit memo) → cashiering refund (Cash/Check/Credit Card).

**Prepaid parts — CRITICAL:** a prepaid part **stays in inventory until you mark customer-received** (Bulk Actions → Mark as Received). Audit with the **Prepaid Report**.

## Parts on RO (Parts RO Sales) — the two tabs
- **P&A (Price & Availability)** = a **quote** to service; parts **NOT yet sold**. Validate exact part (counterperson's job), set qty, pricing, ETA → **Submit** (do NOT pull parts).
- **Fulfillment** = **"bill it and pull it"** — customer already approved; build/validate parts → Submit → auto-generates **versioned pick list** → Print/Pick. Orders tab → order shortfalls (OEM/Vendor) → creates an **SOR**.
- **Counterperson column blank = New Request** (lock it far-left). **Orange circle = "part not found in inventory"** → reconcile to **green**. **Auto-resolved ≠ sold** (still verify, e.g. blue-vs-yellow coolant).
- **SOR status oval**: **Red** = parts NOT ordered; **Orange** = some/all ordered; **Green** = all ordered AND all received.

## Pricing System

**Where pricing is set (lowest → highest priority):**
1. **Source Code** (failsafe default — always set one or pricing errors/guesses).
2. **Default Pricing Setup** (Part Settings) — by sale type (SOs) + RO default part pricing.
3. **Price Codes** (e.g., "List minus 10%").
4. **Price Breaks & Formulas** (matrix building blocks).
5. **Customize Price Setup** (full matrix per source code).
6. **Customer Management** (customer-specific sale type + price code).
7. **Manual Override** (line) = **"king of kings"** — trumps everything.

**Sales Order hierarchy (least → greatest):** Source Code → Default sale-type → **Customer-Defined Price** → **Parts Kit / Flat Pricing** → **Manual Override**. Customer-defined used ~99% for wholesale; flat pricing usually tied to an op code or parts kit.

**Service/RO hierarchy:** the two **green** options (customer-defined / kit-flat) override everything; else cascade **flat cost → source escalation → default → final**.

**Price Codes attributes:** Min/Max, **cent rounding**, positive/negative adjustment or flat dollar, separate **Printed price** section (controls what customer sees vs charged).

**Price Breaks & Formulas:** each break starts at **$0.01**, set end amount; **base options: Cost, List Price, Trade Price, Comp, Warranty**; positive/negative; name + Save.

**Customize Price Setup:** tie a **matrix to a source code** (classic: tires). **Default Pricing Setup**: top = Sales Orders by sale type; bottom = RO defaults (Customer Pay / Warranty / Sales).

**Customer Management:** profile → Parts section → pencil → set Default Sale Type + Default Part Pricing → Save → **refresh ("3× for good luck")** → test with a real SO.

## Statuses & Terminology
- SO: Partially filled, Pending payment, Closed. **Sell Status filter** surfaces closed orders.
- RO Sales: New Request (blank counterperson), In Progress, Submitted, Closed, Draft.
- **P&A** = Price & Availability; **Fulfillment** = bill it and pull it; **SOR** = Special Order Request; **CM** = Credit Memo prefix; **P&I** = Parts & Inventory detail.

## Gotchas
1. **Prepaid parts** stay in inventory until marked customer-received — audit Prepaid Report.
2. **Sell to negative** requires reconciling negative inventory on finalize.
3. **Cores**: green = you still owe/await; red = should be in dirty-core inventory.
4. **Auto-resolved ≠ sold** — always verify the part.
5. **Orange "part not found" must become green.**
6. **Don't open a submitted RO via "Create Fulfillment" just to look** — leaves it stuck Submitted/In Progress.
7. **Filters must be cleared** to search by SO/RO number.
8. **Gear/three-dots/column settings are per-user, not global.**
9. **In-and-out (sublet)**: start from a **part line**, not by picking Miscellaneous.
10. **Manual override beats every pricing rule.**
11. **No price code in Source Code** → pricing guesses/errors.
12. **Supersession behavior depends on settings.**
13. **Core returns** = **CM** credit-memo numbers; large cores may refund by check/CC.
14. **After config changes, refresh + test.**

## Related skills
- `tekion-parts-ordering-receiving` — POs, SOR, receiving
- `tekion-parts-autoorder-diagnosis` — replenishment/shortage diagnosis
- `tekion-opcode-default-pricing` — opcode labor + parts pricing
- `tekion-sitemap` — master nav map
