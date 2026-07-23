---
name: tekion-roles-permissions
description: Create/duplicate a Tekion custom ROLE and toggle its PERMISSIONS via the Roles admin page (/core/roles). Verified live at Blackstone Chevrolet 2026-07-10 (created "Concierge" cloned from ServiceAdvisor + enabled deal viewing). Covers the no-duplicate-button trap, permission pill mechanics, and save/verify flow.
triggers:
  - tekion create role
  - tekion duplicate role
  - tekion role permissions
  - tekion roles admin
  - concierge role
---

# Tekion Roles & Permissions (create, duplicate, toggle)

**HARD RULE first:** creating/editing ROLES is allowed, but ASSIGNING USERS to a role
or touching employee/user records requires Joe's explicit permission (his standing rule
2026-07-10). Create the role, stop before user assignment.

All work via the `:9223` persistent browser (must be authed + on the right dealer).
Load `tekion-sitemap` first for login/dealer-switch.

## URL / layout
- Roles page: **`https://app.tekioncloud.com/core/roles`** (direct nav works).
  Selecting a role → `?role=<mongoId>` (custom) or `?role=<dealerId>_RoleName` (standard, e.g. `1251_ServiceAdvisor`).
- 3 panels: LEFT = role list (ant-menu, grouped Accounting/General/Parts/Sales/Service —
  Accounting expanded by default); CENTER = permission categories (ant-collapse:
  Accounting, Advanced Analytics, ..., Sales, Service, ...); RIGHT = pills/detailed view.
- Top-right header: **Create Custom Role** button (~x1178, y94).

## Duplicating a role — THE TRAP
There is **NO duplicate/copy action**. The role row kebab (`.icon-overflow`, needs
`scrollIntoView` + `/mouse` click at coords — JS click doesn't open the portal) contains
ONLY **"Archive Role"**. Duplication = **Create Custom Role modal with a Role Template**:

1. Click **Create Custom Role** → modal: Role Name (`input#name`), Role Template*,
   Persona*, Department*.
2. Set name via native value-setter on `#name` + dispatch `input`/`change`.
3. Open **Role Template** select by `/mouse` at its coords (input cls
   `tekion-select-...-requiredInput`, ~x497,y321). Options render in a portal —
   query `[role="option"], .ant-select-item`, find exact text (e.g. `ServiceAdvisor`),
   dispatch mousedown+mouseup+click.
4. Picking the template **auto-fills Persona + Department** (ServiceAdvisor → Service).
5. Click **Create** (find button text 'Create' inside `.ant-modal`, click via /mouse).
   New role appears in the left list under its department group; URL gets a mongo id.
   **The template clones the ENTIRE permission set.**

## Expanding groups / reading permissions
- LEFT role groups: click `.ant-menu-submenu-title` whose text matches (e.g. 'Service')
  via `dispatchEvent(new MouseEvent('click',{bubbles:true}))`. Role rows = `.ant-menu-item`.
- CENTER permission categories: click the `.ant-collapse-header` with exact text
  (e.g. 'Sales'). NOTE: there are TWO sets of 'Sales'/'Service' text on the page —
  left-rail role groups (x≈64-84) vs center collapse headers (x≈426). Disambiguate by x.
- Permission pills = `button` with class `core_switch_switch__...`;
  **ON = className contains `core_switch_selected`**. Toggle = JS click (works fine here).
- Groups inside a category = `.core_roleDetails_permissionGroup__...` divs; the group
  title is a preceding sibling text node. Each group has an 'All' pill first.

## Save + verify
- After any toggle a **Save** button appears top-right of the detail panel (~x1196,y687).
  Click via /mouse. **Save disappearing = saved** (no toast fired in testing).
- VERIFY: hard `/navigate` back to `?role=<id>`, re-expand the category, confirm the
  pills still show `core_switch_selected`.

## "View sales deals" — no single switch
Tekion has NO plain "view deals" permission. Deal visibility is granular under the
**Sales** category. Minimal read-only = **Desking > Desking View** +
**Desking > Desking Deal Jacket View**. Deliberately separate (leave OFF unless asked):
gross visibility (`DealList View Front/Back/Total Gross`), `Desking F&I View`,
`View Cost & Profit`, Contract In Transit. The ServiceAdvisor template ships with ALL
Deals List + Desking view perms OFF.

**Deals LIST access (learned 2026-07-14):** there is NO "DealList View" pill — the
Deals List group only has `DealList Edit` plus granular column-view pills (gross, PVR,
contract age). **`DealList Edit` is the base switch that grants access to the Deals
list module** (the Sales Person role confirms: it has DealList Edit ON as its list
access). So "give role access to Deals" = DealList Edit ON + Desking View +
Desking Deal Jacket View; leave the gross-column pills OFF unless asked.
BC Concierge role id = `6a511605d9cdf64d97735778` — has exactly this set as of 2026-07-14.

## Concurrency pitfall (hit 2026-07-14)
Other jobs (menu-sales scrapers, quote pullers) share the :9223 browser and can
NAVIGATE AWAY mid-edit (page suddenly on /ro/quotes/...). Before each toggle/save,
re-check `location.href` is still on /core/roles?role=<id>; if hijacked, re-navigate
and redo the expand. Toggle+Save in ONE quick sequence, then verify with a fresh
hard reload. Also: running kb_search_scrape.py mid-task navigates :9223 to
tekion.service-now.com — don't mix KB scraping with a roles edit session.

## Known permission answers
- **Stop advisors changing the Service Advisor on ROs** (KB0025857/KB0024919): permission
  **"Repair Order SA Edit"** under the **Service** section of a role. Without it the SA
  field on open ROs is not editable/visible for change. Only gates PRE-invoice edits
  (post-invoice locked anyway). Per-role per-store. CHANGED 2026-07-13 per Joe:
  SCT (876) ServiceAdvisor role → toggled OFF (was ON). Other stores/roles untouched.
  Direct URL ?role=876_ServiceAdvisor worked; the permission pill is itself the
  <button> whose text == "Repair Order SA Edit" (className core_switch_selected = ON).

- **Stop call-center/BDC agents from FORCE-BOOKING appointments** (verified SCT 2026-07-21):
  the permission = **"Appointment Slot Override"** pill, under **DSE category → Appointments
  group** (same group holds Transportation Type Override, Ride Share Override, Appointment
  Create/Edit/Cancel/View). Toggling it OFF removes the ability to override full slots/capacity
  while leaving normal booking intact. Plain JS `b.click()` toggles it fine; Save at ~(1196,687)
  via /mouse; verify with a TRUE remount (/home then back — same-URL nav re-reads unsaved DOM).
  CHANGED 2026-07-21 per Joe: SCT (876) **BDCSpecialist** → OFF. BDCManager + BDCSuperAdmin left
  ON (Christina McKenzie = BDCManager, keeps the ability). Per-role per-store — other stores untouched.
  **Joe's explicit scope directive (2026-07-22): BDCSpecialist is the ONLY role to block, SCT ONLY —
  do NOT touch BDCManager/BDCSuperAdmin and do NOT replicate to other stores unless he asks.**
  SCT BDC roster ground truth (direct /users/{id} lookups): Minnie Chavez, Crystal Garcia,
  Brenda Lara = BDCSpecialist-only (blocked); Miranda Long has BDCSpecialist as secondary (blocked);
  **Ana Medina holds BDCSpecialist + BDCManager → can STILL override via BDCManager.** Closing that
  gap requires removing BDCManager from her user record = employee-record change = needs Joe's
  explicit approval first (his standing HARD RULE). Flagged to Joe 2026-07-22, no go-ahead given.

## Finding WHO holds a role (OpenAPI users fan-out)
Roles pages don't list members. Use OpenAPI `GET /openapi/v4.0.0/users` (tekion_client at
`/home/itadmin/tekion-api/`), but note THREE traps:
1. **`pageNumber` is IGNORED** — every page returns the same first 100. Real pagination =
   pass `meta.nextFetchKey` back as query param **`nextFetchKey`** (NOT `fetchKey` — that's
   silently ignored too). Loop until nextFetchKey is null (SCT = 1536 users, ~253 active).
