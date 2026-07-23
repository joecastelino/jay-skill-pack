# Tekion CRM — Process Automation (Distillation)

Source: CRM Jump Start webinar "Process Automation" — presenter **James Mall, Customer Value Architect (CVA), Tekion**. CRM-side (not Fixed Ops). Webinar recordings live inside Tekion.

> Decision-tree convention (memorize): **YES branch always goes LEFT (green), NO branch always goes RIGHT (red).**

---

## App & Navigation

- **Tile/app name:** **Process Automation** (literally labeled "Process Automation"). This is where **all tasks are fired** and **all processes that run on leads** are handled.
- **Top status filter:** defaults to **Active** — by default you see only *active* processes. (Counterpart state is **Draft** = inactive.)
- **Type filter:** filter by **Rules** and **Processes** (view just rules or just processes).
- **Search box:** free-text search by process name. Useful when you don't know the names yet — type partial names like `internet`, `new`, `sold` to shortcut to matching processes.
- **Left-hand nav = filters by trigger/execution event** (filters the list by what each process is built to execute on):
  - **All** — every active process/rule.
  - **Newly checked in** (lead check-in) — processes that execute when a lead/customer is **checked into the store** (a new lead). Note: a training environment shows many; a real store typically has only **one or two** here.
  - **Lead updated** — execute when something on the lead is updated (e.g., a status field changes, salesperson reassigned, etc.); action taken based on what was updated.
  - **Lead stage updated** — execute when a **lead stage** changes.
  - **Lead custom stage updated** — execute when a **custom stage** changes (e.g., "Sold on Order").
  - (List continues "down the line," each self-explanatory by its trigger name.)

---

## Rules vs Processes

Key mental model: **"Processes run ON a lead. Rules run independently and blindly."**

**PROCESSES**
- Run **on leads** after being fired/triggered.
- Must be **triggered** to start — these are called **manual trigger processes**. "Manual trigger" does **not** mean a human starts it; it means **the system** must tell it to start. Many things can trigger it (lead created, lead updated, appointment created, stage change, etc.).
- More complex; branching logic. The bulk of the webinar focuses here.

**RULES**
- Run **independently/blindly** on a **schedule** — a **Schedule Time Rule** fires at a set time of day.
- A rule **sits every single day** scanning for leads that match its criteria, then executes (creates a call task, email task, creates a lead, assigns, etc.).
- One-shot/standalone logic — runs that one action, done. Can be made complex but typically simple.
- **Common rules you'll see:** `1 Service Appointment`, **1 Year Follow Up**, **1 Year Sold**, **2 Year Sold**, **3 Year Sold**.
- Example rule walkthrough: a "First Service Appointment" Schedule Time Rule runs **every day at 4:00 AM**, looks for leads with status **Booked / Sold / (deprecated) / Closed** that have a **Contract Date within the last 1 day**, then **creates a Lead for service** and assigns it to the BDC (plus other tasks) so the service team follows up to schedule first service.

---

## Reading the Process List

Columns, left → right:

1. **Type** — indicates **Rule** or **Process**.
2. **Name** — process/rule name.
3. **Description** — recommended to write a clear description that "marries" to what the process does (helps identify it later).
4. **Active count** — number of leads **currently in** the process right now.
5. **Run count** — **historical total** number of leads that have ever gone through the process (includes the ones currently active).
6. **Status** — Active (shown in **green**) vs Draft.

**Critical interpretation:**
- **Active (green) ≠ actually running.** A process can be marked Active but show **no active count and no run count** → meaning **no leads are flowing into it**, even though it's "on."
- If you expect leads but see **no numbers**, your setup/trigger may be misconfigured — either ignore it, or fix the setup so leads funnel in.
- Example: **Showroom Flow Control** process — present on essentially every system; fires when a customer is **checked into the store**. e.g., active count **3**, run count **642** (642 total ever, including the current 3).

---

## New Lead Decision Tree

The **Newly Decision Tree** ("new lead decision tree") is the most important and most complex process. Fires **as soon as a new lead is created** (initial firing event = **New Lead**). **Every** new lead funnels here: Internet lead, Showroom lead, Phone Up, Checked-in customer/check-in lead.

