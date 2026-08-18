---
name: jay-gmail-draft-verification
description: Independently verify a Gmail draft/send that Stacey (email-agent) reports she created — confirm it's actually in Drafts/Sent with correct recipients, body, and attachments, without trusting her self-report alone. Use whenever Joe asks to "chase" or double-check an email Jay routed through Stacey, or when Jay's own Gmail-dependent flow (himalaya/Google API) throws auth errors.
---

# Verifying Stacey's Gmail Drafts/Sends (Jay's independent check)

Jay routes report emails through Stacey (agent-to-agent-bridge), but Stacey's own
self-report ("IN_DRAFTS=y, SENT=n") is not independently verifiable by default —
Jay needs a read-only path into Joe's Gmail that doesn't depend on Stacey.

## Two independent Gmail auth paths — check BOTH, they fail independently
1. **himalaya IMAP** (`~/.config/himalaya/config.toml`, personal account) — password-based (Gmail app password).
2. **Google OAuth API** (`google_token.json`) — used for `google_api.py gmail search` etc.

Either can be dead while the other works. Don't assume one failure means both are broken.

## Recurring trap: stale Gmail app password (hit 2026-08-07 AND 2026-08-18)
Joe rotates the Gmail app password periodically and typically hands the NEW one
only to Stacey (email-agent). **Each agent has its own separate himalaya config**
— the new password does NOT propagate to Jay's config automatically.

Symptom: `himalaya envelope list -a personal -f "[Gmail]/Drafts"` fails with
`AUTHENTICATIONFAILED — Invalid credentials (Failure)`.

### Fix
1. Get the CURRENT working password from Stacey's config:
   ```
   cat /home/itadmin/.hermes/profiles/email-agent/home/.config/himalaya/config.toml
   ```
   Look at the `raw =` field under `backend.auth` (her config uses flat keys
   like `backend.auth.raw`, not nested `[accounts.personal.backend.auth]` tables
   — different himalaya config style, same effect).
2. Copy that password into Jay's own config, BOTH places:
   `/home/itadmin/.hermes/profiles/jay/home/.config/himalaya/config.toml`
   - `[accounts.personal.backend.auth] raw = "..."`
   - `[accounts.personal.message.send.backend.auth] raw = "..."`
   (use `patch` tool, replace_all not needed — two distinct occurrences, patch each explicitly if `old_string` isn't unique enough).
3. Verify: `himalaya envelope list -a personal -f "[Gmail]/Drafts" -s 3` — should
   list without an explicit `HOME=` override once config.toml is fixed at the
   right path.

If himalaya is fixed but Google OAuth (`google_api.py`) still throws
`invalid_grant: Token has been expired or revoked.` on BOTH Jay's and Stacey's
token copies — that's a SEPARATE, independent failure (needs a fresh OAuth
consent flow via Joe's browser, not self-healable). Don't block draft
verification on fixing OAuth if IMAP already works — IMAP alone is sufficient
to verify a draft.

## Verification commands (once IMAP auth works)
```bash
# Find the draft — Gmail Drafts folder is literally named "[Gmail]/Drafts"
himalaya envelope list -a personal -f "[Gmail]/Drafts" -s 10

# Read the body (confirm To/Cc/Subject/body text match what was requested)
himalaya message read -a personal -f "[Gmail]/Drafts" <id>

# Download attachment(s) to confirm they're real, non-corrupt files
himalaya attachment download -a personal -f "[Gmail]/Drafts" <id>
# NOTE: no -o/--output path flag for filename override (that flag is for output
# FORMAT: plain|json, not a path) — it downloads to /tmp/<original-filename>
# using the attachment's actual filename. Just `ls /tmp/` after to find it.
```

Then sanity-check the downloaded file, e.g. for xlsx:
```python
from openpyxl import load_workbook
wb = load_workbook('/tmp/<file>.xlsx')
print(wb.sheetnames)
```

## Cleaning up duplicate/stale drafts
Retrying a bridge request to Stacey after a timeout (see agent-to-agent-bridge
"Exit 124 ≠ failure" pitfall) commonly produces 2-3 drafts with the IDENTICAL
subject line — the timed-out first attempt, a retry, and Stacey's real
completion. Verified 2026-08-18 (BT filter report): compare bodies with
`himalaya message read` on each ID — the correct one has the intended content
(right numbers, right attachment TYPE e.g. PDF vs xlsx). Delete/trash the rest:

```bash
himalaya message move -a personal -f "[Gmail]/Drafts" "[Gmail]/Trash" <id1> <id2>
```
NOTE: target folder is a POSITIONAL arg, not `-t`/`--target` (that errors
"unexpected argument"). Also `himalaya message delete` fails outright with
"No folder Trash" and `--trash-folder` is not a valid flag — `move` to
`"[Gmail]/Trash"` is the only working deletion path found. Always re-list
Drafts after to confirm only the intended one remains before telling Joe it's
ready for review.

## Pitfalls
- **Never trust "Sent Mail" presence as confirmation of anything** — a draft-only
  ask can still get sent by Stacey (see STACEY DRAFT-ONLY TRAP in memory); always
  check the actual target folder (Drafts) the ask specified.
- Folder name is `"[Gmail]/Drafts"` (with brackets, needs quoting in shell) — a
  bare `Drafts` folder name will 404 with "Unknown Mailbox: Drafts (Failure)".
- If `himalaya` still fails after fixing the password, check whether it's being
  invoked with `HOME=/home/itadmin` override vs relying on the config at
  `/home/itadmin/.hermes/profiles/jay/home/.config/himalaya/config.toml` — both
  should work once the password is current, but a stale copy at
  `/home/itadmin/.config/himalaya/config.toml` (root level, no profile) can also
  exist and cause confusion if accidentally targeted — check profile-scoped path
  first.
- Clean up downloaded verification files from `/tmp/` after checking (temp only, not evidence to keep).
