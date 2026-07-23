---
name: tekion-process-automation
description: Tekion CRM Process Automation — the tile where lead processes/rules fire. Covers Rules vs Processes, the New Lead Decision Tree, reading the process list (active vs run count), building/editing a process (step types, delay tasks, conditions), exit conditions, and the yes=left/no=right convention. Load for any CRM lead-automation, decision-tree, or "why didn't this task fire" question. This is CRM-side, NOT Fixed Ops.
---

# Tekion CRM — Process Automation

Source: CRM Jump Start webinar (James Mall, CVA). CRM-side. Full distillation at `references/process-automation-full.md`.

> **Decision-tree convention (memorize): YES branch always goes LEFT (green), NO branch always goes RIGHT (red).**
> **NEVER-GUESS RULE:** if you hit something not covered here, STOP and ask Joe.

## App & Navigation
- **Process Automation** tile — where all tasks fire and all lead processes run.
- **Top status filter:** defaults to **Active** (counterpart = **Draft** = inactive).
- **Type filter:** Rules vs Processes. **Search box:** free-text by name (type `internet`, `new`, `sold`).
- **Left-nav = trigger/event filters:** All · **Newly checked in** (lead check-in) · **Lead updated** · **Lead stage updated** · **Lead custom stage updated** · (more by trigger name).

## Rules vs Processes
**"Processes run ON a lead. Rules run independently and blindly."**
- **Processes** — run on leads after being triggered (**manual trigger** = the SYSTEM triggers it, not a human). Branching logic. Most of the work lives here.
- **Rules** — **Schedule Time Rules** fire at a set time daily, scan for matching leads, then execute one action. Common: `1 Service Appointment`, `1 Year Follow Up`, `1/2/3 Year Sold`. Example: First Service Appt rule runs daily 4 AM, finds Sold leads with Contract Date in last 1 day, creates a service Lead → assigns BDC.

## Reading the Process List (columns L→R)
**Type · Name · Description · Active count · Run count · Status**
- **Active count** = leads currently IN the process. **Run count** = lifetime total (includes current).
- ⚠ **Active (green) ≠ actually running.** Zero active + zero run count = no leads flowing in → check triggers/setup.
- Example: **Showroom Flow Control** (fires on check-in), active 3 / run 642.

## New Lead Decision Tree
The **Newly Decision Tree** — most important/complex process. Fires **as soon as a new lead is created** (every lead: Internet, Showroom, Phone Up, Check-in). **Every box is a question; the lead's answer drives the action.**

Page anatomy: **Name** (left, editable via **pencil** top-right) · **Advanced View / Basic View** toggle (**Advanced required when branches exist**; Basic = vertical/linear) · **3-dots (⋮)**: Edit · **Process Execution Log** (leads that came through, expandable step-by-step) · **Audit Log** (who changed what).

Standard flow (yes=left/green, no=right/red):
1. **Lead Status = Active?** YES → continue.
2. **If/Else: Lead Department = Sales?** selected = YES; unselected = NO.
3. **Field check: Source Type** (multi-select: Internet, OEM, etc.). ⚠ **anything NOT checked = no path = lead does nothing** (e.g., Campaign).
4. Branches: OEM / Phone Up / Walk-in / **Internet** (most common).
5. **Internet → If/Else: BDC assigned exists?** NO → **3-day Delay** (waits until lead assignment updated; fires when BDC assigned). YES → dept-hours check.
6. **Dept hours check** (reads Dealer Configuration tile Sales/Service hours). NO (closed) → **Delay until dept opens** → **Go To node** routes back to YES. YES → task creation.
7. Tasks fire **Call → Email → Call (delay 3 hrs)**, then **Delay to Start of Operating Hours** so the next-day workflow fires at open. **Don't delete these delays.**

## Building/Editing a Process
1. Open by clicking name; edit via **pencil** or **3-dots → Edit**.
2. **Basic** (vertical) vs **Advanced** (branches). Basic shows **Immediate actions** (fire on process start) + **delayed actions**.
3. **+ buttons** insert steps. Step types: **Create Task** (Call/Email/Text), Update Task, **Send Email** (system auto-sends ≠ Create Email Task), Send Text, Update Lead, Send Notification, Assign Lead, **Check Field Values**, **If**, **If/Else**, **Delay Task**.
4. **Create Task** settings: Task Due/Overdue timing (e.g., due in 15 min), "Due within operating hours only" (pauses overdue clock after hours), "operating days only."
5. **Task Duplication** (2 options): **Skip** if same-type task already assigned, OR **Cancel existing & assign new** (more popular — Day 2 cancels Day 1). ⚠ "Cancel & replace" **hides pile-ups** (won't see reps not completing tasks).
6. **Conditions/Dependencies** per task (e.g., "email exists", Source = Costco) — fail = step skipped.
7. **Send Email** fields: Reply-to, Reply to BDC, BCC, **template** (Communication Setup), From, conditions.
8. **Moving tasks does NOT change their delay.**
9. **Error indicators:** ⚠ exclamation/hazard on a task; red unconnected-step markers; click **Show** for full issue list.
10. **Save options:** **Publish** (active) · **Save as Draft** (⚠ **makes the process INACTIVE** — never do this to a live process) · **Save as Template**.

## Delay Tasks
- **Time/lead-event delay** (e.g., 3-day) — can end early on an exit event (e.g., "until Lead Assignment updated").
- **Department/Dealership Operating Hours delay** — delay until Start (or End) of Operating Hours; **Go To node** (drag dotted connector) routes flow after timeout. Lead arriving after hours waits, resumes at open.

## Exit Conditions
- **Every process must have an exit condition** (except a terminal Sold process). Missing = "exit workflow missing" error (publishable but incomplete).
- Structure: **Trigger** (Lead Checked In / Updated / Appointment Created / Stage updated…) → **Call Workflow** (which process to launch) → **Properties** (optional gating).
- Examples: Appointment Created → Appointment Created process; Checked In → Showroom Flow Control; **Lead Updated → Task Cleanup** (if status = Bad/Duplicate/Sold/Inactive/Lost → zeros out all tasks); status Closed/Booked → **Sold Follow-Up**.

## Viewing Automation on a Lead
- Leads → open a lead → shows each process that ran with status. **"Completed" = task CREATION completed, not the task done.** **In Queue (Q)** = waiting to fire.
- **Automation Log** (3-dots) shows each condition's **Evaluated True/False**.

## Gotchas
- YES=left/green, NO=right/red.
- Advanced View mandatory when branches exist.
- Active (green) ≠ running.
- **Save as Draft = INACTIVE** — never on a live process.
- Unchecked field-value options = no path = lead silently does nothing.
- Don't delete "delay to start of operating hours."
- "Manual trigger" = system-triggered, not human.
- Create Email Task ≠ Send Email.
- "Cancel & replace" task dedup hides pile-ups.
- Moving tasks doesn't change delay timing.
- Dept hours come from the Dealer Configuration tile.

## Related skills
- `tekion-scheduling` — appointment/scheduling settings (companion CRM/service config)
- `tekion-sitemap` — master nav map