Core concept: **every box is a question/decision; based on the lead's answer it takes an action.** Layout shown is the **fairly standard / out-of-the-box** setup (can be customized on request).

Page anatomy:
- **Name** shown on left (e.g., "Newly Decision Tree"); editable via the **pencil** (top-right).
- **Advanced View / Basic View** toggle (top-right). **Advanced View is REQUIRED whenever there are branches.** Basic View = simple **vertical** list, easier for single linear processes.
- **3-dots menu (⋮, top-right):**
  - **Edit** (edit the process).
  - **Process Execution Log** — leads that have come through the process (new leads created). Each lead is expandable (dropdown) to see how it processed step-by-step. (Example lead names appeared, e.g. a Google Ads lead.)
  - **Audit Log** — who changed the process and when (like other Tekion audit logs). Important when multiple people can edit Process Automation.

**Standard flow logic (yes=left/green, no=right/red):**
1. **Field check — Lead Status = Active?** (`if lead status is any of: Active`). YES → continue. (Tons of fields are selectable; here it just confirms the lead is active.)
2. **If/Else — Lead Department = Sales?** If/Else box lets you pick a department; selected = YES branch, anything not selected = NO. (Sales → YES; Service/Parts → NO. You can group e.g. Sales+Service = yes.)
3. **Field-value check — Source Type** (`if source type is any one of...`). Multi-select dropdown (e.g., **Internet, OEM**, etc.). **Gotcha:** if a source type is **not checked**, there's **no answer** for it → process does **nothing** for that lead. (e.g., a **Campaign** lead does nothing if Campaign isn't selected.)
4. Branches by source type: **OEM** path, **Phone Up** path, **Walk-in** path (just checked-in customer), **Internet** path (most common). No match (e.g., campaign) → nothing.
5. **Internet branch → If/Else: "BDC (one) assigned exists?"** (does a BDC user exist on the lead?)
   - **NO (no BDC assigned)** → **Delay** (3-day delay). Waits until **lead assignment is updated**; once a BDC rep is assigned (even 5 min later), it launches and continues. With auto-assignment it can fire immediately; otherwise it waits up to 3 days. (Same logic could target **Salesperson 1 / Salesperson 2** instead of BDC.)
   - **YES (BDC assigned)** → proceed to **Department-hours check.**
6. **Department check — "Within working hours of department" (Sales)?** Reads the **Dealer Configuration tile** for **Sales hours / Service hours**. Choose Sales or Service.
   - **NO (dept closed, e.g. lead arrives 10 PM)** → **Delay Task** (delay until department opens) → on timeout (store opens) → **Go To node** → drag-and-drops (dotted line) back over to the **YES** answer (i.e., re-enters as if dept is now open).
   - **YES (dept open)** → continue to task creation / lead-source checks.
7. **Lead-source check** (optional; may or may not be configured), then **task creation** (call / email / call) with delays.

**Task block specifics in the tree:**
- Tasks fire as **Call → Email → Call (3 hours later)** (the second call has a **delay by 3 hours**).
- After tasks: a **Delay Task = Sales Department Operating Hours**, delaying to **Start of Operating Hours**. (Presenter noted a "double negative" where both delay-to-end and delay-to-start existed; he deletes the redundant one, keeps **delay to start**.)
- **Why the delay matters (key teaching point):** "delay to start of operating hours" makes the workflow (e.g., the **Internet Lead Tasking Workflow**) fire **first thing the next morning** when Sales opens (e.g., 8:30/9:00 AM). Without it, if a lead comes in at 2 PM, every day's tasks would fire at 2 PM. **Do NOT remove these delays** thinking they're clutter.

---

## Building/Editing a Process (numbered)

