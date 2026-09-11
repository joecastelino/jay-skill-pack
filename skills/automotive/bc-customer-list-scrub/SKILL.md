---
name: bc-customer-list-scrub
description: >
  Compare/scrub BC customer lists (GM Rewards, Consolidated Leads, etc.) —
  match customers across lists, flag overlaps, and produce Joe's ranked master
  output with GM Rewards first (ranked by $) and secondary list appended.
  Load for ANY BC customer data comparison, list merge, or "scrub these two lists."
triggers:
  - scrub these lists
  - compare gm rewards
  - consolidated lead list
  - combine customer lists
  - bc rewards list
---

# BC Customer List Scrub

## Joe's required output format (MUST follow this)

1. **GM Rewards ranked first** — sorted by Rewards $ highest to lowest
2. **Flag overlap** — rows on BOTH lists get `TOP 50 + OVERLAP` / `OVERLAP` flag
3. **Top 50 highlighted** — `TOP 50` or `TOP 50 + OVERLAP` flag
4. **Secondary list appended** — at bottom, deduped (exclude anyone already in GM section)
5. **One CSV file** — single deliverable, `csv.QUOTE_ALL` to handle commas in dollar amounts

Output columns: Rank, Flag, Source, Customer Name, Email, Phone, Last Visit, Last RO#, Months Since Visit, Rewards $, Rewards Points, Rewards Status, Member #, [CL fields...]

## Matching rules (strict — avoid false positives)

- **Email is truth**: match on normalized email (lowercase, strip spaces/hyphens/parens/dots)
- **Placeholder emails are NOT matches**: `no@no.com`, `none@email.com`, `none@none.com`, `noemail@yahoo.com`, `none@gm.com`, `none@yahoo.com`, `n/a`, empty
- **Email + phone mismatch = different person**: if emails match but phones differ, it's a shared email (like `no@no.com` matching 6+ people) — reject the match
- **Phone-only match** (no email match): only accept if the CL record has a real email (not placeholder)
- GM list has real emails for nearly all customers; CL has many placeholders

## Email delivery

- **Use direct SMTP for CSV attachments**: Stacey bridge times out (>170s) on MIME attachment operations
- SMTP creds in himalaya config (`~/.config/himalaya/config.toml`, key `backend.auth.raw`)
- MIME: `multipart/mixed`, text/plain body, `MIMEBase('text','csv')` + base64 encode + `Content-Disposition: attachment`
- From/To: `jcastelino@americanmotorscorp.com`

## Files

- GM Rewards lapsed: typically a CSV with columns Customer, Email, Phone, Last Visit, Last RO#, Months Since Visit, Rewards $, Rewards Points, Rewards Status, Member #
- Consolidated Lead List: CSV with 72 columns, first row is a disclaimer (skip it), real header on row 2. Key columns: Full Name, Email, Phone, VIN, Year, Model, Retention Status, Rewards Enrollment Status, Reward Points, Last Service Date, Lead Type, Oil Life %
- Output to `/home/itadmin/bc-rewards-scrub/`