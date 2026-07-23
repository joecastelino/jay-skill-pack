---
name: tekion-kb-search-scrape
description: Search and scrape the Tekion ServiceNow Knowledge Base (tekion.service-now.com) authenticated as Joe, then store articles in the Tekion KB / GBrain. Use whenever you need to look up HOW a Tekion workflow/setting works, find KB articles by keyword, or ingest Tekion documentation. The KB auto-SSOs from the logged-in DMS session — no separate login needed. Load alongside tekion-sitemap and persistent-browser-server.
---

# Tekion ServiceNow KB — Search & Scrape

The Tekion Knowledge Base lives on ServiceNow at `tekion.service-now.com/sp/en`.
It is a SEPARATE app from the DMS, BUT it **auto-SSOs** from Joe's logged-in DMS
session — so via the `:9223` persistent (authenticated) browser you can read any
KB article as Joe. (Older memory said the KB was "blocked / PDF-export only" — that
is OBSOLETE. SSO works.)

## One-time SSO bootstrap (only if KB shows a login form)
If `tekion.service-now.com/sp/en?id=index` shows "Login / Log in" instead of
"JC Joe Castelino", establish SSO FIRST. **THE RELIABLE METHOD (verified 2026-07-12):
just `/navigate` to `https://app.tekioncloud.com/core/knowledge-base/search`** —
that's the URL the DMS "Knowledge Base" link fires (discovered via `window.open`
hook); it performs the full SSO handshake in the SAME tab and lands you on
`tekion.service-now.com/sp` authenticated as Joe. Requires a live DMS session on
:9223 (verify "Welcome back, Joe" on /home first).

