# Tekion Parts — Ordering & Receiving (Distilled)

Source: Tekion CVA webinar (Emily Shaw, Fixed Ops). Auto-transcribed; field names reconstructed/normalized. Covers Special Order Requests (SOR/SOP), Purchase Orders, and Parts Receiving in the Tekion ARC web app (and mobile scan-gun app).

---

## Apps & Navigation

Core parts apps/tiles referenced (Tekion ARC, Parts module):

- **Special Order Request** tile/screen — manages SOR/SOP parts. Shareable (view access) with Service Advisors / BDC / Service Manager so they can see arrival status.
- **Purchase Orders** screen — all PO creation/management. Shows a list of **8 PO types** (see below). Visible types depend on role permissions and OEM franchise/integration status.
- **Parts Receiving** application — where shipping/receiving lives day-to-day; receive incoming PO lines. Available on **web** and on the **mobile scan-gun app** (log into the app; same flow).
- **Warehouse Management** — separate app; the ONLY place to **print labels** (cannot print labels from Parts Receiving).
- **PNI** (Part Number Inquiry / part record) — view a part's **transactional history** (who/when/where received, document ties, on-hold reasons).
- **Source Codes** (setup) — define **stocking parameters** (used by stock orders) and min/max sale quantity logic.
- **Core Management** — correct path for **returning a core** (NOT vendor credit / miscellaneous credit).

Entry points to create an SOR (3 ways):
1. **Customer number** → create SOR directly against a customer profile (gets a **"C"** identifier — standalone, not tied to RO/SO).
2. **Sales Order** (retail / wholesale / internet) → add part not in stock → SOR auto-generates.
3. **Repair Order** → preferred when vehicle is in for service; ties SOR to that RO and eases receiving (receives back into original RO, or a secondary RO if vehicle already left).

> SOR is ALWAYS tied to the **customer number** — not to VIN, not to phone number.

Common UI elements:
- **Filter funnel** ("martini glass") icon — on every list screen. Build criteria → **Save** the filter → it becomes a selectable **quick filter** dropdown option. **Apply** to run; **Clear** to reset to defaults.
- Column layout is per-user (rearranging/removing columns affects only your view, not the team).
- **Live link** — click to jump directly to the source document (SO/RO/PO).
- **Actions** menu (top) — bulk actions on selected rows.
- **three-dots (…)** row menu and **info "i"** icon (hover any PO type for a description).

---

## Order Parts Workflow (Create a Purchase Order)

### A. Stock Order (OEM) — bring in a book of parts not tied to a customer
1. Open **Purchase Orders** screen.
2. Select **OEM Stock Order** (a.k.a. "Olean/OEM stock order").
3. Choose how to build the list:
   - **Stocking parameters** (defined in **Source Codes**), OR
   - Select a **Source Code** + set a **minimum sale quantity** to pull qualifying parts.
