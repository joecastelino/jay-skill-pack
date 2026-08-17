---
name: tekion-vendor-data-sharing-audit
description: Audit which third-party vendors/integrations (vAuto, HomeNet, VinSolutions, CDK, Carfax, Podium, OEM feeds, etc.) are receiving data feeds from Tekion, broken down by store. Use when asked "what vendors get data feeds/integrations from AMG", "who are we sending inventory/CRM/recon feeds to", or similar vendor-integration inventory questions.
---

# Tekion Vendor Data Sharing Audit

## Where the data actually lives
**Core app → "Vendor Data Sharing"** tile, URL `https://app.tekioncloud.com/core/vendor-data-sharing`.
Reached via: app-grid (nine-dot icon top-right ~x1130,y31.5) → Settings tab → Core apps section →
"Vendor Data Sharing" tile (NOT "Vendor Management", a different tile).

**Do NOT confuse this with "Integration Hub"** (app-grid search "integration") — Integration Hub is
a marketplace of installable apps (status/subscribe tiles), not real syndication feeds. Direct
iframe URL to its "My Integrations" view (`apc.tekioncloud.com/dealer/integration-hub/list?token=...`)
returns "Forbidden" if hit directly — dead end, use in-app nav only. The REAL vendor feed data
(vAuto, HomeNet, VinSolutions, Carfax, CDK, etc.) is under Vendor Data Sharing, not Integration Hub.

## Page structure
Table columns: Vendor Name, Data Type, Download Data, Data Shared Date, Data Sharing Status.
Top-level rows show `VendorName\n(N)` where N = count of data-sharing events; click to expand and
see the Data Type sub-rows (e.g. Vehicle Inventory, Parts Inventory, Customer, Service).
Some rows are OEM rollups (e.g. BC shows a `GM (65)` parent row aggregating sub-vendor counts like
CDK Global, HomeNet, Carfax under the GM umbrella) — don't double-count the rollup against its children.

## Date filter — KNOWN METHODOLOGY GOTCHA
The default view loads a NARROW recent window (looked like ~Aug 16-17, i.e. last 1-2 days) and is
the most RELIABLE/consistent view for cross-store comparison — every store returns a clean, stable
vendor list under it. Wider filters are unreliable:
- **"Year-to-Date"** under-reports — missed vendors that showed up in "Reset".
- **"Reset" (all-time/unfiltered)** samples inconsistently — for SCT it additionally surfaced
  vAuto, Tekion, PEN (Power Information Network), CCC, OpsTrax, RecallMasterUS that did NOT
  appear under YTD or under the default narrow window for other stores.
- A custom date range (e.g. Aug 1-17) did NOT change the total count at all in one test — the
  filter UI can silently fail to apply.
