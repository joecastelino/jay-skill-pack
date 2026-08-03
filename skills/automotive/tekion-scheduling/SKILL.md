---
name: tekion-scheduling
description: Tekion Service Scheduling Settings — appointment slot times, capacities, service advisors, shops, transportation, vehicle/opcode exclusions, and the consumer scheduler. Covers the "lowest ceiling wins" capacity model, shop top-down matching, the daily overnight scheduler + "Run Scheduler" button, parts-on-appointment notifications, and the concierge mobile write-up flow. Load for any appointment/scheduling/capacity setup or troubleshooting in Tekion.
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
- To apply changes immediately: **Summary tab → Run Scheduler** button — scrapes current settings and pushes changes live in real time (no waiting for overnight run).

## Concierge / Mobile Write-Up Flow
- Concierge workflow is **ONLY available through the mobile write-up process** (Tekion ARC mobile app).
- Used for night-drop, pickup & delivery, mobile service, tow-ins — **the only way to capture a digital signature when the customer is NOT in front of you.**
- Flow: check in appt → **assign a Porter** (customer auto-texted ETA) → confirm vehicle/mileage → MPVI/inspection (drag to defer/delete line items, set severity red/yellow) → present menu (can be made mandatory in check-in setups) → confirm contacts/addresses (pencil to override) → **CP link texted/emailed to customer** → customer signs estimate in consumer portal → screen auto-refreshes → **RO number created**. Digital signatures show **green** on PDF views.
- Non-appointment (night-drop/tow-in): change **transportation type to Concierge** in the delivery screen to use the same flow.

## Diagnosing "no appointments available" (verified SCT 2026-07-30)
When someone reports the scheduler won't offer slots for days/weeks, do NOT start with settings theory — pull the booked-vs-capacity numbers first. All via the :9223 persistent browser (in-page XHR hook; raw fetch to /api/scheduling 500s "Token doesn't exist" — the app's axios interceptor adds auth a bare fetch can't).

1. **Ground truth = Appointments calendar month stats.** Navigate `/dse-v2/appointments` (redirects to `/appointments/calendar/month`), arm an XHR hook capturing `scheduling` URLs, click Month / the toolbar arrows (right-arrow icon ~x845,y162; Today/Month/Week/Day at ~y160). Each nav fires `POST /api/scheduling/u/appointment/calendar/month/stats` (body = appointmentDateTime GTE/LTE epoch-ms filters). Response: per-day `appointmentDayStatistics {maxAppointmentCapacity, bookedAppointmentCount, missedAppointmentCount, colorCodeInfo{NEW,COMPLETED,...}}` + per-slot stats on week view (`/calendar/week/stats`). booked≈max through day N ⇒ genuinely full until day N+1; that's the answer.
2. **Capacity ceilings** = `GET /api/scheduling/u/settings/appointment` (fires on Scheduling Settings load). Key fields: `capacity[]` per-day `maxCapacity` (dealership max, the usual lowest ceiling), `bdcCapacity`, `regularCapacity`/`quickCapacity` (Consumer online buckets — often tiny, e.g. SCT 40/day vs dealership 134 — online customers hit "full" far earlier than BDC), per-slot arrays (`maxSlotCapacity` etc.; capacity 0 rows = blocked slots like lunch), `bookingFrom/Upto` + `bdc…`/`cs…` variants (booking windows), `lastDailySchedulerRunTime`/`lastWeeklySchedulerRunTime` (confirm the scheduler actually ran), `shouldCheckEndOfDayCapacity`, `enableShopOverBooking`. NOTE: booked counts can EXCEED maxCapacity historically — walk-ins/check-ins land on the calendar regardless of cap, so July running 150-180 against a 134 cap means the cap is undersized vs real throughput.
3. **Shop detail** = click a shop row on `/dse-v2/scheduling-settings/shops` (hook captures `GET .../settings/serviceShop/<uuid>`): `hours[]`, `blocks[]` (e.g. daily 11:30-12:45 lunch ⇒ slot cap 0-1), `bookingFrom/Upto` overrides, `vehicles[]` include/exclude (e.g. TXM = Toyota year>2023 only; older cars fall through to next shop top-down), `maximumHoursToSell`, `shopOpcodes[]` (per-service-type opcode lists + slot/daily/weekly capacityRestriction). SCT shop UUIDs: Express=e762d8da-7d6f-4c77-bf77-479a690a2d1f, TXM=8e56605b-6520-44f5-8e8d-068917b870d7. TXM vehicle window as of 2026-08-01: Toyota, Year Greater Than 2016 (was >2023; Joe widened it so 2017+ vehicles route to TXM).
4. **Summary tab board** (`/dse-v2/scheduling-settings/summary`, `POST .../settings/summary`) shows capacity CONFIG (originalCapacity/availableCapacity per slot, advisor totalCapacity=32/day each), NOT net-of-bookings — don't read it as availability. Shop filter = tekion-select at ~x685,y243; date = ant-calendar input at ~x419,y238.
5. **OpenAPI `/service-appointments:search` is NOT reliable for day counts** — filter format `{"field":"appointmentDateTime","operator":"BTW","values":[ms,ms]}`, pageSize max 50, paginationToken; but pagination 500s partway and default sort samples recent creations ⇒ massive undercounts vs calendar stats. Use it for appointment detail lookups only; trust calendar stats for volume.
6. Rearm the XHR hook after every page navigation (SPA route changes keep it, hard navigations kill it).

