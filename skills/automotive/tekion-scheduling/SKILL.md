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
