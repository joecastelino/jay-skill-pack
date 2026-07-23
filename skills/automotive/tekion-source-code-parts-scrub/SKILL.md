---
name: tekion-source-code-parts-scrub
description: Extract and analyze the FULL part list for a Tekion Source Code (e.g. SCT Source 103 "GENERAL STOCK 2-3") to make stocking recommendations — which parts to activate, BRP/BSL review, negative-on-hand cleanup, mis-coded fast-movers, and capital-tied-up review. Use when Joe asks to "scrub a source code", "review stocking levels per part", "should I activate more parts", "what's mis-coded", or "pull all the parts in source code X".
triggers:
  - scrub source code
  - review source code parts
  - stocking levels per part
  - should I activate more parts
  - pull all parts in a source code
  - source code part list
  - BRP BSL recommendation per part
  - parts inventory analysis for a source code
---

# Tekion Source Code — Full Part-List Scrub & Stocking Recommendations

Pull EVERY part on a Tekion Source Code, then segment into actionable buckets and
make stocking recommendations. Verified on SCT (876) Source 103, 6,014 parts, 2026-06-23.

## When to use
Joe asks to review a whole source code's stocking: activate parts? BRP/BSL levels?
which are mis-coded / negative / tying up capital? This is the source-CODE-wide view,
not a single-part shortage (for that use `tekion-parts-autoorder-diagnosis`).

## Prereqs
- Persistent browser server on :9223, logged in, on the right dealer (verify via dealer selector).
- The Source Code edit page has 4 tabs: Source Code Details · Stocking Parameters · List of Parts · Sales History.

## Step 1 — Navigate to the source code
1. `/navigate` to `/parts/source-codes/list` (wait ~8-13s — the grid is virtualized; all 22
   source-code cells render as leaf elements whose textContent is exactly the code, e.g. "102").
2. **You MUST open the edit page by CLICKING the code cell** — a cold `/navigate` (or even
   pushState) to `/parts/source-codes/edit/<id>` renders ONLY the app shell (empty tabs, no
   download icon). Click via: find the leaf el `e.children.length===0 && /^102$/.test(e.textContent.trim())`,
   `scrollIntoView({block:"center"})`, dispatch mousedown+mouseup+click. After ~7s the edit page
   shows 4 `.ant-tabs-tab`: Source Code Details · Stocking Parameters · List of Parts · Sales History.
3. Read **Stocking Parameters** there, OR (faster) pull all params at once from the settings API
   (see verified-source-codes block below). Click the "List of Parts" tab (`.ant-tabs-tab` whose
   textContent matches) → the `1,579 Result(s)` count + the `.icon-download1` download icon appear.

## Step 2 — Export the full part list (THE reliable method, REWRITTEN 2026-06-24)
The "List of Parts" tab has 1.5k–6k+ rows (virtualized) — DO NOT scrape page-by-page, and
the internal API `POST /api/wms/pricing/u/sourceCode/inventory/parts` CANNOT be replayed
standalone (custom axios-interceptor auth → 500 "Token doesn't exist" for every header
guess). Use the tab's **download button** → server-side xlsx on S3.

### ⛔ THE OLD `curl <signed S3 url>` METHOD IS BROKEN — DO NOT USE IT (verified 2026-06-24)
Tekion now **masks the AWS access key** in the signed URL. Both the success toast AND the
underlying API JSON (`/api/media-v3/u/v2/presignedurls`) render the credential literally as
`X-Amz-Credential=AKIART...Z5S6` — with a real `...` ellipsis in the string. Curling that URL
externally returns `<Error><Code>InvalidAccessKeyId</Code>`. The `window.__blobs` / `<a download>`
href is ALSO masked (the "Download" control is a `<span>`, not an `<a>` — no usable href). The
browser can still download because it resolves the real key internally at the network layer, but
that key is never exposed to JS or an external curl. **So you must download the bytes INSIDE the
browser and ferry them back as base64.** Here is the working flow:

1. Open the source-code edit page (`/parts/source-codes/edit/<mongoid>`), click the
   **"List of Parts"** tab. Confirm via `.ant-tabs-tab` whose className includes `active`.
   The panel shows counts like `1,579 Result(s)` / Positive OH / Negative OH / (OH+Hold)>0 —
   read these as your headline totals.
