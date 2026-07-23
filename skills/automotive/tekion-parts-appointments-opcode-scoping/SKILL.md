---
name: tekion-parts-appointments-opcode-scoping
description: Restrict Tekion Parts-on-Appointments (Parts RO Sales > Appointments queue) to a subset of opcodes — e.g. recalls only, per Glade at SCT. Covers the per-opcode "Consider for Parts preparation on Appointment" checkbox, Bulk Update, the limited Appointments-tab filters, and how to derive a store's recall keep-list from the opcode list. Load for any "parts department should only see X appointments" request.
---

# Tekion — Scope Parts-on-Appointments to specific opcodes (recalls-only pattern)

Origin: Joe/Glade request 2026-07-20 (SCT 876) — "parts appointments for recalls only".
Greenlit as Option A. KB sources: KB0012918 (config), KB0012911 (order/hold/fulfill flow),
KB0021854 (No-Parts filter), KB0025115 (available appointment filters).

## The mechanism (the key fact)
There is NO recall/opcode filter on the Parts RO Sales → Appointments tab. The real
control is **per-opcode**: Opcode Management → open opcode → **Parts section →
"Consider for Parts preparation on Appointment" checkbox**. It is **ON for ALL opcodes
by default**. Unchecked = that opcode never notifies Parts / never lands in the
Appointments prep queue. Mass changes via **Bulk Update** button on the opcode list
(`/ro/opcode`, top of results toolbar).

Supporting knobs (Scheduling Settings → General, see `tekion-scheduling`):
- "Notify Parts department of appointment part request" — immediately vs N days before.
- "Hold Parts on Missed & In-Progress appointments for few days".
Parts-side notifications: Profile Settings → Notification Settings → Service → Appointments.

## What the Appointments tab CAN filter (Option B, view-only)
Funnel icon → Add Filter. Fields: Appointment Date/Time, Appointment Status,
Part Status, Counter Person. Best available: `Part Status | Not In | No Parts`
(KB0021854). NOT a recall filter — don't promise one.

## Recalls-only recipe
1. **Derive the keep-list** (per store — never reuse another store's):
   - `/ro/opcode` has SERVICE-TYPE TABS on the left (SCT has a dedicated **"Recalls"**
     tab = its own service type; 106 opcodes there).
   - Only **ACTIVE** opcodes matter — Inactive/Archived can't be added to appointments.
     SCT split was 3 ACTIVE / 50 Inactive / 53 Archived.
   - Also search for generic opcodes: SCT has **RECALL** (Active, DIAGNOSTICS,
     "PERFORM RECALL. VERIFIED OPEN RECALL:") — Joe explicitly wanted it kept.
   - SCT keep-list (2026-07-20): **RECALL, 23TA13, 23TC01, 23TC05** (+ leave the whole
     Recalls service type checked — harmless for dead ones).
2. **Present keep-list to Joe for confirm** before touching anything (he asked to review it).
3. **Bulk Update**: uncheck "Consider for Parts preparation on Appointment" on all
   ACTIVE non-recall opcodes (~2K total at SCT incl. inactive; scope actives first
   via Status filter). Leave keep-list checked.
4. **Verify**: spot-check one unchecked opcode's Parts section; book/inspect the
   Parts RO Sales → Appointments queue thins to recall appointments.

## Caveats to state to Joe
- **New opcodes default to checked ON** — future recall campaigns auto-flow (good),
  but new non-recall opcodes will also default ON (needs periodic re-scrub).
- This is store-wide: Parts stops getting prep notifications for tires/menus/everything
  non-recall — confirm the whole parts team understands, not just the requester.

## Browser mechanics / pitfalls (:9223, hard-won this session)
- `:9223 /eval` body key is `{"js": ...}` NOT `expression`. `/screenshot` is **GET**
  (returns `{"screenshot": base64}`), not POST.
- **curl -d with JS containing quotes/plus-concat breaks body-parser** — for any
  non-trivial js payload, POST via python `urllib` + `json.dumps` instead of inline curl.
- Opcode search box = `input[searchfield="ALL"]`. After native-value-setter typing,
  a single `keydown Enter` sometimes does NOT refire the search (row count stays stale,
  e.g. "2,066") — fire the full `keydown`+`keypress`+`keyup` Enter sequence.
- The **Reset** button (filters) also WIPES the search box text — retype after Reset.
- XHR-hook capture of `/api/service-module/u/opcode/search`: parse `responseText`
  INSIDE the hook and accumulate `hits` by `id` into `window.__hits` (raw responseText
  >200KB truncates and breaks JSON.parse later). Response shape `data.count` + `data.hits[]`
  with `{opcode,status,opcodeType,category,description,id}`.
- Virtualized list pagination can stall (stuck 100/106 despite scroll jiggling) —
  use the **Status dropdown filter** (Select... next to "Status:") to slice the set
  instead of fighting the scroller.
- KB SSO drops between sessions: re-bootstrap by navigating :9223 to
  `https://app.tekioncloud.com/core/knowledge-base/search` (see tekion-kb-search-scrape).
- Verify `localStorage.currentActiveDealerId` BEFORE reading — browser drifts dealers
  (was on BC 1251 when this SCT task started; switched via dealer pill → row click).

## Status / next step
As of 2026-07-20: keep-list presented to Joe, bulk update NOT yet executed —
awaiting his confirm on the list + caveat #2. Execute step 3–4 on go.

## Related skills
- `tekion-scheduling` (notify-parts toggles), `tekion-kb-search-scrape`,
  `tekion-sitemap`, `persistent-browser-server`, `tekion-opcode-api`.
