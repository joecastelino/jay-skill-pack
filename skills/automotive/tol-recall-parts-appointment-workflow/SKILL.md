---
name: tol-recall-parts-appointment-workflow
description: TL (Toyota of Lancaster, dealer 1092) recall-only parts appointment workflow — deployed 2026-09-12. Mass-uncheck, keep-list, RECALL opcode, placeholder part, notify-immediately, and backlog sweep.
---

# TL Recall-Only Parts Appointment Workflow

Deployed 2026-09-12 at Toyota of Lancaster (TL, dealer 1092). Mirrors SCT build documented in `tekion-parts-appointments-recalls-only`.

## Deployed State

| Component | Status |
|-----------|--------|
| Mass-uncheck | **981 ACTIVE → 949 OFF, 32 ON** (verified live 2026-09-17 via :9225 in-page fetch) |
| Keep-list | 31 campaign codes + generic `RECALL` |
| RECALL opcode | EXISTS, id `RECALL_1092`, ACTIVE, DIAGNOSTICS / Service Type Recalls, flag ON |
| Placeholder part | **"ORDER PARTS RECALL"** (free-text, no part number → stays UNRESOLVED → queues). NOTE: differs from SCT's "RECALL PART - SEE VIN"; either is fine. |
| Notify-immediately | **OFF** — most generated requests sit `invisible:true` until the window. SCT was flipped ON. Joe's call. |
| Backlog sweep | **NOT run — 490 `PART_REQUEST_PENDING` records back to 2025 (only 5 post-flip).** Sweep LAST, after any notify flip (see SECOND WAVE in `tekion-parts-appointments-recalls-only`). |

**Effect proof (Sep 2026):** Sep 13→17 = 905 appts / **8 pending (0.9%)** vs Sep 1–10 = 1,400 appts / **155 pending (11%)** → generation down ~92%.

**KNOWN LEAK (unproven):** the 8 post-flip pending rows are NON-recall (`LOF4CYL`, `TIRE4`, `EXHANGEC`/`RDIFF`/`RBRAKE`, menu `TEK45000VNM`) yet those opcodes read `eligibleForPartPreparation:false`. Their acquisitions carry `sourceRequestedDetail.opcode = null` and a DIFFERENT `requestedBy` user per record → looks like parts the **ADVISOR manually requested on the appointment**, bypassing the opcode-flag generation path. Diagnose via `GET /api/parts/proxy/u/fulfillment/<id>` → `appointmentRequestDetails.partAcquisitions[].sourceRequestedDetail`, not yet confirmed.

## TL Keep-List (32 opcodes)

**30 Toyota campaign codes:** 20TA02, 20TA024RN, 20TA03, 20TA05, 20TA06, 20TC01, 21TA01, 21TA03, 21TA04, 21TA05, 21TA06, 21TC03, 21TC05, 21TD03, 21TG01, 21TH01, 22TA02, 22TA05, 22TA07, 22TA09, 22TC01, 22TC05, 22TC07, 22TC08, 22TD02, 22TE02, 23TA09, 23TC05, 23TC06, 23TJ01R1, 24TA07

**1 generic:** RECALL (Category=Diagnostics, Service Type=Recalls, Skill=tech/generic)

**18 internal codes EXCLUDED:** 90L, BST, D0L, DSF, E04, EOL, EOM, ESS, FON, ISERVICE, JOA, JOB, JOR, JOU, KOA, KOB, ZKG

## Fast Mass-Uncheck Method (REUSABLE)

Via in-page `fetch()` on authenticated :9223 — WAY faster than browser clicks:

```js
// 1. Pull all active opcodes
const r = await fetch('/api/service-module/u/opcode/search', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({searchText:"", status:"ACTIVE", page:0, size:1000})
});
const data = await r.json();

// 2. Filter to recall keep-list
const keepSet = new Set([...campaigns, 'RECALL']);
const toUncheck = data.data.hits.filter(h => !keepSet.has(h.opcode));

// 3. Bulk-update in batches of 100
for (let i = 0; i < toUncheck.length; i += 100) {
  const batch = toUncheck.slice(i, i+100);
  await fetch('/api/service-module/u/opcode/bulk-update', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      ids: batch.map(h => h.id),
      fields: {considerForPartsPreparation: false}
    })
  });
}
```

## RECALL Opcode Build (Generic)

- Opcode: `RECALL`
- Category: Diagnostics
- Service Type: Recalls
- Skill: tech/generic
- Free-text placeholder part: "RECALL PART - SEE VIN" (Create "NAME" type, NOT real part-master — must stay unresolved to hit Pending Requests queue)
- Parts-prep flag: ON

**GOTCHA:** Joe created this manually — Jay's browser had the Skill field stuck on "Skills Default" despite multiple attempts to change it. The Create button stays disabled until Skill is set correctly.

## Maintenance

New non-recall opcodes default to parts-prep flag ON — need periodic sweeping or manual unchecking at creation. No automated sweep cron deployed yet at TL.

## After Backlog Sweep

Run the fulfilment API to clear pre-existing non-recall Pending Requests. Same method as SCT — the queue will still show old requests (free-text oil/filter/tire placeholders) until swept.