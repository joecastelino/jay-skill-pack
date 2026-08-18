---
name: tekion-labor-rate-create
description: Create or complete a Tekion Labor Rate Pricing entry (e.g. a Caliber Collision wholesale-parts labor rate) via the Labor Pricing screen. Covers the list-first dedup check, the create/edit form field mechanics, and the Part Price Code gotcha (no generic "Wholesale" option — codes are custom per store).
triggers:
  - create labor rate
  - labor rate pricing
  - caliber collision rate
  - wholesale labor rate
  - new labor pricing tekion
---

# Tekion Labor Rate — Create/Complete a Labor Pricing Entry

## When to use
Joe/a store asks for a new labor rate (e.g. "Caliber Collision Rate @225/hour, parts
pricing wholesale") to be added at a specific Tekion store. Labor rates are
per-dealership — always confirm/clarify WHICH store first if not stated.

## Step 0 — ALWAYS check the existing list first (dedup / resume-draft check)
Navigate `https://app.tekioncloud.com/ro/labor-pricing` on the target dealer (switch
dealer first if needed — see `tekion-sitemap` dealer-switch JS pattern). Read the full
table via `document.body.innerText` (paginate the slice if it's long — the list can run
~1500+ chars, e.g. BT had 23 rows).

**Look for a near-match or partial/abandoned entry before creating new.** Verified case
(BT, 2026-08-18): a row named **"Caliber C.C"** already existed — Rate Type **Fixed**
$225, description "Caliber C.CV", Part Price Code **"-"** (unset). This was clearly a
prior incomplete attempt at the exact same ask ("Caliber Collision Rate @225/hr,
wholesale parts"), not a different/intentional row. Completing/fixing that existing row
is the right move — do NOT create a duplicate new row next to a clear draft. Only
create fresh via "Add Labor Pricing" if no plausible existing draft/match exists.

To open an existing row for editing: find the name cell (`el.children.length===0 &&
textContent.trim()===name`), `scrollIntoView`, get its bounding rect, `/mouse` click
near its center (text links here don't respond to plain `/click` by selector reliably —
`/mouse` at the rendered coords works). Lands on
`/ro/labor-pricing/edit/<mongoId>`.

## Form fields (Labor Rate Pricing edit page)
| Field | Control | Notes |
|---|---|---|
| Name | textbox (ref e80 typically) | required |
| Description | textbox (ref e81 typically) | required — can mirror Name |
| Customer Time / Manufacturer Time | radio pair + multiplier +/- steppers | leave default (Customer Time selected, multiplier 1) unless told otherwise |
| Rate Type | combobox — click to open, options: **Hourly Labor Rate / Dynamic Pricing / Custom / Fixed** | click combobox ref, then find the option `li/div/span` by exact text match, get its rect, `/mouse` click center. Plain `/click` on the option can no-op — prefer `/mouse`. |
| Rate value | spinbutton/textbox that appears once Rate Type is set | for Hourly this is the $/hour value |
| Part Price Code | combobox, searchable, ~20 store-specific options | see gotcha below |

## Part Price Code selection mechanic — TYPE + Enter, NOT /mouse click on the list item
Verified BT 2026-08-18: unlike the Rate Type combobox (where `/mouse`-clicking the
option's rendered rect works), the Part Price Code combobox's dropdown-list items did
**NOT** respond to `/mouse` clicks — the click registered (`{"success":true}`) but the
dropdown just closed and the field stayed on placeholder "Select" (confirmed via
screenshot+vision, twice). This combobox is a **searchable/filterable** Ant Select.
The reliable method: `/click` the combobox to open it, then `POST /type {ref, text:
"<search term>"}` (e.g. "Trade") — the list filters down to "N result(s) available for
search term X", then `POST /press {key:"Enter"}` selects the top/only filtered result.
Verify via `document.body.innerText` showing "option <text>, selected." No need to
locate/click the option element at all once you're typing+Enter.

## GOTCHA: Part Price Code has NO generic "Wholesale" entry
Tekion's Part Price Code list is a store-specific catalog of numbered price codes —
there is no plain "Wholesale" choice. Verified BT (2026-08-18) 20 options included:
`4 | Trade` (closest to generic wholesale), plus Cost+X% / List-X% tiers, PLUS
**store-custom Caliber-branded codes already present**: `16 | Caliber Bakersfield
list -32%` and `18 | Caliber Central Valley`. This means AMG already has an
established per-location Caliber Collision wholesale-discount convention — when asked
to set "wholesale" pricing for a Caliber-named rate, **do NOT assume "Trade" is
correct**. Check the store's existing Part Price Code list first for a Caliber-branded
code, and if the discount % isn't obvious/confirmed, STOP and ask the user which code
(or exact %) to use — this directly affects real parts $ pricing, don't guess (see
Joe's NEVER-GUESS rule). Verified resolution 2026-08-18 (BT "Caliber Collision Rate"):
asked user directly in-chat (numbered options: Bakersfield code / Central Valley code /
generic Trade / custom %) — user chose generic **"4 | Trade"**. So Trade IS an
acceptable default when the user confirms it, just don't silently assume it.

**No `clarify` tool in Slack context** — when asking this kind of blocking question from
a Slack conversation, `clarify()` errors out ("not available in this execution
context"). Fall back to a plain chat message with numbered choices instead of the
clarify tool; this works fine and the user can just reply with their pick.

## Save
Bottom-right "Save" button. Verify by re-navigating to the list (`/ro/labor-pricing`)
via a fresh nav (not just re-reading current DOM) and confirming the row now shows
correct Name / Rate Type / Rate / Part Price Code / Active status.

## Related
- `tekion-sitemap` — Labor Pricing URL (`/ro/labor-pricing`), dealer switch JS.
- `persistent-browser-server` — `/mouse` endpoint for React/Ant controls that ignore `/click`.