2. `userNameDetails.completeNames` is a **LIST** of `{nameType, value}` objects, not a dict —
   or just use `firstName`/`lastName`.
3. The **list payload has NO role info** — you must `GET /users/{id}` per user
   (`userRoleDetails.primaryRole` + `secondaryRoles[]`, each `{persona, roleName}`).
   Fan-out over ~250 users takes 15+ min with 429 backoff → run as a BACKGROUND script
   (foreground execute_code hits the 300s cap). Check secondaryRoles too — users like
   Miranda Long carry BDCSpecialist as a *secondary* role and are still affected.
   **The list scan is NOT authoritative for "who holds role X"** — pagination glitches and
   per-user fetch errors made it MISS Minnie Chavez and Ana Medina entirely (2026-07-22).
   When Joe asks about a specific person, do a DIRECT user lookup (search by name →
   GET /users/{id}) rather than trusting a prior roster scan; report scan-errored users
   by name so Joe can flag any that matter.
Same user id resolves at multiple dealers (swap `dealer_id` header) — useful to check which
store a person's role lives at (Christina McKenzie = BDCManager at both 826 and 876).

## Pitfalls
- The `/screenshot` endpoint returns JSON `{"screenshot":"<base64>"}` — decode to a real
  PNG before `vision_analyze` ("Only real image files" error otherwise).
- `/eval` needs body key `js` (not `expression`).
- Kebab dropdown renders in a portal; dismiss by clicking the kebab again (never click
  random elements — nav wipe hazard).
- Roles page loads with only Accounting expanded; other groups exist but are collapsed —
  a text scan that misses 'ServiceAdvisor' does NOT mean it's absent.
