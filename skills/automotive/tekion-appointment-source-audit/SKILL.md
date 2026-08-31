---
name: tekion-appointment-source-audit
description: Answer "why do appointments from vendor X show as Integration / can we relabel the appointment source" and audit appointment volume by source (BDC, Consumer, Walk-in, Integration/Open API, AI) per store. Covers Tekion's fixed appointmentSource→category enum, the internal /api/scheduling/u/appointment/search aggregation API, and how to identify which vendor is behind an Integration bucket.
triggers:
  - why do appointments show as integration
  - can we relabel the appointment source
  - appointment source audit by store
  - bdc vs walk-in vs integration appointments
  - which vendor is behind the integration bucket
  - open_api appointment source
  - ai bdc appointment bucket
  - appointment volume by source per store
---

# Tekion — Appointment Source / "shows as Integration" audit

## The question this answers
"Appointments booked through <AI/BDC vendor> come over as **Integration** in the
scheduler. Can we set that up on our end, or does the vendor need to change it?"

**Short answer: it is NOT a dealer setting.** `appointmentSource` is stamped by the
system that CREATES the appointment, and the source→category mapping is a Tekion
PLATFORM-level enum, identical at every dealer.

## Ground truth: the source→category map
`GET /api/scheduling/u/appointment/source-categories` (internal, no body).
Verified 2026-08-26: returns the **identical 26-entry map at all 7 AMG dealers**
(682 bytes, 26 keys each) — proof it is not dealer-configurable.

```
WALKIN bucket:            WALK_IN_KEYLOUNGE_TOWED_TRUCK, WALK_IN_KEYLOUNGE, WALKIN_WEB,
                          WALK_IN_MOBILE, WALK_IN_IOT, WALKIN_MOBILE, WALK_IN_WEB, WALKIN_IOT
INTEGRATION bucket:       GM_OSS, ARDS_BOL, ARDS_CCC, WI_ADVISOR, TOYOTA_INTEGRATION, OPEN_API
AI bucket:                MARKETING_AI, AI_BDC, T1_AI
BDC_SCHEDULING:           BDC_SCHEDULING
CONSUMER_SCHEDULING:      CONSUMER_SCHEDULING
CONSUMER_KIOSK:           CONSUMER_KIOSK
INTERNAL:                 INTERNAL, SALES_KIOSK, DEALS
MIGRATION:                NEW_DEALER_MIGRATION, EXISTING_DEALER_MIGRATION
RO:                       RO
```

**Key implication:** an **AI** category ALREADY EXISTS. A vendor that writes through
the generic public Open API gets `OPEN_API` → bucket `INTEGRATION`. To land in the
AI bucket the vendor must be onboarded by Tekion as an AI-class source
(`AI_BDC` / `MARKETING_AI` / `T1_AI`). That is a **Tekion + vendor** change — there
is nothing to toggle in Scheduling Settings, Vendor Data Sharing, or Integration Hub.
(Confirmed: `GET /api/scheduling/u/settings/appointment` has NO source/label field —
only `externalSourceCapacities` / `externalSourceNotifications` booleans, which are
capacity/notification behavior, not labelling.)

## Where the label surfaces in the UI
`/dse-v2/appointments/list` (Appointments **list** view, not the scheduler calendar)
has two columns: **Appointment Source** (the friendly bucket, e.g. "Integration",
"BDC Scheduling", "Walk-in") and **Appointment Sub Source** (renders the raw code for
OEM feeds, e.g. `GM OSS | - | GM_OSS`; blank `-` for OPEN_API).
The scheduler day-view detail drawer shows only the creating USER (e.g. "System User"),
not the source — use the list view.

## Method — count appointments by source, per store, no quota cost
Uses the :9223 authenticated browser. A bare in-page `fetch()` to
`/api/scheduling/...` returns **500 "Token doesn't exist or is invalid"** — the app's
axios interceptor adds auth a bare fetch can't. Capture the real headers first:

```js
// 1) arm header capture
(()=>{window.__H=null;const sh=XMLHttpRequest.prototype.setRequestHeader;
XMLHttpRequest.prototype.setRequestHeader=function(k,v){this.__h=this.__h||{};this.__h[k]=v;return sh.apply(this,arguments);};
const o=XMLHttpRequest.prototype.open,s=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return o.apply(this,arguments);};
XMLHttpRequest.prototype.send=function(b){const self=this;this.addEventListener('load',()=>{
 if(self.__u&&self.__u.includes('/api/scheduling/'))window.__H=self.__h;});return s.apply(this,arguments);};return 'ok';})()
// 2) fire a scheduling call so __H populates (SPA nav keeps hooks; hard nav kills them)
history.pushState({},'','/dse-v2/appointments/scheduler/month');window.dispatchEvent(new PopStateEvent('popstate'));
```

