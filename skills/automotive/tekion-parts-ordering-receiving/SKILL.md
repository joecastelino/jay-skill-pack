---
name: tekion-parts-ordering-receiving
description: Order parts (purchase orders), handle Special Order Requests (SOR/SOP), and receive parts in Tekion's Parts module. Covers the 8 PO types, the SOR→special-order-PO flow, Parts Receiving app (web + mobile scan-gun), Manual Receipts, float/cross-ship/backorder handling, and all statuses. Load for any "how do I order/receive a part" or SOR troubleshooting task in Tekion.
---

# Tekion Parts — Ordering & Receiving

Source: Tekion CVA webinar (Emily Shaw, Fixed Ops). Covers Special Order Requests (SOR/SOP), Purchase Orders, and Parts Receiving in the Tekion web app and mobile scan-gun app. Full transcript distillation lives at `references/ordering-receiving-full.md`.

> **NEVER-GUESS RULE (Joe's directive):** On any Tekion parts troubleshooting, do NOT invent a plausible answer. If you hit something not covered here, STOP and tell Joe so he can supply the KB/PDF or teach it.

## Apps & Navigation

- **Special Order Request** tile — manages SOR/SOP parts. View-shareable with Service Advisors / BDC / Service Manager so they see arrival status.
- **Purchase Orders** screen — all PO creation/management. Lists **8 PO types** (visible types depend on role permissions + OEM franchise/integration).
- **Parts Receiving** app — day-to-day receiving; on **web** and the **mobile scan-gun app** (same flow).
- **Warehouse Management** — separate app; the ONLY place to **print labels** (cannot print labels from Parts Receiving).
- **PNI** (Part Number Inquiry) — a part's **transactional history** (who/when/where received, document ties, on-hold reasons).
- **Source Codes** (setup) — stocking parameters + min/max sale quantity logic.
- **Core Management** — correct path for **returning a core** (NOT vendor/misc credit).

## The 8 Purchase Order Types
1. **OEM Special Order** (needs SOR)
2. **OEM Stock Order**
3. **Vendor Special Order** (needs SOR)
4. **Vendor Stock Order**
5. **Sublet PO**
6. **Miscellaneous PO**
7. **Vendor Credit PO**
8. **Miscellaneous Credit PO**

(Top OEM-direct types only show for integrated/franchised OEM dealers with permissions.)

## Three ways to create an SOR
1. **Customer number** → SOR directly against a customer profile (gets a **"C"** identifier — standalone, not tied to RO/SO).
2. **Sales Order** (retail/wholesale/internet) → add part not in stock → SOR auto-generates.
3. **Repair Order** → preferred when vehicle is in for service; ties SOR to that RO, eases receiving.

> **SOR is ALWAYS tied to the customer number** — not VIN, not phone.

## Order Parts Workflow (create a PO)

**OEM Stock Order:** Purchase Orders → OEM Stock Order → build list from Source Code stocking params OR pick Source Code + min sale qty → confirm/edit (optional Download to Excel) → set **Manual** if not OEM-integrated → Submit → confirm → Submit. Status = Submitted, received 0/N.

**Vendor Stock Order:** same flow; start by selecting **Vendor**, optionally use a saved **template** (drag-drop to generate list).

**Vendor PO (general):** select Vendor (required) → fill info + **Comments** → confirm Shipping/Billing addresses → set **Pre-invoice** toggle → Submit. Open-PO actions: Reissue PO, Print, Copy/View Copy, Cancel (only before parts move; needs reason).

**Sublet PO:** create with RO ref / no ref / stock vehicle → Vendor → Description → RO# → **GL account** → pricing → Submit.

**Miscellaneous PO:** non-inventory + **"in-and-out" parts**. Vendor → part/desc + Qty → Pricing → GL → invoice# → Submit. **Status stays "Submitted" — never "Received"** (doesn't enter inventory). Notify accounting for in-and-out parts.

**OEM/Vendor Special Order PO:** ⚠ **CANNOT create without an existing SOR.** You can only **assign** parts that already have a generated SOR/priority — cannot add a new part line here.

## Special Order (SOR) full flow
1. On Sales Order or Repair Order, banner shows existing SORs for that customer; click **Details** to peek.
2. Add part; if qty > on-hand, system auto-drops the shortfall to order. Watch **superseded** parts.
3. **Priority Codes** auto-list (user-configurable).
4. **Create Sales Order** → **SOR column** populates with SOR number. Line shows **0/0 in RED** = action needed (not ordered).
5. **Orders tab** → create the order (OEM/Vendor Special Order) if permissioned. **Actions → Unlink SOR** → Reserve/Move to inventory/Void.
6. From **Purchase Orders → OEM/Vendor Special Order**: queue lists SOR-generated parts → **bulk-select** → Save → pull into one PO → Manual if not integrated → Submit.

## Receiving Workflow (Parts Receiving app)
1. Open Parts Receiving (Status is the key column). Locate order by part#. Open → lines + qty.
2. **Bulk fill** (all) OR **one-by-one** (when OEM ships partial). Subset → status **Pending → Partially Received**.
3. **Update** to refresh; **Receipt Transactions** tab shows received-by/channel.
4. Mirrored on Purchase Orders screen (e.g., "1 of 3 lines received").

**Receive directly from a PO/SOR (permissioned):** **Open Receiving** inside the PO/SOR → fill Quantity → Receive.

**Manual Receipt** (order placed in OEM portal, no Tekion PO): Parts Receiving → **Create Manual Receipt** → enter **Control Number** → add part + qty → Receive → Submit. ⚠ **Tekion auto-creates a STOCK order** for it (even if it was a portal special order). Cleanup: close the matching customer SOR and **fill the part from the new on-hand qty**.

**"Float" / new parts:** assign a **Source Code** and/or **Default Bin** → Submit to make available. Row **(…)** actions: Create Vendor Stock Order, Create OEM Order, **Receive to an Order** (attach to existing order via reference+qty), **Remove from Float**.

**Line dispositions** (right end of a line): **Mark as Backordered** (add ETA), **Mark as Canceled**, **Mark as Cross-Shipped** (part from non-PDC source; Received-by-Shipment recognizes cross-ship).

**Cancel a backordered part — two options:** (1) **Cancel the part in the SOR** → SOR canceled + a NEW SOR auto-created to reorder; (2) **Return to SOR queue** → re-enables reordering via a new PO (e.g., Vendor Special Order from a local dealer).

## Statuses & Terminology
Draft · Submitted · Requested (SOR exists, not ordered) · Ordered · Pending · Partially Received · Received · Closed/Filled · Canceled/Backordered/Cross-Shipped · On Hold (received but tied to a doc, no on-hand until filled). **Not Pre-invoiced** vs **Pre-invoiced**.

- **RED 0/0** on an SOR line = action needed.
- Count format: **received (LEFT) / ordered-pending (RIGHT)**.
- **"C"** = SOR from a Customer (standalone). **SL column** links a line to its SOR. **Control Number** = entered on Manual Receipt. **Priority Code** = user-defined ordering priority. **Source Code** = drives stocking params. **Bin/Default Bin** = storage location.

## Gotchas / Pitfalls
- **No special-order PO without an SOR.** Special Order POs only *assign* SOR-generated parts.
- **SOR tied to customer number only** — never VIN/phone.
- **Manual Receipt always creates a STOCK order** — then close the customer SOR + fill from on-hand.
- **Set integration to Manual when not OEM-integrated**, else it tries to transmit.
- **No on-hand after receiving = on-hold/doc-tied**, not an error. Fill on its document; use PNI to find the tie.
- **Miscellaneous POs never show "Received"** (not inventory). Loop in accounting for in-and-out parts.
- **Pre-invoicing** is configurable: OFF → PO closes on receipt; ON → user codes the pre-invoice (e.g., NAPA charges to a GL). Decide with controller.
- **Returning a core → Core Management**, NOT a credit PO.
- **Cannot print labels in Parts Receiving** — use Warehouse Management.
- **Permissions gate everything** (Open Receiving, visible PO types, special-order creation).
- **Superseded parts**: on-hand may reflect a different/superseded number — verify.
- **Drafts get orphaned** — periodically filter by Draft to clean up.
- **Column/layout changes are per-user only.**

## Related skills
- `tekion-parts-sales-orders` — counter sales, parts on ROs, pricing
- `tekion-parts-autoorder-diagnosis` — why a part didn't auto-order / stocked out
- `tekion-source-code-parts-scrub` — source-code part-list extraction
- `tekion-sitemap` — master nav map
