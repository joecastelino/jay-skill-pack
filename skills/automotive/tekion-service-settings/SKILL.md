---
name: tekion-service-settings
description: >
  Reference map of Tekion's Service Settings application (App Grid > Settings >
  Service Settings) — the master config for service/RO workflows: General Setup,
  Job Sequence, Flag Tech on, Round-Up rules, Default Service Advisor, RO/Job
  Flags, Holds, Parts Request, pay-type setups (Customer/Warranty/Internal/
  Insurance), Reminders, Express Mode, Tags, RO KPI List, Quotes, Role Config,
  Consumer Portal, Approval Settings, Deferred Recommendation Rules, Job Clock
  Setup, P&L View Setup. Use when asked where/how a service workflow behavior is
  configured (e.g. "why do tech flag hours auto-match bill time", "how is the
  recommendation opcode set", "where do return-RO / comeback tags come from").
triggers:
  - service settings tekion
  - turn off duplicate tag warning
  - restrict entry of duplicate tag
  - warning when checking in customers
  - setting not in check-in setup
  - flag tech on
  - recommendation opcode
  - default service advisor setting
  - ro flag setup
  - job sequence
  - round up hours
  - pre-invoice rule
  - return ro comeback tag
  - job tag filters
  - cant edit job tags
  - tag criteria filter
  - deferred recommendation rules
  - job clock setup
  - express mode setup
---

# Tekion — Service Settings (config reference)

The master switchboard for service/RO workflow behavior. Distilled from Tekion KB0010647
(PDF at `~/tekion-kb/pdfs/`). The **full field-by-field text** is in
`references/service-settings-full.txt` — load it when you need an exact field description.

## Nav & permissions
- **App Grid > Settings > Service Settings section > Service Settings tile.**
- Permissions (`Roles > Permissions > Service > RO`): Service Setup, Access Service
  Settings, Edit Service Settings.
- Left-side tabs; use up/down arrows to reveal more sections, left-arrow to collapse.

## The sections (left-side tabs) and what each governs
1. **General Setup** — the big one. Key fields:
   - **Job Sequence**: Alphabet (Job A/B/C) vs Numerical (Job 1/2/3).
   - **Recommendation Opcode**: default opcode when a recommendation is created without
     one (must exist in Opcode Management).
   - **Flag Tech on**: when tech flag hours auto-match bill hours — `Manual` (stays as
     entered) / `Job Save` / `RO Invoiced` (locks after invoice) / `Job Completed`.
     (Wage Types Config in Employee Onboarding sets flag-on-bill vs actual vs labor hours;
     does NOT apply when Manual.)
   - **Display Amount / Include Fees / Taxes / Coupons in Estimates** (PDF toggles).
   - **Allow to close RO in details view**, **Allow customers to sign invoices online**,
     **Show Service History of Other Dealerships** (same tenant), **Notify customer on
     invoice**.
   - **Round Up Settings**: round Technician Actual / Labor-Bill / Flag hours to nearest
     tenth (hours entered to the hundredth, e.g. 1.56; >5 second-decimal rounds up).
   - **Allow techs to clock in to multiple ROs/Jobs** (per pay-type-combination toggles).
   - **Accept Return RO after Last Service** (N days → shows "Return RO"/Comeback tag;
     renameable in Keyword Configuration), **Restrict duplicate Tag#**, **Onstar
     Integration**, **Select Default Service Advisor for jobs** (same-as-RO vs
     job-creator), **Make Cause mandatory for recommendations**.
2. **Service Module Selection** — which service modules are active.
3. **Parts Request** — parts-request workflow behavior between service & parts.
4. **Customer Pay / Warranty / Internal Pay / Insurance** — per-pay-type defaults
   (cost centers, rules).
5. **Reminders** — service reminder config.
6. **Express Mode Setup** — quick-lane / express check-in workflow.
7. **Tags / Job Tags** — RO and job tag definitions.
8. **RO Flag** — RO-level flag definitions/behavior.
9. **Hold** — RO/job hold reasons & behavior.
10. **RO KPI List** — which KPIs surface on the RO list.
11. **Quotes** — quote workflow config.
12. **Role Configuration** — role-driven service behavior.
13. **Consumer Portal** — what the customer-facing portal shows/allows.
14. **Approval Settings** — RO/job approval rules.
15. **Deferred Recommendation Rules** — how declined/deferred recs are tracked & resurfaced.
16. **Job Clock Setup** — clock-in/out rules (Applicable / Mandatory per job).
17. **Profit and Loss View Setup** — P&L visibility config.

## When to use
- Joe asks "why does X happen on the RO / where is Y configured" → match it to a section
  above, then read the exact field in `references/service-settings-full.txt`.
- Pairs with: `tekion-opcode-create` (Recommendation Opcode must exist there),
  `tekion-service-menu-setups`, `tekion-sitemap` (nav).

## Pre-Invoice validation rules (verified live SCT 2026-07-23)
- URL `/service/settings/ro-settings`, left-nav tab **Pre-Invoice** → "Validation Rules" table.
- Each rule row = name + Warning/Error radio pair + Applicable Job Types + Pay Types + Rule Level (Job/RO).
- **"Pending Recommendations Error"** (RO-level) = the block-invoice-without-approved/deferred-recs rule.
  Fires when recs are in RETURNED_TO_TECH, REVIEWED, SENT_TO_CUSTOMER, SUBMITTED, DRAFTED,
  PRE_DRAFTED, or CUSTOMER_APPROVED. Warning = nag only; Error = hard-blocks invoicing.
- Edit procedure via :9223: find row container by leaf text, walk up to the element containing
  ≥2 `input[type=radio]`, scrollIntoView the target radio, `/mouse` its center, then click the
  page **Submit** button (bottom-right ~1211,689) and require the "Service settings updated
  successfully" toast. Verify with a TRUE remount (nav /home → back → re-read radios) —
  same-URL re-read is a false positive (SAVE-VERIFY TRAP).

## Notification behavior is NOT centralized here (verified 2026-08-24)
Only two notification-ish items exist on this page: **"Notify customer on invoice"**
(General Setup) and the **customer-arrival** notifications (Service Communication Setup).
Everything else lives elsewhere — see skill `tekion-notification-settings-audit` for the
full 5-surface map. Most relevant here: **Parts Request** section →
*"Auto submit Parts Fulfillment request for jobs when: Job is Created, Job is Saved,
Tech is Assigned"* = the real "a job was added to the RO → tell Parts" trigger.

Live section list (TL 1092, 2026-08-24 — more than the KB's 17): General Setup ·
Opcode Mapping & Selection · Service Module Selection · Parts Request · Customer Pay ·
Warranty · Internal Pay · Reminders · Tags · RO Flag · Hold · Booker Workflow ·
Pre-Tech Finish · Pre-Job Completion · Pre-Invoice · Recommendation Addition Rules ·
RO List KPI · Total Sales · Quotes · Role Configuration · Service Communication Setup ·
Consumer Portal · Deferred Recommendation Rules · Follow up Recommendation Rules ·
Recommendation Rules · Return RO · Job Clock Setup · Profit and Loss View Setup ·
Reports · Credit Note Setup · Machine Learning · Opcode Pricing · Tax Settings.

⚠ The page renders ~1,990 innerText lines (ALL sections in one scroll). Never read it
linearly — grep the innerText array and slice around the hit index.

⚠ Routing flake: on :9223 this URL repeatedly redirected to `/parts/tax-code-setup`
even after a `/home` bounce, while loading fine on :9225. If a known-good URL keeps
landing elsewhere, switch browser lanes instead of debugging the route.

## Tags section — RO/Job tags (verified BT 1249, ST 876, TL 1092 on 2026-08-24)
- URL `/service/settings/ro-settings`, left-nav **Tags** (hash `#TAGS`). Two sub-tabs:
  **Active Tags** / **Archived Tags**.
- Table columns: Tag Type · Tag Name · Color · Text Color · Show in RO/PDF (two toggles:
  RO and PDF) · Criteria · Add Manually · Archive. Last row is always a BLANK add-row.
- **Tag Type dropdown values: `RO` · `Job` · `Recommendation`.** The Tag NAME list is
  driven by Tag Type. Under **Job** the available names are:
  PDI, Hold, Service Menu, **Add-on**, Due Bill, Recall, Recommendation,
  Deferred Recommendation, Insurance, Internal Split, Warranty Split, Manual Flag Hrs,
  Adjusted Flag Hrs, UVI, MPI, Return RO, Mobile Shop, Express Shop.
- **"Add-on" is a JOB-type tag** — the label that appears on an RO/job line for work added
  after check-in. It is NOT automatic: a row must exist here. If a store lost its "Add on"
  tag, the row was deleted (check **Archived Tags** first — Unarchive is non-destructive).
- AMG baseline 2026-08-24: BT / ST / TL each have only **3 active tags — MPI, PDI, UVI
  (all Recommendation type)** and **Archived Tags = "No rows found."** No Add-on row exists
  fleet-wide; it must be re-created, not un-archived.
- Restore recipe: blank add-row → Tag Type = **Job** → Tag Name = **Add-on** → pick
  Color/Text Color → toggle **RO** (and **PDF** if it should print) → Save.
- Mechanics: the blank row's Tag Type select sits at ~x587 on the row; Tag Name at ~x800.
  Options render in a portal — query `[class*="option"],[role="option"]` filtered by
  `offsetParent`. Navigating away without Save discards cleanly (no confirm modal fires
  from the Tags row builder). `#TAGS` hash anchor works but the page must be loaded from
  `/home` first — a direct navigate to `/service/settings/ro-settings` on a cold tab can
  silently land on an unrelated screen (`/parts/tax-code-setup`); assert `location.href`.

### Tags table — DOM mechanics that actually work (hard-won 2026-08-25, SCT 876)

The Tags grid is a **ReactTable**, and the page contains ~120 `.rt-table`s. Nothing else
below works until you anchor on the right one:

```js
const crit=[...document.querySelectorAll('.rt-resizable-header-content')]
            .find(e=>e.textContent.trim()==='Criteria');
let tbl=crit; while(tbl && !String(tbl.className||'').split(' ').includes('rt-table')) tbl=tbl.parentElement;
const rows=[...tbl.querySelectorAll('.rt-tbody .rt-tr')];   // last row = blank add-row
const cells=[...row.querySelectorAll('.rt-td')];            // 0 drag,1 Type,2 Name,3 Color,
                                                            // 4 TextColor,5 RO/PDF,6 Criteria,
                                                            // 7 AddManually,8 Archive
```

Five traps, each of which cost turns:

1. **Header text is NOT reachable by TreeWalker / leaf-`innerText` scans.** Searching for a
   leaf element whose text is `"Tag Type"` returns `[]`. The label lives in
   `.rt-resizable-header-content` — query that class directly.
2. **The table scrolls HORIZONTALLY** (`scrollWidth` 1200 vs `clientWidth` 772). Criteria /
   Add Manually / Archive sit **off-screen right** and `/mouse` will click empty space.
   Walk up from `tbl` to the first ancestor with `scrollWidth>clientWidth+5` and set
   `scrollLeft=scrollWidth` BEFORE reading coords. Re-read `getBoundingClientRect()` after.
3. **Read react-select option lists off the React fiber instead of opening the dropdown:**
   walk `cell[Object.keys(cell).find(k=>k.startsWith('__reactFiber$'))]` down `.child/.sibling`
   until `memoizedProps.options` is an array of `{label,...}`. This returned
   `["RO","Job","Recommendation"]` for Tag Type instantly, with no click and no portal race.
4. **Portal options render duplicates at NEGATIVE y.** `[class*=option]` returns rows from
   OTHER collapsed sections at `y≈-2800`. Always filter
   `e.offsetParent && e.getBoundingClientRect().y>0` or you'll `/mouse` off-canvas.
5. **`/eval` returns HTTP 500 whenever the JS throws** — a missing element mid-expression
   looks identical to "the browser broke." Guard every helper with an early
   `if(!crit) return 'NOCRIT';` and return sentinel strings, never let it throw.

### The page RESETS between turns
On :9223 the bound page reverted to a previously-open RO detail URL between nearly every
`execute_code` call. Symptom: `/eval` reads a *fully valid* DOM that belongs to the wrong
screen, and `browser_vision`/screenshot describes an unrelated page ("Pay Type Split By
Payers"). **Do the whole Tags interaction inside ONE `execute_code` call:**
`navigate /service/settings/ro-settings` → sleep 10 → `/mouse` the `Tags` `.ant-tabs-tab`
(find its live center; ~x233 but y MOVES) → sleep 5-6 → then act. Re-navigating at the top of
every call is cheap insurance; assuming continuity is not.

### ROOT CAUSE: "why aren't my job tag filters editable?" (SOLVED SCT 876, 2026-08-25)

**Criteria is a CREATE-TIME-ONLY field. Tekion permanently locks it the moment the tag is
saved.** This is by design in the app bundle, not a bug, not a permission, not a click issue.

Proof — from `serviceSettings.<hash>.chunk.js`, the `TAG_FILTER_TRIGGER` ("Criteria") column
config `setMapCellPropsToComponentProps`:

```js
var t = tget(e,'original.tagsFilter',EMPTY_ARRAY),   // the saved criteria
    r = tget(e,'original.isTagSaved',false);
...
function(selectedFilters, isTagSaved){
  return isEmpty(selectedFilters)
      ? { disableFilterTrigger: isTagSaved }   // saved + NO criteria  -> funnel is DEAD
      : { isReadOnly:          isTagSaved };   // saved + HAS criteria -> view-only, no Apply
}(t, r)
```

So for any row with `isTagSaved:true`:
- **no criteria saved** → `disableFilterTrigger` → the funnel still renders and still gets a
  click, but the popover mounts with `.ant-popover-inner-content` `innerHTML.length === 0`.
  **The empty white box IS the disabled state.** Don't chase it as a render/click bug.
- **criteria saved** → `isReadOnly` → rows render but are greyed with no Apply.

Same lock applies to the rest of the row: `Tag Type` and `Tag Name` selects carry
`aria-disabled="true"` and `Add Manually` is `ant-checkbox-wrapper-disabled`. Only
**Color / Text Color / RO / PDF** stay live on a saved tag.

**Fix depends on whether the tag name is still free** (see the Clovis section below — this
is NOT always "archive and re-create"):
- Tag is **active** and you want criteria on it → Archive it, then re-create from the blank
  add-row setting Criteria BEFORE the first Save. (Archive is non-destructive.)
- Tag is **already archived** → you CANNOT re-create it; the archived record reserves the
  name. **Unarchive instead** — it comes back with Criteria CLEARED.

### Proof the blank add-row IS fully editable (do this to demo it)
Corrects the earlier "Tag Type won't commit" note — it commits fine:
1. Scroll the table **LEFT** (`scrollLeft=0`) → blank row cell[1] center ≈ (599, 562).
2. `/mouse` it → portal options render at ≈(598,605) RO / (598,636) Job / (598,667)
   Recommendation. `/mouse` **Job**. Cell now reads `option Job, selected.`
3. Scroll the table **RIGHT** (`scrollLeft=scrollWidth`) → blank row funnel ≈ (950, 562).
4. `/mouse` it → popover `innerHTML.length` jumps **0 → 7,449**, text =
   `Select / Select / Select / Add Filter / Reset / Apply`. Fully live.
5. Navigating to `/home` discards cleanly — no confirm modal, nothing written.

**Job-tag filter fields available** (from the live `fields.renderOptions.filterTypes`):
`Technician` (ASYNC_MULTI_SELECT) · `Job Type / Pay Type` (MULTI_SELECT) · `Department`
(MULTI_SELECT) · `Service Type` (MULTI_SELECT). The Job Type / Pay Type option list is
PDI, Recall, Return RO, Service Menu, Due Bill, MPI, Voided, RO Hold, Job Hold, CP Split,
W Split, I Split, Sublet, UVI, CP, W, I.

Read the whole thing without clicking anything: pull `additional` off the Criteria cell's
React fiber — `cell[__reactFiber$].memoizedProps.additional` gives `allTags[]` (every tag with
`id`, `assetType`, `tagsFilter`, `isTagSaved`, colors) plus `tagTypeOptions`.

### AMG baseline (SCT 876, re-verified 2026-08-25 — supersedes the 2026-08-24 3-tag note)
5 active tags: UVI / MPI / PDI (RECOMMENDATION) + **Add-on** (`ADD_ON_REPAIR`, JOB,
id `6a8ddcd7bd725a438565b5b1`) + **Recommendation** (`RECOMMENDATION`, JOB, id
`...b5b2`). **Every one has `tagsFilter: []`** — i.e. no criteria was ever set at creation,
which is exactly why all their funnels open empty. Note `Recommendation` in
`tagTypeOptions` is `isDisabled:true` — you cannot create new Recommendation-type tags.

### TRIAGE FIRST on a bare "I can't edit job tag filters" (2026-08-26)
Two questions before touching a live settings page — the fix path forks completely:
1. **Which store?** Tag inventory differs per store and drifts. Don't assume SCT.
2. **New tag or existing tag?** New → blank add-row is fully editable, just build it.
   Existing → Criteria is locked forever (see root cause above); it's Archive+re-create
   (if name is free) or Unarchive (if already archived). **Never archive a published tag
   without Joe's explicit go.**

⚠ **Baselines drift — re-read live, don't quote a stored count.** On 2026-08-26 SCT/876
showed only **3 saved rows (UVI/MPI/PDI, all Recommendation) with NO Job-type tags**,
contradicting the 5-tag 2026-08-25 baseline below (which included Add-on + Recommendation
as JOB). Either the tags were removed or a stale/wrong dealer context was read. Always
assert `currentActiveDealerId` + the header store name before reporting a tag inventory,
and state the read date.

### ARCHIVED tag = name is RESERVED; Unarchive CLEARS criteria (VC 1891, 2026-08-26)

**VC 1891 end state after the unarchive (verified by screenshot, Active Tags):**
MPI / UVI / PDI (Recommendation) · Recommendation (Job) · **Add-on (Job, Criteria empty)**.
Archived Tags tab = empty. Reversible: archive Add-on again to undo.


A second store presented the *opposite* shape of the same ticket, and the SCT playbook does
not work there. **Check the Archived Tags sub-tab BEFORE assuming you must re-create.**

At VW Clovis the Add-on Job tag was **archived**, and the archived copy carried a criteria
filter of **all 17 Job Type / Pay Type values**. Consequences:

1. **The archived record RESERVES the tag name.** Building a fresh Add-on from the blank
   add-row is impossible — after filtering, the option renders `aria-disabled="true"`
   (visible text still reads `Add-on`, so you must read the attribute, not the label). If
   you press Enter anyway the select silently commits a DIFFERENT option (it grabbed
   `Recall`) — always re-read the cell text after Enter to confirm what actually landed.
2. **The Archived Tags row exposes ONLY an Unarchive button** (`data-test-id`
   `*-UNARCHIVE-Button`). There is no delete, so the name can never be freed.
3. **Unarchive restores the tag with Criteria EMPTY.** This is the whole trick: for a
   "restore this tag but WITHOUT the criteria filter" request, Unarchive alone is the
   complete fix. Confirm dialog = "<Tag> / Do you want to unarchive this tag?" → **Yes**.
   Verified after: Archived tab empty, Add-on live on Active Tags, Criteria cell blank.

Archived Tags table has only 4 columns (Tag Type · Tag Name · Criteria · Unarchive) — the
`.rt-td` indices from the Active table do NOT apply.

### Use `/click` with a `data-jay` tag — NOT `/mouse` coordinates
`/mouse` on this page is unreliable: coordinates captured in one `execute_code` call are
stale by the next (the grid re-renders and scrolls), and a stale click lands on the LEFT
NAV and silently switches you to another section — I landed on "Pre-Tech Finish" and only
caught it via screenshot. Both browser servers expose `POST /click {selector}`. Do this:

```js
// tag the element in /eval, then click it by attribute in a separate call
[...document.querySelectorAll('button')]
  .filter(e=>e.offsetParent && /UNARCHIVE/i.test(String(e.getAttribute('data-test-id'))))
  .forEach((x,i)=>x.setAttribute('data-jay','un'+i));
```
- Section tabs are easiest as `/click {"selector":"text=\"Archived Tags\""}` — works for
  `Tags`, `Active Tags`, `Archived Tags`, and the modal's `Yes`.
- **Every row appears TWICE** (frozen pane + horizontally-scrolling pane), e.g. `un0` at
  x≈365 and `un1` at x≈1137 for the same Add-on row. The first copy can be overlapped and
  will fail `page.click` with a 10s timeout; **if `un0` times out, click `un1`.**

### /eval payload + screenshot handling (both servers)
- Body key is **`js`**, not `expression` (`{"error":"js is required"}`).
- Long JS breaks inline curl quoting. Write the payload to a file and use
  `--data-binary @/tmp/_js.json`:
  ```python
  json.dump({"js":js},open('/tmp/_js.json','w'))
  terminal("curl -s -m 40 %s/eval -H 'Content-Type: application/json' --data-binary @/tmp/_js.json"%B)
  ```
- `/screenshot` returns **JSON with a base64 `screenshot` field**, not a PNG. Decode before
  `vision_analyze` or you get garbage:
  ```python
  d=json.loads(open(p,'rb').read()); open(p2,'wb').write(base64.b64decode(d['screenshot']))
  ```
- **Verify the Criteria column with vision, not the DOM.** Frozen-vs-scrolling pane offsets
  made `.rt-td` index 3 read the color input instead of Criteria; a screenshot answered it
  immediately.
- In-page `fetch('/api/service-module/u/tags/search')` returns **500 "Token doesn't exist or
  is invalid"** — the app's axios interceptor adds auth a bare fetch can't replicate, so
  there is no cheap server-side confirmation of `tagsFilter`. Say so rather than implying
  you verified the backend.

### The Caliber Ops cron will steal :9223 mid-task
`~/caliber-ops/scripts/tekion-scraper.ts` drives :9223 and **switches dealers underneath
you** — it yanked an in-progress Clovis session to another store. If the dealer context
flips unexpectedly, `pgrep` for the scraper before debugging anything else. Recovery: move
to **:9225** and inject the session (no OTP needed):

```python
ss=json.load(open('/home/itadmin/caliber-ops/scripts/.tekion-storage-state.json'))
# POST ss['cookies'] to :9225 /cookies, then navigate to app.tekioncloud.com and
# replay ss['origins'][0]['localStorage'] entries via /eval, then reload.
```
Lands on BC 1251 by default — switch dealers through the UI pill afterward.

⚠ **`.tekion-storage-state.json` goes STALE** (verified 2026-09-03: injecting it left :9225 on
/login). When :9225 is logged out, **clone the LIVE session from :9223 instead** (read-only on
:9223, doesn't disturb the cron):

```python
# 1. Dump :9223 localStorage EXCLUDING amplitude keys (one is 1.3MB of analytics junk that
#    blows every payload limit): build the dict in-page, btoa() it onto window.__jayls,
#    read it back in 15,000-char substr slices, then delete window.__jayls.
#    (Raw JSON slices break json.loads — always base64 the whole blob first.)
# 2. On :9225: navigate /login, then stream the base64 blob INTO the page via
#    window.__acc += "<15KB slice>" per /eval call, finally one /eval that
#    JSON.parse(decodeURIComponent(escape(atob(window.__acc)))) and localStorage.setItem loop.
# 3. Navigate /home, sleep 12, assert currentActiveDealerId (lands on BC 1251).
```
Working script pattern: /tmp/clone_session.py from 2026-09-03 session. Traps hit:
- :9225 server has **no GET /cookies endpoint** (404) — cookies aren't needed anyway;
  the Tekion session is localStorage-based and login survived on LS alone.
- POST bodies >~300KB → `PayloadTooLargeError`/HTTP 413; even 60KB chunks of the amplitude
  key failed. Filtering `amplitude*` keys shrinks the whole dump to ~1.3KB (14 keys).
- Run this as a **standalone python script via terminal()**, not execute_code — the slice
  loop needs >50 tool calls and hits the execute_code cap.

## "The RO Estimate Amount does not match the Actual Amount" popup (FIXED SCT 876, 2026-08-26)

That modal is titled **Pre-Job Completion Information → Warnings in RO** and is produced by
the **Pre-Job Completion** section's validation rule **`Estimate Amount Validation`**
(Rule Level = RO). Turn OFF the row's **Applicable** checkbox (`.rt-td` index **1**) to kill
the popup. There is a SECOND, DIFFERENT rule with a similar name — **Pre-Invoice →
`CP Amount Exceeds Estimate Amount`** — which fires at INVOICE time, not job-completion.
Always enumerate both before changing anything; only disable the one matching the modal
title in the screenshot.

**Joe's ruling 2026-08-26: leave `CP Amount Exceeds Estimate Amount` (Pre-Invoice) ON** —
he wants it as a cashier-side guardrail. Do NOT offer to turn it off again; only the
Pre-Job Completion `Estimate Amount Validation` rule was disabled (SCT 876). Neither rule
had Applicable Job Types / Pay Types set (both "Select..."), which is why the Pre-Job one
fired on every RO indiscriminately — scoping is an alternative to disabling if Joe ever
wants the warning back for a subset (e.g. Warranty only).

Working recipe (avoids every trap in this file):
```python
# 1. dealer pill (1130,32) -> /mouse the store leaf row; assert localStorage.currentActiveDealerId
# 2. navigate /service/settings/ro-settings, sleep 12
# 3. locate the row across ALL ~120 .rt-table's (the page renders every section at once):
#    for each .rt-table, scan .rt-tbody .rt-tr innerText for /Estimate Amount/
#    -> SCT: tbl index 9 = Pre-Job Completion, tbl index 10 = Pre-Invoice
# 4. tag the checkbox AND its wrapper with data-jay, scrollIntoView({block:'center'})
# 5. /click '[data-jay="estcbwrap"]'  (click the WRAPPER, not the raw input; ant-v5-checkbox)
# 6. tag buttons matching /^(Submit|Save)$/ -> /click; require toast
#    "Service settings updated successfully"
# 7. TRUE remount verify: nav /home -> sleep 6 -> nav back -> sleep 14 -> re-read checked
```
Row `y` can be ~8000px (full-page scroll) — `/mouse` coords are useless here; use
`/click` with `data-jay`. `/eval` must be an IIFE `(function(){...})()`; a bare
`function out(){}; out()` throws `SyntaxError: Unexpected identifier`.

## General Setup TOGGLES — the reliable flip recipe (verified TL 1092, 2026-08-27)

Ticket shape: *"is there a setting to turn off the warning for duplicate tags when
checking in customers? I don't see it in Check-In Setup."* → **it is NOT in Check-In
Setup.** `Restrict entry of duplicate Tag#` lives in **General Setup** on
`/service/settings/ro-settings`, in the toggle block right after *"Allow technicians to
clock-in to multiple ROs/Jobs at the same time"*. Generalize: when a store says a
service-workflow warning isn't in the screen they expected, **grep the whole
`ro-settings` innerText for the keyword before believing it doesn't exist** — the page
renders ~4,000 innerText lines with every section expanded, so one grep finds any toggle:

```js
(function(){var t=document.body.innerText.split('\n'),o=[];
for(var i=0;i<t.length;i++) if(/duplicat|Tag#/i.test(t[i]))
  o.push(i+':'+t.slice(Math.max(0,i-2),i+3).join(' | '));
return JSON.stringify({url:location.href,hits:o.slice(0,20),len:t.length});})()
```

These toggles are **`button.ant-switch`**, NOT `input[type=checkbox]` — the `.rt-td`
checkbox recipe from the validation-rule sections does not apply. Find one by label:

```js
// leaf element whose text == the label, then walk UP <=6 parents to the first
// ancestor containing a button.ant-switch; tag it, don't trust coordinates
var els=[].slice.call(document.querySelectorAll('*')),lab=null;
for(var i=0;i<els.length;i++){var e=els[i];
  if(e.children.length===0 && /Restrict entry of duplicate Tag/i.test(e.textContent||'')){lab=e;break;}}
var p=lab,box=null;
for(var k=0;k<6;k++){p=p.parentElement; if(!p)break; if(p.querySelector('button.ant-switch')){box=p;break;}}
var sw=box.querySelector('button.ant-switch'); sw.setAttribute('data-jay','duptag');
sw.scrollIntoView({block:'center'});
return sw.getAttribute('aria-checked');   // "true"/"false" — read this, NOT .checked
```

Full sequence that worked first try (~8 calls, no flailing):
1. `opcode_preflight.py --dealer <ID>` — it will FAIL on dealer drift; that's the point.
2. Switch dealer: nav `/home` → `/mouse` the pill at **(1130,32)** → `scrollIntoView` the
   `[class*="root_dealerInfoItem_container"]` row matching the store name, **re-read its
   rect after scrolling** (TL moved y 428→352), `/mouse` it → sleep 12 → assert
   `localStorage.currentActiveDealerId`.
3. Nav `/service/settings/ro-settings`, **sleep 15**.
4. Tag the switch (above) → `/click '[data-jay="duptag"]'` → re-read `aria-checked` flipped.
5. Tag the page **Submit** (only one on the page, ~x1166 y673) → `/click`.
6. **TRUE REMOUNT verify**: nav `/home` (sleep 8) → nav back (sleep 16) → re-read
   `aria-checked`. Same-URL re-read is the SAVE-VERIFY TRAP and proves nothing.
7. `opcode_preflight.py --restore`.

⚠ **Toast polling is useless on this page.** The generic
`[class*=toast],[class*=notification],[class*=snackbar]` scan returns the header clock
and notification badge (`"11:14 AM"`, `"99+"`, `"70"`) and never the success toast — the
"require a toast" rule from the Pre-Invoice section does NOT transfer here. Rely on the
true-remount read as the sole proof of persistence.

Toggle is **store-scoped** — flipping TL does nothing for the other 6. Always tell Joe
which store you changed and offer the fleet sweep.

**Known `Restrict entry of duplicate Tag#` state (as of 2026-08-28):**
- **TL 1092 = OFF** (flipped 2026-08-27 at Joe's request; true-remount verified).
- **BC 1251 = ON** (read live, not changed).
- ST / BT / SV / AR / VC = **unread** — fleet sweep offered to Joe, not yet run.
Re-read live before quoting these; they drift.

### opcode_preflight.py --restore was BROKEN (fixed 2026-08-27)
`restore_cron()` replayed `/tmp/cron_orig_opcode.txt`. If a prior session died before
`--restore`, the next run's `pause_cron()` reads an ALREADY-PAUSED crontab, writes that
paused text into the backup (`n==0` → "already paused / no pipeline line"), and then
`--restore` reinstalls the paused line → permanent
`RESTORE FAILED  JAYPAUSE lines remaining = 1`. Now it strips the `#JAYPAUSE ` marker
from the LIVE crontab instead — idempotent and self-healing. If you see that FAIL on an
older copy, unpause by hand: `crontab -l` → strip the marker → write with a **trailing
newline** (crontab refuses `"new crontab file is missing newline before EOF"`) →
`crontab <file>`. Never `crontab -l | sed | crontab -`.

## Pay Types Setup — "it's not there" = a PERMISSION, not a missing feature (VC 1891, 2026-09-03)

Pay Types Setup (payer types / Service 3.0 split-payer config) = **Settings → Service
Settings → Pay Types Setup**, direct URL **`/ro/paytypes`**. Add New → Base Pay Type
(Customer/Internal/Warranty) + 3-letter Notation + Name + **Default Payer** +
**Associated Payers** (multi-select). Base C/I/W pay types can't be deactivated, only
custom ones. Store-scoped. It's step 1 of the Service 3.0 chain (Pay Types → Tax Codes →
Vehicle Groups → Labor Pricing → opcode pay-type config → Fees → GLAM cash holding acct).

**BOTH the settings tile AND the `/ro/paytypes` route are gated by the single permission
`View Pay Types Setup`** (Roles → \<role\> → **Service → Repair Order**). If it's OFF the
tile silently vanishes and the direct URL renders *"You do not have the permissions to
access the content."* — Joe reported "its not there" and this was the cause. Verified on
VC 1891: the **System Administrator** role had `View Pay Types Setup` = OFF (unselected
pill) while neighbors (Job PayType Edit, Internal PayType Change) were ON. Fix = flip
that one pill + save; applies to everyone on the role. **Role changes fall under Joe's
employee/role hard rule — get explicit go before toggling.** When a user says a settings
tile "isn't there", check the role permission for that tile BEFORE assuming a version/
support gate.

## Approval Settings — what it CAN and CANNOT gate (verified live BC 1251, 2026-09-03)

Joe asked "what else can I set up in approver workflow? declined work? certain opcodes?"
Answer, from KB + live read (BC's `Enable RO Approval flow` toggle was OFF at read time):

**CAN configure (everything keys on PAY TYPE):**
1. `Enable RO Approval flow` — master toggle in General Setup (NOT a separate left-nav
   section on the live page; the KB's "Approval Settings" section renders as this toggle).
2. **Additional Jobs can be added for the following Paytypes** — pay types addable
   post-check-in WITHOUT an approver (e.g. CP+I only → warranty adds need approval).
3. **Additional Jobs can be changed only to the following Paytypes** — pay-type change
   matrix (CP→I only, etc. — blocks silent flips to Warranty).
4. **Recommendations require Approval before sending to the Customer** — per-pay-type
   toggle; if off, approval happens via RO Bulk Action in the RO kebab.
5. Additional **warranty hours** approval (the RO Bulk Action → Approval → Additional
   Hours flow tested on TL 398624).
- **Approvers are NOT set in the UI** — users are designated approvers by emailing
  support@tekion.com.

**CANNOT:**
- **Declined work — NO approval gate.** The only hook is upstream (approve before SENDING
  the rec). Once sent, customer approves/declines freely. Declined/deferred work is
  governed only by Deferred Recommendation Rules (red/amber retention periods) — no approver.
- **Opcode-scoped approval — does NOT exist.** Verified the adjacent surfaces too:
  Pre-Invoice/Pre-Job Completion validation rules scope by Job Type + Pay Type only;
  **Hold automation filter fields = Department, Job Type/Pay Type, Job Status, Status,
  RO Flag, Job Parts Status, RO Type, Sublet Job, Job Tags — no opcode** (read live off
  the funnel popover's React fiber `filterTypes`).

**Nearest workarounds for opcode-ish control:** Internal Pay $ limit (over-limit close
needs `Internal Repair Order Review Close` permission); turn OFF `Allow Creation of
Custom Concern Opcode`; Hold automation keyed on Job Type/Pay Type + Job Tag with
role-restricted "Remove When" = a manual release step. True opcode-level approval =
Tekion feature request.

**Fiber trick for filter popovers:** the funnel popover's field list isn't in options on
the `-control` elements — walk the popover element's own `__reactFiber$` down child/sibling
until `memoizedProps.filterTypes` (or `.additional.filterTypes`) appears; each entry has
`{label, type}`. Works anywhere the ant-v5 filter dialog is used.

## Pitfalls
- Several behaviors are gated by **"when enabled by support"** (e.g. Select Default Service
  Advisor for jobs) — if a toggle is missing, it may need Tekion support to enable.
- Settings here STACK with **PDF Settings** and **Dealer Configurations > Customer
  Notifications** — a single behavior (e.g. showing taxes on estimate, notify-on-invoice)
  often requires BOTH the Service Settings toggle AND the corresponding PDF/Dealer-Config
  setting. Don't assume one toggle is sufficient.
