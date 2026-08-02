---
name: tekion-coupon-management
description: Create/edit service discount coupons in Tekion's Coupon Management app (e.g. tire promos like Bridgestone B3G1, $-off or %-off labor/parts coupons). Covers the real URLs, form mechanics (old antd calendar, react-select GL account), toggle defaults, GL split conventions, and verification. Verified live at SCT 2026-08-02.
triggers:
  - tekion coupon
  - create coupon
  - tire promotion
  - B3G1
  - discount coupon setup
  - coupon management
---

# Tekion Coupon Management — create/edit coupons

Verified live at SCT (dealer 876) 2026-08-02 building the Bridgestone B3G1 coupon.
All work via the :9223 persistent browser (load `tekion-sitemap` + `persistent-browser-server` first).

## URLs (the real ones)
- **Coupon List** = `/core/coupons` ✅ — reach via nine-dots App Grid (icon at ~30,32) → search "coupon" → Coupon Management tile (/ Core). ⚠ `/core/coupon-management` renders BLANK (107 chars); `/coupon-management` bounces to /home.
- **Create** = `/core/coupons/create`
- **Edit** = `/core/coupons/edit/<base64(couponCode)>` — e.g. FLUID → `RkxVSUQ=`. Direct nav works; also clicking the coupon-code cell in the list opens it.
- Permissions: Coupon Management Edit + View (KB0025143).

## KB anchors
- **KB0025143** — create-a-coupon field list.
- **KB0026638** — coupon eligibility is **gated at the OPCODE level** ("Coupon Eligible" toggle in Opcode Management). If a valid active coupon won't attach to a job, check the opcode first. Also documents coupon Split (Customer Discount % vs Dealer Absorb %) and the not-applying checklist: Active? opcode in Applicable Opcodes? date range? usage limit?

## Form mechanics (order matters!)
1. **Text fields** (`#couponCode`, `#description`): native value-setter + input+blur events works.
2. **Dates** — OLD antd calendar, NOT ant-picker. `/type` into the "Select Date" input → **HTTP 500**. Instead: `/mouse` the date input to open the popup, then `/mouse` the day cell. Cells = `.ant-calendar-date` (there are 42; duplicates of a day number = current-month vs next-month cell — pick the one WITHOUT `ant-calendar-next-month-btn-day` on its parent). Next-month arrow = `.ant-calendar-next-month-btn`; header month check = `.ant-calendar-my-select` (reads e.g. "Sep2026").
3. **Dropdowns** (Coupon Type / Applied On / Pricing Method): classic ant-select. `/mouse` the select, options render as `.ant-select-dropdown li` — /mouse the option. Coupon Type = Flat | Target Selling Price. Applied On = Labor | Parts | Labor & Parts. Pricing Method = $ | %.
4. **PITFALL — set dropdowns BEFORE value fields.** The value input's id depends on Pricing Method: `$` → `#flatAmount`, `%` → `#percentage`. A fallback regex like `/flat|value/i` can silently match `#couponCode` (contains no… it matched via `value_undefined`/couponCode fallback and OVERWROTE the coupon code with "25"). Always target the exact id and RE-VERIFY `#couponCode` afterward.
5. **GL Account (Cost Center split row)** — react-select with a ~4px-wide invisible input. Find it by bounding-rect zone (the empty input in the split table row), `setAttribute('data-jay','gl')`, `/mouse` its container, then `/type {selector:"input[data-jay='gl']", text:"4702"}` → option "4702 - SLS - ASM DISCOUNT" appears → `/mouse` it. Then set the "Account Split" placeholder input to `100` via native setter.
6. **Toggles** (`.ant-switch`, checked = `ant-switch-checked`): scrollIntoView + `/mouse` center. **Default state trap:** "Allow Coupon to be added to the same RO more than once" starts **ON** — turn OFF unless multi-use wanted. "Apply coupon at RO, Appointment, Quote level" starts OFF — SCT convention is ON (matches FLUID/CABINANDAIRFILTER).
7. **Save** = bottom-right button (~1211,689). Success = toast "Coupon successfully created" and redirect to `/core/coupons`. **Verify with a true remount** (nav /home → back to /core/coupons → find the code in the list) per the SAVE-VERIFY TRAP.

## SCT conventions (from existing 27 coupons)
- GL split accounts: **Labor → 4402 - SLS - ASM DISCOUNT**, **Parts → 4702 - SLS - ASM DISCOUNT**, 100% split, Split By = Flat (Gross also used on % coupons e.g. CABINANDAIRFILTER).
- Pay Type = CP/Customer Pay, Pre-Tax.
- "Include Services" (service-type/opcode/skill filters) and "Include Parts" filters exist under Overrides once Applied On includes that side — CABINANDAIRFILTER uses Include Services w/ opcode list. Leaving filters empty = advisor applies manually to the right job.

## Buy-3-get-1 (B3G1) pattern
4th-tire-free = **25% off Parts** on the tire job (mathematically identical when all 4 tires are the same model, which the OEM promo requires). Decisions to flag to Joe: expiry = install-by date (grace week) vs sale-end date; optional Cap Amount as a guardrail since the % hits ALL parts on the job it's applied to.

## Pitfalls recap
- `/core/coupon-management` = blank trap; use `/core/coupons`.
- `/type` into date fields = 500; use calendar cell clicks.
- Value-field id switches with Pricing Method; verify couponCode wasn't clobbered.
- "Allow more than once" defaults ON.
- Edit-page reads are the fastest way to clone store conventions — open an existing similar coupon first and record its GL/toggles before creating.
