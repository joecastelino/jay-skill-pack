---
name: tekion-pdf-print-copies-diagnosis
description: >
  Diagnose "the customer invoice prints 2 times" / duplicate document printing at any
  AMG Tekion store. Root cause lives in PDF Settings → Print tab → AutoPrint Settings:
  the Quantity column = copies per print event. Also covers: finding which store an
  employee works at via the OpenAPI users endpoint, and the /ro/pdf-settings nav traps.
  Verified live at VW Clovis (1891) 2026-09-02 (Joe Mendoza ticket).
triggers:
  - invoice prints twice
  - invoice prints 2 times
  - duplicate invoice printing
  - document prints two copies
  - auto print settings tekion
  - pdf settings print tab
  - which store does an employee work at
---

# Tekion — "Invoice prints twice" diagnosis (PDF Settings Quantity)

## TL;DR
Duplicate prints are almost never user-specific. **PDF Settings → Print tab →
AutoPrint Settings → Quantity column** sets copies-per-print-event per document type.
Quantity=2 on `Invoice - Customer Pay` (trigger `Payer Invoice`) = every CP invoice
auto-prints 2 copies for EVERY advisor at that store.

## Step 0 — Which store is the complainer at?
If the ticket names an employee ("Joe Mendoza has an issue…"), find their store via
the OpenAPI users endpoint across all 7 dealers. **Use the canonical client — do NOT
hand-roll headers** (`app_id`/`secret_key`/`access_token` headers = 401; the client
uses `Authorization: Bearer`):

```python
import sys; sys.path.insert(0, "/home/itadmin/tekion-api")
from tekion_client import load_config, api_get
cfg = load_config()
stores = {"AR":6195,"BC":1251,"BT":1249,"ST":876,"SV":826,"TL":1092,"VC":1891}
# per store: GET /openapi/v4.0.0/users?pageSize=100, paginate via meta.nextFetchKey
# dealer_id = f"americanmotorscorporation_{did}_0"
# name from userNameDetails.completeNames[nameType==DISPLAY_NAME]
```
Pitfalls: (a) names can be None → guard `.lower()`; (b) **dedupe by user id AND track
seen fetchKeys** — pagination can loop returning the same page forever; (c) match is
case-insensitive substring. Result 2026-09-02: Joe Mendoza = VC 1891.

## Step 1 — KB context (optional, fast)
`kb_search_scrape.py search "invoice printing two copies"` → KB0011063
(*SERVICE SETTINGS: PDF Settings - Print Tab*) documents every column. Key facts:
- **Quantity** = "number of copies to print for each time the document is triggered".
- Auto Print Triggers: RO Invoiced / CP Closed / W Closed / I Closed / RO Closed /
  Payer Invoice (Service 3.0). No trigger selected = manual print only.
- "Print on invoice" toggle (General Settings header) = master auto-print switch.

## Step 2 — Read the store's Print tab (:9223)
1. Switch dealer to the target store (pill at (1130,32), scrollIntoView the
   `[class*="root_dealerInfoItem_container"]` row, re-read rect, /mouse; assert
   `localStorage.currentActiveDealerId`).
2. Navigate **`/ro/pdf-settings`** (sleep 15). TRAPS:
   - `/service/settings/pdf-settings` → blank (108 chars). `/pdf-settings` → bounces
     to /home. `/service/settings/pdf-settings/print` → blank (330 chars).
   - The App Grid overlay is INVISIBLE to `document.body.innerText` (renders outside
     the queried DOM) — don't try to find the tile via innerText; use the direct URL.
3. Click the left-nav **Print** tab. TRAP: `/click {"selector":"text=\"Print\""}`
   matches some other "Print"-ish element and **bounces you to /core/reports**.
   Instead tag the leaf first:
   ```js
   // leaf, exact text 'Print', visible, left rail (x<400, y>50)
   els.filter(e=>e.children.length===0 && e.offsetParent &&
     e.textContent.trim()==='Print' && e.getBoundingClientRect().x<400)
   [0].setAttribute('data-jay','printtab');
   ```
   then `/click '[data-jay="printtab"]'`, sleep 8.
4. Read the AutoPrint table from the **DOM, not vision** — the Quantity column is
   off-screen right (screenshot/vision cannot see it). Anchor on the header:
   ```js
   // find .rt-resizable-header-content with text 'Quantity', walk up to .rt-table,
   // then map .rt-tbody .rt-tr → .rt-td innerText per row
   ```
   Column order: Document · Category · Auto Print Trigger(s) · Check-in Auto Print ·
   Duplex · Display Voided Job · Reprint · Job Tag · Job External Note · **Quantity** ·
   Quick RO Auto Print · VI RO Auto Print.

## Step 3 — Interpret
- Any invoice row with **Quantity ≥ 2** and an auto-print trigger = the duplicate.
- Rows with trigger "Select..." only print manually — Quantity 2 there means manual
  prints also come out doubled.
- VC 1891 baseline (read 2026-09-02): Invoice - Customer Pay = **2** (Payer Invoice),
  Invoice - CVSC = **2**, Closed RO Invoice = **2** (manual), Invoice - Service
  Advisor = **2** (manual); Warranty/Internal = 1. "Print on invoice" = ON.

## Step 3b — "But only ONE person has the problem"
Store-level Quantity=2 still fits a single complainer: the Payer-Invoice auto-print
fires on the workstation of whoever **triggers** the event (closes/cashiers the CP
invoice). If one advisor does most CP invoicing, only they see doubles; manual
reprints by others default to 1 copy in the dialog. Competing per-user causes:
1. **Windows printer driver/preferences** on their PC set to copies=2.
2. **Double-print behavior**: invoice auto-prints at cashiering AND they hit Print
   again manually (very common).
Discriminating question for the user: does it double when it **auto-prints at
invoicing** (→ Tekion Quantity) or when they **manually hit Print** (→ their
dialog/driver/habit)?
Discriminating test: flip `Invoice - Customer Pay` Qty 2→1, have them invoice one CP
RO. Still doubles → workstation-side. (Restore the setting after if store wanted 2.)

## Step 4 — Before fixing, ASK JOE
This is often a **deliberate config** (customer copy + file copy — the VC row was
last edited on purpose in 2024). Present the table and offer: fix CP row only, fix
all 2's, or leave as designed. Fix = change Quantity dropdown → 1 → page **Save**
(bottom-right) → true-remount verify (nav /home → back → re-read).

## Related
- `tekion-sitemap` (nav), `tekion-service-settings` (Service Settings ≠ PDF Settings;
  they STACK — "Notify customer on invoice" lives in Service Settings),
  `tekion-kb-search-scrape` (KB0011063/KB0024754/KB0025107).
