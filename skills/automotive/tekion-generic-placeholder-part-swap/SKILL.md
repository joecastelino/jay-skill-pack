---
name: tekion-generic-placeholder-part-swap
description: Replace a specific auto-populating part (e.g. a BG or WS transmission fluid) on Tekion opcodes and menu included-services with a GENERIC placeholder part (e.g. "Transmission Fluid") that has NO inventory/parts-master record, preserving exact pricing. Use when a menu/opcode estimates the wrong specific part for some vehicles and Parts should substitute the real part at RO time. Verified end-to-end at Blackstone Toyota (BT, dealer 1249) 2026-07-20 across 5 fluid lines.
---

# Tekion Generic Placeholder Part Swap

## When to use
A service opcode or menu included-service auto-populates a SPECIFIC part (specific fluid, filter brand, etc.) that is wrong for some vehicles on the estimate. Joe's fix: swap it for a generic placeholder line ("Transmission Fluid") so the estimate is brand/spec-neutral and Parts bills the correct real part at RO time. Joe explicitly does NOT want a part added to inventory/parts master.

## Core mechanic (Joe-confirmed)
In any Tekion part-select dropdown (opcode edit, included-service edit), typing a string with **no catalog match** surfaces a `Create "<your text>"` option. Picking it creates an **opcode-local placeholder part line** with a settable price and **NO parts-master/inventory record**. Verify: search the string at `/parts/inventory/part` afterward — no record should exist.

## Where the specific part can live (check ALL of these)
For a "wrong fluid on estimate" complaint, the part may auto-populate from several sources — trace before swapping (never-guess rule):
1. The à-la-carte opcode's **Default tab parts** (`/ro/opcode/edit/<OPCODE>`)
2. The menu's **included service** (`/ro/service-menu-setups/included-service` → row ⋮ → Edit service) — this is what menus actually bill
3. **Sibling opcodes** with similar descriptions (e.g. BT had SMTRANSMISSION, SMTRANSMISSIONHYBRID, ATFXWS, HVTRANS, ATF — the literal "WS fluid" was on SMTRANSMISSIONHYBRID, not the one first suspected). ATF was labor-only (no parts) — always check, some have nothing to swap.

## Procedure (per part line, on :9225 browser server)
1. **Baseline first**: dump current part rows (name/qty/price) + labor to a `*-before-YYYYMMDD.json` in `/home/itadmin/bt-menu-build/` (or store-appropriate dir) for clean revert.
2. Navigate to the edit page; kill Pendo: `document.querySelectorAll('[id*=pendo],[class*=pendo]').forEach(e=>e.remove())`.
3. Scroll 'Part Name' label into view. Click INTO the target row's part select (~x+80 of the singleValue, y+8). Verify `document.activeElement.id` starts with `partName` — the **Fees select can steal focus/text** (known gotcha, produces "No Match Found").
4. Type the generic name via native value-setter + per-char `input` events on `document.activeElement`.
5. Click the `Create "<name>"` option (appears ~40px below the row).
6. **Price behavior — critical**:
   - If the old row had a FIXED price, it **survives the swap** (HVTRANS kept $136.24 automatically) — just verify.
   - If the old row had a BLANK price (bills dynamically at parts-master LIST), the placeholder has no master record to price from — you MUST set a fixed price. Read the currently-billed price off a live quote first (open the opcode on a throwaway quote, read the Unit Price column), then set it in the row's `ant-input-number-input` (placeholder `0.00`). **This freezes the price** — flag to Joe that it no longer floats with list-price changes.
7. Click **Update** (opcode page, ~1211,688) or **Save** (included-service page). Require success toast.
8. **True remount verify**: navigate to `/home`, back to the edit URL, re-read rows. Same-URL re-nav does NOT remount the SPA (false positive).
9. **Quote explode verify**: on a throwaway quote, add the opcode and confirm the parts table shows the generic name at the same price and unchanged op total. Cancel out of the panel to leave the quote clean.

## Quote opcode search PITFALL (cost several attempts)
The quote page's opcode search (`input#undefined-opcodeSearch`, mode select `#searchType` = Opcode) **does NOT find custom opcodes by their code** — typing `SMTRANSMISSION` or `SMTRANSMISSIONHYBRID` returns only `Create "..."`. It matches on **DESCRIPTION text**: type e.g. `TRANSMISSION FLUID EXCHANGE` or `hybrid` and the real `ATFXWS - ...` / `HVTRANS - ...` options appear. Type with keydown+native-setter-input+keyup per char; results take ~5-7s. Dropdown is scrollable (set scrollTop on the menu container) when >20 results.

## :9225 browser server quirks
- `/eval` body key is `{"js": ...}` — `expression` fails.
- Screenshot = **GET** `/screenshot`, JSON key `screenshot` (base64). POST /screenshot is 404.
- Complex JS with template literals/arrow funcs can 500 the eval — use `(function(){...})()` ES5 style.
- If at `/login`: `cd /home/itadmin/tekion-auth && python3 login.py`.
- Check :9223 before using it — it may hold someone else's in-progress work (park on :9225 for subagent/side work per lane rule).

## BT reference state (2026-07-20, all verified)
| Surface | Old part | New | Price |
|---|---|---|---|
| SMTRANSMISSION opcode | BG3143 FULL SYN ATF | Transmission Fluid | $136.24 |
| Included svc 697ba2a4c4a9a7372669a4d1 | BG3123 3GAL | Transmission Fluid | $185.31 |
| SMTRANSMISSIONHYBRID opcode | 00289-ATFWS WORLD STANDARD ATF ×7 | Transmission Fluid ×7 | $15.66 ea |
| ATFXWS opcode | BG3123 (dynamic LIST) | Transmission Fluid | $134.57 FROZEN |
| HVTRANS opcode | BG3123 | Transmission Fluid | $136.24 |
| ATF opcode | (labor-only, no parts) | untouched | $496.04 flat |

Baselines: `/home/itadmin/bt-menu-build/smtransmission-opcode-before-20260720.json`, `smtransmissionhybrid-opcode-before-20260720.json`, `atfxws-hvtrans-opcode-before-20260720.json`.

## Verification checklist
- [ ] Success toast within ~3s of Update/Save
- [ ] True remount (via /home) shows generic name + correct price/qty
- [ ] Parts master search shows NO record for the generic name
- [ ] Quote explode: same op total, generic name in parts table
- [ ] Baseline JSON on disk before any change
