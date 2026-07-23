---
name: tekion-sitemap
description: Master navigation site map for the Tekion DMS. Direct URL/nav reference for every workflow (Service/RO, Parts & Inventory, Source Code, Purchase Order, Vehicle Inventory, Reports, Accounting, Admin) so you jump straight to a screen via the persistent browser (:9223) instead of hunting menus. Load this FIRST for any browser-based Tekion task.
triggers:
  - tekion navigation
  - tekion site map
  - tekion url
  - where is in tekion
  - navigate tekion
  - tekion parts inventory screen
  - tekion stocking details
---

# Tekion DMS — Navigation Site Map (skill wrapper)

Load this skill at the start of ANY browser-based Tekion workflow. The full,
always-current site map lives in a reference file (also mirrored at
`~/tekion-reports/TEKION-SITEMAP.md` for non-skill access):

→ `references/sitemap.md`

## When to use
- You need to reach a Tekion screen (Parts, RO, Opcode, Source Code, PO, VI, Reports)
  and want the direct URL instead of clicking through the App Grid.
- You hit "where is X in Tekion?" — check the site map's App/Module URL Map first.

## The 4 rules that save the most time
1. **Auth + dealer first.** Login bounces? Re-OTP. Default dealer after login is BC
   Blackstone Chevrolet (1251) — ALWAYS switch to the target store before navigating
   to store data. Known dealer IDs: BC=1251, ST/SCT=876, BT=1249, TL=1092
   (SV/AR/VC still tbd — fill in as switched).
2. **Navigate by URL, not menus.** Most SPA screens accept `POST /navigate {url}`
   directly. e.g. Parts list = `/parts/inventory/part`, part detail =
   `/parts/inventory/part/view/M_TMNA_<PARTNUM>/details`.
3. **All Tekion work goes through the `:9223` persistent browser** (logged in), NOT
   the `browser_*` tool (separate, unauthenticated). Use `execute_code` + the HTTP API.
4. **React/Ant gotchas:** use `/press` Enter (not JS click); popovers render in portals
   invisible to snapshot — use the `.ant-popover-inner-content` JS pattern or vision.

## Keep it current
Every time you verify a NEW URL or nav path in Tekion, append it to
`references/sitemap.md` (patch this skill). Fill in unknown dealer IDs (BT/SV/TL/AR/VC)
as you switch to those stores. This file is only as good as it is complete — maintain it.

## Related skills
- `persistent-browser-server` — start/restart the :9223 server, API reference
- `tekion-browser-navigation` — login flow, OTP, dealer-switch detail, opcode editing
- `tekion-openapi-repair-orders` — when data can be pulled via API instead of browser
- `tekion-parts-autoorder-diagnosis` — the parts stock-out / replenishment workflow