1. **Open a process:** click its name in the list. Edit via the **pencil** (rename) or **3-dots → Edit**.
2. **Choose view:** **Basic View** (vertical, simple) vs **Advanced View** (required for branches). Basic shows **Immediate actions** (fire the moment the process starts — *not* tied to when the lead was created) plus a series of **delayed actions** (e.g., 30 min later, 1 day, 2 days, 3 days).
3. **Add a step / insert between steps:** use the **+ (plus) buttons** between boxes. Available step types:
   - **Create Task** (→ Call, Email, or Text task assigned to staff)
   - **Update Task**
   - **Send Email** (system auto-sends an email — distinct from *Create Email Task*)
   - **Send Text** (system auto-sends text)
   - **Update Lead**
   - **Send Notification**
   - **Assign Lead**
   - **Check Field Values** (a yes/no field condition)
   - **If** (yes → path; otherwise nothing)
   - **If/Else** (branch giving different answers based on the value)
   - **Delay Task** (see Delay Tasks section)
4. **Configure a Create Task:** pick type (Call/Email/Text). Each type shows **contextual advanced settings**.
   - **Task Due / Overdue timing:** set how long until the lead shows **overdue** (e.g., first task **due in 15 minutes**).
   - **"Due within operating hours only" checkbox:** pauses the overdue clock outside store hours (e.g., a 6-hour due window stops at 5 PM close and resumes next open day).
   - **"Task due in dealership operating days only":** task only shows overdue on days the dealership is open.