4. Confirm/edit the part list. Optionally **Download to Excel** to manipulate, then review running totals (Total Part Lines, Total Number of Parts, Total Cost).
5. Set integration mode — **Manual** if not OEM-integrated (won't transmit to OEM).
6. **Submit** → confirmation popup → Submit again. PO shows status **Submitted** and received count **0 / N**.

### B. Vendor Stock Order
- Same flow as OEM stock order. Start by selecting your **Vendor**, fill info, optionally use a saved **template** (drag-and-drop to generate the list), add parts manually if needed, Submit.

### C. Vendor PO (general) — required fields
1. Purchase Orders → vendor PO type.
2. Select **Vendor** first (required).
3. Fill order info; add **Comments** (recommended — visible to team & accounting).
4. Confirm **Shipping** and **Billing** addresses.
5. Set **Pre-invoice** toggle (**"Not pre-invoiced"** vs pre-invoice ON — see Gotchas).
6. **Submit.**
- Top actions on an open PO: **Reissue PO**, **Print**, **Copy / View Copy**, **Cancel** (allowed only before parts move/received; must enter a cancel reason).

### D. Sublet PO (mostly Service, available to Parts)
- Create with **Repair Order ref**, **without reference**, or on a **stock vehicle**. Add Vendor → Description → RO number (if any) → **GL account** to bill to (if mapping done) → pricing → Submit. (Can also be imported onto the RO; deeper coverage is on the Service side.)

### E. Miscellaneous PO
- For non-inventory purchases (office supplies, misc vendors requiring a PO) and **"in-and-out" parts** (part that should flow in/out of the system without leaving inventory residue).
- Select **Vendor** → add part/description + **Quantity** → **Pricing** → optionally code the **GL** → invoice number (if provided) → **Submit**.
- **Status stays "Submitted" only** — never shows "Received" (does not enter inventory). Validate the PO list against the vendor invoice. Notify **accounting** for in-and-out parts so it processes correctly.

### F. OEM Special Order PO / Vendor Special Order PO
> **Hard prerequisite:** you CANNOT create a special-order PO without an existing **SOR (priority)**. The SOR feeds a queue that the special-order PO pulls from. You can *search* a part here but cannot *add* a new part line — only **assign** parts that already have a generated SOR/priority code.

See full SOR → PO flow in the next section.

---

## Special Order Parts (SOR / SOP / SOR)

Terminology note: "**SOP**" / "**SOR**" / "special order request" are interchangeable (varies by dealership/prior DMS). Tekion's object = **Special Order Request**.

### Create SOR via Sales Order or Repair Order
1. Open/create the **Sales Order** (or **Repair Order**).
2. A banner shows existing SORs for that customer number (e.g., "you have 4 SORs"); click **Details** to peek at what's already requested/arrived.
3. Add the part. If sale qty exceeds on-hand, the system **auto-drops the shortfall** to order based on settings.
   - Watch for **superseded** parts (on-hand may map to a different/superseded part number).
4. **Priority Codes** auto-list and are **user-configurable** (set them up however you want); leave or change.
5. **Create Sales Order.** The **SOR column** populates with the generated **SOR number** (tied to the customer number).
6. The line shows **received / ordered** as **0 / 0 in RED** — red = action needed (not yet ordered).

### From the SO/RO Orders tab
- Move to the **Orders** tab. If you have permission, **create the order** (OEM Special Order or Vendor Special Order) directly from the tile.
- If you lack permission, stop — a designated person creates the special-order PO.
- **Actions → Unlink SOR**: then choose **Reserve it / Move to inventory / Void**. Voiding removes the line from the SOR queue.

### Create the Special Order PO (from Purchase Orders screen)
1. Purchase Orders → **OEM Special Order** (or **Vendor Special Order**).
2. The screen lists SOR-generated parts in the queue (by category, e.g., "GM overnight").
3. **Bulk-select** the parts (e.g., select all for the day) → **Save** → they pull into one PO screen.
4. Set **Manual** if not OEM-integrated (won't push to GM/OEM portal).
5. **Submit** → confirmation → Submit. Header shows the **Special Order number** and status **Submitted** (0 received).
6. The special-order PO now lives on the Purchase Orders main screen.

### SOR list screen (Special Order Request tile) — for Service Advisors
- **Filter funnel** options include **Reference Type** (Repair Order / Customer / Appointment / Sales Order) and **Status** (Requested, Ordered, Received, Partially Received, Draft, etc.). Advisors typically filter Reference = **Repair Order** and drop **Draft**.
- Save the advisor filter so it's a reusable quick filter.
- Columns show customer name + status (e.g., "Received" → call the customer to bring car back in).
- **Actions → Move to On Hand** (bulk): closes out an SOR when the customer no longer needs the part; clears it from pending so it won't wait for fulfillment on the document.
- Click into an SOR to see: part info, the **PO it was ordered from**, **priority codes**, order date, current status, **requested by**, and a **live link** to the source SO/RO.
- **SL column** relates the line to its SOR; shows **received (left) vs ordered/pending (right)**.
- **Orders** tab inside the SOR → **Open Receiving** (permissioned) to receive the part directly to that order: fill **Quantity** → **Receive**.
- **Receipt** tab — view receipted-in history (1-to-1 receipts, "Closed"/"Filled" indicators), though most receiving review happens in the Parts Receiving app, not here.

---

## Receiving Workflow (Parts Receiving app)

Web or mobile scan-gun. Shipping/receiving staff "live" in this screen waiting for orders to arrive.

### Standard receive against a PO
1. Open **Parts Receiving**. **Status** is the key column (often dragged left for visibility).
2. Locate the order (search by part number / look it up). Open it — lines + quantities show.
3. Receive options:
   - **Bulk fill** (fill all automatically), or
   - **One-by-one** line receive (use when OEM ships only part of the order).
4. Receiving a subset → PO/SOR status changes **Pending → Partially Received**.
5. **Update** the screen to refresh; **Receipt Transactions** tab shows what's already received + who (e.g., "by Chris") and channel ("on the web").
6. Mirror on the Purchase Orders screen: PO status updates to **Partially Received**; inside the PO you see e.g. "1 of 3 lines received," on-hand qty vs required qty.

### Receive directly from a PO or SOR (permissioned)
- Inside an open PO or SOR: **Open Receiving** appears (if you have permission) — receive the part you physically found without going through Parts Receiving. Status still reflects partial until all lines done.

### On-hold / no on-hand after receive
- A received line may show **no on-hand quantity** because it's **tied to a document and on hold** (e.g., on a customer SOR). It's pending you **filling the part on the document**. Use **PNI → transactional history** to investigate.

### Manual Receipt (order placed in OEM portal but no Tekion PO exists)
1. Parts Receiving → **Create Manual Receipt**.
2. Enter the **Control Number**, add the **part**, set quantity, **Receive**.
   - If pricing is loaded in your price tape, price auto-fills. **Submit.**
3. Tekion **auto-creates a Stock Order** for it (even if the OEM portal order was a "special order") — because a special-order PO requires an SOR, which a manual receipt doesn't have.
4. **Cleanup:** if the part was really meant for a customer SOR, **close out the SOR** and **fill the part using the on-hand qty** from this manual stock order — prevents a dangling open SOR while the part is already on hand.

### "Float" / parts needing to be added to inventory
- New/unknown parts can sit in a "float"/needs-to-be-added-to-inventory state. Assign a **Source Code** and/or **Default Bin**, then **Submit** to make it available, enabling a manual receipt.
- Row **three-dots (…)** actions here include: **Create Vendor Stock Order**, **Create OEM Order**, plus two newer actions:
  - **Receive to an Order** — attach the received part to an existing order (find order, enter **reference** + **quantity** → **Save**); clears it from the manual-receipt/float section and applies it to the real order. (You'll likely need the order number.)
  - **Remove from Float** — confirm prompt; clears the item from the float screen.

### Line-level disposition (right end of a receiving/PO line)
- **Mark as Backordered** — part not arriving yet. Shows sales-order/prepayment/quantity info; add **latest ETA** (e.g., the 27th). You can still audit/receive it later if it arrives early.
- **Mark as Canceled** — part canceled.
- **Mark as Cross-Shipped** — part comes from a source other than the expected PDC; on **Received by Shipment**, the system **recognizes cross-ship**.

### Canceling a backordered part — two options
1. **Cancel the part in the SOR** → SOR canceled and a **new SOR auto-created** to reorder, OR
2. **Return it to the SOR queue** → re-enables reordering the part in a PO (e.g., source it as a **Vendor Special Order** from a local dealer that has it).
- After canceling a part out, remaining lines show **Received** and the order leaves the screen.

---

## Statuses & Terminology

PO / SOR / line statuses observed:
- **Draft** — started but not finalized/submitted (find via filter to clean up).
- **Submitted** — PO created/sent (manual = not transmitted to OEM).
- **Requested** — SOR generated (SR number exists) but not yet ordered.
- **Ordered** — special-order PO created.
- **Pending** — awaiting receipt.
- **Partially Received** — some lines/qty received.
- **Received** — fully received.
- **Closed / Filled** — receipt complete (1-to-1), shown on Receipt tab.
- **Canceled** / **Backordered** / **Cross-Shipped** — line dispositions.
- **On Hold** — received but tied to a document (no on-hand until filled on doc).
- **Not Pre-invoiced** vs **Pre-invoiced** — invoice status on a PO.

Color cue: **RED 0/0** on an SOR line = action needed (not ordered).
Count format: **received / ordered** — **received on LEFT**, **ordered/pending on RIGHT**.

Identifiers / columns:
- **"C"** prefix/identifier = SOR created from a **Customer** (standalone, not RO/SO).
- **SOR number** / **SR number** — the special-order request id (tied to customer number).
- **SL column** — links a line to its SOR; shows received vs ordered.
- **Control Number** — entered on a Manual Receipt.
- **Priority Code** — user-defined ordering priority on SOR/special-order parts.
- **Source Code** — drives stocking parameters; assigned when adding parts to inventory.
- **Bin / Default Bin** — storage location assigned on receipt.

The **8 Purchase Order types** (Purchase Orders screen; top = OEM direct connections):
1. **OEM Special Order** (needs SOR)
2. **OEM Stock Order**
3. **Vendor Special Order** (needs SOR)
4. **Vendor Stock Order**
5. **Sublet PO**
6. **Miscellaneous PO**
7. **Vendor Credit PO**
8. **Miscellaneous Credit PO**

(Top OEM-direct types only show for integrated/franchised OEM dealers with proper permissions.)

---

## Gotchas / Pitfalls

- **No special-order PO without an SOR.** OEM/Vendor Special Order POs can only *assign* parts that already have a generated SOR/priority — you cannot add a brand-new part line there.
- **SOR is tied to the customer number only** — never VIN or phone. Wrong customer = wrong SOR.
- **Manual Receipt always creates a STOCK order**, even if you placed an OEM-portal special order. Remember to close the matching customer SOR and fill it from the new on-hand stock qty, or you'll have a dangling SOR + a filled part = confusion.
- **Set integration to Manual when not OEM-integrated**, otherwise the system expects to transmit. In a non-integrated/test setup the order won't push to the OEM (e.g., GM) portal.
- **No on-hand after receiving = on-hold/doc-tied**, not an error. Fill the part on its document (use PNI transactional history to find the tie).
- **Miscellaneous POs never show "Received"** (status stays Submitted; not inventory). Validate list vs invoice and loop in accounting — especially for **in-and-out parts**.
- **Pre-invoicing** is configurable: OFF → PO closes as soon as received; ON → user codes the pre-invoice (e.g., route NAPA charges to GL 242, split out fees to other accounts). Decide with controller/accounting before enabling.
- **Returning a core** → use **Core Management**, NOT Vendor Credit / Miscellaneous Credit PO.
- **Cannot print labels in Parts Receiving** — must use **Warehouse Management** (label printing here was deprioritized).
- **Permissions gate everything**: Open Receiving inside a PO/SOR, visible PO types, and direct special-order creation all require role permissions; limited roles see fewer PO types.
- **Superseded parts**: on-hand may reflect a superseded/different part number than what you typed — verify before ordering.
- **Backorder cancel choice matters**: "Cancel the part" auto-creates a NEW SOR to reorder; "Return to SOR queue" lets you re-source via a new PO (e.g., local dealer). Pick deliberately.
- **Drafts get orphaned**: someone saves a PO as Draft and never finalizes — periodically filter by Draft status to find and complete/clear them.
- **Cross-ship**: if a part arrives from a non-PDC source, use **Mark as Cross-Shipped** / Received by Shipment so the system reconciles it correctly.
- **Receiving exists in two places** (web + mobile scan-gun app) — same logical flow; pick per your team's process.
- Column/layout changes are **per-user only** — don't assume teammates see your arrangement.
