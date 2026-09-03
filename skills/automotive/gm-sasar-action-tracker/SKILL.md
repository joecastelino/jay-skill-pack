---
name: gm-sasar-action-tracker
description: Fill out a GM SASAR (warranty self-audit) corrective-action tracker + BAC Action Plan doc for a GM store (built for Blackstone Chevy BC/1251, Ruben Estrada). Joe supplies RO# + GM citation shorthand; Jay pulls each RO from Tekion, verifies the deficiency, writes a full 20-column corrective-action row, and emails the xlsx + paste-ready action-plan rows. Use when Joe mentions SASAR, GM warranty audit/review, "Action Tracker", or gives lists of ROs with GM citations.
---

# GM SASAR Action Tracker (warranty self-audit corrective actions)

## Trigger
Joe: "GM warranty report / SASAR / Action Tracker" for a GM store, then sends lines like
`89783 - Better tech story, rental timeline needs better support documentation` (RO# + GM citation shorthand). Batches of 1–13+ arrive over multiple messages.

## Working assets (BC case, Aug 2026)
- Dir: `/home/itadmin/bc-sasar/` (persistent — NEVER Jay's ephemeral ~)
- Deliverable: `GM_SASAR_Action_Tracker_RUBENS_filled.xlsx` (append ACT-nnn rows here)
- Blank template: `tracker.xlsx`; Action Plan doc export: `gmdoc.txt`; plan rows: `BAC319544_action_plan_rows.txt`
- Google Sheet id `1Lm_r3lLVKdPmBiQ5pyfGhj1-6gof9WpL` (Action Tracker gid=718385741), Doc id `1pKnpjpE6hLwPeCEUgcP29cXuScKuPDiE2oE05RFwFHI` — anonymous `export?format=xlsx` / `format=txt` works (Joe link-shared them)
- BC constants: Review Date **08/11/2026**, Containment Due **09/01/2026**, PAC due 10/03/2026, verification 10/17/2026, Status "PAC In Progress". BAC# **319544**.
- Personnel: **Ruben Estrada — Service Director** (NOT Manager, Joe corrected), Larae Parereti — Warranty Administrator, Craig Holman — Shop Foreman, Arthur Markarian — GM.

## Hard constraints / pitfalls
1. **Do NOT try to edit the live Google Sheet in the browser** — Sheets canvas grid rejects all synthetic input (browser_type, execCommand insertText). Verified failure. Joe approved EMAIL delivery of the filled xlsx instead (`jay_mail.send_report`).
2. Google API tokens fleet-wide = `invalid_grant` (dead since ~Aug 2026). Use anonymous export URLs; if writing to the live sheet is ever required: convert to native Google Sheet + re-auth OAuth.
3. **RO numbers may be typo'd** (e.g. "983878" = 6 digits; BC ROs are 5). Search Tekion for plausible variants (98378/98387), pick by which vehicle/hours FIT the citation (98378 = CT5-V 23.4 hrs across 2 jobs fit "overlapping time"; 98387 = 0.7 hrs did not). Flag the disambiguation to Joe in the email.
4. **Verify every citation against real Tekion data before writing** — pull vehicle (VIN/year/model), warranty jobs, ops, hours. The Finding column must cite actual VIN + hours as evidence. Joe rejects unverified claims.
5. Batch pulls: `POST /repair-orders:search` with `documentNumber IN [...]`, then per-RO `/ro-vehicle`, `/jobs`, `/jobs/{id}/operations` (filter payType==WARRANTY; billDuration is SECONDS). Client: `/home/itadmin/tekion-api/tekion_client.py` (load_config, get_token; dealer bc=1251). Cache to `batch_ros.json`.
6. openpyxl string gotcha in execute_code: apostrophes inside quoted GM citations break f-string escaping — use `chr(8217)` or string concat, avoid `\\'` in single-quoted literals.
7. Row heights: `ws.row_dimensions[n].height = 190` for readability.

## Tracker row structure (cols A–T, one row per ACT-nnn, start row 2)
A ActionID | B Review Date | C Area/Process | D Finding (RO#, vehicle+VIN, hrs, GM citation restated + specific deficiency) | E Severity dropdown | F Immediate Containment | G Containment owner | H Containment due | I 5-Why (numbered 1–5, land on SYSTEMIC cause) | J Root Cause | K Permanent Corrective Action | L PAC owners | M PAC due | N Evidence | O Verification method ("Layered audit — ... 90 days") | P Verify date | Q Status | R,S blank | T GM citation verbatim in quotes

## Severity convention (Joe-approved)
- **Medium** = documentation deficiencies (OLH story/timeline, tech story, SOR/rental docs, sublet bill, TAC case, SBD, overlap)
- **High** = claim-integrity or big-exposure items (VIN mismatch on submission; 30-day extended rental)

## Citation → row pattern library (all Joe-approved)
- **OLH story/timeline** → task-itemized story + time per task + dated sequence; WA checklist gate; SD audits 5 OLH claims/wk × 90d. Link repeat findings to ACT-001's PAC (one program, not N fixes).
- **Root cause of failure missing** → story must state WHY the part failed, not just what was replaced.
- **Rental documentation** → "rental support package": rental agreement dates + RO status timeline + parts order chronology (order/ETA/receipt). SOR variant: attach SOR/PO records mapped to rental days.
- **Extended rental (>threshold)** → High severity; >5 days needs SD pre-approval + day-by-day validation timeline; weekly WIP rental review.
- **VIN mismatch** → High; character-by-character VIN match (RO vs Global Connect vs claim) as checklist gate; 10 claims/wk spot audit × 60d.
- **Sublet** → final vendor invoice attached + reconciled before submission; invoice routing to WA.
- **Incoherent tech story** → 3-Cs (complaint/cause/correction) standard; Foreman QC pre-close + WA second check.
- **Authorized OLH** → authorization logged on RO (who/when/why/hours) at grant time; story accounts for each authorized block.
- **Diag story for OLH** → documented test→result→decision sequence tied to hours.
- **TAC / out-of-box defective part** → stop job, open TAC case, record case# in story, tag part for return.
- **Overlapping time** → SD sign-off netting shared teardown/access per GM labor time guide on multi-op claims.
- **SBD (strategy based diagnosis)** → SBD training seminar (Foreman leads) + SBD steps documented in every warranty diag story; repeat ROs share one PAC as training examples.

## Deliverable per batch (email via jay_mail.send_report to Joe)
1. Updated xlsx attached
2. Per-RO summary bullets (ACT#, RO#, vehicle, hrs, fix one-liner; bold High severities; flag any RO disambiguation)
3. Paste-ready **BAC 319544 Action Plan** rows (HTML table in body + .txt attachment): Observation/Deviation | Job Card # | Correction/Action | Individual Responsible ("Ruben Estrada Service Director / Larae Parereti Warranty Administrator / Craig Holman Shop Foreman") | Implementation Date. Combine same-citation ROs (e.g. both SBD ROs) into one plan row.

## Reuse at other GM stores
Same structure works fleet-wide; swap dealer id, personnel, BAC#, review/containment dates (ALWAYS confirm dates + titles with Joe — he corrected both once). GM citation vocabulary (OLH, SOR, TAC, SBD, Global Connect) is GM-universal.
