---
name: tekion-ro-job-paytype-triage
description: Triage a bare "RO <number> job <N> needs to be <pay type>" ticket (or any bare-RO# request) from Joe. Covers the CRITICAL cross-store RO#-collision trap (RO numbers are NOT unique across the 7 AMG stores), the zero-quota OpenAPI symptom-verification pass that runs BEFORE any browser work, and where the pay-type change actually happens. Use for any ticket that names an RO number without naming a store.
triggers:
  - RO needs to be warranty not internal
  - change pay type on a job
  - bare RO number ticket
  - which store is this RO at
---

# Tekion: "RO NNNNNN job N needs to be <pay type>" — triage

Joe fires these one-liners with **no store named**. Do NOT assume a store, and do
NOT open a browser first. The whole locate + verify pass is free over the OpenAPI
and takes ~10 seconds.

## ⚠️ RULE 0 — RO NUMBERS ARE NOT UNIQUE ACROSS THE 7 STORES

Verified live 2026-08-24: **RO 398422 existed at BOTH Stevens Creek Toyota (876)
and Toyota of Lancaster (1092)** — SCT's was a CLOSED 2023 internal PDI, TL's was
an open warranty transaxle job from that morning. Each store has its own RO
number sequence, so collisions are routine, not exotic.

**ALWAYS sweep all 7 dealers before you touch anything.** Picking the first store
that returns a hit will eventually have you editing a stranger's closed RO at the
wrong store.

Disambiguate hits by `status` + `creationTime` — a CLOSED RO from years ago is
almost never what Joe is looking at. But if BOTH hits are plausible, **ask**.

## Step 1 — Sweep all 7 stores for the RO number (zero browser, ~2s)

```python
import sys, json, urllib.request, urllib.error
sys.path.insert(0,"/home/itadmin/tekion-api")
from tekion_client import load_config, get_token
cfg=load_config(); tok=get_token(cfg)
BASE=cfg["base_url"]+"/openapi/v4.0.0"

def post(path, dealer, body):
    req=urllib.request.Request(BASE+path, data=json.dumps(body).encode(),
        headers={"Authorization":f"Bearer {tok}","app_id":cfg["app_id"],
                 "dealer_id":dealer,"Content-Type":"application/json"})
    try: return json.loads(urllib.request.urlopen(req,timeout=40).read())
    except urllib.error.HTTPError as e: return {"err":e.code,"body":e.read().decode()[:200]}

RO="398422"
for k,d in cfg["dealers"].items():                       # ar bc bt st sv tl vc
    out=post("/repair-orders:search", d,
        {"filters":[{"field":"documentNumber","operator":"IN","values":[RO]}],"pageSize":5})
    for r in ((out.get("data") or {}).get("results") or []):
        print(k, d, r["documentNumber"], r["status"], r["documentId"], r["creationTime"])
```

Remember: filter key is **`filters`** (a LIST) with **`operator`**, and the field is
**`documentNumber`** — `roNumber` returns 0 rows. (See `tekion-openapi-repair-orders`
for the full payload-shape trap.)

## Step 2 — Read job-level pay types from the API (STILL no browser)

```python
D=cfg["dealers"]["tl"]; rid="<documentId from step 1>"
def get(path):
    req=urllib.request.Request(BASE+path, headers={"Authorization":f"Bearer {tok}",
        "app_id":cfg["app_id"],"dealer_id":D,"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=40).read())

jobs=(get(f"/repair-orders/{rid}/jobs").get("data") or {}).get("jobs") or []
for jb in jobs:
    print(jb["jobNumber"], jb["payType"], jb["status"],
          (jb.get("concern") or {}).get("text","")[:60])
```

`jobNumber` is a **string** ("1","2",...) and matches the numbered job list Joe sees
in the UI, so "job 1" maps cleanly. `payType` ∈ CUSTOMER_PAY / WARRANTY / INTERNAL.
Also free on the job record: `status`, `concern.text`, `causes[]`, `hold`,
`createdByUserId`, `modifiedByUserId`.

## Step 3 — STEP-ZERO RULE: does the symptom even reproduce?

Same discipline Joe hammered on the menu-price tickets (pull a clean quote FIRST):
**confirm the wrong value is actually there before doing any repair work.**

On the 2026-08-24 ticket, job 1 at TL was **already WARRANTY** — checked twice, ten
minutes apart. There was nothing to fix. Had I skipped this and gone straight to
the browser, I'd have burned 20 minutes driving a dealer switch and an RO page to
"correct" a field that was already correct — or worse, flipped the wrong job.

If the symptom does NOT reproduce, **stop and report back with the full job table**
and ask which store/job he means. Do not "fix" something to make the ticket true.

## Step 4 — Only then, make the change (browser)

There is **no OpenAPI write path** for pay type — it's a job-form radio in the RO
detail page. Mechanics (Pay Type radios CP/W/I, the Confirm PayType Change modal,
the "Remove Returned parts to proceed" gate, and the Internal-needs-a-Cost-Center
requirement) are documented in **`tekion-ro-void-job-remove-parts`** → *"Alternative
to voiding: flip the whole job to INTERNAL"*. Same radios, any direction.

RO detail URL: `/ro/repair-orders/<documentId>/jobs/<jobId>`

### Ask before flipping when ANY of these are true
- The job is **Completed / Closed** — re-pricing against a different rate is a real
  financial change, not a clerical one.
- The RO is on **Hold** or has multiple payers / splits ("2 Payers" chip).
- Target is **INTERNAL** — internal jobs require a Cost Center, which is a GL
  decision. Joe picks it, not you.
- Changing to/from WARRANTY where a labor rate differs (TL warranty rate was
  $236.63/hr) — the job total will move.

Per Joe's NEVER-GUESS rule, state the pre-change baseline and get an explicit go.

## Gotchas hit on 2026-08-24

- **`:9223` was parked on `tekion.service-now.com` (the KB SPA)** and every
  `/navigate` to `app.tekioncloud.com` landed back on the ServiceNow index — the
  KB session had taken over the tab. `/url` reported the KB URL while
  `localStorage.currentActiveDealerId` still read a Tekion dealer, which is
  confusing. Fix: use the **`:9225`** instance instead (it was clean and
  authenticated), or restart :9223. Don't fight the hijacked tab.
- **Dealer popover: TL and VC are below the fold.** Clicking a y-coordinate read
  from an earlier snapshot silently fails — `currentActiveDealerId` just doesn't
  change. Working sequence:
  ```js
  const rows=[...document.querySelectorAll('[class*="root_dealerInfoItem_container"]')]
              .filter(x=>x.offsetParent!==null);
  const tl=rows.find(e=>e.innerText.includes('Toyota of Lancaster'));
  tl.scrollIntoView({block:'center'});
  const r=tl.getBoundingClientRect();      // RE-READ after scrolling
  ```
  then `/mouse` the fresh center, sleep ~9s, and **verify
  `localStorage.currentActiveDealerId` flipped** before trusting anything on screen.
- **The RO detail page renders slowly and `/eval` can return the PREVIOUS page's
  DOM.** A read came back as 586 chars of the old `/vi/visettings` page after a
  successful navigate. Poll until it settles instead of a single sleep:
  ```python
  for i in range(8):
      time.sleep(4)
      print(api("/eval","POST",{"js":"JSON.stringify({u:location.href,l:document.body.innerText.length})"}))
  ```
  A loaded RO page is ~1,900+ chars and contains `RO# - <number>`. Anything under
  ~700 chars means it hasn't rendered — do not conclude "the page is blank."
- Remove Pendo overlays after every hard nav:
  `document.querySelectorAll('[id*="pendo"],[class*="pendo"]').forEach(e=>e.remove())`

## Report format Joe wants back

A compact per-job table (job #, opcode/concern, pay type, status, $), the store and
dealer id you found it at, and — if there were multiple hits — both, so he can pick.
Flag explicitly whether the symptom reproduced.

## Cross-refs
- `tekion-openapi-repair-orders` — search payload shape, cents rule, job/op endpoints
- `tekion-ro-void-job-remove-parts` — the actual pay-type radio + Confirm modal mechanics
- `tekion-ro-close-blocked-triage` — when the real problem is "can't close", not pay type
- `persistent-browser-server` — :9223/:9225 lanes, dealer switch, injection
