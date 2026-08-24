---
name: tekion-notification-settings-audit
description: >
  Definitively answer "where did notification X go / does notification Y exist / who gets
  notified when Z happens" in Tekion. Dumps the COMPLETE list of user notification event
  types (all modules) from the internal notification-preference API instead of scrolling
  the giant Profile Settings table, then maps the request to the right config surface
  (per-user Profile Settings vs Service Settings vs Dispatch vs Scheduling vs Parts
  Settings). Load for any "I can't find the setting that notifies ..." ticket.
triggers:
  - notification setting missing tekion
  - where did the notification setting go
  - who gets notified when
  - notification settings tekion
  - add on job notification
  - tekion notification preferences
  - profile settings notification settings
---

# Tekion — Notification Settings Audit ("where did notification X go?")

Origin: Joe 2026-08-24, "Where did the 'add on' job notification settings go" —
answer turned out to be **no such event exists** (never did, under that name). The
value of this skill is proving existence/absence FAST and authoritatively instead of
scrolling a ~920-line settings table or guessing.

## STEP ZERO — do not guess a location
Per Joe's NEVER-GUESS rule: if you cannot find the named setting, say so plainly,
list where you looked, name the closest real settings, and ask which store/screen he
saw it on + who is missing the notification (parts / tech / advisor). A plausible-
sounding wrong location gets rejected instantly and burns trust. Absence proven by
the API dump below IS a legitimate, useful answer.

## The unlock: dump ALL notification events from the API
The per-user notification preferences load from ONE internal call. Capture it with an
XHR hook, then you have every event type in the system as JSON — searchable, no
scrolling, no vision.

**Endpoint:** `GET /api/notificationServiceV2/u/user/preference/<dealerId>`

Procedure on the authenticated persistent browser (`:9223` for Jay's lane, `:9225`
for subagents):

```python
# 1. land on the profile page
post("/navigate", {"url": "https://app.tekioncloud.com/userProfile"}); sleep(8)

# 2. arm an XHR hook (fetch hook MISSES it — this is XHR)
ev("""(function(){window.__x=[];
 const o=XMLHttpRequest.prototype.open,s=XMLHttpRequest.prototype.send;
 XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return o.apply(this,arguments)};
 XMLHttpRequest.prototype.send=function(){this.addEventListener('load',()=>{
   try{window.__x.push({u:this.__u,r:this.responseText.slice(0,400000)})}catch(e){}});
   return s.apply(this,arguments)};return 'ok'})()""")

# 3. click the "Notification Settings" tab (leaf text match, ~x530,y155)
post("/mouse", {"x":530, "y":155}); sleep(8)

# 4. read it back — flatten to module | eventType | title
ev("""(function(){const j=JSON.parse(window.__x[0].r);
 return JSON.stringify(j.data.map(x=>[x.metadata&&x.metadata.moduleName,
   x.eventType, x.metadata&&x.metadata.title]))})()""")
```

**Response shape** — `{data:[...], status}`, `data` is a flat array (156 rows at BT
2026-08-24), each row:
```json
{"id":"0_<userId>_PARTS_MARKED_CROSS_SHIPPED","userId":"...","dealerId":"0",
 "eventType":"PARTS_MARKED_CROSS_SHIPPED",
 "preference":{"WEB":true,"TEXT":false,"EMAIL":true,"MOBILE":false},
 "override":false,
 "metadata":{"moduleName":"Parts","deliveryType":["EMAIL","WEB","MOBILE","TEXT"],
   "description":"Parts marked as cross shipped","title":"Parts Marked As Cross-shipped",
   "key":"PARTS_MARKED_CROSS_SHIPPED","group":"Parts"}}
```
`preference` = the actual on/off per channel. `deliveryType` = which channels are even
*available* (UI shows "Unavailable" for channels not in this list). `override` flags a
per-dealer override of the default.

Modules present: Accounting · Analytics · Core · Email · General · Internal · Parts ·
Sales · Service. (Payroll/TEKPayroll render as sub-groups under Accounting.)

### Service + Parts events that actually exist (BT 1249, 2026-08-24)
The ones people usually mean when they ask about job/parts notifications:

