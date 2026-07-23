# Tekion Parts Workflows & Pricing — Distilled Knowledge

> Source: Tekion "Jump Start" webinar, *Parts Workflows and Pricing* (Part 1 of a weekly parts series).
> Presenter: **Emily Shaw**, Customer Value Architect (CVA), Fixed Operations at Tekion.
> Scope covered: (1) Parts **Sales Order** workflow, (2) Parts **RO Sales** workflow, (3) **Pricing** hierarchy, price codes, price breaks/formulas, matrices, defaults.
> Note: demo done in a Tekion **test environment**; some odd data is expected.

---

## Apps & Navigation

- **Nine dots (app launcher)** at top of screen = main navigation entry point for all parts apps. Apps can be **pinned to the taskbar** if used frequently.
- **Sales Order** app — App launcher (nine dots) → **Sales Order** (under Parts). This is the **Parts Sales Order** screen used for counter sales (front counter / back counter / wholesale / internal). Path corresponds to `/parts/sales-order`.
- **Parts RO Sales** app — App launcher (nine dots) → **Parts RO Sales** → select / pin. Used to sell/quote parts against **Repair Orders (ROs)** from the service department.
- **Customer Management** app — used to set a customer's **default sale type** and **default part pricing** (price code). Requires permission.
- **Settings → Part Settings** — central place for parts configuration: sale types, price codes, core handling, default pricing, price breaks & formulas, custom (matrix) pricing, lost sales, superession behavior.
- **Knowledge Base** — referenced for deeper info on quotes & appointments.

### Per-screen UI controls (recurring patterns)
- **Filter funnel** (top of list screens) — filter by **status**; **save filter groups** (e.g., one per counterperson). Hit **Apply**. Filters must be **cleared** to search reliably by number.
- **Three dots / nine-dot "kebab" menu → Settings** (top of a screen) — per-screen, **per-user (not global)** preferences.
- **Gear icon** — customize visible **columns** per screen; drag/reorder, and you can **lock** a column. Adjustments are **per-user, not global**.
- **Action button / action bar** (per line) — line-level actions (mark prepaid, sell to negative, returns, used core return, unlink special order, print label, etc.).
- **Bulk actions** — select multiple part lines → apply actions in bulk (e.g., mark prepaid, mark as received).
- **Little blue bubbles** above a list header = count of items in **New Request** status.

---

## Parts Sales Order / Counter Sale Workflow (numbered)

1. **Open Sales Order app** (nine dots → Sales Order). The landing list is customizable via the **filter funnel** (filter by status, save filter groups per counterperson). Use the small **drop/tick** to expand more info on what's sitting on a sales order.
2. Click **Create** to start a **new sales order**.
3. **Enter the customer** (Emily used herself). On customer entry the header **auto-collapses** (controlled by a per-user setting under the three-dots/kebab → Settings). Tekion ties everything to **customer number**, NOT to a vehicle VIN.
4. **Optional per-user input settings** (three-dots → Settings):
   - "**Pressing enter** … goes to the next line after quantity" — keyboard-warrior fast entry.
   - A **Beta** toggle (bottom) to **load info in the background** so large orders don't slow down. Hit **Save**.
5. **Set the advanced/header fields** — click the **drop arrow** to expose advanced fields:
   - **Sale Type**: **Retail** (usually front counter), **Wholesale** (front/back counter, warehouse), **Internal**. Configurable in Settings; add as many as needed; can be **routed into accounting** to separate on the financial statement.
   - **Price Code**: either **customer-specific** or a **default price code by sale type**.
   - **VIN** field — check/attach VIN if customer has one on file (lets you reference the vehicle, e.g., "that '21 Subaru"). VIN is informational only (account is keyed to customer number).
   - **Department** (if departments are set up).
   - **Comments** field.
6. **Special Orders banner (blue banner)** — shows any **special orders tied to that customer number**. Columns show **received vs ordered** (green = received). You can **select these parts and import them in**, or **request**/view what's **on order**.
7. **Parts import options** (left side):
   - **Snap-on / integration import** — load cart in Snap-on then import into the sales order.
   - Import **SRs**.
   - **XL Import (Excel)** — download a **template**, build the list in Excel (e.g., recurring body-shop supply order), import → parts drop into the sales order.
   - Facts-print / old-school large wholesale orders can also be added.
8. **Add a part** — type part number or description (catalog has all brands). Watch for **supersession** (behavior depends on supersession settings: may auto-supersede to newest number or stay on old). Errors shown if part **not added to inventory**.
   - Use the **gear icon** to add/reorder columns (e.g., move up **Printed List Price**).
   - Select a line → bottom panel shows **part info**; click the **box-with-arrow** to pull **P&I** (Parts & Inventory) detail into the screen without leaving.