Typical verdict template: booking windows fine + scheduler ran recently + days booked to the dealership cap ⇒ not a bug, capacity-starved; fixes = raise dealership max and/or consumer allocation, then Run Scheduler.

## EDITING a shop's Vehicle limitation (verified live SCT 2026-08-01 — TXM year>2023 → year>2016)

Use case: older vehicles fail a shop's year filter, fall through to the booked-solid Main shop, consumer sees "weeks out". Fix = widen the year window on the shop row.

1. Shops tab → click shop row → detail page `/dse-v2/scheduling-settings/shops/<uuid>`. **Vehicles section renders BELOW the viewport** (~y1336 on load) — `scrollIntoView({block:'center'})` on the operator select first, then re-read rects.
2. Row = three tekion-selects: **operator | year | make**. Operator options are ONLY `Greater Than / Equals / Less Than` — **Greater Than is STRICT**, so "2017 → current" = `Greater Than 2016`. It's open-ended upward (covers 2026 + future model years automatically; no upper bound exists).
3. Year dropdown: clicking the select renders the FULL 1970–2025 option list; **typing into the react-select search input does NOT filter it** — compute the target option's y from the returned list and `/mouse` click it directly. Options above the viewport have negative y; scroll or pick from the visible range.
4. Save (bottom-right, ~x1211,y689) → toast **"Shop Updated Successfully. Changes will be effective starting from next day."** + PUT `/api/scheduling/u/settings/serviceShop/<uuid>` 200.
5. **Verify with a TRUE remount** (nav to /home, then back to the shop URL — per the SAVE-VERIFY TRAP a #hash re-nav re-reads your own unsaved DOM). Persisted payload shape: `vehicles:[{operator:"INCLUDE", equalityRelation:"GREATER_THAN", vehicleInfo:{year:"2016", make:"toyota"}}]`.
6. Summary tab → **Run Scheduler** to apply now. NOTE: the on-demand run is a LIGHTER pass than the overnight rebuild — consumer availability may only partially improve until the next overnight run; re-test the next morning before concluding it didn't work.
7. **Routing-flip tell on the consumer side:** re-run the consumer test with the same VIN — if the earliest bookable day now shows **AM slots starting at the shop's opening time (e.g. 7:00 AM = TXM)** where it was PM-only before, the vehicle is routing into the widened shop even if the earliest *day* hasn't moved (that's real demand, check booked-vs-max via calendar month stats).
8. Hard `location.href` navigation KILLS the XHR hook — after any hard nav, rearm the hook and use `history.pushState + PopStateEvent` SPA navigation to make the app refire settings/serviceShop/stats calls into your capture.

## Testing the CONSUMER scheduler
Direct URL, no dealer-site iframe needed: `https://conscheduling.tekioncloud.com/consumer-scheduling/sign-in/phone?accessToken=americanmotorscorporation_47_876` (SCT; token pattern `americanmotorscorporation_<n>_<dealerId>` — find other stores' tokens by loading the store website's schedule-service page and reading iframe src, e.g. SCT embeds it at stevenscreektoyota.com/schedule-service-here.html). Flow: **Continue as a guest** → Add VIN → Confirm → maintenance packages render (Basic/Basic+/Signature with menu prices — doubles as a menu-price spot check) → Select → Continue ×2 → transport/advisor/calendar page. Disabled calendar days = no availability; a day can be bookable with AM showing "No Slots Available" and only PM slots. Use the plain browser_* tools (public site, no auth). STOP before final confirm on a real customer VIN — it books a real appointment.
**Shop-routing symptom decoded:** older vehicle (e.g. 2021) fails TXM's `year>2023` vehicle limitation → falls through top-down to the MAIN shop → weeks-out availability, while 2024+ vehicles get near-term TXM/Express slots. If consumer capacity is already raised and older cars still can't book, the lever is shop-side: widen TXM/Express vehicle window, add menu opcodes to Express serviceable opcodes, or raise main-shop caps.

## EDITING a shop's vehicle-year limitation (verified live SCT 2026-08-02 — TXM >2023 → >2016)
Shops tab → click shop row → detail page `/dse-v2/scheduling-settings/shops/<uuid>`. Scroll to the **Vehicles** section (Include/Exclude radio + Year/Make/Model row of tekion-selects; it sits BELOW the viewport — `scrollIntoView` the operator select first, then re-read rects).
- **Year operator options are ONLY: Greater Than / Equals / Less Than** — strict comparisons, NO ">= " and NO explicit range. To express "2017 → current" you set **Greater Than 2016**. Greater Than is open-ended upward (covers future model years automatically) — when Joe asks "add 2026 too," nothing to change.
- Year dropdown renders the FULL 1970+ option list (typing in the react-select input does NOT filter it) — find the target year's option by text and click its coordinates.
- **Save & verify:** Save button bottom-right → arm XHR hook first; the save is `PUT /api/scheduling/u/settings/serviceShop/<uuid>` (200) + toast "Shop Updated Successfully. Changes will be effective starting from next day." Per the SAVE-VERIFY TRAP, remount fully (nav to /home then back) and re-read; persisted shape in the GET: `vehicles:[{operator:"INCLUDE",equalityRelation:"GREATER_THAN",vehicleInfo:{year:"2016",make:"toyota",...}}]`. Then Summary → **Run Scheduler** to apply now.
- **Consumer-side proof of TXM routing:** re-run the consumer scheduler test with an affected VIN — the tell that the vehicle now lands in TXM is **AM slots from 7:00 AM** appearing (TXM/Express open 7:00; Main-shop-routed vehicles showed "No Slots Available" AM / PM-only). Earliest-day may still be far out if the store is genuinely booked to the dealership cap — read booked-vs-max from calendar month stats before calling it a routing failure.
- Note: Express at SCT has NO vehicle limitation (blank Year/Make/Model = all pass); only TXM filters by year.

## EDITING a shop's vehicle-year limitation (verified live SCT 2026-08-02, TXM 2023→2016)
Shop detail page → scroll to **Vehicles** section (Include/Exclude radio + Year/Make/Model row of tekion-selects). The Year operator select offers ONLY **Greater Than / Equals / Less Than** — no ≥, so "2017 to current" = **Greater Than 2016** (always pick target-year-minus-1; open-ended upward, future years included automatically). Procedure via :9223: scrollIntoView the `singleValue` div reading the current year → re-read rect (moves after scroll) → /mouse click the `-control` → option list renders ALL years 1970+ (typing in the react-select input does NOT filter here — compute the option's y from the returned list and click it; options can render at negative y, scroll first). Save button bottom-right → PUT `/api/scheduling/u/settings/serviceShop/<uuid>` 200 + toast "Shop Updated Successfully. Changes will be effective starting from next day." → verify by TRUE remount (nav to /home then back, per SAVE-VERIFY TRAP) AND by re-capturing the serviceShop GET: `data.vehicles[] = {operator:"INCLUDE", equalityRelation:"GREATER_THAN", vehicleInfo:{year:"2016", make:"toyota"}}`. Then Summary → Run Scheduler. **Consumer-side proof of routing:** re-run the Venza-style consumer test — a vehicle newly qualifying for TXM shows **7:00 AM slots** (TXM's open) where before it was PM-only on the main shop; earliest bookable DAY may not move if the store is genuinely booked to cap (that's demand, not config). Express shop at SCT has NO vehicle limitation (blank row = all years pass). Note: mid-day "Run Scheduler" is a lighter pass than the overnight rebuild — day-level availability may only shift after the nightly run.

## EDITING a shop's vehicle limitation (verified live SCT 2026-08-01 — TXM year >2023 → >2016)

Page: Shops tab → click the shop row (URL becomes `/dse-v2/scheduling-settings/shops/<uuid>`; loads `GET /api/scheduling/u/settings/serviceShop/<uuid>`). Scroll to the **Vehicles** section (Include/Exclude radio + Year/Make/Model row of tekion-selects — it sits BELOW the viewport, `scrollIntoView` the operator select first, then re-read rects).

- **Year operator options are ONLY: Greater Than / Equals / Less Than** — no ≥ and no range. So "2017 through current" = **Greater Than 2016** (strict operator, open-ended upward — future years like 2026+ are automatically included; don't add a second row). Joe's "add 2026 too" was already covered.
- The year dropdown renders ALL years 1970→current as options; the react-select filter-typing may not narrow the visible list — just compute the target option's y from the returned list and `/mouse` click it.
- **Save** (bottom-right ~x1211,y689) → toast "Shop Updated Successfully. Changes will be effective starting from next day." → verify with a TRUE remount (nav to /home then back — SAVE-VERIFY TRAP: same-URL re-read shows your own unsaved DOM) and/or re-capture the serviceShop GET: `data.vehicles = [{operator:"INCLUDE", equalityRelation:"GREATER_THAN", vehicleInfo:{year:"2016", make:"toyota"}}]`.
- Then **Summary → Run Scheduler** to apply now. NOTE (observed 8/1): the on-demand Run Scheduler is a LIGHTER pass than the overnight rebuild — the consumer calendar picked up the routing change (AM slots appeared where it was PM-only) but earliest-day availability didn't shift until the overnight run.
- **Consumer-side proof of routing:** re-run the customer-view test with the affected VIN; the tell for TXM routing is the **7:00 AM slot block appearing** (TXM/Express hours) where before it was "No Slots Available" AM + PM-only (main shop).
- SCT Express shop has **NO vehicle limitation** (blank Year/Make/Model = all vehicles pass); only TXM carries the year filter.

## EDITING a shop's vehicle year limitation (verified live SCT TXM 2026-08-01 — >2023 → >2016)
Shops tab → click the shop row (fires `GET /api/scheduling/u/settings/serviceShop/<uuid>`, capture via XHR hook to read config). Scroll to the **Vehicles** section (Include/Exclude radio + Year/Make/Model row of tekion-selects; starts far below viewport ~y1336 — `scrollIntoView` the operator's `singleValue` div first, then re-read rects).
1. **Operator select** offers ONLY `Greater Than / Equals / Less Than` — all STRICT. There is no ≥, so "year X to current" must be entered as **Greater Than X−1** (2017→current = Greater Than **2016**). No "Less Than or Equal" either — a bounded range needs Equals rows or can't be expressed.
2. **Year select PITFALL:** typing into its react-select search input does NOT filter the list (native-setter + input event accepted but options stay 1970–2025) — the full list renders anyway; find the target option (`[class*="-option"]`, may be at negative y) and `/mouse` click it directly.
3. Verify the row via visible `singleValue` texts (e.g. `Greater Than | 2016 | Toyota`), then **Save** (bottom-right ~x1211,y689). Success = `PUT .../settings/serviceShop/<uuid>` 200 + toast "Shop Updated Successfully. Changes will be effective starting from next day."
4. **Remount-verify** (SAVE-VERIFY TRAP): nav to /home then back to the shop URL, re-read the Vehicles section text.
5. Apply now: Summary tab → **Run Scheduler** (button ~x1139,y168; toast "Scheduler is running..."); availability rebuild takes ~10 min.

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

## Gotchas
- **Lowest ceiling wins** across all capacity/hours settings.
- **Shop order = most-restrictive-first**; default shop = catch-all.
- **Changes don't apply until overnight run** unless you hit **Run Scheduler**.
- **Global holidays** live in Dealer Configuration → Dealer Details (grayed-out holidays editable only there).
- **Vehicle exclusions**: better to **include** the makes you service than try to exclude all others (limited to provisioned makes).
- **Concierge requires the mobile app** — not available on desktop write-up.
- **Notify parts department** toggle controls whether parts are alerted for parts-on-appointment opcodes (all vs time-windowed).
- VIN-mandatory often OFF; promise-time mandatory is a separate toggle.

## Related skills
- `tekion-process-automation` — CRM lead automation (companion)
- `tekion-service-settings` — broader service config map
- `tekion-service-menu-setups` — service menus/pricing
- `tekion-sitemap` — master nav map