2. **Hook XHR responses** (the app uses axios = XHR, NOT fetch — a fetch hook catches nothing):
   ```js
   (function(){window.__xhr=[];var oo=XMLHttpRequest.prototype.open,os=XMLHttpRequest.prototype.send;
   XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return oo.apply(this,arguments)};
   XMLHttpRequest.prototype.send=function(){var x=this;this.addEventListener('load',function(){try{
   var u=x.__u||'';if(/presignedurl|media-v3|report\/download/i.test(u))window.__xhr.push({u:u,b:x.responseText||''});
   }catch(e){}});return os.apply(this,arguments)};return 'xhr-hooked'})()
   ```
3. Click `.icon-download1` (the single source-code-level download icon — there is NO separate
   per-tab download; clicking it on ANY tab regenerates the **Part List By Source Code** report).
   Wait ~10s. A toast appears: "Part List By Source Code Report has been generated successfully.
   Download". Then click the **"Download"** `<span>` (find it: a leaf el with
   `children.length===0 && textContent.trim()==='Download'`).
4. The captured `window.__xhr` now holds a `/api/media-v3/.../presignedurls` response whose JSON
   has the (masked) S3 URL. You only need it to drive an **in-browser fetch**. Run this in `/eval`
   (it fetches the file with the page's own creds and base64s it into a global):
   ```js
   (async function(){try{
     var u=(window.__xhr||[]).map(x=>x.b).join('');
     var m=u.match(/https:\/\/com-tekioncloud[^"\\]+\.xlsx[^"\\]*/); if(!m) return 'NO_URL';
     var url=m[0].replace(/\\u002F/g,'/');
     var r=await fetch(url); if(!r.ok) return 'FETCH_'+r.status;
     var b=new Uint8Array(await r.arrayBuffer()),s=''; for(var i=0;i<b.length;i++)s+=String.fromCharCode(b[i]);
     window.__b64=btoa(s); return 'OK_'+b.length;
   }catch(e){return 'ERR_'+e.message}})()
   ```
   Expect `OK_<bytes>` (Source 101 = 107,659 bytes). The fetch SUCCEEDS in-browser even though the
   key looks masked — that's the whole point.
5. **Ferry `window.__b64` out in ≤16,000-char chunks** (the :9223 `/eval` AND `/screenshot`
   endpoints corrupt/truncate any response > ~20,000 chars — a control char appears at char 20000
   and breaks `json.loads`). Get the length first, then slice:
   ```python
   # length: eval  (window.__b64||"").length   -> e.g. 143548
   # loop i in range(0,total,16000): eval  (window.__b64||"").slice(i,i+16000)
   # use json_parse (lenient) not json.loads; "".join the chunks; base64.b64decode; write .xlsx
   ```
   Reassemble, `base64.b64decode`, write the `.xlsx`. Verify with `file` → "Microsoft Excel 2007+".
   (`/eval` payloads are easiest passed via `-d @/tmp/payload.json` to avoid shell-quoting hell;
   `/eval` wants `{"js":"<expression>"}` — an EXPRESSION, a bare `return` throws "Illegal return".)

## Step 3 — Parse the xlsx (CRITICAL: inline strings, not sharedStrings)
The export uses `t="inlineStr"` cells with `<is><t>` — `sharedStrings.xml` is EMPTY
(count 0). openpyxl `read_only` returns only 1 row (bad dimension tag), and full load
can time out. Parse the XML directly with iterparse:
```python
import zipfile, xml.etree.ElementTree as ET
NS="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
z=zipfile.ZipFile("part-list.xlsx")
rows=[]
for ev,el in ET.iterparse(z.open("xl/worksheets/sheet1.xml")):
    if el.tag==NS+"row":
        cells=[]
        for c in el.findall(NS+"c"):
            t=c.get("t")
            if t=="inlineStr":
                isn=c.find(NS+"is"); tn=isn.find(NS+"t") if isn is not None else None
                cells.append(tn.text if tn is not None and tn.text else "")
            else:
                v=c.find(NS+"v"); cells.append(v.text if v is not None else "")
        rows.append(cells); el.clear()
```
Columns: PART NUMBER, PART DESCRIPTION, GROUP, Manufacturer, Bins, ON HAND QTY,
ON HOLD QTY, TOTAL QTY, PART COST, CORE PRICE, PART LIST PRICE, TOTAL PART COST,
TOTAL EXTENDED COST. **No sales-velocity column** — see caveat in Step 5.

## Step 4 — Segment into actionable buckets

### FIRST: is this a FAST band or a SLOW band? The interpretation flips.
The source-code NAME tells you the demand tier and changes what's "good" vs "bad":
- **SLOW band** (e.g. 103 "GENERAL STOCK 2-3" = sells 2-3 pieces): carrying ZERO stock on
  most parts is CORRECT and expected. The action items are activation candidates,
  mis-coded fast-movers stuck here, and capital tied up in slow high-$ parts.
- **FAST band** (e.g. 101 "GENERAL STOCK 15-999" = sells 15+): carrying positive on-hand is
  EXPECTED and healthy (101 had 91% positive OH — that's good, not a problem). For a fast
  band the signals shift to: negative-OH on CORE service items (e.g. spark plugs went -11 —
  high-velocity parts billed off ROs faster than received), OVERSTOCK (e.g. a single accessory
  at 443 units — flag as possible runaway stock/bulk buy), big HOLD pile-ups on a negative
  part (backorder), and high-$ fast parts sitting at zero on-hand (a skipped reorder).
  Do NOT flag "most parts carry stock" as a problem on a fast band — that's the point of it.

Verified source codes (SCT 876), LIVE params from `GET /api/parts/proxy/u/settings/source-code`
(returns ALL 22 active source codes w/ stockingParam.bestReorderPoint/bestStockingLevel,
demandCalcCriteria.monitoringDuration, phaseInCriteria.totalDemands — read it directly instead of
clicking each Stocking Parameters tab): 101 = ID 630e11860c76920008ed4416, "GENERAL STOCK 15-999",
BRP17/BSL21. As of 2026-06-24 Joe set it to **6mo monitor, phase-in 5/12mo** — but it was
PREVIOUSLY **9mo / phase-in 3** (do NOT assume the current value was the prior value; always
confirm the BEFORE state with Joe before modeling a change). Trust the live settings API for
CURRENT values. 102 = ID 630e11870c76920008ed4423, "GENERAL STOCK
4-14", BRP47/BSL50, 9mo, phase-in 3/12mo, 5,009 parts. 103 = ID 630e11850c76920008ed4411,
"GENERAL STOCK 2-3", BRP80/BSL85, 9mo, phase-in 3/12mo, ~6,011 parts. (Others: 100=17/19,
104=29/30, 105 ACCESSORIES=36/37, 50 SIGHTLINE WIPERS=40/45, 10 BATTERIES=1/2, 2 filters=15/20.)

### Buckets (compute and rank — same code works for both bands; interpret per tier above):
- **Negative on-hand** (oh<0): inventory-accuracy problem (the in-and-out / negative-OH
  backfill trap — see tekion-parts-autoorder-diagnosis). Sum extended cost = $ distortion.
- **Negative OH WITH active Hold** (oh<0 AND hold>0): URGENT — being sold short on a live
  ticket right now.
- **High on-hand (oh>=10)** in a slow "2-3" band: MIS-CODED fast movers — belong in a
  faster source (e.g. coolant/fluids → Oil & Chemicals source). The classic tell: a fluid
  or common fastener with 20-77 units in a slow-mover band.
- **Expensive (cost>=$500, oh>=1)**: high-$ collision/hybrid parts (reman trans, HV
  batteries, panels) tying up capital in a slow band → review stock vs special-order.
- **Hold>0 but oh<=0**: ACTIVATION candidates — live demand, no stock. Set Min Qty 1 if recurring.
- **oh==0 AND hold==0** (the bulk): correctly dormant (paint codes, fasteners, special-order
  bin = SP-ORD). Do NOT recommend stocking these — that's the whole point of a slow band.

## Step 5 — BRP/BSL recommendation caveat (be honest with Joe)
The source-code export does NOT carry per-part 9-month sales velocity, so you CANNOT
compute exact piece-level BRP/BSL targets from it alone — that lives on each part's
**Monthly Data** page. For exact per-part reorder qty, pull velocity on the top ~50-100
movers (or just the neg-OH + high-impact subset). State this limitation; offer to pull
velocity on the movers if Joe wants exact piece counts. Do NOT fabricate per-part qty.

### Pulling per-part velocity — BULK SALE-HISTORY API (verified 2026-06-24, the FAST way)
**This REPLACES the old vision-scrape method.** The Monthly Data grid is canvas/virtualized
(not in innerText, not DOM-readable) — but the data behind it comes from a clean JSON API you
can replay for EVERY part. 12,599 parts in ~4 minutes, zero errors (vs ~11 hrs by vision).

**Endpoint:** `POST /api/wms/parts/u/inventory/utility/salehistory/groupByMonth`
**Body:** `{"partId":"M_TMNA_<PARTNUM>"}`  ← inventoryId is IGNORED (empty/null give identical data; do NOT bother looking it up)
**Returns:** `{data:[{year, month:"<MonthName>", saleQty}]}` = full monthly sold-qty history.

**Auth:** a bare in-page `fetch` gets 500 "Token doesn't exist" — the app injects custom headers
via its axios interceptor. CAPTURE them once: hook `setRequestHeader` on a real salehistory XHR
(drive the SPA into any part's `/monthlyData` via history.pushState+PopStateEvent so the hook
survives — a full reload wipes it; React-Query caches monthlyData so use a FRESH partId each time).
The header set is: `tekion-api-token, roleId, userId, tenantname, dealerId, tek-siteId,
original-userid, original-tenantid, clientId, locale, program, applicationId, subApplicationId,
productIds` + Accept/Content-Type. Stash them: `window.__H = <captured headers>`.

**Harvest at scale** — define an in-page concurrent worker, then loop batches from Python:
```js
window.__harv = async function(pids, conc){ conc=conc||10; const H=window.__H, out={}; let idx=0;
  const M={January:0,February:1,March:2,April:3,May:4,June:5,July:6,August:7,September:8,October:9,November:10,December:11};
  async function w(){ while(idx<pids.length){ const i=idx++,pid=pids[i];
    try{ const r=await fetch("/api/wms/parts/u/inventory/utility/salehistory/groupByMonth",
      {method:"POST",headers:H,credentials:"include",body:JSON.stringify({partId:pid})});
      out[pid]= r.status===200 ? (await r.json()).data.map(d=>[d.year,M[d.month],d.saleQty]) : {err:r.status};
    }catch(e){ out[pid]={err:String(e.message)} } } }
  const ws=[]; for(let k=0;k<conc;k++) ws.push(w()); await Promise.all(ws); return JSON.stringify(out); };
```
Python: loop `pids` in chunks of ~200, `POST /eval {"js":"window.__harv(<batch-json>, 10)"}`, parse
with `json.loads(json.loads(raw)["result"])`, accumulate into `velocity.json`. The captured token
held a full 12.6k-part run (~4 min); if a batch returns mostly `{err:500}` the token expired —
re-capture `window.__H` from a fresh monthlyData visit and resume (skip pids already collected).

### Live ON-ORDER qty (needed for true reorder = BSL_qty − (OH + onOrder))
**Endpoint:** `POST /api/partTrade/u/purchase/parts/liveOnOrderQty`, body = a **bare ARRAY** of
partIds (NOT `{partIds:[...]}` — that 400s). Returns `{data:[{partId, quantity}]}`. Batch ~100
partIds/call; all 12.6k in ~30s. Same `window.__H` headers.

### Reorder math (full Tekion logic, validated 2026-06-24)
Per part: `units = Σ saleQty over the source's monitor window` (use last N COMPLETE months —
skip the current partial month). `day_supply = units/(monitor_months*30)`. `BRP_qty =
day_supply*BRP_days`, `BSL_qty = day_supply*BSL_days`. A part orders only if it's **phased in**
(total demands over last 12 complete months ≥ source phase-in threshold) AND
`(OH+onOrder) ≤ round(BRP_qty)`; **order qty = round(BSL_qty) − (OH+onOrder)**. Apply the three
rounding modes (floor / round-half-up / ceil) to answer "what does flipping BSL Rounding cost?".

KEY RESULT (SCT 101/102/103, 2026-06-24): combined order Round-Down $52.8K → Round-Nearest $311K
→ Round-Up $436K. The balloon is the SLOW bands (102 "$26K→$137K", 103 "$5K→$139K") — ~2,600
slow-tail parts whose BSL qty <1.0 bumped 0→1. Fast band 101 barely moves ($22K→$35K). Fast-movers
are rounding-IMMUNE. CONCLUSION: leave fleet-wide rounding on Round-Down; fix real shortages
(parts selling NEGATIVE on-hand on live tickets — 45 across the three) surgically with Min Qty +
neg-OH cleanup. The two problems are SEPARABLE.

### Run the demand math to validate (don't eyeball)
Use the most-recent COMPLETE `monitor` months (skip the current partial month):
`day_supply = total_units / (months*30)`, `BSL_qty = day_supply * BSL_days`, then
floor / round / ceil for Round-Down / Round-to-Nearest / Round-Up. KEY RESULT (Source 101
spark plug 90080-91180, 2026-06-24): 415 units/9mo → 1.54/day → BSL = 32.3 → all three
rounding modes give 32. **CONCLUSION: rounding only moves parts whose BSL qty < ~1.0 (the
slow tail); genuine fast-movers are rounding-IMMUNE.** This is the answer to "won't Round-to-
Nearest balloon the order to $200K?" — the balloon is the slow tail bumped 0→1, NOT the fast-
movers, so the two problems are SEPARABLE (fix fast-movers with Min Qty + negative cleanup;
leave fleet-wide rounding alone). See tekion-parts-autoorder-diagnosis for the full math/levers.

Source-code-level BRP/BSL (e.g. 80/85 days slow, 17/21 fast) is usually reasonable — do NOT
change blindly. To shrink a stock order WITHOUT the fleet-wide rounding flip: lower the monitor
window (9→6, weights recent demand), tighten phase-in (3→5 sales/12mo, drops the dead tail), or
set part-level Min Qty on known movers (a floor UNDER source logic — doesn't inflate the rest).

### MODEL SETTINGS IMPACT OUTSIDE TEKION (Joe's stated preference 2026-06-24)
When Joe changes source-code settings and asks "what does it look like / let's see", he wants the
impact MODELED OFFLINE from the harvested velocity data — NOT Tekion's live Stock Order Preview.
Quote: "I'd rather run it outside of Tekion and have you give me a report." So: re-run the reorder
math (day_supply→BRP_qty/BSL_qty→order qty×cost) under OLD vs NEW params from the cached
parts.json/velocity.json/onorder.json, produce a before/after table by source + rounding mode, and
hand it to Stacey to email. Never run the live preview unless he explicitly asks for it.

### COUNTERINTUITIVE: shortening the MONITOR window RAISES the order under Round-Down
Verified by modeling SCT 101/102/103 when Joe moved 102/103 from 9mo→6mo (2026-06-24):
combined Round-Down order went $52.7K → $91.6K (**+$39K, +74%**) — it went UP, not down.
MECHANISM: `day_supply = units / (monitor_months × 30)`. Recent sales are weighted toward the
last few months, so the last 6mo holds MORE than 6/9 of the 9mo total; dividing by a smaller
denominator (180 vs 270 days) RAISES day_supply → raises BSL_qty. On a SLOW band under Round-Down,
hundreds of tail parts that floored to 0 at 9mo now floor to 1+ at 6mo and get pulled onto the
order (SCT: 705 parts crossed 0→1 in source 102, 308 in 103; fast band 101 was already 6mo = $0
change). This is REAL recent demand surfacing, not waste — but warn Joe the order grows. KEY
distinction for the customer (Glade): the monitor-window change (+$39K) is SEPARATE from and far
smaller than the rounding-flip balloon (Round-to-Nearest $251-311K, Round-Up $436-457K). Keep
rounding on Round-Down and the order stays ~$92K. To CAP the monitor-window increase, tighten
phase-in on the slow bands or set part-level Min Qty — do NOT touch rounding. So a shorter window
SHARPENS demand signal (good) but is NOT a tool to shrink the order — for that, use phase-in.

### TUNING RULE — monitor window vs phase-in (verified by velocity modeling 2026-06-24)
Two levers behave very differently; do NOT change them in lockstep across bands:
- **Monitor window** (e.g. 9mo→6mo): SAFE to shorten on EVERY band. Sharpens recency, no part
  is disqualified — just reweights demand toward recent months. Recommend 6mo fleet-wide.
- **Phase-in threshold** (sales/12mo a part needs to qualify for auto-order): MUST SCALE TO THE
  BAND'S VELOCITY. Raising it culls the dead tail on a FAST band but STRANGLES a slow band.
  Model the band's demand distribution BEFORE recommending a phase-in change:
  - 101 (fast, 15-999): phase-in 5 fits — only true movers qualify, dead tail dropped cleanly.
  - 102 (4-14): phase-in 3→5 would cull ~1,411 parts (the entire 3-4/yr tier; order $26K→$37K).
    KEEP at 3. Dist: ~28% sell 3-4/yr, ~50% sell 5-9/yr, ~19% sell 10+/yr.
  - 103 (slow, 2-3): phase-in 3→5 disqualifies ~1,912 of 1,997 active parts = effectively turns
    the source OFF ($4.7K→$545). KEEP at 3. Dist: ~65% sell 1-2/yr, ~32% sell 3-4/yr, ~0% sell 5+.
  Bottom line: a phase-in of 5 on a "2-3" band asks parts to sell ABOVE the band's own definition —
  self-defeating. Match phase-in to the band name's piece count, never copy a fast band's setting down.

### LEVER DECOMPOSITION + RECONCILE AGAINST THE CUSTOMER'S NUMBER (verified 2026-06-24)
When you model a multi-lever change (e.g. 101 went 9mo/phase-3 → 6mo/phase-5), DECOMPOSE which
lever moved the dollars — hold each constant and flip the other:
  - 9mo/ph3 → 6mo/ph3 (window only):   the window delta
  - 9mo/ph3 → 9mo/ph5 (phase-in only): the phase-in delta
SCT 101 result: +$1,573 total, ALL from the window; phase-in 3→5 added $0 (every selling 101 part
already clears 5/yr, so tightening phase-in dropped nothing). This tells Joe exactly which knob did what.
RECONCILE vs the customer's figure: Glade independently calculated ~$6,500 for 101 vs my +$1,573.
When your number ≠ theirs, do NOT just restate yours — run the SAME change under all three rounding
modes and show where their number lands. Glade's $6,500 sat BETWEEN my Round-Down (+$1,573) and
Round-to-Nearest (+$14,519), which means he's using a different rounding rule OR counting demand
EVENTS (RO count) rather than piece QUANTITY. The real deliverable is identifying the DEFINITION
difference (rounding mode / demand basis / baseline), not winning on the number. Flag it for them to
reconcile in the meeting.

### DEMAND-RECURRENCE TIERS — flag one-time collision parts to EXCLUDE (verified 2026-06-24)
Joe thinks in demand-recurrence tiers and will ask to "flag the one-time collision jobs so I don't
order them." For each part the order pulls in, count the number of DISTINCT MONTHS it sold in over
the last 12 complete months (from velocity.json), not just total qty:
  - **ONE-TIME** (sold in ≤1 month/12, ≤2 pieces): a single collision job, won't repeat → candidate to skip.
  - **SPORADIC** (2-3 months/12): intermittent but REAL demand (a FRAME ASSY or BLOCK ASSY that sold
    in 2-3 separate months IS recurring collision demand) → KEEP on the order.
  - **RECURRING** (4+ months/12): steady demand → KEEP.
The surgical "DON'T ORDER" list = ONE-TIME **AND** collision/high-cost (desc matches FRAME/PANEL/
BLOCK/DOOR/FENDER/QUARTER/HOOD/BUMPER/HEADLAMP/RADIATOR/WHEEL/SENSOR/MOULDING/CLIP… or unit cost
≥$150). SCT result: 38 parts / $3,391 — pull those, order drops ~$3.4K with zero stockout risk.
PITFALL: do NOT define one-time as "single spike" too loosely — many collision parts sell across
2-3 months and are genuinely recurring; tiering by distinct-months-sold (not total qty) avoids
killing real intermittent demand. Deliver as a multi-tab xlsx: "FLAG-Do Not Order" + one tab per tier.

### DECIMAL-BSL "ROUNDING CROSSER" REPORT (Joe asked for this exact view 2026-06-24)
When Joe asks for the order change "by part number" and references a decimal (e.g. "the brake pad
went from .85, round to now 1.4"), he wants the RAW pre-rounding BSL quantity at OLD vs NEW params,
NOT the rounded order qty. Show, per part: OLD units / OLD BSL_qty (2 decimals) / OLD order, then
NEW units / NEW BSL_qty (2 decimals) / NEW order. The headline subset is the **ROUNDING CROSSERS**:
parts where `floor(BSL_old)==0 AND floor(BSL_new)>=1` — these were NOT ordering (BSL rounded to 0)
and now order 1. That set IS the entire order increase. SCT 9mo→6mo: 1,081 crossers (101:68 /
102:705 / 103:308). Real examples that matched Joe's case exactly: PAD KIT DISC BRAKE 0.93→1.05,
PAD RR BUMPER 0.93→1.40. PITFALL: do NOT conflate "ordered at 6mo but not 9mo" with "rounding
crosser" — a part can newly order for OTHER reasons (was over-stocked at 9mo, or phase-in changed).
A TRUE rounding crosser is specifically `floor(BSL_old)==0 and floor(BSL_new)>=1`; filter on that.
Deliver as xlsx: tab 1 = the crossers (sorted by source then biggest BSL jump), tab 2 = ALL parts
with decimal BSL at both windows so Joe can audit any line. Explain how to read it: BSL_qty is
un-rounded; floor it (Round-Down) to get the order; 0→1 = newly orders one × unit cost.

### SOURCE-CODE MOVE AUDIT — who moved which parts between source codes (verified 2026-06-24)
Use when Joe asks "what did <person> change today / what parts did they move to source <X>"
(e.g. Glade moving parts to Source 9 "PARTS OFF STOCK ORDER", the non-stocking bucket). Tekion's
source-code export gives the CURRENT state, NOT a per-edit audit trail with timestamps — so you
produce the change list by DIFFING a frozen "before" baseline against the live source list.
PROCEDURE:
1. **Freeze a baseline IMMEDIATELY** when the request comes in (or use an existing earlier export):
   copy the current parts.json to `baseline_<date>_<time>.json` and build a `{part_number:
   source_code}` map. The baseline is read-only — never let the 2 AM/other jobs overwrite it.
2. **Get Source 9's mongo ID** from `GET /api/parts/proxy/u/settings/source-code` (returns all 22
   codes w/ id+description). SCT Source 9 = `630e11860c76920008ed4418` "PARTS OFF STOCK ORDER".
3. **At report time, export the CURRENT full part list for the target source** (Step 2 download
   method) and parse part numbers.
4. **DIFF:** for every part now in Source 9, look it up in the baseline `{pn:src}` map. If it was
   in 101/102/103 in the baseline and is now in 9 → that's a MOVE. Cross-reference desc/cost/OH
   from baseline_meta. Report: Part#, Original Source, New Source (9), Cost, On-Hand, plus total
   on-hand $ value taken off stock order (Σ cost×OH). Summary tab: counts by origin source.
**CRITICAL BASELINE LESSON (cost a correction this session):** a baseline frozen AFTER the person
already started moving parts will MISS their early moves — those parts are already gone from
101/102/103 in your "before" snapshot. Always ask whether they'd already started; if so, build a
HISTORICAL baseline = the UNION of every earlier full export you have (e.g. yesterday's source-103
export + today's 9 AM velocity snapshot + today's source-101 export) → `{pn: original_source}` for
EVERY part ever seen in the candidate sources. Diff Source 9 against THAT union to catch both early
and late moves. SCT example: the June 23 source-103 export had 16 parts already gone by the 9 AM
June 24 snapshot — those were Glade's early moves that a 9 AM-only baseline would have missed.
Quick live headline (no full diff): click into the target source's "List of Parts" tab and read
the "N Result(s)" count (SCT Source 9 = 1,810 parts at the time). To SCHEDULE the audit for later
(person still mid-edit), use a one-shot cron job with this skill attached + a self-contained prompt
pointing at the frozen baseline files (all under /home/itadmin/sct-sourcecodes-velocity/); the job
must re-capture window.__H itself since a navigate wipes it.
SCOPE WARNING (Joe corrected this twice 2026-06-25): he wants ONLY the INTERSECTION — parts that
left 101/102/103 AND are now in 9 — NOT a full dump of Source 9. Exclude every Source-9 part that
never originated from the candidate bands. Title the report accordingly ("parts that left
101/102/103 for 9"), not "Source 9 audit."
**"DO NOT STOCK" SCORECARD page (Joe asked 2026-06-25):** alongside the move list, add a separate
tab that cross-references the 38-part surgical "do not order" flag list (from the demand-recurrence
tiers above — one-time collision/high-cost) against what actually landed in Source 9, split into:
(a) FLAGGED AND in Source 9 = the person acted on the recommendation (matched), and (b) FLAGGED
but NOT in Source 9 = a flagged "don't stock" part still on stock order. This scores how closely
their manual moves matched Jay's recommendation. Confirm WHICH list to use (the 38-part surgical
list vs the full 234-part one-time list) — Joe's default is the 38-part surgical list since that's
the actual "do not stock" recommendation delivered.

### Two ACTION buckets when delivering a per-part stock-order review (tight criteria)
After computing reorder, the two surgical recommendation lists Joe wants (keep them NARROW — a
slow band legitimately has thousands of low-sellers, so broad buckets = noise he'll reject):
- **REACTIVATE**: part MEETS the band's phase-in demand bar (qualifies to be ordered) BUT the
  system isn't ordering it — zero/negative stock AND nothing on order (likely flagged Non-Stock /
  Manual / Special-Order). These are demonstrated movers the source is silently skipping.
- **MANUAL-BUMP**: a phased-IN mover that went NEGATIVE on-hand (shelf too shallow for its
  velocity). Set a part-level Min Qty floor so it rebuilds past the negative-backfill trap (see
  tekion-parts-autoorder-diagnosis). SCT result 2026-06-24: Reactivate 520 parts (101:13/102:312/
  103:195), Manual-Bump 135 (101:24/102:68/103:43).
The ground-truth $ for any scenario is Tekion's own **Stock Order PREVIEW** (generates a reviewable
DRAFT, nothing committed) — offer to run it if Joe wants a hard number before changing settings.

## Step 6 — Deliver via Stacey
Build a clean multi-sheet xlsx (Summary + one tab per bucket) and a plain-English body,
drop both in the project dir, then hand to Stacey to email Joe (she owns the send +
signature). See memory: Jay drops artifacts, Stacey sends. Call:
`~/bin/ask-agent stacey "...send to Joe, body=<file>, attach=<xlsx>, confirm once sent"`

## Pitfalls
- **The signed S3 URL is key-MASKED — never curl it externally** (`InvalidAccessKeyId`). Fetch
  the bytes INSIDE the browser and base64 them out (Step 2). This is the #1 gotcha — the old
  "curl the href" instruction was wrong as of 2026-06-24.
- **:9223 `/eval` and `/screenshot` corrupt responses > ~20,000 chars** — ferry base64 in ≤16k
  chunks and parse with lenient `json_parse`, not `json.loads`.
- **The "Download" control is a `<span>`, not an `<a>`** — no href to grab; you must click it AND
  use the in-browser fetch. The app uses XHR (axios), so hook XHR not fetch to catch the presign.
- **Monthly Data velocity grid is canvas/virtualized** — not in innerText, not XHR-capturable; read
  it with `/screenshot` + `vision_analyze` (NOT `browser_vision`), and wait ~12-15s for it to render.
- xlsx is inlineStr — openpyxl read_only gives 1 row; parse XML directly (Step 3).
- Internal sourceCode/inventory/parts API is NOT replayable (custom auth) — use the export.
- Don't recommend stocking the dormant bulk — a slow band is supposed to carry zero on most.
- Don't invent per-part BRP/BSL qty without velocity; flag the data gap instead.
- `$` in shell `-c` python breaks — write the analysis to a .py file and run it. Also money format:
  use `"${:,.0f}".format(x)`, NOT `"$%,.0f" % x` (the `%,` form raises ValueError).
- mkdir the project dir at the REAL path `/home/itadmin/sct-source<NN>/` — `~/...` resolves to the
  ephemeral profile home and is wiped on daily reset (cost a failed download this session).
- Hand to Stacey via the full path `/home/itadmin/.hermes/profiles/jay/home/bin/ask-agent stacey "..."`
  (the bare `~/bin/ask-agent` may not be on PATH); pass body=<file> + attach=<xlsx>, ask her to confirm.
