---
name: tekion-warehouse-bin-management
description: Answer how Tekion handles bins — which bin a sale pulls from (Primary Bin), whether you can replenish/auto-transfer between bins, the Warehouse Management app (Bin Change, Bin Reports, locations), and the CDK-migration ghost-bin pattern. Use when Joe asks about "bins messed up", choosing a pull bin, per-bin replenishment, bin transfers, or primary vs secondary bins. Load with tekion-sitemap + persistent-browser-server.
---

# Tekion Warehouse / Bin Management

Verified live read-only at SCT (Stevens Creek Toyota, 876) on 2026-06-29 using the spark plug 90080-91180 as the worked example.

## The three questions Joe asks — answered authoritatively

### "Can I choose which bin a sale pulls from?"
**No — not per-transaction.** Tekion automatically relieves stock from the **Primary Bin**. There is NO "pull from bin X" selector on a sale/RO. The ONLY bin-level role designation is the **Primary Bin** flag (shown on the part's Bin Details). You change *which* bin sales draw from only by **changing which bin is Primary** — never per sale. (Glade told us this in June; confirmed in the actual settings here.)

### "Can I replenish one bin vs another?"
**No automatic per-bin replenishment exists.** Replenishment params (**BRP / BSL / Min / Max**) live at the **PART level**, not the bin level — they govern the part's TOTAL on-hand. Incoming PO stock lands in the **Primary Bin**. There is **no per-bin min/max** and **no automatic bin-to-bin transfer feature** in Tekion. The only bin-movement tool is the manual **Bin Change** (below).

### "Were my bins messed up because of a bin SETTING?"
Usually **no** — because there's no bin replenishment setting that could break. The classic SCT case = a **CDK→Tekion migration artifact**: the old CDK bin (e.g. bin **5005** on the spark plug, holding a phantom **−16**) was loaded as an opening balance at conversion and **no Tekion transaction ever touched it** (every sale pulls from the Primary Bin, e.g. 2420). Incoming POs backfill the phantom net-negative instead of building shelf stock. It's stranded legacy data, not a misconfig. Fix = manual **Bin Change** to clear/move the ghost, OR a **Bin Spot Check / Physical Inventory** on those bins to reset shelf truth (see skill `tekion-physical-inventory`).

## Warehouse Management app

Reach it via **App Grid (nine-dots, ~x30,y32) → search "Warehouse" → click the WM result `<A>`** (≈x480,y222). Direct URLs silently BOUNCE to the parts list (`/parts/inventory/warehouse` = wrong) — must go through the App Grid search. The real landed URL is **`/parts/warehouse-management`**.

Verified sub-URLs:
- `/parts/warehouse-management` — Locations list (SCT: "Stevens Creek Toyota" 408 bins / 91,023 parts / $2.0M + an "Unallocated" location with 1 bin). Top buttons: **Print Label · Bin Change · Bin Reports · Add Location**.
- `/parts/warehouse-management/bin-change` — **Bin Change** = the ONLY manual bin-move tool. "Change Bin By: **Part**" (reassign a specific part's bin) or "**Bin**" (move everything in one bin). Type part name → Select Parts to Modify Bin → Save. Manual reassignment, NOT scheduled/auto.
- `/parts/warehouse-management/bin-reports` — **Bin Reports** = printable bin list only (Custom / Range bin selection → Print). No settings.
- `/parts/warehouse-management/edit-warehouse-location/<locId>` — location detail: Location Details + **Bin Details** (Total N Bins, **Add Bin**, per-bin: Bin Name, Site, Description, Location Description, No of Unique Parts, View Parts). No per-bin replenishment/min-max fields here either.

## Where to READ live per-bin on-hand
The part view's **Bin Details** section (left-nav on `/parts/inventory/part/view/M_TMNA_<PN>/details`) shows each bin with on-hand qty and tags the **Primary Bin**. Example (spark plug, 2026-06-29): bin 2420 = Primary, +31; bin 5005 = (no role), −16; Total = 15. Just `/eval document.body.innerText` and slice the "Bin Details" section — don't try a cold `fetch()` (fails auth).

## KNOWN GAP — do NOT guess
I could NOT locate the control to **re-designate which bin is Primary** from the part view. The Primary flag displays but the edit surface (Edit Part? automatic from txn history?) is unverified. If re-designating Primary matters, get the Tekion KB on Bin/Warehouse setup or dig into Edit Part — do not invent how it's changed.

## Browser-API reminders (see persistent-browser-server skill)
- `:9223 /eval` body = `{"js": ...}` (NOT `expression`).
- `/click` needs `{selector|text|ref}` (errors on coords); `/mouse {x,y}` = raw-coordinate click.
- Dealer switch FIRST (default after any nav can be wrong store): open `.root_dealerSelect_container__eXjxN2P5EN`, wait ~1.5s, click the `STStevens Creek Toyota` leaf in `.ant-popover-inner-content`, verify header shows the store.

## Cross-references
tekion-sitemap, persistent-browser-server, tekion-physical-inventory, tekion-parts-autoorder-diagnosis, tekion-ghost-bin-negative-onhand.
