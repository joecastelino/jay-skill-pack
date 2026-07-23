---
name: amg-store-manager-meeting-prep
description: >
  Prep Joe for a working meeting with a store service manager (e.g. Ruben at BC,
  Kevin at SCT, Sean at TOL) — actionable items backed by LIVE store baselines
  computed from Jay's cached Tekion pipeline data, framed as what JOE (VP Fixed
  Ops) can do to help, drafted to Joe's own inbox. Use for any "prep a meeting
  with <manager>", "action items for <store>", "what can I do to help him" ask.
trigger: meeting prep, action items for Ruben/Kevin/Sean, all-day meeting, help store manager, store action plan
---

# AMG Store-Manager Meeting Prep (verified 2026-07-07, Ruben/BC)

## THE FRAMING RULE (Joe corrected this hard — get it right first time)
Joe is **VP of Fixed Ops**. When he preps a meeting with a store manager, he does
NOT want the manager's to-do list — he wants **what JOE can do to help**. Frame
every item around Joe's levers the manager doesn't have:
1. **Cross-store data/benchmarking** — Joe sees all 7 stores; commit Jay-built
   scorecards/reports as the measurement the manager gets for free.
2. **Infrastructure Joe owns** — labor rates/ELR grid, Service Menu Setups
   (tier build/pricing), Tekion scheduling settings. A broken/missing tier
   (e.g. BC sold ZERO BSM in June) is a setup problem Joe fixes, not a selling
   problem the manager coaches.
3. **Money/pay-plan authority** — spiffs (per shown appointment, per menu on the
   mid tier), funding Jay's build-outs.
Theme line Joe liked: "I measure, I fix the infrastructure, I fund the
incentives — you run the floor."
First draft as manager-to-do-list gets rejected ("I'm the god damn VP...").

## Data sources — NO live API pull needed (works even during OVERALL_QUOTA 429)
All baselines compute in seconds from cached JSON in
`/home/itadmin/tekion-reports/data/` (BC shown; sibling files exist per store):
- `bc-week-cp-scan.json` — current week per-RO CP cents `{id:{no,cp_cents}}`.
  CP RO = cp_cents>1; rev/RO = total/count.
- `bc-prior4wk-cp-scan.json` — same + `week` index 0-3 → per-week trend, CP mix
  (cp count / total records per week = CP% of closed).
- `bc-menu-closed-mtd-MASTER-<YYYY-MM>.json` — `records` is a DICT (values may
  be lists — flatten); per-menu `{ro,opcode,labor_price,parts_price,advisor,...}`.
  Menu $ = labor_price+parts_price (already dollars, NOT cents here).
  Tier mix = Counter(opcode[-3:]) → BNM/BSM/PSM/VNM.
- Advisor spread = group menus by `advisor` — top-vs-bottom gap is a strong
  talking point (June BC: Juan 29 vs Valentine 2).
Derived KPIs Joe wants: closed ROs/wk, CP ROs/wk + CP%, CP rev/RO (avg + range +
current wk), menus/mo + $/menu, menu penetration = menus ÷ CP ROs (~15% June BC;
target framing 25% = +$X/mo at current avg ticket).

## Deliverable
1. Slack summary first (baseline snapshot + 3 items) for discussion.
2. On approval, Stacey builds ONE draft **TO JOE HIMSELF**
   (jcastelino@americanmotorscorp.com) — confirm recipient; "prep for my
   meeting" = Joe's inbox, NOT the manager. Use the DRAFT-ONLY hard-stop
   phrasing (imap.append to Drafts ONLY, no send/SMTP/X-GM-RAW, override
   hardcoded Kevin/Ruben defaults) + demand terse echo
   `TO= | SUBJECT= | IN_DRAFTS= | SENT=`.
3. Verify independently via himalaya: draft exists in [Gmail]/Drafts with
   correct To:, Sent Mail grep count = 0.

## Offer proactive ammo for the meeting
- BDC/appointments lane usually has NO data feed — the pitch is "commit me to
  build the scheduling pull + daily set/shown/converted scorecard."
- Offer declined-services / customers-due call lists as day-one BDC dial lists.
- If OpenAPI quota is dead, note the zero-quota fallbacks (:9223 in-page APIs,
  part-sales ledger) for any fresh pulls.

## Pitfalls
- MTD master `records` dict values can be lists — flatten before summing.
- CP scan cents need /100; menu master prices are already dollars.
- June master may be stale (asof 6/29) — state the as-of date in the summary.