Then aggregate. **Cross-store works by swapping only `dealerId` + `tek-siteId`** —
no dealer switch needed:

```js
const h=Object.assign({},window.__H); h.dealerId='876'; h['tek-siteId']='-1_876';
const body={pageInfo:{start:0,rows:0},
 filters:[{operator:"GTE",values:[Date.now()-60*86400000],field:"createdTime"}],
 groupBy:[{key:"appointmentSource",field:"appointmentSource",groupType:"FIELD",filters:[]}]};
const j=await (await fetch('/api/scheduling/u/appointment/search',
  {method:'POST',headers:h,body:JSON.stringify(body),credentials:'include'})).json();
j.data.groups[0].buckets.map(x=>x.key+':'+x.docCount);   // lowercased keys
```
- `rows:0` = aggregation only (fast, no payload).
- `groupBy` supports nested `subGroups` (e.g. schedulingType → appointmentSource).
- Filter a single source with `{operator:"IN",values:['open_api'],field:"appointmentSource"}`.
- Sort `{order:"ASC"|"DESC",field:"createdTime"}` + rows:1 gives first/last-ever
  appointment from a source = when the integration went live.
- Free-text `searchText:"MIA"` searches customer/comment text (useful but noisy).

## Identifying WHICH vendor is behind an Integration bucket
`externalSourceInfo` is always null and there is no vendor-name field. Use:
1. **Per-store exclusivity** — if a store's only INTEGRATION source is `open_api`,
   then Integration == that one vendor at that store (already a clean filter).
   OEM feeds are distinguishable: `GM_OSS` (GM stores), `TOYOTA_INTEGRATION`.
