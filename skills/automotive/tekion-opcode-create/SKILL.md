---
name: tekion-opcode-create
description: >
  Create a NEW opcode from scratch in Tekion's Opcode Management application —
  the full Default-tab field reference (opcode type, eligibility, category,
  service type, labor, pay-type pricing, parts, cost centers, associated opcodes,
  sublet, auto-dispatch). Canonical workflow distilled from Tekion KB0025686.
  Use when asked to CREATE/build a new opcode (vs editing pricing on an existing
  one — for that use tekion-opcode-default-pricing / tekion-opcode-overrides).
triggers:
  - create a new opcode
  - create opcode tekion
  - new opcode management
  - build an opcode
  - opcode fields reference
  - opcode service type
  - sublet opcode
  - associated opcodes
---

# Tekion — Create a New Opcode (Opcode Management)

Authoritative field-by-field reference for creating a new opcode, distilled from
Tekion's own KB **KB0025686** (PDF saved at `~/tekion-kb/pdfs/`, text at
`~/tekion-kb/text/Create_a_new_opcode_in_the_Opcode_Management_application.txt`).

**Companion skills:**
- Edit labor $ / add parts on an existing opcode → `tekion-opcode-default-pricing`
- Vehicle/part override ROWS → `tekion-opcode-overrides`
- Verify committed state via API → `tekion-opcode-api`
- Navigation / URLs → `tekion-sitemap`

## Permissions & Nav
- Permissions: **Operation Management View** + **Operation Management Update**
  (`Roles > Permissions > Parts > Parts`).
- Nav: **App Grid > Settings > Service Settings > Opcode Management** → Opcode List
  → **Create Opcode** (upper-right). Direct URL pattern: `/ro/opcode`
  (list) / `/ro/opcode/edit/<OPCODE>` (edit). The **Default tab** is the default view.

## Default-tab sections (in order)

### Opcode
- **Opcode type**: `Individual` (independent repair/maint job) · `Service Menu`
  (maintenance item inside a service menu) · `Inspections` (requires Inspection Type:
  UDI / PDI / MPI) · `Tire Storage`.
- **Opcode**: the code as defined by the service dept. NOTE: catalog opcodes pulling
  from the data source start with **TEK**.
- **Display Value**: what shows on the RO and in opcode search (can = the opcode). For
  SCP dealers, the Display Value shows instead of the TEK/system opcode.
- **Description**: the repair/maintenance job description.

### Eligibility Criteria
Defines where the opcode is available in search. **Condition**: `In` (included) /
`Not in` (excluded — e.g. hide from consumer portal, or RO-only). **Value**: options
based on the criteria chosen.

### Category
Used in **GLAM (GL Account Mapping)** to direct charges to accounts, and for
filter/reporting grouping. Loaded at installation.

### Service Type
Drives default labor rates (customer/warranty/internal) per service type; used with
department in GLAM for RO posting accounts; can drive technician wage configs
(Employee Onboarding → Employment Details). Main Service / Maintenance Service /
Service Interval Menu types load at installation.

### Job Priority and Skill
- **Job Priority**: used when auto-dispatch is on and the team's dispatch type is
  Claim Work Job Priority or Auto Dispatch Job Priority. Changeable on the RO.
- **Skill**: groups opcodes for auto-dispatch; techs get primary/secondary skills.
  Extra skill groups added in Dispatch Settings.

### Consumer Scheduling
- **Display Name**: name shown when scheduling via consumer portal.
- **Cause** / **Story Line**: default cause + correction statements pulled to the job.
  Multiple allowed (Add Cause / Add Story Line); all pull to the RO; remove via Delete.

### Standard Opcode Mapping
Maps an OEM opcode to the standard opcode so it pulls to the job. **OEM** (dropdown) +
**Opcode** (OEM code). For warranty jobs the OEM opcode pulls to the claim.

### Default Pay Type *(Service 3.0 only)*
Pay type auto-applied when opcode is added to an RO (+ default payer from Pay Types
Setup). Custom pay types come from Pay Types Setup. TIP: use for prepaid maintenance,
service contracts, fleet programs, warranty billing.

### Labor
- **Clock-In Mandatory**: require tech clock-in before working the op.
- **Customer**: default customer labor time pulled for ALL pay types. A Labor Pricing
  multiplier/kicker applies on top (e.g. 1.5 × 2.0 hr = 3.0 hr on the RO).
- **Manufacturer**: MFR-allowed labor time (Labor Time Guide). NOTE: labor hours only
  pull from **Customer time OR the Labor Time Guide** on the RO.

### Pay Type Pricing Setup
- **Eligible for Customer Pay Special Labor Pricing in Customer Management**: on by
  default (all opcodes). Deselect to bill only at Opcode-Management / Service-Type rates.
- **Labor Rate Configuration** rows: **Pay Type**, **Labor Rate** (Fixed Price / Hourly
  Price / Labor Price Guide + value), **Allow Override**, **Discount Eligible**.
  `Add` (top-right) to add a rule; drag handle to reorder; kebab → Remove / View Audit
  Logs. *(Service 3.0)*

### Parts
- **Consider for Parts Preparation on Appointment**: pre-stage parts when on an appt.
- **Eligible for Customer Pay Special Parts Pricing in Customer Management**.
- **Enable Part Price Cap**: cap total part price.
- Part rows: **Part Name** (dropdown), **Quantity**, **Parts Price**, **Select Fees**
  (auto-bill fees from Fee Management).

### Cost Centers
**Warranty Default Cost Center / Internal Default Cost Center** for warranty + internal
work: **Cost Center** (e.g. Warranty Claim, Internal Loaner Expense) + **Split %** +
**Allow Override** + Delete. Multiple allowed; splits must total **100%**.