**Recommendation:** use the DEFAULT narrow window for a clean per-store comparison baseline (what's
actively syncing right now), then separately note that a broader "Reset" sweep may reveal additional
DORMANT/less-frequent integrations (vAuto is the one Joe cares about — it didn't show up in the
narrow window for any store in one pass, only in SCT's "Reset" view). Always disclose which filter
state you used when reporting numbers, and flag that dormant vendors may be undercounted.

## Switching stores — pitfalls and the reliable method
Dealer switcher pill = `.root_dealerSelect_container__eXjxN2P5EN` (top-right ~x1100-1130,y20-32).
Click it, wait ~2s, popover = `.ant-popover-inner-content`.

**PITFALL 1 — only 6 of 7 stores visible without scrolling.** The popover list is a scrollable
container inside itself (a `root_dealerInfoList_itemListContainer` div with `scrollHeight >
clientHeight`). By default only AR/AM/BC/BT/ST/SV show — **Toyota of Lancaster (TL) and Volkswagen
of Clovis (VC) are BELOW THE FOLD** and clicking their "expected" coordinates (extrapolated from the
visible 6) actually re-clicks whatever real row happens to sit at that y — this caused repeated silent
mis-switches (multiple "switches" that all landed back on AR or stayed on the previous store while the
extracted "vendor list" was actually a stale re-read of the SAME unchanged page). **Fix: before reading
row coordinates, scroll the inner container** (`el.scrollTop = el.scrollHeight` on the element with
`scrollHeight > clientHeight`), THEN re-query for the target store's exact text match with
`offsetParent!==null` filter, THEN `/mouse` click its center.

**PITFALL 2 — coordinate caching gives false switches.** Don't reuse a coordinate captured once;
the popover's DOM (and thus row y-positions) can shift between scroll states. Re-derive coords fresh
every attempt.

**PITFALL 3 — verifying "did the switch actually work" needs TWO checks, not one.**
`localStorage.currentActiveDealerId` changing is necessary but a previous session showed cases where
this DID change but the visible page header still lagged/showed the old store name transiently. The
robust check: after `/mouse` click + ~3.5s wait, `/navigate` to the vendor-data-sharing URL fresh, then
read `document.body.innerText`, locate `"Vendor Data Sharing History"`, and read the ~40 chars BEFORE
it — this contains the store code + full name header (e.g. `"TL\nToyota of Lancaster\n"`). Confirm
BOTH `currentActiveDealerId` changed AND the header text matches the target store name before trusting
the vendor table content.

## Confirmed dealer IDs (all 7 AMG stores, verified via this method)
| Code | Store | Tekion dealerId |
|---|---|---|
| AR | Alfa Romeo of San Jose | 6195 |
| BC | Blackstone Chevrolet Cadillac | 1251 |
| BT | Blackstone Toyota | 1249 |
| ST | Stevens Creek Toyota | 876 |
| SV | Stevens Creek Volkswagen | 826 |
| TL | Toyota of Lancaster | 1092 |
| VC | Volkswagen of Clovis | 1891 |

There's also an 8th entry in the switcher, **AM — American Motors Customs & Classics** — appears to
be a non-service/holding entry, not one of the 7 real stores; verify relevance with Joe before
including it in a store-by-store report.

## Extraction snippet (per store, after confirmed switch)
```python
r = api("/eval","POST",{"js":"document.body.innerText"})
txt = r["result"]
idx = txt.find("Vendor Name")
end = txt.find("Results Per Page")
vendor_block = txt[idx:end]   # gives "VendorName\n(N)\n..." pairs, parse by line
```

## Results captured 2026-08-17 (default narrow-window view, for reference)
- **ST**: Toyota(12), CDK Global(7), SmartVMA(10), Authenticom(4), OE Connect Toyota(2), Sirius XM(2),
  TVI Market PRO(2), HomeNet(2), Cloud One(2), Carfax(1), Market Scan(1), Parts Sales Xcellerator(1),
  Power Information Network(1), Stone Eagle(1), True Car(1)
- **BT**: Toyota(12), SmartVMA(10), Authenticom(4), CDK Global(4), OE Connect Toyota(2), Carfax For
  Life(2), Cloud One(3), HomeNet(2), Sirius XM(2), TVI Market PRO(2), Carfax(1), Market Scan(1),
  Parts Sales Xcellerator(1), Stone Eagle(1), True Car(1), Vin Solutions(1)
- **TL**: CDK Global(13), Toyota(8), Authenticom(2), OE Connect Toyota(2), HomeNet(2), Sirius XM(2),
  TVI Market PRO(2), Carfax(1), Cloud One(1), Market Scan(1), Parts Sales Xcellerator(1), Stone
  Eagle(1), True Car(1), Vin Solutions(1)
- **BC**: GM/General Motors(65 rollup), SmartVMA(10), CDK Global(5), Authenticom(4), Cloud One(3),
  Carfax For Life(2), HomeNet(2), OE Connect GM(2), TVI Market PRO(2), Carfax(1), Market Scan(1),
  Parts Sales Xcellerator(1), Sirius XM(1), Stone Eagle(1), True Car(1), Vin Solutions(1)
- **SV**: CDK Global(9), Authenticom(4), Vin Solutions(2), Podium(2), Cloud One(2), HomeNet(2),
  Sirius XM(2), TVI Market PRO(2), Carfax(1), Market Scan(1), True Car(1)
- **VC**: CDK Global(13), Authenticom(3), Cloud One(3), Vin Solutions(2), HomeNet(2), Carfax(1),
  Market Scan(1), Parts Sales Xcellerator(1)
- **AR**: Fiat Chrysler Automobiles(2), Cloud One(3), HomeNet(2), TVI Market PRO(2), CDK Global(1),
  Sirius XM(1)

Function groupings: OEM feed = Toyota/GM/FCA; Inventory-recon-photo = HomeNet, TVI Market PRO, Stone
Eagle, SmartVMA; CRM/leads = Vin Solutions, Podium (Podium only at SV); Valuation/history = Carfax,
Carfax For Life (only BC/BT), True Car, Market Scan; DMS sync = CDK Global, Authenticom, Cloud One;
Parts = Parts Sales Xcellerator, Power Information Network (PEN, only seen at ST); OEM connect =
OE Connect Toyota/GM. vAuto did NOT appear in the default narrow window for any store — only showed
up in SCT's broader "Reset" pull; treat vAuto as needing a dedicated all-time sweep to confirm status.