9. **Cores** — line shows core handling: **green = waiting on the core to come back** (received core, not yet charged); **red = core should be in hand and goes to dirty-core inventory** upon finalize. If core is **zeroed out in "filled" and zeroed in "sale"**, the core **amount is charged out**. Example: printed list price $31.56, core price $15.00. Core charge behavior (charge customer or not) is configurable in **Part Settings**.
10. **Set quantity** — quantity splits into **fill** (on hand) and **order** (need to procure). E.g., on-hand 1, ordering qty 2 → "1 to fill, 1 to order."
11. **Set Priority code** (custom in Tekion; NOT OEM-specific by default; e.g., "John's order"). Shows on the resulting purchase order.
12. **Create Sales Order** — resolve any supersession prompt ("leave it"), then **Create**. You now get a **sales order number** and status info (e.g., **partially filled**, **pending payment**).
13. **Modify** (button) to make changes. **Action button** (per line) options include:
    - **Mark as prepaid** — for non-returnable / special parts; adds a **prepaid icon** to the line.
    - **Sell to the negative** — sell stock you physically have but isn't yet in the system (e.g., after bin spot checks); **must reconcile negative inventory** on finalize.
    - Supersession details, etc.
    - **Bulk actions** available for multi-line selection (e.g., bulk mark prepaid).
14. **Modify → Invoice** — generates the **invoice**. From here:
    - **Create Purchase Order** — **OEM Special Order** (from OEM) or **Vendor Order** (third party).
    - **Picklist** — print & pick (some stores use iPads in the warehouse).
    - **Process Return** option.
    - **Transaction history**.
15. **Proceed to Cashiering** — payment options: **Cash**, **On Delivery / COD**, **Other** (split payment, dealership eats a %, route to a different customer or **GL account**). Collect payment (demo used **Cash**).
16. **Receipt / Invoice** — **Show Receipt**; **View or Print Invoice** at top.
17. **Core return (after cashiering/closed)** — customer brings core back later:
    - Change the **Sell Status filter** (uncheck others, check **Closed**, **Apply**) or **Search** by sales order number to find it.
    - Select the part → **Create Return** → action bar → **Used Core Return**.
    - System modifies the sales order to create the return → **return invoice** whose number **starts with `CM` (credit memo)**.
    - **Proceed to cashiering** → refund (Cash, **Check**, or **Credit Card** depending on original payment) → **Refund** / **Show Receipt** / print invoice.
18. **Prepaid parts — critical finalization step**: a **prepaid part stays in your inventory until you mark the customer as having received it**.
    - Hover shows **Customer Delivered** once processed; otherwise mark via **Bulk Actions → Mark as Received** (a.k.a. "mark as customer received").
    - Use the **Prepaid Report** to find prepaid parts that were handed out but never marked received, and clear them.

---

## Parts on RO (Parts RO Sales)

App: **Parts RO Sales** (nine dots → Parts RO Sales).

