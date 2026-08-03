---
name: tekion-technician-queue-dispatch
description: Explains Tekion's Technician Queue / Claim Work auto-dispatch behavior — why a tech gets pulled out of the queue when an advisor opens/reopens an RO, and what settings can change that behavior. Use when diagnosing "why did my tech get grabbed out of queue" or "can we stop a tech from being pulled on RO reopen" questions.
---

# Tekion Technician Queue / Auto Dispatch

## Core mechanic (verified via KB, not guessed)
- Tech clicks **Claim Work** with no ROs available → enters queue with a rank.
- The moment an advisor **creates an RO** (or a job/RO becomes dispatchable again, including a **reopen**), Tekion's auto-dispatch engine fires immediately.
- It walks the queue by rank and assigns the RO to the **highest-ranked tech with matching skills** (not strictly rank #1).
- That tech is **removed from the queue** the instant they're assigned — even if the car isn't physically staged yet.
- Only other ways a tech leaves queue: clocking out for lunch/end of day.
- Queue refreshes every ~2 minutes; dispatch trigger = RO/job availability.
- Dispatch TYPE is set per-team: **Teams settings → Service tab → "Claim Work Job" vs "Claim Work RO"**.

## Reopened-RO case (no dedicated "don't pull from queue on reopen" toggle exists)
There is NO documented setting that flatly disables dispatch-on-reopen. But levers that address it indirectly, in **Dispatch Settings** (App Grid → Settings → Service Settings → Dispatch Settings, KB0019330):

1. **"Auto assign Technician same as Last Service from Return RO"** (General Settings toggle) — closest fit. When ON, a reopened/returning RO auto-assigns the SAME tech who worked it before instead of pulling the next queued tech. Queue stays intact.
2. **"Auto Assign Technician to Added Job"** toggle — if OFF, jobs added/reactivated on an open RO do NOT auto-dispatch; they wait for manual assignment. Turning this OFF stops advisors from accidentally yanking a queued tech just by editing a ticket.
3. **RO Hold limits** (Dispatch Settings → RO Hold tab) — techs can carry up to N held ROs (Tekion recommends 5) without losing queue eligibility.
4. **Reserve Technician** feature — reserve specific techs to specific ROs; those jobs bypass the general queue entirely.

## Rank editing
Repair Order app → Action → Technician Queue → drag the 6-dot handles to reorder. Requires "Technician Queue Edit" permission.

## Unknowns / escalate to PSM
- Whether reopening a **closed** RO behaves identically to job-add on an OPEN RO under these same toggles — not documented, needs live testing or PSM confirmation.
- Whether a "delay dispatch until vehicle check-in" option exists at all — not found in KB; if asked, say so rather than guessing.
- Deeper Auto Dispatch config changes beyond these toggles → PSM / support@tekion.com.

## Source KB articles
- KB0013137 — Technician Queue editing (dispatch removes tech from visibility once assigned)
- KB0010985 — Technician Queue (refresh cadence, dispatch trigger, per-team dispatch type setting)
- KB0019330 — Dispatch Settings (General Settings toggles, RO Hold tab, Reserve Technician)

Use `tekion-kb-search-scrape` skill to re-pull/verify these articles if details need refreshing.
