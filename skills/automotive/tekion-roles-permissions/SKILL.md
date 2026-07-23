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

## MERGING two roles into one (PROVEN 2026-07-23 — BC "Appraiser" = Sales Person + BDCSpecialist)
The Create modal accepts only ONE template, so a merge = **create from the bigger template,
then diff the other role and toggle the delta ON**. Fully scripted, exact-verified:

1. **Dump both roles' pill states** with `/home/itadmin/tekion-reports/role_dump.py <roleQuery> <out.json>`
   (roleQuery = `1251_SALES_PERSON` style standard id or mongo id). It hard-navigates,
   strips pendo, iterates every center collapse header (filter `getBoundingClientRect().x>300`
   to skip left-rail dupes), expands each, and records `{group, name, on}` per pill.
   Group title = nearest non-empty `previousSibling.textContent` of the
   `core_roleDetails_permissionGroup` div. BC role universe = 1,345 pills across 18 categories.
   **Standard-role URL ids are irregular** — Sales Person = `1251_SALES_PERSON` but
   BDCSpecialist = `1251_BDCSpecialist` (not `1251_BDC_SPECIALIST`); when unsure, click the
   role in the left rail and read the URL rather than guessing.
2. **Compute delta** = `on(B) − on(A)` keyed on (category, group, name). SP∪BDC example:
   254 ∪ 82 → 281 target, 27 delta.
3. **Create the role** from template A via the Create Custom Role modal (clone verified
   identical to template before toggling — dump the new role once and diff = 0).
4. **Toggle delta + SAVE PER CATEGORY** with
   `/home/itadmin/tekion-reports/role_toggle_appraiser.py` (adapt ROLE + delta file).
   JS `button.click()` toggles fine; after each category's toggles click the Save button
   (find by visible text, /mouse at its rect center). Save disappearing = saved — BUT the
   LAST category's save-btn-count can stay 1 (Save re-rendered); re-check for a lingering
   visible Save after the loop and click it once more.
5. **Verify with a TRUE remount**: navigate to `/home` then re-dump the new role;
   assert `on(new) == on(A) ∪ on(B)` exactly (0 missing / 0 extra).

**Dead ends (don't retry):** the internal
`/api/rolesandpermissionservice/u/admin/*` endpoints (roles-minimal, v3/permissions)
return 500 "Token doesn't exist or is invalid" when called via bare in-page `fetch` with
localStorage headers — the axios interceptor auth can't be replicated; and role-switching
in the UI fires NO capturable XHR for permission data (it's preloaded), so an XHR hook
yields nothing. DOM pill scraping is THE working read path.

**Merge review tip for Joe:** flag any sensitive inherited pills in the report (e.g.
Appointment Slot Override rode in via BDCSpecialist on the Appraiser merge) so he can
decide whether to strip them.

## Merging two roles into one (verified BC 2026-07-23, "Appraiser" = Sales Person + BDCSpecialist)
The Create modal takes ONE template only. Merge recipe:
1. Dump BOTH source roles' pills with `/home/itadmin/tekion-reports/role_dump.py <roleQuery> <out.json>`
   (expands each center category, reads every `core_switch` button's group+name+state).
2. Diff: delta = ON-in-B minus ON-in-A. Create the new role from the BIGGER template (A).
3. Toggle the delta ON with `role_toggle_appraiser.py` pattern: per CATEGORY toggle then Save
   (Save button ~1196,687 appears per unsaved batch; save-per-category, guard `location.href`
   against session dealer/nav drift between toggles).
4. Verify: hard remount (/home then back), re-dump, assert union == new role's ON set exactly.
BC "Appraiser" role id = `6a629362f110bc589bf37706` (Sales Person template, persona Sales Person,
254+27=281 perms; **Appointment Slot Override deliberately OFF** per Joe 2026-07-23).

## Assigning a user to a role via USER SETUP (Joe-approved path, verified BC 2026-07-23)
Joe's employee-record rule still applies (explicit approval required) — but when he says
"assign in User Setup only, don't touch Employee Onboarding," the path is:
1. `/core/user-setup` (sidebar US). Search = the EXPANDABLE search (collapsed to w=0!):
   `/mouse` click at its coords (~1070,160) to expand FIRST, then set value via native
   setter + input event, focus, `/press` Enter. (Enter via KeyboardEvent does NOT filter;
   `/type` page.fill times out while collapsed — "element is not visible".)
2. Click the user's Display Name cell → `/core/user-setup/edit/<userId>`.
3. Dealership Roles row: "Role Name" = react-select singleValue (click, pick option);
   "Secondary Roles" = multiSelectDropdown (click widget → ant-dropdown portal with
   checkboxes; uncheck to remove). **PITFALL: reopening the multi-select can silently
   check the FIRST option ("95/5") — always re-open and read checked[] before saving.**
4. Save = bottom-right **Update** button. **`/mouse` click at its coords can MISS (no XHR
   fires, nothing persists, no error) — use JS `b.click()` on the button element and
   confirm via XHR hook: `PUT /api/userservice/u/user-access-settings/<userId>` → 200
   "User and access settings updated successfully".** Then verify with true remount AND
   OpenAPI `GET /users/{id}` (userRoleDetails).
Ivan Govea (BC, empNo 5654, id db4c2a79-690c-44d9-9387-d0db8837528d) = Appraiser primary,
no secondaries, as of 2026-07-23.

## Finding WHO holds a role (OpenAPI users fan-out)
Roles pages don't list members. Use OpenAPI `GET /openapi/v4.0.0/users` (tekion_client at
`/home/itadmin/tekion-api/`), but note THREE traps:
1. **`pageNumber` is IGNORED** — every page returns the same first 100. Real pagination =
   pass `meta.nextFetchKey` back as query param **`nextFetchKey`** (NOT `fetchKey` — that's
   silently ignored too). Loop until nextFetchKey is null (SCT = 1536 users, ~253 active).
2. `userNameDetails.completeNames` is a **LIST** of `{nameType, value}` objects, not a dict —
   or just use `firstName`/`lastName`.
3. The list payload MAY now include `userRoleDetails` (primary + secondaryRoles), `active`,
   and `email` inline — verified at BC 2026-07-23 (371 users, 4 pages, `data` is a bare LIST
   not a dict; Josh Williams lookup needed zero fan-out). If those fields are present, skip
   the per-user fan-out entirely. Older behavior (**list payload has NO role info**) may
   still apply on some queries — fall back to `GET /users/{id}` per user
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