### Associated Opcodes
Opcodes auto-added as additional operations when this opcode is added (e.g. alignment
auto-added with a FWD transmission R&R). NOTE: only **Individual** service-type opcodes
auto-add. Added in display order.

### Sublet
Work done by an outside company (towing, body work). Toggle **Sublet Op Code**, then
`Add` per-pay-type sublet pricing rows: **Pay Type**, **Sublet Labor Mark Up**, **Labor
Min/Max Value**, **Sublet Parts Mark Up**, **Parts Min/Max Value**, Delete.

### Auto-Dispatch / Completion
- **Consider for Auto Dispatch**: on by default; deselect for jobs needing no tech
  (sublets, loaners) so a tech isn't force-assigned.
- **Mark as Complete when added as a Job**: off by default; auto-completes the op when
  added (only if pre-job validations pass — Pre-Job Completion rules live in Service
  Settings). Use for no-tech jobs.

## Save
`Save` (lower-right) creates the opcode. Configure default pay types + labor-rate rules
carefully so the right payer/pricing applies automatically on the RO.

## VERIFIED CREATE MECHANICS via :9223 (ROTATEBAL @ BT 1249, 2026-07-02)

Full end-to-end create executed through the persistent browser server. Sequence:

1. **Nav**: SPA `window.location.href='/ro/opcode'` (wait ~8s), then `/click {text:"Create Opcode"}`
   → lands on `/ro/opcode/add` (Draft mode, Opcode Type defaults to Individual Service).
2. **Plain text fields** (work with `/type` after tagging `data-jay` via `/eval`):
   `#opcode_undefined` (the code), `#opcodeDisplayValue_undefined`, `#description_undefined`.
3. **Category / Service Type are react-select CONTAINERS** (`#CATEGORY_FIELD`,
   `#SERVICE_TYPE_FIELD` = `tekion-select-*-container` DIVs). `/type` on the container fails
   ("not an <input>"), a `/mouse` click on it does NOT open a dropdown, and the native
   value-setter throws **"Illegal invocation"** (known quirk). WORKING RECIPE: tag the INNER
   `input` (`c.querySelector('input')` — it reuses the container's id), `/type` a filter string
   into it (e.g. "Maint"), wait ~1.5s, options render as visible `[class*=option]` elements —
   `/mouse` click the option center. Verify via `[class*=singleValue]` innerText.
4. **Flag hours**: `#LABOR_HOURS_FIELD` (Customer) + `#MANUFACTURER_HOURS_FIELD` — `/type` + Tab.
5. **Pay Type Pricing Setup** (same mechanics as tekion-opcode-default-pricing): row badges
   `[class*=pricingTable_payType]` — NOTE the form renders MULTIPLE badge groups at different
   y-bands (eligibility ~251, pricing ~605-687, sublet ~1782); the labor pricing rows are the
   CP/W/I band near the "Pay Type Pricing Setup" section. Confirm row identity with
   `document.elementFromPoint(120, rowY)` = "CP" before clicking. Row's `.ant-select` at x≈493
   → options in `.ant-select-dropdown-menu-item` (LEGACY ant class) = Labor Price Guide |
   Hourly Price | Fixed Price → picking Fixed reveals `input[placeholder="Enter price"]` in
   that row → `/type` the $ + Tab.
6. **Submit button is `Create`** (blue, bottom-right ~x1211,y688), NOT Update/Save.
   ⚠️ A button scan filtering on `/save|cancel|update/i` MISSES it — I only found "Save Draft"
   and thought the form had no commit button until a screenshot+vision pass showed Create.
   Include `create|publish` in button-scan regexes.
7. **Success signal = URL flips to `/ro/opcode/edit/<OPCODE>`** — there is no reliable toast.
   ALWAYS verify by API read-back (opcode search endpoint, see tekion-opcode-api): confirm
   status ACTIVE, flatPrice, hours, dealerId.

Convention cloned for BT maintenance add-ons (matches BGMOAG/4ALIGN/WIPER/CABIN): Individual
Service / Category=Maintenance / Service Type=Maintenance Service / Default Pay Type=CP /
Fixed Price CP / Skill=DEFAULT / no parts for labor-only services.

## ⚠️ BEFORE creating: audit for near-duplicate opcodes (burned 2026-07-02)

An exact-match existence check (`searchFields:["OPCODE"]` + `hits.find(x=>x.opcode===CODE)`)
is NOT enough to declare an opcode "missing":
- **Search is case-sensitive on compare**: "44K" showed MISSING but lowercase **"44k"** existed.
- **Near-dupes hide under different codes**: "FOBBATTERY" missing but **FOBBATT** existed
  ($5.99); "ROTATEBAL" missing but **BALANCE** ($89.95, balance-only) + **ROTATE** ($39.95)
  existed.
Before creating, run BROAD searches on `searchFields:["OPCODE","DESCRIPTION"]` with keyword
fragments (e.g. "ROTATE", "BALANCE", "FOB", "KEY") and compare case-insensitively. Creating a
duplicate = the "Perform Tire Rotation (2)" clutter problem Joe hates. Default to
reuse+reprice an existing cousin (flag the à-la-carte blast radius) and only create new when
the service content genuinely differs (e.g. BALANCE lacked rotation → ROTATEBAL justified).

## Pitfalls / notes
- Opcodes are **store-specific** — create only at the store(s) needed (Joe-confirmed);
  don't replicate across all 7 unless asked.
- Several fields are **Service 3.0 only** (Default Pay Type, Labor Rate Configuration).
- For the browser-automation mechanics of actually typing into V2 fields (spinbuttons,
  react-select parts, incremental Save Draft), see `tekion-opcode-default-pricing` —
  this skill is the FIELD MAP; that skill is the CLICK MECHANICS.