DO NOT waste time on the ServiceNow login page itself — all of these FAIL:
- "Use external login" → User ID + Submit → bounces back to username/password
- `login_locate_sso.do` with either of Joe's emails → bounces back to login
- The manual Get Help → Knowledge Base click path also has TWO traps: (1) Pendo
  tour overlays swallow the clicks — remove `[id*=pendo],[class*=pendo]` after
  opening the drawer AND before re-scanning for the "Knowledge Base" element
  (its coords shift once overlays are gone); (2) the link calls `window.open`
  (new tab the :9223 server doesn't track) — hook
  `window.open=u=>{window.__opened.push(String(u))}` to capture the URL, then
  `/navigate` to it in the tracked tab.

## The helper script (canonical)
`/home/itadmin/tekion-reports/kb_search_scrape.py` (uses the :9223 browser):
```
python3 kb_search_scrape.py search "bin location"          # -> [{kb:KB0012192, title:...}, ...]
python3 kb_search_scrape.py article KB0012192              # -> {url, body}
python3 kb_search_scrape.py article KB0012192 KB0022520    # batch
```
Tested working 2026-06-29.

**Bulk / recursive scraping of a landing-page tree** (e.g. "Landing page for
Service 3.0 KB articles", sys_id b2a882cbc3d54350a5d19ec905013167 → ~60 articles):
`/home/itadmin/tekion-kb/scripts/scrape_service30_tree.py` — BFS from a seed
sys_id, extracts 32-hex sys_ids from body links (entityId=...), follows
"Landing page for ..." sub-indexes to depth 2, saves each to
`tekion-kb/text/SVC30_<sysid8>_<slug>.txt`. Adapt SEED for other trees. Run as
background (8s page-load + 2s pacing per article). It self-detects auth loss
("Log in" in document.title → prints AUTH/EMPTY, doesn't save garbage).

## How it works (the mechanics — the hard-won parts)
1. **The KB is a Seismic web-component SPA with ~390 shadow roots.** The search box
   is an `<input>` inside `sn-search-combobox` → must PIERCE shadow DOM to find it.
   Normal `document.querySelector('input')` returns nothing.
2. **Find the search input**: recurse shadow roots collecting visible `INPUT`s; on
   the home page it sits around (617,287). Click it with `/mouse` (raw coords) to focus.
3. **Type into it**: `document.activeElement` (drill through `.shadowRoot.activeElement`)
   → set value via the native `HTMLInputElement.prototype.value` setter, dispatching
   `input` events per char, then a synthetic `Enter` KeyboardEvent. This navigates to
   `?id=search&q=...`. (The :9223 server has NO keyboard endpoint — must do it in-page.)
4. **Read results**: deep-walk shadow roots concatenating `textContent`; results render
   as triples `KBxxxxxxx` / "N ago" / Title. Pair each `KB\d{7}` with the next title line.
   Left rail also shows **KB Category** facets (Parts & Inventory, Warehouse Management,
   Parts Settings, Physical Inventory, Repair Order, etc.).
5. **Open an article by KB number (THE reliable trick)**: navigate directly to
   `https://tekion.service-now.com/sp/en?id=kb_article_view&sysparm_article=KBxxxxxxx`
   — it 302s to the article slug. DO NOT try clicking result links: they're
   `javascript:void(0)` Angular handlers and `.click()` won't route.
   **sys_id articles too**: many articles/landing pages are addressed by 32-hex
   sys_id instead of KB number — `?id=kb_article&sys_id=<32hex>` works the same.
   Links INSIDE article bodies use the form
   `https://app.tekioncloud.com/core/knowledge-base?entityType=KNOWLEDGE&entityId=<32hex>`
   — the entityId IS the sys_id; extract it and rewrite to the sp/en URL.
6. **Read article body from REGULAR DOM** (not shadow): `.kb-article-content`
   (fallbacks `[itemprop=articleBody]`, `article`, `.article-content`). Body is plain text.

## Storing into the brain (the ingest workflow)
After scraping, persist so it's searchable in GBrain:
1. Save raw text → `/home/itadmin/tekion-kb/text/<KB>_<slug>.txt`
2. Write a DISTILLED markdown page → `/home/itadmin/tekion-kb/distilled/<topic>.md`
   (steps, settings, exact field names, gotchas, + a KB# index table).
3. Auto-embed: anything dropped in `/home/itadmin/tekion-kb/{distilled,text,transcripts}`
   is picked up by `session-end-sync.sh` → `ingest-kb-batch-to-brain.py` within ~15 min
   (sha1-tracked, only new/changed). No manual embed step. Search later via `gbrain`.
4. If it documents a workflow, also create/patch a `tekion-*` skill + update `tekion-sitemap`.

## Pitfalls
- Full page navigation WIPES any injected XHR/fetch hooks — reinstall after load, or
  just use the direct article URL method (no hooks needed).
- The ServiceNow Table API (`/api/now/table/kb_knowledge`) returns 401; the SP search
  POST (`/api/now/sp/search`) needs a portal+source payload that's fiddly — the UI
  search-box-typing method above is more reliable than reverse-engineering the API.
- Verify store/auth isn't the blocker: if KB shows login, do the Get Help bootstrap.
- Use vision (`browser_vision`/`:9223 /screenshot` + vision_analyze) to read result
  positions and KB numbers when DOM parsing is ambiguous — the rail tabs are clickable
  category filters worth exploring (Joe's tip 2026-06-29).

## Service 3.0 corpus (scraped 2026-07-13 — already in the brain)
The full Service 3.0 KB tree (seed sys_id `b2a882cbc3d54350a5d19ec905013167`) is
scraped: **76 articles** at `/home/itadmin/tekion-kb/text/SVC30_*.txt`, embedded in
GBrain — search there before re-scraping. Derived deliverables (sent to Joe as a
Gmail DRAFT with 6 PDFs, 2026-07-13):
- `/home/itadmin/tekion-kb/distilled/service-3-0-kb-index.md` — index of all 76
- `/home/itadmin/tekion-kb/distilled/service-3-0-reading-action-plan.md` — Joe's 4-session (~5.5h) dependency-ordered reading path
- `/home/itadmin/tekion-kb/distilled/service-3-0-lesson-plan.md` — role-based training tracks (A Advisors, B Cashiers/Office = most-changed, C Managers = go FIRST/own config, D BDC), 2 wks/store, go-live gates
- `/home/itadmin/tekion-kb/cheatsheets/` — 4 print-ready 1-pagers (advisor / cashier / accounting / manager)

CORE 3.0 CONCEPT (the unlock for any Service 3.0 question): **payers are split
from pay types** — one CP job can carry MULTIPLE payers; each payer gets its own
invoice, its own real-time cashiering line (2.0 incremental cashiering is gone),
and its own JE posting line. Tax codes become MANDATORY. Store setup dependency
order: Pay Types Setup → Tax Codes → Vehicle Groups → Labor Pricing → Opcode
pay-types → Customer Mgmt defaults → Fees. Landing pages (12 of the 79 sys_ids)
are just link hubs — skip when reading.

## Cross-references
- tekion-sitemap, persistent-browser-server, tekion-browser-navigation (dealer switch),
  jay-brain-and-skill-index (GBrain ingest internals).
