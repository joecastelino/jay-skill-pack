---
name: tekion-scheduling
description: Tekion Service Scheduling Settings — appointment slot times, capacities, service advisors, shops, transportation, vehicle/opcode exclusions, and the consumer scheduler. Covers the "lowest ceiling wins" capacity model, shop top-down matching, the daily overnight scheduler + "Run Scheduler" button, parts-on-appointment notifications, and the concierge mobile write-up flow. Load for any appointment/scheduling/capacity setup or troubleshooting in Tekion.
tags: []
related_skills: []
triggers:
  - appointment slots arent working
  - fix scheduling capacity settings
  - lyft ride radius or mileage limit
  - service advisor scheduling setup
  - run the scheduler button
  - consumer scheduler configuration
  - shop capacity or booking window settings
  - parts on appointment notifications
  - transportation settings in tekion scheduling
---

# Tekion — Service Scheduling Settings

Source: Tekion service scheduling webinar (CVA-led). Full distillation at `references/scheduling-full.md`.

> **GOLDEN RULE: settings work TOGETHER — whatever the LOWEST ceiling that gets hit determines the cap.** (e.g., an advisor bookable midnight–midnight in a shop open 9–4 → 9–4 is the limiter.)
> **NEVER-GUESS RULE:** if you hit something not covered here, STOP and ask Joe.

## Navigation & Top-Down Principle
Scheduling Settings has left-hand tabs. **Work top-down** — the order matters because the system reads broad → granular and most-restrictive wins.

**Direct URL (verified 2026-07-14):** `https://app.tekioncloud.com/dse-v2/scheduling-settings` — guessed URLs like `/scheduling-settings` bounce to /home; reach it via App Grid → search "Scheduling" → "Scheduling Settings" tile (under Digital Service Experience 2.0 Settings), or navigate to the dse-v2 URL directly. Tabs route as `/dse-v2/scheduling-settings/{transportation|summary|...}`.

## Lyft ride radius / mileage limit (verified SCT 2026-07-14)
Transportation tab → click the **Lyft** row → detail page `/dse-v2/scheduling-settings/transportation/TRANSPORTATION_SETTINGS/<uuid>`. The page has: Advance Booking, Availability to book, Pickup Time, **Ride Providers** table (Provider=Lyft, Fee Code e.g. LYFTCONC), **Restrictions** table (Type/Condition/Value rows: "Ride distance | Less than | N mi" and "Total number of rides allowed per RO | Less than | N"), Dealership Sites (pickup address), Email Recipients, Vehicles include/exclude. Change the Ride distance Value (ant-input-number-input) → **Save** (bottom-right) → toast "Transportation updated successfully. Changes will be effective starting from next day." → to apply NOW, go to **Summary tab → Run Scheduler** (toast "Scheduler is running..."). SCT baseline before 2026-07-14 change: ride distance 10 mi, rides/RO <2; changed to 15 mi.

## Tabs (left → right / top → down)

