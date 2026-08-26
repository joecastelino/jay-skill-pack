---
name: tekion-duplicate-customer-record-diagnosis
description: Confirm/refute a store claim that an RO, recommendation, or deferred service "went to a different customer number for the same customer" in Tekion. Finds duplicate customer records sharing a phone/VIN, maps which customer id each RO + recommendation was stamped with, and identifies who wrote it.
triggers:
  - different customer number
  - duplicate customer record
  - recommendation went to the wrong customer
  - customer history missing / split
  - deferred service didn't follow the customer
---

# Tekion Duplicate Customer Record — "it went to a different customer number"

## Symptom
Store says: "we added the recommendation / wrote the RO and it landed on a DIFFERENT customer
number for the same customer." Effect: prior service history, deferred/declined recommendations,
and marketing follow-up don't tie to the new RO.

## Diagnosis (all API, no browser, ~6 calls, zero risk)

### 1. Find the RO — sweep all 7 dealers (RO numbers are NOT unique fleet-wide)
```python
for k,d in cfg["dealers"].items():
    post("/repair-orders:search", d, {"filters":[{"field":"documentNumber","operator":"IN","values":[RO]}],"pageSize":5})
```
Disambiguate on `status` + `creationTime`. The result carries `primaryCustomer.id`,
`assignee.advisor.id`, `createdByUserId.id` for free.

### 2. Get the customer on the RO
`GET /repair-orders/{rid}/ro-customers/{customerId}` → name, address, phones, email.
`GET /repair-orders/{rid}/ro-vehicle` → VIN.

### 3. Find the DUPLICATES — search by PHONE (best key)
**`/customers:search` does NOT exist (404). Use `GET /customers?phone=...`** (spec:
`customer__get-customers.json`). Query params: `phone`, `email`, `lastName`, `firstName`,
`search` (partial across name/email/phone/arcId), `id`, `companyName`, `customerType`.
```python
get("/customers?"+urlencode({"phone":"8184811997"}))
```
Each record returns `displayId` (**this is the human "customer number"**), `id` (UUID),
`creationTime`, `customerDetails.name`, and `vehicles[]` with VINs. Duplicates = same phone,
same/near-identical name, overlapping VINs.

### 4. Map every RO on the VIN to its customer id — this is the proof
```python
post("/repair-orders:search", d, {"filters":[{"field":"vin","operator":"IN","values":[VIN]}],"pageSize":50})
# print documentNumber, status, creationTime, primaryCustomer.id
```
If 14 historical ROs sit on customer A and the new one sits on customer B → claim CONFIRMED.

### 5. Confirm the RECOMMENDATIONS carry the same (wrong) customer id
Internal reporting API (headers `/tmp/tekion_rec_headers.json`, swap `dealerId`/`tek-siteId`):
`POST /api/service-module/u/reporting/recommendation/search` with
`filters:[{"field":"roNo","values":[RO],"operator":"IN"}]` → each hit has `customer.{id,name,email,phone}`.
- `roNo` ✔ and `vehicle.vin` ✔ are valid filter fields. **`customerId` and bare `vin` return 0** — dead ends.
- `vehicle.vin` gives the FULL recommendation history across all duplicate customer records — the
  cleanest way to show which deferred lines are stranded on which customer number.

Also useful: `GET /api/service-module/u/ro/{roId}` → `data.recommendations[]` (id/status/concern)
and `data.ro.customerInfo.customerNumber` (= the displayId stamped on the RO).

### 6. Name the people
`GET /openapi/v4.0.0/users/{id}` resolves `createdByUserId` / `assignee.advisor.id`
→ `userNameDetails.completeNames[DISPLAY_NAME]`.

## Root cause (what to tell the store)
Not a Tekion bug. The VIN is linked to **multiple customer records**, so at write-up the advisor
picks a vehicle and Tekion offers whichever customer record is attached — an advisor who picks the
wrong one silently forks the history. Duplicates usually originate from a SALES record (created at
delivery) vs a SERVICE record (created at first RO), plus later ad-hoc re-adds.
Tell: duplicate `displayId`s with the same phone, different `email` placeholders
(`noemail@mail.com` vs `NONE@YAHOO.COM`) and different creation dates.

## Fix
Tekion Customer merge (Customers module → open the duplicate → merge into the master).
**This is a data mutation — get Joe's explicit OK before merging.** Recommend merging INTO the
record with the longest RO history so deferred/declined follow-up stays intact.

## Reference case (TL/1092, RO 398549, 2026-08-26) — claim CONFIRMED
CYNITHIA COOPER, 2022 Camry `4T1G11AK7NU053419`, phone 818-481-1997 → **3 customer records**:
- **#665523** (created 7/8/2022) — all 14 prior ROs 2022→6/10/2026, email `noemail@mail.com`
- **#669655** (created 8/19/2022) — MRS CYNITHIA ANNE COOPER, Avalon + Camry, `NONE@YAHOO.COM` ← RO 398549 written here by Michael Hachey
- **#1317353** (created 1/27/2026) — third dupe, Camry attached, zero ROs

June RO 388418 (advisor Haide Camacho, cust #665523) deferred LOWER BALL JOINTS + BRAKE FLUID
EXCHANGE; both were sold on RO 398549 ($2,691.81 CP) under #669655 — so the deferred-to-sold
conversion is invisible on the original customer record.