2. **`customerComments` fingerprint** — AI voice-agent bookings write a narrative
   summary ("The customer needs to schedule a 28,000-mile service for his 2025 Toyota
   Camry."). Rules-based/OEM feeds leave it null.
3. **`oemExternalId`** — populated on OEM feeds (GM_OSS), null on OPEN_API.
4. **Definitive test:** get ONE known appointment number from the vendor and pull its
   `appointmentSource` directly (`searchText:"<apptNo>"` or filter on `apptNo`).

## AMG baseline — last 30 days, captured 2026-08-31 (source group-by)
| Store | total | bdc_scheduling | consumer | walk_in_web | open_api | other |
|---|---|---|---|---|---|---|
| ST 876 | 5,981 | 3,630 | 989 | 925 | **437** | – |
| BT 1249 | 4,182 | 2,782 | 595 | 551 | **254** | – |
| TL 1092 | 5,018 | 3,438 | 558 | 897 | **125** | – |
| SV 826 | 835 | 433 | 168 | 134 | **17** | ai_bdc 83 |
| BC 1251 | 2,201 | 1,324 | 155 | 467 | **5** | gm_oss 250 |
| VC 1891 | 882 | 489 | 200 | 193 | 0 | – |
| AR 6195 | 202 | 141 | 50 | 11 | 0 | – |
Reading: ST/BT/TL Integration == open_api == one vendor, clean 1:1 filter. BC Integration is
MIXED (gm_oss + open_api) → must use Sub Source. VC/AR have NO integration bookings at all.
SV has open_api AND ai_bdc → two vendors, must confirm which is which before attributing.

## AMG baseline (last 60 days, captured 2026-08-26)
| Store | BDC | Consumer | Walk-in | Integration (open_api) | AI (ai_bdc) |
|---|---|---|---|---|---|
| ST 876 | 7,826 | 2,053 | 1,719 | **649** | – |
| BT 1249 | 5,883 | 1,212 | 1,066 | **321** | – |
| TL 1092 | 7,095 | 1,102 | 1,771 | **292** | – |
| SV 826 | 917 | 344 | 295 | **73** | **179** |
| BC 1251 | 2,878 | 326 | 863 | 453 (gm_oss) | – |
| VC 1891 | 1,104 | 364 | 483 | 0 | – |
| AR 6195 | 205 | 59 | 24 | 0 | – |

Note SV carries BOTH `ai_bdc` and `open_api` — two different AI/integration vendors
coexist there; do not assume a single vendor owns "the AI appointments" fleet-wide.
`open_api` first appearances: BT Nov 2022, SV Aug 2024, ST Mar 2025, TL Aug 2025.

## "Can we list vendor X as an AGENT instead of an Integration?" — NO (verified 2026-08-31)
Named-agent attribution in Tekion comes from TWO places, and neither can hold a vendor:
1. **`appointmentTakerUserId`** on the appointment = the dimension BDC-agent reporting
   groups by. Verified: for EVERY external source it is `null`.
   - `OPEN_API` (ST/BT/TL/SV/BC): `createdByUserId="1"` (System User), `appointmentTakerUserId=null`,
     `externalBdcAgent=false`, `externalId=null`, `appointmentChannel=null`, `leadId=null`.
   - `AI_BDC` (SV, Tekion's own AI class): `createdByUserId="-1"`, `appointmentTakerUserId=null`.
     **So even getting reclassified to the AI bucket does NOT produce an agent name** — there is
     no field on the appointment for an external agent identity.
   - Contrast `bdc_scheduling`: taker is a real user UUID and groups cleanly
     (ST 7d: 159/135/121/103/85… per agent).
2. **`bdcAgentIds`** array in `GET /api/scheduling/u/settings/appointment` — the store's BDC agent
   roster. Verified 2026-08-31: ST has 6 UUIDs, all other 6 stores `[]`. It accepts only real
   Tekion USER records, and adding one would not help because Open API writes stamp System User,
   not the roster user. (Also: creating a Tekion user for a vendor needs Joe's explicit OK.)
**Conclusion to give Joe:** vendor-as-agent is not achievable at any layer — dealer setting,
Tekion reclassification, or a dummy user. Track by SOURCE FILTER instead, and build the
attribution report externally off `appointmentSource`.

### "What if I just CREATE a Tekion user called MIA?" — doesn't work either (verified 2026-08-31)
365-day group-by on `createdByUserId`, filtered to all 6 external sources:
| Store | ext-source appts (1yr) | createdBy breakdown |
|---|---|---|
| ST 876 | 3,898 | `1`:3,898 (100% System User) |
| BT 1249 | 1,616 | `1`:1,614 + 2 UUIDs @1 each |
| TL 1092 | 1,794 | `1`:1,794 |
| SV 826 | 1,324 | `-1`:788 (ai_bdc) + `1`:533 + 3 UUIDs @1 each |
| BC 1251 | 2,184 | `1`:2,184 |
The 5 UUID outliers are 1 appointment each and are HUMANS who later rescheduled the record
(BT appt161414/161324 = `status MISSED_RESCHEDULED`, `updatedAppointmentSource` flipped to
`BDC_SCHEDULING`) — the record gets re-stamped on human touch, it is not vendor attribution.
So: a new user record would simply never be referenced. The Open API write stamps System User
no matter which users exist. **The only path where a MIA user actually shows as an agent is if
MIA stops writing via Open API and instead books AS that user through the BDC scheduling path** —
then `appointmentSource` becomes `BDC_SCHEDULING` and taker = MIA's user id, and MIA appears in
native BDC agent reports. Costs/consequences to state: a Tekion user seat, MIA holding live DMS
credentials with scheduling access, MIA's volume merging into the BDC bucket (loses the clean
vendor split), and it STILL requires MIA to change their integration — so no advantage over
asking Tekion for AI-class onboarding. **NEVER create the user — Joe's hard rule is no employee/
user record changes without his explicit permission.**

**KNOWN GAP (do not guess):** the `Appointment Create` / `Update Appointment` WRITE specs are
listed in the plan quota sheet (`specs/plan-details/dealer-level-apis-full.txt` lines 26-35) but
were NOT captured in `specs/apis/` — Service Appointments only has 10 read/search endpoints. So
whether the create payload exposes a taker/agent field is UNVERIFIED. Re-scrape APC docs for the
Service Appointment write endpoints before asserting either way.

## Known AMG case: MIA (asked again 2026-08-27, and 2026-08-31 "list MIA as an agent")
Joe: "appointments made through MIA come over as Integration — can we set that up or
does MIA need to change it?" **Answer given: MIA must fix it on their end.** MIA books
through the generic public Open API → `OPEN_API` → Integration. No dealer-side toggle.
Ask = MIA opens a ticket with Tekion to be onboarded as an AI-class source
(`AI_BDC`/`MARKETING_AI`); cc the AMG Tekion rep since it's a partner-registration change.
Interim: at ST/BT/TOL `open_api` is the ONLY Integration source, so
"Integration" already == MIA there; use the Appointments **List** view columns.
Still open: get one known MIA appointment number to confirm `OPEN_API` definitively
rather than by inference, then build a standing MIA-attributed appointment/conversion
report off that filter (offered to Joe, not yet built).

## Pitfalls
- Dealer switcher popover row coords go stale fast; the popover auto-closes. For
  read-only cross-store work **skip the switcher entirely** — swap the two headers.
- `window.__H` is wiped by any hard `/navigate`; re-arm and re-fire a scheduling call.
- The :9223 `/screenshot` endpoint is **GET** and returns JSON `{screenshot:<base64>}`,
  not a file. `browser_vision` opens a DIFFERENT unauthenticated context — useless here.
- Don't use the OpenAPI `/service-appointments:search` for counts (pagination 500s,
  massive undercounts) — the internal endpoint above is ground truth.

## Related
`tekion-scheduling`, `tekion-vendor-data-sharing-audit`, `tekion-sitemap`.