**General settings:**
- **Appointment slot times** — 15 / 30 min increments.
- **Missed (no-show) window** — how long after appt time = missed; how long to **hold parts** for missed appointments before returning to inventory.
- **How far in advance** appointments can be booked (call-in vs online separately; e.g., same-day call-in, 8 hrs online).
- **Late booking emails** — trigger when an appt is booked outside the normal window.
- **Color coding** — by appointment status (most common), shop, or transportation type.
- **BDC call center** — auto-allocate appointments through BDC-login agents as call-center appts (shows in Appointment Performance report).
- **End-of-day capacity** — factors job hours into scheduling (5 hrs of work won't fit a shop closing in 2 hrs → pushes to tomorrow).
- **Move appointment to actual checked-in slot** — early drop-off slides the appt to today, reopens the original slot.
- **Auto-assign / notify Service Advisor**, default to last advisor, swap vehicle keep jobs, suggest first available slot, **create customer record at time of appointment** (vs at check-in).
- **Notify parts department of appointments** — ON = notify parts for any parts-on-appointment opcode regardless of timing; or set a time range (e.g., only within 7 days). This is the **parts-on-appointment** toggle. **Per-opcode control**: Opcode Management → opcode → Parts section → "Consider for Parts preparation on Appointment" checkbox (ON by default for ALL opcodes; Bulk Update for mass changes) — see `tekion-parts-appointments-opcode-scoping` for the recalls-only pattern (KB0012918).
- **Promise time mandatory** toggle; **VIN mandatory** (often OFF — customers don't know 17 digits).

**Service Advisors tab** — add anyone who can have appts booked under their name. **Add Service Advisor** (blue box) → pick user → give a **schedule** (repeat + start/end date). **Multiple named schedules** (A/B/C) handle weekend rotations (e.g., every-3-weeks Saturday). Add **blocks** (one-off days off, half-days).

**Shops tab** — active shops the system considers. **Order matters: most-restrictive at top, least-restrictive at bottom.** System reads top-down (Express → Remote → Toyota → Main) and stays with the first match; a **default shop** = catch-all. Each shop: name/description, departments, override booking windows (more restrictive than General wins), hours, daily blocks (one-off/recurring), holidays (global holidays from **Dealer Configuration → Dealer Details**; grayed-out holidays managed there), advisor↔shop mapping (advisors can live in multiple shops), **vehicle limitations** (include/exclude by make/model/year — e.g., mobile shop = Ford only), **serviceable opcodes** (add in bulk by service type; set slot/day/week capacities per service — e.g., max 3 LOFs 9–10am, max 8 recalls/day).

**Transportation tab** — modes (concierge tied to service concierge SKU; lift tied to lift/rideshare integration). Each has active status, notes, where-bookable, email recipients. Rentals/loaners/valets: BDC-only booking, hourly/dollar limits, vehicle exclusions.

**Capacities tab** — broadest → granular: **Dealership** (max appts/day) → overrides (call-in / online / quick-scheduler maximums) → **Service Advisors** (daily limits, selectable from call-in/online, slot capacities) → **Shops** (# appts and/or max hours) → **Transportation**. Blank slot = no limit; numbers = the limit. Lowest ceiling hit = the cap.

**Consumer Scheduling tab** — toggles: customers can pick advisor/transportation, quick-booking, show pricing, "any service advisor," show all makes/models, default same-as-last-time, disassociate old vehicles, show promos/service-menus/recalls, tax-inclusive pricing (Toyota), missed-appointment display duration. **Module order configurable** (drag 6-dots) — one page vs multi-page. Optional modules: NLAI promos, accessories (GM catalog), dealer promotions.

## The Overnight Scheduler & "Run Scheduler"
- **By default, changes take effect with the daily scheduler that runs overnight (~midnight–2 AM).**
- To apply changes immediately: **Summary tab → Run Scheduler** button — scrapes current settings and pushes changes live in real time (no waiting for overnight run). NOTE: the on-demand run is a LIGHTER pass than the overnight rebuild — routing changes (which shop a vehicle lands in) show up immediately on the consumer calendar, but earliest-bookable-DAY availability may not fully shift until the next overnight run. Re-test the next morning before concluding a capacity/routing change "didn't work."

## Concierge / Mobile Write-Up Flow
- Concierge workflow is **ONLY available through the mobile write-up process** (Tekion ARC mobile app).
- Used for night-drop, pickup & delivery, mobile service, tow-ins — **the only way to capture a digital signature when the customer is NOT in front of you.**
- Flow: check in appt → **assign a Porter** (customer auto-texted ETA) → confirm vehicle/mileage → MPVI/inspection (drag to defer/delete line items, set severity red/yellow) → present menu (can be made mandatory in check-in setups) → confirm contacts/addresses (pencil to override) → **CP link texted/emailed to customer** → customer signs estimate in consumer portal → screen auto-refreshes → **RO number created**. Digital signatures show **green** on PDF views.
- Non-appointment (night-drop/tow-in): change **transportation type to Concierge** in the delivery screen to use the same flow.

## Diagnosing "no appointments available" (verified SCT 2026-07-30)
When someone reports the scheduler won't offer slots for days/weeks, do NOT start with settings theory — pull the booked-vs-capacity numbers first. All via the :9223 persistent browser (in-page XHR hook; raw fetch to /api/scheduling 500s "Token doesn't exist" — the app's axios interceptor adds auth a bare fetch can't).

1. **Ground truth = Appointments calendar month stats.** Navigate `/dse-v2/appointments` (redirects to `/appointments/calendar/month`), arm an XHR hook capturing `scheduling` URLs, click Month / the toolbar arrows (right-arrow icon ~x845,y162; Today/Month/Week/Day at ~y160). Each nav fires `POST /api/scheduling/u/appointment/calendar/month/stats` (body = appointmentDateTime GTE/LTE epoch-ms filters). Response: per-day `appointmentDayStatistics {maxAppointmentCapacity, bookedAppointmentCount, missedAppointmentCount, colorCodeInfo{NEW,COMPLETED,...}}` + per-slot stats on week view (`/calendar/week/stats`). booked≈max through day N ⇒ genuinely full until day N+1; that's the answer.
2. **Capacity ceilings** = `GET /api/scheduling/u/settings/appointment` (fires on Scheduling Settings load). Key fields: `capacity[]` per-day `maxCapacity` (dealership max, the usual lowest ceiling), `bdcCapacity`, `regularCapacity`/`quickCapacity` (Consumer online buckets — often tiny, e.g. SCT 40/day vs dealership 134 — online customers hit "full" far earlier than BDC), per-slot arrays (`maxSlotCapacity` etc.; capacity 0 rows = blocked slots like lunch), `bookingFrom/Upto` + `bdc…`/`cs…` variants (booking windows), `lastDailySchedulerRunTime`/`lastWeeklySchedulerRunTime` (confirm the scheduler actually ran), `shouldCheckEndOfDayCapacity`, `enableShopOverBooking`. NOTE: booked counts can EXCEED maxCapacity historically — walk-ins/check-ins land on the calendar regardless of cap, so July running 150-180 against a 134 cap means the cap is undersized vs real throughput.
3. **Shop detail** = click a shop row on `/dse-v2/scheduling-settings/shops` (hook captures `GET .../settings/serviceShop/<uuid>`): `hours[]`, `blocks[]` (e.g. daily 11:30-12:45 lunch ⇒ slot cap 0-1), `bookingFrom/Upto` overrides, `vehicles[]` include/exclude (e.g. TXM = Toyota year>2023 only; older cars fall through to next shop top-down), `maximumHoursToSell`, `shopOpcodes[]` (per-service-type opcode lists + slot/daily/weekly capacityRestriction). SCT shop UUIDs: Express=e762d8da-7d6f-4c77-bf77-479a690a2d1f, TXM=8e56605b-6520-44f5-8e8d-068917b870d7. TXM vehicle window as of 2026-08-02: Toyota, Year Greater Than 2016 (was >2023; Joe widened it so 2017+ vehicles route to TXM).
4. **Summary tab board** (`/dse-v2/scheduling-settings/summary`, `POST .../settings/summary`) shows capacity CONFIG (originalCapacity/availableCapacity per slot, advisor totalCapacity=32/day each), NOT net-of-bookings — don't read it as availability. Shop filter = tekion-select at ~x685,y243; date = ant-calendar input at ~x419,y238.
5. **OpenAPI `/service-appointments:search` is NOT reliable for day counts** — filter format `{"field":"appointmentDateTime","operator":"BTW","values":[ms,ms]}`, pageSize max 50, paginationToken; but pagination 500s partway and default sort samples recent creations ⇒ massive undercounts vs calendar stats. Use it for appointment detail lookups only; trust calendar stats for volume.
6. Rearm the XHR hook after every page navigation (SPA route changes keep it, hard navigations kill it).

Typical verdict template: booking windows fine + scheduler ran recently + days booked to the dealership cap ⇒ not a bug, capacity-starved; fixes = raise dealership max and/or consumer allocation, then Run Scheduler.

## EDITING a shop's Vehicle limitation (year/make filter) — canonical procedure (verified live SCT 2026-08-01/08-02, TXM >2023 → >2016)

Use case: older vehicles fail a shop's year filter, fall through to the booked-solid Main shop, consumer sees "weeks out". Fix = widen the year window on the shop row.

1. Shops tab → click shop row → detail page `/dse-v2/scheduling-settings/shops/<uuid>` (loads `GET /api/scheduling/u/settings/serviceShop/<uuid>` — capture via XHR hook to read current config). **Vehicles section renders BELOW the viewport** (~y1336 on load) — `scrollIntoView({block:'center'})` on the operator select first, then re-read rects (they move after scroll).
2. Row = three tekion-selects: **operator | year | make**.
   - **Operator options are ONLY `Greater Than / Equals / Less Than` — ALL STRICT.** There is no ≥ and no explicit range/"between".
   - **To express "year X → current" you must enter `Greater Than (X−1)`.** E.g. "2017 → current" = **Greater Than 2016**.
   - **Greater Than is open-ended upward** — it automatically covers ALL future model years (2026, 2027, ...). If Joe later asks "add 2026 too" / "move it up to 2026 vehicles," the answer is **nothing to change** — Greater Than N already includes every year after N. Don't add a second row or re-edit.
3. **Year dropdown PITFALL:** clicking the select renders the FULL 1970–current option list; **typing into the react-select search input does NOT filter it**. Just find the target option in the returned list (`[class*="-option"]`, may render at negative y if above viewport — scroll first) and `/mouse` click its coordinates directly.
4. Confirm the row reads correctly via the visible `singleValue` texts (e.g. `Greater Than | 2016 | Toyota`), then **Save** (bottom-right, ~x1211,y689). Success = `PUT /api/scheduling/u/settings/serviceShop/<uuid>` 200 + toast **"Shop Updated Successfully. Changes will be effective starting from next day."**
5. **Verify with a TRUE remount** (nav to /home, then back to the shop URL — per the SAVE-VERIFY TRAP, a same-URL/#hash re-nav re-reads your own unsaved DOM as a false "persisted"). Persisted payload shape: `vehicles:[{operator:"INCLUDE", equalityRelation:"GREATER_THAN", vehicleInfo:{year:"2016", make:"toyota"}}]`.
6. Summary tab → **Run Scheduler** to apply now instead of waiting for the overnight rebuild (toast "Scheduler is running..."; full effect ~10 min, but see the "on-demand run is lighter than overnight" note above).
7. **Routing-flip tell on the consumer side:** re-run the consumer scheduler test with an affected VIN — if the earliest bookable day now shows **AM slots starting at the shop's opening time (e.g. 7:00 AM = TXM/Express)** where it was PM-only or "No Slots Available" AM before, the vehicle is routing into the widened shop even if the earliest *day* hasn't moved (that can be genuine demand — check booked-vs-max via calendar month stats before calling it a routing failure).
8. Hard `location.href` navigation KILLS the XHR hook — after any hard nav, rearm the hook and prefer `history.pushState + PopStateEvent` SPA navigation to keep it alive across the verify step.
9. SCT-specific baseline: Express shop has **NO vehicle limitation** (blank Year/Make/Model row = every year/make passes); only TXM carries the year filter. Don't assume this pattern holds at other stores — check each shop's own Vehicles section.

## EDITING dealership capacities (verified live SCT 2026-07-31 — consumer 40→100)

Page: Capacities tab → Dealership sub-tab (`/dse-v2/scheduling-settings/capacities`). Page load fires `POST /api/scheduling/u/settings/capacity/request/option` — capture via XHR hook to read current values: `data.appointmentCapacity[]` per day `{maxCapacity, bdcCapacity, regularCapacity, quickCapacity}`. Grid = 4 rows × 7 day columns of `input.ant-input-number-input`:
- Row y≈314: **Max. Scheduling Capacity** (dealership max — counts BDC + online + walk-ins combined)
- Row y≈355: **Max. BDC Capacity**
- Row y≈396: **Max. Consumer – Regular Capacity** (online booking bucket)
- Row y≈437: **Max. Consumer – Quick Capacity** (quick scheduler bucket)
Columns Sun→Sat at x≈635,735,835,935,1035,1135,1235 (1280×720). Each row also has a "Slot Capacity" link in the Actions column for per-slot overrides.

**Edit procedure per cell (via :9223):** `/mouse` click the input center → `/press Control+A` → `/press` each digit → verify. **THREE PITFALLS hit live:**
1. **Rightmost (Saturday) column is CLIPPED behind the vertical-tab layout container** — the grid scrolls horizontally. `elementFromPoint` at the input's rect returns `dse-v2_verticalTabLayout` div, clicks silently miss. FIX: `input.scrollIntoView({block:'center',inline:'center'})` first, then re-read the rect (it moves, e.g. x1268→x907) and confirm `document.elementFromPoint(cx,cy)===input` before clicking.
2. **Blind coordinate loops corrupt neighbor cells** — a missed click left focus on the previous cell and typed into the WRONG input (overwrote SUN max with the consumer value). ALWAYS: tag the target with `setAttribute('data-jay','t')`, click, then verify `document.activeElement.getAttribute('data-jay')==='t'` BEFORE typing; re-read the whole grid (`inputs.map(i=>i.value)` grouped by rect.y) after each batch and fix strays.
3. Fresh rects every pass — layout shifts after scroll.

**Save & verify:** Save button bottom-right (~x1172,y674). Arm the XHR hook before clicking — the save `POST /api/scheduling/u/settings/capacity` response ECHOES the persisted state (check `regularCapacity` etc. in it = strongest confirmation, beats DOM re-read per the SAVE-VERIFY TRAP). Toast: "Dealership capacities saved successfully". Then Summary tab → **Run Scheduler** (toast "Scheduler is running...") to apply now instead of overnight. Proof it ran: `lastDailySchedulerRunTime` in `GET /api/scheduling/u/settings/appointment` updates within ~10 min (epoch ms; e.g. clicked 7:24 AM → run stamped 7:32:55 AM). `lastWeeklySchedulerRunTime` is the separate weekly run.

SCT baseline (pre-2026-07-31): max 134 (Wed 155) all rows BDC=134/155, consumer regular+quick 40 (Wed 50). Changed consumer regular+quick → 100 all days. Ceiling logic reminder for Joe-type questions: consumer bucket raised past dealership max ⇒ dealership max becomes the online binding ceiling, BUT it's shared with BDC/walk-ins, so heavy call-in days still block online even with a big consumer bucket.

## Testing the CONSUMER scheduler
Direct URL, no dealer-site iframe needed: `https://conscheduling.tekioncloud.com/consumer-scheduling/sign-in/phone?accessToken=americanmotorscorporation_47_876` (SCT; token pattern `americanmotorscorporation_<n>_<dealerId>` — find other stores' tokens by loading the store website's schedule-service page and reading iframe src, e.g. SCT embeds it at stevenscreektoyota.com/schedule-service-here.html). Flow: **Continue as a guest** → Add VIN → Confirm → maintenance packages render (Basic/Basic+/Signature with menu prices — doubles as a menu-price spot check) → Select → Continue ×2 → transport/advisor/calendar page. Disabled calendar days = no availability; a day can be bookable with AM showing "No Slots Available" and only PM slots. Use the plain browser_* tools (public site, no auth). STOP before final confirm on a real customer VIN — it books a real appointment.
**Shop-routing symptom decoded:** older vehicle (e.g. 2021) fails TXM's `year>2023` vehicle limitation → falls through top-down to the MAIN shop → weeks-out availability, while 2024+ vehicles get near-term TXM/Express slots. If consumer capacity is already raised and older cars still can't book, the lever is shop-side: widen TXM/Express vehicle window, add menu opcodes to Express serviceable opcodes, or raise main-shop caps.

## Diagnosing a SINGLE-OPCODE booking failure (verified SCT 2026-08-05, Venza/AIRFILTER) — a DIFFERENT root cause than shop routing

Symptom looks identical to the shop-routing case above ("no slots for weeks, then it dumps into Main Shop"), but when the complaint is about ONE SPECIFIC standalone service (e.g. "just an air filter replacement" — no menu package), check the **opcode's own Active/Inactive status FIRST**, before re-diagnosing shop vehicle-filters/capacity again. A shop can list an opcode in its Servicable Opcodes AND have wide-open vehicle filters AND healthy capacity, and the booking will still fail if the underlying opcode is Inactive — no shop can schedule a dead opcode, so the widget silently falls through to whatever fallback (usually the busiest shop), producing the same "weeks out" symptom.

**Fast check — opcode Active/Inactive status:** navigate directly to `https://app.tekioncloud.com/ro/opcode/edit/<OPCODE>` (e.g. `/ro/opcode/edit/AIRFILTER`). The page header reads `Opcode Details: <OPCODE> - <description>` immediately followed by **`Active`** or **`Inactive`** as plain text — no need to open the Opcode List and search. This is much faster than the Opcode List page's "Search here..." bar, which did NOT reliably filter 2,066 results by typed opcode/description in testing (still showed non-matching rows after Enter).

**Watch for near-duplicate opcodes:** SCT had both `AIRFILTER` ("REPLACE ENGINE AIR FILTER AND CLEAN AIR BOX" — **Inactive**) and `AIR` ("CUSTOMER REQUESTS TO REPLACE AIR FILTER" — **Active**). Same trap as the earlier 4Runner rotation case (duplicate "(N)"-suffixed opcodes) — always check ALL similarly-named opcodes' status, don't stop at the first match.

**Filtering a shop's OWN Servicable Opcodes table** (to confirm/deny an opcode is even in a shop's list) — the per-shop detail page has a dedicated search box scoped to that table, separate from the global header search:
1. Scroll the `Servicable Opcodes` heading into view (`scrollIntoView({block:'center'})`) — the table's `input.ant-input[placeholder="Search..."]` only gets correct on-screen coordinates after scroll.
2. `/mouse` click the input to focus it, then set the value via native setter + dispatch (do NOT use `/type` with a CSS selector here — it returned a 500 after a 30s timeout in testing, likely selector ambiguity with the OTHER `Search...`/`Search here...` inputs on the page):
   ```python
   api("/eval","POST",{"js":
     "(()=>{const el=document.activeElement;"
     "const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
     "s.call(el,'AIR'); el.dispatchEvent(new Event('input',{bubbles:true})); return 'typed';})()"})
   ```
3. Read the result: `document.body.innerText` between `Servicable Opcodes` and `Results Per Page` — `No rows found` = definitively not in that shop's list.

**Pagination / row-click coordinate trap (cost significant time 2026-08-05):** on this shop-detail page, clicking a cached `/eval`-derived coordinate for pagination numbers ("2", "Next") or even for a shop-name row link frequently **navigated to a totally unrelated page** (Appointments calendar, Opcode List, RO detail, /home) instead of doing the expected in-page action. Root cause is almost certainly stale coordinates from a previous `/eval` call being reused after the SPA re-rendered, combined with concurrent notification toasts stealing the click. FIX: **re-derive the element's coordinates from a fresh `/eval` immediately before every `/mouse` click** — never reuse coordinates from an earlier snapshot/response, even a few calls back. If a click lands somewhere unexpected, don't fight it — `/navigate` straight back to the known shop-detail URL (`/dse-v2/scheduling-settings/shops/<uuid>`) and re-verify with a fresh `document.body.innerText` check before continuing.

**Diagnostic order for "can't book appointment X" going forward:**
1. Reproduce live in the consumer widget with the exact VIN (per "Testing the CONSUMER scheduler" above).
2. Check the OPCODE's own Active/Inactive status (`/ro/opcode/edit/<code>`) — a dead opcode can't book anywhere, full stop.
3. Only then move to shop-level checks: vehicle year/make filters, serviceable-opcode list membership, capacity ceilings (per the sections above).
4. Don't assume a prior fix for the SAME vehicle (e.g. a shop vehicle-filter widening) covers a NEW complaint about a DIFFERENT service on that vehicle — each opcode/service has its own failure surface.

## Diagnosing "Main Shop keeps absorbing Express-type quick-service jobs" (SCT 2026-08-05, Ann Souza LOF+car-wash case)

Symptom: quick-maintenance appointments (LOF, rotation, cabin filter, etc.) that should land in Express keep showing up in Main Shop's day-view slots, with no obvious single cause. Root-cause method = **compare each shop's Servicable Opcodes list directly, don't theorize** (evidence-first, per the never-guess rule):

1. Shops tab → open each candidate shop (e.g. Main Shop, Express) → scroll to **Servicable Opcodes** table.
2. The opcode list per row is truncated with a **`+N` button** (e.g. "1TIRE, 2TIRE, ... +39") — this is a real `<button>` element, NOT a span/link. Find and click it directly via JS, no mouse coordinates or `scrollIntoView` needed — `element.click()` works even when the element is off-screen/below the viewport:
   ```js
   Array.from(document.querySelectorAll('button')).filter(e=>e.innerText.trim()==='+39')[0].click()
   ```
   The full opcode list renders inline as `- OPCODE,` lines appended after the row; re-read `document.body.innerText` to capture it.
3. Diff the two shops' full Maintenance Service opcode lists. If they're **near-identical** (e.g. both Main Shop and Express list LOF, ROTATE, CABIN, TPMS, WIPER, MPI, DETAIL, CODECHECK, CAS, RAF, RACF, MPVI, OKAL, MILLIGHT, FMAT, and the BG* fluid-flush codes), there's no exclusivity constraint forcing quick-service jobs to Express — the scheduling engine can legally place them in either shop.
4. Cross-check the two settings that turn "can go either way" into "actually does go either way": **General tab → "Suggest First Available Slot"** and **Consumer Scheduling tab → "Enable 'Any Service Advisor' for Appointment Booking"**. Both ON (SCT baseline) means the engine grabs whichever shop/advisor has an open slot first rather than preferring the more-specific shop.
5. **Fix (not yet applied as of 2026-08-05 — awaiting Joe's go-ahead):** remove the overlapping quick-maintenance opcodes from **Main Shop's** Servicable Opcodes list (keep them exclusive to Express). This removes Main Shop's eligibility for those opcodes so the engine stops offering it for LOF-type jobs. This is a Published, fleet-wide scheduling config — treat as a live-change-needs-approval item like other Published Tekion configs, don't just apply it.

**Default shop indicator** (useful for any "which shop is the catch-all" question): on the Shops list page (`/dse-v2/scheduling-settings/shops`), each row has a button with class containing `defaultShopIcon`. If that button's class list ALSO includes the suffix `defaultShopIconDisabled`, that shop is NOT the default. The one row WITHOUT the `Disabled` suffix is the current default/catch-all shop. At SCT (2026-08-05) that was **Express** — TXM, Mobile Service Unit, and Main Shop all carried the `Disabled` suffix.

## Gotchas
- **Lowest ceiling wins** across all capacity/hours settings.
- **Shop order = most-restrictive-first**; default shop = catch-all.
- **Changes don't apply until overnight run** unless you hit **Run Scheduler** (and even then, day-level availability can lag to the next overnight run — see note above).
- **Global holidays** live in Dealer Configuration → Dealer Details (grayed-out holidays editable only there).
- **Vehicle exclusions**: better to **include** the makes you service than try to exclude all others (limited to provisioned makes).
- **Year filter operator is always strict** (Greater Than / Equals / Less Than only) — no ≥/≤/between. "Greater Than N" already covers every future year; don't re-edit when asked to "add" a later year that's already above N.
- **Concierge requires the mobile app** — not available on desktop write-up.
- **Notify parts department** toggle controls whether parts are alerted for parts-on-appointment opcodes (all vs time-windowed).
- VIN-mandatory often OFF; promise-time mandatory is a separate toggle.

## Related skills
- `tekion-process-automation` — CRM lead automation (companion)
- `tekion-service-settings` — broader service config map
- `tekion-service-menu-setups` — service menus/pricing
- `tekion-sitemap` — master nav map
