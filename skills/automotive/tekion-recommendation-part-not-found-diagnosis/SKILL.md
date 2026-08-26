---
name: tekion-recommendation-part-not-found-diagnosis
description: Diagnose "Parts can only hit Create for the part number when we have N in stock" / "the part won't populate on a recommendation" in Tekion. Root-causes the empty part line on an MPI recommendation or estimate back to a free-text placeholder part on the opcode plus the OEM-description search trap. Verified TL (dealer 1092) RO 398792 cabin filter, 2026-08-26.
triggers:
  - can only hit create the part number
  - part won't populate on recommendation
  - parts can't find the part but we have stock
  - recommendation part line empty
  - create part instead of selecting
---

# Tekion — "Parts can only hit Create" on a recommendation / estimate

## The complaint (how Joe phrases it)
"RO <n> the cabin filter in recommendations: when parts goes to fill the parts price,
they can only hit **Create** the part number, when we actually have **515** of them in
stock." Store people read this as a Tekion bug or an inventory bug. It is almost always
**two independent config/data problems stacked**. Diagnose BOTH before answering — and
per the never-guess rule, prove each with an API read, not a screenshot.

## Answer shape (what actually explains it)
1. **The opcode's default part is a free-text placeholder** (created by typing a name and
   clicking `Create "<text>"`), so it has `partId: null, partNumber: null` — nothing links
   to inventory. Every recommendation/estimate line from that opcode arrives EMPTY.
2. **Searching the service word returns nothing** because Toyota (and most OEMs) describe
   the part differently — e.g. every 87139-* cabin filter at TL is described
   **"ELEMENT, AIR REFINER"**, the word "cabin" appears in only 2 of 35 records. Parts
   types "cabin filter", gets an empty dropdown, and the only offered action is `Create`.

Hitting Create makes ANOTHER ad-hoc non-inventory part → the line never relieves stock and
carries no real cost. That's the compounding damage worth telling Joe about.

## Step-by-step (all read-only, ~2 min)

### 0. Resolve the RO across all 7 stores first
RO numbers are NOT unique fleet-wide (398792 existed at BOTH ST/876 as a 2023 CLOSED RO
and TL/1092 as the live one). Sweep `documentNumber IN [ro]` per dealer, disambiguate on
`status` + `creationTime`. See `tekion-openapi-repair-orders`.

### 1. Read the recommendation's part line (internal API)
```python
h = json.load(open("/tmp/tekion_rec_headers.json"))   # captured axios headers
h["dealerId"]="1092"; h["tek-siteId"]="-1_1092"       # swap per store
GET https://app.tekioncloud.com/api/service-module/u/ro/<documentId>
    -> data.recommendations[] -> operations[].parts[]
```
Tell of the defect:
```json
{"partLineId": null, "partName": null, "partNumber": null,
 "quantity": 1, "unitPrice": 2199, "status": "PARTS_WORKING"}
```
All three identity fields null = the opcode handed the RO nothing.
(`unitPrice` still shows a number — it comes from the placeholder's price, not a part.)

### 2. Read the opcode's DEFAULT parts — this is the root cause
```python
POST /api/service-module/u/opcode/search
     {"searchText":"CABIN","pageInfo":{"start":0,"rows":20}}
# the search HIT itself carries the full opcode incl. parts[] — no detail GET needed
```
**`GET /api/service-module/u/opcode/<ID>` 500s and `/opcode/detail/<ID>` 404s** — don't
waste calls; the list-search hit already has everything (parts, pricing flags,
eligibility, storyLines).

Placeholder (broken):
```json
{"partId": null, "partNumber": null, "partName": "CABIN", "quantity": 1, "unitPrice": null}
```
Real linked part (healthy) — compare against a sibling opcode:
```json
{"partId": "03adbc6b...", "partNumber": "7073", "partName": "7073 - Frigi Fresh Unscented",
 "unitPrice": 25.13}
```
Also check `forcedPartSelectionEnabled`, `partsSalePricingType`, `eligibleForPartPreparation`.
Sweep the whole family in one search (`searchText:"CABIN"` returned 15 opcodes at TL:
CABIN, SMCABIN, BGCF, TAC30, TEK04020101, UCDAIR, PORTMAJOR…) — placeholders and typos
cluster (`BGCF` had partName **"CABIN FITER"**).

### 3. Prove the stock exists and prove the search trap
**Use the OpenAPI for PREFIX enumeration** — this is the fast way to list a part family:
```python
POST /openapi/v4.0.0/parts-inventory:search  {"searchText": "87139"}
# paginate meta.nextPageToken -> 35 rows, partNumber/description/onHandQty
```
Then run the SAME search on the word the advisor/parts person would type:
```python
{"searchText":"CABIN"}       # TL -> only 2 rows: 87139-07010 (21 OH) + junk "OR.." (0 OH)
{"searchText":"cabin filter"}# TL -> 1 junk row, 0 OH
```
That side-by-side IS the proof: 1,553 units on hand across 87139-*, but the word "cabin"
surfaces almost none of them. Print it as a two-table contrast for Joe.

### 4. Show it is NOT a platform bug — the opcode works on real ROs
Scan the last 14 days of ROs, prefilter on the free `tags` OPCODE value, fan out only
candidates, and list the part numbers actually billed under that opcode. At TL: 72 of
1,250 ROs used `CABIN` and billed real numbers (YZZ93, YZZ82, 0C010, 07010, WB001). So
Parts CAN find them by number on a live RO — it's the recommendation/estimate path (blank
line + description search) that dead-ends. **Run this BEFORE blaming Tekion.**
Cost note: 25 ROs × jobs→operations→parts ≈ 187s — run it in a background terminal job,
not inline, if you need more than ~25.