5. **Task Duplication options (two, important / newly popular):**
   - **Skip creating the task** if the **same type** of task is already assigned to the user (e.g., yesterday's email task incomplete → no new email task created today; a call would still create).
   - **Cancel existing automatic task of the same type and assign a new one** (more popular) — Day 2 cancels Day 1, only Day 2 shows. Prevents task pile-up. **Gotcha:** because tasks don't pile up, you **won't easily notice** a rep who's not completing tasks (no big overdue count on the dashboard).
6. **Advanced settings on tasks:** **Skip task / communication if communication is not permitted** (respects customer **opt-out**).
7. **Conditions / Dependencies (per task):** conditions that must be true for the task to fire. Add **multiple conditions** — e.g., "**email exists / does not exist**" (don't create an email task if no email), or based on assignee, deal status, last payment date, **Source** (e.g., only send a particular email if Source = Costco), etc. If condition fails, the step is **skipped**.
8. **Send Email step fields:** **Reply-to** (e.g., the salesperson), **Reply to BDC** (CCs the BDC), **BCC** someone, choose a **template** (templates live under **Communication Template / Communication Setup**), set the **From** (salesperson, BDC, etc.), and per-step **conditions**.
9. **Moving tasks:** you can drag/reorder tasks, **but moving does NOT change the delay** on them.
10. **Error indicators:** **hazard / exclamation (⚠) icons** flag a problem on a specific task; **red signs** flag broken/unconnected steps. Click **"Show"** at the bottom to list other issues/warnings.
11. **Bulk edits:** **Bulk Select** a range of steps, then **Delete Steps** to delete everything below a point. When deleting a branch box you get the option to **delete all paths** or **keep the answer/keep everything below**.
12. **Save options (bottom):**
    - **Publish** — saves and makes the process **active**.
    - **Save as Draft** — **moves the process OUT of active INTO draft = makes it INACTIVE.** ⚠ Never "Save as Draft" on your Newly Decision Tree (or any live process) or it stops functioning until you re-edit and **Publish**.
    - **Save as Template** — saves as a reusable template (import/export templates within Tekion; advanced).
13. **Exit:** top-left **Exit** → choose **Discard** to abandon changes.

---

## Delay Tasks

A **Delay Task** puts the lead in a **holding pattern** until a condition/time, then continues to whatever comes next. Two main delay modes:

- **Time/lead-event delay** (e.g., **3-day delay**): waits N days, but can **end early on an exit event** (e.g., "wait until **Lead Assignment is updated**" — fires as soon as a BDC rep is assigned). Optional **delay start time** (start the delay at a certain time of day — usually leave alone).
- **Department / Dealership Operating Hours delay:** delay until **Start of Operating Hours** (or End) of a chosen department (**Sales** or **Service**). If a lead hits this delay outside hours it **immediately holds and waits until the store opens**, then continues.
  - Components: **Timeout** = "store opens" ends the delay; then a **Go To node** routes flow to a chosen point (drag-and-drop the dotted-line connector to any box — commonly back to the YES branch of the prior department-hours check).
  - **Tasks Execution / delay execution:** optionally delay task execution to a specific **time of day** (e.g., fire at 9:10 AM).
  - **Toggle: "Create the tasks at start of next operating hour"** if the lead arrives after operating hours (often unnecessary if upstream logic already checks hours).
- **Inline delay example:** a **"delay by 3 hours"** between a call and the next call task.

---

## Exit Conditions

- **Every process you create must have an exit condition** ("imperative"). Exception: a terminal **Sold** process which is itself an ending process.
- Configure via **Exit Conditions** (the new-process error often reads **"exit workflow missing"** / "configure exit conditions"; a missing exit workflow shows as a **failing result / error message** but doesn't block publishing).
- **Structure of an exit condition:** **Custom Criteria** built from:
  - **Trigger** box(es) — the event that signals this lead should **leave the current process and start another**. Triggers mirror the left-nav events: **Lead Checked In, Lead Updated, Appointment Created, Lead Stage / Custom Stage updated**, etc.
  - **Call Workflow** — which process to launch on that trigger.
  - **Properties** (optional) — field conditions gating the trigger.
- **Worked examples:**
  - **Appointment Created** trigger → call the **Appointment Created** process (every CRM has one; follows up on the appointment).
  - **Checked In** trigger → **Showroom Flow Control** process (holds to determine sold/not-sold; waits for an update/checkout).
  - **Sold on Order** custom stage flag → routes to the **Sold on Order** process.
  - **Lead Updated → "Task Cleanup":** think of it in reverse — *if* lead status is set to any of **Bad / Duplicate / Sold / Inactive / Lost**, fire the **Task Cleanup** template/process, which **zeros out / clears all existing tasks**. Nearly every dealer has a Task Cleanup process; appears on many processes (fires when a lead is sold, marked bad, inactive, etc.).
  - **Lead status is any of Closed / Booked** → fires the **Sold Follow-Up** process (typical sold process = a call task + a follow-up task ~5 days later; customizable).

---

## Gotchas

- **YES = left/green, NO = right/red** — always.
- **Advanced View is mandatory whenever branches exist;** Basic View can't show branching.
- **Active (green) does not mean running.** Zero active/run counts = no leads flowing in → check your triggers/setup.
- **Active count = currently in process; Run count = lifetime total (includes current).**
- **"Save as Draft" = makes the process INACTIVE.** Never do it to a live process (esp. the Newly Decision Tree) or automation stops until re-published.
- **Field-value / source-type checks: anything NOT checked has NO path** → the lead silently does nothing (e.g., Campaign leads if Campaign isn't selected).
- **Don't delete the "delay to start of operating hours" delays** — they're what make tasks fire next-morning at open instead of at the lead's arrival time.
- **"Manual trigger" doesn't mean human-triggered** — the system triggers it.
- **Create Email Task ≠ Send Email** — the former assigns a task to staff; the latter has the system auto-send.
- **Task duplication "cancel & replace" hides pile-ups** — you won't easily see reps who aren't completing tasks (no big overdue count surfaces).
- **Moving/reordering tasks does NOT change their delay timing.**
- **Every process needs an exit condition** or it'll error with "exit workflow missing" (publishable but incomplete).
- **Delay tasks freeze the lead** until their time/event — a lead arriving after hours just waits, then resumes at open.
- Watch the **⚠ exclamation/hazard icons** and **red unconnected-step markers**; click **Show** for the full issue list.
- **Department hours come from the Dealer Configuration tile** (Sales hours / Service hours); the dept-hours check reads those.

---

## Viewing Automation on a Lead

- Go to the **Leads** section → open a lead. Lead-list **columns are adjustable/movable** (e.g., show Source Type).
- The lead shows each process that ran (e.g., **"Newly Decision Tree – Initial Tasks"**), with **status** (completed / queued / not completed) and the delay/task steps (3-day assignment delay, create call/email tasks, the later call, the next-day operating-hours delay, etc.).
- **"Completed" on a task means the task's CREATION completed — not that the task was done.** **"In Queue (Q)"** = waiting to fire based on timing.
- **Automation Log** (also reachable via the process **3-dots**) gives advanced detail showing each condition's **Evaluated True / Evaluated False** (the yes/no answers through the tree).