| Module | eventType | Title |
|---|---|---|
| Service | `TECH_ASSIGNED` | Technician Is Assigned |
| Service | `JOB_HOLD_TO_UNHOLD` | Job Is Unhold From Hold |
| Service | `RO_READY_FOR_INVOICE` | Ready For Invoice |
| Service | `RECOMMENDATION_SUBMITTED` / `_APPROVED_BY_SERVICE_ADVISOR` / `_REJECTED_*` / `_VOIDED` | Recommendation … |
| Service | `CUSTOMER_ARRIVED`, `CustomerArrivalTime` | Customer Has Arrived / Arrival Time |
| Service | `ROCreatedWithPartsPreparationDoneAgainstAppointment` | RO Created With Parts Preparation Done Against Appointment |
| Service | `SUBLET_UPDATED`, `MPVI_SUBMITTED`, `VIN_CHANGE`, `WARRANTY_SUBMIT` | … |
| Parts | `P_AND_A_REQUESTED` | P&A Requested |
| Parts | `RECOMMENDATION_APPROVED` | P&A Approved |
| Parts | `RO_FULLFILLMENT_REQUESTED` | Part Fulfillment Requested |
| Parts | `RO_PART_CLAIMED` / `RO_PART_FULLFILLED` | Parts Claimed / Parts Fulfilled |
| Parts | `RO_SOR_PARTS_RECEIVING` / `_PARTIAL_RECEIVING` | SOR Parts Receiving By Job / By Part |
| Parts | `RO_PART_AUTOFULFIL` | Express RO Parts Not Fulfilled |
| Parts | `PARTS_MARKED_BACK_ORDERED` / `_CROSS_SHIPPED` | … |

**There is NO "Add On Job" / "Added Job" / "Add-On" notification event.** Nearest
things that carry that word are `THREAD_ITEM_ADDED` (General) and
`PRINTER_INSTALLED` ("Printer Addition Success") — neither is service-related.

## Mapping a request to the right config surface
Notification behavior is spread across 5 screens. Check in this order:

1. **Per-user delivery toggles** — Profile Settings → Notification Settings.
   Nav: avatar bottom-left of the left rail (~30,660) → popover → **"View Profile
   Setting"** (~165,619) → lands `/userProfile` → tab **"Notification Settings"**
   (~530,155). Filters at top: Notification Type / Notified On / View By (dealer).
   "Reset All Overrides" action. Bottom Cancel/Save.
   ⚠ Direct URL `/userProfile` works. `/core/profile-settings` and
   `/core/user-profile/notification` **silently land on a Fee edit page** —
   always assert `location.href` after navigate.
2. **When Parts gets pinged off a job** — Service Settings
   `/service/settings/ro-settings` → **Parts Request** section →
   *"Auto submit Parts Fulfillment request for jobs when: Job is Created, Job is
   Saved, Tech is Assigned"*. This is the real "a job was added → tell parts" trigger.
3. **Appointment-time parts notification** — Scheduling Settings
   `/dse-v2/scheduling-settings` → **General** tab → *Additional Settings* →
   "Notify Parts department of appointment part request immediately / few days before".
   Also "Customer Notify Service Advisor" lives here.
4. **Tech assignment on an added job** — Dispatch Settings `/ro/dispatch-settings` →
   General Settings → **"Auto Assign Technician to Added Job"** (+ "Only Assign if
   Technician has matching Skills", "Auto Assign Technician who submitted
   Recommendation", "…for previously Deferred services"). Assignment, NOT notification —
   don't conflate the two when answering.
5. **Customer-facing SOR/receipt notifications** — Parts Settings
   `/parts/parts-settings` → "Default settings for customer notification on SORs".

Whole-doc scan trick for any of these settings pages:
```js
const l=document.body.innerText.split('\n').map(x=>x.trim()).filter(x=>x);
l.forEach((x,i)=>{if(/notif|notify|alert/i.test(x))console.log(i,x)});
```
`/service/settings/ro-settings` is ~1,990 lines — never read it linearly, always grep
the innerText array and slice around the hit index.

## Pitfalls (all hit live 2026-08-24)
- **:9223 can be parked on the ServiceNow KB** (`tekion.service-now.com`) from a prior
  task → `localStorage` has no `t_token` and reads look logged-out. Navigate to
  `app.tekioncloud.com/home` first and re-verify `t_token` + `currentActiveDealerId`.
- **Stale SPA routing:** on :9223, `/service/settings/ro-settings` repeatedly redirected
  to `/parts/tax-code-setup` (a leftover route), even after a `/home` bounce. The SAME
  URL loaded perfectly on :9225. If a known-good URL keeps landing somewhere else, switch
  browser lanes rather than fighting it.
- **Scheduling Settings deep-links to the Summary tab.** You must click the **General**
  leaf (~137,160) to see the notification toggles.
- **App Grid search input is not queryable** — `document.querySelectorAll('input')`
  returns `[]` with the grid open. Use `/screenshot` + `vision_analyze` for tile coords,
  or skip the grid and use direct URLs.
- The profile popover is an **ant-popover portal** — read it via
  `.ant-popover-inner-content` leaf-walk, not a normal selector.
- `dealerId` in the returned rows is `"0"` (tenant-level default) even though the URL
  path carries the real dealer id — don't read row `dealerId` as the store.

## Related skills
`tekion-service-settings` (section map) · `tekion-sitemap` (URLs) ·
`tekion-scheduling` (notify-parts toggles) · `tekion-kb-search-scrape` (KB lookup) ·
`tekion-parts-appointments-opcode-scoping` (per-opcode parts-prep flag).
