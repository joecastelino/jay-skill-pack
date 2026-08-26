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
  - approval workspace notification
  - approver not getting notified tekion
  - turn on approval notifications email text
  - approval setup reminders tekion
  - notification setting missing tekion
  - where did the notification setting go
  - who gets notified when
  - notification settings tekion
  - add on job notification
  - tekion notification preferences
  - profile settings notification settings
  - add on tag missing repair order
  - tekion ro tags
  - tekion job tag
  - where did the tag go tekion
---

# Tekion — Notification Settings Audit ("where did notification X go?")

Origin: Joe 2026-08-24, "Where did the 'add on' job notification settings go" —
answer turned out to be **no such notification event exists** (never did, under that
name). The value of this skill is proving existence/absence FAST and authoritatively
instead of scrolling a ~920-line settings table or guessing.

## ⚠ RESOLVED 2026-08-25 — "Add on" is a TAG, not a notification
Joe clarified on the follow-up: *"no, I'm talking on the repair order. it used to have
a tag of Add on."* **Read this before running the API dump below.**

- **Add-on is a Job-type TAG** configured at Service Settings
  `/service/settings/ro-settings` → left-nav **Tags**.
- Tag Type dropdown = **RO / Job / Recommendation**. Job-type tag names available:
  PDI · Hold · Service Menu · **Add-on** · Due Bill · Recall · Recommendation ·
  Deferred Recommendation · Insurance · Internal Split · Warranty Split ·
  Manual Flag Hrs · Adjusted Flag Hrs · UVI · MPI · Return RO · Mobile Shop · Express Shop.
- Row columns: Tag Type · Tag Name · Color · Text Color · toggle **RO** · toggle **PDF**
  (PDF = tag prints on the invoice). Bottom blank row = add. Separate **Archived Tags**
  sub-tab.
- **Live state verified BT 1249 / ST 876 / TL 1092:** each store has ONLY 3 tags, all
  *Recommendation* type (MPI, PDI, UVI). Zero Job-type rows. Archived Tags EMPTY.
  → The Add-on row was **deleted**, not archived — nothing to restore, it must be
  re-created per store.
- Recreate: Tags → blank bottom row → Tag Type=Job → Tag Name=Add-on → pick
  Color/Text Color → toggle RO on (PDF only if it should print for the customer) → Save.
  Ask Joe which stores + RO-only vs RO+PDF before saving; don't assume.

**Triage rule:** when someone says a *thing on the repair order* disappeared, check
**Tags** BEFORE Notification Settings. "Notification" in Joe's phrasing may mean any
visual flag/badge on the RO, not a push/email preference.

## ⚠ RESOLVED 2026-08-25 — "Approval Workspace notifications" (turn ON a channel)
Joe: *"how do I turn on approval workspace notifications? so the approver gets a text
message, email or alert when there is an approval that needs to be approved."*
This is the **turn-it-ON** variant of this skill (vs. the prove-absence variant above).

**Answer:** Profile Settings → Notification Settings → module **Core** → group
**Approval Management**. Six events, all with WEB/MOBILE/TEXT/EMAIL available:

| eventType | Title | Who it hits | Default state (TL 1092, Joe's user) |
|---|---|---|---|
| `APPROVAL_REQUEST_RECEIVED_FOR_APPROVAL` | REQUEST RECEIVED FOR APPROVAL | **the APPROVER** ← the one people want | WEB ✅ MOBILE ✅ **TEXT ❌ EMAIL ❌** |
| `APPROVAL_REQUEST_SENT_FOR_APPROVAL` | REQUEST SENT FOR APPROVAL | submitter | WEB ✅ MOBILE ✅ TEXT ❌ EMAIL ❌ |
| `APPROVAL_REQUEST_SENT_GOT_APPROVED` | REQUEST SENT GOT APPROVED | submitter | WEB ✅ MOBILE ✅ TEXT ❌ EMAIL ❌ |
| `APPROVAL_REQUEST_SENT_GOT_REJECTED` | REQUEST SENT GOT REJECTED | submitter | WEB ✅ MOBILE ✅ TEXT ❌ EMAIL ❌ |
| `APPROVAL_REQUEST_SENT_GOT_RETURNED` | REQUEST SENT GOT RETURNED | submitter | **all four ❌** |
| `APPROVAL_REQUEST_SENT_GOT_WITHDRAWN` | REQUEST SENT GOT WITHDRAWN | submitter | WEB ✅ MOBILE ✅ TEXT ❌ EMAIL ❌ |

**Root cause of "nobody gets notified": TEXT and EMAIL ship OFF.** Only the in-app
bell (WEB) and ARC mobile push are on out of the box. Adjacent hits the search also
surfaces: `EMPLOYEE_TIME_APPROVAL_STATUS` (Accounting→Payroll, EMAIL available/off,
Mobile+Text Unavailable), `ROLE_PERMISSION_APPROVAL` (General, WEB only),
`RECAP_APPROVAL_STATUS` / `TRADEIN_APPROVAL_STATUS` / `CUSTOMER_APPROVAL_STATUS`
(Sales, WEB only), `CUSTOMER_APPROVED_RECOMMENDATION` +
`RECOMMENDATION_APPROVED_BY_SERVICE_ADVISOR` (Service, WEB/MOBILE only),
`RECOMMENDATION_APPROVED` = "P&A Approved" (Parts, WEB only).

**Two things to tell the asker (both are the real gotchas):**
1. **It is a PER-USER preference, not a store setting.** Flipping your own toggles does
   nothing for anyone else. Each approver must set their own — **there is NO admin path.**
   (Do NOT suggest User Mimicking: KB0011016 confirms it's an internal Tekion-only ARC app,
   not available to dealer admins. Every admin/override endpoint 404s and userId spoofing
   is ignored — see the PER-USER proof section below.) TEXT goes to the **user record**
   phone, not the employee record. **NEVER edit another employee's record without Joe's
   explicit OK** (standing hard rule).
2. **Reminders/nagging are NOT a user preference** — they live on the RULE:
   `/core/approval-setup` → business process → rule → **Additional Options →
   Reminders** (interval min/hrs) and **Request Expiry**. Approval requests themselves
   only exist if a rule matches (Approval Setup, per business process + department).
   TL 1092 as of 2026-08-25: business processes = *Deal recap* (Sales, 0 rules) and
   *Service* (Service, 2 rules).

**Save behavior (multi-store users):** Save pops an **"Apply changes to"** modal —
*All dealerships* (global, INCLUDING existing per-dealer overrides) vs *Dealerships
without Override* (global, EXCLUDING them). For a fleet-wide fix pick All dealerships.
`Actions` dropdown does bulk Turn On/Off Web·Email·Mobile·Text over the filtered view;
`Reset All Overrides` reverts everything to the global default.

KB refs: KB0021275 (About Approval Workspace) · KB0021229 (Add a rule in Approval
Setup — incl. Reminders/Expiry) · KB0014652 (Profile Settings→Notification Settings
field-by-field) · KB0010959 (how to update user notification settings) ·
KB0021347/KB0021549 (auto-delegation) · KB0021348 (self-approvals).

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
Row count varies by store/role: 156 at BT 1249, **176 at TL 1092**.

### FASTER than the API dump when you already know the keyword: the in-page search
The Notification Settings tab has its own **magnifier search** that collapses the
~15,000px-tall table down to just the matching groups — ideal for a screenshot Joe can
actually read. Verified 2026-08-25:

```python
post('/mouse', {'x':951,'y':209})          # magnifier, right of the View By filter
ev("""(function(){const el=[...document.querySelectorAll('input')].find(e=>e.placeholder==='Search');
 const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
 el.focus(); s.call(el,'approval'); el.dispatchEvent(new Event('input',{bubbles:true}));
 el.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:13,bubbles:true}));
 return 'typed'})()""")                     # native value-setter + synthetic Enter
# then bring the group into the viewport before screenshotting:
ev("""(function(){const e=[...document.querySelectorAll('*')].find(e=>e.children.length===0
 && /Approval Management/i.test((e.textContent||'').trim())); if(e)e.scrollIntoView({block:'center'});
 return 'ok'})()""")
```
Read the filtered result from `document.body.innerText` (group headers + row titles),
then use `/screenshot` + `vision_analyze` to read the **toggle states** — the toggles
are styled divs, so on/off does NOT appear in innerText. Cross-check the vision read
against the API dump's `preference` object; they agreed exactly in the approval case.

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

## ⚠⚠ PER-DEALER SCOPING IS THE #1 ROOT CAUSE (proven TL 1092, 2026-08-25)

Notification preferences are **per-user AND per-dealer**. Two row types coexist:
- `dealerId:"0"` = tenant-level DEFAULT, `override:false` (what you get if you never touched it)
- `dealerId:"<store>"` = per-store OVERRIDE, `override:true` (created the moment you toggle+Save while viewing that store)

The Save button PUTs to `/api/notificationServiceV2/u/user/preference/v2/<dealerId>?flag=false`
— `flag=false` = **THIS DEALERSHIP ONLY**. `flag=true` = all dealerships (415 if called raw; must go through the UI dialog).

**The trap:** the `View By` dropdown at the top of Notification Settings selects which dealership you're editing.
Flip a toggle with `View By` on the wrong store and you create an override on a store the person doesn't work at,
while their real store keeps the `dealerId:"0"` default (`TEXT:false, EMAIL:false`). UI shows it as ON. Delivery stays OFF.

**Audit any user across all 7 stores (self only):**
```js
(async function(){const H=Object.assign({},window.__H);delete H['content-length'];const out={};
for(const d of ['1092','876','1249','1251','826','6195','1891']){
 const r=await fetch('/api/notificationServiceV2/u/user/preference/'+d,{headers:H});const j=await r.json();
 const row=(j.data||[]).find(x=>x.eventType=='APPROVAL_REQUEST_RECEIVED_FOR_APPROVAL');
 out[d]=row?{p:row.preference,ov:row.override,dealerId:row.dealerId}:'none';}
return JSON.stringify(out)})()
```
Real result for Joe (8cc203af…) before fix: 1092 default-off, 826 `TEXT:true/EMAIL:false` (stray override),
all others falling back to the `"0"` row. Classic per-store drift.

## Reading approval RULES without the Approval Setup permission (workaround, 2026-08-25)

`GET /api/arcapproval/u/approval-setup/<id>` = 400 TDA156 "User does not have permission to View Rules!".
**But the Approval Workspace search returns the full embedded rule (levels + approverIds) with no extra permission.**
Navigate to `/core/approval-workspace`, capture the app's own `POST /api/arcapproval/u/approval/search?locale=en_US`
via the XHR hook, then **replay `e.b` with `e.h` verbatim and just blank `filters:[]`**.

CRITICAL: replay with the CAPTURED header object `e.h` — rebuilding headers from `window.__H` gives **500 unexpected.error**
on this endpoint (it needs the full 16-header set incl. `roleId`, `tek-siteId`, `original-userid`, `applicationId`, `productIds`).

```js
(async function(){const e=(window.__x||[]).filter(a=>/approval\/search/.test(a.u)).pop();
const H=Object.assign({},e.h);delete H['content-length'];
const b=JSON.parse(e.b); b.filters=[]; b.pageInfo={start:0,rows:50};
const r=await fetch(e.u,{method:'POST',headers:H,body:JSON.stringify(b)});const j=await r.json();
return JSON.stringify((j.data.hits||[]).map(h=>({id:h.id,status:h.status,
 created:new Date(h.createdTime).toLocaleString(),
 tasks:(h.approvalTaskResponses||[]).map(t=>({st:t.status,elig:(t.eligibleApprovers||[]).map(a=>a.approverId),appr:(t.approvers||[]).map(a=>a.approverId)})),
 rules:h.rules})))})()
```
`hits[].rules[].levels[].approvers[].approverId` = the actual approver list. `eligibleApprovers` vs `approvers`
tells you who *could* approve vs who *did*. This is how you prove an approver is (or isn't) on the rule
**without** Approval Setup View. Top-level `status:"PENDING"` filter alone returns 0 — use `filters:[]` and read `status` per hit.

## STICKY DESKTOP ALERT — `notificationStylePreference.WEB` (verified TL 1092, 2026-08-25)

"Can the desktop alert STAY instead of disappearing?" → **Yes.** The Web column cell has a small
style dropdown (default label "General") next to its toggle, at approx **(785, 429)** for the first row.
It is a **MULTI-SELECT** — options:

| Option | API value | Behavior |
|---|---|---|
| General Notifications | `GENERAL` | transient toast, auto-dismisses (the default) |
| **Alert Banner** | `ALERT_BANNER` | **persistent banner — stays until acknowledged** ← what you want for approvals |
| Nudge Banner | `NUDGE_BANNER` | recurring nudge |

Selecting Alert Banner does NOT replace General — both stay checked. Saved payload:
```json
"notificationStylePreference":{"WEB":["GENERAL","ALERT_BANNER"]}
```
Verify via `GET /api/notificationServiceV2/u/user/preference/<dealerId>` → row `.notificationStylePreference.WEB`.

Also on the same row: `soundPreference.WEB` (default `false`) — there's an audible-chime option, separate from style.

**Same per-dealer trap applies** — the style is stored on the per-dealer override row, so set it with
`View By` pointed at the correct store.

## Check the user's TEXT destination number (new 2026-08-25)

Text notifications go to the **USER record** phone, not the employee record — and they routinely differ.
- User record: `POST /api/userservice/u/v2/userandroles?locale=en_US` body `{...,"searchText":"<name>","filters":[]}` → `phone`
- Employee record: `POST /api/userservice/u/employee/search?locale=en_US` `{"searchText":"<name>"}` → `phoneNumber`

Sean Preston TL: user `6619522134` vs employee `6616097997` — **different numbers**. If the user-record number
isn't the person's cell, texts silently go nowhere with every toggle correctly ON. Always reconcile both before
blaming the notification engine.

**EMAIL destination** comes from the same two records — check both the same way
(`email` on the user record, `email` on the employee record). In the Sean Preston case they MATCHED
(`spreston@tol-av.com` both places), which is the useful contrast: **phone mismatched, email did not.**
So if email still doesn't land after the toggle is verifiably saved on the right dealer, it's a
delivery-side problem (recipient spam filtering / Tekion sender reputation), not a config problem —
say that plainly rather than re-walking the toggles.

## TRIAGE ORDER for "I turned it on and they still get nothing"
Run in this order; each step is cheap and rules out a whole class of cause.
1. **Verify the save actually persisted, by API, for the RIGHT dealerId** — `GET /api/notificationServiceV2/u/user/preference/<dealerId>`,
   read the event row's `preference` + `override`. The UI renders defaults on unsaved rows and will lie. (#1 real cause = per-dealer `View By` drift.)
2. **Verify the person is actually an approver on the rule** — Approval Workspace search replay (above). If they're not on the rule, no notification setting can help.
3. **Reconcile the destination** — user-record phone vs employee-record phone; same for email.
4. **Only then** suspect the delivery engine — and open a Tekion ticket with 1–3 attached as evidence.
5. **Recommend Alert Banner regardless.** It's the most reliable of the three channels: no phone number
   to be wrong, no deliverability to fail, renders in the app the approver already has open all day.

## ⚠ APPROVAL WORKSPACE notifications (verified TL 1092, 2026-08-25)
Joe: "how do I turn on approval workspace notifications so the approver gets a text/email?"

**The events (module Core → group "Approval Management"):**
| eventType | title | channels available |
|---|---|---|
| `APPROVAL_REQUEST_RECEIVED_FOR_APPROVAL` | REQUEST RECEIVED FOR APPROVAL ← **the approver's ping** | EMAIL, WEB, MOBILE, TEXT |
| `APPROVAL_REQUEST_SENT_FOR_APPROVAL` | REQUEST SENT FOR APPROVAL (submitter confirm) | all 4 |
| `APPROVAL_REQUEST_SENT_GOT_{APPROVED,REJECTED,RETURNED,WITHDRAWN}` | submitter outcome | all 4 |
Fleet default = `{WEB:true, MOBILE:true, TEXT:false, EMAIL:false}` → **that's why nobody
gets texts/emails out of the box.**

**THE BIG GOTCHA — preferences are STRICTLY PER-USER, self-service only.**
An admin flipping their own toggles does NOTHING for anyone else. Proven:
- `GET /api/notificationServiceV2/u/user/preference/<dealerId>` **ignores** a spoofed
  `userId` header and a `?userId=` query param — the returned rows always carry the
  caller's own userId. There is no `.../user/<id>/preference/...` route (404).
- No dealer/admin-level override endpoint exists: `/u/dealer/<id>/preference`,
  `/u/admin/preference/<id>`, `/u/user/preference/default/<id>` all 404
  `unexpected.error`.
- **User Mimicking is NOT a dealer tool** — KB0011016 says it's an internal ARC app for
  Tekion employees only (requires a Tech Motors Pod 0 login + @tekion email). Do not
  tell Joe to mimic a user.
→ **Answer: each approver must open their own Profile Settings → Notification Settings
→ search "approval" → toggle Text/Email on `REQUEST RECEIVED FOR APPROVAL` → Save.**
On Save, a multi-dealer user gets an "Apply changes to" modal: *All dealerships*
(incl. overrides) vs *Dealerships without Override*.

**Reminders are a RULE setting, not a user setting** — Approval Setup
(`/core/approval-setup`) → business process → rule → *Additional Options* →
**Reminders** (interval min/hrs) + **Request Expiry**. That's the nag for an approver
sitting on a request (KB0021229).

**PERMISSION WALL hit 2026-08-25:** clicking a business-process row on
`/core/approval-setup` silently does nothing for Joe's System Administrator role.
The API says why: `GET /api/arcapproval/u/approval-setup/<id>` → 400
`TDA156 "User does not have permission to View Rules!"`. Needed perms (KB0021229):
**Approval Setup View · Approval Setup Edit · View All Rules \<Department\> ·
Edit All Rules \<Department\>** at Roles → Permissions → Core → Approval Setup.
Until that's granted you CANNOT verify who is actually listed as an approver on a
rule. Say so — don't guess that the user is on the rule.
Related: Approval Workspace `/core/approval-workspace` (+ `/settings` → Auto
Delegation / Self Approvals, store-wide). "All Approvals" in the left dropdown needs
the **All Request View Approval Workspace** permission (KB0021275).
KB refs: KB0021275 (workspace overview) · KB0021229 (add rule) · KB0021414 (statuses) ·
KB0021347/21549 (auto-delegation) · KB0021348 (self-approvals) · KB0014652 (notif tab).

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
6. **RO/Job/Recommendation TAGS (badges on the RO)** — Service Settings
   `/service/settings/ro-settings` → left-nav **Tags** (+ **Archived Tags**).
   This is where "Add-on", "Recall", "Due Bill", "Hold", "Service Menu" etc. live.
   Not a notification at all — a visual flag on the job/RO. See the RESOLVED
   section at the top of this skill.

Whole-doc scan trick for any of these settings pages:
```js
const l=document.body.innerText.split('\n').map(x=>x.trim()).filter(x=>x);
l.forEach((x,i)=>{if(/notif|notify|alert/i.test(x))console.log(i,x)});
```
`/service/settings/ro-settings` is ~1,990 lines — never read it linearly, always grep
the innerText array and slice around the hit index.

## Pitfalls (all hit live 2026-08-24 / 2026-08-25)
- **The `:9223 /eval` param is `js`, NOT `expression`.** Sending `{"expression":...}`
  returns `{"error":"js is required"}` — easy to misread as "the browser is broken."
  Cost a turn 2026-08-25.
- **`/screenshot` returns JSON, not a PNG.** `curl -o x.png /screenshot` writes
  `{"screenshot":"<base64>"}` and `vision_analyze` rejects it with *"Only real image
  files are supported"*. Always
  `base64.b64decode(json.load(open(f))["screenshot"])` → real .png first.
  Also: `browser_vision` opens a SEPARATE unauthenticated context (returns a blank
  page) — never use the `browser_*` tools against the :9223 session.
- **Clicking the "Notification Settings" tab can BOUNCE you off `/userProfile`.**
  Observed: clicked (530,155), and a later `location.href` read
  `…/ro/repair-order/6a8df…` — the click landed on a stale prior page and the XHR
  hook array came back `undefined` (`Cannot read properties of undefined`). Fix:
  `/navigate` to `https://app.tekioncloud.com/userProfile`, `sleep 9`, **assert
  `location.href` is /userProfile**, THEN arm the hook, THEN click. Re-assert the URL
  after the click before reading `window.__x`.
- **The `/userProfile` page renders My Profile AND Notification Settings in the same
  DOM** — `document.body.innerText` shows "Personal / Employment / Email Signature"
  even when the Notification tab is active. Don't conclude the tab didn't open from
  innerText alone; check for the "Notification Type: / Notified On: / View By:" filter
  strings further down, or screenshot it.
- **Approval Setup business-process rows are NOT clickable by any method I found.**
  `/mouse` on the row text (127,301), synthetic MouseEvent on the `.rt-tr`, and pendo
  removal all returned success with zero navigation — the page stayed on
  `/core/approval-setup`. (An RO toast — "Repair Order - 150869: Fulfilment Request" —
  popped instead, i.e. the click went somewhere else entirely.) Don't burn turns on it;
  the list view already gives business process / department / last modified / rule
  count, and KB0021229 documents the rule editor. Revisit with a fresh page load +
  `/pages` bound-tab check if drill-in is actually required.
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
- **Capturing `window.__H` (real axios headers) is fragile.** The hook must be armed
  AFTER the SPA route has loaded and BEFORE the triggering click; a full `/navigate`
  wipes it. Reliable recipe: navigate → sleep 3 → arm hook → sleep 6 → click a
  refresh/reload icon on the page → read `window.__x[0].h`. Hooking `fetch` alone
  misses these (they're XHR); hooking both is safest. Captured headers only work for
  the dealer you captured them under — reusing them against another `dealerId` in the
  URL returns 500 `"Token doesn't exist or is invalid"`.
- **User Setup (`/core/user-setup`) search:** the row search input is hidden until you
  click the magnifier (~x1065,y164); it's `input[placeholder="Search..."]`. Tag it with
  a `data-jay` attr, fill via the :9223 `/type` endpoint (native value-setter alone
  doesn't commit), then dispatch a REAL `keydown+keypress+keyup` Enter — the server
  won't filter without Enter. There is no `/key` endpoint on the :9223 server.
  Underlying API: `POST /api/userservice/u/v2/userandroles` with
  `{sort,filters,searchText,pageInfo:{start,rows}}` → returns full user records
  (email, phone, roles, MFA, active) — faster than driving the grid.
- Clicking a user row opens `/core/user-setup/edit/<userUuid>` (User Details: Login Id,
  Phone Number, roles, MFA). The row kebab (~x1232) only offers Force Logout /
  Deactivate / Edit Login Id — **no way to edit another user's notification prefs.**

## Related skills
`tekion-service-settings` (section map) · `tekion-sitemap` (URLs) ·
`tekion-scheduling` (notify-parts toggles) · `tekion-kb-search-scrape` (KB lookup) ·
`tekion-parts-appointments-opcode-scoping` (per-opcode parts-prep flag).