## API gotchas hit this session (save yourself 20 min)
- `/api/wms/parts/u/inventory/withPart/search` returns `{"total":1,"list":[]}` — a
  **non-zero total with an empty list** — when you pass `page:{"pageNumber":1,"pageSize":N}`.
  The working page key is **`{"start":0,"rows":N}`**. Silent, no error. Same for the v2
  path `/api/wms/parts/u/inventory/v2/withPart/search`.
- `withPart/search` is **exact-match only** on partNumber (no prefix/wildcard/searchText);
  `87139` → 0 rows, `87139YZZ82` → 1 row. For family enumeration use OpenAPI
  `parts-inventory:search` (which DOES do substring/prefix) or a source-code export.
- Part numbers in these APIs are stored **without the dash**: `87139YZZ81` matches,
  `87139-02090` returns 0.
- On-hand lives at `partInventory.quantity.onHandQty` (also `totalQty`, `available`,
  `minimumQty`). `inventoryPartDetail` has cost/list/supersessions but NO quantity.
- `/tmp/tekion_rec_headers.json` replays fine from plain urllib for both service-module
  and wms endpoints — just swap `dealerId` + `tek-siteId`. No browser needed for any of
  the above (:9223 may be parked on someone else's work).

## The fix (do NOT apply unless asked — Joe often wants diagnosis only)
1. Best: attach the real filters as **vehicle-scoped Overrides → Parts** rows on the
   opcode so the correct number auto-populates by VIN (skill `tekion-opcode-overrides` /
   `tekion-tek-opcode-part-replace`; for menu-included opcodes use
   `tekion-included-service-parts-override`).
2. Minimum viable: replace the free-text default with ONE real catalog part so a number
   lands and Parts can supersede it.
3. Housekeeping: delete junk inventory records (TL's `OR..` "CABIN FILTER", 0 OH) and fix
   placeholder typos (`BGCF` "CABIN FITER").
Always test on a throwaway quote before/after.

## Relationship to `tekion-generic-placeholder-part-swap`
That skill teaches how to CREATE these placeholders **deliberately** (so Parts substitutes
the right fluid at RO time). This skill is the **downside**: a placeholder on a
recommendation-heavy opcode leaves Parts with a blank line and a dead-end search.
Placeholders are fine for fluids where any brand works; they are BAD for
vehicle-specific filters where a VIN-scoped override is the right answer.

## Reference case
TL (1092) RO **398792**, 2016 Corolla 36,694 mi, rec `6a8f4a4b3774634c8d7cd052`,
opcode `CABIN` (`CABIN_1092`, DEALER_DEFINED), placeholder partName "CABIN",
line price $21.99. Stock invisible to the search: 87139-YZZ82 = **515**, YZZ09 280,
YZZ93 184, 0R030 136; 1,553 total across 35 `87139-*` records.
