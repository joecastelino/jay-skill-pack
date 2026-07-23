---
name: tekion-menu-custom-price-row
description: Set a vehicle-scoped CUSTOM package price and labor hours on a Tekion Service Menu by adding a new vehicle row (e.g. "2014 Camry 90K VNM = 2.4 hrs / $469.88"). Use when Joe wants a specific vehicle's menu package price/hours changed without touching other vehicles or tiers. Verified SCT 90K menu 2026-07-03.
---

# Tekion Menu Custom Price/Hours Vehicle Row

Sets a fixed package price + labor hours for ONE vehicle scope on ONE tier of a service menu.
This is the fix surface when Opcode Management Overrides on a TEK menu opcode shows NO Labor module
(Cost-Center only) — package price/hours live on the MENU vehicle row, not the opcode.

**Verified case**: RO 572276 Kevin's 2014 Camry — 90K VNM 2.1hrs/$439.80 → 2.40hrs/$469.88.
Menu edit URL: `/ro/service-menu-setups/edit/693b0d30a21e1d4aa518d44f` (SCT 90K menu, dealer 876).

**LIVE STATE (2026-07-06)**: This fix is DONE — Joe scoped it to "just the 2014 Camry" (all trims);
new row Saved + Published + quote-verified on Kevin's VIN 4T1BF1FK1EU406693 (2.40 hrs / $469.88, other
tiers/vehicles untouched). This is an INTENTIONAL override, not a bug, if 2014 Camry 90K quotes differ
from other years. **OPEN LOOSE END**: RO 572276 itself still shows 2.1/$439.80 — Joe never answered
whether Jay should delete/re-add the menu line on the RO (Working status → tech reassignment needed)
or Kevin handles it. Also uncleaned: ~5 throwaway Highlander quotes (Jeff Borg VIN 5TDKZRFH2HS511864)
+ Camry verification quotes at SCT.

## Prerequisites
- persistent-browser-server on :9223, logged in (tekion-autonomous-login), dealer VERIFIED (876=SCT — session drifts!)
- Step zero (Joe's rule): pull a throwaway quote on the exact VIN first to baseline the symptom + capture decoded trim.

## Procedure

### 1. Add the scoped vehicle row (bottom of Menu Included Services = wins precedence)
- Menu list → row kebab (icon-overflow) → Edit.
- Bottom blank row: Make dropdown → check Toyota. **Dismiss dropdowns by toggling their own trigger or opening the next cell — never click random elements.**
- Model cell: checkbox multi-select, type to filter, check ONLY the model (verify with `checkedOpts` scan — "Camry" not "Camry Hybrid" etc.).
- Year cell: check the single year.
- Trim cell = `input.ant-input` placeholder "Select Vehicle Trim". Clicking it opens the **Trim Details modal** (radio "All trims (including future trims)" vs "Specific trims" + Filters). For "just the 2014 Camry" scope keep All trims → Save (Save is a SPAN not BUTTON — click last leaf element with text 'Save' inside modal). Input value becomes "All trims selected".

### 2. Expand the new row
Caret needs full event sequence: `pointerdown,mousedown,pointerup,mouseup,click` (PointerEvent for pointer*). Plain .click() and even mousedown/mouseup/click alone silently fail. Verify expansion by counting "Modify System Services" leaf nodes (may render off-viewport at negative y — scrollIntoView).

### 3. Set Custom price + hours (the core discovery)
Expanded row sections: Modify System Services / Add Services / Modify System Inspections / Add Inspections / **Menu Price** / **Labor Hours**.

**TIER TRAP**: Header row shows `Basic | Basic | Basic + | Value | Signature | Premium` but there are only 3 real columns with input IDs:
- `BASIC_NORMAL_0` = Basic (BNM)
- `VALUE_NORMAL_0` = **the "Basic +" displayed column = VNM tier** ← 90K VNM lives here
- `PREMIUM_SEVERE_0` = Signature/Severe (SNM/PSM)

**GATING**: all three per-tier selects are `disabled` until the master row-level dropdown (`PRICE_TYPE_0` / `HOURS_TYPE_0`) is set to **Custom**. Sequence:

1. Open `PRICE_TYPE_0`: `inp.focus()` + dispatch `keydown/keyup ArrowDown (keyCode 40)`. **This is the ONLY way that works** — mousedown on `-control`, /mouse click on coords, and clicking the singleValue all fail to open these react-selects.
2. Pick option "Custom" (options render in-DOM: Custom | Sum of Services | Total Menu Price | Total Labor + Parts Price). Click option with mousedown/mouseup/click MouseEvents.
3. Per-tier selects now enabled. Open `VALUE_NORMAL_0` (same ArrowDown trick — filter by y-coordinate, the ID is NOT unique: appears in Menu Price row AND Labor Hours row AND as hidden dups at negative y; also matches ant-checkbox-inputs elsewhere — always filter `offsetParent!==null && !className.includes('checkbox')` + y-range).
4. Pick **"Total Menu Price"** → an `input.ant-input-number-input` (placeholder 0.00) appears in that cell. Set via native value setter + input/change/blur events. e.g. `469.88`.
5. Labor Hours section: `HOURS_TYPE_0` → Custom (options: Custom | Sum of Services | Menu Labor Hours). Then `VALUE_NORMAL_0` in the hours row → **"Menu Labor Hours"** → number input appears → set `2.4` (displays 2.40).
6. Untouched tiers stay "Sum of Services" — they keep pricing from services. Only the customized tier/vehicle changes.

### 4. Save → hard reload verify → Publish (Joe's go required)
- Bottom Save button. Success toast "Service menu saved successfully".
- **Hard reload the edit URL**, re-expand the row (note: reload restores OTHER rows' expansion state — collapse strays first; carets are all `icon-caret-down` class regardless of state, find by y-offset from the Camry row ~+13px), confirm number inputs persist (469.88 / 2.40) and types = Custom.
- Publish → toast "Service menu published successfully". No confirm modal.

### 5. Quote verification
Fresh throwaway quote: /ro/quotes → Create Quote → `input#vin` type VIN → **Enter keydown to decode** (type alone doesn't trigger) → `input#vehicleOdometer` → Continue. Service Menu carousel → click interval "90K mi" → **tier TABS** (Basic / Basic + / Signature) — click each and read `Package OpCode : TEKxxxxx` + price from body text. Basic=TEK90000BNM, Basic+=TEK90000VNM. Add To Quote to confirm hours on the line ("2.40 hrs" + "$469.88").

## Pitfalls
- Session drifts dealers between tasks — verify 876 before anything.
- Row-by-row save discipline still applies if touching multiple rows (batched edits silently discarded).
- The quote's "TRIM" may default-decode (e.g. SE 2.5L AT) — fine for row scoping when using All-trims.
- RO lines do NOT reprice retroactively — existing RO needs menu line delete/re-add to repull pricing (tech reassignment needed if job Working).
- execute_code 300s cap; /tmp screenshots + vision_analyze for visual verification.
