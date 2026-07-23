---
name: tekion-parts-shortage-diagnosis
description: "[DEPRECATED — use tekion-parts-autoorder-diagnosis] Old name for the Tekion parts stock-out / why-didn't-this-auto-order diagnosis. All content was merged into tekion-parts-autoorder-diagnosis (the canonical, fuller skill). This file is a redirect only."
triggers:
  - parts inventory shortage
  - why aren't parts auto ordering
  - parts stock out
  - had to get parts locally
---

# DEPRECATED — merged into `tekion-parts-autoorder-diagnosis`

This skill has been **superseded**. Everything that used to live here (RO→parts OpenAPI walk,
the API hard-limit proof, the ServiceNow KB access notes, the root-cause buckets) was folded
into the canonical skill, which also has the deeper material:

**→ Load `tekion-parts-autoorder-diagnosis`** for any "why did we run out / had to get this
part locally / why isn't it auto-ordering" question.

That skill now covers, end to end:
- Step 1: RO numbers → parts via OpenAPI + the API hard-limit proof + on-hand confirm
- Step 2: live Stocking Details in the browser (:9223)
- Step 2b: Open Documents drawer (the highest-signal step)
- Step 2c: confirming a Draft stock-order PO in the Purchase Order list
- Step 2d: the Transactions ledger (shortage smoking gun)
- **Step 2e: the negative-on-hand backfill trap + in-and-out receiving discipline**
- Step 3: running the demand calc (day-supply, BSL qty, the BSL Round-Down trap)
- Step 4: per-part verdict table + the two fix levers (Min Qty vs source-code BRP/BSL)
- KB references + ServiceNow access notes

Do not add new content here — put it in `tekion-parts-autoorder-diagnosis`.