### Screen layout — the "hand-between-the-headers" mental model
- **Left side headers = selling parts on an existing RO** (RO already created): the **P&A** and **Fulfillment** tabs.
- **Right side headers = preparing for a future RO**: **Quotes** and **Appointments** (if you're not using these two right-side items, "definitely a conversation to be had"). Knowledge Base has more on quotes/appointments.

### The two key tabs (mental model: "bill it and pull it" vs "price and availability")
- **Fulfillment** = "**bill it and pull it**" — the **customer already approved** the work; you **build/validate the parts and pricing**, then send someone to the warehouse to **pull** the part and hand to service. (Equivalent to "fulfillment" in other DMS terminology.)
- **P&A (Parts P&A)** = **Price and Availability** — a **quote** to the service side; parts **not yet sold**. You're quoting price + availability onto the RO.

### Recommended setup
- Use the **gear icon** to drag the **Counterperson** column far left (and **lock** it). When Counterperson is **blank**, it's a **New Request** that came over for you to work; if a **name** is attached, a counterperson has started/completed it.
- **Blue bubbles** above the header = count of New Requests. **Blue boxes** in the list flag items needing attention.

### P&A (Price & Availability) workflow — numbered
1. Open a **New Request** (blank counterperson). It shows the **technician's request** — e.g., a **Recommendation** with **Concern** and **Cause** (hover to read). Techs/advisors can describe parts but **cannot validate the exact part** — that's the counterperson's job.
2. **Validate parts**: copy the **VIN** (top) → open **parts catalog** to confirm the right part, or enter the known part number. Set **quantity** per line.
3. **Part-not-found handling**: a non-part-number entry (e.g., a tire size `245/35R17`) shows an **orange circle "part not found in inventory."** Replace it with a real part number (search "tire" / your tire coding / third-party tire site) to **reconcile orange → green**. Green = resolved.
4. **Auto-resolved**: hover may show "**added by service** and **got auto resolved by the system**." **Auto-resolved ≠ sold to customer** — it means the system recognized the part number. Still verify (e.g., blue vs yellow coolant cars).
5. **Pricing on the line**: shows **list price**; you can **load/change the pricing here** if needed.
6. **Availability / ETA**: for out-of-stock, set availability criteria or an **ETA** (manual, or pulled from catalog), e.g., for back-ordered / VIN-specific parts.
7. **Submit** — sends the quote back to service. Do **NOT** pull parts (P&A only quotes). Status changes to **Submitted**.
8. **Media**: technicians can **upload pictures/videos** to the RO (e.g., location of the part on the block); media lives on the RO for later reference.

→ After submit, the **service advisor** calls the customer/sales manager (internal units). On **approval**, the job moves into **Parts Fulfillment**.

### Fulfillment workflow — numbered
1. Open the RO from the Fulfillment list (use Counterperson column / blue boxes to find new ones).
2. The RO shows **jobs/lines**; only lines **with parts** are actionable. You can **collapse/close lines** on long ROs to focus.
3. **Recall lines**: hover shows the **recall number** the advisor entered. **Requests** tab shows the **original parts request** as submitted from service.
4. **Add fees** here if needed (also available on the prior screen).
5. **Add/confirm parts** (e.g., spark plugs from a recall). System flags **parts in multiple bins** and **supersession** (skip or replace). Confirm quantity.
6. **Line actions** (right side): adjustments, **remove part** (wrong part). If configured, removing can be **counted as a lost sale** (Lost Sales is a feature you turn on/off in settings).
7. **Set quantity** (demo: qty 6 with 4 on hand → **fill 4, order 2**). Adjust **priority code** as needed. (No ETA selection here since availability was already communicated in P&A.)
8. **Internal chat**: drop comments in the **chat** to ping the **advisor/tech**. Ordering can trigger a **bell alert/notification** to advisor & tech that the part was ordered.
9. **Save as Draft** (if waiting on tech/recall info) **or Submit**.
10. **Submit** → auto-generates a **pick list** (e.g., "pull 4 of 4 available"). **Print / Pick** — selecting print/pick gives **versioned** pick lists (track if someone pulls fewer than printed).
11. **Orders** tab — order shortfalls (e.g., "need 2 more spark plugs"): **OEM** (OEM special order) or **Vendor** order. Both screens also show **Miscellaneous** (see gotcha below). Creates an **SOR** (Special Order Request).
12. **SOR view** shows **Received** and **Ordered** columns and the **status oval** (see Statuses below). **Line actions** here: **unlink special order**, **print part label**.
13. Service can see part status on their side via **Special Order Requests** or directly on the **part line** of the RO; advisor sees what's in stock vs on order.

### Parts in-and-out (sublet / counter-style on an RO)
- **Miscellaneous** (on the order screens) is generally used when **selling parts as in-and-out**, BUT in Tekion the correct way to do **in-and-out** is to **start from a part line and add the information** there — not by simply selecting Miscellaneous.

---

## Pricing & Price Types

### A. Pricing places (where pricing is set)
1. **Source Code** (the failsafe / lowest-priority default).
2. **Default Pricing Setup** (Part Settings) — by **sale type** (sales orders) and **RO default part pricing** (RO).
3. **Price Codes** (Part Settings) — named codes like "**List minus 10%**".
4. **Price Breaks & Formulas** (Part Settings) — the "matrix" building blocks.
5. **Customize Price Setup** (Part Settings) — full **matrix / custom pricing** per source code.
6. **Customer Management** — customer-specific default sale type + price code.
7. **Manual Override** (on the line) — the "king of kings."

### B. Sales Order pricing hierarchy (least → greatest priority)
Stated "from least priority to greatest." If nothing else is set, the line falls back down to **Source Code**:
1. **Source Code** price code (failsafe). If no price code is set in source code, the system may "make something up" or **error** — most shops put something here. Set defaults here.
2. **Default (sale) type** price.
3. **Customer-Defined Price** — set via Customer Management (e.g., "E price code 6 = list minus 5" assigned to Emily). **Takes precedence** over the above.
4. **Parts Kit pricing / Flat Pricing** — these "trump each other" with customer-defined and are where the system **starts**, then defaults down until it reaches the final created price.
5. **Manual Override** (Tekion-green box) — **trumps everything** ("manual override is the king of kings").

Practical rules of thumb:
- **Customer-defined pricing** is used ~99% of the time for **wholesale customers**, or set a **default price code for wholesale** (walk-ins dubbed wholesale get price X).
- **Flat pricing** is usually tied to an **op code** (e.g., an oil change) or a **parts kit** (hard-coded price for the kit).

### C. Service/RO price code hierarchy (structured differently)
- The two **green** options (customer-defined / kit-flat equivalents) **override everything** — "the trump cards, in control."
- Otherwise it **falls left→right, dropping back down** through buckets: **flat cost → source escalation → default → final**. The line lands in whichever bucket is set up first.
- Note: this slide is "super busy"; there's a companion slide. Treat as: green overrides win, else cascade flat-cost → source-escalation → default → final.

### D. Default Pricing Setup (Part Settings → defaults)
- **Top section = Sales Orders** — by **sale type** (e.g., "any Parts Retail customer always gets this price"). Configure → **Save** → shows **Update**. Applies only if the customer profile has nothing set and it's not a parts kit.
- **Bottom section = RO default part pricing** — **Edit** to set defaults for:
  - **Customer Pay**
  - **Warranty** (e.g., a warranty price code)
  - **Sales** department (full pop or special pricing)
  - Create special pricing → **Save**. Used as the RO default when no higher hierarchy rule applies.

### E. Price Codes (Part Settings)
- A price code defines how the catalog **list price** is transformed. Example description: "**List minus 10%**."
- Editable attributes per code:
  - **Minimum / Maximum**.
  - **Cent rounding** (round a percentage result to a specific cent value).
  - **Positive or negative** adjustment (markup/markdown) **or a flat dollar amount**.
  - **Second "Printed" section** — set a separate **printed price on the invoice** (to show or hide customer savings vs the actual sell price). The difference between the two sections controls what the customer sees vs what's charged.

### F. Price Breaks & Formulas (Part Settings — the "matrix" building blocks)
- This is where you "set up your matrix so to speak." Each formula is a **dollar-amount break** mapped to a **formula**.
- A new break **always starts at one penny ($0.01)** (lowest dollar amount); you then set the **end amount** (e.g., $0.01–$5.00).
- **Formula base options**: **Cost**, **List Price**, **Trade Price**, **Comp**, **Warranty**.
- **Direction**: **positive or negative** (cost-plus or cost-minus).
- Enter the **percent**, **name** it, **Save**. (Don't over-complicate — keep a few standards plus 1–2 promo/special ones.)

### G. Customize Price Setup (Part Settings — full custom matrix)
- Build custom pricing using the breaks/formulas above. Tie a **matrix to a source code** (e.g., default source code → choose the formula from Price Breaks & Formulas).
- **Add additional source codes** to the matrix for grouped custom pricing.
- Classic use case: **tires** — set up custom tire pricing so it always hits a chosen formula. Save.

### H. Customer Management (customer-level default pricing)
- Customer Management → customer profile → **Parts section** → **pencil (edit)**.
- Set **Default Sale Type** (e.g., Emily = Retail) and **Default Part Pricing** (price code).
- Can also restrict payment methods (e.g., disallow credit card / check for a customer).
- **Save**, then **refresh the screen ("three times for good luck")** to verify; create a sales order for that customer to confirm the defaults auto-apply.

---

## Statuses & Terminology

### Sales Order statuses / states
- **Partially filled** / **Pending payment** — shown after creating a sales order with mixed fill/order and unpaid balance.
- **Closed** — paid/cashiered sales orders (filter under Sell Status → Closed to find them).
- **Sell Status filter** — used to surface closed orders (e.g., for core returns).

### Parts RO Sales statuses
- **New Request** — incoming, **blank counterperson** column; counted by **blue bubbles**.
- **In Progress** — note: there's no status literally called "Open"; if you open a submitted item via **Create Fulfillment** and back out without changes it lingers in **Submitted / In Progress** ("looking at something / pending").
- **Submitted** — P&A quote or fulfillment sent.
- **Closed** — completed (name attached, work done).
- **Draft** — saved-but-not-submitted fulfillment.

### Part-line indicator colors
- **Cores (sales order line)**: **green = core still owed/awaited (not charged)**; **red = core should be in hand → dirty-core inventory on finalize**; zeroed in fill & sale = **core amount charged out**.
- **Part validation (RO)**: **orange circle = "part not found in inventory"** (unresolved); **green = resolved**. Reconcile orange→green.
- **Order/SOR status oval** (Parts RO Sales): **Red = parts NOT ordered**; **Orange = some or all parts ordered**; **Green = all parts ordered AND all parts received**.

### Key terminology
- **P&A** = **Price and Availability** (quote on an RO; parts not sold).
- **Fulfillment** = "**bill it and pull it**" (approved parts to be pulled/sold on an RO).
- **SOR** = **Special Order Request** (created when ordering parts; tracks received/ordered).
- **Supersession** — newer part number replacing an older one; behavior governed by supersession settings.
- **Core** — returnable component; tracked received vs charged.
- **Sale Types** — **Retail**, **Wholesale**, **Internal** (configurable; routable to accounting).
- **Price Code** — list-transformation rule (e.g., "list minus 10%").
- **Customer-Defined Price** — price code assigned at the customer level (e.g., "E price code 6 = list minus 5").
- **Manual Override** — line-level price override; highest priority ("king of kings").
- **CM** — **Credit Memo** prefix on **return invoices**.
- **Prepaid part** — paid-for part that stays in inventory until **marked customer-received**.
- **Lost Sale** — optional tracking when a part is removed/not sold (toggle in settings).
- **P&I** — Parts & Inventory detail (pulled into a sales-order line via the box-with-arrow).
- **Priority Code** — custom ordering priority (not OEM-specific by default; e.g., "John's order").

---

## Gotchas / Pitfalls

1. **Prepaid parts must be marked "received/customer-delivered"** or they stay in inventory forever. Audit with the **Prepaid Report** regularly.
2. **Selling to the negative** requires you to **reconcile negative inventory** when finalizing (e.g., after bin spot checks not yet entered).
3. **Cores**: green vs red is easy to misread — **green = you still owe/await the core**, **red = it should already be in your dirty-core inventory**. Whether the customer is charged for cores is a **Part Settings** toggle.
4. **Auto-resolved ≠ sold**: on an RO, "auto resolved by the system" only means the part number was recognized — **always verify the part** (the blue-vs-yellow-coolant trap).
5. **Orange "part not found" must be reconciled to green** before the system treats the RO part line as valid.
6. **Don't enter a submitted RO via "Create Fulfillment" just to look** — it leaves the item stuck in **Submitted / In Progress** on the main screen. To view, **change the status filter / search and open it**, then **back out** (clearing filters).
7. **Filters must be cleared** to search by sales-order/RO number reliably; otherwise saved filters hide the record.
8. **Column/preference/gear/three-dots settings are per-user, NOT global** — each counterperson sets their own; don't expect changes to apply teamwide.
9. **In-and-out (sublet) parts** are NOT done by just picking **Miscellaneous** on the order screen — you must **start from a part line** and add the info; Miscellaneous alone is the wrong path.
10. **Manual override beats every pricing rule** — a hand-keyed price wins over customer-defined, kits, defaults, and source code. Watch for unintended overrides.
11. **If no price code exists in Source Code**, pricing may "make something up" or **error** — always set a source-code default as the failsafe.
12. **Supersession behavior depends on settings** (auto-supersede to newest vs stay on old) — confirm before relying on it; you'll get a prompt to resolve before creating the order.
13. **Refunds/core returns**: cash may not be in the till for large core values ($1,500) — be ready to refund by **check** or back to **credit card** depending on original tender. Return invoices are **CM (credit memo)** numbers.
14. **After config changes, refresh the screen** (Emily: "three times for good luck") and test with a real sales order to confirm defaults applied.
15. **Lock the Counterperson column** in Parts RO Sales so new (blank-counterperson) requests are always visible; otherwise new work is missed.

---

## Cross-References (for the tekion-parts-sales-orders skill)
- **Caliber RO-dollars source**: confirmed pattern — Tekion **Sales Orders** live at **`/parts/sales-order`** (nine dots → Sales Order). This webinar's sales-order workflow is that screen.
- **"11 price types in Parts RO Sales"**: not enumerated by exact count in this transcript, but the **RO price hierarchy buckets** named here are: **flat cost**, **source escalation**, **default**, **final/create-price**, plus the two overriding **green** options (**customer-defined** and **parts-kit / flat pricing**), with **manual override** on top. Pricing inputs/bases available in formulas: **Cost, List Price, Trade Price, Comp, Warranty**. RO default pricing categories: **Customer Pay, Warranty, Sales/Internal, Special pricing**. (Full 11-type enumeration likely lives on the companion "busy" pricing slide referenced but not shown.)
